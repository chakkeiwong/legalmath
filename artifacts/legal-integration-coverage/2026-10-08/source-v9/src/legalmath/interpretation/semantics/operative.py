"""Immutable, source-bound operative wording overlays; no legal closure."""
from copy import deepcopy
from pathlib import Path
from ...canonical import digest, canonical, raw_digest
from ...errors import LegalMathError

PROFILE = "legalmath.operative-overlay.v1"


def fail(reason):
    raise LegalMathError("E_INTEGRITY", details=reason)


def value_at(obj, path):
    for key in path:
        if isinstance(obj, list):
            if type(key) is not int or not 0 <= key < len(obj):
                fail("Invalid list field")
        elif not isinstance(obj, dict) or type(key) is not str or key not in obj:
            fail("Unknown operative field")
        obj = obj[key]
    return obj


def allowed_path(path):
    if len(path) == 2 and path == ["reading", "explanation"]:
        return True
    if (len(path) == 3 and path[0] == "reading" and
            path[1] == "remaining_questions" and type(path[2]) is int):
        return True
    if (len(path) == 4 and path[:2] == ["candidate_repair", "dimensions"] and
            type(path[2]) is int and path[3] == "explanation"):
        return True
    return (len(path) == 3 and path[:2] == ["candidate_repair", "unresolved_questions"]
            and type(path[2]) is int)


def build_overlay(records, patches, *, expected_pointer, current_pointer, evidence):
    if current_pointer() != expected_pointer:
        fail("Active pointer changed before overlay preparation")
    keys = [(r["role"], r["reading_id"]) for r in records]
    if len(keys) != len(set(keys)):
        fail("Duplicate role/reading identity")
    original = dict(zip(keys, records))
    output = deepcopy(records)
    changed = dict(zip(keys, output))
    seen, changes = set(), []
    if not patches:
        fail("Empty overlay")
    for patch in patches:
        required = {"role", "reading_id", "path", "before", "after", "reason", "evidence_ids"}
        if set(patch) != required or not allowed_path(patch["path"]):
            fail("Overlay is restricted to declared operative prose")
        key = (patch["role"], patch["reading_id"])
        identity = (*key, tuple(patch["path"]))
        if key not in original or identity in seen:
            fail("Missing or repeated field identity")
        seen.add(identity)
        if not patch["reason"] or not patch["evidence_ids"] or any(
                i not in evidence for i in patch["evidence_ids"]):
            fail("Missing source/acquisition evidence")
        before = value_at(original[key]["operative"], patch["path"])
        if not isinstance(before, str) or before != patch["before"]:
            fail("Operative text differs from reviewed precondition")
        if not isinstance(patch["after"], str) or not patch["after"] or before == patch["after"]:
            fail("Invalid replacement")
        parent = value_at(changed[key]["operative"], patch["path"][:-1])
        parent[patch["path"][-1]] = patch["after"]
        changes.append({**deepcopy(patch), "predecessor_record_hash": digest(original[key]),
                        "source_evidence": [deepcopy(evidence[i]) for i in patch["evidence_ids"]]})
    if current_pointer() != expected_pointer:
        fail("Active pointer changed before overlay write")
    return {"profile": PROFILE, "pointer_hash": expected_pointer,
            "baseline_hash": digest(records), "patch_hash": digest(patches),
            "records": output, "changes": changes, "formula_changes": 0,
            "accepted_substantive_repairs": 0, "release_eligible": False}


def write_overlay(path, overlay, *, current_pointer):
    path = Path(path)
    if current_pointer() != overlay["pointer_hash"]:
        fail("Active pointer changed before overlay write")
    if path.exists():
        fail("An immutable overlay already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical(overlay)
    with path.open("xb") as stream:
        stream.write(raw)
    return {"path": str(path), "sha256": raw_digest(raw)}
