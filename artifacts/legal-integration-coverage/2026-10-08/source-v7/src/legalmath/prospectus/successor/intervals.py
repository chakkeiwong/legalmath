"""Independent source-interval accounting, separate from rendered output."""
from .anchors import bind
from .contracts import digest

DISPOSITIONS = {"COPIED", "EXCLUDED_BY_CHOICE", "REPLACED_TEMPLATE", "SUPERSEDED",
                "INACTIVE_REPLACEMENT", "REFERENCE", "PREMISE", "UNRESOLVED"}


def check(graph, records, relevant=None):
    """Sweep interval boundaries rather than reusing the renderer's coverage set.

    Dispositions are per use: exclusion of one use cannot cancel a copied use.
    Bytes without a disposition, including instructions, remain unresolved.
    """
    units = {u["id"]: u for u in graph["units"]}
    relevant = set(relevant) if relevant is not None else {k for k, u in units.items() if u["visible"]}
    if relevant - units.keys():
        raise ValueError("Unknown accounting scope")
    by_unit, uses = {}, {}
    for row in records:
        source = bind(graph, row["source"])
        if row["disposition"] not in DISPOSITIONS or not row.get("use") or not row.get("reason"):
            raise ValueError("Invalid interval disposition")
        if row["disposition"] in {"EXCLUDED_BY_CHOICE", "SUPERSEDED", "INACTIVE_REPLACEMENT", "REPLACED_TEMPLATE"}:
            if not row.get("binding"):
                raise ValueError("Exclusion/replacement requires a decision binding")
        identity = (tuple(row["use"]), source["unit"], source["start"], source["end"])
        if identity in uses and uses[identity] != row["disposition"]:
            raise ValueError("Contradictory dispositions for the same use")
        uses[identity] = row["disposition"]
        by_unit.setdefault(source["unit"], []).append(row)
    gaps, unresolved = [], []
    for key in sorted(relevant):
        raw = units[key]["raw"]
        rows = by_unit.get(key, [])
        boundaries = sorted({0, len(raw)} | {r["source"][k] for r in rows for k in ("start", "end")})
        if not raw.strip():
            unresolved.append({"unit": key, "start": 0, "end": len(raw), "reason": "Empty or unread source"})
        for a, b in zip(boundaries, boundaries[1:]):
            if not raw[a:b].strip():
                continue
            covering = [r for r in rows if r["source"]["start"] <= a and b <= r["source"]["end"]]
            if not covering:
                gaps.append({"unit": key, "start": a, "end": b, "quote": raw[a:b], "reason": "No occurrence disposition"})
            elif any(r["disposition"] == "UNRESOLVED" for r in covering):
                unresolved.append({"unit": key, "start": a, "end": b, "reason": "Unresolved use of source"})
    return {"version": "interval-accounting.v1", "records_sha256": digest(records),
            "scope": sorted(relevant), "gaps": gaps, "unresolved": unresolved,
            "complete": not gaps and not unresolved}
