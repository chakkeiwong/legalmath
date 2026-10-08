"""Verify the reviewed BASF table repairs against an immutable comparator."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REL = Path("docs/implementation/prospectus-basf-reference-repair")
PLAN = "docs/plans/prospectus-basf-reference-repair-2026-10-08.md"
REVIEW = REL / "source-review-002"
BASELINE = "docs/implementation/prospectus-adoption/phases/A1/attempt-007/product.json"
GRAPH = "docs/implementation/prospectus-repair-2026-10-06/phases/P1/attempt-009/source-graph.json"
NEW_RULES = {"different-rate-table-caption", "B24", "B25", "B26", "B27"}
LIMIT = 200 * 1024 * 1024


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def execute(base):
    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from legalmath.prospectus.successor import basf, jobs

    paths = [ROOT / PLAN, Path(__file__), ROOT / "pyproject.toml",
             ROOT / "tests/prospectus_successor/test_basf_sources.py", ROOT / REVIEW / "review.json"]
    paths += [p for p in (ROOT / "src/legalmath/prospectus/successor").glob("*")
              if p.suffix in {".py", ".json"}]
    methods = {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}
    previous = list(base.glob("run-*/manifest.json"))
    if sum(json.loads(p.read_text())["method"] == methods for p in previous) >= 3:
        raise ValueError("Three attempts for unchanged method exhausted")
    if sum(p.stat().st_size for p in base.rglob("*") if p.is_file()) > LIMIT - 35 * 1024 * 1024:
        raise ValueError("Insufficient space within 200 MB evidence bound")
    index = 1
    while (base / f"run-{index:03d}").exists():
        index += 1
    out = base / f"run-{index:03d}"
    out.mkdir()
    tick = time.monotonic()
    inputs, commands = {}, []
    failure, comparison, counts = None, None, None

    def bound(relative, expected=None):
        path = ROOT / relative
        observed = sha(path)
        if expected and observed != expected:
            raise ValueError("Changed source/comparator: " + str(relative))
        inputs[str(relative)] = observed
        return path

    def historical(relative):
        path = Path(relative)
        receipt = json.loads(bound(path.parent / "receipt.json").read_text())
        return json.loads(bound(path, receipt["outputs"][path.name]).read_text())

    try:
        graph, baseline = historical(GRAPH), historical(BASELINE)
        bound(BASELINE, "6c4172b8507803dbe898a8a0c7458c6882343c2604f36424e8e65b4c9384161f")
        admission = json.loads(bound(jobs.BASF).read_text())
        for source in admission["sources"].values():
            bound(source["original"], source["sha256"])
        review = json.loads(bound(REVIEW / "review.json").read_text())
        bound("src/legalmath/prospectus/successor/basf_scope_review.json", review["data_sha256"])
        for name, expected in review["evidence"].items():
            bound(name, expected)
        argv = [str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q",
                "tests/prospectus_successor/test_basf_sources.py", "--junitxml=" + str(out / "tests.xml")]
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "CUDA_VISIBLE_DEVICES": "-1"}
        start = time.monotonic()
        run = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
        (out / "tests.txt").write_text(run.stdout + run.stderr)
        commands.append({"argv": argv, "returncode": run.returncode, "wall_seconds": time.monotonic() - start})
        suites = ET.parse(out / "tests.xml").getroot()
        counts = {key: sum(int(s.get(key, "0")) for s in suites.iter("testsuite"))
                  for key in ("tests", "failures", "errors", "skipped")}
        if run.returncode:
            raise ValueError("Focused tests failed; see tests.txt")
        current = basf.construct(graph, admission)
        if current["raw_body"] != baseline["raw_body"] or current["source_map"] != baseline["source_map"]:
            raise ValueError("Raw source characters or occurrence order changed")
        old_edits = [e for e in current["operations"] if e.get("scope_rule") not in NEW_RULES]
        delta = [e for e in current["operations"] if e.get("scope_rule") in NEW_RULES]
        if old_edits != baseline["operations"] or {e["scope_rule"] for e in delta} != NEW_RULES or len(delta) != 5:
            raise ValueError("Change exceeded the five reviewed edits")
        expected_text = baseline["candidate_text"]
        for edit in sorted(delta, key=lambda e: e["start"], reverse=True):
            spans = [m for m in baseline["character_map"] if m["operation"] == "COPY"
                     and m["raw_start"] <= edit["start"] < edit["end"] <= m["raw_end"]]
            if len(spans) != 1 or edit["new"]:
                raise ValueError("Delta is not an exact reviewed deletion of copied text")
            a = spans[0]["start"] + edit["start"] - spans[0]["raw_start"]
            b = a + edit["end"] - edit["start"]
            if expected_text[a:b] != edit["old"]:
                raise ValueError("Delta does not match baseline rendered text")
            expected_text = expected_text[:a] + expected_text[b:]
        if current["candidate_text"] != expected_text:
            raise ValueError("Unreviewed rendered text changed")
        by_id = {u["id"]: u for u in graph["units"]}
        for span in current["source_map"]:
            if current["raw_body"][span["start"]:span["end"]] != by_id[span["unit"]]["raw"]:
                raise ValueError("Source occurrence changed")
        for span in current["character_map"]:
            if span["operation"] == "COPY" and current["candidate_text"][span["start"]:span["end"]] != current["raw_body"][span["raw_start"]:span["raw_end"]]:
                raise ValueError("Copied source characters changed")
        if current["interval_accounting"]["gaps"] or current["full_german_contract_constructed"]:
            raise ValueError("Conservation or acceptance boundary failed")
        inventory = json.loads(bound(REVIEW / "dispositions.json").read_text())
        remaining = {(r["start"], r["end"]) for r in current["remaining_brackets"]}
        if remaining != {(r["start"], r["end"]) for r in inventory if r["status"] == "UNRESOLVED"}:
            raise ValueError("Residuals differ from the reviewed inventory")
        comparison = {"status": "REVIEWED_TABLE_REPAIR_PASS", "new_rules": sorted(NEW_RULES),
            "source_occurrences_preserved": len(current["source_map"]), "unchanged_prior_operations": True,
            "only_five_reviewed_deletions": True, "before": {
                "remaining_brackets": len(baseline["remaining_brackets"]),
                "unresolved_intervals": len(baseline["interval_accounting"]["unresolved"])},
            "after": {"remaining_brackets": len(remaining),
                "unresolved_intervals": len(current["interval_accounting"]["unresolved"])},
            "remaining_inventory": [r for r in inventory if r["status"] == "UNRESOLVED"],
            "counts_are_explanatory_only": True, "independent_legal_review": False}
        save(out / "comparison.json", comparison)
        save(out / "product.json", current)
        (out / "candidate.txt").write_text(current["candidate_text"])
        for name, expected in {**methods, **inputs}.items():
            if sha(ROOT / name) != expected:
                raise ValueError("Method/evidence drift during verification: " + name)
        if sum(p.stat().st_size for p in base.rglob("*") if p.is_file()) > LIMIT:
            raise ValueError("200 MB evidence bound exceeded")
    except Exception as exc:
        failure = str(exc)
        save(out / "failure.json", {"error": failure})
    next_phase = {"attempt": str(out.relative_to(ROOT)), "status": "REPAIR_REQUIRED" if failure else "VERIFY_INSTALLED",
        "failure": failure, "remaining": comparison["remaining_inventory"] if comparison else [],
        "command": "python3 -m scripts.prospectus_basf_reference_repair" if failure else
                   "python3 -m scripts.verify_prospectus_adoption",
        "review": "Repair observed failure" if failure else "PASS for installed verification; acceptance pending"}
    save(out / "next-phase.json", next_phase)
    save(out / "manifest.json", {"status": "FAILED" if failure else "REVIEWED_TABLE_REPAIR_PASS; LEGAL_ACCEPTANCE_PENDING",
        "failure": failure, "command": [sys.executable, "-m", "scripts.prospectus_basf_reference_repair"],
        "commands": commands, "wall_seconds": time.monotonic() - tick,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "environment": {"driver": sys.version, "application_python": str(ROOT / ".venv/bin/python"),
                        "PYTHONPATH": str(ROOT / "src"), "CUDA_VISIBLE_DEVICES": "-1"},
        "cpu_gpu": "CPU; GPU intentionally hidden; driver imports no GPU library",
        "random_seeds": "N/A; deterministic source checks", "data_version": basf.SHA,
        "plan": PLAN, "result_file": str(REL / "RESULT.md"), "method": methods, "inputs": inputs,
        "tests": counts, "outputs": {p.name: sha(p) for p in out.iterdir() if p.is_file()}})
    save(base / "next-phase.json", next_phase)
    print(json.dumps({"directory": str(out.relative_to(ROOT)), "failure": failure, "tests": counts,
                      "after": comparison["after"] if comparison else None}, indent=2))
    return 1 if failure else 0


def main():
    base = ROOT / REL
    base.mkdir(parents=True, exist_ok=True)
    with (base / ".run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raise SystemExit(execute(base))


if __name__ == "__main__":
    main()
