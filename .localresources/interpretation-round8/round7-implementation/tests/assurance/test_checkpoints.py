"""Adverse and end-to-end checks for the round-seven task checkpoint layer.

These fixtures exercise accounting and provenance.  They do not establish that
the synthetic English rule is legally correct.
"""
from copy import deepcopy

import pytest

from legalmath.canonical import digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.checkpoints import (
    CheckpointQueue, fidelity_plan, plan_tasks, task_spec, receipt, verify_receipt,
)
from legalmath.interpretation.assurance.relevance import (
    RelevanceReview, relevance_request, validate_relevance,
)
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import Allowance, Completion
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.decomposition import compact_request
from tests.assurance.support import inventory, packet, reading


ROUTE = digest({'provider': 'test.checkpoint.v1', 'model': 'fixture'})


def _claims(n=51):
    template = inventory()['claims'][0]
    return [{**deepcopy(template), 'claim_id': f'claim.{i:02d}'} for i in range(n)]


def _candidates(n=4):
    return {f'candidate.{i}': reading() for i in range(n)}


def _settings():
    return Settings(timeout_seconds=2, max_input_bytes=200_000, max_output_bytes=200_000)


def _fidelity_answer(request):
    claims = {c['claim_id']: c for c in request['claims']}
    candidates = {c['candidate_id']: c['representation'] for c in request['candidates']}
    pairs = request['required_pairs']
    return {'checks': [
        {'claim_id': pair['claim_id'], 'candidate_id': pair['candidate_id'],
         'label': 'ENTAILED', 'source_evidence': deepcopy(claims[pair['claim_id']]['evidence']),
         'representation_quotes': [candidates[pair['candidate_id']]],
         'rationale': 'Controlled fixture; source and representation are deliberately aligned.',
         'failing_stage': 'NONE', 'question': None}
        for pair in pairs], 'additional_concerns': []}


class _CountedProvider:
    provider_id = 'test.checkpoint.v1'
    live = True

    def __init__(self, allowance, route, responder):
        self.allowance, self.route, self.responder = allowance, route, responder

    def complete(self, request, schema, settings):
        wire = compact_request(request)
        slot = self.allowance.reserve(digest(wire))
        value = self.responder(request)
        return Completion(value, {
            'provider': self.provider_id, 'fresh_context': True,
            'request_hash': digest(wire), 'response_hash': digest(value),
            'original_request_hash': digest(request), 'wire_request_hash': digest(wire),
            'compact_request': wire,
            'allowance_slot': slot, 'provider_route_hash': self.route,
            'usage': [], 'configuration': 'synthetic fixture',
        })


def _queue(tmp_path, *, claims=None, candidates=None, batch_size=4, maximum_attempts=3):
    claims = claims or _claims()
    candidates = candidates or _candidates()
    plan = fidelity_plan(packet(), claims, candidates, ROUTE,
                         batch_size=batch_size, maximum_attempts=maximum_attempts)
    return CheckpointQueue(tmp_path / 'queue', plan), plan, claims, candidates


def _provider_factory(tmp_path, responder, maximum=500):
    allowance_path = tmp_path / 'allowance.json'
    allowance = Allowance(allowance_path, maximum, reservation_ceiling=maximum)
    return allowance_path, lambda _path: _CountedProvider(allowance, ROUTE, responder)


def test_plan_has_exact_204_pairs_and_reproducible_task_ids(tmp_path):
    queue, plan, claims, candidates = _queue(tmp_path)
    assert len(plan['tasks']) == 51
    assert sum(len(t['context']['required_pairs']) for t in plan['tasks']) == 204
    assert len({p for t in plan['tasks'] for p in map(tuple, t['context']['required_pairs'])}) == 204
    assert plan['tasks'] == fidelity_plan(packet(), claims, candidates, ROUTE, batch_size=4)['tasks']
    assert queue.report()['status'] == 'INCOMPLETE'


def test_synthetic_204_pair_run_is_counted_and_aggregates_once(tmp_path):
    queue, plan, _, _ = _queue(tmp_path)
    ledger, factory = _provider_factory(tmp_path, _fidelity_answer)
    result = queue.run(factory, ledger, _settings(), maximum_actions=51, deadline_seconds=60,
                       backoff_seconds=0)
    assert result['status'] == 'COMPLETE_CHECKS'
    assert result['completed_tasks'] == 51 and result['attempts'] == 51
    aggregate = queue.aggregate_fidelity()
    assert aggregate == {'status': 'NO_ISSUE_DETECTED_IN_PROFILE', 'execution_complete': True,
                         'pairs': 204, 'findings': 0, 'legal_accuracy_evaluated': False,
                         'release_eligible': False}
    ledger_value = loads(ledger.read_bytes())
    assert len(ledger_value['calls']) == 51
    assert len(loads((tmp_path / 'queue' / 'aggregate.json').read_bytes())['checks']) == 204


def test_repair_cannot_change_source_candidates_or_required_pairs(tmp_path):
    queue, plan, claims, candidates = _queue(tmp_path, claims=_claims(1), candidates=_candidates(1),
                                             batch_size=1, maximum_attempts=2)
    ledger, _ = _provider_factory(tmp_path, _fidelity_answer)
    base = plan['tasks'][0]['request']
    broken = deepcopy(_fidelity_answer(base)); broken['checks'][0]['representation_quotes'] = []
    seen = []

    def responder(request):
        seen.append(request)
        if request['task'] == 'REPAIR_OUTPUT':
            assert request['source_packet'] == base['source_packet']
            assert request['claims'] == base['claims']
            assert request['candidates'] == base['candidates']
            return _fidelity_answer(request)
        return broken

    _, factory = _provider_factory(tmp_path, responder)
    report = queue.run(factory, ledger, _settings(), maximum_actions=2, deadline_seconds=30,
                       backoff_seconds=0)
    assert report['status'] == 'COMPLETE_CHECKS' and len(seen) == 2
    assert seen[1]['repair_of_request_hash'] == digest(base)
    forged = deepcopy(seen[1]); forged['claims'][0]['statement'] = 'changed'
    with pytest.raises(LegalMathError) as error:
        from legalmath.interpretation.assurance.checkpoints import _validate_repair_request
        _validate_repair_request(forged, plan['tasks'][0])
    assert error.value.code == 'E_INTEGRITY'
    assert 'protected request field' in error.value.details


def test_interrupted_reservation_requires_explicit_recovery_then_can_retry(tmp_path):
    queue, _, _, _ = _queue(tmp_path, claims=_claims(1), candidates=_candidates(1),
                            batch_size=1, maximum_attempts=2)
    ledger, _ = _provider_factory(tmp_path, _fidelity_answer)
    interrupted = {'seen': False}

    def crash(request):
        if not interrupted['seen']:
            interrupted['seen'] = True
            raise KeyboardInterrupt()
        return _fidelity_answer(request)

    _, factory = _provider_factory(tmp_path, crash)
    with pytest.raises(KeyboardInterrupt):
        queue.run(factory, ledger, _settings(), maximum_actions=1, deadline_seconds=30,
                  backoff_seconds=0)
    with pytest.raises(LegalMathError) as error:
        queue.report()
    assert error.value.code == 'E_JOB_STATE'
    assert queue.recover() == 1
    assert queue.report()['status'] == 'INCOMPLETE'
    _, factory = _provider_factory(tmp_path, _fidelity_answer)
    report = queue.run(factory, ledger, _settings(), maximum_actions=1, deadline_seconds=30,
                       backoff_seconds=0)
    assert report['status'] == 'COMPLETE_CHECKS'
    assert len(loads(ledger.read_bytes())['calls']) == 2  # interrupted calls are never refunded


def test_manifest_mutation_and_route_mismatch_are_hard_integrity_failures(tmp_path):
    queue, _, _, _ = _queue(tmp_path, claims=_claims(1), candidates=_candidates(1),
                            batch_size=1)
    ledger, factory = _provider_factory(tmp_path, _fidelity_answer)
    queue.run(factory, ledger, _settings(), maximum_actions=1, deadline_seconds=30, backoff_seconds=0)
    attempt = next((tmp_path / 'queue' / 'attempts').glob('*/attempt-001'))
    response = attempt / 'response.json'
    value = loads(response.read_bytes()); value['value']['additional_concerns'] = ['tampered']
    save(response, value)
    with pytest.raises(LegalMathError, match='integrity'):
        queue.report()


def test_source_only_relevance_requires_all_claims_and_uncertainty_question():
    claims = _claims(1)
    request = relevance_request(packet(), claims, 'introductory-purpose')
    quote = {'unit_id': 'p1', 'quote': packet()['units'][0]['text']}
    value = {'decisions': [{'claim_id': claims[0]['claim_id'], 'role': 'UNRESOLVED',
                            'evidence': [quote], 'reasoning': 'The purpose statement may qualify scope.',
                            'unresolved_question': 'Which operative provision makes this claim applicable?'}],
             'questions': ['Confirm whether the purpose statement changes the selected control scope.']}
    assert validate_relevance(value, packet(), claims)['decisions'][0]['role'] == 'UNRESOLVED'
    missing = deepcopy(value); missing['decisions'] = []
    with pytest.raises(LegalMathError):
        validate_relevance(missing, packet(), claims)
    value['decisions'][0]['unresolved_question'] = None
    with pytest.raises(LegalMathError):
        validate_relevance(value, packet(), claims)


def test_completed_task_resume_spends_nothing_and_incomplete_aggregate_is_refused(tmp_path):
    queue, plan, _, _ = _queue(tmp_path, claims=_claims(2), candidates=_candidates(1), batch_size=1)
    ledger, factory = _provider_factory(tmp_path, _fidelity_answer)
    queue.run(factory, ledger, _settings(), maximum_actions=1, backoff_seconds=0)
    with pytest.raises(LegalMathError) as error:
        queue.aggregate_fidelity()
    assert error.value.code == 'E_JOB_STATE'
    resumed = CheckpointQueue(tmp_path/'queue', plan)
    assert resumed.run(factory, ledger, _settings(), maximum_actions=1, backoff_seconds=0)['execution_complete']
    assert resumed.run(factory, ledger, _settings(), maximum_actions=10, backoff_seconds=0)['slice_actions'] == 0
    assert len(loads(ledger.read_bytes())['calls']) == 2


def test_exact_historical_import_is_free_and_new_grant_stays_separate(root, tmp_path):
    parent = root/'artifacts/interpretation/round6/D1F/attempt-01/live/investigation'
    seed = root/'artifacts/interpretation/round6/D1S/attempt-02/live'
    origin = seed/'calls/call-000'
    original = loads((origin/'response.json').read_bytes())
    route = original['provenance']['provider_route_hash']
    plan = fidelity_plan(*[loads((parent/name).read_bytes()) for name in ('packet.json','claims.json','candidates.json')], route)
    queue = CheckpointQueue(tmp_path/'import', plan)
    ledger = root/'artifacts/interpretation/round2/live-allowance.json'
    before = ledger.read_bytes()
    queue.import_response(plan['tasks'][0]['task_id'], origin, seed, ledger)
    assert ledger.read_bytes() == before
    report = queue.report()
    assert report['completed_tasks'] == report['imported_tasks'] == 1
    assert report['attempts'] == 0 and len(report['pending_task_ids']) == 50
    assert not report['execution_complete'] and not report['release_eligible']
    with pytest.raises(LegalMathError):
        queue.import_response(plan['tasks'][0]['task_id'], origin, seed, ledger)


@pytest.mark.parametrize('mutation', ['route', 'reservation', 'response', 'history'])
def test_receipt_detects_route_response_and_reservation_changes(tmp_path, mutation):
    queue, plan, _, _ = _queue(tmp_path, claims=_claims(1), candidates=_candidates(1))
    request = plan['tasks'][0]['request']
    ledger, factory = _provider_factory(tmp_path, _fidelity_answer)
    answer = factory(tmp_path).complete(request, plan['tasks'][0]['schema'], _settings())
    response = {'value': answer.value, 'provenance': answer.provenance}
    proof = receipt(request, response, ledger, ROUTE)
    if mutation == 'route': response['provenance']['provider_route_hash'] = '0'*64
    if mutation == 'reservation': response['provenance']['allowance_slot'] = 2
    if mutation == 'response': response['value']['additional_concerns'].append('altered')
    if mutation == 'history':
        value = loads(ledger.read_bytes()); value['calls'][0]['issued_at_ns'] = '1'; save(ledger, value)
    with pytest.raises(LegalMathError) as error:
        verify_receipt(proof, request, response, ROUTE)
    assert error.value.code == 'E_INTEGRITY'


def test_missing_pairs_receive_exact_bounded_feedback_then_exhaust(tmp_path):
    queue, plan, _, _ = _queue(tmp_path, claims=_claims(1))
    seen = []
    def omit(request):
        seen.append(request)
        value = _fidelity_answer(request); value['checks'].pop()
        return value
    ledger, factory = _provider_factory(tmp_path, omit)
    report = queue.run(factory, ledger, _settings(), maximum_actions=10, backoff_seconds=0)
    assert report['attempts'] == 3 and report['exhausted_task_ids'] == [plan['tasks'][0]['task_id']]
    assert not report['execution_complete'] and len(loads(ledger.read_bytes())['calls']) == 3
    assert seen[1]['validation_error_data']['counts']['missing_pairs'] == 1
    assert seen[1]['invalid_response'] == _fidelity_answer(plan['tasks'][0]['request']) | {'checks': seen[1]['invalid_response']['checks']}
    assert queue.run(factory, ledger, _settings(), maximum_actions=10)['slice_actions'] == 0


@pytest.mark.parametrize('error,details,expected,calls', [
    ('E_RESOURCE_LIMIT','Shared live allowance or reviewed increment exhausted','ALLOWANCE_OR_RESOURCE_EXHAUSTED',1),
    ('E_RESOURCE_LIMIT','Input byte cap','ALLOWANCE_OR_RESOURCE_EXHAUSTED',1),
    ('E_DEPENDENCY','Authentication failed','DEPENDENCY',1),
    ('E_DEPENDENCY','Temporarily unavailable','PROVIDER_CIRCUIT_OPEN',2),
    ('E_RESOURCE_LIMIT','Codex call deadline','PROVIDER_CIRCUIT_OPEN',2),
])
def test_permanent_limits_and_consecutive_transport_failures_stop_slice(tmp_path,error,details,expected,calls):
    queue, _, _, _ = _queue(tmp_path, claims=_claims(2), candidates=_candidates(1), batch_size=1)
    def fail(request): raise LegalMathError(error, details=details)
    ledger, factory = _provider_factory(tmp_path, fail)
    result = queue.run(factory, ledger, _settings(), maximum_actions=100, backoff_seconds=0)
    assert result['stop_reason'] == expected and result['slice_actions'] == calls
    assert not result['execution_complete'] and result['completed_tasks'] == 0


def test_changed_plan_or_stale_method_cannot_resume(tmp_path):
    queue, plan, _, _ = _queue(tmp_path)
    changed = deepcopy(plan); changed['route_hash'] = '0'*64
    with pytest.raises(LegalMathError) as error: CheckpointQueue(tmp_path/'queue', changed)
    assert error.value.code == 'E_IDEMPOTENCY'
    changed = deepcopy(plan); changed['method_hash'] = '0'*64
    with pytest.raises(LegalMathError) as error: CheckpointQueue(tmp_path/'other', changed)
    assert error.value.code == 'E_STALE_REVIEW'


def test_criticism_missing_candidates_and_bad_signed_attack_are_rejected(tmp_path):
    from legalmath.interpretation.assurance.arguments import criticism_request
    from legalmath.interpretation.assurance.checkpoints import validate_task
    from .test_integration import responder
    candidates = _candidates(2); claims = _claims(1)
    request = criticism_request(packet(), claims, candidates)
    task = task_spec('CRITICISM', request, {'packet':packet(), 'candidates':candidates})
    valid = responder()(request)
    assert validate_task(task, valid) == valid
    missing = deepcopy(valid); missing['arguments'].pop()
    with pytest.raises(LegalMathError): validate_task(task, missing)
    invalid = deepcopy(valid)
    invalid['attacks'] = [{'attacker':'arg.0', 'target':'arg.1', 'kind':'REBUT',
        'target_component':'arg.1', 'rationale':'A shared sign cannot rebut.'}]
    with pytest.raises(LegalMathError) as error: validate_task(task, invalid)
    assert error.value.details['errors'][0]['kind'] == 'REBUT'
