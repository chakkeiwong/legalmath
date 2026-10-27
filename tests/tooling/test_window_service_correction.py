from copy import deepcopy
from pathlib import Path
import importlib.util
import json
import os
import fcntl
import pytest
from scripts import legal_window_service_correction as correction
from scripts.legal_mission_execution import save, ref, Refused
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_provider import CampaignAllowance

def test_lock_owner_matches_only_the_process_holding_the_exact_file(tmp_path):
    path=tmp_path/'mission.lock'
    with path.open('a') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert correction.lock_owner(path,os.getpid())
        assert not correction.lock_owner(path,os.getpid()+100000)
    assert not correction.lock_owner(path,os.getpid())

def fixture(root):
    review={'path':'review.md','sha256':'old-review'}
    save(root/'scope.json',dict(grant_hash='grant',review=review))
    scope=ref(root,'scope.json')
    old=dict(review=review,grant_hash='grant',phase_service_scope=scope)
    save(root/'prior.json',old);prior=ref(root,'prior.json')
    current=dict(old,review={'path':'window.md','sha256':'window-review'},predecessor=prior,
        window_continuation={'prior_binding':prior})
    save(root/'current-binding.json',current)
    save(root/'stage.json',dict(grant_hash='grant',service_scope=scope))
    save(root/'current-stage.json',ref(root,'stage.json'))
    return current,CampaignAllowance(root,{},root=root)

def test_reproduces_failure_and_corrects_supported_inheritance(tmp_path):
    binding,allowance=fixture(tmp_path)
    with pytest.raises(LegalMathError) as caught:
        allowance.service_scope()
    assert caught.value.code=='E_AUTHORITY' and caught.value.details==correction.REASON
    fixed=correction.corrected_binding(binding)
    assert set(fixed)==set(binding)|{'phase_service_predecessor'}
    assert all(fixed[k]==v for k,v in binding.items())
    save(tmp_path/'current-binding.json',fixed)
    assert allowance.service_scope()[0]==binding['phase_service_scope']

@pytest.mark.parametrize('mutation',['grant','scope','predecessor','bytes'])
def test_inheritance_still_rejects_changed_authority(tmp_path,mutation):
    binding,allowance=fixture(tmp_path);fixed=correction.corrected_binding(binding)
    if mutation=='grant':fixed['grant_hash']='foreign'
    elif mutation=='scope':fixed['phase_service_scope']={'path':'scope.json','sha256':'wrong'}
    elif mutation=='predecessor':fixed['predecessor']={'path':'foreign.json','sha256':'wrong'}
    else:save(tmp_path/'prior.json',{})
    save(tmp_path/'current-binding.json',fixed)
    with pytest.raises(LegalMathError):allowance.service_scope()

@pytest.mark.parametrize('mutation',['missing','wrong','already_set'])
def test_correction_refuses_unreviewed_binding(tmp_path,mutation):
    binding,_=fixture(tmp_path)
    if mutation=='missing':binding.pop('predecessor')
    elif mutation=='wrong':binding['predecessor']={'path':'wrong','sha256':'wrong'}
    else:binding['phase_service_predecessor']=binding['predecessor']
    with pytest.raises(Refused):correction.corrected_binding(binding)

def state_fixture(root):
    veto=dict(code='E_AUTHORITY',reason=correction.REASON,scope=['baseline-p14','acquire-p10'],evidence=[])
    before=dict(tasks={
        'baseline-p14':dict(status='FAILED',attempts=[{'number':i,'result':{'path':str(i)}} for i in range(1,7)]),
        'baseline-gatecoin':dict(status='RUNNING',attempts=[{'number':4}]),
        'acquire-p10':dict(status='PENDING',attempts=[{'number':13}]),
        'corpus':dict(status='BLOCKED',attempts=[{'number':6}]),
        'done':dict(status='SUCCEEDED',attempts=[{'number':1}])},
        events=[{'action':'old'}],continuation_vetoes=[veto,{'code':'E_INTEGRITY','reason':'unrelated','scope':['corpus']}],
        resolved_continuation_vetoes=[{'veto':'older'}])
    save(root/'before.json',before)
    c=dict(prior_state=ref(root,'before.json'),resolved_vetoes=[veto],attempt_additions={'baseline-p14':1},
        result={'path':'tests'},review={'path':'review'})
    program={'window_continuation':{correction.KEY:c}}
    return before,program

def test_preserves_attempts_and_independent_owners(tmp_path,monkeypatch):
    from scripts import legal_window_continuation
    monkeypatch.setattr(legal_window_continuation,'validate_state_history',lambda *args:None)
    before,program=state_fixture(tmp_path);after=correction.project_state(before,program,'now')
    correction.validate_history(program,after,tmp_path)
    assert after['tasks']['baseline-p14']['status']=='PENDING'
    assert after['tasks']['baseline-p14']['attempts']==before['tasks']['baseline-p14']['attempts']
    assert all(after['tasks'][k]==v for k,v in before['tasks'].items() if k!='baseline-p14')
    assert after['continuation_vetoes']==before['continuation_vetoes'][1:]

@pytest.mark.parametrize('mutation',['attempt','success','events','foreign_veto','resolution','reopen'])
def test_history_validation_rejects_unrelated_changes(tmp_path,monkeypatch,mutation):
    from scripts import legal_window_continuation
    monkeypatch.setattr(legal_window_continuation,'validate_state_history',lambda *args:None)
    before,program=state_fixture(tmp_path);after=correction.project_state(before,program,'now')
    if mutation=='attempt':after['tasks']['baseline-p14']['attempts'].pop()
    elif mutation=='success':after['tasks']['done']['status']='PENDING'
    elif mutation=='events':after['events'].pop(0)
    elif mutation=='foreign_veto':after['continuation_vetoes']=[]
    elif mutation=='resolution':after['resolved_continuation_vetoes'].pop()
    else:after['tasks']['corpus']['status']='PENDING'
    with pytest.raises(Refused):correction.validate_history(program,after,tmp_path)

def test_candidate_runtime_and_worker_directory():
    path=correction.ROOT/correction.WORK/'candidate/scripts/legal_integration_phased_live.py'
    if not path.exists():pytest.skip('candidate not staged')
    spec=importlib.util.spec_from_file_location('window_service_candidate',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    program={'window_continuation':{'runtime':'old',correction.KEY:{'runtime':'new'}}}
    assert module.active_live(program)==Path('new')
    assert module.active_live({'window_continuation':{'runtime':'old'}})==Path('old')
    source=(correction.ROOT/correction.WORK/'candidate/scripts/legal_window_continuation.py').read_text()
    worker=source[source.index('def worker():'):source.index('def arm():')]
    assert 'ROOT/WORK/' not in worker
    assert "phase_service_predecessor=revision['prior_binding']" in source
    assert "Shared authority veto; no further live owners" in worker

def test_reopens_only_other_owners_failed_by_same_shared_defect(tmp_path,monkeypatch):
    from scripts import legal_window_continuation
    monkeypatch.setattr(legal_window_continuation,'validate_state_history',lambda *args:None)
    before,program=state_fixture(tmp_path)
    before['tasks']['baseline-gatecoin']=dict(status='FAILED',attempts=[{'number':i} for i in range(1,5)])
    extra=dict(code='E_AUTHORITY',reason=correction.REASON,scope=['baseline-gatecoin'],evidence=[])
    before['continuation_vetoes'].append(extra);save(tmp_path/'before.json',before)
    c=program['window_continuation'][correction.KEY]
    c.update(prior_state=ref(tmp_path,'before.json'),resolved_vetoes=[before['continuation_vetoes'][0],extra],
        attempt_additions={'baseline-p14':1,'baseline-gatecoin':1})
    after=correction.project_state(before,program,'now')
    correction.validate_history(program,after,tmp_path)
    assert after['tasks']['baseline-gatecoin']['status']=='PENDING'
    assert len(after['tasks']['baseline-gatecoin']['attempts'])==4
    assert after['tasks']['acquire-p10']==before['tasks']['acquire-p10']
