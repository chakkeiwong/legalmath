from copy import deepcopy
from itertools import product
import pytest
from scripts import prospectus_affiliate_oracle as oracle
from legalmath.prospectus import affiliate_substitution as module


@pytest.mark.parametrize('row',oracle.scenarios('test'),ids=lambda r:r['id'])
def test_independent_complete_conditions(row):
    actual=module.analyze(row,'test')
    for key,value in oracle.expected(row).items():assert actual[key]['status']==value
    assert actual['actual_substitution']=='NOT_ESTABLISHED' and not actual['complete_legal_test']
    assert actual['onward_notice_and_document_duties']=='SEPARATE_REQUIREMENTS_NOT_DISCHARGED'


def test_exhaustive_four_valued_affiliate_alternatives():
    count=0
    for values in product((True,False,None,'conflict'),repeat=6):
        premises=dict(zip(oracle.AFFILIATE,values))
        assert module.affiliation(premises)['status']==oracle.affiliation(premises);count+=1
    assert count==4096


@pytest.mark.parametrize('attack',('same-company','wrong-instrument','empty-event','actual','parent-label',
    'affiliate-override','missing-confirmation','missing-guarantee','numeric-boolean','raw-stake'))
def test_unsupported_shortcuts_refused(attack):
    row=deepcopy(oracle.scenarios('test')[1])
    if attack=='same-company':row['identity']['successor']=row['identity']['issuer']
    elif attack=='wrong-instrument':row['identity']['instrument_id']='other'
    elif attack=='empty-event':row['identity']['substitution_event_id']=''
    elif attack=='actual':row['kind']='ACTUAL_EVENT'
    elif attack=='parent-label':row['affiliate_categories']['parent_company']=True
    elif attack=='affiliate-override':row['affiliate']=True
    elif attack=='missing-confirmation':row['prerequisites'].pop('required_lawyer_confirmations_received_by_fiscal_agent')
    elif attack=='missing-guarantee':row['prerequisites'].pop('programme_guarantee_extended')
    elif attack=='numeric-boolean':row['issuer_elected']=1
    else:row['affiliate_categories']['majority_relation_section16']='51%'
    with pytest.raises(ValueError):module.analyze(row,'test')
