from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest

from legalmath.canonical import canonical, digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search import providers
from scripts import legal_review_timeout_correction as correction
from scripts.legal_review_repair_service import terminal_receipt
from scripts.legal_mission_execution import read, save, ref, Refused
from tests.assurance.test_review_repair_budget_service import migrated
from tests.assurance import test_delayed_service_recovery as delayed


def message(text):
    return {'type':'item.completed','item':{'id':'item_1','type':'agent_message','text':text}}


def amend_events(root, failure, additional):
    folder=root/'provider-evidence'/f'{failure.allowance_slot:04}-{failure.request_hash[:16]}'
    manifest=read(folder/'manifest.json')
    events=[json.loads(line) for line in (folder/'events.jsonl').read_text().splitlines() if line.strip()]
    data=b'\n'.join(canonical(e) for e in events+additional)
    (folder/'events.jsonl').write_bytes(data)
    manifest['files']['events.jsonl']['retained_sha256']=hashlib.sha256(data).hexdigest()
    save(folder/'manifest.json',manifest)
    return folder


@pytest.mark.parametrize('blank',['',' ','\n\t  '])
def test_ended_blank_message_gets_exact_counted_recovery(tmp_path,monkeypatch,blank):
    allowance,_,prior=migrated(tmp_path,monkeypatch)
    monkeypatch.setattr(delayed,'REQUEST',{'question':'new exact failed request'})
    allowance.expected=digest(delayed.REQUEST)
    ended=delayed.failure(tmp_path,25,timeout=True)
    amend_events(tmp_path,ended,[message(blank),{'type':'item.completed','item':{'type':'reasoning','text':'thinking'}}])
    request,schema,failure,_=terminal_receipt(tmp_path,'',25,ended.request_hash)
    assert isinstance(failure,providers.TerminatedCallTimeout)
    assert (request,schema)==(delayed.REQUEST,delayed.SCHEMA)
    assert allowance.reserve_service_recovery(failure)==300
    charges=read(tmp_path/'stage/service-recovery.json')['charges']
    assert len(charges)==25 and charges[:24]==prior['charges']
    with pytest.raises(LegalMathError): allowance.reserve_service_recovery(failure)


@pytest.mark.parametrize('event',[
    message('partial answer'),message('I cannot comply'),message(None),message(1),
    {'type':'item.completed','item':{'type':'agent_message'}},
    {'type':'item.completed','item':{'type':'agent_message','text':' ','refusal':'blocked'}},
    {'type':'item.completed','item':{'type':'refusal','text':'no'}},
    {'type':'item.completed','item':None}, {'type':'item.completed'},
    {'type':'unknown.event'}, {'type':None}, None,
    {'type':'item.completed','item':{'type':'error','message':'401 unauthorized'}},
    {'type':'turn.completed'},
])
def test_output_ambiguity_and_completed_turn_never_get_replacements(tmp_path,monkeypatch,event):
    allowance,_,prior=migrated(tmp_path,monkeypatch)
    ended=delayed.failure(tmp_path,25,timeout=True)
    amend_events(tmp_path,ended,[event])
    with pytest.raises((LegalMathError,Refused)):
        terminal_receipt(tmp_path,'',25,ended.request_hash)
    with pytest.raises(LegalMathError): allowance.reserve_service_recovery(ended)
    assert read(tmp_path/'stage/service-recovery.json')['charges']==prior['charges']


@pytest.mark.parametrize('problem',['auth','billing','refusal','mixed_unknown','completed_file','unproved_end','tampered'])
def test_blank_message_cannot_hide_other_failure(tmp_path,monkeypatch,problem):
    allowance,_,_=migrated(tmp_path,monkeypatch)
    ended=delayed.failure(tmp_path,25,timeout=True)
    extras=[message(' ')]
    errors={'auth':'401 unauthorized','billing':'429 insufficient_quota','refusal':'invalid_request: cannot comply',
        'mixed_unknown':'unknown provider error'}
    if problem in errors:
        extras += [{'type':'error','message':errors[problem]}]
        if problem=='mixed_unknown': extras += [{'type':'error','message':'HTTP 503 Service Unavailable'}]
    folder=amend_events(tmp_path,ended,extras)
    if problem=='completed_file': (folder/'result.json').write_text('{}')
    if problem=='tampered': (folder/'events.jsonl').write_text('{}')
    if problem=='unproved_end':
        manifest=read(folder/'manifest.json')
        termination=read(folder/'termination.json');termination['process_terminated']=False
        save(folder/'termination.json',termination)
        manifest['files']['termination.json']['retained_sha256']=ref(tmp_path,folder/'termination.json')['sha256']
        save(folder/'manifest.json',manifest)
    with pytest.raises((LegalMathError,Refused)): terminal_receipt(tmp_path,'',25,ended.request_hash)
    with pytest.raises(LegalMathError): allowance.reserve_service_recovery(ended)


def test_blank_plain_timeout_and_499_are_opt_in():
    from tests.assurance.test_service_continuation import events
    for detail in ('request timed out','HTTP status 499'):
        items=events(detail)+[message(' ')]
        assert providers.transient_service_details(items,output_present=False,allow_terminal_499=True) is None
        assert providers.transient_service_details(items,output_present=False,
            allow_terminal_499=True,allow_terminal_timeout=True)
    assert providers.transient_service_details(events('503 Service Unavailable')+[message('partial')],
        output_present=False,allow_terminal_timeout=True) is None


def test_historical_delayed_profile_does_not_gain_blank_retry(tmp_path,monkeypatch):
    allowance,_=delayed.setup(tmp_path,monkeypatch)
    ended=delayed.failure(tmp_path,1,timeout=True)
    amend_events(tmp_path,ended,[message(' ')])
    with pytest.raises(LegalMathError): allowance.reserve_service_recovery(ended)


def test_actual_slot_3591_is_authenticated_empty_timeout():
    result=correction.exact_failure(correction.ROOT)
    assert result['slot']==3591 and result['provider_calls']==0 and not result['legal_acceptance']


@pytest.mark.parametrize('problem',['live','missing_identity','uncertain'])
def test_retained_reservation_does_not_bypass_active_or_uncertain_dispatch(tmp_path,monkeypatch,problem):
    import scripts.legal_mission_execution as execution
    state={'tasks':{'a':{'status':'RUNNING','master_live':True,'live_supervisor':{'pid':123,'start':'456'}}}}
    monkeypatch.setattr(execution,'process_alive',lambda _:problem=='live')
    if problem=='missing_identity': state['tasks']['a'].pop('live_supervisor')
    if problem=='uncertain': save(tmp_path/'runtime/a/calls/dispatch.json',{'calls':{'x':{'status':'RESERVED'}}})
    with pytest.raises(Refused): correction.verify_orphans(tmp_path,state,tmp_path/'runtime')


def test_ended_reservation_can_recover_without_new_attempt(tmp_path,monkeypatch):
    import scripts.legal_mission_execution as execution
    state={'tasks':{'a':{'status':'RUNNING','master_live':True,'live_supervisor':{'pid':123,'start':'456'},'attempts':[{}]}}}
    monkeypatch.setattr(execution,'process_alive',lambda _:False)
    before=deepcopy(state)
    correction.verify_orphans(tmp_path,state,tmp_path/'runtime')
    assert state==before


def test_shared_deferral_yields_to_recovery_instead_of_looping(monkeypatch):
    from scripts import legal_integration_phased_live as live
    from types import SimpleNamespace
    owner=SimpleNamespace(program={'review_repair':{'timeout_correction':True}},
        summary=lambda:{'ready':[],'running':['baseline-gatecoin']})
    calls=[]
    monkeypatch.setattr(live,'defer_open_service',lambda *_:calls.append('defer') or True)
    campaign=SimpleNamespace(complete_node=lambda *_:pytest.fail('No dispatch before recovery'))
    live.drain_answers(owner,campaign,None)
    assert calls==['defer']


def test_only_exact_veto_is_resolved_and_attempts_preserved(tmp_path):
    known={'code':'E_AUTHORITY','reason':correction.REASON,'evidence':[],'scope':['baseline-p14']}
    other={'code':'E_INTEGRITY','reason':'unrelated','evidence':[],'scope':['other']}
    before={'events':[{'original':True}],'continuation_vetoes':[known,other],'tasks':{
        'baseline-p14':{'status':'FAILED','attempts':[{'number':i,'result':{'old':i}} for i in range(1,4)],'result':{}},
        'baseline-gatecoin':{'status':'RUNNING','attempts':[{'number':i} for i in range(1,5)]},
        'done':{'status':'SUCCEEDED','attempts':[{'number':1,'result':{}}]}}}
    save(tmp_path/'before.json',before)
    spec={'review':{'review':True},'result':{'result':True},'prior_state':ref(tmp_path,'before.json')}
    program={'review_repair':{'timeout_correction':spec}}
    state=correction.project_state(before,program,'now')
    correction.validate_history(program,state,tmp_path)
    assert state['tasks']['baseline-p14']['attempts']==before['tasks']['baseline-p14']['attempts']
    assert state['tasks']['baseline-gatecoin']==before['tasks']['baseline-gatecoin']
    assert state['continuation_vetoes']==[other]
    assert state['resolved_continuation_vetoes'][0]['veto']==known
    state['continuation_vetoes']=[]
    with pytest.raises(Refused): correction.validate_history(program,state,tmp_path)


@pytest.mark.parametrize('problem',['child','reserved','identity','live_orphan','half_open'])
def test_handover_refuses_uncertain_process_without_signalling(tmp_path,monkeypatch,problem):
    import scripts.legal_mission_execution as execution
    owner={'pid':987654,'start':'123'}
    save(tmp_path/correction.WORK/'worker.json',{'process':owner})
    save(tmp_path/correction.STATE,{'tasks':{
        'baseline-p14':{'status':'FAILED','attempts':[{}]*3},
        'baseline-gatecoin':{'status':'RUNNING','attempts':[{}]*4,'master_live':True,
            'live_supervisor':{'pid':111,'start':'222'}}}})
    (tmp_path/correction.DOC).mkdir(parents=True,exist_ok=True)
    save(tmp_path/correction.WORK/'service/service-circuit.json',
        {'open':True,'failed_slots':[3591],'half_open_reserved':problem=='half_open'})
    save(tmp_path/correction.SOURCE/'arms/p14/baseline/calls/dispatch.json',
        {'calls':{'one':{'status':'RESERVED' if problem=='reserved' else 'FAILED'}}})
    monkeypatch.setattr(execution,'process_identity',lambda _:None if problem=='identity' else owner)
    monkeypatch.setattr(execution,'process_alive',lambda _:problem=='live_orphan')
    original=Path.read_text
    monkeypatch.setattr(Path,'read_text',lambda path,*a,**k:
        'child' if str(path).startswith('/proc/') else original(path,*a,**k))
    signals=[]
    monkeypatch.setattr(correction.os,'kill',lambda *a:signals.append(a))
    if problem=='child': assert not correction.settle_once(tmp_path,expected=owner)['settled']
    else:
        with pytest.raises(Refused): correction.settle_once(tmp_path,expected=owner)
    assert signals==[]


def test_nested_predecessor_validation_preserves_existing_ledger_archive(tmp_path):
    from scripts.legal_mission_execution import historical_evidence,verify
    path=str(correction.WORK/'service/service-recovery.json')
    for destination in ('old.json','new.json'):
        save(tmp_path/destination,{'charges':[1,2,3]})
    previous={'path':path,'sha256':ref(tmp_path,'old.json')['sha256']}
    old={(path,previous['sha256']):ref(tmp_path,'old.json')}
    latest=[{'previous':previous,'archive':ref(tmp_path,'new.json')}]
    with historical_evidence(tmp_path,correction.mapped(latest)):
        with historical_evidence(tmp_path,old):
            verify(tmp_path,previous)
