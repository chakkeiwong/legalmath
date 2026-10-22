"""Source-rule counterexamples: registration and ownership are different partitions."""
from copy import deepcopy
import pytest
from legalmath.prospectus import closure_mechanisms as kernels
from legalmath.prospectus.successor.financial_profiles import assess


def scenario(prefix):
    issue = 'seb-at1-usd-2024' if prefix == 'seb' else 'bbva-at1-series15-2025'
    s = dict(issue_id=issue, source_sha256=kernels.PROFILES[issue]['sha256'],
             premise_kind='HYPOTHETICAL', currency='USD' if prefix == 'seb' else 'EUR', listed=False)
    if prefix == 'seb':
        s.update(bank_cet1_ratio='0.1', group_cet1_ratio='0.06', usd_per_sek='0.1',
                 adjusted_floor_usd='3', quota_value_sek='10.45')
    else:
        s.update(issuer_determined_cet1_ratio='0.05', capital_reduction=True,
                 condition_7_7_redemption_override=False, valid_timely_opt_out=True,
                 adjusted_floor_price='3', nominal_share_value='0.49', five_eligible_closing_prices=[])
    return s


def holding(prefix, holder, name, group=None, amount='5', account='same-account'):
    row = dict(legal_holder_id=holder, registration_name=name, account_id=account)
    row['principal' if prefix == 'seb' else 'liquidation_preference'] = amount
    if group is not None:
        row['registration_group_id'] = group
    return row


def question(s):
    bundle = dict(instrument_id=s['issue_id'], documents=[dict(sha256=s['source_sha256'])])
    return assess(bundle, s)


@pytest.mark.parametrize('prefix', ['bbva', 'seb'])
@pytest.mark.parametrize('same_holder,expected', [(True, [1, 1]), (False, [3])])
def test_explicit_registration_partition_controls_rounding(prefix, same_holder, expected):
    s = scenario(prefix)
    s['holdings'] = [holding(prefix, 'holder-a', 'A', 'registration-a'),
                     holding(prefix, 'holder-a' if same_holder else 'holder-b',
                             'B' if same_holder else 'A', 'registration-b' if same_holder else 'registration-a')]
    result = question(s)
    assert result['status'] == 'CONDITIONAL'
    c = result['value']['calculation']
    assert [r['shares'] for r in c['registration_entitlements']] == expected
    assert 'holder_entitlements' not in c
    assert c['beneficial_holder_allocation'] == 'NOT_ESTABLISHED'
    assert c['registration_grouping'] == 'SUPPLIED_SAME_REGISTRATION_PARTITION'
    if not same_holder:
        assert c['registration_entitlements'][0]['legal_holder_ids'] == ['holder-a', 'holder-b']
    assert result['value']['actual_event'] == 'NOT_ESTABLISHED'
    assert result['value']['full_settlement_supported'] is False


@pytest.mark.parametrize('prefix', ['bbva', 'seb'])
@pytest.mark.parametrize('active', [True, False])
@pytest.mark.parametrize('bad', ['legacy-split', 'legacy-combined', 'mixed', 'blank', 'not-string',
                                 'conflicting-name', 'split-name', 'blank-holder', 'blank-name'])
def test_bad_mapping_is_refused_even_without_conversion(prefix, active, bad):
    s = scenario(prefix)
    a, b = holding(prefix, 'holder-a', 'A', 'group-a'), holding(prefix, 'holder-b', 'B', 'group-b')
    if bad == 'legacy-split':
        a.pop('registration_group_id'); b.pop('registration_group_id'); b['legal_holder_id'] = 'holder-a'
    elif bad == 'legacy-combined':
        a.pop('registration_group_id'); b.pop('registration_group_id'); b['registration_name'] = 'A'
    elif bad == 'mixed':
        b.pop('registration_group_id')
    elif bad == 'blank':
        b['registration_group_id'] = ' '
    elif bad == 'not-string':
        b['registration_group_id'] = 42
    elif bad == 'conflicting-name':
        b['registration_group_id'] = 'group-a'
    elif bad == 'split-name':
        b['registration_name'] = 'A'
    elif bad == 'blank-holder':
        b['legal_holder_id'] = ''
    else:
        b['registration_name'] = '\t'
    s['holdings'] = [a, b]
    if not active:
        if prefix == 'seb':
            s.update(bank_cet1_ratio='0.1', group_cet1_ratio='0.1')
        else:
            s.update(issuer_determined_cet1_ratio='0.1', capital_reduction=False)
    assert question(s)['status'] == 'UNSUPPORTED'


@pytest.mark.parametrize('amounts,shares,fraction', [(['5', '5'], 3, '1/3'),
    (['1.5', '1.5'], 1, '0'), (['2.9999', '0.0001'], 1, '0'),
    (['2.9999'], 0, '29999/30000'), (['3000000000000', '0.3'], 1000000000000, '1/10')])
def test_exact_arithmetic_boundaries(amounts, shares, fraction):
    rows = [holding('seb', 'holder-' + str(i), 'A', 'group-a', amount=a) for i, a in enumerate(amounts)]
    result = kernels.whole_shares(rows, '3', 'principal')
    assert result[0]['shares'] == shares
    assert result[0]['fraction_without_cash_compensation'] == fraction


def test_row_order_and_within_group_split_preserve_registration_total():
    rows = [holding('seb', 'holder-a', 'A', 'group-a'), holding('seb', 'holder-b', 'A', 'group-a')]
    expected = kernels.whole_shares(rows, '3', 'principal')
    assert kernels.whole_shares(list(reversed(rows)), '3', 'principal') == expected
    first = deepcopy(rows[0]); first['principal'] = '2'
    second = deepcopy(rows[0]); second['principal'] = '3'; second['account_id'] = 'another-account'
    assert kernels.whole_shares([first, second, rows[1]], '3', 'principal') == expected


def test_name_case_and_whitespace_are_not_silently_normalised():
    rows = [holding('seb', 'holder-a', 'A', 'group-a'), holding('seb', 'holder-b', ' a ', 'group-a')]
    with pytest.raises(ValueError, match='registration partition'):
        kernels.whole_shares(rows, '3', 'principal')


def test_legacy_coinciding_partitions_keep_the_original_shape():
    rows = [holding('seb', 'holder-a', 'A'), holding('seb', 'holder-a', 'A', account='different-account')]
    assert kernels.whole_shares(rows, '3', 'principal') == [dict(legal_holder_id='holder-a',
        registration_names=['A'], amount='10', shares=3, fraction_without_cash_compensation='1/3')]
