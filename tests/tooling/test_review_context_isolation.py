"""The context repair may move an idle owner, never erase or duplicate its work."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import signal
from types import SimpleNamespace

import pytest

from scripts import legal_review_context_isolation as isolation
from scripts import legal_review_deployment as deployment
from scripts.legal_mission_execution import Refused, digest, read, ref, save


def idle_owner(tmp_path, monkeypatch):
    from scripts import legal_mission_execution as execution
    owner = dict(pid=987654, start='123')
    monkeypatch.setattr(isolation, 'ROOT', tmp_path)
    for name in ('worker.json', 'armed.json'):
        save(tmp_path/isolation.DEPLOYMENT/name, dict(process=owner))
    state = dict(tasks={'baseline-p14': dict(status='RUNNING', attempts=[dict(number=i) for i in range(1,6)],
        master_live=True, live_supervisor=owner)})
    save(tmp_path/isolation.STATE, state)
    (tmp_path/isolation.DOC).mkdir(parents=True, exist_ok=True)
    save(tmp_path/isolation.DEPLOYMENT/'service/service-circuit.json', dict(open=False))
    save(tmp_path/isolation.BASE/'live-calls.json', dict(calls=[dict(slot=1)]))
    save(tmp_path/isolation.SOURCE/'arms/p14/baseline/calls/dispatch.json',
         dict(calls={'one': dict(status='VALIDATED')}))
    live = [True]
    monkeypatch.setattr(execution, 'process_identity', lambda _: owner if live[0] else None)
    monkeypatch.setattr(execution, 'process_alive', lambda _: live[0])
    original = Path.read_text

    def read_text(path, *args, **kwargs):
        if str(path).startswith('/proc/'):
            return '' if path.name == 'children' else '987654 (python) T 0 0'
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', read_text)
    signals = []

    def kill(pid, number):
        assert pid == owner['pid']
        signals.append(number)
        if number == signal.SIGTERM:
            live[0] = False

    monkeypatch.setattr(isolation.os, 'kill', kill)
    return owner, signals


@pytest.mark.parametrize('problem', ['open', 'half_open_request_hash', 'half_open_schema_hash',
    'half_open_reserved', 'reserved', 'child', 'identity', 'another_owner', 'p14_owner'])
def test_uncertain_handover_sends_no_signals(tmp_path, monkeypatch, problem):
    from scripts import legal_mission_execution as execution
    owner, signals = idle_owner(tmp_path, monkeypatch)
    if problem in ('open', 'half_open_request_hash', 'half_open_schema_hash', 'half_open_reserved'):
        save(tmp_path/isolation.DEPLOYMENT/'service/service-circuit.json',
             dict(open=False, **{problem: 'pending'}) if problem != 'open' else dict(open=True))
    elif problem == 'reserved':
        save(tmp_path/isolation.SOURCE/'arms/p14/baseline/calls/dispatch.json',
             dict(calls={'one': dict(status='RESERVED')}))
    elif problem == 'child':
        original = Path.read_text
        monkeypatch.setattr(Path, 'read_text', lambda p,*a,**k:
            '555' if str(p).startswith('/proc/') and p.name=='children' else original(p,*a,**k))
    elif problem == 'identity':
        monkeypatch.setattr(execution, 'process_identity', lambda _: None)
    else:
        state = read(tmp_path/isolation.STATE)
        foreign = dict(pid=111, start='222')
        if problem == 'p14_owner':
            state['tasks']['baseline-p14']['live_supervisor'] = foreign
        else:
            state['tasks']['another'] = dict(status='RUNNING', master_live=True, live_supervisor=foreign)
        save(tmp_path/isolation.STATE, state)
    if problem in ('identity', 'another_owner', 'p14_owner'):
        with pytest.raises(Refused):
            isolation.settle()
    else:
        assert isolation.settle()['settled'] is False
    assert signals == []
    assert not (tmp_path/isolation.HERE/'handover.json').exists()


def test_busy_provider_is_left_running(tmp_path, monkeypatch):
    import fcntl
    _, signals = idle_owner(tmp_path, monkeypatch)
    with (tmp_path/isolation.DEPLOYMENT/'service/service-worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert isolation.settle()['settled'] is False
    assert signals == []


def test_idle_handover_preserves_attempts_and_is_idempotent(tmp_path, monkeypatch):
    owner, signals = idle_owner(tmp_path, monkeypatch)
    before = (tmp_path/isolation.STATE).read_bytes()
    receipt = isolation.settle()
    assert receipt['process'] == owner and receipt['supervisor_ended'] and receipt['service_settled']
    assert receipt['calls'] == 1 and receipt['reserved_dispatches'] == 0
    assert signals == [signal.SIGSTOP, signal.SIGTERM, signal.SIGCONT]
    assert (tmp_path/isolation.STATE).read_bytes() == before
    assert isolation.settle() == receipt
    assert len(signals) == 3


def test_journal_created_during_handover_resumes_owner(tmp_path, monkeypatch):
    _, signals = idle_owner(tmp_path, monkeypatch)
    original = isolation.os.kill

    def signal_and_create(pid, number):
        original(pid, number)
        if number == signal.SIGSTOP:
            save(tmp_path/isolation.SOURCE/'arms/gatecoin/baseline/calls/dispatch.json', dict(calls={}))

    monkeypatch.setattr(isolation.os, 'kill', signal_and_create)
    with pytest.raises(Refused, match='stable idle boundary'):
        isolation.settle()
    assert signals == [signal.SIGSTOP, signal.SIGCONT]
    assert not (tmp_path/isolation.HERE/'handover.json').exists()


@pytest.mark.parametrize('problem', [None, 'request', 'result', 'reserved', 'veto'])
def test_seed_authenticates_calls_and_retains_failures(tmp_path, monkeypatch, problem):
    from scripts import legal_integration_campaign as campaign
    from legalmath.interpretation.assurance.bounded_context import Limits
    from legalmath.interpretation.assurance.bounded_product import BoundDispatch
    monkeypatch.setattr(isolation, 'ROOT', tmp_path)
    provider = SimpleNamespace(check=lambda: None, live=False)
    monkeypatch.setattr(campaign, 'provider', lambda: provider)
    limits = Limits()
    directory = tmp_path/isolation.SOURCE/'arms/p14/baseline'
    checker = BoundDispatch(provider, directory/'calls', SimpleNamespace(limits=limits))
    checker.capacity_manager = True
    save(directory/'identity.json', dict(limits=asdict(limits), common_capacity_profile='common-stage-capacity.v1'))
    save(tmp_path/'individual.json', dict(original='unchanged'))
    checkpoint = dict(profile='common-capacity-checkpoint.v1', input_hash='same', calls={},
                      individual_reviews=ref(tmp_path, 'individual.json'))
    save(tmp_path/'checkpoint.json', checkpoint)
    save(tmp_path/isolation.PROGRAM, dict(review_repair=dict(deployment=dict(
        arm_checkpoints={'p14': {'baseline': ref(tmp_path,'checkpoint.json')}}))))
    saved = dict(input_hash='same', calls={})
    for key, status in [('pass', 'VALIDATED'), ('fail', 'FAILED')]:
        request = dict(task='AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS', content=key)
        shape = dict(type='object')
        result = dict(status=status, value=dict(verdict='UNRESOLVED'))
        if key == 'fail' and problem == 'veto':
            result['continuation_veto'] = True
        saved['calls'][key] = dict(status=status, identity=checker.request_identity(request,shape),
                                  result_hash=digest(result))
        if key == 'fail' and problem == 'request': request['content']='changed'
        if key == 'fail' and problem == 'result': result['value']['verdict']='ACCEPT'
        if key == 'fail' and problem == 'reserved': saved['calls'][key]['status']='RESERVED'
        for name, value in [('request', request), ('schema', shape), ('result', result)]:
            save(directory/'calls'/key/(name+'.json'), value)
    save(directory/'calls/dispatch.json', saved)
    save(tmp_path/isolation.BASE/'live-calls.json', dict(calls=[1,2]))
    save(tmp_path/isolation.HERE/'baseline.json', dict(calls=2))
    save(tmp_path/isolation.HERE/'handover.json', dict(ledger=ref(tmp_path,isolation.BASE/'live-calls.json')))
    before = (directory/'calls/dispatch.json').read_bytes()
    if problem:
        with pytest.raises(Refused):
            isolation.seed()
        assert not (tmp_path/isolation.HERE/'seed.json').exists()
    else:
        assert isolation.seed() == dict(imported_calls=2, provider_calls=0)
        seeded = read(tmp_path/isolation.HERE/'seed.json')
        current = read(tmp_path/seeded['arm_checkpoints']['p14']['baseline']['path'])
        assert current['individual_reviews'] == checkpoint['individual_reviews']
        assert current['calls']['pass']['mode'] == 'VALIDATED'
        assert current['calls']['fail']['mode'] == 'RETAINED_FAILURE'
        assert read(tmp_path/current['calls']['pass']['result']['path'])['value']['verdict'] == 'UNRESOLVED'
        from legalmath.interpretation.assurance.phased.capacity_checkpoint import retained
        product = SimpleNamespace(root=tmp_path,
            capacity_checkpoint=seeded['arm_checkpoints']['p14']['baseline'],
            route=SimpleNamespace(input_hash='same', limits=limits, encode=lambda s:list(s)))
        checked=[]
        for key, status in [('pass','VALIDATED'),('fail','FAILED')]:
            folder=directory/'calls'/key
            reused=retained(product, dict(key=key, request=read(folder/'request.json'),
                schema=read(folder/'schema.json'), validate=lambda value: checked.append(value)))
            assert reused['status']==status
            if key=='pass':
                assert reused['provenance']['new_provider_calls']==0
                assert reused['value']['verdict']=='UNRESOLVED'
        assert checked==[dict(verdict='UNRESOLVED')]
    assert (directory/'calls/dispatch.json').read_bytes() == before


def test_same_attempt_all_history_and_vetoes_survive_projection(tmp_path):
    before = dict(tasks={'baseline-p14': dict(status='RUNNING', attempts=[dict(number=n) for n in range(1,6)]),
        'done': dict(status='SUCCEEDED', attempts=[dict(number=1)], result='preserve')},
        events=[dict(action='original')], continuation_vetoes=[dict(reason='unrelated veto')])
    save(tmp_path/'before.json', before)
    revision = dict(prior_state=ref(tmp_path,'before.json'), review={})
    program = dict(review_repair=dict(deployment=dict(context_isolation=revision)))
    current = isolation.project_state(before, program, 'now')
    isolation.validate_history(program, current, tmp_path)
    assert current['tasks'] == before['tasks']
    for kind in ('attempt', 'event', 'veto', 'success'):
        changed=deepcopy(current)
        if kind=='attempt': changed['tasks']['baseline-p14']['attempts'].pop()
        elif kind=='event': changed['events'][0]={'action':'different'}
        elif kind=='veto': changed['continuation_vetoes']=[]
        else: changed['tasks']['done']['result']='different'
        with pytest.raises(Refused): isolation.validate_history(program, changed, tmp_path)


def test_worker_uses_new_receipts_only_after_registration(tmp_path, monkeypatch):
    monkeypatch.setattr(deployment, 'ROOT', tmp_path)
    value = dict(review_repair=dict(deployment={}))
    save(tmp_path/deployment.PROGRAM, value)
    assert deployment.worker_directory() == deployment.HERE
    value['review_repair']['deployment']['context_isolation']={'profile':'corrected-context-isolation.v1'}
    save(tmp_path/deployment.PROGRAM, value)
    assert deployment.worker_directory() == isolation.HERE


def test_mutable_service_archives_do_not_replace_historical_identities():
    rows=[dict(previous={'path':p,'sha256':'same'},archive={'path':'before/'+p,'sha256':'same'})
          for p in [isolation.CHANGED[0], str(isolation.DEPLOYMENT/'service/service-circuit.json'),
                    str(isolation.PROGRAM)]]
    assert set(isolation.mapped(rows)) == {(isolation.CHANGED[0], 'same')}
    assert set(isolation.mapped(rows, mission=True)) == {
        (isolation.CHANGED[0], 'same'), (str(isolation.PROGRAM), 'same')}
