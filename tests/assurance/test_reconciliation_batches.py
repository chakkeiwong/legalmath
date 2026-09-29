"""Output partitioning preserves whole inputs and cannot hide incomplete work."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from legalmath.canonical import canonical, digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import reconciliation_batches as rb, readable_tables, source_references
from legalmath.interpretation.assurance.single_reader import validate_reconciliation


@pytest.fixture(scope='module')
def source_case():
    root = Path(__file__).resolve().parents[2]
    request = json.loads((root/'artifacts/assurance-continuation/2026-09-29/split-capacity/run/model/action-0015/references/original-request.json').read_text())
    study = json.loads((root/'artifacts/assurance-successor/2026-09-28/study-source-freeze.json').read_text())
    packet = next(t['packet'] for t in study['tasks'] if t['task_id'] == '26ec35')
    return request, packet, request['interpretation'], request['coverage']


def answer(case, selected):
    request, packet, interpretation, coverage = case
    return {'packet_hash': digest(packet), 'interpretation_hash': digest(interpretation),
        'coverage_hash': digest(coverage),
        'concerns': [{'concern_id': c, 'status': 'RETAINED_UNRESOLVED', 'evidence': [],
                      'rationale': 'Synthetic accounting fixture; meaning remains unresolved.'} for c in selected],
        'questions': [{'question_id': q['control_id'], 'question_hash': digest(q),
                       'status': 'UNRESOLVED', 'rationale': 'Synthetic accounting fixture.'} for q in interpretation['questions']],
        'revised_interpretation': None, 'remaining_uncertainty': ['No legal quality label.']}


def test_actual_full_source_and_all_concerns_survive_each_bounded_request(source_case):
    original, _, _, coverage = source_case
    before = canonical(original); groups = rb.batches(coverage)
    assert [len(g) for g in groups] == [66, 66, 66, 65]
    assert [i for g in groups for i in g] == [c['concern_id'] for c in coverage['concerns']]
    for group in groups:
        request, schema = rb.request(original, group)
        assert canonical(request['source_packet']) == canonical(original['source_packet'])
        assert canonical(request['coverage']) == canonical(coverage)
        assert request['output_identity_contract']['question_hashes'] == {
            q['control_id']: digest(q) for q in original['interpretation']['questions']}
        assert set(schema['$defs']['QuestionDisposition']['properties']['question_hash']['enum']) == set(
            request['output_identity_contract']['question_hashes'].values())
        wire, _, _ = source_references.prepare(request, schema)
        encoded = readable_tables.encode(wire)
        assert len(canonical(encoded)) < 200000
        assert canonical(readable_tables.decode(encoded, expected_request_hash=digest(wire))) == canonical(wire)
    assert canonical(original) == before


def test_join_checks_original_hashes_and_every_concern_exactly_once(source_case):
    _, packet, interpretation, coverage = source_case
    pieces = [{'selected_concern_ids': g, 'value': answer(source_case, g)} for g in rb.batches(coverage)]
    report = rb.join(packet, interpretation, coverage, pieces)
    assert report['accounting_complete'] and len(report['addressed_concerns']) == 263
    assert report['missing_concerns'] == [] and not report['automatic_revision_applied']
    assert report['legal_correctness'] == 'NOT_ESTABLISHED'


def test_partial_join_retains_all_missing_concerns(source_case):
    _, packet, interpretation, coverage = source_case
    group = rb.batches(coverage)[0]
    report = rb.join(packet, interpretation, coverage, [{'selected_concern_ids': group, 'value': answer(source_case, group)}])
    assert not report['accounting_complete'] and len(report['missing_concerns']) == 197


@pytest.mark.parametrize('mutation', ['duplicate', 'foreign', 'omission', 'hash', 'unsupported_explanation'])
def test_batched_output_cannot_borrow_or_invent_evidence(source_case, mutation):
    _, packet, interpretation, coverage = source_case
    group = rb.batches(coverage)[0]; value = answer(source_case, group)
    if mutation == 'duplicate': value['concerns'][-1] = deepcopy(value['concerns'][0])
    if mutation == 'foreign': value['concerns'][0]['concern_id'] = rb.batches(coverage)[1][0]
    if mutation == 'omission': value['concerns'].pop()
    if mutation == 'hash': value['coverage_hash'] = 'c'*64
    if mutation == 'unsupported_explanation': value['concerns'][0]['status'] = 'PROPOSED_SOURCE_EXPLANATION'
    with pytest.raises(LegalMathError):
        validate_reconciliation(value, packet, interpretation, coverage, required_concerns=group)


def test_old_whole_response_validator_still_rejects_a_partial_response(source_case):
    _, packet, interpretation, coverage = source_case
    with pytest.raises(LegalMathError):
        validate_reconciliation(answer(source_case, rb.batches(coverage)[0]), packet, interpretation, coverage)


def test_duplicate_piece_and_divergent_questions_cannot_be_hidden(source_case):
    _, packet, interpretation, coverage = source_case
    groups = rb.batches(coverage)
    one = {'selected_concern_ids': groups[0], 'value': answer(source_case, groups[0])}
    with pytest.raises(LegalMathError): rb.join(packet, interpretation, coverage, [one, one])
    two = {'selected_concern_ids': groups[1], 'value': answer(source_case, groups[1])}
    two['value']['questions'][0]['status'] = 'NON_EXECUTABLE_PROPOSAL'
    report = rb.join(packet, interpretation, coverage, [one, two])
    assert len(report['question_disagreements']) == 1
    assert report['cross_batch_semantic_consistency'] == 'NOT_ESTABLISHED'


def test_empty_join_cannot_conceal_duplicate_original_concern_ids(source_case):
    _, packet, interpretation, original = source_case
    coverage = deepcopy(original); coverage['concerns'].append(deepcopy(coverage['concerns'][0]))
    with pytest.raises(LegalMathError): rb.join(packet, interpretation, coverage, [])
