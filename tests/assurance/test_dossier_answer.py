"""Whole-evidence preservation, dependency delivery and bounded reduction controls."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from legalmath.canonical import digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import dossier_answer as whole
from legalmath.interpretation.assurance import investigation_answer as answer
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.search.models import Settings
from scripts.legal_mission_context_boundary import receipt
from tests.search.support import FunctionProvider
from .test_successor_workflow import investigation


@pytest.fixture(scope='module')
def prepared(investigation):
    root, runner, _, dossier = investigation
    with TemporaryDirectory(prefix='whole-dossier-test-', dir=root / 'artifacts') as td:
        directory = Path(td)
        save(directory / 'qualification.json', {
            'profile': 'investigation-answer-source-qualification.v1',
            'source_packet_hash': digest(loads((root / dossier['packet']['path']).read_bytes())),
            'limitations': ['Synthetic local fixture; source applicability unassessed.'],
            'evidence': [dossier['packet']], 'details': {}})
        ref = evidence_file(runner.directory / 'revisions' / dossier['revision'] / 'dossier.json', root)
        args = {'investigation_directory': runner.directory, 'expected_revision': dossier['revision'],
            'questions': [{'question_id': 'gift', 'text': 'Selected gift control'}],
            'qualification_ref': evidence_file(directory / 'qualification.json', root)}
        original = answer.prepare_request(root, ref, **args)
        yield root, directory, ref, args, original


def test_all_substantive_categories_reconstruct_exactly_with_unformalized_readings(prepared):
    original = deepcopy(prepared[4])
    other = deepcopy(next(iter(original['candidates'].values())))
    other['formalization'] = None
    original['candidates']['unformalized'] = other
    original['investigation']['new_substantive_category'] = {'contrary': ['Do not discard this qualification.']}
    p = whole.partition(original)
    index = p['registry']
    assert whole.restore(index) == original
    assert [rid for group in p['batches'] for rid in group] == list(index['records'])
    assert 'candidates' not in index['common'] and 'source_claims' not in index['common']
    assert 'investigation' not in index['common'] and 'source_criticism' not in index['common']
    rid = index['readings']['unformalized']
    assert whole.record_value(index, index['records'][rid])['formalization'] is None
    assert any('new_substantive_category' in r['path'] for r in index['records'].values())
    reviews = [receipt(whole.review_request(index, group)) for group in p['batches']]
    req = whole.interaction_request(original, p, reviews)
    synthesis = whole.synthesis_request(original, p, reviews, receipt(req))
    assert synthesis['candidates']['unformalized'] == other
    assert synthesis['source_qualification'] == original['source_qualification']


def test_judgment_dependency_group_carries_exact_claim_reading_and_role(prepared):
    original = prepared[4]
    index = whole.registry(original)
    rid, record = next((rid, r) for rid, r in index['records'].items()
        if isinstance(whole.record_value(index, r), dict) and {'claim_id', 'candidate_id', 'source_support'} <= whole.record_value(index, r).keys()
        and 'proposals' in r['path'])
    request = whole.review_request(index, [rid])
    ids = {r['record_id'] for r in request['records']}
    assert index['readings'][whole.record_value(index, record)['candidate_id']] in ids
    assert index['source_claims'][whole.record_value(index, record)['claim_id']] in ids
    assert request['assigned_records'] == [rid]
    assert any('attempt_assignment' in s['fields'] for s in record['scopes'])
    assert any(s['fields'].get('attempt_assignment', {}).get('role') for s in record['scopes'])


def test_exact_duplicate_rows_share_content_but_preserve_every_occurrence(prepared):
    original = deepcopy(prepared[4])
    batch = original['investigation']['scoped']['batches'][0]
    row = deepcopy(batch['proposals'][0]['checks'][0])
    batch['proposals'][0]['checks'].append(row)
    index = whole.registry(original)
    matches = [r for r in index['records'].values() if whole.record_value(index, r) == row]
    assert len(matches) >= 2 and len({r['content_id'] for r in matches}) == 1
    assert len({r['occurrence_id'] for r in matches}) == len(matches)
    assert all(len(r['occurrences']) == 1 for r in matches)
    assert whole.restore(index) == original


def test_contextual_references_and_nested_arguments_keep_their_definitions(prepared):
    original = deepcopy(prepared[4])
    candidate = next(iter(original['candidates']))
    claim = original['source_claims'][0]['claim_id']
    original['contextual_evidence'] = {'candidate_id': candidate, 'claim_id': claim,
        'rows': [{'argument_id': 'outer', 'attacks': ['inner']}],
        'nested_rows': [{'arguments': [{'argument_id': 'inner', 'premise': 'Preserved whole row.'}]}]}
    index = whole.registry(original)
    rid = next(rid for rid, row in index['records'].items()
               if whole.record_value(index, row) == {'argument_id': 'outer', 'attacks': ['inner']})
    request = whole.review_request(index, [rid])
    supplied = {row['record_id'] for row in request['records']}
    nested = next(rid for rid, row in index['records'].items()
                  if row['path'] == ['contextual_evidence', 'nested_rows', 0])
    assert {index['readings'][candidate], index['source_claims'][claim], nested} <= supplied
    assert whole.restore(index) == original


def test_orphaned_judgment_is_not_detached_from_its_missing_claim(prepared):
    original = deepcopy(prepared[4])
    original['investigation']['scoped']['batches'][0]['proposals'][0]['checks'][0]['claim_id'] = 'absent'
    with pytest.raises(LegalMathError, match='Reference does not resolve'):
        whole.registry(original)


@pytest.mark.parametrize('fault', ['value', 'scope', 'dependency', 'missing'])
def test_archive_tampering_is_rejected(prepared, fault):
    index = whole.registry(prepared[4])
    rid = next(iter(index['records']))
    if fault == 'value': index['contents'][index['records'][rid]['content_id']] = 'changed'
    if fault == 'scope': index['records'][rid]['scopes'] = [{'false_role': True}]
    if fault == 'dependency': index['dependencies'][rid] = [] if index['dependencies'][rid] else ['foreign']
    if fault == 'missing': del index['records'][rid]
    with pytest.raises(LegalMathError): whole.restore(index)


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'quote', 'binding', 'foreign_dependency'])
def test_invalid_review_cannot_enter_interaction(prepared, fault):
    p = whole.partition(prepared[4]); index = p['registry']
    req = whole.review_request(index, p['batches'][0]); value = receipt(req)
    if fault == 'missing': value['accounts'][0]['record_ids'].pop()
    if fault == 'duplicate': value['accounts'] *= 2
    if fault == 'quote': value['findings'][0]['support'] = [{'unit_id': req['source_packet']['units'][0]['unit_id'], 'quote': 'Invented law'}]
    if fault == 'binding': value['review_binding'] = '0' * 64
    if fault == 'foreign_dependency': value['findings'][0]['cross_record_dependencies'] = ['absent']
    with pytest.raises(LegalMathError): whole.validate_review(value, req)


def test_cross_group_dependency_is_supplied_to_mandatory_interaction(prepared):
    original = prepared[4]
    p = whole.partition(original, maximum_records_per_group=20)
    assert len(p['batches']) > 1
    reviews = [receipt(whole.review_request(p['registry'], b)) for b in p['batches']]
    other = p['batches'][-1][-1]
    reviews[0]['findings'][0]['cross_record_dependencies'] = [other]
    req = whole.interaction_request(original, p, reviews)
    assert other in {r['record_id'] for r in req['dependency_records']}
    interaction = receipt(req)
    whole.validate_interaction(interaction, req)
    interaction['review_account'].pop()
    with pytest.raises(LegalMathError): whole.validate_interaction(interaction, req)


def test_oversized_indivisible_reading_stops_before_any_reduction(prepared):
    original = deepcopy(prepared[4])
    next(iter(original['candidates'].values()))['substantive_oversize'] = 'x' * 210000
    with pytest.raises(LegalMathError) as exc: whole.partition(original)
    assert exc.value.code == 'E_RESOURCE_LIMIT'


def test_actual_product_to_whole_consumer_includes_interaction_and_legal_limit(prepared):
    root, directory, ref, args, _ = prepared
    provider = FunctionProvider(receipt)
    result = whole.propose(root, ref, provider, directory / 'valid', **args)
    assert result['status'] == 'STRUCTURALLY_VALID_PROPOSAL', result
    assert result['provider_calls'] == result['review_groups'] + 2
    assert [r['task'] for r in provider.requests[-2:]] == ['REVIEW_DOSSIER_INTERACTIONS', 'SYNTHESIZE_WHOLE_DOSSIER_ANSWER']
    assert not result['legal_quality_evaluated'] and not result['tool_consideration_verified']
    value = loads((directory / 'valid/answer-proposal.json').read_bytes())
    assert value['answers'][0]['answer'] == 'No legal answer evaluated.'
    with pytest.raises(FileExistsError): whole.propose(root, ref, provider, directory / 'valid', **args)


@pytest.mark.parametrize('stage', ['interaction', 'synthesis'])
def test_aggregate_overflow_stops_before_affected_dispatch(prepared, monkeypatch, stage):
    root, directory, ref, args, _ = prepared
    function = getattr(whole, stage + '_request')
    def overflow(*a, **kw):
        value = function(*a, **kw)
        value['overflow'] = 'x' * 210000
        return value
    monkeypatch.setattr(whole, stage + '_request', overflow)
    provider = FunctionProvider(receipt)
    result = whole.propose(root, ref, provider, directory / (stage + '-overflow'), **args)
    assert result['status'] == 'CAPACITY_BLOCKED'
    blocked = 'REVIEW_DOSSIER_INTERACTIONS' if stage == 'interaction' else 'SYNTHESIZE_WHOLE_DOSSIER_ANSWER'
    assert all(r['task'] != blocked for r in provider.requests)


def test_invalid_or_oversized_review_is_retained_without_retry(prepared):
    root, directory, ref, args, _ = prepared
    def invalid(request):
        result = receipt(request); result['accounts'] = []; return result
    provider = FunctionProvider(invalid)
    result = whole.propose(root, ref, provider, directory / 'rejected', **args)
    assert result['status'] == 'REJECTED' and len(provider.requests) == 1
    assert (directory / 'rejected/review-000-raw.json').exists()


def test_final_contract_rejects_lost_reading_tool_or_interaction(prepared):
    original = deepcopy(prepared[4]); p = whole.partition(original)
    reviews = [receipt(whole.review_request(p['registry'], b)) for b in p['batches']]
    req = whole.interaction_request(original, p, reviews)
    request = whole.synthesis_request(original, p, reviews, receipt(req))
    response = receipt(request)
    whole.validate_synthesis(response, request, original)
    missing = deepcopy(response); missing['reading_account'] = []
    with pytest.raises(LegalMathError): whole.validate_synthesis(missing, request, original)
    wrong = deepcopy(response); wrong['interaction_hash'] = '0' * 64
    with pytest.raises(LegalMathError): whole.validate_synthesis(wrong, request, original)
