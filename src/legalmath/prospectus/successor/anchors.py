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
    unit = next((u for u in graph["units"] if u["id"] == source["unit"]), None)
    if unit is None or not unit.get("visible", False):
        raise ValueError("Source occurrence unavailable")
    if source["document"] != unit["document"] or source["source_sha256"] != unit["source_sha256"]:
        raise ValueError("Source edition mismatch")
    a, b = source["start"], source["end"]
    if type(a) is not int or type(b) is not int or not 0 <= a < b <= len(unit["raw"]):
        raise ValueError("Invalid source interval")
    if unit["raw"][a:b] != source["quote"]:
        raise ValueError("Source quote changed")
    return {**source, "page": unit["page"], "bbox": unit.get("bbox")}

def in_period(row, effective, known):
    start, available = timestamp(row["valid_from"]), timestamp(row["known_from"])
    end = timestamp(row["valid_until"]) if row.get("valid_until") else None
    withdrawn = timestamp(row["known_until"]) if row.get("known_until") else None
    if end is not None and end <= start or withdrawn is not None and withdrawn <= available:
        raise ValueError("Invalid validity/knowledge interval")
    return (start <= effective and (end is None or effective < end)
            and available <= known and (withdrawn is None or known < withdrawn))
