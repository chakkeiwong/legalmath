"""Adversarial accounting/capacity tests; no legal-quality acceptance."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from legalmath.canonical import canonical, digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import investigation_answer as answer
from legalmath.interpretation.assurance import staged_investigation_answer as staged
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.search.models import Settings
from tests.search.support import FunctionProvider
from scripts.legal_mission_staged_answer import receipt
from .test_successor_workflow import investigation


@pytest.fixture(scope='module')
def prepared(investigation):
    root, runner, _, dossier = investigation
    with TemporaryDirectory(prefix='staged-answer-test-', dir=root / 'artifacts') as td:
        directory = Path(td)
        save(directory / 'qualification.json', {
            'profile': 'investigation-answer-source-qualification.v1',
            'source_packet_hash': digest(loads((root / dossier['packet']['path']).read_bytes())),
            'limitations': ['Synthetic fixture.'], 'evidence': [dossier['packet']], 'details': {}})
        ref = evidence_file(runner.directory / 'revisions' / dossier['revision'] / 'dossier.json', root)
        arguments = {'investigation_directory': runner.directory, 'expected_revision': dossier['revision'],
            'questions': [{'question_id': 'gift', 'text': 'Selected gift control'}],
            'qualification_ref': evidence_file(directory / 'qualification.json', root)}
        original = answer.prepare_request(root, ref, **arguments)
        partition = staged.partition(original)
        yield root, directory, ref, arguments, original, partition


def test_exact_registry_restores_repeated_judgments_concerns_and_disagreement(prepared):
    original = deepcopy(prepared[4])
    scoped = original['investigation']['scoped']
    scoped['batches'][0]['proposals'][0]['additional_concerns'] = [
        {'question': 'Contrary premise outside this batch', 'candidate_ids': ['unformalized']}]
    index = staged.registry(scoped)
    assert staged.restore(index) == scoped
    assigned = prepared[5]['batches']
    assert [r for b in assigned for r in b] == list(prepared[5]['registry']['records'])
    first = next(iter(index['records']))
    index['records'][first]['value']['rationale'] = 'tampered'
    with pytest.raises(LegalMathError):
        staged.restore(index)


def test_actual_dossier_to_staged_consumer_retains_raw_evidence_and_legally_empty_limit(prepared):
    root, directory, ref, args, original, _ = prepared
    provider = FunctionProvider(receipt)
    result = staged.propose(root, ref, provider, directory / 'valid', **args)
    assert result['status'] == 'STRUCTURALLY_VALID_PROPOSAL'
    assert not result['legal_quality_evaluated'] and not result['tool_consideration_verified']
    raw = loads((directory / 'valid/review-000-raw.json').read_bytes())
    assert 'No legal conclusion' in raw['value']['findings'][0]['conclusion']
    assert loads((directory / 'valid/original-request.json').read_bytes()) == original
    assert len(provider.requests) == result['review_batches'] + 1
    assert all(r['source_qualification'] == original['source_qualification'] for r in provider.requests)
    assert all(r['candidates'] == original['candidates'] for r in provider.requests)
    with pytest.raises(FileExistsError):
        staged.propose(root, ref, provider, directory / 'valid', **args)


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'foreign', 'binding', 'quote', 'dependency'])
def test_invalid_review_cannot_enter_synthesis(prepared, fault):
    p = prepared[5]
    request = staged.review_request(p['common'], p['registry'], p['batches'][0])
    value = receipt(request)
    if fault == 'missing': value['accounts'][0]['record_ids'].pop()
    if fault == 'duplicate': value['accounts'] *= 2
    if fault == 'foreign': value['accounts'][0]['record_ids'][0] = 'foreign'
    if fault == 'binding': value['review_binding'] = '0' * 64
    if fault == 'quote':
        value['findings'][0]['support'] = [{'unit_id': request['source_packet']['units'][0]['unit_id'],
                                          'quote': 'Invented source text.'}]
    if fault == 'dependency': value['findings'][0]['cross_record_dependencies'] = ['foreign']
    with pytest.raises(LegalMathError):
        staged.validate_review(value, request)


def test_cross_batch_dependencies_and_unformalized_readings_stay_explicit(prepared):
    original = deepcopy(prepared[4])
    reading = deepcopy(next(iter(original['candidates'].values())))
    reading['formalization'] = None
    original['candidates']['unformalized'] = reading
    p = staged.partition(original)
    request = staged.review_request(p['common'], p['registry'], [p['batches'][0][0]])
    value = receipt(request)
    outside = next(r for r in p['registry']['records'] if r not in value['accounts'][0]['record_ids'])
    value['findings'][0]['cross_record_dependencies'] = [outside]
    assert staged.validate_review(value, request)['findings'][0]['cross_record_dependencies'] == [outside]
    assert request['candidates']['unformalized']['formalization'] is None


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'hash', 'binding'])
def test_synthesis_requires_every_bound_review(prepared, fault):
    original, p = prepared[4:]
    reviews = [receipt(staged.review_request(p['common'], p['registry'], b)) for b in p['batches']]
    request = staged.synthesis_request(original, p, reviews)
    value = receipt(request)
    staged.validate_synthesis(value, request, original)
    if fault == 'missing': value['review_account'].pop()
    if fault == 'duplicate': value['review_account'] *= 2
    if fault == 'hash': value['review_account'][0]['review_hash'] = '0' * 64
    if fault == 'binding': value['stage_binding'] = '0' * 64
    with pytest.raises(LegalMathError):
        staged.validate_synthesis(value, request, original)


def test_common_context_capacity_stops_before_dispatch(prepared):
    root, directory, ref, args, _, _ = prepared
    provider = FunctionProvider(lambda _: pytest.fail('Capacity failure dispatched'))
    result = staged.propose(root, ref, provider, directory / 'overflow', **args,
                            settings=Settings(max_input_bytes=1000))
    assert result['status'] == 'CAPACITY_BLOCKED' and result['provider_calls'] == 0
    assert (directory / 'overflow/original-request.json').exists()


def test_complete_oversized_record_cannot_be_split_or_discarded(prepared):
    original = deepcopy(prepared[4])
    original['investigation']['scoped']['batches'][0]['proposals'][0]['checks'][0]['rationale'] = 'x' * 210000
    with pytest.raises(LegalMathError) as exc:
        staged.partition(original)
    assert exc.value.code == 'E_RESOURCE_LIMIT'


def test_rejected_review_is_retained_and_not_retried(prepared):
    root, directory, ref, args, _, _ = prepared
    def bad(request):
        value = receipt(request)
        value['accounts'] = []
        return value
    provider = FunctionProvider(bad)
    result = staged.propose(root, ref, provider, directory / 'rejected', **args)
    assert result['status'] == 'REJECTED' and len(provider.requests) == 1
    assert (directory / 'rejected/review-000-raw.json').exists()


def test_mutation_during_review_blocks_further_calls(prepared):
    root, directory, ref, args, _, _ = prepared
    args = deepcopy(args)
    q = loads((root / args['qualification_ref']['path']).read_bytes())
    path = directory / 'mutable-qualification.json'
    save(path, q)
    args['qualification_ref'] = evidence_file(path, root)
    def mutate(request):
        q['limitations'] = ['Changed during review.']
        save(path, q)
        return receipt(request)
    provider = FunctionProvider(mutate)
    result = staged.propose(root, ref, provider, directory / 'changed', **args)
    assert result['status'] == 'REJECTED' and len(provider.requests) == 1


def test_actual_synthesis_payload_is_admitted_after_reviews(prepared, monkeypatch):
    root, directory, ref, args, _, _ = prepared
    normal = staged.synthesis_request
    def oversized(*a, **kw):
        value = normal(*a, **kw)
        value['reviews'][0]['findings'][0]['conclusion'] = 'x' * 210000
        return value
    monkeypatch.setattr(staged, 'synthesis_request', oversized)
    provider = FunctionProvider(receipt)
    result = staged.propose(root, ref, provider, directory / 'synthesis-overflow', **args)
    assert result['status'] == 'CAPACITY_BLOCKED'
    assert all(r['task'] == 'REVIEW_SCOPED_EVIDENCE' for r in provider.requests)
    assert (directory / 'synthesis-overflow/synthesis-request.json').exists()
