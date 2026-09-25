"""A supported model judgment must not erase recorded interpretation disputes."""
from copy import deepcopy
import pytest
from legalmath.canonical import digest
from legalmath.interpretation.assurance.declared_evaluation import MethodRun
from legalmath.interpretation.assurance.issue_search import (
    merge_hypotheses,distinguish,reconsideration_required,
)
from legalmath.interpretation.search.formal import Comparisons
from legalmath.interpretation.search.providers import Allowance,Completion
from tests.assurance.test_declared_evaluation import data,JDK


@pytest.mark.parametrize('discrepancy',['reading_question','different_behaviors'])
def test_supported_critics_still_trigger_actual_reconsideration(discrepancy,tmp_path):
    _,case,public,_=data();reading=deepcopy(case['reference']['binding_reading'])
    reading['questions']=[];readings=[reading]
    if discrepancy=='reading_question':
        reading['questions']=['Does an incorporated definition change this declared input?']
    else:
        rival=deepcopy(reading);rival['local_id']='alternative'
        rival['formalization']['result']='(or regulated business hong_kong)'
        readings.append(rival)
    ledger=tmp_path/'allowance.json';allowance=Allowance(ledger,100,reservation_ceiling=24)
    requests=[]
    class Provider:
        provider_id='test.discrepancy';live=True;routing={'provider':'fixture','model':'all-supported'}
        def complete(self,request,schema,settings):
            requests.append(request);slot=allowance.reserve(digest(request))
            if request['task']=='ISSUE_HYPOTHESES':
                answer={'readings':deepcopy(readings),'vocabulary_concerns':[],'questions':[]}
            else:
                answer={'judgments':[{'candidate_id':cid,'judgment':'SUPPORTED_READING',
                    'source_evidence':reading['citations'],'rationale':'Controlled all-supported critic.',
                    'unresolved_question':None} for cid in request['required_candidate_ids']],
                    'missed_readings':[],'vocabulary_concerns':[],'questions':[]}
            return Completion(answer,{'provider':self.provider_id,'fresh_context':True,
                'request_hash':digest(request),'response_hash':digest(answer),
                'allowance_slot':slot,'provider_route_hash':digest(self.routing)})
    result=MethodRun(tmp_path/'method',public,Provider(),ledger,JDK).execute('assurance')
    assert result['cycles']==1 and len(result['review_history'])==2
    assert len(requests)==6
    assert reconsideration_required(result['reviews'],result['merged'])
    assert not result['release_eligible']
    if discrepancy=='reading_question':
        assert any(c.get('candidate_id') and c['question']==reading['questions'][0]
                   for c in result['merged']['concerns'])
    else:
        assert result['behavior_groups']==2


def test_executed_equivalence_can_clear_expression_disagreement_but_not_source_question(tmp_path):
    _,case,public,_=data();reading=deepcopy(case['reference']['binding_reading'])
    reading['questions']=[];rival=deepcopy(reading);rival['local_id']='reordered'
    rival['formalization']['result']='(and hong_kong business regulated)'
    merged=merge_hypotheses({'reader':{'readings':[reading,rival],'vocabulary_concerns':[],
        'questions':[]}},public['issue'],public['packet'],public['at'])
    compared=distinguish(public['issue'],public['packet'],merged['candidates'],Comparisons(tmp_path,JDK,public['at']))
    assert len(compared['behavior_groups'])==1 and merged['distinct_encoded_expressions']==2
    reviews={'critic':{'judgments':[{'judgment':'SUPPORTED_READING','unresolved_question':None}],
        'missed_readings':[],'vocabulary_concerns':[],'questions':[]}}
    assert reconsideration_required(reviews,merged)
    assert not reconsideration_required(reviews,merged,behavior_groups=1)
    next(iter(merged['candidates'].values()))['questions']=['Is the supplied definition adequate?']
    assert reconsideration_required(reviews,merged,behavior_groups=1)


def test_local_verification_cannot_complete_after_issue_deadline(tmp_path,monkeypatch):
    import legalmath.interpretation.assurance.declared_evaluation as implementation
    from legalmath.errors import LegalMathError
    _,case,public,_=data();reading=deepcopy(case['reference']['binding_reading'])
    class Provider:
        routing={'provider':'fixture'}
    method=MethodRun(tmp_path/'late',public,Provider(),tmp_path/'unused-ledger',JDK,deadline_seconds=30)
    monkeypatch.setattr(method,'generate',lambda *a,**k:{'reader':{
        'readings':[reading],'questions':[],'vocabulary_concerns':[]}})
    def late_verification(*args,**kwargs):
        monkeypatch.setattr(implementation,'monotonic',lambda:method.deadline+1)
        return {'java_cases':64,'behavior_groups':[['reading']]}
    monkeypatch.setattr(implementation,'distinguish',late_verification)
    with pytest.raises(LegalMathError) as error:method.execute('single-reader')
    assert error.value.code=='E_RESOURCE_LIMIT'
    assert not (tmp_path/'late/result.json').exists()
