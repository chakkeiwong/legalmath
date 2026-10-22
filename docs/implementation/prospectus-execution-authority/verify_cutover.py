"""Retain a final snapshot; do not seal the mutable authority as a package."""
import ast
from collections import Counter
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus.execution_authority import Authority, CODE, REL, file_hash, read, write
from legalmath.prospectus.successor import closure_program


def main():
    started = time.monotonic()
    base = ROOT / REL
    target = base / "verification/final-001.json"
    if target.exists():
        raise ValueError("Final verification snapshot already retained")
    authority = Authority(ROOT)
    state = authority.status()
    events = authority.events()
    assert state == read(base / "state.json")
    assert state["revision"] == 3 and not state["running"]
    assert state["next_task"] == "portuguese-2008"
    rows = {t["id"]: t for t in state["tasks"]}
    assert rows["native-cohort"]["state"] == rows["native-interfaces"]["state"] == "COMPLETE"
    assert rows["native-layout-cases"]["state"] == rows["native-candidates"]["state"] == "RESULT_RECORDED"
    assert len(state["obligations"]) == 59 and len(rows) == 44
    assert not any(o["complete"] for o in state["obligations"])
    assert not any(state["completion"].values()) and not state["program_complete"]
    outputs, files_checked = {}, 0
    admissions = []
    for event in events:
        if event["kind"] == "ADMIT":
            path = ROOT / event["attempt"] / "admission.json"
            assert file_hash(path) == event["admission_sha256"]
            admissions.append(event["attempt"])
        if event["kind"] in {"ACCEPT", "RECORD", "REJECT"} and event.get("outputs_sha256"):
            assert authority.retained_evidence_valid(event)
            outputs[event["attempt"]] = event["outputs_sha256"]
            files_checked += len(read(ROOT / event["attempt"] / "outputs.json"))
    current = closure_program.status(ROOT)
    previous = read(ROOT / "docs/implementation/prospectus-integration-closure/ocr-geometry-repair-2026-10-12/final-current-status.json")
    receipts = {r["phase"]: r["receipt_sha256"] for r in current["phases"]}
    assert len(receipts) == 9
    assert all(r["current"] and r["artifact_valid"] and r["engineering_checks"] == "PASS" for r in current["phases"])
    assert receipts == {r["phase"]: r["receipt_sha256"] for r in previous["phases"]}
    checks = base / "checks/attempt-005.xml"
    suites = ET.parse(checks).getroot().findall(".//testsuite")
    assert sum(int(s.attrib["tests"]) for s in suites) == 41
    assert all(int(s.attrib["failures"]) == int(s.attrib["errors"]) == 0 for s in suites)
    syntax = list(CODE) + ["tests/prospectus/test_execution_authority.py"] + [str(p.relative_to(ROOT)) for p in base.rglob("*.py")]
    for name in syntax:
        ast.parse((ROOT / name).read_text(), filename=name)
    whitespace = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True)
    assert whitespace.returncode == 0, whitespace.stdout + whitespace.stderr
    documents = [REL + "/" + name for name in ("CUTOVER.md", "OPERATIONS.md", "CONTINUATION-REVIEW.md")]
    snapshot = {"status": "PASS", "command": "timeout 120 .venv/bin/python " + str(Path(__file__).relative_to(ROOT)),
                "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "program_sha256": state["program_sha256"], "revision": state["revision"],
                "event_head": state["event_head"], "events": len(events),
                "admissions": admissions, "output_manifests": outputs, "output_files_checked": files_checked,
                "current_unchanged_receipts": receipts, "task_states": dict(Counter(t["state"] for t in rows.values())),
                "next_task": state["next_task"], "all_original_obligations_open": True,
                "authority_code": {name: file_hash(ROOT / name) for name in CODE},
                "syntax_files": len(syntax), "checks": {"file": str(checks.relative_to(ROOT)), "sha256": file_hash(checks), "passed": 41},
                "documents": {name: file_hash(ROOT / name) for name in documents},
                "whitespace_check": "PASS", "method_sha256": file_hash(Path(__file__)),
                "interpreter": sys.executable, "cpu_gpu": "CPU only; no GPU imports", "random_seeds": "N/A; deterministic consistency check",
                "wall_seconds": time.monotonic() - started,
                "plan": "docs/plans/prospectus-execution-authority-2026-10-12.md",
                "completion": state["completion"], "program_complete": False,
                "limits": "Snapshot of consistency and bounded execution, not whole-program completion or legal acceptance; live authority files remain mutable through reviewed operations"}
    write(target, snapshot, exclusive=True)
    print({"status": "PASS", "current_receipts": 9, "checks_passed": 41,
           "output_files_checked": files_checked, "next_task": state["next_task"], "wall_seconds": snapshot["wall_seconds"]})


if __name__ == "__main__":
    main()
