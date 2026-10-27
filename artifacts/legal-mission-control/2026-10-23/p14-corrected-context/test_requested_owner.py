"""Operational tests: no provider calls, no production state writes."""
import importlib.util
from pathlib import Path
import signal
from types import SimpleNamespace
import pytest
from scripts.legal_mission_execution import read,save,Refused

spec=importlib.util.spec_from_file_location('requested_owner',Path(__file__).with_name('requested_owner.py'))
ops=importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)

def fixture(root,monkeypatch):
    owner=dict(pid=987654,start='123')
    dead=dict(pid=111,start='222')
    monkeypatch.setattr(ops,'ROOT',root)
    monkeypatch.setattr(ops,'authenticate',lambda:dict(old_owner=owner))
    monkeypatch.setattr(ops,'children',lambda identity:'')
    monkeypatch.setattr(ops,'state_of',lambda identity:'T')
    alive=[True]
    monkeypatch.setattr(ops,'process_identity',lambda pid:owner if pid==owner['pid'] and alive[0] else None)
    monkeypatch.setattr(ops,'process_alive',lambda identity:identity==owner and alive[0])
    signals=[]
    def kill(pid,sig):
        assert pid==owner['pid']
        signals.append(sig)
        if sig==signal.SIGTERM: alive[0]=False
    monkeypatch.setattr(ops.os,'kill',kill)
    for name in ('worker.json','armed.json'):
        save(root/ops.isolation.HERE/name,dict(process=owner))
    (root/ops.isolation.HERE/'worker.log').write_text('old')
    save(root/ops.HERE/'operation.json',dict(test=True))
    save(root/ops.BASE/'current-binding.json',dict(phase_service_scope=dict(path='service/scope.json')))
    save(root/'service/service-circuit.json',dict(open=False))
    save(root/ops.BASE/'live-calls.json',dict(calls=[dict(slot=1)]))
    state=dict(tasks={
        'baseline-p14':dict(status='RUNNING',attempts=[{}]*5,master_live=True,live_supervisor=dead),
        'tool-gatecoin-bm25':dict(status='RUNNING',attempts=[{}]*2,master_live=True,live_supervisor=owner)})
    save(root/ops.STATE,state)
    save(root/ops.isolation.RUNTIME/'arms/gatecoin/bm25/calls/dispatch.json',
         dict(calls={'answer':dict(status='VALIDATED')}))
    return owner,signals

@pytest.mark.parametrize('problem',['reserved','child','open','half_open','foreign','identity','busy'])
def test_unsafe_handover_never_signals(tmp_path,monkeypatch,problem):
    owner,signals=fixture(tmp_path,monkeypatch)
    held=None
    if problem=='reserved':
        save(tmp_path/ops.isolation.RUNTIME/'arms/gatecoin/bm25/calls/dispatch.json',dict(calls={'x':dict(status='RESERVED')}))
    elif problem=='child': monkeypatch.setattr(ops,'children',lambda _: '555')
    elif problem=='open': save(tmp_path/'service/service-circuit.json',dict(open=True))
    elif problem=='half_open': save(tmp_path/'service/service-circuit.json',dict(open=False,half_open_request_hash='pending'))
    elif problem=='foreign': monkeypatch.setattr(ops,'process_alive',lambda _:True)
    elif problem=='identity': monkeypatch.setattr(ops,'process_identity',lambda _:None)
    else:
        import fcntl
        held=(tmp_path/'service/service-worker.lock').open('a')
        fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
    try:
        if problem in ('foreign','identity'):
            with pytest.raises(Refused): ops.settle_once()
        else: assert ops.settle_once()['settled'] is False
    finally:
        if held: held.close()
    assert signals==[]

def test_idle_handover_preserves_state_and_calls(tmp_path,monkeypatch):
    owner,signals=fixture(tmp_path,monkeypatch)
    before={p:(tmp_path/p).read_bytes() for p in (ops.STATE,ops.BASE/'live-calls.json')}
    result=ops.settle_once()
    assert result['supervisor_ended'] and result['process']==owner
    assert signals==[signal.SIGSTOP,signal.SIGTERM,signal.SIGCONT]
    assert all((tmp_path/p).read_bytes()==data for p,data in before.items())
    assert ops.settle_once()==result
    assert len(signals)==3

def test_new_journal_after_stop_resumes_without_termination(tmp_path,monkeypatch):
    _,signals=fixture(tmp_path,monkeypatch)
    original=ops.os.kill
    def kill(pid,sig):
        original(pid,sig)
        if sig==signal.SIGSTOP:
            save(tmp_path/ops.isolation.RUNTIME/'arms/new/calls/dispatch.json',dict(calls={}))
    monkeypatch.setattr(ops.os,'kill',kill)
    with pytest.raises(Refused,match='boundary'): ops.settle_once()
    assert signals==[signal.SIGSTOP,signal.SIGCONT]

def test_changed_binding_after_stop_resumes_without_termination(tmp_path,monkeypatch):
    _,signals=fixture(tmp_path,monkeypatch)
    old=ops.authenticate
    count=[0]
    def authenticate():
        count[0]+=1
        if count[0]>1: raise Refused('Changed binding')
        return old()
    monkeypatch.setattr(ops,'authenticate',authenticate)
    with pytest.raises(Refused,match='binding'): ops.settle_once()
    assert signals==[signal.SIGSTOP,signal.SIGCONT]

def test_selected_resumes_existing_attempt_through_production_entry(tmp_path,monkeypatch):
    from scripts import legal_integration_campaign as campaign
    from scripts import legal_integration_phased_live as live
    fixture(tmp_path,monkeypatch)
    (tmp_path/live.LIVE).mkdir(parents=True)
    called=[]
    service=SimpleNamespace(check=lambda:called.append('checked'))
    monkeypatch.setattr(campaign,'provider',lambda:service)
    monkeypatch.setattr(live,'answer',lambda q,t,s:called.append((q,t,s)) or {'legal_acceptance':False})
    def complete(execution,tid,action):
        called.append(tid)
        return action()
    monkeypatch.setattr(campaign,'complete_node',complete)
    execution=SimpleNamespace(summary=lambda:dict(ready=['tool-gatecoin-bm25'],running=['baseline-p14']))
    before=(tmp_path/ops.STATE).read_bytes()
    result=ops.run_selected(execution,'baseline-p14')
    assert result['disposition']=='EXECUTED_EXISTING_NODE'
    assert called==['checked','baseline-p14',('p14',None,service)]
    assert (tmp_path/ops.STATE).read_bytes()==before

def test_failed_selected_result_continues_independent_owners(tmp_path,monkeypatch):
    from scripts import legal_review_timeout_correction as timeout
    from scripts import legal_review_repair as repair
    fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(timeout,'verify_orphans',lambda *args:None)
    monkeypatch.setattr(ops,'MasterExecution',lambda *args:object())
    seen=[]
    def selected(execution,tid):
        seen.append(tid)
        return dict(task_id=tid,status='FAILED',legal_acceptance=False)
    monkeypatch.setattr(ops,'run_selected',selected)
    monkeypatch.setattr(repair,'live',lambda:seen.append('drain') or dict(execution='WORK_REMAINS'))
    monkeypatch.setattr(ops.subprocess,'call',lambda *args,**kwargs:0)
    ops.worker()
    assert seen==[*ops.SELECTED,'drain']
    assert read(tmp_path/ops.HERE/'finished.json')['integration_complete'] is False
