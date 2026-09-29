from copy import deepcopy
from datetime import timedelta
from fractions import Fraction
from pathlib import Path

import pytest

from legalmath.canonical import digest
from legalmath.transaction.evidence import Store
from legalmath.prospectus import instrument_sources as sources, instrument_terms as terms
from legalmath.prospectus import instrument_prices as prices, instrument_cases as cases

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def fixture(tmp_path):
    store = Store(tmp_path/"store")
    calendar, scenario = cases.fixtures(store)
    return sources.dossier(ROOT)["terms"], calendar, scenario, store


def evaluate(fixture, **changes):
    t,c,s,_ = fixture
    event = deepcopy(s["event"]); event.update(changes)
    return terms.trigger(t,event["publication"],c,notice=event["notice"],higher=event["higher"],restoration=event["restoration"])


def test_source_terms_and_tamper():
    packet = sources.dossier(ROOT)
    assert packet["terms"]["initial_conversion_price"] == "37.77"
    assert packet["terms"]["initial_principal"] == "500000000"
    assert packet["annex"] == "A" and packet["current_applicability"] == "NOT_ESTABLISHED"
    assert packet["anomalies"][0]["printed_formula"] == "(A-B)/B"
    changed = deepcopy(packet); changed["terms"]["initial_conversion_price"] = "33.30"
    with pytest.raises(ValueError, match="Changed source"):
        sources.verify(changed, ROOT)


def test_all_source_bytes_are_bound(tmp_path):
    folder = tmp_path/"docs/prospectus/originals"; folder.mkdir(parents=True)
    (folder/(sources.KEY+".pdf")).write_bytes(b"wrong edition")
    with pytest.raises(ValueError, match="Unsupported source edition"):
        sources.dossier(tmp_path)


def test_ratio_equal_boundary_addback_and_generated_invariant(fixture):
    t,c,s,_ = fixture
    publication = deepcopy(s["event"]["publication"])
    # An independently structured integer inequality checks the production ratio.
    for capital in range(10):
        for extra in range(4):
            for rwa in (1, 50, 100, 143):
                publication.update(cet1=str(capital),higher_amount=str(extra),rwa=str(rwa))
                result = terms.trigger(t,publication,c,higher=[],restoration=False)
                assert result["ratio_breach"] == (100*capital + 100*extra < 7*rwa)
    publication.update(cet1="6",higher_amount="1",rwa="100")
    assert terms.trigger(t,publication,c,higher=[],restoration=False)["ratio_breach"] is False
    publication["rwa"] = "0"
    with pytest.raises(ValueError): terms.trigger(t,publication,c)


def test_calendar_rank_oracle_and_cross_market_closure(fixture):
    _,_,_,store = fixture
    calendar, s = cases.fixtures(store, closures=["2026-09-04", "2026-09-07"])
    assert calendar.is_open("2026-09-04",publication=True)
    assert not calendar.is_open("2026-09-04")
    opening = sorted(set(calendar.record["open_days"]["Zurich"]) & set(calendar.record["open_days"]["Singapore"]))
    for i in range(28):
        start = (terms.day("2026-09-01") + timedelta(days=i)).isoformat()
        for count in (1,3,5,20):
            # Select by rank rather than reimplementing the production day loop.
            assert calendar.after(start,count) == [d for d in opening if d > start][count-1]
    with pytest.raises(ValueError,match="coverage"): calendar.after("2026-11-30",1)
    assert terms.trigger(sources.dossier(ROOT)["terms"],s["event"]["publication"],calendar,higher=[],restoration=False)["base_notice_deadline"] == "2026-09-14"


def test_calendar_retrieval_cannot_be_changed(fixture):
    _,c,_,store=fixture
    store.path(c.identity).write_bytes(b"{}")
    with pytest.raises(ValueError,match="changed"): terms.Calendar(store,c.identity)


def test_no_notice_is_not_a_trigger(fixture):
    result = evaluate(fixture,notice=None)
    assert result["ratio_breach"] and result["trigger_event"] is None
    assert result["status"] == "QUALIFIED"
    assert evaluate(fixture)["trigger_event"] is True


def test_notice_channel_first_publication_and_delisting(fixture):
    notice = deepcopy(fixture[2]["event"]["notice"])
    notice["six_publications"] = ["2026-09-08","2026-09-07"]
    assert terms.notice_date(notice) == "2026-09-07"
    notice["listed_on_six"] = False
    assert terms.notice_date(notice) is None
    notice["intermediary_delivery"] = "2026-09-09"
    assert terms.notice_date(notice) == "2026-09-09"
    notice["listed_on_six"] = None
    assert terms.notice_date(notice) is None


def test_higher_trigger_delay_and_latest_conversion(fixture):
    higher = [{"id":"a","notice_date":"2026-09-18","conversion_date":"2026-10-30"},
              {"id":"b","notice_date":"2026-09-17","conversion_date":"2026-10-20"}]
    notice = deepcopy(fixture[2]["event"]["notice"])
    notice.update(six_publications=["2026-09-18"],conversion_date="2026-10-30")
    result = evaluate(fixture,notice=notice,higher=higher)
    assert result["trigger_event"] is True and result["conversion_deadline"] == "2026-10-30"
    notice["conversion_date"] = "2026-10-29"
    assert evaluate(fixture,notice=notice,higher=higher)["trigger_event"] is None
    higher[0]["notice_date"] = None
    assert evaluate(fixture,notice=notice,higher=higher)["status"] == "QUALIFIED"


def restoration(agreement="2026-09-06"):
    return {"agreement_date":agreement,"requested_by_ubs":True,"written_finma_agreement":True,
        "restored_or_imminent":True,"pro_forma_cet1_ratio":"0.08","jointly_deemed_adequate":True,
        "no_conversion_notice":"2026-09-07"}


def test_restoration_strict_timing_above_threshold_and_ordinary_only(fixture):
    record = restoration()
    result = evaluate(fixture,notice=None,restoration=record)
    assert result["restoration_exception"] and result["notice_required_under_ratio"] is None
    assert result["status"] == "QUALIFIED"  # absent notice history is not negative evidence
    # Exactly seven percent does not meet the stated 'above' condition.
    record["pro_forma_cet1_ratio"] = "0.07"
    assert evaluate(fixture,notice=None,restoration=record)["restoration_exception"] is False
    record = restoration("2026-09-07")
    assert any("Intraday" in x for x in evaluate(fixture,restoration=record)["issues"])
    p = deepcopy(fixture[2]["event"]["publication"]); p["kind"] = "extraordinary"
    n = deepcopy(fixture[2]["event"]["notice"]); n["six_publications"] = [p["date"]]
    result = evaluate(fixture,publication=p,notice=n,restoration=restoration())
    assert result["restoration_exception"] is False and result["trigger_event"] is True


def test_viability_friday_calendar_notice_event_anchored_conversion(fixture):
    _,c,s,_ = fixture
    notice = deepcopy(s["event"]["notice"])
    result = terms.viability(c,cases.viability_event(),notice=notice)
    assert result["notice_deadline"] == "2026-09-07"
    assert result["conversion_deadline"] == "2026-10-02"
    assert result["notice_and_schedule_satisfied"]
    notice["six_publications"] = ["2026-09-08"]
    assert terms.viability(c,cases.viability_event(),notice=notice)["status"] == "QUALIFIED"
    notice["six_publications"] = ["2026-09-07"]; notice["conversion_date"] = "2026-10-05"
    assert terms.viability(c,cases.viability_event(),notice=notice)["status"] == "QUALIFIED"


def test_viability_requires_written_basis_and_alternative_notice(fixture):
    _,c,s,_=fixture
    event=cases.viability_event(); event["finma_written_capital_absorption_essential"]=None
    assert terms.viability(c,event)["viability_event"] is None
    alt={"change_date":"2026-09-01","joint_determination_date":"2026-09-02",
        "law_changed_after_issue":True,"joint_ubs_finma_determination":True,"without_regulatory_event":True,"notice_date":None}
    assert terms.viability(c,cases.viability_event(),alternative=alt)["status"] == "QUALIFIED"
    alt["notice_date"]="2026-09-04"
    assert terms.viability(c,cases.viability_event(),alternative=alt)["viability_event"] is False
    # Law-change determination alone is not the date provisions cease to apply.
    alt["notice_date"]="2026-09-07"
    assert terms.viability(c,cases.viability_event(),notice=s["event"]["notice"],alternative=alt)["viability_event"] is True


def test_aggregate_once_floor_property_and_no_cash():
    for n in range(1,70):
        for price in ("37.77","37.76","100","0.1"):
            result=terms.share_entitlement(["250000"]*n,price,"250000")
            actual=result["shares"]; principal=250000*n; p=Fraction(price)
            assert actual*p <= principal < (actual+1)*p
            assert result["cash_for_fraction"] == "0"
    one=terms.share_entitlement(["250000"],"37.76","250000")["shares"]
    combined=terms.share_entitlement(["250000","250000"],"37.76","250000")["shares"]
    assert combined > 2*one
    with pytest.raises(ValueError): terms.share_entitlement(["1"],"37.77","250000")


def test_settlement_is_not_inferred_from_entitlement(fixture):
    schedule=evaluate(fixture)
    entitlement=terms.share_entitlement(["250000"],"37.77","250000")
    assert terms.settlement(schedule,entitlement)["issuer_obligation_discharged"] is None
    checked=terms.settlement(schedule,entitlement,share_creation_date="2026-09-28",depository_received_date="2026-09-29")
    assert checked["issuer_obligation_discharged"] is True and checked["holder_delivery"] == "NOT_ESTABLISHED"


def action(kind,data,*,at="2026-09-03",identity="a"):
    return {"id":identity,"date":at,"kind":kind,"data":data,"employee_plan":False,"overlapping_adjustment":False}


def test_rights_threshold_and_printed_anomaly(fixture):
    data={"shares_before":"100","new_shares":"20","consideration":"1800","market_price":"100","subscription_price":"90"}
    assert prices.factor("rights",data) == Fraction(118,120)
    data["subscription_price"]="95"
    assert prices.factor("rights",data) == 1
    assert prices.factor("extraordinary_distribution",{"market_price":"100","distribution_per_share":"10"}) == 9
    t,_,s,_=fixture
    h=deepcopy(s["price_history"])
    h["actions"]=[action("extraordinary_distribution",{"market_price":"100","distribution_per_share":"10"})]
    result=prices.price_at_notice(t,"2026-09-07",h)
    assert result["price"] is None and result["trace"][0]["literal_factor"] == "9"


def test_price_window_carry_forward_floor_rounding_and_missing_history(fixture):
    t,_,s,_=fixture
    t={**t,"initial_conversion_price":"100"}; h=deepcopy(s["price_history"])
    h["actions"]=[action("split",{"old_shares":"199","new_shares":"200"}),
        action("split",{"old_shares":"198","new_shares":"199"},at="2026-09-04",identity="b")]
    result=prices.price_at_notice(t,"2026-09-07",h)
    assert result["price"] == "99" and result["trace"][0]["disposition"] == "CARRIED_FORWARD"
    h["par_value_sgd"]="99.50"
    assert prices.price_at_notice(t,"2026-09-07",h)["price"] == "100"
    h["actions"]=[action("split",{"old_shares":"1","new_shares":"3"})]; h["par_value_sgd"]="0.1"
    assert prices.price_at_notice(t,"2026-09-07",h)["price"] is None
    h["actions"][0]["date"]="2026-09-08"
    assert prices.price_at_notice(t,"2026-09-07",h)["price"] == "100"
    h["complete"]=False
    assert prices.price_at_notice(t,"2026-09-07",h)["price"] is None


def test_successor_ratio_and_event_effective_window():
    ds=["2026-08-28","2026-08-31","2026-09-01","2026-09-02","2026-09-03"]
    ordinary=[{"date":d,"vwap":"50","sgd_fx":"2"} for d in ds]
    relevant=[{"date":d,"vwap":"25","sgd_fx":"2"} for d in ds]
    kw=dict(relevant_event="2026-09-04",effective_date="2026-09-11",conversion_date="2026-09-29",
        approved_entity=True,arrangements_entered=True,terms_amended=True,dealing_days=ds)
    assert prices.successor_price("100",ordinary,relevant,**kw)["new_conversion_price"] == "50"
    kw["effective_date"]="2026-09-12"
    assert prices.successor_price("100",ordinary,relevant,**kw)["new_conversion_price"] is None


def test_offer_half_cent_rounding_fraction_floor_and_viability_exclusion(fixture):
    _,c,_,_=fixture
    args=dict(holder_weight="1/2",proceeds_sgd_net="1.01",remaining_shares=3,offer_end="2026-10-05",calendar=c)
    result=prices.offer_allocation(event_kind="trigger",**args)
    assert result["cash_sgd"] == "51/100" and result["remaining_shares"] == 1
    assert result["cash_due"] == "2026-10-12"
    with pytest.raises(ValueError): prices.offer_allocation(event_kind="viability",**args)
