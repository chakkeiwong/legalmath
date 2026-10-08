import importlib.util
import json
from pathlib import Path
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("catala_master", ROOT / "scripts/catala_master_program.py")
MASTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MASTER)


def test_review_is_bound_to_exact_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(MASTER, "reviewed_inputs", lambda: {"program.py": "new"})
    review = tmp_path / "review.json"
    review.write_text(json.dumps({"verdict": "PASS_FOR_BOUNDED_EXECUTION",
                                  "reviewed_inputs": {"program.py": "old"}}))
    with pytest.raises(ValueError, match="changed after"):
        MASTER.verify_review(review)


def test_failed_phase_stops_dependents_but_records_decision(tmp_path):
    run = MASTER.Run.__new__(MASTER.Run)
    run.out, run.records, run.started = tmp_path, [], time.monotonic()
    run.run_manifest = {"phases": run.records}
    run.freeze = lambda: {"frozen": True}

    def fail():
        raise RuntimeError("deliberate toolchain failure")

    def unexpected():
        raise AssertionError("dependent phase must not execute")

    run.toolchain = fail
    for name in MASTER.PHASES[2:7]:
        setattr(run, name, unexpected)
    assert run.execute() == 1
    assert [r["status"] for r in run.records] == ["PASS", "FAIL", *(["NOT_RUN"] * 5), "PASS"]
    decision = json.loads((tmp_path / "decision.json").read_text())
    assert decision["decision"] == "NOT_PROMOTED" and not decision["optional_pilot_viable"]
    assert json.loads((tmp_path / "run-manifest.json").read_text())["execution_status"] == "FAILED"


def test_existing_evidence_directory_cannot_be_reused(tmp_path):
    class Args:
        out = tmp_path

    with pytest.raises(ValueError, match="new output directory"):
        MASTER.Run(Args())
