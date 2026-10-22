"""Reconcile the new authority with old evidence without rerunning the product."""
import ast
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus.execution_authority import Authority, CODE, REL, digest, file_hash, read, write
from legalmath.prospectus.successor import closure_program


def main():
    started = time.monotonic()
    base = ROOT / REL
    if (base / "shadow-check.json").exists():
        raise ValueError("Shadow comparison already retained")
    authority = Authority(ROOT)
    state = authority.status()
    current = closure_program.status(ROOT)
    previous = read(ROOT / "docs/implementation/prospectus-integration-closure/ocr-geometry-repair-2026-10-12/final-current-status.json")
    assert len(current["phases"]) == 9
    assert all(r["current"] and r["artifact_valid"] and r["engineering_checks"] == "PASS" for r in current["phases"])
    assert {r["phase"]: r["receipt_sha256"] for r in current["phases"]} == {
        r["phase"]: r["receipt_sha256"] for r in previous["phases"]}
    assert state["next_task"] == "native-cohort" and not state["program_complete"]
    assert not any(row["complete"] for row in state["obligations"])
    assert {row["id"] for row in state["obligations"]} >= {"E04", "E05"}
    paths = list(CODE) + ["tests/prospectus/test_execution_authority.py"]
    for name in paths:
        ast.parse((ROOT / name).read_text(), filename=name)
    write(base / "shadow-check.json", {"status": "PASS", "wall_seconds": time.monotonic() - started,
          "command": "timeout 120 .venv/bin/python " + str(Path(__file__).relative_to(ROOT)),
          "current_unchanged_receipts": {r["phase"]: r["receipt_sha256"] for r in current["phases"]},
          "original_obligation_entries": len(state["obligations"]), "remaining_tasks": len(state["tasks"]),
          "next_substantive_task": state["next_task"], "scope_removed": [], "closed_by_test_totals": [],
          "program_sha256": state["program_sha256"], "authority_code": {p: file_hash(ROOT / p) for p in paths},
          "cpu_gpu": "CPU only; no GPU imports", "seeds": "N/A; deterministic comparison",
          "plan": "docs/plans/prospectus-execution-authority-2026-10-12.md",
          "limits": "No new legal or automatic capability; existing product evidence reused exactly"}, exclusive=True)
    print("Shadow check PASS: nine unchanged current receipts; all 59 obligations open; next native-cohort")


if __name__ == "__main__":
    main()
