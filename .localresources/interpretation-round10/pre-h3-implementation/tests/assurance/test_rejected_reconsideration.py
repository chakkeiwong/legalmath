"""A structural repair may change meaning; the discarded proposal needs review."""
from copy import deepcopy
from legalmath.canonical import digest
from legalmath.interpretation.assurance.declared_evaluation import MethodRun
from legalmath.interpretation.search.providers import Allowance,Completion
from tests.assurance.test_declared_evaluation import data,JDK


def test_rejected_alternative_is_supplied_unchanged_to_semantic_reviser(tmp_path):
    _,case,public,_=data();reading=deepcopy(case['reference']['binding_reading'])
    reading['questions']=[]
    rejected=deepcopy(reading);rejected['local_id']='rejected-alternative'
    rejected['formalization']['scope']='This is prose rather than an expression'
    rejected['formalization']['result']='(or regulated business hong_kong)'
    reconstructed=deepcopy(rejected);reconstructed['formalization']['scope']='true'
    ledger=tmp_path/'allowance.json';allowance=Allowance(ledger,100,reservation_ceiling=24)
    requests=[];revisers=[]
    class Provider:
        provider_id='test.rejected-branch';live=True;routing={'provider':'fixture','model':'semantic-change'}
        def complete(self,request,schema,settings):
            requests.append(request);slot=allowance.reserve(digest(request))
            if len(requests)==1:
                answer={'readings':[rejected],'vocabulary_concerns':[],'questions':[]}
            elif request['task'] in ('ISSUE_HYPOTHESES','REPAIR_OUTPUT'):
                readings=[reading]
                if request.get('role')=='discrepancy-reviser':
                    revisers.append(request)
                    readings=[reading,reconstructed]
                answer={'readings':readings,'vocabulary_concerns':[],'questions':[]}
            else:
                answer={'judgments':[{'candidate_id':cid,'judgment':'SUPPORTED_READING',
                    'source_evidence':reading['citations'],'rationale':'Controlled supporting criticism.',
                    'unresolved_question':None} for cid in request['required_candidate_ids']],
                    'missed_readings':[],'vocabulary_concerns':[],'questions':[]}
            return Completion(answer,{'provider':self.provider_id,'fresh_context':True,
                'request_hash':digest(request),'response_hash':digest(answer),
                'allowance_slot':slot,'provider_route_hash':digest(self.routing)})
    result=MethodRun(tmp_path/'method',public,Provider(),ledger,JDK).execute('assurance')
    assert result['cycles']==1 and len(revisers)==1
    history=revisers[0]['prior_hypotheses']['rejected_proposals']
    assert history['records'][0]['original_reading']==rejected
    assert not history['semantic_edits_performed']
    assert result['invalid_proposals']['records'][0]['original_reading']==rejected
    assert result['behavior_groups']==2 and result['task_attempts']==7
