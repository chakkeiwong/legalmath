"""Current-route regressions: engineering evidence, never legal correctness."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import tempfile

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import pytest

from legalmath.canonical import digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.original_questions import attach, validate
from legalmath.interpretation.assurance.investigation_answer import question_text
from legalmath.interpretation.assurance.optional_tools import ToolSession, retrieval_questions
from legalmath.interpretation.assurance.route_admission import RouteBudgetProvider, workload
from legalmath.interpretation.assurance.transport import CompactProvider
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
from legalmath.interpretation.assurance.engine import Assurance
from legalmath.interpretation.search.models import Settings
from tests.search.support import FunctionProvider
from .test_integration import settings, source, responder, AT
from .test_round16 import scoped_fixture, JDK
from .test_successor_workflow import complete_responder

QUESTIONS = [{'question_id':'p10','text':'What fulfills the requirement?'},
             {'question_id':'evidence','text':'What does reconciliation establish?'}]


class RetrievalBackend:
    def __init__(self): self.calls=[]
    def identity(self): return {'fixture':'original-question-retrieval.v1'}
    def retrieval(self, packet, inputs, work):
        self.calls.append(deepcopy(inputs))
        return {'status':'PASS','tool':'BM25','query':inputs['question'],
                'target_question_hash':inputs.get('question_hash'),
                'target_candidate_id':inputs.get('candidate_id'),'passages':[]}


def test_original_binding_is_exact_and_does_not_rewrite_source():
    packet,*_=scoped_fixture(); packet['selected_slice']=question_text(QUESTIONS)
    request={'task':'GENERATE','source_packet':packet}
    attached=attach(request,QUESTIONS)
    assert attached['original_questions']==QUESTIONS and attached['source_packet']==packet
    assert 'original_questions' not in request
    assert attach(attached,QUESTIONS)==attached
    with pytest.raises(LegalMathError):validate(QUESTIONS,'What activates the duty?')
    with pytest.raises(LegalMathError):validate([QUESTIONS[0],QUESTIONS[0]])
    with pytest.raises(LegalMathError):attach({**request,'original_questions':list(reversed(QUESTIONS))},QUESTIONS)


def test_separate_original_queries_reach_accounting_and_cache_without_joined_query(tmp_path):
    packet,*_=scoped_fixture(); packet['selected_slice']=question_text(QUESTIONS)
    backend=RetrievalBackend(); session=ToolSession(backend,tmp_path,original_questions=QUESTIONS)
    request={'task':'GENERATE','source_packet':packet}
    augmented=session.augment(request)
    checks=augmented['external_tool_context']['checks']
    assert [x['query'] for x in checks]==[q['text'] for q in QUESTIONS]
    assert [retrieval_questions(x,QUESTIONS,{}) for x in checks]==[['p10'],['evidence']]
    assert len(backend.calls)==2 and all(x['question']!=packet['selected_slice'] for x in backend.calls)
    restarted=ToolSession(backend,tmp_path,original_questions=QUESTIONS)
    assert restarted.augment(request)==augmented and len(backend.calls)==2
    assert restarted.report()['original_questions']==QUESTIONS
    with pytest.raises(LegalMathError):ToolSession(backend,tmp_path,original_questions=list(reversed(QUESTIONS)))


def test_context_is_bound_before_transport_with_or_without_tools(tmp_path):
    packet,*_=scoped_fixture(); packet['selected_slice']=question_text(QUESTIONS)
    for enabled in (False,True):
        provider=FunctionProvider(lambda r:{'received':True})
        tools=ToolSession(RetrievalBackend(),tmp_path/str(enabled)/'tools',original_questions=QUESTIONS) if enabled else None
        compact=CompactProvider(provider,tmp_path/str(enabled)/'transport',optional_tools=tools,original_questions=QUESTIONS)
        compact.complete({'task':'SOURCE_INVENTORY','source_packet':packet},{'type':'object'},Settings())
        assert provider.requests[0]['original_questions']==QUESTIONS
        assert provider.requests[0]['original_question_binding']==digest(QUESTIONS)


@pytest.mark.parametrize('task',['REPAIR_SOURCE_INVENTORY','PROPOSE_DERIVED_MAPPING','REGISTERED_EXAMPLE_QUERIES'])
def test_reachable_constructor_uses_core_reservation(tmp_path,task):
    provider=FunctionProvider(lambda r:{'received':r['task']})
    required=workload(pieces=1,reader_claims=[1,1],selected_claims=1,all_claims=1,
        candidates=1,formalized_candidates=1,dossier_groups=1,derived_mapping_calls=1,example_query_calls=1,semantic_rounds=1)
    guard=RouteBudgetProvider(provider,tmp_path,required,required['stages'],
        (datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat())
    guard.complete({'task':task},{},Settings())
    assert loads(guard.path.read_bytes())['calls'][0]['stage']=='core'
    with pytest.raises(LegalMathError):guard.complete({'task':'UNDECLARED_NEW_TASK'},{},Settings())
    assert len(provider.requests)==1


@pytest.mark.parametrize('task',['REPAIR_SOURCE_INVENTORY','PROPOSE_DERIVED_MAPPING','REGISTERED_EXAMPLE_QUERIES'])
def test_known_constructor_without_its_own_reserve_cannot_borrow_core_calls(tmp_path,task):
    provider=FunctionProvider(lambda r:pytest.fail('Unreserved constructor dispatched'))
    required=workload(pieces=1,reader_claims=[1,1],selected_claims=1,all_claims=1,
        candidates=1,formalized_candidates=1,dossier_groups=1)
    guard=RouteBudgetProvider(provider,tmp_path,required,required['stages'],
        (datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat())
    with pytest.raises(LegalMathError) as error:guard.complete({'task':task},{},Settings())
    assert error.value.details['unreserved_constructor']==task
    assert not loads(guard.path.read_bytes())['calls']


def test_mutated_question_context_is_rejected_before_new_tool_or_model_call(tmp_path):
    packet,*_=scoped_fixture();packet['selected_slice']=question_text(QUESTIONS)
    backend=RetrievalBackend();session=ToolSession(backend,tmp_path/'tools',original_questions=QUESTIONS)
    session.original_questions[0]['question_id']='forged'
    with pytest.raises(LegalMathError):session.augment({'task':'GENERATE','source_packet':packet})
    provider=FunctionProvider(lambda r:pytest.fail('Changed original identity dispatched'))
    transport=CompactProvider(provider,tmp_path/'transport',original_questions=QUESTIONS)
    transport.original_questions[0]['question_id']='forged'
    with pytest.raises(LegalMathError):transport.complete({'task':'GENERATE','source_packet':packet},{},Settings())
    assert not backend.calls and not provider.requests


def test_original_query_and_optional_constructor_costs_are_explicit():
    args=dict(pieces=5,reader_claims=[39,39],selected_claims=67,all_claims=78,candidates=12,
              formalized_candidates=6,tool_enabled=True)
    old=workload(**args); new=workload(**args,original_question_count=2,derived_mapping_calls=2,example_query_calls=1)
    assert new['stages']['core']==old['stages']['core']+3
    assert new['optional_tool_actions']==old['optional_tool_actions']+9


def test_complete_route_rejects_wrong_original_target_before_side_effects(tmp_path):
    provider=FunctionProvider(lambda r:pytest.fail('Wrong target dispatched'))
    runner=CompleteInvestigation(tmp_path,tmp_path/'run',provider,JDK,AT,settings=settings())
    with pytest.raises(LegalMathError):runner.run([source()],'Different original question',original_questions=QUESTIONS)
    assert not runner.directory.exists() and not provider.requests


def test_complete_route_does_not_dispatch_downstream_of_source_restart(tmp_path,monkeypatch):
    from legalmath.interpretation.assurance.integrated import IntegratedInvestigation
    monkeypatch.setattr(IntegratedInvestigation,'run',lambda *a,**k:{'interpretation':{
        'directory':str(tmp_path/'core'),'report':{'status':'RESTART_REQUIRED',
            'repair_stop':{'new_model_calls_for_repair':0}}}})
    provider=FunctionProvider(lambda r:pytest.fail('Downstream stage dispatched after source restart'))
    runner=CompleteInvestigation(tmp_path,tmp_path/'run',provider,JDK,AT,settings=settings())
    with pytest.raises(LegalMathError) as error:
        runner.run([source()],question_text(QUESTIONS),original_questions=QUESTIONS)
    assert error.value.details['stage']=='SOURCE_REVIEW_RESTART'
    assert not provider.requests
    assert loads((runner.directory/'current-state.json').read_bytes())['status']=='RESTART_REQUIRED'


def test_staged_inventory_repair_stops_before_new_inventory_or_stale_criticism(root,tmp_path):
    normal=responder()
    def respond(request):
        task=request.get('original_task',request['task'])
        if task=='REVIEW_SOURCE_CLAIMS':
            return {'request_binding':request['request_binding'],
                'checked_unit_ids':[u['unit_id'] for u in request['source_packet']['units']],
                'claims':[{'claim_id':c['claim_id'],'claim_hash':digest(c),'assessment':'QUESTIONED',
                    'source_reading':c['statement'],'support':c['evidence'],'contrary':[],
                    'qualifications':[],'missing_authorities':[],'nonlocal_claim_ids':[]} for c in request['claims']],
                'unresolved_questions':[]}
        if task=='REVIEW_SOURCE_OMISSIONS':
            return {'checked_unit_ids':[u['unit_id'] for u in request['source_packet']['units']],
                    'issues':[],'unresolved_questions':[]}
        value=normal(request)
        if task=='SOURCE_INVENTORY':value['claims'][0]['exceptions']=[]
        return value
    provider=FunctionProvider(respond)
    config=settings(1).model_copy(update={'staged_source_review':True,'total_model_calls':24})
    result=Assurance(tmp_path/'repair',provider,JDK,AT,config).drive([source()],'Selected gift control')
    assert result['status']=='RESTART_REQUIRED',result
    assert not result['execution_complete'] and result['repair_stop']['new_model_calls_for_repair']==0
    assert 'candidate-search' in result['repair_stop']['invalidated_stages']
    assert sum(r['task']=='SOURCE_INVENTORY' for r in provider.requests)==2
    assert not any(r['task'] in ('REPAIR_SOURCE_INVENTORY','STRUCTURED_CRITICISM') for r in provider.requests)


def test_complete_product_delivers_original_questions_in_every_model_stage(root):
    with tempfile.TemporaryDirectory(prefix='question-first-product-',dir=root/'artifacts') as directory:
        provider=FunctionProvider(complete_responder)
        runner=CompleteInvestigation(root,directory,provider,JDK,AT,settings=settings(),maximum_scoped_actions=12,scoped_rounds=1)
        result=runner.run([source()],question_text(QUESTIONS),original_questions=QUESTIONS)
        assert result['execution_complete'],result['core']['interpretation']['report']
        assert result['binding']['original_questions']==QUESTIONS
        assert {'SOURCE_INVENTORY','GENERATE','DEFINE_EXACT_QUESTIONS','SCOPED_SOURCE_FIDELITY'} <= {r['task'] for r in provider.requests}
        assert all(r['original_questions']==QUESTIONS for r in provider.requests)
        count=len(provider.requests)
        assert runner.run([source()],question_text(QUESTIONS),original_questions=QUESTIONS)==result
        assert len(provider.requests)==count
        from legalmath.interpretation.assurance import investigation_answer as consumer
        from legalmath.interpretation.assurance.integration_contract import evidence_file
        from legalmath.interpretation.assurance.monitor import save
        packet=loads((root/result['packet']['path']).read_bytes())
        qualification=Path(directory)/'qualification.json'
        save(qualification,{'profile':'investigation-answer-source-qualification.v1',
            'source_packet_hash':digest(packet),'limitations':['Scripted fixture, not legal evidence.'],
            'evidence':[result['packet']],'details':{'fixture':True}})
        ref=evidence_file(Path(directory)/'revisions'/result['revision']/'dossier.json',root)
        args={'investigation_directory':directory,'expected_revision':result['revision'],
            'questions':QUESTIONS,'qualification_ref':evidence_file(qualification,root)}
        assert consumer.prepare_request(root,ref,**args)['original_questions']==QUESTIONS
        renamed=deepcopy(QUESTIONS);renamed[0]['question_id']='changed-id-same-text'
        with pytest.raises(LegalMathError) as error:
            consumer.prepare_request(root,ref,**{**args,'questions':renamed})
        assert 'identities' in str(error.value.details)
