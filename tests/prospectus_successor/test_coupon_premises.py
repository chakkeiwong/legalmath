"""Exact input visibility and mutation isolation at actual coupon consumers."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from scripts.prospectus_closure_fixtures import (coupon_scenario, anchored_direct_fixture,
    anchored_selected_fixture, full_term_fixture, request)
from legalmath.prospectus.successor import contract_assembly, contract_terms, service, source_graph
from legalmath.prospectus.successor.fixed_coupon import calculate

ROOT = Path(__file__).resolve().parents[2]

def build(tmp_path, version):
    if version == 1:
        return coupon_scenario(tmp_path)
    if version == 2:
        req = anchored_direct_fixture(tmp_path)
        return source_graph.build(req['bundle'], tmp_path), req['financial_scenario']
    folder = ROOT/'docs/implementation/prospectus-execution-authority/attempts/finance-conventions/attempt-002'
    req = json.loads((folder/'direct-definitive-request.json').read_text())
    return source_graph.build(req['bundle'], ROOT), req['financial_scenario']

@pytest.mark.parametrize('version', [1,2,3])
@pytest.mark.parametrize('entitled', [True,False])
def test_complete_exact_validated_scenario_survives_output(tmp_path, version, entitled):
    graph, scenario = build(tmp_path, version)
    for row in scenario['holdings']:row['entitled'] = entitled
    # Input event order is retained exactly; the separately reported event
    # chronology is sorted by its existing rules. No silent normalization.
    scenario['events'].reverse()
    before = deepcopy(scenario)
    result = calculate(scenario, graph)
    assert result['calculation_inputs'] == before == scenario
    assert result['source_evidence'] == before['evidence']
    assert result['actual_event'] == 'NOT_ESTABLISHED'
    assert not result['full_settlement_supported']
    assert not result['entitlement_basis']['legal_entitlement_established']
    if not entitled:assert result['transfers'] == []

@pytest.mark.parametrize('version', [1,2,3])
def test_input_and_result_nested_values_are_detached(tmp_path, version):
    graph, scenario = build(tmp_path, version)
    original = deepcopy(scenario)
    result = calculate(scenario, graph)
    expected = deepcopy(result)
    scenario['events'][0]['id'] = 'changed-input'
    scenario['evidence']['currency']['source']['quote'] = 'changed-input'
    scenario['calendar']['holidays'].append('1900-01-01')
    scenario['holdings'][0]['principal'] = 'changed-input'
    scenario['rounding']['quantum'] = 'changed-input'
    scenario['references'].clear()
    assert result == expected
    scenario = deepcopy(original)
    result = calculate(scenario, graph)
    result['events'][0]['id'] = 'changed-output'
    result['source_evidence']['currency']['source']['quote'] = 'changed-output'
    result['calculation_inputs']['calendar']['holidays'].append('1900-01-01')
    result['calculation_inputs']['evidence']['currency']['reason'] = 'changed-output'
    assert scenario == original

@pytest.mark.parametrize('selected', [False,True])
def test_exact_premises_reach_real_current_and_frozen_consumers(tmp_path, selected):
    req = (anchored_selected_fixture if selected else anchored_direct_fixture)(tmp_path)
    ps = {'P1': service.source_product(req,tmp_path)}
    ps['P2'] = service.construction_product(ps['P1'],tmp_path)
    ps['P3'] = service.interpretation_product(ps['P1'],ps['P2'])
    ps['P4'] = service.law_product(ps['P1'],ps['P3'])
    ps['P5'] = service.financial_product(ps['P1'],ps['P2'],ps['P3'])
    expected = deepcopy(req['contract_calculation']['premises'] if selected else req['financial_scenario'])
    if selected:
        for key,row in ps['P3']['payload']['contract_terms']['terms'].items():
            if key in ('issue_principal','maturity_date'):continue
            expected[key] = deepcopy(row['value'])
            expected['evidence'][key] = {'source':deepcopy(row['source']),'reason':row['reason']}
    reports = [service.consume(ps,tmp_path,mode=mode) for mode in ('frozen','current')]
    for answer in reports:
        q = answer['questions']['Q5']
        assert q['status'] == 'CONDITIONAL'
        result = q['value']['calculation'] if selected else q['value']
        assert result['calculation_inputs'] == expected
        assert result['day_fraction'] == '1/2'
        assert not answer['may_execute_transaction']
    assert reports[0]['questions'] == reports[1]['questions']

@pytest.mark.parametrize('field', ['calendar','rounding','events'])
def test_missing_premises_do_not_become_a_reported_calculation(tmp_path, field):
    graph, scenario = coupon_scenario(tmp_path)
    req = request(tmp_path,[u['raw'] for u in graph['units']])
    req['financial_scenario'] = scenario
    scenario.pop(field)
    answer = service.assess(req,tmp_path)['questions']['Q5']
    assert answer['status'] == 'UNSUPPORTED'
    assert 'calculation_inputs' not in (answer.get('value') or {})
