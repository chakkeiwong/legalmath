"""Independent payable-amount counterexample and admitted schedule boundaries."""
from copy import deepcopy
from fractions import Fraction
import pytest
from scripts.prospectus_closure_fixtures import coupon_scenario, full_term_fixture, request, term_fixture
from legalmath.prospectus.successor import contract_assembly, contract_terms, service, source_graph
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.fixed_coupon import calculate, rounded
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


def test_excluded_accounts_survive_answer_without_entitlement_inference(tmp_path):
    graph, scenario = coupon_scenario(tmp_path)
    for row in scenario['holdings']:
        row['entitled'] = False
    result = calculate(scenario, graph)
    assert result['transfers'] == []
    basis = result['entitlement_basis']
    assert basis['holdings'] == scenario['holdings']
    assert basis['excluded_accounts'] == [row['account_id'] for row in scenario['holdings']]
    assert not basis['legal_entitlement_established']
    assert not basis['transfer_effects_inferred'] and not basis['note_form_inferred']
    scenario['holdings'][0]['entitled'] = True
    scenario['event_scope']['record'] = 'NOT_APPLICABLE'
    assert basis['holdings'][0]['entitled'] is False
    assert basis['event_scope']['record'] == 'REQUIRED'


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


@pytest.mark.parametrize("value", [None, False, True, 0, 1, 1.5, [], {}, "", " \t "])
@pytest.mark.parametrize("field", ["legal_holder_id", "account_id", "event_id"])
def test_coupon_rejects_nontext_or_blank_identity(tmp_path, field, value):
    graph, scenario = coupon_scenario(tmp_path)
    if field == "event_id":
        scenario["events"][0]["id"] = value
    else:
        scenario["holdings"][0][field] = value
    with pytest.raises(ValueError, match="Nonblank string .*identifier"):
        calculate(scenario, graph)


def test_coupon_text_holders_remain_distinct_and_same_holder_accounts_aggregate(tmp_path):
    graph, scenario = coupon_scenario(tmp_path)
    scenario["holdings"] = [
        {"legal_holder_id": "true", "account_id": "a", "principal": "50", "entitled": True},
        {"legal_holder_id": "1", "account_id": "b", "principal": "50", "entitled": True},
        {"legal_holder_id": "true", "account_id": "c", "principal": "50", "entitled": True},
    ]
    value = calculate(scenario, graph)
    assert [r["legal_holder_id"] for r in value["transfers"]] == ["1", "true"]
    assert [r["amount"] for r in value["transfers"]] == ["5/2", "5"]
    assert value["entitlement_basis"]["holdings"] == scenario["holdings"]
    scenario["holdings"][0]["legal_holder_id"] = True
    scenario["holdings"][1]["legal_holder_id"] = 1
    with pytest.raises(ValueError, match="Nonblank string .*identifier"):
        calculate(scenario, graph)


def test_coupon_text_identifiers_are_not_silently_normalized(tmp_path):
    graph, scenario = coupon_scenario(tmp_path)
    row = deepcopy(scenario["holdings"][0])
    row.update(legal_holder_id=" holder ", account_id=" account ")
    scenario["holdings"] = [row]
    scenario["events"][-1]["id"] = " payment "
    value = calculate(scenario, graph)
    assert value["transfers"][0]["legal_holder_id"] == " holder "
    assert value["transfers"][0]["payment_event"] == " payment "
    assert value["entitlement_basis"]["holdings"] == [row]


@pytest.mark.parametrize('field,invalid', [
    *[('quantum', value) for value in [0, -1, '0', '-0.01', '1/0', True, 0.1, None, '', 'NaN', [], {}]],
    *[('rule', value) for value in ['HALF_EVEN', '', None, 0, True, [], {}]],
])
@pytest.mark.parametrize('entitled', [True, False])
@pytest.mark.parametrize('aggregation', ['PER_LEGAL_HOLDER', 'PER_CALCULATION_AMOUNT'])
def test_coupon_rounding_domain_independent_of_entitlement(tmp_path, field, invalid, entitled, aggregation):
    graph, scenario = coupon_scenario(tmp_path)
    scenario['rounding']['aggregation'] = aggregation
    if aggregation == 'PER_CALCULATION_AMOUNT':
        scenario['calculation_amount'] = '100.1'
        scenario['evidence']['calculation_amount'] = deepcopy(scenario['evidence']['currency'])
    for row in scenario['holdings']:
        row['entitled'] = entitled
    assert calculate(scenario, graph)['entitlement_basis']['holdings'] == scenario['holdings']
    scenario['rounding'][field] = invalid
    before = deepcopy(scenario)
    with pytest.raises(ValueError, match='rounding'):
        calculate(scenario, graph)
    assert scenario == before


@pytest.mark.parametrize('quantum', [1, '0.01', '1/100', Fraction(1, 100)])
@pytest.mark.parametrize('rule', ['HALF_UP', 'DOWN'])
@pytest.mark.parametrize('aggregation', ['PER_LEGAL_HOLDER', 'PER_CALCULATION_AMOUNT'])
def test_coupon_valid_rounding_keeps_excluded_accounts(tmp_path, quantum, rule, aggregation):
    graph, scenario = coupon_scenario(tmp_path)
    scenario['rounding'].update(quantum=quantum, rule=rule, aggregation=aggregation)
    if aggregation == 'PER_CALCULATION_AMOUNT':
        scenario['calculation_amount'] = '100.1'
        scenario['evidence']['calculation_amount'] = deepcopy(scenario['evidence']['currency'])
    for row in scenario['holdings']:
        row['entitled'] = False
    before = deepcopy(scenario)
    result = calculate(scenario, graph)
    assert result['transfers'] == []
    assert result['entitlement_basis']['holdings'] == before['holdings']
    assert result['entitlement_basis']['excluded_accounts'] == ['a1', 'a2', 'b1']
    assert not result['entitlement_basis']['legal_entitlement_established']
    assert not result['full_settlement_supported']
    assert scenario == before


@pytest.mark.parametrize('field,invalid', [('quantum', 0), ('quantum', '1/0'), ('rule', [])])
@pytest.mark.parametrize('entitled', [True, False])
@pytest.mark.parametrize('aggregation', ['PER_LEGAL_HOLDER', 'PER_CALCULATION_AMOUNT'])
@pytest.mark.parametrize('selected', [False, True])
def test_coupon_rounding_refusal_at_actual_consumers(tmp_path, field, invalid, entitled, aggregation, selected):
    if selected:
        req = (full_term_fixture if aggregation == 'PER_CALCULATION_AMOUNT' else term_fixture)(tmp_path)
        supplied = req['contract_calculation']['premises']
        rounding = req['term_interpretations']['terms']['rounding']['value']
    else:
        graph, supplied = coupon_scenario(tmp_path)
        req = request(tmp_path, [u['raw'] for u in graph['units']])
        req['financial_scenario'] = supplied
        rounding = supplied['rounding']
        rounding['aggregation'] = aggregation
        if aggregation == 'PER_CALCULATION_AMOUNT':
            supplied['calculation_amount'] = '100.1'
            supplied['evidence']['calculation_amount'] = deepcopy(supplied['evidence']['currency'])
    for row in supplied['holdings']:
        row['entitled'] = entitled
    assert service.assess(req, tmp_path)['questions']['Q5']['status'] == 'CONDITIONAL'
    rounding[field] = invalid
    if selected:
        graph = source_graph.build(req['bundle'], tmp_path)
        assembly = contract_assembly.assemble(graph, req['assembly'])
        req['contract_calculation']['terms_sha256'] = digest(contract_terms.admit(graph, assembly, req['term_interpretations']))
    before = deepcopy(req)
    if selected:
        with pytest.raises(ValueError, match='rounding'):
            service.assess(req, tmp_path)
    else:
        answer = service.assess(req, tmp_path)['questions']['Q5']
        assert answer['status'] == 'UNSUPPORTED'
        assert 'rounding' in ' '.join(answer['unresolved'])
    assert req == before


@pytest.mark.parametrize('value,quantum,rule,expected', [
    ('1.0049', '0.01', 'HALF_UP', Fraction(1)),
    ('1.005', '0.01', 'HALF_UP', Fraction(101, 100)),
    ('1.0051', '0.01', 'HALF_UP', Fraction(101, 100)),
    ('1.005', '0.01', 'DOWN', Fraction(1)),
    (Fraction(3, 2), 1, 'HALF_UP', Fraction(2)),
    ('3/2', 1, 'DOWN', Fraction(1)),
    (0, Fraction(1, 100), 'HALF_UP', Fraction(0)),
])
def test_coupon_rounding_exact_tie_and_nonmutation(tmp_path, value, quantum, rule, expected):
    assert rounded(value, quantum, rule) == expected
    graph, scenario = coupon_scenario(tmp_path)
    before, graph_before = deepcopy(scenario), deepcopy(graph)
    result = calculate(scenario, graph)
    # 200.20 * 5% = 10.010 and 100.10 * 5% = 5.005, rounded once per holder.
    assert [row['amount'] for row in result['transfers']] == ['1001/100', '501/100']
    assert scenario == before and graph == graph_before
