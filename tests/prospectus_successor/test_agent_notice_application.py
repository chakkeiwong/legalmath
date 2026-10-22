from copy import deepcopy
from itertools import product
import pytest
from scripts import prospectus_agent_notice_oracle as oracle
from legalmath.prospectus import agent_notice_application as module


@pytest.mark.parametrize('row', oracle.scenarios('test-instrument'), ids=lambda row:row['id'])
def test_exact_intervals_and_open_world_result(row):
    actual=module.analyze(row,'test-instrument');expected=oracle.expected(row)
    for k in ('notice_precondition','conditional_notice_precondition'):
        assert actual[k]['status']==expected[k]
    assert actual['exact_interval']==expected['exact_interval']
    assert actual['actual_change_effective']=='NOT_ESTABLISHED'
    assert actual['calculation_agent_office']=='UNRESOLVED'
    assert not actual['holders_informed_date_derived']


@pytest.mark.parametrize('values',product((True,False,None,'conflict'),repeat=4))
def test_independent_complete_four_valued_truth_table(values):
    premises=dict(zip(('insolvency','section13_notice','lower','upper'),values))
    assert module.notice_condition(premises)['status']==oracle.condition(premises)


@pytest.mark.parametrize('attack',('instrument','agent','event','publication-role','delivery-role',
    'end-role','convention','date','reverse','actual','numeric-boolean','extra','undeclared-convention'))
def test_invalid_scenario_cannot_supply_a_notice_fact(attack):
    row=deepcopy(oracle.scenarios('test-instrument')[2]);iv=row['interval']
    if attack=='instrument': row['identity']['instrument_id']='other'
    elif attack=='agent': iv['start']['agent_id']='other'
    elif attack=='event': iv['end']['change_event_id']='other'
    elif attack=='publication-role': iv['start']['role']='PUBLICATION'
    elif attack=='delivery-role': iv['start']['role']='CLEARING_DELIVERY'
    elif attack=='end-role': iv['end']['role']='HOLDERS_INFORMED'
    elif attack=='convention': iv['convention']='BUSINESS_DAYS'
    elif attack=='date': iv['end']['value']='2024-02-30'
    elif attack=='reverse': iv['end']['value']='2023-12-31'
    elif attack=='actual': row['kind']='ACTUAL_EVENT'
    elif attack=='numeric-boolean': row['insolvency']=1
    elif attack=='extra': row['effective']=True
    else: iv['convention']=None
    with pytest.raises(ValueError):module.analyze(row,'test-instrument')


def test_independent_boundary_expectations():
    rows={r['id']:r for r in oracle.scenarios('test-instrument')}
    for identity,expected in (('29-civil','NO'),('30-civil','YES'),('45-civil','YES'),('46-civil','NO'),
        ('30-minus-microsecond','NO'),('45-plus-microsecond','NO'),('30-gap-clear-days','NO'),
        ('31-gap-clear-days','YES'),('all-open','UNKNOWN'),('insolvency-exception-without-dates','YES')):
        assert oracle.expected(rows[identity])['notice_precondition']==expected
