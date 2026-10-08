from copy import deepcopy
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.authority_arguments import evaluate
from legalmath.interpretation.assurance.meaning_bridges import frame, compare_models
from legalmath.interpretation.search.formal import Comparisons
from tests.search.test_formal import AT
from .support import packet
from .test_repair import mapped_pair


def authority_fixture():
    p=packet();e=[{'unit_id':p['units'][0]['unit_id'],'quote':p['units'][0]['text']}]
    a={'authority_id':'a','source_kind':'FAQ','proposition':'A declared synthetic rule',
       'text_role':'OFFICIAL_ANSWER','role_basis':e,'jurisdiction':'Hong Kong','actor_class':'Distributor',
       'relevant_factors':['gift'],'applicability':'PROPOSED_APPLICABLE','applicability_basis':e,
       'effective_from':'2020-01-01','effective_until':None,'temporal_basis':e,
       'treatment':'NO_TREATMENT_ESTABLISHED','treatment_basis':[],'assumptions':['Fixture dates are declared, not legal evidence.']}
    return p,{'authorities':[a],'priorities':[],'unresolved':[]}


@pytest.mark.parametrize('field,value,reason',[
 ('text_role','SUBMISSION','NON_OPERATIVE_TEXT'),('actor_class','Manager','CONTEXT_MISMATCH'),
 ('jurisdiction','Another jurisdiction','CONTEXT_MISMATCH'),('effective_from','2099-01-01','OUTSIDE_DECLARED_INTERVAL'),
 ('applicability','UNRESOLVED','APPLICABILITY_UNRESOLVED'),('effective_from',None,'EFFECTIVENESS_UNRESOLVED')])
def test_authentic_quote_cannot_override_inapplicable_authority(field,value,reason):
    p,v=authority_fixture();v['authorities'][0][field]=value
    r=evaluate(v,p,at=AT,jurisdiction='Hong Kong',actor_class='Distributor')
    assert reason in r['findings'][0]['reasons'] and not r['conditionally_eligible']
    assert not r['binding_legal_priority_established'] and not r['pruned_interpretations']


def test_priority_cycle_and_unsourced_treatment_retained():
    p,v=authority_fixture();b=deepcopy(v['authorities'][0]);b['authority_id']='b';v['authorities'].append(b)
    evidence=b['role_basis']
    v['priorities']=[{'priority_id':a+b,'preferred':a,'displaced':b,'rationale':'Synthetic priority',
                     'evidence':evidence,'premise_status':'SOURCE_EXPRESS'} for a,b in [('a','b'),('b','a')]]
    r=evaluate(v,p,at=AT,jurisdiction='Hong Kong',actor_class='Distributor')
    assert any('PRIORITY_CYCLE' in f['reasons'] for f in r['findings'])
    v['authorities'][0]['treatment']='OVERRULED'
    with pytest.raises(LegalMathError):evaluate(v,p,at=AT,jurisdiction='Hong Kong',actor_class='Distributor')


def bridge_fixture():
    a,b,m=mapped_pair()
    def model(r,actors):return {'actors':actors,'objects':['gift'],'unit_of_assessment':'one offer',
         'temporal_basis':'declared assessment time','reading':r}
    left,right=model(a,['Distributor','Offer recipient']),model(b,['Distributor'])
    value={'profile':'meaning-bridge.v1','left_schema_hash':digest(left),'right_schema_hash':digest(right),
           'source_packet_hash':digest(packet()),'left_frame':frame(left),'right_frame':frame(right),
           'mapping':m,'frame_assumptions':['The recipient of the same offer is implicit in the right schema.'],
           'evidence':m['evidence'],'semantic_status':'PROPOSED_CONDITIONAL_MAPPING'}
    return left,right,value


def test_missing_actor_is_preserved_even_when_mapped_java_agrees(root,tmp_path):
    a,b,m=bridge_fixture();checker=Comparisons(tmp_path,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT)
    r=compare_models(a,b,packet(),m,checker)
    assert r['comparison']['status']=='CONDITIONAL_EQUIVALENT_IN_DECLARED_DOMAIN'
    assert r['changed_frame_dimensions']==['actors'] and r['unresolved_premises']
    assert not r['legal_equivalence_established']


def test_absent_partial_stale_or_unjustified_mapping_never_becomes_agreement():
    a,b,m=bridge_fixture()
    assert compare_models(a,b,packet(),None,None)['status']=='INCOMPARABLE_ABSTRACTIONS'
    m['frame_assumptions']=[]
    with pytest.raises(LegalMathError):compare_models(a,b,packet(),m,None)
    a['temporal_basis']='changed cutoff'
    with pytest.raises(LegalMathError):compare_models(a,b,packet(),m,None)
