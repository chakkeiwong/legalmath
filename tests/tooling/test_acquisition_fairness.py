from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts import legal_integration_phased_live as live


def test_ready_acquisition_precedes_answer_drain(monkeypatch):
    execution=SimpleNamespace(summary=lambda:dict(ready=['baseline-p14','acquire-p10'],running=[]))
    campaign=SimpleNamespace(complete_node=lambda *a:pytest.fail('Starved acquisition'))
    live.drain_answers(execution,campaign,object(),maximum_nodes=1,yield_to_acquisitions=True)


def test_bounded_answer_turn_then_independent_work(monkeypatch):
    queue=['baseline-p14','tool-gatecoin-bm25']
    execution=SimpleNamespace(summary=lambda:dict(ready=list(queue),running=[]))
    seen=[]
    def complete(execution,tid,action):
        seen.append(tid);queue.remove(tid)
        return {'failed':tid=='baseline-p14'}
    monkeypatch.setattr(live,'defer_open_service',lambda *a:False)
    campaign=SimpleNamespace(complete_node=complete)
    live.drain_answers(execution,campaign,object(),maximum_nodes=1)
    assert seen==['baseline-p14'] and queue==['tool-gatecoin-bm25']
    live.drain_answers(execution,campaign,object())
    assert seen==['baseline-p14','tool-gatecoin-bm25']


@pytest.mark.parametrize('fairness',[True,False])
def test_actual_live_loop_orders_independent_acquisitions(tmp_path,monkeypatch,fairness):
    program={'settled_recovery':{'recoveries':{}},
        'repair_execution':{'recoveries':{q:{'path':q+'.json'} for q in ('p14','gatecoin','p10','evidence')}}}
    if fairness:program[live.FAIRNESS_FIELD]=live.FAIRNESS_PROFILE
    pending=['acquire-p10','acquire-evidence','tool-gatecoin-bm25']
    execution=SimpleNamespace(program=program,summary=lambda:dict(ready=list(pending),running=[]))
    seen=[]
    def complete(owner,tid,action):
        seen.append(tid);pending.remove(tid)
        return {'failed':tid=='acquire-p10'}
    campaign=SimpleNamespace(provider=lambda:SimpleNamespace(check=lambda:None),complete_node=complete)
    monkeypatch.setattr(live,'ROOT',tmp_path)
    monkeypatch.setattr(live,'LIVE',Path('runtime'))
    monkeypatch.setattr(live,'configure',lambda *a:campaign)
    monkeypatch.setattr(live,'MasterExecution',lambda *a:execution)
    monkeypatch.setattr(live,'defer_open_service',lambda *a:False)
    def read(path):
        if path==tmp_path/live.PROGRAM:return program
        return {'account_recovery':{'roots':[]}}
    monkeypatch.setattr(live,'read',read)
    result=live.live()
    assert not result['ready']
    expected=['acquire-p10','acquire-evidence','tool-gatecoin-bm25'] if fairness else [
        'acquire-p10','tool-gatecoin-bm25','acquire-evidence']
    assert seen==expected


def test_service_deferral_does_not_spend_another_turn(monkeypatch):
    execution=SimpleNamespace(summary=lambda:dict(ready=['baseline-p14'],running=[]))
    seen=[]
    monkeypatch.setattr(live,'defer_open_service',lambda *a:False)
    def complete(owner,tid,action):
        seen.append(tid);return {'service_deferred':True}
    live.drain_answers(execution,SimpleNamespace(complete_node=complete),object(),maximum_nodes=2)
    assert seen==['baseline-p14']
