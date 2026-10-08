"""Scoped factual evidence, dated source changes and covered calendars.

Retrieval and an assertion's scope are checked mechanically. The truth of a
supplier's assertion and its legal effect are deliberately not certified.
"""
from copy import deepcopy
from datetime import timedelta

from ..canonical import digest
from ..transaction.evidence import fields, instant
from ..transaction import intake
from .instrument_terms import day

KINDS = {"determination", "calendar", "notice", "settlement", "private_facts",
         "law_coverage", "publication", "market"}
BANK_SCOPE = ("instrument_id", "client_id", "booking_entity_id", "establishment_id", "service", "action", "route_sha256")


def resolve(store, identity, *, scope, kind, at, known_at):
    if identity is None:
        return {"status": "UNKNOWN", "value": None, "issues": ["Evidence missing"]}
    row = store.json(identity)
    fields(row, {"source_sha256", "scope", "kind", "recorded_at", "effective_from",
                 "effective_until", "fresh_until", "complete", "premise_kind"})
    if row["kind"] not in KINDS or row["premise_kind"] not in {"HYPOTHETICAL", "SUPPLIED", "SOURCE_DEPENDENT_PROPOSAL"}:
        raise ValueError("Unsupported evidence kind or provenance")
    if type(row["complete"]) is not bool or not isinstance(row["scope"], dict):
        raise ValueError("Explicit scope and completeness required")
    value = store.json(row["source_sha256"])
    issues = []
    at, known = instant(at), instant(known_at)
    if row["scope"] != scope or row["kind"] != kind:
        issues.append("Evidence belongs to a different subject, event or kind")
    recorded = instant(row["recorded_at"])
    if recorded > known:
        issues.append("Evidence not yet recorded at the knowledge cutoff")
    for name in ("effective_from", "effective_until", "fresh_until"):
        if row[name] is not None:
            instant(row[name])
    start, end, fresh = (row[k] for k in ("effective_from", "effective_until", "fresh_until"))
    if start and end and instant(end) <= instant(start):
        raise ValueError("Reversed evidence interval")
    if start is None or instant(start) > at or (end is not None and at >= instant(end)):
        issues.append("Evidence effective interval does not cover the decision")
    if fresh is None or known >= instant(fresh):
        issues.append("Currentness of this factual record not established")
    if row["complete"] is not True:
        issues.append("Required record coverage is incomplete")
    return {"status": "UNKNOWN" if issues else "CONDITIONAL", "value": None if issues else value,
            "issues": issues, "evidence_sha256": identity, "source_sha256": row["source_sha256"],
            "premise_kind": row["premise_kind"], "truth_of_assertion": "NOT_ESTABLISHED"}


def attach_private(request, store, identities):
    """Adapt scoped private records to the existing fourteen-obligation engine."""
    from ..transaction.catalog import declarations
    from ..transaction.engine import DERIVED
    result = deepcopy(request)
    context = result["context"]
    scope = {k: context[k] for k in BANK_SCOPE}
    registry = store.json(result["registry_sha256"])
    assertions = store.json(context["facts_sha256"])
    accepted, unresolved = [], []
    for identity in identities:
        checked = resolve(store, identity, scope=scope, kind="private_facts",
                          at=context["effective_at"], known_at=context["known_at"])
        if checked["status"] != "CONDITIONAL":
            unresolved.append(checked)
            continue
        facts = checked["value"]
        if not isinstance(facts, dict) or set(facts) - (set(declarations()) - set(DERIVED)):
            raise ValueError("Private input cannot assert derived results or quality labels")
        for key, value in facts.items():
            typ = declarations()[key]
            if not ((typ == "bool" and type(value) is bool) or (typ == "integer" and type(value) is int and value >= 0)):
                raise ValueError("Private fact has the wrong type")
        row = store.json(identity)
        key = "scoped-private:" + identity
        registry[key] = intake.record(row["source_sha256"], "facts", key, row["recorded_at"],
            media_type="application/json", provenance="synthetic" if row["premise_kind"] == "HYPOTHETICAL" else "supplied",
            effective_from=row["effective_from"], effective_until=row["effective_until"], fresh_until=row["fresh_until"])
        for name in facts:
            assertions.setdefault(name, []).append({"source": key, "pointer": "/" + name})
        accepted.append(checked)
    result["registry_sha256"] = store.put(registry)
    context["facts_sha256"] = store.put(assertions)
    return {"request": result, "accepted": accepted, "unresolved": unresolved,
            "legal_clearance": "NOT_ESTABLISHED", "human_quality_evidence": False}


class CoveredCalendar:
    """One market/purpose with an explicit Boolean for every covered date."""
    def __init__(self, record, *, market, purpose):
        fields(record, {"market", "purpose", "start", "end", "days"})
        if record["market"] != market or record["purpose"] != purpose:
            raise ValueError("Calendar market/purpose mismatch")
        start, end = day(record["start"]), day(record["end"])
        if not 0 <= (end-start).days <= 3660:
            raise ValueError("Bounded calendar interval required")
        expected = {(start+timedelta(days=i)).isoformat() for i in range((end-start).days+1)}
        if not isinstance(record["days"], dict) or set(record["days"]) != expected or any(type(v) is not bool for v in record["days"].values()):
            raise ValueError("Every covered date requires an explicit open/closed value")
        self.record = deepcopy(record)
        self.identity = digest(record)

    def is_open(self, value):
        day(value)
        if value not in self.record["days"]:
            raise ValueError("Calendar does not cover the requested date")
        return self.record["days"][value]

    def preceding(self, value, count):
        day(value)
        if type(count) is not int or count < 1:
            raise ValueError("Positive count required")
        # Cover the anchor itself, too; an early fragment cannot prove adjacency.
        self.is_open(value)
        dates = sorted(d for d, opened in self.record["days"].items() if opened and d < value)
        if len(dates) < count:
            raise ValueError("Insufficient covered preceding dealing days")
        return dates[-count:]


def source_change(previous, current, *, dependent_receipts):
    """Same URL does not imply same edition; same bytes do not imply current law."""
    required = {"url", "sha256", "retrieved_at", "purpose"}
    for row in (previous, current):
        fields(row, required)
        instant(row["retrieved_at"])
        if not isinstance(row["sha256"], str) or len(row["sha256"]) != 64:
            raise ValueError("Content hash required")
    if current["url"] != previous["url"] or instant(current["retrieved_at"]) <= instant(previous["retrieved_at"]):
        raise ValueError("Ordered retrievals of the same source required")
    changed = previous["sha256"] != current["sha256"] or previous["purpose"] != current["purpose"]
    return {"changed": changed, "reassess_receipts": sorted(set(dependent_receipts)) if changed else [],
            "current_legal_force": "NOT_ESTABLISHED", "complete_amendment_history": "NOT_ESTABLISHED"}


def requirements(request, store):
    """Machine-readable missing-input queue from the actual bank inventory."""
    from ..transaction import engine
    report = engine.investigate(request, store)
    context = request["context"]
    return {"profile": "instrument-evidence-requests.v1", "request_hash": digest(request),
        "scope": {k: context[k] for k in BANK_SCOPE}, "obligations": report["inventory"],
        "missing_facts": {n: {"type": row["type"], "status": row["status"], "issues": row["issues"]}
            for n, row in report["observations"].items() if row["status"] != "KNOWN"},
        "required_law_coverage": ["jurisdiction", "entity_and_instrument_scope", "action_and_capacity",
            "effective_edition", "amendment_and_order_history", "exceptions_and_suspensions", "sanctions_identity_and_ownership"],
        "required_fact_record": ["source_sha256", "scope", "kind", "recorded_at", "effective_from",
            "effective_until", "fresh_until", "complete", "premise_kind"],
        "coverage_universe": "DECLARED_INVENTORY_ONLY_NOT_COMPLETE_DISCOVERY_OF_ALL_LAW",
        "may_execute_transaction": False, "human_quality_evidence": False}
