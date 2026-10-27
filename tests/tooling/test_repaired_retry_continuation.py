from copy import deepcopy
from pathlib import Path
import pytest
from scripts import legal_repaired_retry_continuation as module
from scripts.legal_mission_execution import Refused,save,ref,digest

def baseline():
    return dict(tasks={k:dict(status='FAILED',attempts=[{'n':i} for i in range(n)],result={'old':True})
        for k,n in module.ATTEMPTS.items()},events=[],continuation_vetoes=[])

def test_reopening_retains_attempts_and_only_changes_two_owners():
    before=baseline();before['tasks']['succeeded']=dict(status='SUCCEEDED',attempts=[{'result':'kept'}])
    p={module.KEY:{'review':{'path':'review','sha256':'hash'}}}
    after=module.project_state(before,p,'now')
    for tid in module.ATTEMPTS:
        assert after['tasks'][tid]['attempts']==before['tasks'][tid]['attempts']
        assert after['tasks'][tid]['status']=='PENDING'
    assert after['tasks']['succeeded']==before['tasks']['succeeded']
    assert before['tasks']['baseline-p14']['status']=='FAILED'

def test_reopening_a_success_is_refused():
    before=baseline();before['tasks']['baseline-p14']['status']='SUCCEEDED'
    with pytest.raises(Refused):module.project_state(before,{module.KEY:{'review':{}}},'now')

def test_history_rejects_lost_attempts_and_success_mutation(tmp_path,monkeypatch):
    from scripts import legal_baseline_corpus_deployment
    monkeypatch.setattr(legal_baseline_corpus_deployment,'validate_history',lambda *a:None)
    before=baseline();before['tasks']['success']=dict(status='SUCCEEDED',attempts=[{'n':1}])
    save(tmp_path/'before.json',before);save(tmp_path/'program.json',{});save(tmp_path/'baseline.json',dict(changed_paths=[],archived=[]))
    revision=dict(prior_state=ref(tmp_path,'before.json'),prior_program=ref(tmp_path,'program.json'),
        baseline=ref(tmp_path,'baseline.json'))
    program={module.KEY:revision};current=deepcopy(before)
    module.validate_history(program,current,tmp_path)
    current['tasks']['success']['reason']='changed'
    with pytest.raises(Refused):module.validate_history(program,current,tmp_path)
    current=deepcopy(before);current['tasks']['baseline-p14']['attempts'].pop()
    with pytest.raises(Refused):module.validate_history(program,current,tmp_path)
