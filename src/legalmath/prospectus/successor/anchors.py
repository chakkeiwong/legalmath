"""Exact occurrence identity over a verified source graph."""
from .contracts import timestamp

def fields(row, allowed, required=()):
    if not isinstance(row, dict) or set(row) - set(allowed) or set(required) - set(row):
        raise ValueError("Unexpected or missing fields")
    return row

def bind(graph, source):
    fields(source, {"unit", "document", "source_sha256", "start", "end", "quote"},
           {"unit", "document", "source_sha256", "start", "end", "quote"})
    if graph is None:
        raise ValueError("Verified source graph required")
    matches = [u for u in graph["units"] if u["id"] == source["unit"]]
    if len(matches) > 1:
        raise ValueError("Duplicate source occurrence identity")
    unit = matches[0] if matches else None
    if unit is None or not unit.get("visible", False):
        raise ValueError("Source occurrence unavailable")
    if source["document"] != unit["document"] or source["source_sha256"] != unit["source_sha256"]:
        raise ValueError("Source edition mismatch")
    a, b = source["start"], source["end"]
    if type(a) is not int or type(b) is not int or not 0 <= a < b <= len(unit["raw"]):
        raise ValueError("Invalid source interval")
    if unit["raw"][a:b] != source["quote"]:
        raise ValueError("Source quote changed")
    result = {**source, "page": unit["page"], "bbox": unit.get("bbox")}
    if unit.get('geometry_issues'):
        result.update(geometry_issues=unit['geometry_issues'], image_sha256=unit.get('image_sha256'))
    return result

def _interval_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Interval endpoint requires a timezone-aware timestamp string")
    return timestamp(value)


def in_period(row, effective, known):
    start = _interval_timestamp(row["valid_from"])
    available = _interval_timestamp(row["known_from"])
    # Only absence or explicit null declares an open end. Malformed falsey
    # values must not silently extend an authority, fact or amendment interval.
    end = _interval_timestamp(row["valid_until"]) if row.get("valid_until") is not None else None
    withdrawn = _interval_timestamp(row["known_until"]) if row.get("known_until") is not None else None
    if end is not None and end <= start or withdrawn is not None and withdrawn <= available:
        raise ValueError("Invalid validity/knowledge interval")
    return (start <= effective and (end is None or effective < end)
            and available <= known and (withdrawn is None or known < withdrawn))
