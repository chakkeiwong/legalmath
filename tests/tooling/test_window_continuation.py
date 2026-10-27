from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import pytest
from scripts import legal_window_continuation as amendment
from scripts.legal_mission_execution import save, ref, digest, Refused
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.time_authority import effective_deadline
from tests.assurance.test_time_authority import fixture, extend_fixture

def renewed_fixture(root):
    grant,ledger,extension,bind,store=fixture(root)
    prior,binding=extend_fixture(store,extension,bind(extension))
    previous_extension=store('second-extension.json',prior)
    prior_program=store('second-program.json',dict(deadline_utc=prior['deadline_utc'],time_continuation={'time_extension':previous_extension}))
    prior_binding=store('second-binding.json',dict(binding,program=prior_program,time_extension=previous_extension))
    approved=datetime.now(timezone.utc)-timedelta(seconds=1)
    deadline=(approved+timedelta(hours=72)).isoformat()
    authority=dict(user_instruction=amendment.USER,approved_at_utc=approved.isoformat(),duration_seconds=259200,deadline_utc=deadline,calls_added=0,replacements_added=0)
    value=dict(prior,profile='integration-time-extension.v3',user_instruction=amendment.USER,
        approved_at_utc=approved.isoformat(),deadline_utc=deadline,previous_extension=previous_extension,
        prior_program=prior_program,prior_binding=prior_binding,previous_deadline_utc=prior['deadline_utc'],
        authorization=store('authority.json',authority))
    current=dict(binding,effective_deadline_utc=deadline)
    def publish():
        current['time_extension']=store('third-extension.json',value)
        current['program']=store('third-program.json',dict(deadline_utc=value['deadline_utc'],window_continuation={'time_extension':current['time_extension']}))
        store('current-binding.json',current)
    publish()
    return value,current,ledger,store,publish

def test_renewed_window_preserves_grant_calls_and_prior_extensions(tmp_path):
    value,current,ledger,store,publish=renewed_fixture(tmp_path)
    original=(tmp_path/'live-grant.json').read_bytes()
    assert effective_deadline(tmp_path,tmp_path)==value['deadline_utc']
    assert (tmp_path/'live-grant.json').read_bytes()==original
    assert json.loads((tmp_path/'live-calls.json').read_text())==ledger

@pytest.mark.parametrize('mutation',['instruction','duration','deadline','charges','authority','previous','program','review'])
def test_renewed_window_rejects_authority_changes(tmp_path,mutation):
    value,current,ledger,store,publish=renewed_fixture(tmp_path)
    if mutation=='instruction': value['user_instruction']='continue'
    elif mutation=='duration': value['duration_seconds']+=1
    elif mutation=='deadline': value['deadline_utc']='2030-01-01T00:00:00+00:00'
    elif mutation=='charges': store('live-calls.json',dict(ledger,calls=[]))
    elif mutation=='authority': value['authorization']=store('authority.json',{'approved':True})
    elif mutation=='previous': value['previous_extension']=store('invalid-previous.json',{'profile':'unknown'})
    elif mutation=='review': current['review']=store('foreign-review.json',{})
    publish()
    if mutation=='program':
        current['program']=store('third-program.json',{'deadline_utc':value['deadline_utc']})
        store('current-binding.json',current)
    with pytest.raises(LegalMathError): effective_deadline(tmp_path,tmp_path)

def state_fixture(tmp_path):
    before=dict(tasks={'baseline-p14':dict(status='FAILED',attempts=[{'number':i,'result':{'path':str(i)}} for i in range(1,6)]),
        'baseline-gatecoin':dict(status='RUNNING',attempts=[{'number':4}]),
        'complete':dict(status='SUCCEEDED',attempts=[{'number':1,'result':{'path':'complete'}}])},
        events=[{'action':'old'}],continuation_vetoes=[{'scope':['blocked']}])
    save(tmp_path/'before.json',before)
    program={amendment.KEY:{'prior_state':ref(tmp_path,'before.json'),'review':{'path':'plan'}},'review_repair':{}}
    return before,program

def test_reopen_only_interrupted_owner_and_keep_all_attempts(tmp_path,monkeypatch):
    from scripts import legal_review_repair
    monkeypatch.setattr(legal_review_repair,'validate_state_history',lambda *args:None)
    before,program=state_fixture(tmp_path)
    state=amendment.project_state(before,program)
    assert state['tasks']['baseline-p14']['status']=='PENDING'
    assert state['tasks']['baseline-p14']['attempts']==before['tasks']['baseline-p14']['attempts']
    assert state['tasks']['baseline-gatecoin']==before['tasks']['baseline-gatecoin']
    amendment.validate_state_history(program,state,tmp_path)

@pytest.mark.parametrize('mutation',['attempt','success','events','veto'])
def test_reject_history_loss(tmp_path,monkeypatch,mutation):
    from scripts import legal_review_repair
    monkeypatch.setattr(legal_review_repair,'validate_state_history',lambda *args:None)
    before,program=state_fixture(tmp_path);state=amendment.project_state(before,program)
    if mutation=='attempt': state['tasks']['baseline-p14']['attempts'].pop()
    elif mutation=='success': state['tasks']['complete']['status']='PENDING'
    elif mutation=='events': state['events'].pop(0)
    else: state['continuation_vetoes']=[]
    with pytest.raises(Refused): amendment.validate_state_history(program,state,tmp_path)

def test_runtime_uses_successor_without_changing_historical_runtime():
    from scripts.legal_integration_phased_live import active_live
    program={'window_continuation':{'runtime':str(amendment.RUNTIME)},'review_repair':{'optional_quote_validation':{'runtime':str(amendment.SOURCE)}}}
    assert active_live(program)==amendment.RUNTIME
    assert active_live({'review_repair':program['review_repair']})==amendment.SOURCE
