"""Separate provision validity, knowledge and actual observations."""
from .contracts import QueryResult, timestamp
from ..legal_review import LegalVersion, AUTHORITY_FACTS


def assess(bundle, bases, facts):
    if not bases:
        return QueryResult("Q4", "UNKNOWN", unresolved=["No dated primary legal basis supplied"]).json()
    rows = []
    for basis in bases:
        required = ("id", "authority", "jurisdiction", "edition", "source", "valid_from", "known_from", "premises")
        if any(not basis.get(k) for k in required):
            raise ValueError("Incomplete legal basis")
        version = LegalVersion(timestamp(basis["valid_from"]),
            timestamp(basis["valid_until"]) if basis.get("valid_until") else None, timestamp(basis["known_from"]))
        period = version.visible_and_in_period(timestamp(bundle["effective_at"]), timestamp(bundle["known_at"]))
        values, missing = {}, []
        for name in AUTHORITY_FACTS:
            candidates = [f for f in facts if f["name"] == name and f["basis_id"] == basis["id"] and
                f["instrument_id"] == bundle["instrument_id"] and
                timestamp(f["known_from"]) <= timestamp(bundle["known_at"]) and
                timestamp(f["observed_at"]) <= timestamp(bundle["effective_at"]) and
                (not f.get("valid_until") or timestamp(bundle["effective_at"]) < timestamp(f["valid_until"]))]
            if any(type(f["value"]) is not bool or not f.get("source") for f in candidates):
                raise ValueError("Typed source-linked fact required")
            unique = {f["value"] for f in candidates}
            values[name] = "CONFLICT" if len(unique) > 1 else next(iter(unique)) if unique else None
            if not unique:
                missing.append(name)
        if period != "IN_RECORDED_PERIOD":
            status = "UNKNOWN"
            missing.append(period)
        elif "CONFLICT" in values.values():
            status = "CONFLICT"
        elif any(v is False for v in values.values()):
            status = "NO"
        elif missing:
            status = "UNKNOWN"
        else:
            status = "YES"
        rows.append({"basis": basis["id"], "status": status, "missing": missing, "premises": values,
                     "actual_exercise": "NOT_ESTABLISHED", "open_end_proves_currentness": False})
    statuses = {r["status"] for r in rows}
    status = next(iter(statuses)) if len(statuses) == 1 else "UNKNOWN"
    return QueryResult("Q4", status, rows, unresolved=[x for r in rows for x in r["missing"]]).json()
