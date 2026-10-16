from copy import deepcopy
from datetime import datetime, timedelta, timezone
import pytest
from legalmath.canonical import digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.route_admission import workload, admission, RouteBudgetProvider
from legalmath.interpretation.assurance.optional_tools import adapter_results, retrieval_questions
from legalmath.interpretation.search.models import Settings
from tests.search.support import FunctionProvider


def required(**kwargs):
    return workload(**dict({'pieces':5,'reader_claims':[39,39],'selected_claims':67,'all_claims':78,
        'candidates':12,'formalized_candidates':6},**kwargs))


def test_original_remaining_grant_refuses_known_doomed_prefix():
    needed=required()
    result=admission(needed,{'core':23,'question_assignment':3,'scoped':82,'dossier_reviews':64,'interaction':1,'synthesis':1},
        deadline_utc='2026-10-12T04:28:01+00:00',now=datetime(2026,10,10,tzinfo=timezone.utc))
    assert needed['scoped_pairs']==936 and needed['stages']['scoped']==156
    assert needed['core_pairs']==804 and needed['deterministic_unformalized_pairs']==402
    assert not result['admitted']
    assert {r['boundary'] for r in result['failures']} >= {'core','scoped'}


def test_context_passes_repairs_deferred_candidates_tools_and_final_answer_count():
    first=required(scoped_batch=64,dossier_groups=12)
    larger=required(scoped_batch=64,dossier_groups=12,context_passes=2,semantic_rounds=1,
        candidates=24,formalized_candidates=12,tool_enabled=True,other_core_calls=4)
    assert larger['stages']['core']>first['stages']['core'] and larger['stages']['scoped']>first['stages']['scoped']
    assert larger['optional_tool_actions']>0
    assert larger['stages']['interaction']==larger['stages']['synthesis']==1
    too_many=required(reader_claims=[150,150],all_claims=300,selected_claims=300,candidates=24)
    result=admission(too_many,{s:1000 for s in too_many['stages']},deadline_utc='2099-01-01T00:00:00+00:00')
    assert {r['boundary'] for r in result['failures']} >= {'core_pairs','scoped_pairs'}


def guard(tmp_path, provider=None):
    provider=provider or FunctionProvider(lambda r:{'received':r['task']})
    w=required(pieces=1,reader_claims=[1,1],selected_claims=1,all_claims=1,candidates=1,formalized_candidates=1,dossier_groups=1)
    wrapped=RouteBudgetProvider(provider,tmp_path,w,w['stages'],(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat())
    return wrapped,provider


def test_guard_rejects_unknown_constructor_changed_population_and_unaffordable_transition(tmp_path):
    wrapped,provider=guard(tmp_path)
    with pytest.raises(LegalMathError):wrapped.complete({'task':'UNBUDGETED'},{},Settings())
    with pytest.raises(LegalMathError):wrapped.observe(claims=2)
    more=deepcopy(wrapped.plan['required']);more['stages']['scoped']=999
    with pytest.raises(LegalMathError):wrapped.transition('actual-scoped',more)
    assert not provider.requests
    assert not loads(wrapped.path.read_bytes())['transitions'][-1]['admission']['admitted']


def test_failed_reservation_survives_restart_without_another_dispatch(tmp_path):
    def fail(r):raise LegalMathError('E_DEPENDENCY',details='disconnected')
    wrapped,provider=guard(tmp_path,FunctionProvider(fail))
    with pytest.raises(LegalMathError):wrapped.complete({'task':'GENERATE'},{},Settings())
    restarted=RouteBudgetProvider(provider,tmp_path,wrapped.plan['required'],wrapped.plan['remaining'],wrapped.plan['deadline_utc'])
    with pytest.raises(LegalMathError):restarted.complete({'task':'GENERATE'},{},Settings())
    assert len(provider.requests)==1 and loads(wrapped.path.read_bytes())['calls'][0]['status']=='FAILED'


def test_durable_guard_keeps_stage_classification_for_output_repair(tmp_path):
    wrapped,provider=guard(tmp_path)
    wrapped.complete({'task':'REPAIR_OUTPUT','original_task':'SCOPED_SOURCE_FIDELITY'},{},Settings())
    assert loads(wrapped.path.read_bytes())['calls'][0]['stage']=='scoped'


def test_nested_adapter_status_is_not_hidden_by_shared_pass():
    check={'status':'PASS','tool':'Candidate tools','results':[
        {'tool':'LegalRuleML','status':'PASS'}, {'tool':'Logical English','status':'UNSUPPORTED'}]}
    assert {r['tool_id']:r['status'] for r in adapter_results(check)}=={'legalruleml':'PASS','logical-english':'UNSUPPORTED'}
    graph={'status':'PASS','tool':'Argument tools','selected_tools':['pyarg','carneades','clingo'],
        'checks':{'pyarg':{'agrees':True},'carneades':{'agrees':False},'clingo':{'agrees':True}}}
    assert {r['tool_id']:r['status'] for r in adapter_results(graph)}['carneades']=='FAILED'


def test_retrieval_for_different_question_or_unbridged_typed_target_is_not_answer_support():
    questions=[{'question_id':'p10','text':'What satisfies paragraph 10?'}]
    check={'kind':'retrieval','query':questions[0]['text'],'inputs_hash':digest({'question':questions[0]['text']})}
    assert retrieval_questions(check,questions,{})==['p10']
    wrong={**check,'query':'Was a request made?','inputs_hash':digest({'question':'Was a request made?'})}
    assert retrieval_questions(wrong,questions,{})==[]
    assert retrieval_questions({**check,'target_candidate_id':'trigger-reading'},questions,{})==[]
