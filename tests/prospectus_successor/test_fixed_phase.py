"""Source-bound fixed phase, separate period premises and adverse boundaries."""
from copy import deepcopy
from fractions import Fraction
import pytest
from scripts import prospectus_fixed_phase as retained
from legalmath.prospectus.successor import contract_terms
from legalmath.prospectus.successor.contracts import digest


@pytest.fixture(scope='module')
def fixture():
    request, _, graph, assembly = retained.build_request()
    admitted = contract_terms.admit(graph, assembly, request['term_interpretations'])
    request['contract_calculation']['terms_sha256'] = digest(admitted)
    return request, admitted, graph, assembly


def run(fixture, mutation=None):
    request, admitted, graph, assembly = deepcopy(fixture)
    if mutation:
        mutation(request['contract_calculation'])
    return contract_terms.scenario(admitted, request['contract_calculation'], graph, assembly)


def test_all_six_coupons_include_reset_date_without_a_maturity(fixture):
    result = run(fixture)
    assert [p['due_date'] for p in result['coupon_schedule']] == retained.DUE
    assert [c['payment_date'] for c in result['calculations']] == retained.PAY
    assert [c['day_fraction'] for c in result['calculations']] == ['1/4', '1', '1', '1', '1', '1']
    assert sum(Fraction(c['transfers'][0]['amount']) for c in result['calculations']) == 267750
    assert not result['redemption_inferred'] and not result['full_settlement_supported']
    assert result['floating_phase'] == 'NOT_MODELLED'
    assert 'maturity_date' not in result['contract_terms']['terms']


@pytest.mark.parametrize('key', ['no_call', 'no_cancellation', 'no_conversion', 'no_principal_reduction', 'no_tax'])
@pytest.mark.parametrize('value', [False, None, 1])
def test_all_phase_absence_assumptions_are_explicit_booleans(fixture, key, value):
    with pytest.raises(ValueError, match='absence assumption'):
        run(fixture, lambda c: c['premises']['phase_assumptions'].__setitem__(key, value))


@pytest.mark.parametrize('mutation', [
    lambda c: c['periods'].pop(),
    lambda c: c['periods'].append(deepcopy(c['periods'][-1])),
    lambda c: c['periods'][0].__setitem__('accrual_end', '2026-11-26'),
    lambda c: c['premises'].__setitem__('annual_rate', '1/2'),
    lambda c: c['premises'].__setitem__('premise_kind', 'ACTUAL'),
    lambda c: c.__setitem__('terms_sha256', '0' * 64),
    lambda c: c.__setitem__('version', 'selected-coupon-calculation.v1'),
    lambda c: c['premises']['phase_assumptions'].pop('no_call'),
    lambda c: c['premises']['holdings'][0].__setitem__('principal', '1250000001'),
    lambda c: c['premises']['holdings'][0].pop('principal'),
    lambda c: c['premises']['holdings'].__setitem__(0, None),
    lambda c: c['periods'][2]['events'][0].__setitem__('at', '2026-08-25T00:00:00Z'),
    lambda c: c['periods'][0]['events'][-1].__setitem__('order', 1),
    lambda c: c['premises']['calendar'].__setitem__('valid_until', '2028-11-26'),
    lambda c: c['premises']['evidence']['phase_assumptions']['source'].__setitem__('source_sha256', '0' * 64),
])
def test_unsafe_or_incomplete_phase_packet_is_refused(fixture, mutation):
    with pytest.raises(ValueError):
        run(fixture, mutation)


def test_delaying_first_payment_does_not_change_accrual(fixture):
    def delay(c):
        c['premises']['calendar']['holidays'] = ['2026-11-25']
        c['periods'][0]['payment_date'] = '2026-11-26'
        c['periods'][0]['events'][-1]['at'] = '2026-11-26T00:00:00Z'
    result = run(fixture, delay)
    assert result['calculations'][0]['payment_date'] == '2026-11-26'
    assert result['calculations'][0]['day_fraction'] == '1/4'
    assert result['calculations'][0]['transfers'][0]['amount'] == '12750'


def test_rounding_and_principal_are_validated_even_without_entitlement(fixture):
    request, admitted, graph, assembly = deepcopy(fixture)
    calculation = request['contract_calculation']
    calculation['premises']['holdings'][0]['entitled'] = False
    assert all(c['transfers'] == [] for c in run((request, admitted, graph, assembly))['calculations'])
    admitted['terms']['rounding']['value']['quantum'] = '0'
    calculation['terms_sha256'] = digest(admitted)
    with pytest.raises(ValueError):
        contract_terms.scenario(admitted, calculation, graph, assembly)


def test_excluded_principal_still_counts_against_issue_principal(fixture):
    def over_issue(c):
        c['premises']['holdings'].append({'legal_holder_id': 'excluded', 'account_id': 'excluded',
                                         'principal': '1250000000', 'entitled': False})
    with pytest.raises(ValueError, match='issue principal'):
        run(fixture, over_issue)


@pytest.mark.parametrize('key,value', [('note_form', 'DEFINITIVE'), ('day_count', 'ACT_ACT_ICMA'),
                                     ('fixed_phase_boundary', 'MATURITY'), ('frequency', 2), ('eom', True),
                                     ('fixed_phase_end', '2031-11-26')])
def test_incompatible_selected_phase_domain_is_refused(fixture, key, value):
    request, admitted, graph, assembly = deepcopy(fixture)
    admitted['terms'][key]['value'] = value
    request['contract_calculation']['terms_sha256'] = digest(admitted)
    with pytest.raises(ValueError):
        contract_terms.scenario(admitted, request['contract_calculation'], graph, assembly)


def test_selected_end_must_match_its_quoted_date(fixture):
    request, _, graph, assembly = deepcopy(fixture)
    request['term_interpretations']['terms']['fixed_phase_end']['value'] = '2030-11-25'
    with pytest.raises(ValueError, match='Date differs'):
        contract_terms.admit(graph, assembly, request['term_interpretations'])
