from ..errors import LegalMathError
from ..sources.intake import resolve_span


def coverage_report(db, con, bundle, inventory):
    spans = {s["id"]: s for s in bundle["source_spans"]}
    rows, covered = [], set()
    for item in inventory:
        span = item["source_span"]
        if span["id"] in covered:
            raise LegalMathError("E_DUPLICATE_ID")
        if span["id"] in spans and spans[span["id"]] != span:
            raise LegalMathError("E_HASH_MISMATCH")
        if not set(item.get("rule_ids", [])) <= {r["id"] for r in bundle["rules"]}:
            raise LegalMathError("E_REFERENCE")
        quote = resolve_span(db, con, span)
        if not item.get("disposition"):
            raise LegalMathError("E_DEPENDENCY")
        covered.add(span["id"])
        rows.append({"span_id": span["id"], "quote": quote, "disposition": item["disposition"],
                     "rule_ids": item.get("rule_ids", [])})
    if not set(spans) <= covered:
        raise LegalMathError("E_DEPENDENCY")
    return {"provisions": rows, "issues": sorted({x for m in bundle["interpretations"] for x in m["issue_ids"]}),
            "authority": "DRAFT_REQUIRES_BANK_REVIEW", "coverage_is_legal_approval": False}
