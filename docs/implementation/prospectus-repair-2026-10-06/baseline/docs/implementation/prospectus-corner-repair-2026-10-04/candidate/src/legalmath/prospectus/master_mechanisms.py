"""Exact conditional arithmetic; real loss and legal authority remain separate."""
from copy import deepcopy
from fractions import Fraction
import re

from .master_control import ROOT, read, sha

DEUTSCHE = "deutsche-at1-2025"


def amount(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("Exact integer, decimal or rational string required; floats are rejected")
    if not re.fullmatch(r"\d+(?:\.\d+|/\d+)?", str(value)):
        raise ValueError("Unsigned exact amount required")
    result = Fraction(value)
    if result < 0 or (positive and result <= 0):
        raise ValueError("Amount outside supported domain")
    return result


def repaired_inventory(inventory):
    result = deepcopy(inventory)
    ids = [row["id"] for row in result["issues"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate issue identity")
    result["scope"] = f"{len(ids)} exposed development issues; all selected source readings remain qualified. No unseen-family observations in this inventory."
    result["exposure"] = {"development_issues": len(ids), "unseen_issues": 0}
    return result


def issue_context(bank, issue):
    if issue["security_type"] not in {"debt", "coco_debt"}:
        raise ValueError("Only source-declared debt instruments supported")
    result = deepcopy(bank)
    result["context"].update(instrument_id=issue["id"], instrument_kind="debt_bond")
    return result


def deutsche_dossier():
    inventory = read(ROOT / "docs/prospectus/gap-closure/final-inventory.json")
    doc = inventory["documents"][DEUTSCHE]
    if sha(ROOT/doc["original"]) != doc["sha256"] or sha(ROOT/doc["text"]) != doc["text_sha256"]:
        raise ValueError("Deutsche source edition changed")
    extracted = read(ROOT/doc["text"])
    pages = {row["page"]: " ".join(row["text"].split()) for row in extracted["pages"]}
    required = {4:["controlling and binding"],52:["5.125", "pro rata"],53:["not affect", "discretion"],54:["Annual Profit", "tier 1 capital"],55:["Trigger Event"]}
    anchors=[]
    for page, terms in required.items():
        for term in terms:
            if term not in pages[page]:raise ValueError(f"Missing clause anchor {page}: {term}")
        anchors.append({"pdf_page":page,"text":pages[page],"sha256":__import__('hashlib').sha256(pages[page].encode()).hexdigest()})
    return {"profile":"deutsche-at1-2025-conditional-arithmetic.v1", "issue_id":DEUTSCHE,"source":doc,
            "threshold_ratio":"41/800", "anchors":anchors,"controlling_language":"German",
            "source_interpretation":"Local section 5(4) correspondence; broader law, fiscal effects and actual determinations remain unverified.",
            "arithmetic_scope":"Conditional principal allocation and stated write-up cap; not full event/notice/settlement implementation."}


def write_down(*, ratio, required_loss, principal, others, currency, premise_kind):
    if premise_kind not in {"HYPOTHETICAL", "SOURCE_DEPENDENT_PROPOSAL"}:
        raise ValueError("Explicit conditional provenance required")
    if not re.fullmatch("[A-Z]{3}", currency):raise ValueError("Currency code required")
    ratio, required_loss, principal = amount(ratio), amount(required_loss), amount(principal,positive=True)
    total = principal
    for row in others:
        if row["currency"] != currency or type(row["effective"]) is not bool:
            raise ValueError("Inconsistent units or unknown effectiveness")
        value=amount(row["principal"])
        if row["effective"]:total+=value
    triggered=ratio < Fraction(41,800)
    allocation=min(required_loss,total)*principal/total if triggered else Fraction(0)
    return {"trigger_under_premises":triggered,"write_down":str(allocation),"remaining_principal":str(principal-allocation),
            "eligible_total":str(total),"currency":currency,"premise_kind":premise_kind,
            "required_loss_provenance":"Externally determined amount; not inferred from CET1 alone",
            "actual_event_or_loss":"NOT_ESTABLISHED","notice_effectiveness":"Not inferred from notice absence"}


def write_up(*, annual_profit, written_down_initial, tier1, distributions, mda_available,
             own_initial, pool_initial, own_prevailing, issuer_selected_total, conditions, premise_kind):
    if premise_kind not in {"HYPOTHETICAL", "SOURCE_DEPENDENT_PROPOSAL"}:raise ValueError("Conditional provenance required")
    needed={"subsequent_financial_year","no_annual_loss_created","no_continuing_or_recreated_trigger",
            "regulatory_conditions_met","pari_passu_conditions_met","notice_and_payment_date_met","issuer_elected_write_up"}
    if set(conditions)!=needed or any(type(v) is not bool for v in conditions.values()):raise ValueError("All write-up conditions must be explicit Booleans")
    j,s,t,d,m,n,p,v,e=[amount(x) for x in (annual_profit,written_down_initial,tier1,distributions,mda_available,own_initial,pool_initial,own_prevailing,issuer_selected_total)]
    if t<=0 or p<=0 or n<=0 or n>p or v>n:raise ValueError("Invalid capital or nominal pool")
    h=j*s/t
    cap=max(Fraction(0),min(h-d,m))
    selected=min(e,cap) if all(conditions.values()) else Fraction(0)
    addition=min(n-v,selected*n/p)
    return {"H":str(h),"available_pool_cap":str(cap),"write_up":str(addition),"new_principal":str(v+addition),
            "issuer_discretion_retained":True,"entitlement_from_cap":False,"premise_kind":premise_kind,
            "actual_write_up":"NOT_ESTABLISHED","rounding_and_regulatory_determination":"Required separately before operational use"}


def input_requirements(issue, mechanisms):
    return {"issue_id":issue["id"],"calculation_profile": "UBS_existing" if issue["id"]=="ubs-sgd-at1-2024" else "Deutsche_conditional_arithmetic" if issue["id"]==DEUTSCHE else "NOT_IMPLEMENTED" if mechanisms else "NO_LOSS_MECHANISM_IDENTIFIED_IN_SELECTED_SOURCES",
        "actual_inputs_supplied":False,"may_execute_transaction":False,
        "groups":{
            "contract":["Executed applicable agreements, amendments and controlling language"],
            "authority":["Dated jurisdiction, entity, procedure and authority evidence"],
            "event":["Trigger determination, effective instruments, actual notices and settlement"],
            "calculation":["Issue-specific formula, required loss, outstanding capital, holdings, prices and currency"],
            "client":["Client identity/status, booking entity, mandate and suitability evidence"],
            "bank":["Policy, capacity, route, current sources and all 14 obligations"]},
        "absence_meaning":"Missing inputs, not negative facts or permission"}
