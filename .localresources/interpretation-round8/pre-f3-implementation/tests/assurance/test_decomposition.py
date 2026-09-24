from copy import deepcopy
import pytest
from legalmath.canonical import canonical,digest,loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.decomposition import (
    partition,merge_pieces,compact_request,validate_cross,apply_cross)
from legalmath.interpretation.assurance.engine import Assurance,AssuranceSettings
from legalmath.interpretation.assurance.transport import CompactProvider,transient_service_failure
from tests.search.support import FunctionProvider
from tests.search.test_formal import AT
from .support import packet,inventory


def source_packet():
    p=packet();p['units']=[{**deepcopy(p['units'][0]),'unit_id':'u'+str(i),'locator':'Actual original location '+str(i),
        'text':text,'span':{'retained':'metadata '+('x'*100)}} for i,text in enumerate([
            'The condition is necessary.', 'Unless an exception applies.', 'Definitions qualify that condition.'])]
    return p


def piece_inventory(p):
    inv={'claims':[],'units':[],'authorities':[],'uncertainties':[]}
    for i,u in enumerate(p['units']):
        claim=deepcopy(inventory()['claims'][0]);claim.update(claim_id='same.local.'+str(i),
            evidence=[{'unit_id':u['unit_id'],'quote':u['text']}])
        inv['claims'].append(claim);inv['units'].append({'unit_id':u['unit_id'],'disposition':'CLAIMS',
            'claim_ids':[claim['claim_id']],'rationale':'Exact piece text'})
    return inv


def respond(request):
    task=request.get('original_task',request['task']);p=request['source_packet']
    if task=='SOURCE_INVENTORY':return piece_inventory(p)
    if task=='INVENTORY_CROSS_CHECK':
        return {'checked_unit_ids':[u['unit_id'] for u in p['units']], 'issues':[], 'unresolved_questions':[]}
    pytest.fail('Unexpected task '+task)


def engine(root,tmp_path,provider,**config):
    return Assurance(tmp_path,provider,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,
                     AssuranceSettings(inventory_piece_characters=60,inventory_piece_units=2,output_repairs=0,**config))


def test_partition_preserves_exact_text_order_and_refuses_large_atomic_unit():
    p=source_packet();pieces=partition(p,60,2)
    assert [u for s in pieces for u in s['units']]==p['units']
    assert len(pieces)==2
    with pytest.raises(LegalMathError):partition(p,10,2)
    with pytest.raises(LegalMathError):partition(p,0,2)


def test_merge_namespaces_local_ids_and_rejects_missing_or_duplicate_coverage():
    p=source_packet();pieces=partition(p,60,2);parts=[(x,piece_inventory(x)) for x in pieces]
    merged=merge_pieces(p,parts)
    assert len(merged['claims'])==3 and len({c['claim_id'] for c in merged['claims']})==3
    with pytest.raises(LegalMathError):merge_pieces(p,parts[:1])
    with pytest.raises(LegalMathError):merge_pieces(p,parts+parts)


def test_two_readers_cover_all_pieces_before_full_source_checks(root,tmp_path):
    provider=FunctionProvider(respond);e=engine(root,tmp_path,provider)
    result=e._source_inventories(source_packet())
    assert set(result)=={'atomic-reader','qualification-reader'}
    assert len(provider.requests)==6
    for role in result:
        requests=[r for r in provider.requests if r['role']==role]
        assert [r['task'] for r in requests]==['SOURCE_INVENTORY','SOURCE_INVENTORY','INVENTORY_CROSS_CHECK']
        assert requests[-1]['source_packet']==source_packet()
        assert len(result[role]['units'])==3
        assert 'qualification-reader' not in canonical(requests[0]).decode() if role=='atomic-reader' else True
    plan=loads((tmp_path/'inventory-pieces/round-000/plan.json').read_bytes())
    assert plan['status']=='COMPLETE' and all(r['context_check'] for r in plan['roles'].values())


def test_cross_piece_qualification_cannot_disappear_when_assembled(root,tmp_path):
    p=source_packet();pieces=partition(p,60,2)
    assert [u['unit_id'] for u in pieces[0]['units']]==['u0','u1']
    assert [u['unit_id'] for u in pieces[1]['units']]==['u2']
    def adverse(request):
        value=respond(request)
        if request['task']=='INVENTORY_CROSS_CHECK':
            value['issues']=[{'issue_id':'remote.exception','evidence':[{'unit_id':'u2','quote':p['units'][2]['text']}],
                'affected_claim_ids':[request['inventory']['claims'][0]['claim_id']],
                'explanation':'The second piece qualifies the condition in the first.'}]
        return value
    result=engine(root,tmp_path,FunctionProvider(adverse))._source_inventories(p)
    assert all('The second piece qualifies the condition in the first.' in r['uncertainties'] for r in result.values())


@pytest.mark.parametrize('failed_task',['SOURCE_INVENTORY','INVENTORY_CROSS_CHECK'])
def test_missing_piece_or_context_check_never_becomes_a_complete_reader(root,tmp_path,failed_task):
    def failed(request):
        if request['task']==failed_task:raise LegalMathError('E_DEPENDENCY',details='Provider unavailable')
        return respond(request)
    e=engine(root,tmp_path,FunctionProvider(failed));result=e._source_inventories(source_packet())
    assert result=={}
    assert loads((tmp_path/'inventory-pieces/round-000/plan.json').read_bytes())['status']=='INCOMPLETE'


def test_inventory_budget_refuses_before_dispatch(root,tmp_path):
    e=engine(root,tmp_path,FunctionProvider(lambda r:pytest.fail('Cannot afford complete inventory')),total_model_calls=7)
    p=source_packet();p['units']*=3
    for i,u in enumerate(p['units']):p['units'][i]={**u,'unit_id':'x'+str(i)}
    assert e._source_inventories(p)=={}
    assert e.provider.calls==0


def test_compact_transport_preserves_source_text_and_retains_full_mapping(tmp_path):
    request={'task':'SOURCE_INVENTORY','source_packet':source_packet()};wire=compact_request(request)
    assert [(u['unit_id'],u['text']) for u in wire['source_packet']['units']]==[
        (u['unit_id'],u['text']) for u in request['source_packet']['units']]
    assert len(canonical(wire))<len(canonical(request)) and request['source_packet']['units'][0]['span'] is not None
    provider=FunctionProvider(respond);compact=CompactProvider(provider,tmp_path)
    from legalmath.interpretation.search.models import Settings
    answer=compact.complete(request,{},Settings())
    assert provider.requests==[wire]
    assert answer.provenance['original_request_hash']==digest(request)
    assert loads((tmp_path/'call-000/original-request.json').read_bytes())==request
    assert loads((tmp_path/'call-000/request.json').read_bytes())==wire


def test_transport_circuit_stops_futile_downstream_paid_requests(tmp_path):
    def fail(r):raise LegalMathError('E_DEPENDENCY',details='Overloaded')
    provider=FunctionProvider(fail);compact=CompactProvider(provider,tmp_path)
    from legalmath.interpretation.search.models import Settings
    for _ in range(2):
        with pytest.raises(LegalMathError):compact.complete({'task':'SOURCE_INVENTORY'}, {},Settings())
    assert len(provider.requests)==1 and len(list(tmp_path.glob('call-*')))==1


def test_cross_check_missing_units_invented_claims_and_false_quotes_rejected():
    p=source_packet();inv=piece_inventory(p)
    valid={'checked_unit_ids':['u0','u1','u2'],'issues':[],'unresolved_questions':[]}
    for defect in ('missing','claims','quote'):
        bad=deepcopy(valid)
        if defect=='missing':bad['checked_unit_ids'].pop()
        else:bad['issues']=[{'issue_id':'issue','evidence':[{'unit_id':'u1','quote':p['units'][1]['text'] if defect=='claims' else 'not present'}],
            'affected_claim_ids':['not.real'] if defect=='claims' else [],'explanation':'Incomplete link'}]
        with pytest.raises(LegalMathError):validate_cross(bad,p,inv)


def test_retry_distinguishes_availability_from_permanent_or_application_errors():
    for code,details in [('E_DEPENDENCY','Our servers are currently overloaded'),
                         ('E_RESOURCE_LIMIT','Codex call deadline')]:
        assert transient_service_failure(LegalMathError(code,details=details))
    for code,details in [('E_DEPENDENCY','Authentication failed'),
                         ('E_RESOURCE_LIMIT','Input byte cap'),
                         ('E_SCHEMA','Invalid JSON'),('E_AUTHORITY','Tool use')]:
        assert not transient_service_failure(LegalMathError(code,details=details))


@pytest.mark.parametrize('failed',[False,True])
def test_compact_piece_replay_reuses_verified_wire_reservation(tmp_path,failed):
    from legalmath.interpretation.assurance.journal import JournalProvider,RetainedProvider
    from legalmath.interpretation.assurance.monitor import save
    from legalmath.interpretation.search.providers import Allowance,CodexProvider,Completion
    from legalmath.interpretation.search.models import Settings
    from legalmath.canonical import raw_digest
    ledger=tmp_path/'allowance.json';allowance=Allowance(ledger,100)
    class Counted:
        provider_id='counted.fixture';live=True
        def __init__(self):self.calls=0
        def complete(self,request,schema,settings):
            self.calls+=1;slot=allowance.reserve(digest(request))
            if failed:raise LegalMathError('E_DEPENDENCY',details='Overloaded')
            return Completion(respond(request),{'allowance_slot':slot,'request_hash':digest(request)})
    counted=Counted();base=tmp_path/'investigation'
    journal=JournalProvider(CompactProvider(counted,tmp_path/'transport'),base/'calls')
    request={'task':'SOURCE_INVENTORY','source_packet':source_packet()};schema={'type':'object'}
    if failed:
        with pytest.raises(LegalMathError):journal.complete(request,schema,Settings())
    else:journal.complete(request,schema,Settings())
    save(base/'report.json',{'execution_complete':False})
    def manifest():
        save(base/'manifest.json',{'report_hash':digest({'execution_complete':False}),
            'files':{str(p.relative_to(base)):raw_digest(p.read_bytes()) for p in base.rglob('*.json') if p.name!='manifest.json'}})
    manifest();before=ledger.read_bytes()
    replay=RetainedProvider(counted,base,ledger)
    if failed:
        with pytest.raises(LegalMathError) as error:replay.complete(request,schema,Settings())
        assert error.value.details['retained_failure']['allowance_slot']==1
    else:
        answer=replay.complete(request,schema,Settings())
        assert answer.value==respond(request) and answer.provenance['new_live_invocation'] is False
    assert counted.calls==1 and ledger.read_bytes()==before
    if not failed:
        path=base/'calls/call-000/response.json';value=loads(path.read_bytes())
        value['provenance']['wire_request_hash']=digest({'forged':True});save(path,value);manifest()
        with pytest.raises(LegalMathError):RetainedProvider(counted,base,ledger)


def test_split_source_reaches_java_and_keeps_cross_piece_concern(root,tmp_path):
    from .test_integration import responder,settings,source
    doc=source();doc['data']=b'A distributor should not offer gifts.\nA discount of fees or charges is an exception.'
    ordinary=responder()
    def response(request):
        units=request['source_packet']['units'];task=request['task']
        if task=='SOURCE_INVENTORY':
            inv=inventory();unit=units[0];claim=inv['claims'][0]
            claim['evidence']=[{'unit_id':unit['unit_id'],'quote':unit['text']}]
            claim['exceptions']=[];claim['statement']=unit['text']
            if 'exception' in unit['text']:
                claim.update(kind='EXCEPTION',modality='MAY',action='offer a discount of fees or charges')
            inv['units'][0]['unit_id']=unit['unit_id'];return inv
        if task=='INVENTORY_CROSS_CHECK':
            return {'checked_unit_ids':[u['unit_id'] for u in units],
                'issues':[{'issue_id':'cross.exception','evidence':[{'unit_id':units[1]['unit_id'],'quote':units[1]['text']}],
                'affected_claim_ids':[request['inventory']['claims'][0]['claim_id']],
                'explanation':'Check the exception in the second piece before applying the first.'}], 'unresolved_questions':[]}
        value=ordinary(request)
        if task=='GENERATE':
            value['readings'][0]['citations']=[{'unit_id':u['unit_id'],'quote':u['text']} for u in units]
            value['readings'][0]['formalization']['facts'][1]['source_unit_ids']=[units[1]['unit_id']]
            value['coverage']=[{'unit_id':u['unit_id'],'status':'INTERPRETED','reason':'Scripted selected rule and exception'} for u in units]
        return value
    provider=FunctionProvider(response)
    config=settings().model_copy(update={'inventory_piece_characters':2300,'inventory_piece_units':1})
    result=Assurance(tmp_path/'run',CompactProvider(provider,tmp_path/'transport'),
        root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,config).drive([doc],'Gift rule with a remote fee-discount exception')
    assert result['status']=='UNRESOLVED' and result['execution_complete'],result
    assert result['candidate_ids'] and not result['release_eligible']
    assert any(f['kind']=='INVENTORY_UNCERTAINTY' and 'second piece' in f['details'] for f in result['findings'])
    assert list((tmp_path/'run/java').rglob('*.jar')) and len(provider.requests)==11
    state=loads((tmp_path/'run/search-state.json').read_bytes())
    assert state['java_checks']
    assert all(c['result']['status']=='JAVA_PYTHON_CONFORMANCE' for c in state['java_checks'])


def test_fidelity_piece_keeps_full_source_and_only_required_claims_and_candidates():
    from .support import reading
    from legalmath.interpretation.assurance.semantics import fidelity_request
    claims=piece_inventory(source_packet())['claims'];candidates={'one':reading(),'two':reading(True)}
    pairs=[(claims[0]['claim_id'],'one')]
    request=fidelity_request(source_packet(),claims,candidates,pairs)
    assert request['source_packet']==source_packet()
    assert request['claims']==claims[:1]
    assert [c['candidate_id'] for c in request['candidates']]==['one']
    assert request['required_pairs']==[{'claim_id':claims[0]['claim_id'],'candidate_id':'one'}]
    for bad in ([],pairs+pairs,[('missing','one')],[(claims[0]['claim_id'],'missing')]):
        with pytest.raises(LegalMathError):fidelity_request(source_packet(),claims,candidates,bad)
