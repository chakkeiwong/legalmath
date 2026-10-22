from itertools import product
import pytest
from legalmath.prospectus import concert_application as module
from scripts import prospectus_concert_oracle as oracle


@pytest.mark.parametrize('row',oracle.scenarios('bond'),ids=lambda r:r['id'])
def test_source_necessary_conditions_match_independent_oracle(row):
    assert oracle.projection(module.analyze(row,'bond'))==oracle.classify(row)


def test_all_boolean_necessary_patterns_and_applicability():
    count=0
    for values in product((False,True),repeat=7):
        r=oracle.case('finite');r['premises']=dict(zip(oracle.PREMISES,values[:6]));r['reading_applies']=values[6]
        assert oracle.projection(module.analyze(r,'bond'))==oracle.classify(r);count+=1
    assert count==128


def test_voting_alternative_does_not_inherit_business_change_requirements():
    result=module.analyze(oracle.case('voting'),'bond')
    assert result['necessary_conditions']['status']=='YES'
    assert result['sufficient_legal_test'] is False
    assert result['actual_concert']=='NOT_ESTABLISHED'
    assert result['control_premise_supplied'] is False
    r=oracle.case('other');r['premises']['understanding_about_voting']=False;r['premises']['other_cooperation']=True
    assert module.analyze(r,'bond')['necessary_conditions']['status']=='NO'


@pytest.mark.parametrize('kind',['instrument','target','same-person','empty-event','empty-pair',
    'bad-premise','missing-premise','extra-premise','actual-kind','promoted-finding','invalid-applicability'])
def test_unbound_or_promoted_input_refuses(kind):
    r=oracle.case('invalid')
    if kind=='instrument':r['pair']['instrument_id']='other'
    elif kind=='target':r['pair']['target']='OTHER'
    elif kind=='same-person':r['pair']['right_person']=r['pair']['left_person']
    elif kind=='empty-event':r['pair']['control_event_id']=''
    elif kind=='empty-pair':r['pair']['pair_id']=''
    elif kind=='bad-premise':r['premises'][oracle.PREMISES[0]]=1
    elif kind=='missing-premise':del r['premises'][oracle.PREMISES[0]]
    elif kind=='extra-premise':r['premises']['control_put.control']=True
    elif kind=='actual-kind':r['kind']='ACTUAL'
    elif kind=='promoted-finding':r['actual_concert']=True
    else:r['reading_applies']=1
    with pytest.raises(ValueError):module.analyze(r,'bond')
