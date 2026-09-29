from fractions import Fraction
from pathlib import Path

import pytest

from legalmath.prospectus import preferred_ss as ss, instrument_cases
from legalmath.prospectus.instrument_evidence import CoveredCalendar
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[2]


def test_bound_source_and_controlling_document_difference():
    packet = ss.dossier(ROOT)
    assert packet["terms"]["depositary_fraction"] == "1/1000"
    assert packet["product_interpretation"]["debt_legal_form"] is False
    assert packet["source_differences"] and packet["dependencies"]["deposit_agreement"] == "MISSING"


def dividend(**changes):
    data = dict(start="2026-05-17",end="2026-08-17",declared_fraction="1",funds_available=True,
        depositary_shares=100,allocation_basis="round_holder_allocation",withholding="0")
    data.update(changes)
    return ss.regular_dividend(**data)


def test_noncumulative_periods_exact_rate_and_no_payment_inference():
    missed = dividend(declared_fraction="0")
    next_period = dividend(start="2026-08-17",end="2026-11-17")
    assert missed["gross_usd"] == missed["undeclared_carry"] == "0"
    assert Fraction(next_period["exact_holder_usd"]) == Fraction(25)*100*Fraction(19,400)/4
    assert next_period["gross_usd"] == "2969/100" and next_period["actual_payment"] == "NOT_ESTABLISHED"
    assert dividend(declared_fraction="1/2")["exact_holder_usd"] == "475/32"


@pytest.mark.parametrize("changes", [{"declared_fraction":None},{"funds_available":None},
    {"allocation_basis":None},{"withholding":None},{"start":"2022-01-31","end":"2022-05-17"}])
def test_missing_terms_and_stub_qualify(changes):
    assert dividend(**changes)["status"] == "QUALIFIED"


def redemption(**changes):
    args=dict(date="2027-02-17",notice_date="2027-01-18",ordinary=True,capital_event_date=None,
        full_redemption=False,issuer_elected=True,funds_available=True,regulator_approval=True,
        notice_complete=True,depositary_shares=1000)
    args.update(changes)
    return ss.redemption(**args)


def test_redemption_inclusive_dates_and_control_precedence():
    assert redemption()["status"] == "CONDITIONAL"
    assert redemption(notice_date="2027-01-19")["status"] == "QUALIFIED"
    assert redemption(notice_date="2026-12-18")["status"] == "QUALIFIED"
    assert redemption(date="2027-02-16")["status"] == "QUALIFIED"
    assert redemption(regulator_approval=None)["status"] == "QUALIFIED"
    assert redemption(ordinary=False,capital_event_date="2026-11-19",full_redemption=True)["status"] == "CONDITIONAL"
    assert redemption(ordinary=False,capital_event_date="2026-11-18",full_redemption=True)["status"] == "QUALIFIED"
    with pytest.raises(ValueError,match="multiples"):redemption(depositary_shares=1)


def test_liquidation_conservation_parity_and_zero_assets():
    for available in (0,100,1000,2000,10000):
        result=ss.liquidation(available_after_senior_claims=str(available),own_preference="1000",own_declared_unpaid="20",parity_claims="980")
        own=Fraction(result["own_distribution"])
        parity=min(Fraction(available),2000)*Fraction(980,2000)
        assert own+parity+Fraction(result["junior_residual"]) == available
        assert own <= 1020 and not result["undeclared_dividends_included"]


def test_payment_calendar_requires_both_cities_and_keeps_period_unchanged():
    def cal(city,closed):
        start=date(2026,12,28)
        days={(start+timedelta(days=i)).isoformat():(start+timedelta(days=i)).weekday()<5 for i in range(10)}
        for d in closed:days[d]=False
        value=dict(market=city,purpose="banks_not_authorized_or_required_closed",start="2026-12-28",end="2027-01-06",days=days)
        return CoveredCalendar(value,market=city,purpose=value["purpose"])
    ny=cal("New York",["2026-12-31","2027-01-01"])
    ch=cal("Charlotte",["2026-12-30","2026-12-31","2027-01-01"])
    # Exercise the contract's year boundary rule as a declared date-mechanics
    # challenge; Dec 31 is not one of the scheduled Series SS coupon dates.
    result=ss.dividend_payment_date("2026-12-31",new_york=ny,charlotte=ch)
    assert result["payment_date"]=="2026-12-29" and not result["period_adjusted"]
    assert result["additional_dividend_for_delay"]=="0"


def test_equity_scope_does_not_remove_bank_obligations(tmp_path):
    request,store=instrument_cases.request(ROOT,tmp_path)
    joined=request["joined_request"]
    joined["bank_request"]["context"].update(instrument_id=ss.KEY,instrument_kind="preferred_share")
    joined["prospectus_source_ids"]=[ss.KEY]
    joined["issuer_basis_source_ids"]=[]  # No Swiss legal-power profile transferred.
    report=ss.investigate(joined,store,ROOT)
    assert report["calculations"]["scope"]["in_scope_product"]["value"] is False
    assert len(report["inventory"]) == 14 and not report["may_execute_transaction"]
    assert report["observations"]["professional_investor"]["status"] == "UNKNOWN"
    joined["bank_request"]["context"]["instrument_id"]="ubs-sgd-at1-2024-final-published"
    with pytest.raises(ValueError,match="another issue"):ss.investigate(joined,store,ROOT)
