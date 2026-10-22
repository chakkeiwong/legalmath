"""Exact endpoint controls and financial-consumer boundaries for BondBasis."""
from copy import deepcopy
from fractions import Fraction
import pytest
from scripts.prospectus_closure_fixtures import coupon_scenario, term_fixture
from legalmath.prospectus.successor import contract_assembly, contract_terms, service, source_graph
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.fixed_coupon import calculate, year_fraction

CONVENTION = 'THIRTY_360_BOND_BASIS'


@pytest.mark.parametrize('start,end,numerator', [
    ('2026-08-25', '2026-11-25', 90),
    ('2025-01-31', '2025-02-28', 28),
    ('2025-01-29', '2025-03-31', 62),
    ('2025-01-30', '2025-03-31', 60),
    ('2025-01-31', '2025-03-31', 60),
    ('2025-02-28', '2025-03-31', 33),
    ('2024-02-29', '2024-03-31', 32),
    ('2024-01-31', '2024-02-29', 29),
    ('2025-02-28', '2026-02-28', 360),
    ('2025-12-31', '2026-01-31', 30),
    ('2025-01-30', '2025-01-31', 0),
])
def test_endpoint_counts_without_february_adjustment(start, end, numerator):
    assert year_fraction(start, end, CONVENTION, references=[], frequency=1, eom=False) == Fraction(numerator, 360)


@pytest.mark.parametrize('name', ['30/360', '30E/360', 'THIRTY_360_USA', 'BondBasis'])
def test_no_ambiguous_or_unimplemented_alias(name):
    with pytest.raises(ValueError, match='Unsupported'):
        year_fraction('2026-08-25', '2026-11-25', name, references=[], frequency=1, eom=False)


def test_icma_schedule_and_anchor_cannot_silently_select_bond_basis():
    with pytest.raises(ValueError, match='Unexpected reference'):
        year_fraction('2026-08-25', '2026-11-25', CONVENTION,
            references=[{'start': '2026-08-25', 'end': '2027-08-25'}], frequency=1, eom=False)
    with pytest.raises(ValueError, match='anchors'):
        year_fraction('2026-08-25', '2026-11-25', CONVENTION,
            references=[], frequency=1, eom=False, coupon_anchor='2026-11-25')


@pytest.mark.parametrize('start,end', [('2025-01-31', '2025-01-31'), ('2025-02-01', '2025-01-31')])
def test_zero_calendar_interval_is_distinct_from_zero_count(start, end):
    with pytest.raises(ValueError, match='positive accrual'):
        year_fraction(start, end, CONVENTION, references=[], frequency=1, eom=False)


def test_conditional_amount_and_exclusion_are_preserved(tmp_path):
    graph, scenario = coupon_scenario(tmp_path)
    scenario.update(day_count=CONVENTION, references=[], annual_rate='0.051',
        accrual_start='2026-08-25', accrual_end='2026-11-25', due_date='2026-11-25',
        payment_date='2026-11-25', stub='SHORT_FIRST', adjustment='UNADJUSTED')
    scenario['calendar'].update(valid_from='2026-08-25', valid_until='2026-11-26', holidays=[])
    scenario['rounding'].update(quantum='1')
    scenario['holdings'] = [{'legal_holder_id': 'hypothetical', 'account_id': 'declared',
        'principal': '1000000', 'entitled': True}]
    scenario['event_scope']['record'] = 'NOT_APPLICABLE'
    scenario['events'] = [{'id': kind, 'kind': kind, 'at': day + 'T00:00:00Z', 'order': order}
        for kind, day, order in [('accrual_start', '2026-08-25', 0), ('accrual_end', '2026-11-25', 0),
            ('determination', '2026-11-25', 1), ('payment', '2026-11-25', 2)]]
    result = calculate(scenario, graph)
    assert result['day_fraction'] == '1/4' and result['transfers'][0]['amount'] == '12750'
    assert result['actual_event'] == 'NOT_ESTABLISHED' and not result['full_settlement_supported']
    assert not result['entitlement_basis']['legal_entitlement_established']
    scenario['holdings'][0]['entitled'] = False
    assert calculate(scenario, graph)['transfers'] == []
    scenario['premise_kind'] = 'ACTUAL'
    with pytest.raises(ValueError, match='hypothetical'):
        calculate(scenario, graph)


def test_selected_v1_consumes_named_convention_without_inventing_schedule(tmp_path):
    req = term_fixture(tmp_path)
    req['term_interpretations']['terms']['day_count']['value'] = CONVENTION
    req['contract_calculation']['premises']['references'] = []
    graph = source_graph.build(req['bundle'], tmp_path)
    assembly = contract_assembly.assemble(graph, req['assembly'])
    admitted = contract_terms.admit(graph, assembly, req['term_interpretations'])
    req['contract_calculation']['terms_sha256'] = digest(admitted)
    answer = service.assess(req, tmp_path)
    q5 = answer['questions']['Q5']
    assert q5['status'] == 'CONDITIONAL' and q5['value']['regular_due_dates'] is None
    assert q5['value']['calculation']['day_fraction'] == '1'
    assert not answer['independent_legal_acceptance'] and not answer['may_execute_transaction']
    changed = deepcopy(req)
    changed['contract_calculation']['terms_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='binding changed'):
        service.assess(changed, tmp_path)
