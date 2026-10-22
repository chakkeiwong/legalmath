"""Complete source-bound coupon terms and refusal of unsupported assumptions."""
from copy import deepcopy
from fractions import Fraction
import gzip
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import contract_terms
from legalmath.prospectus.successor.contracts import digest


PREP = Path(__file__).resolve().parents[2] / 'docs/implementation/prospectus-execution-authority/reviews/shell-full-coupons-360'
ASSUMPTIONS = ('unchanged_holdings', 'unchanged_note_form', 'no_early_redemption',
               'no_default', 'no_principal_reduction', 'no_tax', 'no_currency_change', 'timely_presentation')


@pytest.fixture(scope='module')
def packets():
    return {name: json.loads(gzip.decompress((PREP / (name + '-packet.json.gz')).read_bytes()))
            for name in json.loads((PREP / 'cases.json').read_text())}


def run(packet):
    return contract_terms.scenario(packet['admitted'], packet['request']['contract_calculation'],
                                   packet['graph'], packet['assembly'])


@pytest.mark.parametrize('name', ['global-plain', 'global-holiday', 'global-excluded',
                                'definitive-plain', 'definitive-holiday', 'definitive-excluded'])
def test_every_coupon_matches_independent_frozen_source_arithmetic(packets, name):
    packet = packets[name]
    result = run(packet)
    assert len(result['calculations']) == 10
    assert [p['due_date'] for p in result['coupon_schedule']] == [f'{y}-12-10' for y in range(2021, 2031)]
    assert result['calculations'][0] == packet['baseline_answer']['questions']['Q5']['value']['calculation']
    for c, expected in zip(result['calculations'], packet['expected']):
        assert c['day_fraction'] == expected['fraction']
        assert c['payment_date'] == expected['payment']
        assert c['calculation_inputs']['references'] == expected['references']
        if expected['excluded']:
            assert c['transfers'] == []
        else:
            assert c['transfers'][0]['amount'] == expected['amount']
    total = sum(Fraction(t['amount']) for c in result['calculations'] for t in c['transfers'])
    assert total == (0 if name.endswith('excluded') else Fraction('51243169.40') if name.startswith('global') else 10249)
    assert result['actual_event'] == 'NOT_ESTABLISHED'
    assert not result['redemption_calculated'] and not result['full_settlement_supported']


@pytest.mark.parametrize('key', ASSUMPTIONS)
@pytest.mark.parametrize('value', [False, None, 1])
def test_each_whole_term_assumption_requires_explicit_true(packets, key, value):
    packet = deepcopy(packets['global-plain'])
    packet['request']['contract_calculation']['premises']['term_assumptions'][key] = value
    with pytest.raises(ValueError, match='assumption'):
        run(packet)


@pytest.mark.parametrize('mutation', [
    lambda c: c['periods'].pop(),
    lambda c: c['periods'].append(deepcopy(c['periods'][-1])),
    lambda c: c['periods'].__setitem__(1, deepcopy(c['periods'][0])),
    lambda c: c['periods'][1].__setitem__('payment_date', '2022-12-10'),
    lambda c: c['periods'][2].__setitem__('events', None),
    lambda c: c['periods'][3]['events'][0].__setitem__('kind', 'unknown'),
    lambda c: c['periods'][4]['events'][0].__setitem__('at', '2024-12-09T00:00:00Z'),
    lambda c: c['periods'][5]['events'][-1].__setitem__('order', 1),
    lambda c: c['periods'][6]['evidence'].pop('events'),
    lambda c: c['periods'][7]['evidence']['payment_date']['source'].__setitem__('source_sha256', '0' * 64),
    lambda c: c['periods'][8].__setitem__('accrual_start', '2029-01-01'),
    lambda c: c['periods'][9]['events'].pop(),
    lambda c: c['premises'].__setitem__('annual_rate', '0.5'),
    lambda c: c['premises'].__setitem__('note_form', 'DEFINITIVE'),
    lambda c: c['premises'].__setitem__('premise_kind', 'ACTUAL'),
    lambda c: c['premises'].__setitem__('profile', 'fixed-coupon.v3'),
    lambda c: c['premises']['term_assumptions'].pop('no_default'),
    lambda c: c['premises']['evidence']['term_assumptions'].__setitem__('reason', ' '),
    lambda c: c['premises']['evidence']['term_assumptions']['source'].__setitem__('source_sha256', '0' * 64),
    lambda c: c['premises']['holdings'][0].__setitem__('principal', '500000001'),
    lambda c: c['premises']['holdings'][0].__setitem__('principal', '-1'),
    lambda c: c['premises']['holdings'][0].pop('principal'),
    lambda c: c['premises']['holdings'].__setitem__(0, None),
    lambda c: c['premises']['calendar'].__setitem__('valid_until', '2030-12-10'),
    lambda c: c.__setitem__('terms_sha256', '0' * 64),
])
def test_incomplete_or_contradictory_period_premises_refuse(packets, mutation):
    packet = deepcopy(packets['global-plain'])
    mutation(packet['request']['contract_calculation'])
    with pytest.raises(ValueError):
        run(packet)


@pytest.mark.parametrize('key,value', [('day_count', 'ACT_ACT_ISDA'), ('frequency', 2),
                                     ('frequency', True), ('eom', True), ('note_form', 'REGISTERED'),
                                     ('adjustment', 'PRECEDING'), ('stub', 'LONG_FINAL'),
                                     ('maturity_date', '2030-12-11'), ('maturity_date', '2020-12-10'),
                                     ('maturity_date', '2621-12-10'), ('due_date', '2021-12-11')])
def test_rehashed_terms_cannot_expand_the_supported_domain(packets, key, value):
    packet = deepcopy(packets['global-plain'])
    packet['admitted']['terms'][key]['value'] = value
    packet['request']['contract_calculation']['terms_sha256'] = digest(packet['admitted'])
    with pytest.raises(ValueError):
        run(packet)


def test_global_multiple_accounts_cannot_replace_one_aggregate(packets):
    packet = deepcopy(packets['global-plain'])
    holdings = packet['request']['contract_calculation']['premises']['holdings']
    holdings[0]['principal'] = '250000000'
    holdings.append({**holdings[0], 'account_id': 'second'})
    with pytest.raises(ValueError, match='one explicitly declared aggregate'):
        run(packet)


def test_excluded_holdings_still_count_against_issue_size(packets):
    packet = deepcopy(packets['definitive-excluded'])
    holdings = packet['request']['contract_calculation']['premises']['holdings']
    holdings.append({**holdings[0], 'principal': '500000000', 'account_id': 'second'})
    with pytest.raises(ValueError, match='issue principal'):
        run(packet)


@pytest.mark.parametrize('name', ['global-excluded', 'definitive-excluded'])
def test_invalid_rounding_still_refuses_without_transfers(packets, name):
    packet = deepcopy(packets[name])
    packet['admitted']['terms']['rounding']['value']['quantum'] = '0'
    packet['request']['contract_calculation']['terms_sha256'] = digest(packet['admitted'])
    with pytest.raises(ValueError, match='rounding'):
        run(packet)


@pytest.mark.parametrize('form', ['global', 'definitive'])
def test_regular_periods_keep_the_selected_rounding_basis(packets, form):
    result = run(packets[form + '-plain'])
    for c in result['calculations'][1:]:
        s = c['calculation_inputs']
        assert s['stub'] == 'REGULAR' and c['day_fraction'] == '1'
        assert 'broken_coupon_amount' not in s and 'note_form' not in s
        if form == 'global':
            assert s['rounding']['aggregation'] == 'PER_LEGAL_HOLDER'
            assert 'calculation_amount' not in s and 'fixed_coupon_amount' not in s
        else:
            assert s['rounding']['aggregation'] == 'PER_CALCULATION_AMOUNT'
            assert s['calculation_amount'] == '1000' and s['fixed_coupon_amount'] == '10.00'


def test_results_are_detached_from_requests_and_other_periods(packets):
    packet = deepcopy(packets['global-plain'])
    before = deepcopy(packet)
    result = run(packet)
    assert packet == before
    result['contract_terms']['terms']['annual_rate']['value'] = '1'
    result['term_assumptions']['no_default'] = False
    result['term_assumption_evidence']['reason'] = 'changed'
    result['calculations'][1]['calculation_inputs']['holdings'][0]['principal'] = '1'
    assert packet == before
    assert result['calculations'][2]['calculation_inputs']['holdings'][0]['principal'] == '500000000'
    packet['request']['contract_calculation']['periods'][2]['events'][0]['kind'] = 'changed'
    assert result['calculations'][2]['events'][0]['kind'] == 'accrual_start'
