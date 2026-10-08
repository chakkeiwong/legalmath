#!/usr/bin/env python3
"""Read-only comparison of every unresolved clause before/after continuation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/implementation/prospectus-evidence-continuation"
BASE = ROOT / "docs/implementation/prospectus-evidence-master/phases/E7/attempt-002"


def read(path):
    return json.loads(path.read_text())


def key(e):
    return e["document"], e["start"], e["end"], e["quote"], e["kind"]


def main():
    state = read(OUT / "state.json")
    phase = state["phases"]["C1"]
    if phase["status"] not in {"PASS", "QUALIFIED"}:
        raise ValueError("A completed C1 replay is required")
    path = ROOT / phase["directory"] / "run/classification.json"
    before = {r["id"]: r for r in read(BASE / "classification.json")["results"]}
    after = {r["id"]: r for r in read(path)["results"]}
    if set(before) != set(after):
        raise ValueError("Case identities changed")
    changed, resolved, newly_unresolved, per_issue = [], [], [], []
    for issue, old in before.items():
        new = after[issue]
        if old["answer"] is not new["answer"]:
            changed.append({"id": issue, "before": old["answer"], "after": new["answer"]})
        old_open = {key(e): e for e in old["evidence"] if e["disposition"].startswith("unresolved")}
        new_open = {key(e): e for e in new["evidence"] if e["disposition"].startswith("unresolved")}
        new_by_key = {}
        for e in new["evidence"]:
            new_by_key.setdefault(key(e), []).append(e)
        for k in old_open.keys() - new_open.keys():
            e = old_open[k]
            resolved.append({"issue": issue, "old_id": e["id"], "document": e["document"],
                             "page": e["page"], "end_page": e["end_page"], "quote": e["quote"],
                             "old_disposition": e["disposition"],
                             "new_dispositions": sorted({x["disposition"] for x in new_by_key.get(k, [])})})
        for k in new_open.keys() - old_open.keys():
            newly_unresolved.append({"issue": issue, **new_open[k]})
        per_issue.append({"id": issue, "answer": new["answer"], "before": len(old_open), "after": len(new_open)})
    result = {
        "review_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "classification": str(path.relative_to(ROOT)),
        "classification_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "answer_changes": changed,
        "unresolved_before": sum(r["before"] for r in per_issue),
        "unresolved_after": sum(r["after"] for r in per_issue),
        "resolved_or_resegmented": sorted(resolved, key=lambda r: (r["issue"], r["page"], r["old_id"])),
        "newly_unresolved": newly_unresolved,
        "per_issue": per_issue,
        "limit": "Source-text comparison only; disposition changes require contextual review."
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
