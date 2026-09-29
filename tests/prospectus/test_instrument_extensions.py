from copy import deepcopy
from pathlib import Path

import pytest

from legalmath.prospectus import instrument_cases as cases, instrument_investigation as engine, instrument_extensions as ext
from legalmath.transaction.evidence import Store
from tests.prospectus.test_instrument_evidence import evidence, AT

ROOT=Path(__file__).resolve().parents[2]
KEY="ubs-sgd-at1-2024-final-published"


@pytest.fixture
def fixture(tmp_path):
    request,store=cases.request(ROOT,tmp_path)
    request["joined_request"]["bank_request"]["context"].update(effective_at=AT,known_at=AT)
    scenario=cases.scenarios(store)["pi"]
    extras={"private_records":[],"alternative_notice":None,"price_determination":None,"holder_delivery":None}
    return request,store,scenario,extras


def run(fixture):
    request,store,scenario,extras=fixture
    request.update(scenario_sha256=store.put(scenario),extensions_sha256=store.put(extras))
    report=engine.investigate(request,store,ROOT)
    engine.revalidate(report,request,store,ROOT)
    return report


def bind_notice(fixture):
    request,store,scenario,extras=fixture
    scenario["event"]["notice"]["six_publications"]=[]
    data=dict(method="alternative_exchange_method",listed_on_six=True,permitted_by_applicable_exchange_rules=True,
        rule_source_sha256=store.put(b"hypothetical exchange rule"),first_effective_date="2026-09-07",notice_source_sha256=store.put(b"hypothetical notice"))
    scope=dict(instrument_id=KEY,clause="14",event_id=ext.event_id(scenario))
    extras["alternative_notice"]=evidence(store,data,scope,"notice")


def bind_price(fixture):
    request,store,scenario,extras=fixture
    scenario["event"]["notice"]["price"]="37.78"
    scenario["price_history"]["actions"]=[dict(id="rounding-case",date="2026-09-03",kind="bonus",data={"old_shares":"1","new_shares":"4"},employee_plan=False,overlapping_adjustment=False)]
    scope=dict(instrument_id=KEY,clause="8(d)/8(m)",event_id=ext.event_id(scenario),history_sha256=store.put(scenario["price_history"]))
    data=dict(price="37.78",actor="independent_adviser",signed=True,adviser_unavailable=False,
        manifest_error=False,bad_faith=False,wilful_default=False,par_value_sgd="0.10")
    extras["price_determination"]=evidence(store,data,scope,"determination")


def test_alternative_notice_drives_actual_schedule_without_invented_six_publication(fixture):
    bind_notice(fixture)
    report=run(fixture);event=report["instrument_event"]
    assert event["actual_notice_date"]=="2026-09-07"
    assert event["settlement"]["issuer_obligation_discharged"] is True
    assert fixture[2]["event"]["notice"]["six_publications"]==[]
    assert len(report["inventory"])==14 and not report["may_execute_transaction"]
    fixture[3]["alternative_notice"]=None
    assert run(fixture)["instrument_event"]["settlement"].get("issuer_obligation_discharged") is not True


def test_determination_and_delivery_share_the_calculated_entitlement(fixture):
    bind_price(fixture)
    request,store,scenario,extras=fixture
    event=run(fixture)["instrument_event"]
    assert event["price"]["reconstructed_price"]["status"]=="QUALIFIED"
    assert event["settlement"]["issuer_obligation_discharged"] is True
    shares=event["settlement"]["entitlement"]["shares"]
    scope=dict(instrument_id=KEY,event_id=ext.event_id(scenario),holder_id=request["joined_request"]["bank_request"]["context"]["client_id"])
    data=dict(taxes_due="0",taxes_paid="0",delivery_receipt_sha256=store.put(b"hypothetical custody receipt"),
        delivered_shares=shares,entitled_shares=shares,registration_receipt_sha256=store.put(b"hypothetical register receipt"),voting_registered=True)
    extras["holder_delivery"]=evidence(store,data,scope,"settlement")
    assert run(fixture)["instrument_event"]["holder_delivery"]["delivered"] is True
    data.update(delivered_shares=shares+1,entitled_shares=shares+1)
    extras["holder_delivery"]=evidence(store,data,scope,"settlement")
    assert run(fixture)["instrument_event"]["holder_delivery"]["delivered"] is None


@pytest.mark.parametrize("missing",["higher","share_creation_date"])
def test_price_evidence_cannot_bypass_unresolved_schedule_or_creation(fixture,missing):
    bind_price(fixture)
    if missing=="higher":fixture[2]["event"]["higher"]=None
    else:fixture[2][missing]=None
    assert run(fixture)["instrument_event"]["settlement"].get("issuer_obligation_discharged") is not True


def test_determination_does_not_authorize_amended_profile(fixture):
    bind_price(fixture)
    request,store,scenario,extras=fixture
    old=store.json(extras["price_determination"])
    scenario["price_history"]["terms_amended"]=True
    old["scope"]["history_sha256"]=store.put(scenario["price_history"])
    extras["price_determination"]=store.put(old)
    result=run(fixture)["instrument_event"]
    assert result["price"]["price"] is None and result["settlement"]["status"]=="UNKNOWN"
