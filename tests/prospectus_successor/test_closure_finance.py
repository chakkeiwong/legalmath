"""Independent payable-amount counterexample and admitted schedule boundaries."""
from copy import deepcopy
import pytest
from scripts.prospectus_closure_fixtures import coupon_scenario, full_term_fixture
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.fixed_coupon import calculate
from legalmath.prospectus.successor.contract_terms import regular_schedule


def test_calculation_amount_rounding_differs_from_holder_rounding(tmp_path):
    graph, scenario = coupon_scenario(tmp_path)
    assert calculate(scenario, graph)['transfers'][0]['amount'] == '1001/100'
    scenario['rounding']['aggregation'] = 'PER_CALCULATION_AMOUNT'
    scenario['calculation_amount'] = '100.1'
    scenario['evidence']['calculation_amount'] = deepcopy(scenario['evidence']['currency'])
    assert calculate(scenario, graph)['transfers'][0]['amount'] == '501/50'
    scenario['holdings'][0]['principal'] = '100'
    with pytest.raises(ValueError, match='integral'):
        calculate(scenario, graph)


def test_published_amount_checked_without_entitled_holders(tmp_path):
    graph, scenario = coupon_scenario(tmp_path)
    scenario.update(calculation_amount='100.1', fixed_coupon_amount='6')
    scenario['rounding']['aggregation'] = 'PER_CALCULATION_AMOUNT'
    for key in ('calculation_amount', 'fixed_coupon_amount'):
        scenario['evidence'][key] = deepcopy(scenario['evidence']['currency'])
    for row in scenario['holdings']:
        row['entitled'] = False
    with pytest.raises(ValueError, match='Published fixed coupon'):
        calculate(scenario, graph)


def test_explicit_bearer_scenario_does_not_invent_register_date(tmp_path):
    graph, scenario = coupon_scenario(tmp_path)
    scenario['event_scope']['record'] = 'NOT_APPLICABLE'
    scenario['events'] = [e for e in scenario['events'] if e['kind'] != 'record']
    assert calculate(scenario, graph)['transfers'][0]['amount'] == '1001/100'
    scenario['event_scope']['record'] = 'REQUIRED'
    with pytest.raises(ValueError, match='record'):
        calculate(scenario, graph)


def test_selected_full_terms_reach_service_and_bind_principal_dates(tmp_path):
    req = full_term_fixture(tmp_path)
    answer = service.assess(req, tmp_path)['questions']['Q5']
    assert answer['status'] == 'CONDITIONAL'
    assert answer['value']['regular_due_dates'] == ['2025-01-01', '2026-01-01']
    assert [t['amount'] for t in answer['value']['calculation']['transfers']] == ['501/50', '501/100']
    for key,value in [('issue_principal','2000'), ('accrual_end','2025-02-01'), ('annual_rate','0.06')]:
        changed = deepcopy(req)
        changed['term_interpretations']['terms'][key]['value'] = value
        with pytest.raises(ValueError, match='differs'):
            service.assess(changed, tmp_path)
    req['contract_calculation']['premises']['holdings'][0]['principal'] = '1001'
    with pytest.raises(ValueError, match='exceed'):
        service.assess(req, tmp_path)


def test_regular_schedule_month_end_anchor_and_stub_rejection():
    assert regular_schedule('2024-02-29','2024-08-31','2025-08-31',2,True,'REGULAR') == [
        '2024-08-31','2025-02-28','2025-08-31']
    assert regular_schedule('2023-08-30','2024-02-29','2024-08-30',2,False,'REGULAR') == [
        '2024-02-29','2024-08-30']
    for first,maturity in [('2024-08-30','2025-08-31'), ('2024-08-31','2025-07-31')]:
        with pytest.raises(ValueError, match='stub'):
            regular_schedule('2024-02-29',first,maturity,2,True,'REGULAR')
