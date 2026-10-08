"""Assemble scoped UBS branch evidence without erasing earlier qualifications."""
from ..canonical import digest
from ..transaction.evidence import fields
from . import instrument_branches as branches, instrument_evidence as evidence
from .instrument_sources import KEY
from .instrument_terms import day

FIELDS = {"private_records", "alternative_notice", "price_determination", "holder_delivery"}


def read(store, identity):
    if identity is None:
        return {k: [] if k == "private_records" else None for k in FIELDS}
    result = store.json(identity)
    fields(result, FIELDS)
    if not isinstance(result["private_records"], list):
        raise ValueError("Explicit private evidence list required")
    return result


def event_id(scenario):
    return digest(scenario["event"])


def notice(store, identity, scenario, context):
    scope = {"instrument_id":KEY,"clause":"14","event_id":event_id(scenario)}
    return branches.alternative_notice(store,identity,scope=scope,at=context["effective_at"],known_at=context["known_at"])


def price(store, identity, scenario, context, actual_notice_date):
    history = scenario["price_history"]
    if history is None:
        return {"status":"QUALIFIED","price":None,"issues":["Complete price history missing"]}
    scope={"instrument_id":KEY,"clause":"8(d)/8(m)","event_id":event_id(scenario),"history_sha256":store.put(history)}
    result=branches.determined_price(store,identity,scope=scope,at=context["effective_at"],known_at=context["known_at"])
    if (history["complete"] is not True or day(history["from"])>day("2024-06-18")
            or day(history["through"])<day(actual_notice_date)
            or history["terms_amended"] is not False or history["issuer_substituted"] is not False):
        result.update(status="QUALIFIED",price=None)
        result["issues"].append("A determination cannot replace missing history or authorize reuse after amendment/substitution")
    return result


def delivery(store, identity, scenario, context, settlement):
    scope={"instrument_id":KEY,"event_id":event_id(scenario),"holder_id":context["client_id"]}
    result=branches.holder_delivery(store,identity,scope=scope,at=context["effective_at"],known_at=context["known_at"])
    if result.get("evidence",{}).get("status")=="CONDITIONAL":
        claimed=result["evidence"]["value"]["entitled_shares"]
        if settlement.get("entitlement",{}).get("shares")!=claimed:
            result.update(status="QUALIFIED",delivered=None)
            result["issues"].append("Holder receipt quantity does not match the calculated entitlement")
    if settlement.get("issuer_obligation_discharged") is not True:
        result.update(status="QUALIFIED",delivered=None)
        result.setdefault("issues",[]).append("Event, price, share creation or depository receipt remains unresolved")
    return result
