"""Declared engineering scenarios attached to a real source proposal, not clients."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

from ..transaction import intake
from .common import read, now
from . import eligibility, instrument_sources, instrument_terms, instrument_investigation


def fixtures(store, *, closures=()):
    start, end = instrument_terms.day("2026-09-01"), instrument_terms.day("2026-11-30")
    days = [(start + timedelta(days=i)).isoformat() for i in range((end-start).days+1)
            if (start + timedelta(days=i)).weekday() < 5]
    calendar_record = {"start": start.isoformat(), "end": end.isoformat(),
        "open_days": {"Zurich": days, "Singapore": [d for d in days if d not in closures]}, "premise_kind": "HYPOTHETICAL"}
    calendar_id = store.put(calendar_record)
    publication = {"date": "2026-09-04", "kind": "ordinary", "cet1": "6", "higher_amount": "0", "rwa": "100"}
    publication["snapshot_sha256"] = store.put(publication)
    notice = {"listed_on_six": True, "six_publications": ["2026-09-07"], "intermediary_delivery": None,
        "declares_event": True, "conversion_date": "2026-09-29", "price": "37.77", "depository": "SIX SIS", "offer": False}
    history = {"from": "2024-06-18", "through": "2026-09-29", "complete": True, "actions": [],
        "par_value_sgd": "0.10", "issuer_substituted": False, "terms_amended": False}
    scenario = {"premise_kind": "HYPOTHETICAL", "product_facts": {"registered_institution": True,
        "professional_investor": False, "specific_ia_am_contracts": False},
        "calendar_sha256": calendar_id, "event": {"kind": "trigger", "publication": publication,
            "notice": notice, "higher": [], "restoration": False}, "price_history": history,
        "holdings": ["250000", "250000"], "share_creation_date": "2026-09-28", "depository_received_date": "2026-09-29"}
    return instrument_terms.Calendar(store, calendar_id), scenario


def viability_event():
    return {"date": "2026-09-04", "customary_measures_inadequate": True,
        "finma_written_capital_absorption_essential": True, "irrevocable_public_support": False,
        "extraordinary_support": False, "capital_improved_or_imminent": False,
        "finma_written_without_support_nonviable": False}


def request(root, directory):
    root = Path(root)
    bank, store = intake.bootstrap(root, directory, at=now())
    registry = store.json(bank["registry_sha256"])
    for row in read(root/"docs/prospectus/legal/manifest.json")["sources"]:
        if row.get("use_for_applicable_law") is False:
            continue
        key = Path(row["text_path"]).stem
        recorded = row["retrieved_on"]
        if "T" not in recorded:
            recorded += "T00:00:00Z"
        raw = key + ".legal-original"
        registry[raw] = intake.record(store.put((root/row["path"]).read_bytes()), "law", row["source_url"], recorded,
            media_type="application/octet-stream")
        registry[key] = intake.record(store.put((root/row["text_path"]).read_bytes()), "law", row["source_url"], recorded,
            dependencies=[raw])
    bank["registry_sha256"] = store.put(registry)
    joined = {"profile": eligibility.PROFILE, "bank_request": bank,
        "product_assertions_sha256": store.put({}), "issuer_basis_source_ids": ["swiss-cao-20250101-de"],
        "prospectus_source_ids": [instrument_sources.KEY], "contract_event_source_id": None}
    result = {"profile": instrument_investigation.PROFILE, "joined_request": joined,
        "dossier_sha256": store.put(instrument_sources.dossier(root)), "scenario_sha256": None}
    return result, store


def scenarios(store):
    _, baseline = fixtures(store)
    cases = {"non_pi": baseline}
    pi = deepcopy(baseline); pi["product_facts"]["professional_investor"] = True
    cases["pi"] = pi
    missing = deepcopy(baseline); missing["event"]["notice"] = None
    cases["missing_notice"] = missing
    missing_calendar = deepcopy(baseline); missing_calendar["calendar_sha256"] = None
    cases["missing_calendar"] = missing_calendar
    outstanding = deepcopy(baseline); outstanding["event"]["higher"] = None
    cases["missing_higher_inventory"] = outstanding
    v = deepcopy(baseline)
    v["event"] = {"kind": "viability", "event": viability_event(), "notice": deepcopy(baseline["event"]["notice"]), "alternative": False}
    cases["viability_friday"] = v
    anomaly = deepcopy(baseline)
    anomaly["price_history"]["actions"] = [{"id": "synthetic-distribution", "date": "2026-09-03",
        "kind": "extraordinary_distribution", "data": {"market_price": "100", "distribution_per_share": "10"},
        "employee_plan": False, "overlapping_adjustment": False}]
    cases["printed_formula_anomaly"] = anomaly
    return cases


def extended_request(root, directory):
    """One declared end-to-end evidence scenario; never an actual notice/client."""
    from ..transaction.evidence import instant
    from .instrument_evidence import BANK_SCOPE
    from .instrument_extensions import event_id
    from fractions import Fraction
    result,store=request(root,directory)
    _,scenario=fixtures(store)
    scenario["product_facts"]["professional_investor"]=True
    context=result["joined_request"]["bank_request"]["context"]
    context.update(client_id="hypothetical-holder",booking_entity_id="hypothetical-bank",establishment_id="hypothetical-HK")
    scenario["event"]["notice"].update(six_publications=[],price="9.44")
    scenario["price_history"]["actions"]=[{"id":"hypothetical-bonus","date":"2026-09-03","kind":"bonus",
        "data":{"old_shares":"1","new_shares":"4"},"employee_plan":False,"overlapping_adjustment":False}]
    def record(data,scope,kind):
        at=context["known_at"]
        return store.put({"source_sha256":store.put(data),"scope":scope,"kind":kind,"recorded_at":at,
            "effective_from":context["effective_at"],"effective_until":None,
            "fresh_until":(instant(at)+timedelta(days=1)).isoformat(),"complete":True,"premise_kind":"HYPOTHETICAL"})
    key=instrument_sources.KEY;event=event_id(scenario)
    notice=record({"method":"alternative_exchange_method","listed_on_six":True,"permitted_by_applicable_exchange_rules":True,
        "rule_source_sha256":store.put(b"HYPOTHETICAL exchange rule"),"first_effective_date":"2026-09-07",
        "notice_source_sha256":store.put(b"HYPOTHETICAL issuer notice")},
        {"instrument_id":key,"clause":"14","event_id":event},"notice")
    price=record({"price":"9.44","actor":"independent_adviser","signed":True,"adviser_unavailable":False,
        "manifest_error":False,"bad_faith":False,"wilful_default":False,"par_value_sgd":"0.10"},
        {"instrument_id":key,"clause":"8(d)/8(m)","event_id":event,"history_sha256":store.put(scenario["price_history"])},"determination")
    shares=int(Fraction(500000)/Fraction("9.44"))
    delivery=record({"taxes_due":"0","taxes_paid":"0","delivery_receipt_sha256":store.put(b"HYPOTHETICAL holder custody receipt"),
        "delivered_shares":shares,"entitled_shares":shares,"registration_receipt_sha256":store.put(b"HYPOTHETICAL registration"),
        "voting_registered":True},{"instrument_id":key,"event_id":event,"holder_id":context["client_id"]},"settlement")
    private=record({"professional_investor":True},{k:context[k] for k in BANK_SCOPE},"private_facts")
    result.update(scenario_sha256=store.put(scenario),extensions_sha256=store.put({"private_records":[private],
        "alternative_notice":notice,"price_determination":price,"holder_delivery":delivery}))
    return result,store
