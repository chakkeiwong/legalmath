from copy import deepcopy
from fractions import Fraction

import pytest

from legalmath.prospectus import instrument_branches as branches
from legalmath.prospectus.instrument_evidence import CoveredCalendar
from legalmath.transaction.evidence import Store
from tests.prospectus.test_instrument_evidence import evidence, calendar, AT

KEY = "ubs-sgd-at1-2024-final-published"


def test_rounding_inequalities_and_ties():
    for numerator in range(401):
        for denominator in (1,2,3,7,100,1000):
            exact = Fraction(numerator,denominator)
            floor = branches.cents(str(exact),"down")
            near = branches.cents(str(exact),"half_up")
            assert floor <= exact < floor+Fraction(1,100)
            assert -Fraction(1,200) < near-exact <= Fraction(1,200)
    assert branches.cents("0.005","half_up") == Fraction(1,100)
    result = branches.rounding_scenarios("37.775")
    assert not result["agree"] and result["operational_price"] is None


def test_separate_exchange_windows_and_price_date():
    ordinary = CoveredCalendar(calendar(),market="SIX",purpose="exchange_dealing")
    relevant = CoveredCalendar(calendar("NYSE",["2026-09-07"]),market="NYSE",purpose="exchange_dealing")
    def rows(c,price): return [dict(date=d,vwap=price,sgd_fx="1") for d in c.preceding("2026-09-10",5)]
    args=dict(existing_price="40", existing_price_date="2026-09-11", ordinary_window=rows(ordinary,"100"), relevant_window=rows(relevant,"50"),
        ordinary_calendar=ordinary,relevant_calendar=relevant,relevant_event="2026-09-10",effective_date="2026-09-14",conversion_date="2026-09-29",
        approved_entity=True,arrangements_entered=True,terms_amended=True)
    result = branches.successor_separate(**args)
    assert result["status"] == "CONDITIONAL" and result["new_conversion_price"] == "20"
    assert result["ordinary_window"] != result["relevant_window"]
    args["relevant_window"] = rows(ordinary,"50")
    assert branches.successor_separate(**args)["status"] == "QUALIFIED"
    args["relevant_window"] = rows(relevant,"50"); args["existing_price_date"] = "2026-09-10"
    assert branches.successor_separate(**args)["new_conversion_price"] is None


def test_determination_binds_history_fallback_and_exceptions(tmp_path):
    store = Store(tmp_path)
    scope = dict(instrument_id=KEY,clause="8(d)/8(m)",event_id="notice-A",history_sha256=store.put({"actions":[]}))
    data = dict(price="37.78",actor="independent_adviser",signed=True,adviser_unavailable=False,
        manifest_error=False,bad_faith=False,wilful_default=False,par_value_sgd="0.1")
    ident = evidence(store,data,scope,"determination")
    def run(identity, **kwargs):return branches.determined_price(store,identity,scope=kwargs.get("scope",scope),at=AT,known_at=AT)
    assert run(ident)["price"] == "1889/50" and not run(ident)["source_formula_rewritten"]
    assert run(ident,scope=dict(scope,history_sha256=store.put({"actions":[1]})))["price"] is None
    data["actor"] = "issuer"
    assert run(evidence(store,data,scope,"determination"))["price"] is None
    data["adviser_unavailable"] = True
    assert run(evidence(store,data,scope,"determination"))["price"] is not None
    data["manifest_error"] = True
    assert run(evidence(store,data,scope,"determination"))["price"] is None


def test_alternative_notice_requires_rules_and_actual_notice(tmp_path):
    store = Store(tmp_path)
    scope = dict(instrument_id=KEY,clause="14",event_id="E")
    data = dict(method="alternative_exchange_method",listed_on_six=True,permitted_by_applicable_exchange_rules=True,
        rule_source_sha256=store.put(b"hypothetical exchange rule"),first_effective_date="2026-09-28",notice_source_sha256=store.put(b"hypothetical actual notice"))
    identity = evidence(store,data,scope,"notice")
    assert branches.alternative_notice(store,identity,scope=scope,at=AT,known_at=AT)["notice_date"] == "2026-09-28"
    data["permitted_by_applicable_exchange_rules"] = None
    assert branches.alternative_notice(store,evidence(store,data,scope,"notice"),scope=scope,at=AT,known_at=AT)["notice_date"] is None


def test_depository_receipt_does_not_prove_holder_receipt_or_registration(tmp_path):
    store = Store(tmp_path)
    scope = dict(instrument_id=KEY,event_id="E",holder_id="H")
    data = dict(taxes_due="10",taxes_paid="10",delivery_receipt_sha256=None,delivered_shares=10,
        entitled_shares=10,registration_receipt_sha256=None,voting_registered=True)
    def run():return branches.holder_delivery(store,evidence(store,data,scope,"settlement"),scope=scope,at=AT,known_at=AT)
    assert run()["status"] == "QUALIFIED" and not run()["delivered"]
    data["delivery_receipt_sha256"] = store.put(b"hypothetical custody receipt")
    assert run()["delivered"] and run()["voting_registered"] is None
    data["registration_receipt_sha256"] = store.put(b"hypothetical register receipt")
    assert run()["status"] == "CONDITIONAL"
    data["taxes_paid"] = "9"
    assert run()["status"] == "QUALIFIED"
