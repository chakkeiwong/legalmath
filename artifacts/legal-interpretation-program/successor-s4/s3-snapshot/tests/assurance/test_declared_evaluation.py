from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.canonical import loads,digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.declared_evaluation import (
    declared_reference_case,score_declared,validate_public,
)
from legalmath.interpretation.assurance.issue_search import merge_hypotheses
from legalmath.interpretation.search.formal import Comparisons

ROOT=Path(__file__).resolve().parents[2]
AT='2026-09-24T00:00:00.000000Z'
JDK=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'


def data():
    old=loads((ROOT/'.localresources/interpretation-round5/public-qa-v1/frozen/study.json').read_bytes())['cases'][0]
    case,public,provenance=declared_reference_case(old)
    return old,case,public,provenance


def result_for(public,readings):
    responses={str(i):{'readings':[r],'vocabulary_concerns':[],'questions':[]} for i,r in enumerate(readings)}
    return {'status':'COMPLETE','public_hash':digest(public),'source_packet_hash':digest(public['packet']),
        'merged':merge_hypotheses(responses,public['issue'],public['packet'],public['at']),
        'reviews':{},'invalid_proposals':{'records':[]}}


def test_reference_version_changes_declaration_and_preserves_hidden_function():
    old,case,public,provenance=data()
    assert provenance['original_case_hash']==digest(old)
    a=old['reference'];b=case['reference']
    assert a['binding_reading']['formalization']==b['binding_reading']['formalization']
    assert a['accepted']==b['accepted'] and a['snapshots']==b['snapshots']
    assert b['binding_reading']['statement'].startswith('[TRUE_IS_SATISFIED]')
    assert set(public)=={'packet','issue','at'}
    with pytest.raises(LegalMathError):validate_public({**public,'reference':b})


def test_paraphrase_is_compared_by_declared_question_and_executed_meaning(tmp_path):
    _,case,public,_=data();reading=deepcopy(case['reference']['binding_reading'])
    reading['statement']='[TRUE_IS_SATISFIED] The selected applicability predicate holds when the three given classifications all hold.'
    result=result_for(public,[reading]);out=score_declared(result,case,public,Comparisons(tmp_path,JDK,public['at']))
    assert out['status']=='ABSTAIN' and out['reference_in_candidate_set']
    assert out['excess_reference_signatures']==0 and not out['release_eligible']
    # The original reference itself retains questions. Only this explicitly
    # cleared synthetic fixture tests the no-concern acceptance disposition.
    reading['questions']=[]
    result=result_for(public,[reading])
    out=score_declared(result,case,public,Comparisons(tmp_path/'cleared-fixture',JDK,public['at']))
    assert out['status']=='ACCEPTED' and out['reference_in_candidate_set']


@pytest.mark.parametrize('field',['question','fact'])
def test_paraphrase_permission_does_not_allow_different_question_or_fact_meaning(field,tmp_path):
    _,case,public,_=data();reading=deepcopy(case['reference']['binding_reading'])
    if field=='question':reading['subject']='Is the office compliant?'
    else:reading['formalization']['facts'][0]['meaning']='The office possesses a licence'
    with pytest.raises(LegalMathError):result_for(public,[reading])


def test_candidate_set_coverage_cannot_hide_excess_alternatives_or_uncertainty(tmp_path):
    _,case,public,_=data();r=case['reference']['binding_reading'];bad=deepcopy(r)
    bad['formalization']['result']='(or regulated business hong_kong)'
    result=result_for(public,[r,bad]);out=score_declared(result,case,public,Comparisons(tmp_path/'multiple',JDK,public['at']))
    assert out['status']=='ABSTAIN' and out['reference_in_candidate_set']
    assert out['distinct_signatures']==2 and out['excess_reference_signatures']==1
    duplicate=deepcopy(r);duplicate['statement']+=' A second wording.'
    result=result_for(public,[r,duplicate]);result['invalid_proposals']['records']=[{'reason':'rejected response retained'}]
    out=score_declared(result,case,public,Comparisons(tmp_path/'same',JDK,public['at']))
    assert out['distinct_signatures']==1 and out['status']=='ABSTAIN' and out['uncertainty_retained']


def test_actual_four_method_task_graphs_keep_hidden_answers_out_and_resume_without_calls(tmp_path):
    from legalmath.interpretation.assurance.declared_evaluation import MethodRun
    from legalmath.interpretation.search.providers import Allowance,Completion
    from legalmath.interpretation.assurance.decomposition import compact_request
    old,case,public,_=data();reading=case['reference']['binding_reading']
    ledger=tmp_path/'allowance.json';allowance=Allowance(ledger,500,reservation_ceiling=100)
    seen=[]
    class Provider:
        provider_id='test.declared-comparison';live=True
        routing={'provider':'fixture','model':'deterministic'}
        def complete(self,request,schema,settings):
            assert not ({'reference','accepted','binding_reading','snapshots'} & set(request))
            seen.append(request);slot=allowance.reserve(digest(request))
            # This fake is an engineering oracle only; the real provider never
            # receives this fixture response or the hidden program.
            if request['task']=='ISSUE_HYPOTHESES':
                value={'readings':[deepcopy(reading)],'vocabulary_concerns':[],
                       'questions':['Fixture unresolved source question, to exercise reconsideration.']}
            else:
                value={'judgments':[{'candidate_id':cid,'judgment':'UNRESOLVED_READING',
                    'source_evidence':reading['citations'],'rationale':'Fixture deliberately retains uncertainty.',
                    'unresolved_question':'Fixture source question remains.'} for cid in request.get('required_candidate_ids',request['candidates'])],
                    'missed_readings':[],'vocabulary_concerns':[],'questions':[]}
            return Completion(value,{'provider':self.provider_id,'fresh_context':True,'request_hash':digest(request),
                'response_hash':digest(value),'allowance_slot':slot,'provider_route_hash':digest(self.routing)})
    for arm,expected in [('single-reader',1),('isolated-readers',2),('search',3),('assurance',6)]:
        initial=len(seen)
        method=MethodRun(tmp_path/arm,public,Provider(),ledger,JDK)
        result=method.execute(arm)
        assert result['task_attempts']==expected and len(seen)-initial==expected
        first=seen[initial]
        assert 'prior_hypotheses' not in first
        if arm!='single-reader':assert 'prior_hypotheses' not in seen[initial+1]
        if arm in ('search','assurance'):assert 'prior_hypotheses' in seen[initial+2]
        if arm=='assurance':assert result['cycles']==1 and len(result['review_history'])==2
        replay=MethodRun(tmp_path/arm,public,Provider(),ledger,JDK).execute(arm)
        assert len(seen)-initial==expected and replay==result


def test_nonexecutable_reading_remains_visible_and_forces_abstention(tmp_path):
    from legalmath.interpretation.assurance.issue_search import distinguish,audit_request
    _,case,public,_=data();r=deepcopy(case['reference']['binding_reading'])
    r['formalization']=None;r['questions']=['Does the fixed vocabulary omit a necessary legal distinction?']
    result=result_for(public,[r]);checker=Comparisons(tmp_path,JDK,public['at'])
    compared=distinguish(public['issue'],public['packet'],result['merged']['candidates'],checker)
    assert compared['java_cases']==0 and not compared['outputs'] and len(compared['unencoded_candidates'])==1
    request=audit_request(public['issue'],public['packet'],result['merged']['candidates'],compared,'source-critic')
    assert len(request['candidates'])==1 and request['unencoded_candidates']
    outcome=score_declared(result,case,public,checker)
    assert outcome['status']=='ABSTAIN' and outcome['distinct_signatures']==0
    assert outcome['unencoded_candidates'] and not outcome['reference_in_candidate_set']
    r['questions']=[]
    with pytest.raises(LegalMathError):result_for(public,[r])


def test_two_reading_bound_and_four_target_criticism_are_enforced_before_dispatch(tmp_path):
    from legalmath.interpretation.assurance.declared_evaluation import MethodRun
    from legalmath.interpretation.assurance.checkpoints import validate_task
    from legalmath.interpretation.assurance.issue_search import Hypotheses
    _,case,public,_=data();r=case['reference']['binding_reading']
    method=MethodRun.__new__(MethodRun);method.public=public
    captured=[]
    def fake_step(name,tasks):
        captured.extend(tasks)
        return {t['task_id']:{'readings':[r],'vocabulary_concerns':[],'questions':[]} for t in tasks}
    method.step=fake_step
    method.generate('initial',('syntax-reader',))
    t=captured[0]
    assert t['schema']['properties']['readings']['maxItems']==2
    assert t['request']['response_schema']['properties']['readings']['maxItems']==2
    three=[deepcopy(r) for _ in range(3)]
    for i,reading in enumerate(three):reading['local_id']='r.'+str(i)
    with pytest.raises(LegalMathError):validate_task(t,{'readings':three,'vocabulary_concerns':[],'questions':[]})
    candidates={f'candidate.{i}':deepcopy(r) for i in range(6)}
    comparisons={'issue_hash':digest(public['issue']),'source_packet_hash':digest(public['packet']),
        'candidates_hash':digest(candidates),'outputs':{},'ranked_scenarios':[]}
    captured.clear()
    method.audit('critic',{'candidates':candidates},comparisons)
    assert len(captured)==2
    assert [len(t['request']['required_candidate_ids']) for t in captured]==[4,2]
    assert all(len(t['request']['candidates'])==6 for t in captured)
    assert all(set(t['context']['candidates'])==set(t['request']['required_candidate_ids']) for t in captured)
