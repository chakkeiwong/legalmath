"""Malformed fractions must not escape the public financial refusal interface."""
from copy import deepcopy
from fractions import Fraction
import pytest
from legalmath.prospectus.semantics import exact
from legalmath.prospectus.successor import financial_profiles, fixed_coupon, contract_terms
from scripts.prospectus_closure_fixtures import coupon_scenario


@pytest.mark.parametrize('value', ['1/0', '-2/0', '0/0', '1/00'])
def test_zero_denominators_are_invalid_quantities(value):
    with pytest.raises(ValueError, match='nonzero denominator'): exact(value)


@pytest.mark.parametrize('value,expected', [(0, (0, 1)), ('1/2', (1, 2)), ('0.125', (1, 8)),
    ('-7/3', (-7, 3)), ('1e-3', (1, 1000)), (Fraction(3, 7), (3, 7))])
def test_valid_representations_keep_their_exact_value(value, expected):
    actual = exact(value)
    assert (actual.numerator, actual.denominator) == expected


@pytest.mark.parametrize('value', [0.0, 0.5, True, False])
def test_inexact_and_boolean_inputs_remain_refused(value):
    with pytest.raises(ValueError): exact(value)


@pytest.mark.parametrize('field', ['annual_rate', 'principal', 'calculation_amount', 'fixed_coupon_amount'])
@pytest.mark.parametrize('entitled', [True, False])
def test_direct_public_consumer_refuses_even_excluded_holder(tmp_path, field, entitled):
    graph, scenario = coupon_scenario(tmp_path)
    for row in scenario['holdings']: row['entitled'] = entitled
    if field == 'principal': scenario['holdings'][0]['principal'] = '1/0'
    elif field in ('calculation_amount', 'fixed_coupon_amount'):
        scenario.update(calculation_amount='100.1')
        scenario['rounding']['aggregation'] = 'PER_CALCULATION_AMOUNT'
        scenario['evidence']['calculation_amount'] = deepcopy(scenario['evidence']['currency'])
        scenario[field] = '1/0'
        scenario['evidence'][field] = deepcopy(scenario['evidence']['currency'])
    else: scenario[field] = '1/0'
    before = deepcopy(scenario)
    with pytest.raises(ValueError, match='nonzero denominator'): fixed_coupon.calculate(scenario, graph)
    result = financial_profiles.assess({'instrument_id': graph['instrument_id']}, scenario, graph)
    assert result['status'] == 'UNSUPPORTED'
    assert any('nonzero denominator' in reason for reason in result['unresolved'])
    assert scenario == before


@pytest.mark.parametrize('field', ['issue_principal', 'calculation_amount', 'fixed_coupon_amount', 'broken_coupon_amount'])
def test_selected_v4_amount_refusal_is_a_validation_error(field):
    # The real source-bound v4 packets are exercised by the admitted runner.
    from scripts.prospectus_exact_quantity import selected_v4_packet
    graph, assembly, packet = selected_v4_packet()
    packet['terms'][field]['value'] = '1/0'
    with pytest.raises(ValueError, match='nonzero denominator'):
        contract_terms.admit(graph, assembly, packet)
