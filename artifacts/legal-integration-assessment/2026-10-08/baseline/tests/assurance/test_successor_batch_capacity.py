"""A larger batch retains all rows, perspectives, follow-ups and spent actions."""
from copy import deepcopy
import pytest
from legalmath.interpretation.assurance.scoped_investigation import investigate
from legalmath.interpretation.search.providers import Completion
from .test_round16 import scoped_fixture


def test_thirty_two_pair_batches_preserve_the_remainder_and_followup(tmp_path):
    packet,claims,candidates,questions,answer=scoped_fixture()
    claims=[{**deepcopy(claims[0]),'claim_id':'claim.'+str(i)} for i in range(65)]
    class Provider:
        live=False;provider_id='scripted.capacity';routing={'synthetic':True}
        def __init__(self):self.requests=[]
        def complete(self,request,schema,settings):
            self.requests.append(request)
            rows=[]
            for pair in request['required_pairs']:
                row=deepcopy(answer['checks'][0]);row.update(pair)
                row['followup_questions']=['A controlled unresolved premise requires the second round.']
                rows.append(row)
            return Completion({'checks':rows,'additional_concerns':[]},{'synthetic':True})
    provider=Provider();out=tmp_path/'scoped'
    result=investigate(packet,claims,candidates,questions,provider,out,
                       batch_size=32,maximum_rounds=2,maximum_actions=12)
    assert [len(b['required_pairs']) for b in result['batches']]==[32,32,1]
    assert result['pairs_with_two_validated_proposals']==65
    assert not result['pending_pairs'] and result['stopped'] is None
    assert len(provider.requests)==12
    assert all(len(b['attempts'])==4 for b in result['batches'])
    assert all(b['reconciliation']['status']=='UNCERTAINTY_REPORTED' for b in result['batches'])
    investigate(packet,claims,candidates,questions,provider,out,
                batch_size=32,maximum_rounds=2,maximum_actions=12)
    assert len(provider.requests)==12


@pytest.mark.parametrize('batch_size',[12,24])
def test_candidate_partition_preserves_full_cartesian_matrix_and_followups(tmp_path,batch_size):
    packet,claims,candidates,questions,answer=scoped_fixture()
    claims=[{**deepcopy(claims[0]),'claim_id':'claim.'+str(i)} for i in range(13)]
    candidates={f'candidate.{i}':deepcopy(candidates['candidate']) for i in range(3)}
    questions={k:deepcopy(questions['candidate']) for k in candidates}
    requests=[]
    class Provider:
        live=False;provider_id='scripted.partition';routing={'synthetic':True}
        def complete(self,request,schema,settings):
            requests.append(request);rows=[]
            for pair in request['required_pairs']:
                r=deepcopy(answer['checks'][0]);r.update(pair)
                r['followup_questions']=['Retain the controlled unresolved premise.'];rows.append(r)
            return Completion({'checks':rows,'additional_concerns':[]},{'synthetic':True})
    result=investigate(packet,claims,candidates,questions,Provider(),tmp_path,
        batch_size=batch_size,maximum_rounds=2,maximum_actions=16,pair_order='candidate-first')
    assert result['stopped'] is None and result['pairs_with_four_dimensions_assessed']==39
    assert set(map(tuple,result['required_pairs']))=={(c['claim_id'],r) for c in claims for r in candidates}
    assert len(requests)==4*((39+batch_size-1)//batch_size) and all(len(r['candidates'])<=2 for r in requests)
    assert all(len(r['source_packet']['units'])==len(packet['units']) for r in requests)
    assert all(len(b['attempts'])==4 for b in result['batches'])
    assert all(b['reconciliation']['status']=='UNCERTAINTY_REPORTED' for b in result['batches'])
