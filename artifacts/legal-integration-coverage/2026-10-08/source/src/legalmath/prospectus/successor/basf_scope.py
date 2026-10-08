"""Apply occurrence-bound readings of the retained BASF pages, failing closed."""
import json
from importlib.resources import files

from .anchors import bind
from .contracts import digest

VERSION = "basf-reviewed-scope.v1"
GUARD_FIELDS = ("id", "document", "source_sha256", "page", "raw", "bbox",
                "text_sha256", "visible")


def review_data():
    return json.loads(files(__package__).joinpath("basf_scope_review.json").read_text(encoding="utf-8"))


def reviewed_edits(graph, admission, raw, source_map, pairs):
    """Return edits and their evidence; this is not independent legal approval."""
    data = review_data()
    if (data["version"] != VERSION or data["instrument_id"] != admission["issue_id"]
            or graph["instrument_id"] != data["instrument_id"]
            or data["admission_sha256"] != digest(admission)
            or data["raw_body_sha256"] != digest(raw.encode())
            or tuple(data["guard_fields"]) != GUARD_FIELDS
            or data["independent_legal_review"] is not False):
        raise ValueError("BASF scope review differs from source or admission")
    units = {u["id"]: u for u in graph["units"]}
    if len(units) != len(graph["units"]):
        raise ValueError("Duplicate BASF source occurrence")
    guarded_ids = {u["id"] for u in graph["units"]
                   if u["page"] in data["guarded_pages"].get(u["document"], [])}
    if guarded_ids != set(data["units"]):
        raise ValueError("BASF reviewed page membership changed")
    for key, expected in data["units"].items():
        unit = units.get(key)
        if unit is None or digest({k: unit.get(k) for k in GUARD_FIELDS}) != expected:
            raise ValueError("BASF reviewed occurrence changed: " + key)
    mapped = {s["unit"]: s for s in source_map}
    if len(mapped) != len(source_map):
        raise ValueError("Duplicate BASF body occurrence")
    bracket_pairs = {(a, b) for a, b, _ in pairs}
    edits, resolved, applied, identities, targets = [], set(), [], set(), set()

    def checked(source):
        if source["unit"] not in data["units"]:
            raise ValueError("BASF scope evidence lacks a reviewed unit guard")
        return bind(graph, source)

    for rule in data["rules"]:
        target = rule["target"]
        a, b = target["start"], target["end"]
        if (rule["id"] in identities or (a, b) in targets
                or (a, b) not in bracket_pairs or raw[a:b] != target["text"]):
            raise ValueError("BASF scope target changed or duplicated")
        identities.add(rule["id"])
        targets.add((a, b))
        # Reconstruct the exact intersections with the raw body. Newlines are
        # assembly separators; every source character must have its own anchor.
        expected_spans = []
        for span in source_map:
            left, right = max(a, span["start"]), min(b, span["end"])
            if left < right:
                unit = units[span["unit"]]
                expected_spans.append({"unit": unit["id"], "document": unit["document"],
                    "source_sha256": unit["source_sha256"], "start": left-span["start"],
                    "end": right-span["start"], "quote": raw[left:right]})
        if not expected_spans or target["spans"] != expected_spans:
            raise ValueError("BASF target occurrence map changed")
        for source in target["spans"]:
            checked(source)
        if not rule["premises"]:
            raise ValueError("BASF scope selection lacks final-term premises")
        for source in rule["premises"] + rule["governing"]:
            checked(source)
        operation = rule["operation"]
        if operation == "select":
            replacements = [(a, a+1, ""), (b-1, b, "")]
        elif operation == "instruction":
            opening = raw.find(":", a, b)
            if opening < 0 or "anwendbar" not in raw[a:opening]:
                raise ValueError("BASF inline instruction boundary changed")
            replacements = [(a, opening+1, ""), (b-1, b, "")]
        elif operation == "exclude":
            replacements = [(a, b, "")]
        elif operation == "substitute":
            checked(rule["value"])
            if rule["value"] not in rule["premises"]:
                raise ValueError("BASF replacement lacks value premise")
            replacements = [(a, b, rule["value"]["quote"])]
        else:
            raise ValueError("Unknown BASF scope operation")
        basis = rule.get("value", rule["premises"][0])
        for left, right, new in replacements:
            edits.append({"start": left, "end": right, "old": raw[left:right], "new": new,
                "reason": rule["reason"], "basis": basis, "review": rule["review"],
                "scope_rule": rule["id"], "premises": rule["premises"],
                "governing": rule["governing"]})
        resolved.add((a, b))
        applied.append({"rule": "scope:" + rule["id"], "status": operation.upper(),
                        "start": a, "end": b})
    edits.sort(key=lambda e: e["start"])
    if any(left["end"] > right["start"] for left, right in zip(edits, edits[1:])):
        raise ValueError("Overlapping BASF scope operations")
    return edits, resolved, applied, {
        "version": VERSION, "review_sha256": digest(data), "source_review": data["source_review"],
        "decisions": data["rules"], "independent_legal_review": False}
