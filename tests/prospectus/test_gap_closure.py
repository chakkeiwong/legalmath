"""Construction-derived counterexamples for the next prospectus reader."""
from itertools import product

import pytest

from legalmath.prospectus.loss_absorption_witnesses import exact_repayment
from legalmath.prospectus.loss_absorption_reader import analyze_issue
from tests.prospectus.test_loss_absorption import fixture, ORDINARY


@pytest.mark.parametrize('unit_label', [
    'Calculation Amount:', 'Calculation Amount',
    'Calculation Amount (in relation to calculation of interest in global form see Conditions):',
    'Calculation Amount (Applicable to Notes in definitive Form.)',
    'Calculation Amount (Applicable to Notes in definitive Form.):',
    'Calculation Amount\n(Applicable to Notes in definitive Form.)\n',
])
@pytest.mark.parametrize('final_label', ['Final Redemption Amount:', 'Final Redemption Amount'])
def test_explicit_cash_fields_accept_layout_variants(unit_label, final_label):
    text = unit_label+' EUR 1,000 7 Issue Date: 24 February 2025. '+final_label+' EUR 1,000 per Calculation Amount.'
    result = exact_repayment(text)
    assert result and result['status']=='equal'
    assert result['currency']=='EUR' and result['amount']=='1000'
    assert all(text[f['start']:f['end']]==f['quote'] for f in result['fields'])


@pytest.mark.parametrize('first,second', [('1,00','1,00'), ('1,000','1,001'), ('0','0'), ('1.000,00','1.000,00')])
def test_malformed_or_unequal_cash_fields_cannot_establish_repayment(first, second):
    result=exact_repayment('Calculation Amount: EUR '+first+'. Final Redemption Amount: EUR '+second+' per Calculation Amount.')
    assert not result or result['status']!='equal'


@pytest.mark.parametrize('prefix', ['Coupon Amount', 'Minimum Denomination', 'Issue Price', 'Early Redemption Amount'])
def test_other_amounts_never_supply_missing_calculation_unit(prefix):
    result=exact_repayment(prefix+': EUR 1,000. Final Redemption Amount: EUR 1,000 per Calculation Amount.')
    assert result and result['status']=='unresolved'


@pytest.mark.parametrize('unit,final', [('EUR','USD'),('GBP','EUR')])
def test_currencies_are_part_of_exact_unit_relation(unit,final):
    result=exact_repayment('Calculation Amount '+unit+' 1,000. Final Redemption Amount '+final+' 1,000 per Calculation Amount.')
    assert result and result['status']=='unresolved'


def test_duplicate_units_do_not_collapse_to_one_even_if_values_match():
    result=exact_repayment('Calculation Amount EUR 1,000. Calculation Amount EUR 1,000. Final Redemption Amount EUR 1,000 per Calculation Amount.')
    assert result and result['status']=='unresolved'


@pytest.mark.parametrize('clause', [
    'Upon a Capital Event, holders shall surrender all rights to repayment of the principal.',
    'The principal repayment claim shall lapse permanently upon a Solvency Event.',
    'The Notes are subject to permanent impairment of principal upon a Capital Event.',
    'The Notes cannot be written down save where a Capital Event occurs.',
    'The Notes are not convertible provided that the Capital Event has not occurred.',
])
def test_unresolved_loss_or_exception_cannot_become_negative(tmp_path,clause):
    issue,docs,_=fixture(tmp_path,[ORDINARY+' '+clause])
    row=analyze_issue(issue,docs,tmp_path)
    assert row['answer'] is not False


def test_optional_conversion_does_not_discard_distinct_principal_write_down(tmp_path):
    issue,docs,_=fixture(tmp_path,[ORDINARY+' Holders may elect to convert the Notes into preference shares, '
        'and the principal amount of the Notes shall be permanently reduced upon a Solvency Event.'])
    row=analyze_issue(issue,docs,tmp_path)
    assert row['facts']['principal_write_down'] is True
    assert row['answer'] is True


@pytest.mark.parametrize('change', ['amount','currency','label','offset','denomination_without_alias'])
def test_independent_money_checker_rejects_self_consistent_claim_tampering(change):
    from copy import deepcopy
    from legalmath.prospectus.money_witness import verify
    text='Calculation Amount: EUR 1,000. Final Redemption Amount: EUR 1,000 per Calculation Amount.'
    record=deepcopy(exact_repayment(text))
    assert verify(text,record)['status']=='CHECKED'
    if change=='amount':record['amount']='100'
    elif change=='currency':record['currency']='GBP'
    elif change=='offset':record['fields'][0]['start']+=1
    else:
        replacement='Minimum Denomination' if change=='label' else 'Specified Denominations'
        text=text.replace('Calculation Amount:',replacement+':',1)
        # Update all offsets/quotes as an attacker with hashing access could do.
        first_end=text.index('.');record['fields'][0].update(start=0,end=first_end,quote=text[:first_end])
        begin=text.index('Final Redemption Amount:');end=text.rindex('.')
        record['fields'][1].update(start=begin,end=end,quote=text[begin:end])
    with pytest.raises(ValueError):verify(text,record)


@pytest.mark.parametrize('clause', [
    'Payments of principal shall be made against presentation and surrender of the Notes.',
    'If the Rate of Interest cannot be determined, the preceding rate shall apply, provided that the Calculation Agent shall notify the Issuer.',
    'A Note Certificate may be transferred upon surrender of the certificate in respect of its principal amount.',
])
def test_payment_document_surrender_and_rate_fallback_are_not_loss_mechanisms(tmp_path, clause):
    issue, docs, _ = fixture(tmp_path, [ORDINARY+' '+clause])
    assert analyze_issue(issue, docs, tmp_path)['answer'] is False


@pytest.mark.parametrize('unit,value,expected', [('100,000','100,000','equal'),('100,000','90,000','unresolved'),('100,00','100,00','unresolved')])
def test_explicit_per_note_denomination_is_checked_exactly(unit, value, expected):
    from legalmath.prospectus.money_witness import verify
    text='Final Redemption Amount of each Note EUR '+value+' per Note of EUR '+unit+' Specified Denomination'
    r=exact_repayment(text)
    assert r['status']==expected
    if expected=='equal': assert verify(text,r)['status']=='CHECKED'


def test_registered_form_unit_alias_retains_explicit_calculation_meaning():
    from legalmath.prospectus.money_witness import verify
    text='Specified Denominations: EUR 100,000. Calculation Amount (in relation to calculation of interest on Notes in global form or registered definitive form see Conditions): Specified Denominations. Final Redemption Amount: EUR 100,000 per Calculation Amount.'
    r=exact_repayment(text)
    assert verify(text,r)['status']=='CHECKED'


@pytest.mark.parametrize('clause', [
    'See also the risk factors headed “The principal amount of the Notes may be reduced to absorb losses”.',
    'See the section entitled "The Notes will be converted into ordinary shares".',
    'Due to uncertainty, it is difficult to predict when, if at all, the principal amount of the Notes may be written down.',
])
def test_reported_heading_or_epistemic_uncertainty_is_not_an_operative_witness(tmp_path, clause):
    issue, docs, _ = fixture(tmp_path, [ORDINARY+' '+clause])
    row=analyze_issue(issue, docs, tmp_path)
    assert row['answer'] is not True
    assert row['facts']['principal_write_down'] is not True
    assert row['facts']['mandatory_common_conversion'] is not True


def test_quoted_heading_does_not_remove_later_independent_operative_loss(tmp_path):
    clause='See the section headed “The Notes may be written down”; upon a Capital Event, the Issuer shall write down the principal amount of the Notes.'
    issue, docs, _ = fixture(tmp_path, [ORDINARY+' '+clause])
    assert analyze_issue(issue, docs, tmp_path)['answer'] is True


@pytest.mark.parametrize('text', [
    'Calculation Amount EUR 1,000. Calculation Amount Specified Denominations. Specified Denominations EUR 2,000. Final Redemption Amount EUR 1,000 per Calculation Amount.',
    'Calculation Amount EUR 1,000. Final Redemption Amount EUR 1,000 per Calculation Amount. Final Redemption Amount of each Note EUR 2,000 per Note of EUR 2,000 Specified Denomination.',
])
def test_mixed_layout_duplicate_fields_remain_ambiguous(text):
    r=exact_repayment(text)
    assert r and r['status']=='unresolved'
