from copy import deepcopy
from itertools import combinations
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.formal import Comparisons
from legalmath.interpretation.assurance.questions import (proposals,partition,verify_partition,
                                                        execute_partitions,annotate_actions)
from legalmath.interpretation.assurance.resolution import choose_action
from .support import packet,reading
from tests.search.test_formal import AT


def fixture(root,tmp_path):
    checker=Comparisons(tmp_path,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT)
    candidates={'good':reading(),'missing':reading(True)};p=packet()
    c={'pair':['good','missing'],'result':checker.compare(candidates['good'],candidates['missing'],p)}
    assert c['result']['status']=='DIFFERENT'
    return checker,candidates,p,[c]


def test_actual_java_partitions_drive_priority_and_shared_error_checks_survive(root,tmp_path):
    checker,candidates,p,comparisons=fixture(root,tmp_path)
    checked=execute_partitions(comparisons,candidates,p,checker)
    r=checked['partitions'][0]
    assert r['separated_pairs']==[['good','missing']] and r['coverage_complete']
    assert all(row['replay']['java'] for row in r['records'].values())
    actions=[{'kind':'REPAIR_STAGE','issue_key':'repair','stage':'FORMALIZATION','candidate_id':'missing','inputs':{}},
             {'kind':'REPAIR_STAGE','issue_key':'shared','stage':'INTERPRETATION','candidate_id':None,'inputs':{}}]
    actions=annotate_actions(actions,checked,candidates,p,AT)
    scope=actions[0]['score_scope']
    assert actions[0]['separated_pairs']==1 and actions[1]['separated_pairs']==0
    assert choose_action(actions,set(),scope,remaining_cost=5)['issue_key']=='shared'
    assert choose_action(actions[:1],set(),scope,remaining_cost=5)['inputs']['partition_hashes']
    assert not r['source_question_answered']


def test_agreement_has_zero_gain_and_unexecuted_scores_do_not_rank(root,tmp_path):
    checker,candidates,p,comparisons=fixture(root,tmp_path)
    candidates['missing']=deepcopy(candidates['good'])
    question=proposals(comparisons,candidates,p,AT)[0][0]
    r=partition(question,candidates,p,checker)
    assert r['separated_candidate_pairs']==0 and r['separated_pairs']==[]
    actions=[{'kind':'REPAIR_STAGE','issue_key':'unverified','separated_pairs':999999,'inputs':{}},
             {'kind':'ACQUIRE_AUTHORITY','issue_key':'source','inputs':{}}]
    assert choose_action(actions,set(),{},remaining_cost=5)['issue_key']=='source'


def test_different_outputs_subjects_fact_definitions_and_limits_are_excluded(root,tmp_path):
    checker,candidates,p,comparisons=fixture(root,tmp_path)
    candidates['different.output']=deepcopy(reading());candidates['different.output']['statement']='[TRUE_IS_COMPLIANT] Opposite output meaning.'
    candidates['different.subject']=deepcopy(reading());candidates['different.subject']['subject']='Other institution'
    candidates['different.fact']=deepcopy(reading());candidates['different.fact']['formalization']['facts'][0]['meaning']='An altered meaning'
    candidates['unsupported']=deepcopy(reading());candidates['unsupported']['formalization']=None
    r=execute_partitions(comparisons,candidates,p,checker,max_replays=1)['partitions'][0]
    assert {e['reason'] for e in r['excluded']}=={'OUTPUT_MEANING_UNALIGNED','SUBJECT_UNALIGNED','INCOMPATIBLE_FACT_BINDINGS','UNSUPPORTED_FORMALIZATION','REPLAY_LIMIT'}
    assert not r['coverage_complete'] and r['separated_candidate_pairs']==0
    empty=execute_partitions(comparisons,candidates,p,checker,max_questions=0)
    assert empty['status']=='INCOMPLETE' and empty['deferred'] and empty['replays_consumed']==0


@pytest.mark.parametrize('change',['source','candidate','time','count','binding','assumption'])
def test_changed_scope_or_forged_partition_cannot_be_reused(root,tmp_path,change):
    checker,candidates,p,comparisons=fixture(root,tmp_path)
    r=execute_partitions(comparisons,candidates,p,checker)['partitions'][0];at=AT
    if change=='source':p['units'][0]['text']+=' Another exception applies.'
    if change=='candidate':candidates['good']['assumptions'].append('New business assumption')
    if change=='time':at='2026-09-24T00:00:00.000000Z'
    if change=='count':r['separated_candidate_pairs']=10
    if change=='binding':r['records']['good']['snapshot']['facts']['discount']['value']=False
    if change=='assumption':r['question']['assumptions']=['Invented applicability assumption']
    if change in ('count','binding','assumption'):r['partition_hash']=digest({k:v for k,v in r.items() if k!='partition_hash'})
    with pytest.raises(LegalMathError):verify_partition(r,candidates,p,at)


def test_runtime_delivers_executed_partition_to_repair_action(root,tmp_path):
    from legalmath.interpretation.assurance.engine import Assurance
    from legalmath.canonical import loads
    from tests.search.support import FunctionProvider
    from .test_integration import responder,settings,source
    good,bad=responder(False),responder(True)
    def respond(request):
        if request.get('role')=='alternatives' and request['task']=='GENERATE': return bad(request)
        return good(request)
    directory=tmp_path/'assurance'
    run=Assurance(directory,FunctionProvider(respond),root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,settings(1))
    r=run.drive([source()],'Gift control with alternative exception reading')
    assert r['execution_complete'],r
    assert any(a.get('separation_basis')=='EXECUTED_JAVA_PARTITIONS' and a['separated_pairs']>0 for a in r['actions'])
    evidence=loads((directory/r['question_partitions']).read_bytes())
    assert any(x['partitions'] for x in evidence) and sum(x['replays_consumed'] for x in evidence)<=32


def test_requested_partition_limit_propagates_incomplete_status(root,tmp_path):
    from legalmath.interpretation.assurance.engine import Assurance
    from tests.search.support import FunctionProvider
    from .test_integration import responder,settings,source
    good,bad=responder(False),responder(True)
    def respond(request):
        return bad(request) if request.get('role')=='alternatives' and request['task']=='GENERATE' else good(request)
    config=settings().model_copy(update={'max_question_replays':0})
    run=Assurance(tmp_path/'run',FunctionProvider(respond),root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,config)
    result=run.drive([source()],'Gift')
    assert not result['execution_complete'] and result['status']=='UNRESOLVED'
    assert any(f['kind']=='QUESTION_PARTITIONS_INCOMPLETE' for f in result['findings'])
