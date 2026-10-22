from copy import deepcopy
from itertools import product
import pytest
from scripts import prospectus_notice_delivery_oracle as oracle
from legalmath.prospectus import notice_delivery as module


@pytest.mark.parametrize('row',oracle.scenarios('test'),ids=lambda r:r['id'])
def test_independent_date_route_and_composed_notice(row):
    actual=module.analyze(row,'test');expected=oracle.expected(row)
    assert actual['route_preconditions']['status']==expected['route']
    assert actual['arithmetic_candidate_date']==expected['date']
    assert actual['notice']['notice_precondition']['status']==expected['notice']
    assert actual['notice']['conditional_notice_precondition']['status']==expected['conditional']
    assert not actual['candidate_date_is_actual_notice'] and not actual['complete_legal_test']


@pytest.mark.parametrize('values',product((True,False,None,'conflict'),repeat=4))
def test_complete_clearing_route_truth_table(values):
    premises=dict(zip(module.PREMISES,values))
    assert module.route_condition('CLEARING_SUBSTITUTION',premises)['status']==oracle.conjunction(list(values))


@pytest.mark.parametrize('attack',('holder-direction','event-id','notice-id','agent','instrument',
    'end-role','route','convention','invalid-date','actual','override','mixed-route','overflow'))
def test_invalid_delivery_inputs_are_refused(attack):
    row=deepcopy(oracle.scenarios('test')[2])
    if attack=='holder-direction':row['event']['role']='HOLDER_TO_FISCAL_AGENT'
    elif attack=='event-id':row['event']['change_event_id']='other'
    elif attack=='notice-id':row['event']['notice_id']='other'
    elif attack=='agent':row['event']['agent_id']='other'
    elif attack=='instrument':row['identity']['instrument_id']='other'
    elif attack=='end-role':row['proposed_change']['role']='PUBLICATION'
    elif attack=='route':row['route']='HOLDER_NOTICE'
    elif attack=='convention':row['convention']='BUSINESS_DAYS'
    elif attack=='invalid-date':row['event']['value']='2024-02-30'
    elif attack=='actual':row['kind']='ACTUAL_EVENT'
    elif attack=='override':row['holders_informed']='2024-01-01'
    elif attack=='mixed-route':row['premises']['exchange_rules_permit']=True
    else:row['event']['value']='9999-12-31'
    with pytest.raises(ValueError):module.analyze(row,'test')


def test_deemed_delay_reverses_naive_window_answer():
    rows={r['id']:r for r in oracle.scenarios('test')}
    for route in ('PUBLICATION','CLEARING_SUBSTITUTION'):
        assert oracle.expected(rows[route+'-naive-30-reverses'])['notice']=='NO'
        assert oracle.expected(rows[route+'-naive-46-reverses'])['notice']=='YES'
