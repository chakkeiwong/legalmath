from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
from types import SimpleNamespace

import pytest

from legalmath.errors import LegalMathError
from scripts import legal_integration_qualification_continuation as continuation
from scripts.legal_integration_master import task, MasterExecution
from scripts.legal_mission_execution import read, save, ref, digest, validate_task_graph, Refused


def test_retained_controls_replay_without_any_live_method(tmp_path, monkeypatch):
    from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
    def forbidden(*args, **kwargs):
        pytest.fail('Replay attempted a provider action')
    for method in ('check', 'complete', 'fork'):
        monkeypatch.setattr(BoundedCodexProvider, method, forbidden)
    work = continuation.WORK / 'local-replay-test'
    monkeypatch.setattr(continuation, 'WORK', work)
    result = continuation.replay_controls()
    assert result['valid'] and result['provider_calls'] == 0
    assert [row['slot'] for row in result['rows']] == [2113, 2115]
    assert result['failed_slot_preserved'] == 2114
    first = (continuation.ROOT / work / 'retained-replay.json').read_bytes()
    continuation.replay_controls()
    assert (continuation.ROOT / work / 'retained-replay.json').read_bytes() == first


@pytest.mark.parametrize('tamper', ['receipt-bytes', 'request', 'schema', 'slot', 'incomplete'])
def test_corrupt_or_mismatched_retained_receipt_is_rejected(tmp_path, tamper):
    request, schema = {'request': 'exact'}, {'type': 'object'}
    directory = tmp_path / 'receipt'
    for name, value in (('request.json', request), ('schema.json', schema), ('result.json', {'ok': True})):
        save(directory / name, value)
    manifest = {'allowance_slot': 2113, 'complete_output_present': True,
        'request_hash': digest(request), 'files': {}}
    for path in directory.iterdir():
        data = path.read_bytes()
        manifest['files'][path.name] = {'bytes': len(data), 'retained_sha256': hashlib.sha256(data).hexdigest()}
    save(directory / 'manifest.json', manifest)
    assert continuation.verify_receipt(tmp_path, directory, 2113, request, schema)[0] == {'ok': True}
    if tamper == 'receipt-bytes':
        save(directory / 'result.json', {'ok': False})
    elif tamper == 'request':
        request = {'request': 'changed'}
    elif tamper == 'schema':
        schema = {'type': 'array'}
    elif tamper == 'slot':
        manifest['allowance_slot'] = 2115
    else:
        manifest['complete_output_present'] = False
    save(directory / 'manifest.json', manifest)
    with pytest.raises(Refused):
        continuation.verify_receipt(tmp_path, directory, 2113, request, schema)


def test_only_missing_control_is_dispatched(tmp_path, monkeypatch):
    from scripts import legal_integration_phased_live as live
    monkeypatch.setattr(continuation, 'ROOT', tmp_path)
    monkeypatch.setattr(continuation, 'WORK', tmp_path / 'new')
    save(tmp_path / 'request.json', {'exact': 'missing'})
    save(tmp_path / 'envelope.json', {'source': 'exact'})
    case = {'name': 'near-cap-missing', 'request': ref(tmp_path, 'request.json'),
        'envelope': ref(tmp_path, 'envelope.json'), 'measurement': {'bytes': 1}}
    save(tmp_path / 'inputs.json', {'cases': [{'name': 'largest-actual'}, case, {'name': 'near-cap-exception'}]})
    replay = {'rows': [{'name': 'largest-actual', 'passed': True}, {'name': 'near-cap-exception', 'passed': True}]}
    save(tmp_path / 'new/retained-replay.json', replay)
    save(tmp_path / continuation.PROGRAM, {continuation.KEY: {
        'qualification_inputs': ref(tmp_path, 'inputs.json'),
        'retained_replay': ref(tmp_path, 'new/retained-replay.json')}})
    save(tmp_path / continuation.BASE / 'current-binding.json', {'binding': 'exact'})
    monkeypatch.setattr(continuation, 'replay_controls', lambda: replay)
    monkeypatch.setattr(continuation, 'tokenizer', lambda *args: list)
    monkeypatch.setattr(live, 'phase_admit', lambda owner: owner)
    calls, constructors = [], []
    class Product:
        def __init__(self, *args, **kwargs):
            constructors.append(kwargs)
            self.dispatch = SimpleNamespace(measure=lambda *args: case['measurement'])
        def run_phase(self, name, requests):
            calls.extend(requests)
            return {'results': [{'result': {'status': 'VALIDATED'}}]}
    monkeypatch.setattr(continuation, 'PhasedProduct', Product)
    outcome = continuation.qualify_accounts(object())
    assert outcome['_node_status'] == 'SUCCEEDED'
    assert len(calls) == len(constructors) == 1
    assert calls[0]['request'] == {'exact': 'missing'}
    assert constructors[0]['maximum_calls'] == 1
    assert constructors[0]['phase_admit'] == 'account-qualification-near-cap-missing'
    result = read(tmp_path / 'new/live/account-qualification/result.json')
    assert result['qualified'] and result['reused_slots'] == [2113, 2115]


def graph():
    nodes = [task(t, ['current-binding'] if t == 'account-qualification' else []) for t in continuation.REOPEN]
    nodes += [task('semantic-preflight'), task('acquire-p10', ['account-qualification']),
        task('baseline-p10', ['acquire-p10']), task('tool-p10-bm25', ['acquire-p10']),
        task('compare-p10-bm25', ['baseline-p10', 'tool-p10-bm25']), task('independent')]
    before = {'tasks': {n['id']: {'attempts': [{'preserved': True}]} for n in nodes}}
    pointer = {'path': 'review.md', 'sha256': 'bound'}
    revision = {k: pointer for k in ('review', 'baseline', 'local_review', 'qualification_inputs', 'retained_replay')}
    old = {'profile': 'legal-mission-execution.v1', 'workers': 2, 'artifact_directory': 'out',
        'deadline_utc': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        'tasks': nodes, 'protected_evidence': []}
    return old, before, revision, pointer


def test_graph_preserves_attempts_deadline_and_independent_completion(tmp_path):
    old, before, revision, pointer = graph()
    frozen = deepcopy((old, before))
    new = continuation.expected_program(old, before, revision, None, plan_reference=pointer)
    assert (old, before) == frozen
    assert new['deadline_utc'] == old['deadline_utc']
    nodes = validate_task_graph(new, tmp_path, reviewed={n['id']: n['maximum_attempts'] for n in new['tasks']}, ceiling_limit=18)
    for original in old['tasks']:
        updated = next(n for n in new['tasks'] if n['id'] == original['id'])
        if original['id'] not in continuation.REOPEN:
            assert updated == original
    assert not nodes['corpus-qualification']['_dependencies']
    assert not nodes['campaign']['requires']
    assert {'current-binding', 'semantic-preflight', 'account-qualification'} <= set(nodes['campaign']['after'])
    assert {'corpus-qualification', 'campaign', 'baseline-p10', 'tool-p10-bm25', 'compare-p10-bm25'} <= set(nodes['continuation-review']['after'])


def test_live_failure_leaves_independent_work_and_completion_reviews_ready(tmp_path):
    nodes = [task('binding'), task('account', ['binding']), task('corpus'),
        task('campaign', after=['account']), task('acquire', ['account']),
        task('review', after=['corpus', 'campaign', 'acquire'])]
    program = {'profile': 'legal-mission-execution.v1', 'workers': 2, 'artifact_directory': 'out',
        'deadline_utc': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        'tasks': nodes, 'protected_evidence': []}
    save(tmp_path / 'program.json', program)
    execution = MasterExecution(tmp_path, 'program.json', 'state.json')
    save(tmp_path / 'evidence.json', {'actual': True})
    def finish(tid, status):
        execution.start(tid)
        path = tid + '.json'
        save(tmp_path / path, {'task_id': tid, 'status': status, 'conclusion': 'Retained outcome',
            'next_action': 'Continue independent', 'evidence': [ref(tmp_path, 'evidence.json')]})
        execution.finish(tid, path)
    finish('binding', 'SUCCEEDED'); finish('account', 'FAILED')
    assert set(execution.summary()['ready']) == {'corpus', 'campaign'}
    finish('corpus', 'BLOCKED'); finish('campaign', 'BLOCKED')
    view = execution.summary()
    assert view['tasks']['acquire']['status'] == 'DEPENDENCY_BLOCKED'
    assert view['ready'] == ['review']
