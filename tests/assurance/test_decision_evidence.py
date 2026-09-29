from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.controls import routing_plan,validate_plan,assert_same_question
from legalmath.interpretation.assurance.control_investigation import BoundedReader,investigate
from legalmath.interpretation.search.providers import Completion
from legalmath.interpretation.assurance.lowering import lower,check_review
from tests.assurance.test_decision_controls import packet,controls,quote,reading,assignment


def fixture():
    p=packet();ctl=controls()
    claim={'claim_id':'claim.one','kind':'OBLIGATION','actor':'firm','action':'use certificate','modality':'MUST',
           'conditions':[],'exceptions':[],'temporal':[],'statement':'certificate condition','relevance':'CONTROL',
           'evidence':quote('u0',p['units'][0]['text']),'uncertainty':[]}
    formal={'facts':[{'name':'cert_required','type':'bool','meaning':'certificate required','unit':'submission',
                     'source_unit_ids':['u0'],'requires_judgment':True}], 'scope':'true','result':'cert_required','result_type':'bool'}
    candidate=reading('candidate','requirement applies','TRUE_IS_SATISFIED',formal)
    route={'claims':[assignment('claim.one','ecert.applicability')],
           'candidates':[assignment('candidate','ecert.applicability')],'missing_questions':[]}
    return p,[claim],{'candidate':candidate},ctl,route


def test_question_identity_rejects_applicability_vs_satisfaction():
    original=controls()[0];other=deepcopy(original);other['result_kind']='REQUIREMENT_SATISFIED'
    with pytest.raises(LegalMathError):assert_same_question(original,other)


def test_deleted_pair_fails_revalidation():
    p,cl,cs,ct,r=fixture();plan=routing_plan(p,cl,cs,ct,[r,r]);plan['required_pairs']=[]
    with pytest.raises(LegalMathError):validate_plan(plan,p,cl,cs)


def test_wrong_output_polarity_cannot_be_routed():
    p,cl,cs,ct,r=fixture();cs['candidate']['statement']='[TRUE_IS_COMPLIANT] certificate possessed'
    result=routing_plan(p,cl,cs,ct,[r,r])
    assert any(f['kind']=='OUTPUT_QUESTION_MISMATCH' for f in result['findings'])
    assert result['required_pairs']==[['claim.one','candidate']]


def test_actual_fidelity_dispatch_and_preserved_source(tmp_path):
    p,cl,cs,ct,r=fixture()
    class Reader:
        requests=[]
        def call(self,request,model,validate):
            self.requests.append(request)
            if request['task']=='CONTROL_ROUTING':return validate(r)
            pairs=request['required_pairs']
            return validate({'checks':[dict(pair,label='NOT_ESTABLISHED',source_evidence=[],
                representation_quotes=[],rationale='fact classification needs evidence',failing_stage='INTERPRETATION',
                question='What establishes the classification?') for pair in pairs], 'additional_concerns':[]})
    reader=Reader();result=investigate(p,cl,cs,ct,reader,tmp_path,'2026-02-03T00:00:00.000000Z')
    assert result['completed_pairs']==1 and result['pending_pairs']==0
    assert len(reader.requests)==3
    assert all(q['source_packet']==p for q in reader.requests)
    assert result['legal_completeness_established'] is False


def test_failed_batch_executes_smaller_repair(tmp_path):
    p,cl,cs,ct,r=fixture()
    cl.append({**cl[0],'claim_id':'claim.two'})
    r['claims'].append(assignment('claim.two','ecert.applicability'))
    class Reader:
        sizes=[]
        def call(self,request,model,validate):
            if request['task']=='CONTROL_ROUTING':return validate(r)
            pairs=request['required_pairs'];self.sizes.append(len(pairs))
            if len(pairs)>1:return None
            return validate({'checks':[dict(pairs[0],label='NOT_ESTABLISHED',source_evidence=[],
                representation_quotes=[],rationale='unresolved',failing_stage='FORMALIZATION',question='unresolved')],
                'additional_concerns':[]})
    reader=Reader();result=investigate(p,cl,cs,ct,reader,tmp_path,'2026-02-03T00:00:00.000000Z')
    assert reader.sizes==[2,1,1]
    assert result['completed_pairs']==2 and result['failed_batches']==1


def test_provider_gets_json_schema_and_raw_response_is_retained(tmp_path):
    from legalmath.interpretation.assurance.controls import Routing
    p,cl,cs,ct,r=fixture()
    class Provider:
        provider_id='test';routing='test';live=False;calls=0
        def complete(self,request,schema,settings):
            assert isinstance(schema,dict) and schema['type']=='object'
            self.calls+=1
            return Completion(r,{'test':True})
    provider=Provider();reader=BoundedReader(provider,tmp_path,{'fixture':True})
    result=reader.call({'task':'TEST'},Routing,lambda v:v)
    assert result==r
    assert reader.call({'task':'TEST'},Routing,lambda v:v)==r
    assert provider.calls==1
    assert len(list(tmp_path.rglob('action-*/result.json')))==1


def test_correspondence_cannot_promote_uncertain_lowering():
    p,cl,cs,ct,r=fixture();original=cs['candidate']
    record=lower(original,{'original_hash':digest(original),'scope':'true','result':'cert_required',
        'explanation':'same expressions','additional_uncertainty':['method unresolved']},p,'2026-02-03T00:00:00.000000Z')
    result=check_review(record,{'original_hash':digest(original),'lowered_hash':record['reading_hash'],
        'judgment':'PRESERVES_DECLARED_MEANING','evidence':original['citations'],
        'rationale':'same expression','uncertainty':[]},p)
    assert result['status']=='LOWERING_UNRESOLVED'
    assert result['source_fidelity_still_required']


def test_priority_cycle_and_missing_date_are_unresolved():
    from legalmath.interpretation.assurance.legal_profile import precedence
    documents={'a':{'source_sha256':'a'*64,'text':'The later circular extends the parallel period.'}}
    anchor={'document_id':'a','source_sha256':'a'*64,'start':0,'end':46,'quote':documents['a']['text']}
    anchor['end']=len(anchor['quote'])
    edge={'higher':'new','lower':'old','question':'parallel','effective_from':'2024-10-24',
          'effective_until':None,'evidence':[anchor]}
    assert precedence(['new','old'],[edge],documents,question='parallel',at='2024-11-01')['selected']=='new'
    reverse={**edge,'higher':'old','lower':'new'}
    result=precedence(['new','old'],[edge,reverse],documents,question='parallel',at='2024-11-01')
    assert result['status']=='UNRESOLVED_PRIORITY' and result['selected'] is None
    edge['effective_from']=None
    assert precedence(['new','old'],[edge],documents,question='parallel',at='2024-11-01')['selected'] is None


def test_changed_authority_blocks_current_duty_use():
    from legalmath.interpretation.assurance.legal_profile import replay_authority_bound_duty
    from tests.conformance.event_support import event_cases
    request=event_cases()[2]['request']
    same=replay_authority_bound_duty(request,'a'*64,'a'*64)
    changed=replay_authority_bound_duty(request,'a'*64,'b'*64)
    assert same['current_assurance_usable']
    assert changed['status']=='AUTHORITY_CHANGED_REINVESTIGATION_REQUIRED'
    assert same['historical']==changed['historical']


def test_source_structure_does_not_normalize_negation_or_quantities():
    from legalmath.interpretation.assurance.source_structure import compare_region
    page={'source_sha256':'a'*64,'raster_sha256':'b'*64,'page':1,'width':600.0,'height':800.0}
    ref={**{k:page[k] for k in ('source_sha256','raster_sha256','page')},'bbox':[50.1,20.0,550.0,100.0],
         'text':'Do not exceed HK$40 million excluding primary residence.'}
    assert compare_region(ref,ref['text'].replace(' ','\n'),page)['status']=='REGION_TEXT_MATCH'
    for source,target in [('not',''),('40','41'),('million','billion'),('excluding','including')]:
        assert compare_region(ref,ref['text'].replace(source,target),page)['status']=='REGION_DISCREPANCY'
    page['raster_sha256']='c'*64
    with pytest.raises(LegalMathError):compare_region(ref,ref['text'],page)


def test_method_satisfaction_is_not_requirement_applicability(tmp_path):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
    from decision_java import build_str,str_cases
    from legalmath.ir.evaluate import evaluate
    from decision_live import AT
    compiled,bindings,readings=build_str()
    reference={'id':'xml.missing','method':'xml','cert':False,'streams':True,'licensed':True,'after_launch':True,
               'expected':{'ecert':'TRUE','submission':'FALSE','resubmission':'FALSE'}}
    cases=str_cases(compiled,bindings,[reference])
    actual=[evaluate(compiled,c['snapshot'],c['rule_id'],AT,AT)['status'] for c in cases]
    assert actual==['TRUE','FALSE','FALSE']
    reference['method']='invalid'
    with pytest.raises(ValueError):str_cases(compiled,bindings,[reference])


def test_uncertain_multi_question_route_preserves_every_pair():
    p,cl,cs,ct,r=fixture()
    r['candidates'][0].update(status='UNRESOLVED',control_ids=[x['control_id'] for x in ct])
    plan=routing_plan(p,cl,cs,ct,[r,r])
    assert plan['required_pairs']==[['claim.one','candidate']]
    assert plan['bindings']['candidates']['candidate']['control_ids']==[]
    assert len(plan['bindings']['candidates']['candidate']['reader_assignments'][0]['control_ids'])==2


def test_reused_batch_id_cannot_erase_completed_work(tmp_path):
    from legalmath.interpretation.assurance.fidelity_batches import FidelityBatches
    ledger=FidelityBatches(tmp_path/'ledger.json',[['c1','r'],['c2','r']])
    ledger.record('batch',[['c1','r']])
    with pytest.raises(LegalMathError):ledger.record('batch',[['c2','r']])
    assert ledger.pending==[('c2','r')]


def test_oversized_routing_executes_chunks_without_losing_claims(tmp_path):
    from legalmath.interpretation.assurance.control_investigation import route_with_repair
    p,cl,cs,ct,r=fixture()
    cl=[{**cl[0],'claim_id':'claim.'+str(i)} for i in range(33)]
    class Reader:
        requests=[]
        def call(self,request,model,validate):
            self.requests.append(request)
            if 'routing_repair' not in request:return None
            return validate({'claims':[assignment(c['claim_id'],'ecert.applicability') for c in request['claims']],
                'candidates':[assignment(k,'ecert.applicability') for k in request['candidates']],
                'missing_questions':['Unresolved external definition']})
    reader=Reader()
    result=route_with_repair(p,cl,cs,ct,reader,tmp_path,'qualification-routing')
    assert [len(q['claims']) for q in reader.requests]==[33,16,16,1]
    assert all(q['source_packet']==p for q in reader.requests)
    assert {r['item_id'] for r in result['claims']}=={c['claim_id'] for c in cl}
    assert result['missing_questions']==['Unresolved external definition']


def test_failed_routing_chunk_cannot_be_replaced_by_partial_success(tmp_path):
    from legalmath.interpretation.assurance.control_investigation import route_with_repair
    p,cl,cs,ct,r=fixture()
    cl=[{**cl[0],'claim_id':'claim.'+str(i)} for i in range(17)]
    class Reader:
        def call(self,request,model,validate):
            if request.get('routing_repair',{}).get('index')!=0:return None
            return validate({'claims':[assignment(c['claim_id'],'ecert.applicability') for c in request['claims']],
                'candidates':[assignment(k,'ecert.applicability') for k in request['candidates']], 'missing_questions':[]})
    assert route_with_repair(p,cl,cs,ct,Reader(),tmp_path,'qualification-routing') is None
    assert (tmp_path/'qualification-routing.chunk-0.json').exists()


def test_exhausted_shared_allowance_stops_requests_without_losing_denominator(tmp_path):
    p,cl,cs,ct,r=fixture()
    class Provider:
        provider_id='test';routing='test';live=False;calls=0
        def complete(self,request,schema,settings):
            self.calls+=1
            raise LegalMathError('E_RESOURCE_LIMIT',details='Shared live allowance or reviewed increment exhausted')
    provider=Provider();reader=BoundedReader(provider,tmp_path/'model',{'fixture':True})
    result=investigate(p,cl,cs,ct,reader,tmp_path/'checks','2026-02-03T00:00:00.000000Z')
    assert provider.calls==1
    assert result['unexamined_pairs']==1 and not result['execution_complete']
    assert result['stopped_reason']=='Shared live allowance or reviewed increment exhausted'


def test_continuation_reuses_verified_response_without_resetting_old_journal(tmp_path):
    from legalmath.interpretation.assurance.controls import Routing
    p,cl,cs,ct,r=fixture()
    class Provider:
        provider_id='test';routing='test';live=False;calls=0
        def complete(self,request,schema,settings):
            self.calls+=1
            return Completion(r,{'test':True})
    provider=Provider();old=BoundedReader(provider,tmp_path/'old',{'round':1},maximum_actions=1)
    assert old.call({'task':'TEST'},Routing,lambda v:v)==r
    before=old.provider.journal.path.read_bytes()
    new=BoundedReader(provider,tmp_path/'new',{'round':2},maximum_actions=2,reuse_from=[old])
    assert new.call({'task':'TEST'},Routing,lambda v:v)==r
    assert provider.calls==1 and old.provider.journal.path.read_bytes()==before
    assert new.provider.journal.report()['consumed_actions']==0
    assert len(list((tmp_path/'new/reused-responses').glob('*.json')))==1
    assert new.call({'task':'A_DIFFERENT_REQUEST'},Routing,lambda v:v)==r
    assert provider.calls==2
    result=next((tmp_path/'old/model').glob('action-*/result.json'))
    result.write_text('{}')
    with pytest.raises(LegalMathError):new.call({'task':'TEST'},Routing,lambda v:v)
