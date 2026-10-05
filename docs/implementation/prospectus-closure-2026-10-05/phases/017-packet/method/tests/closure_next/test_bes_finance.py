"""Source-formula counterexamples and qualification controls, not legal labels."""
from fractions import Fraction
import pytest
from scripts.prospectus_closure_finance import coupon,icma,euro_half_up,deemed_notice,tax_notice,maturity_principal,eurosystem_designation,select_section

@pytest.mark.parametrize("start,end",[
    ("2014-01-21","2015-01-21"),("2016-01-21","2017-01-21")])
def test_full_coupon_across_leap_year(start,end):
    result=coupon("100000","0.04",start,end,[(start,end)],1,rounding="source_half_up")
    assert result["amount"]=="4000.00" and result["day_count"]==[1,1]

def test_leap_partial_is_not_actual_365():
    r=coupon("100000","0.04","2016-01-21","2016-07-21",
             [("2016-01-21","2017-01-21")],1,rounding="source_half_up")
    assert r["day_count"]==[91,183] and r["amount"]=="1989.07"

def test_two_period_long_stub():
    r=coupon("100000","0.04","2015-10-21","2017-01-21",
        [("2015-01-21","2016-01-21"),("2016-01-21","2017-01-21")],1,rounding="source_half_up")
    assert r["day_count"]==[457,365] and r["amount"]=="5008.22"

def test_short_period_uses_ending_determination_period():
    # The printed rule (A) uses the ending period when total accrual is shorter.
    assert icma("2015-12-21","2016-02-21",
        [("2015-01-21","2016-01-21"),("2016-01-21","2017-01-21")],1)==Fraction(62,366)

def test_series36_full_issue_coupon():
    r=coupon("750000000","0.02625","2014-05-08","2015-05-08",
        [("2014-05-08","2015-05-08")],1,rounding="source_half_up")
    assert r["amount"]=="19687500.00" and r["may_execute_transaction"] is False

@pytest.mark.parametrize("raw,expected",[(Fraction(5,1000),"0.01"),(Fraction(4999,1000000),"0.00"),
    (Fraction(1005,1000),"1.01"),(Fraction(1004999,1000000),"1.00")])
def test_exact_half_cent_rounding(raw,expected):assert euro_half_up(raw)==expected

def test_round_full_nominal_once():
    assert euro_half_up(Fraction(10**35)+Fraction(1,100))==str(10**35)+".01"
    assert euro_half_up(Fraction(5,1000)*2)=="0.01"
    assert euro_half_up(Fraction(5,1000))=="0.01"  # summing two rounded holdings would give 0.02

def test_unknown_market_convention_abstains():
    assert coupon("100","0.04","2014-01-21","2015-01-21",
        [("2014-01-21","2015-01-21")],1,rounding=None)["amount"] is None

@pytest.mark.parametrize("periods",[
    [("2014-01-21","2015-01-21"),("2015-02-21","2016-01-21")],
    [("2014-01-21","2015-01-21"),("2015-01-21","2016-01-21"),("2016-01-21","2017-01-21")],
    [("2014-01-21","2014-01-21")]])
def test_invalid_or_unreviewed_schedule_rejected(periods):
    with pytest.raises(ValueError):icma("2014-01-21","2015-01-21",periods,1)

@pytest.mark.parametrize("value",["NaN","Infinity","-1",0.04])
def test_inexact_or_invalid_amounts_rejected(value):
    with pytest.raises(ValueError):
        coupon(value,"0.04","2014-01-21","2015-01-21",[("2014-01-21","2015-01-21")],1,rounding="source_half_up")

def test_notice_skips_explicit_nonbusiness_days():
    calendar={"2024-03-30":False,"2024-03-31":False,"2024-04-01":False,"2024-04-02":True,"2024-04-03":True}
    assert deemed_notice("2024-03-29",calendar)["date"]=="2024-04-03"

def test_missing_calendar_never_defaults_to_weekdays():
    assert deemed_notice("2024-03-29",{})["date"] is None

@pytest.mark.parametrize("end,allowed",[("2024-01-30",False),("2024-01-31",True),("2024-03-01",True),("2024-03-02",False)])
def test_tax_notice_bounds(end,allowed):
    assert tax_notice("2024-01-01",end,legal_counting_confirmed=True)["within_interval"] is allowed

def test_tax_day_count_unconfirmed():
    assert tax_notice("2024-01-01","2024-01-31",legal_counting_confirmed=False)["within_interval"] is None

@pytest.mark.parametrize("cancelled,early",[(None,False),(False,None),(True,False),(False,True)])
def test_maturity_exceptions_preserved(cancelled,early):
    assert maturity_principal("100000",purchased_and_cancelled=cancelled,early_redeemed=early)["amount"] is None

def test_maturity_conditional_only():
    r=maturity_principal("100000",purchased_and_cancelled=False,early_redeemed=False)
    assert r["amount"]=="100000.00" and r["may_execute_transaction"] is False

def test_eligibility_yes_is_not_collateral_recognition():
    text="Yes. Note that the designation “yes” simply means that the Notes are intended upon issue to be registered with Interbolsa; this does not necessarily mean eligible collateral; eligibility criteria apply."
    r=eurosystem_designation(text)
    assert r["intended_registration"] is True and r["eligible_collateral"] is None
    assert eurosystem_designation(text.replace("are intended","are not intended"))["intended_registration"] is None
    assert eurosystem_designation(text.replace("Yes.","No."))["intended_registration"] is None

def test_duplicate_section_number_keeps_both_sources():
    rows=[{"number":"1.17","title":"FTT"},{"number":"1.17","title":"KPMG audit"}]
    r=select_section(rows,"1.17")
    assert r["status"]=="UNRESOLVED" and r["records"]==rows
