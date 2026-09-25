"""Bitemporal evidence selection with interval-local supersession."""
from ..canonical import digest
from ..domain import eligible, interval, scalar, timestamp
from ..errors import LegalMathError
from .load import schema_errors


def normalize(records, declarations, subject_id, valid_at, known_at):
    timestamp(valid_at)
    timestamp(known_at)
    facts = {d["name"]: d["type"] for d in declarations}
    if len(facts) != len(declarations):
        raise LegalMathError("E_DUPLICATE_ID")
    by_id = {}
    for r in records:
        if schema_errors("fact-record", r):
            raise LegalMathError("E_SCHEMA")
        if r["record_id"] in by_id:
            raise LegalMathError("E_DUPLICATE_ID")
        if r["fact_name"] not in facts or r["type"] != facts[r["fact_name"]] or not scalar(r["type"], r["value"]):
            raise LegalMathError("E_TYPE")
        if len(set(r["evidence_ids"])) != len(r["evidence_ids"]) or len(set(r["supersedes_record_ids"])) != len(r["supersedes_record_ids"]):
            raise LegalMathError("E_DUPLICATE_ID")
        interval(r["valid_from"], r["valid_until"])
        timestamp(r["recorded_at"])
        by_id[r["record_id"]] = r
    for r in records:
        for predecessor in r["supersedes_record_ids"]:
            if predecessor not in by_id:
                raise LegalMathError("E_REFERENCE")
            old = by_id[predecessor]
            if any(old[k] != r[k] for k in ("subject_id", "fact_name", "type")):
                raise LegalMathError("E_TYPE")
    seen, stack = set(), set()

    def visit(ident):
        if ident in stack:
            raise LegalMathError("E_CYCLE")
        if ident in seen:
            return
        stack.add(ident)
        for old in by_id[ident]["supersedes_record_ids"]:
            visit(old)
        stack.remove(ident)
        seen.add(ident)
    for ident in by_id:
        visit(ident)
    eligible_records = [r for r in records if r["subject_id"] == subject_id and
        r["recorded_at"] <= known_at and eligible(r["valid_from"], r["valid_until"], valid_at)]
    suppressed = {p for r in eligible_records for p in r["supersedes_record_ids"]}
    selected = [r for r in eligible_records if r["record_id"] not in suppressed]
    result = {}
    for name, typ in facts.items():
        candidates = [r for r in selected if r["fact_name"] == name]
        if not candidates:
            stale = any(r["subject_id"] == subject_id and r["fact_name"] == name and r["recorded_at"] <= known_at for r in records)
            result[name] = {"status": "unknown", "type": typ, "reason": "STALE" if stale else "MISSING"}
            continue
        evidence = sorted({e for r in candidates for e in r["evidence_ids"]})
        values = {digest(r["value"]) for r in candidates}
        if len(values) > 1:
            if len(evidence) < 2:
                raise LegalMathError("E_INTEGRITY")
            result[name] = {"status": "conflict", "type": typ, "evidence_ids": evidence}
        else:
            ends = [r["valid_until"] for r in candidates if r["valid_until"] is not None]
            result[name] = {"status": "known", "type": typ, "value": candidates[0]["value"],
                "evidence_ids": evidence, "valid_from": max(r["valid_from"] for r in candidates),
                "valid_until": min(ends) if ends else None, "recorded_at": max(r["recorded_at"] for r in candidates)}
    return {"subject_id": subject_id, "facts": result}
