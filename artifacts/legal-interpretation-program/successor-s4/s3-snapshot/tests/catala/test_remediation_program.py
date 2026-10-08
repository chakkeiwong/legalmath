import importlib.util
import time
from pathlib import Path
import pytest
from legalmath.canonical import canonical, loads

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("catala_remediation", ROOT / "scripts/catala_remediation_program.py")
MASTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MASTER)


def test_changed_review_inputs_reject_execution(tmp_path, monkeypatch):
    review = tmp_path / "review.json"
    review.write_bytes(canonical({"verdict": "PASS_FOR_IMPLEMENTATION", "inputs": {"generator.py": "old"}}))
    monkeypatch.setattr(MASTER, "inputs", lambda: {"generator.py": "new"})
    with pytest.raises(ValueError, match="changed after review"):
        MASTER.Run(tmp_path / "run", review)
    assert not (tmp_path / "run").exists()


def test_failure_stops_dependents_and_records_failed_decision(tmp_path, monkeypatch):
    run = MASTER.Run.__new__(MASTER.Run)
    run.out, run.started, run.records = tmp_path, time.monotonic(), []
    run.summary = {"phases": run.records}
    run.review = {"inputs": {}}
    monkeypatch.setattr(MASTER, "inputs", lambda: {})
    run.synchronize = lambda: {"merged": True}
    def fail(): raise RuntimeError("Broken pinned compiler")
    run.toolchain = fail
    def forbidden(): raise AssertionError("A dependent phase executed")
    for name in MASTER.PHASES[2:-1]: setattr(run, name, forbidden)
    assert run.execute() == 1
    assert [r["status"] for r in run.records] == ["PASS", "FAIL", *(["NOT_RUN"] * 5), "PASS"]
    assert loads((tmp_path / "decision.json").read_bytes())["optional_backend_viable"] is False
    assert loads((tmp_path / "run-manifest.json").read_bytes())["status"] == "FAIL"
