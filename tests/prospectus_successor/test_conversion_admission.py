"""Same declared input domain on active and inactive conversion branches."""
from copy import deepcopy
from fractions import Fraction

import pytest
from legalmath.prospectus import closure_mechanisms as kernels
from legalmath.prospectus.master_mechanisms import amount
from legalmath.prospectus.successor.financial_profiles import assess


def scenario(issue, active=True):
    base = {'issue_id':issue,'source_sha256':kernels.PROFILES[issue]['sha256'],
            'premise_kind':'HYPOTHETICAL','listed':True,
            'holdings':[{'legal_holder_id':'holder','registration_name':'Name','account_id':'a'}]}
    if issue.startswith('bbva'):
        base.update(currency='EUR',issuer_determined_cet1_ratio='0.05' if active else '0.1',
            capital_reduction=False,condition_7_7_redemption_override=False,
            adjusted_floor_price='4',nominal_share_value='0.49',five_eligible_closing_prices=['5.005']*5)
        base['holdings'][0]['liquidation_preference']='20'
    else:
        base.update(currency='USD',bank_cet1_ratio='0.1',group_cet1_ratio='0.05' if active else '0.1',
            usd_per_sek='0.1',adjusted_floor_usd='2',quota_value_sek='10.45',reviewed_current_market_price_sek='30')
        base['holdings'][0]['principal']='10'
    return base


def result(s):
    return assess({'instrument_id':s['issue_id'],'documents':[{'sha256':s['source_sha256']}]}, s)


FIELDS = [('bbva-at1-series15-2025',f) for f in ('adjusted_floor_price','nominal_share_value')] + [
    ('seb-at1-usd-2024',f) for f in ('usd_per_sek','adjusted_floor_usd','quota_value_sek','reviewed_current_market_price_sek')]


@pytest.mark.parametrize('issue,field', FIELDS)
@pytest.mark.parametrize('active', [False,True])
@pytest.mark.parametrize('value', ['0','-1',True,0.1,'NaN','1/0'])
def test_invalid_price_fx_rejected_independent_of_trigger(issue,field,active,value):
    s=scenario(issue,active); s[field]=value
    assert result(s)['status']=='UNSUPPORTED'


@pytest.mark.parametrize('issue', ['bbva-at1-series15-2025','seb-at1-usd-2024'])
@pytest.mark.parametrize('field', ['legal_holder_id','registration_name'])
@pytest.mark.parametrize('active', [False,True])
@pytest.mark.parametrize('value', ['', ' ', '\t\n', '\u00a0', True, 1, None])
def test_nonblank_identities_required(issue,field,active,value):
    s=scenario(issue,active); s['holdings'][0][field]=value
    assert result(s)['status']=='UNSUPPORTED'


@pytest.mark.parametrize('issue', ['bbva-at1-series15-2025','seb-at1-usd-2024'])
def test_valid_spelling_and_grouping_preserved(issue):
    s=scenario(issue); amount='principal' if issue.startswith('seb') else 'liquidation_preference'
    s['holdings']=[{'legal_holder_id':h,'registration_name':' Same name ' if h==' holder ' else 'Same name','account_id':a,amount:'5'}
                   for h,a in [(' holder ','a'),('holder','b'),(' holder ','c')]]
    original=deepcopy(s); out=result(s)
    assert out['status']=='CONDITIONAL' and s==original
    rows=out['value']['calculation']['holder_entitlements']
    assert [(r['legal_holder_id'],r['amount']) for r in rows]==[(' holder ','10'),('holder','5')]
    assert [r['registration_names'] for r in rows]==[[' Same name '],['Same name']]


@pytest.mark.parametrize('issue', ['bbva-at1-series15-2025','seb-at1-usd-2024'])
def test_legacy_same_name_across_holders_needs_explicit_registration(issue):
    s=scenario(issue); amount='principal' if issue.startswith('seb') else 'liquidation_preference'
    s['holdings']=[{'legal_holder_id':h,'registration_name':' Same name ','account_id':a,amount:'5'}
                   for h,a in [(' holder ','a'),('holder','b'),(' holder ','c')]]
    assert result(s)['status']=='UNSUPPORTED'
    for h in s['holdings']:
        h['registration_group_id']='supplied-same-registration'
    out=result(s)
    assert out['status']=='CONDITIONAL'
    c=out['value']['calculation']
    assert 'holder_entitlements' not in c
    assert c['registration_entitlements'][0]['amount']=='15'
    assert c['registration_entitlements'][0]['legal_holder_ids']==[' holder ','holder']


@pytest.mark.parametrize('issue', ['bbva-at1-series15-2025','seb-at1-usd-2024'])
def test_unknown_optional_elections_and_unlisted_branch_preserved(issue):
    s=scenario(issue,False)
    if issue.startswith('bbva'):
        s.update(capital_reduction=True,valid_timely_opt_out=None)
        assert result(s)['value']['calculation']['status']=='MISSING_ELECTION_EVIDENCE'
        s.update(valid_timely_opt_out=False,listed=False,five_eligible_closing_prices=[])
    else:
        s.update(group_cet1_ratio='0.05',listed=False)
        del s['reviewed_current_market_price_sek']
    assert result(s)['status']=='CONDITIONAL'


@pytest.mark.parametrize('value', ['1/0', '0/0', '100/000'])
@pytest.mark.parametrize('positive', [False, True])
def test_zero_denominator_has_public_validation_exception(value, positive):
    with pytest.raises(ValueError, match='nonzero denominator'):
        amount(value, positive=positive)


@pytest.mark.parametrize('value,expected', [('0', Fraction(0)), (2, Fraction(2)),
    ('5.005', Fraction(1001, 200)), ('1/3', Fraction(1, 3))])
def test_parser_preserves_valid_exact_amounts(value, expected):
    assert amount(value) == expected


@pytest.mark.parametrize('issue,field', [
    ('bbva-at1-series15-2025', 'issuer_determined_cet1_ratio'),
    ('seb-at1-usd-2024', 'bank_cet1_ratio'),
    ('seb-at1-usd-2024', 'group_cet1_ratio')])
@pytest.mark.parametrize('active', [False, True])
def test_zero_denominator_in_trigger_rate_is_unsupported(issue, field, active):
    s=scenario(issue, active); s[field]='1/0'
    assert result(s)['status']=='UNSUPPORTED'


@pytest.mark.parametrize('issue', ['bbva-at1-series15-2025', 'seb-at1-usd-2024'])
@pytest.mark.parametrize('active', [False, True])
def test_zero_denominator_in_holding_is_unsupported(issue, active):
    s=scenario(issue, active)
    field='principal' if issue.startswith('seb') else 'liquidation_preference'
    s['holdings'][0][field]='1/0'
    assert result(s)['status']=='UNSUPPORTED'


@pytest.mark.parametrize('active', [False, True])
def test_zero_denominator_in_price_window_is_unsupported(active):
    s=scenario('bbva-at1-series15-2025', active)
    s['five_eligible_closing_prices'][0]='1/0'
    assert result(s)['status']=='UNSUPPORTED'
