"""Replay repair restores only authenticated ordering, preserving failures."""
from copy import deepcopy
from types import SimpleNamespace
from contextlib import contextmanager
import json

import pytest

from legalmath.canonical import digest
from scripts import legal_integration_reboot_repair as repair
from scripts.legal_mission_execution import save


@pytest.fixture
def phase(tmp_path):
    original = {'records':[{'id':'a','text':'alpha'},{'id':'b','text':'beta'}],
        'verified_locator_bindings':[{'record_id':'a','index_hash':'i'},{'record_id':'b','index_hash':'i'}],
        'payload':{'conclusion':'preserved'},'question':'original'}
    schema = {'type':'object'}
    identity = lambda request, shape: digest({'request':request,'schema':shape})
    product = SimpleNamespace(prepare_calls=lambda calls: calls,
        dispatch=SimpleNamespace(request_identity=identity))
    save(tmp_path/'phases/reduction/phase.json',{'contract':{'calls':[{'key':'reduce-0','identity':identity(original,schema)}]}})
    save(tmp_path/'calls/reduce-0/request.json',original)
    save(tmp_path/'calls/reduce-0/schema.json',schema)
    current=deepcopy(original)
    current['records'].reverse()
    current['verified_locator_bindings'].reverse()
    calls=[{'key':'reduce-0','request':current,'schema':schema,'validate':lambda value:None}]
    return product,calls,original


def test_order_restoration_keeps_exact_original_contract_and_does_not_mutate_inputs(tmp_path,phase):
    product,calls,original=phase
    before=deepcopy(calls[0]['request'])
    result=repair.restored_calls(product,'reduction',calls,tmp_path)
    assert result[0]['request']==original
    assert calls[0]['request']==before


@pytest.mark.parametrize('mutation',['text','payload','question','schema','duplicate','missing','key'])
def test_semantic_or_population_changes_cannot_be_relabelled_as_ordering(tmp_path,phase,mutation):
    product,calls,original=phase
    request=calls[0]['request']
    if mutation=='text': request['records'][0]['text']='changed'
    elif mutation=='payload': request['payload']['conclusion']='changed'
    elif mutation=='question': request['question']='changed'
    elif mutation=='schema': calls[0]['schema']={'type':'string'}
    elif mutation=='duplicate': request['records'].append(deepcopy(request['records'][0]))
    elif mutation=='missing': request['records'].pop()
    else: calls[0]['key']='different'
    with pytest.raises(Exception):
        repair.restored_calls(product,'reduction',calls,tmp_path)


def test_unknown_future_phase_keeps_ordinary_contract(tmp_path,phase):
    product,calls,_=phase
    assert repair.restored_calls(product,'future',calls,tmp_path)==calls


@pytest.fixture
def response(tmp_path,monkeypatch):
    folder=tmp_path/'calls/reduce-0'
    actual={'support':[],'conclusion':'unchanged'}
    wire={'original_request':{'records':[]},'original_schema':{'type':'object'}}
    retained={'status':'VALIDATED','value':actual}
    event={'item':{'type':'agent_message','text':json.dumps(actual)}}
    save(folder/'result.json',retained)
    save(folder/'reference-binding.json',wire)
    save(folder/'request.json',wire['original_request'])
    save(folder/'schema.json',wire['original_schema'])
    save(folder/'wire-response.json',{'value':actual,'provenance':{'events_jsonl':json.dumps(event)}})
    monkeypatch.setattr(repair,'historical_request',lambda value,reviewed:value['original_request'])
    monkeypatch.setattr(repair.bounded_references,'resolve',lambda payload,wire,maximum_bytes:payload)
    outcome={'results':[{'key':'reduce-0','result':retained,'dispatch_result_hash':digest(retained)}]}
    return folder,outcome


def test_message_field_order_is_restored_without_changing_values(tmp_path,response):
    _,outcome=response
    restored=repair.hydrate_outcome(tmp_path,outcome)
    assert restored==outcome
    assert list(restored['results'][0]['result']['value'])==['support','conclusion']


@pytest.mark.parametrize('mutation',['result','message','decoded','ambiguous'])
def test_rehydration_refuses_changed_value_or_message(tmp_path,response,monkeypatch,mutation):
    folder,outcome=response
    if mutation=='result': outcome['results'][0]['result']['value']['conclusion']='changed'
    elif mutation=='decoded':
        monkeypatch.setattr(repair.bounded_references,'resolve',lambda *a,**kw:{'conclusion':'changed'})
    else:
        value=json.loads((folder/'wire-response.json').read_text())
        if mutation=='message':
            value['provenance']['events_jsonl']=json.dumps({'item':{'type':'agent_message','text':'{}'}})
        else: value['provenance']['events_jsonl']+='\n'+value['provenance']['events_jsonl']
        save(folder/'wire-response.json',value)
    with pytest.raises(Exception): repair.hydrate_outcome(tmp_path,outcome)


def test_other_products_keep_their_normal_execution(tmp_path,monkeypatch):
    calls=[]
    monkeypatch.setattr(repair,'ORIGINAL_EXECUTE',lambda product,name,rows,**kw:calls.append(name) or {'ok':True})
    assert repair.exact_execute(SimpleNamespace(directory=tmp_path),'independent',[])=={'ok':True}
    assert calls==['independent']


def failed_state():
    result={'path':'old-result.json','sha256':'old'}
    attempts=[{'number':i,'result':dict(result),'finished_at_utc':'earlier'} for i in range(1,15)]
    veto={'code':'E_INTEGRITY','reason':'Changed phase on resume','scope':['acquire-gatecoin','baseline-gatecoin']}
    return {'tasks':{'acquire-gatecoin':{'status':'FAILED','attempts':attempts,'result':result,
        'reason':'acquire-gatecoin failed: Changed phase on resume'},
        'acquire-p14':{'status':'FAILED','attempts':[{'number':11}]}},'continuation_vetoes':[veto],'events':[]}


def test_one_recovery_segment_preserves_all_attempts_and_original_terminal_result():
    state=failed_state()
    before=deepcopy(state)
    current=repair.project_recovery(state,{'review':'r'},{'diagnostic':'d'},{'pid':3},'now')
    assert state==before
    assert current['tasks']['acquire-p14']==state['tasks']['acquire-p14']
    old,new=state['tasks']['acquire-gatecoin'],current['tasks']['acquire-gatecoin']
    assert len(new['attempts'])==len(old['attempts'])==14
    assert new['attempts']==old['attempts']
    assert new['recovery_segments'][0]['prior_terminal_attempt']==old['attempts'][-1]
    assert current['continuation_vetoes']==[]
    assert current['resolved_continuation_vetoes'][0]['veto']==state['continuation_vetoes'][0]
    # Even a later terminal failure cannot authorize a second replay segment.
    new['status']='FAILED'
    new['reason']=old['reason']
    with pytest.raises(Exception,match='already used'):
        repair.project_recovery(current,{}, {},{'pid':4},'later')


@pytest.mark.parametrize('mutation',['running','different_failure','broader_veto','different_attempt'])
def test_recovery_refuses_unknown_state_or_other_owner_authority(mutation):
    state=failed_state()
    if mutation=='running': state['tasks']['acquire-p14']['status']='RUNNING'
    elif mutation=='different_failure': state['tasks']['acquire-gatecoin']['reason']='different'
    elif mutation=='broader_veto': state['continuation_vetoes'][0]['scope'].append('acquire-p14')
    else: state['tasks']['acquire-gatecoin']['attempts'].pop()
    with pytest.raises(Exception): repair.project_recovery(state,{}, {},{'pid':4},'now')


@pytest.mark.parametrize('circuit_open,settled,expected',[(True,True,[]),(False,False,[]),
    (False,True,['acquire-p10','acquire-evidence'])])
def test_only_original_service_deferrals_resume_after_actual_settlement(tmp_path,monkeypatch,circuit_open,settled,expected):
    monkeypatch.setattr(repair,'ROOT',tmp_path)
    monkeypatch.setattr(repair,'WORK',tmp_path/'repair')
    monkeypatch.setattr(repair,'REVIEW',tmp_path/'review.md')
    monkeypatch.setattr(repair.reboot,'BASE',tmp_path/'master')
    monkeypatch.setattr(repair.reboot,'WORK',tmp_path/'original')
    (tmp_path/'review.md').write_text('reviewed')
    save(tmp_path/'service/scope.json',{'scope':'shared'})
    scope=repair.ref(tmp_path,tmp_path/'service/scope.json')
    save(tmp_path/'master/current-binding.json',{'phase_service_scope':scope})
    save(tmp_path/'service/service-circuit.json',{'open':circuit_open})
    if settled: save(tmp_path/'original/pending-call-settled.json',{'settled':True})
    state={'tasks':{},'events':[]}
    for tid in ('acquire-p10','acquire-evidence'):
        state['tasks'][tid]={'status':'BLOCKED','dispatch_status':'NOT_DISPATCHED',
            'prerequisite_evidence':[scope],'attempts':[{'number':1}]}
        state['events'].append({'task_id':tid,'action':'PREREQUISITE_BLOCKED',
            'shared_scope':['provider-service'],'evidence':[scope]})
    @contextmanager
    def locked(): yield state
    execution=SimpleNamespace(locked=locked,state_path=tmp_path/'state.json')
    assert repair.release_deferrals(execution)==expected
    assert all(len(r['attempts'])==1 for r in state['tasks'].values())
    assert all(r['status']==('PENDING' if expected else 'BLOCKED') for r in state['tasks'].values())


def test_same_boot_uuid_allows_observed_wall_clock_change(tmp_path,monkeypatch):
    monkeypatch.setattr(repair.reboot,'WORK',tmp_path)
    old={'id':'same-boot','started_at_utc':'2026-10-20T01:53:52+00:00'}
    save(tmp_path/'authorization.json',{'boot':old})
    monkeypatch.setattr(repair,'ORIGINAL_BOOT_IDENTITY',lambda:{'id':'same-boot','started_at_utc':'2026-10-20T01:55:07+00:00'})
    assert repair.authenticated_boot()==old
    monkeypatch.setattr(repair,'ORIGINAL_BOOT_IDENTITY',lambda:{'id':'different-boot','started_at_utc':old['started_at_utc']})
    with pytest.raises(Exception,match='different boot'): repair.authenticated_boot()
