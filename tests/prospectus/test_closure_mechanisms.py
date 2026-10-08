"""Boundary checks derived from source clauses and hand calculations."""
import pytest
from legalmath.prospectus import closure_mechanisms as m

def db():
    return dict(operation="write_down", ratio="0.05", required_loss="50", principal="100",
                others=[dict(principal="100", currency="EUR", effective=True),
                        dict(principal="999", currency="EUR", effective=False)],
                currency="EUR", premise_kind="HYPOTHETICAL", trigger_date="2026-01-01",
                determination_date="2026-01-15", reviewed_outer_deadline="2026-02-01",
                notices=dict(trigger_publication="2026-01-02", amount_publication="2026-01-15"))

def bbva():
    return dict(currency="EUR", issuer_determined_cet1_ratio="0.05", capital_reduction=True,
                condition_7_7_redemption_override=False, valid_timely_opt_out=True, listed=True,
                adjusted_floor_price="4", nominal_share_value="0.49", five_eligible_closing_prices=["5.005"]*5,
                holdings=[dict(legal_holder_id="holder-a", registration_name="A", liquidation_preference="10"),
                          dict(legal_holder_id="holder-a", registration_name="A", liquidation_preference="10")])

def seb():
    return dict(currency="USD", bank_cet1_ratio="0.1", group_cet1_ratio="0.05", usd_per_sek="0.1",
                adjusted_floor_usd="2", quota_value_sek="10.45", listed=True,
                reviewed_current_market_price_sek="30", holdings=[dict(legal_holder_id="holder-a", registration_name="A", principal="5"),
                                                                 dict(legal_holder_id="holder-a", registration_name="A", principal="5")])

@pytest.mark.parametrize("ratio,expected", [("0.051249","25"),("0.05125","0"),("0.051251","0")])
def test_deutsche_strict_threshold_ineffective_pool_member_and_notice(ratio, expected):
    s=db(); s["ratio"]=ratio
    r=m.deutsche(s)
    assert r["write_down"]==expected and r["eligible_total"]=="200"
    assert r["holder_notices_given_at"]=="2026-01-18" and r["outer_deadline_met"]
    assert r["operational_rounded_principal"] is None

def test_deutsche_missing_notice_does_not_cancel_loss_and_no_deadline_default():
    s=db(); s["notices"]={}; s["reviewed_outer_deadline"]=None
    r=m.deutsche(s)
    assert r["write_down"]=="25" and r["outer_deadline_met"] is None
    assert r["holder_notices_given_at"] is None and r["missing_notice_invalidates_write_down"] is False
    s["currency"]="USD"
    with pytest.raises(ValueError,match="units"): m.deutsche(s)

@pytest.mark.parametrize("notice,expected", [("2026-01-18","6"),("2026-01-19",None),(None,None)])
def test_deutsche_ten_day_notice_uses_publication_plus_three(notice, expected):
    s=dict(operation="write_up",annual_profit="100",written_down_initial="200",tier1="1000",
           distributions="5",mda_available="12",own_initial="100",pool_initial="200",own_prevailing="90",
           issuer_selected_total="12",premise_kind="HYPOTHETICAL",notice_publication=notice,payment_date="2026-01-31",
           conditions={k:True for k in ("subsequent_financial_year","no_annual_loss_created",
           "no_continuing_or_recreated_trigger","regulatory_conditions_met","pari_passu_conditions_met",
           "notice_and_payment_date_met","issuer_elected_write_up")})
    assert m.deutsche(s)["write_up"]==expected
    if expected:
        s["conditions"]["issuer_elected_write_up"]=False
        assert m.deutsche(s)["write_up"]=="0"

def test_bbva_optout_cannot_defeat_trigger_and_aggregate_precedes_rounding():
    r=m.bbva(bbva())
    assert r["path"]=="MANDATORY_6_1" and r["conversion_price"]=="501/100"
    assert r["holder_entitlements"][0]["shares"]==3

@pytest.mark.parametrize("optout,path",[(True,"OPTED_OUT_6_2"),(False,"CONVERSION_6_2")])
def test_bbva_capital_reduction_elections_and_redemption(optout,path):
    s=bbva(); s.update(issuer_determined_cet1_ratio="0.05125",valid_timely_opt_out=optout)
    assert m.bbva(s)["path"]==path
    s["condition_7_7_redemption_override"]=True
    assert m.bbva(s)["path"]=="REDEMPTION_7_7"

def test_bbva_missing_election_unknown_and_unlisted_needs_no_market_price():
    s=bbva(); s.update(issuer_determined_cet1_ratio="0.1",valid_timely_opt_out=None)
    assert m.bbva(s)["conversion"] is None
    s.update(valid_timely_opt_out=False,listed=False); s.pop("five_eligible_closing_prices")
    assert m.bbva(s)["conversion_price"]=="4"

def test_seb_zero_principal_is_not_zero_recovery():
    s=seb(); r=m.seb(s)
    assert r["principal_after_conversion"]=="0" and r["economic_recovery"] is None
    assert r["holder_entitlements"][0]["shares"]==3
    s["group_cet1_ratio"]="0.05125"
    assert m.seb(s)["conversion"] is False
    s.update(bank_cet1_ratio="0.05",listed=False); s.pop("reviewed_current_market_price_sek")
    assert m.seb(s)["conversion_price_usd"]=="2"

def test_calendar_requires_holidays_and_full_coverage():
    days={"2026-01-02":False,"2026-01-03":True,"2026-01-04":True}
    assert m.business_after("2026-01-01",2,days)=="2026-01-04"
    with pytest.raises(ValueError,match="coverage"): m.business_after("2026-01-01",3,days)
    days["2026-01-02"]=0
    with pytest.raises(ValueError,match="Boolean"): m.business_after("2026-01-01",2,days)

def test_registration_groups_not_implicitly_combined_and_wrong_edition_rejected(tmp_path):
    r=m.whole_shares([dict(legal_holder_id="holder-a",registration_name="A",principal="5"),dict(legal_holder_id="holder-b",registration_name="B",principal="5")],"3","principal")
    assert [h["shares"] for h in r]==[1,1]
    issue={"id":"deutsche-at1-2025","documents":[{"id":"deutsche-at1-2025"}]}
    with pytest.raises(ValueError,match="edition"): m.investigate(issue,{"deutsche-at1-2025":{"sha256":"wrong"}},tmp_path,{})
