from functools import partial
from pathlib import Path
import pytest
from legalmath.prospectus import campaign, archive
from legalmath.prospectus.common import read, write
from .test_evidence import archive_fixture


def controller(tmp_path, monkeypatch):
    program = tmp_path / "program"; program.mkdir()
    write(program / "allowlist.json", {"max_attempts_per_phase": 3, "max_campaign_seconds": 60})
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    monkeypatch.setattr(campaign, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(campaign, "PROGRAM", program)
    monkeypatch.setattr(campaign, "relative", lambda p: str(Path(p).relative_to(tmp_path)))
    fingerprint = {"revision": 1}
    monkeypatch.setattr(campaign, "material_inputs", lambda phase: fingerprint.copy())
    return campaign.state(), fingerprint


def test_failed_phase_repairs_and_refreshes_before_resume(tmp_path, monkeypatch):
    current, fingerprint = controller(tmp_path, monkeypatch)
    source_root = tmp_path / "sources"; source_root.mkdir()
    archive_fixture(source_root)
    (source_root / "text/test.json").write_text('{"broken":true}')
    repair = partial(archive.derivative_repairs, root=source_root)
    monkeypatch.setattr(archive, "derivative_repairs", repair)
    def work(phase, directory, state):
        if repair():
            raise campaign.RepairableError("Derivative mismatch")
        return {"status": "CHECKED", "resolved": ["Derivative rebuilt from unchanged original"]}
    monkeypatch.setattr(campaign, "work", work)
    campaign.run_with_repairs("P0", current)
    assert [e["event"] for e in current["events"]] == ["attempt", "failure", "repair", "attempt", "complete"]
    failed = tmp_path / "runs/P0/attempt-001"
    assert (failed / "failure.json").exists()
    assert read(failed / "next-phase-plan.json")["next_phase"] == "P0"
    assert read(tmp_path / "program/next-phase-plan.json")["next_phase"] == "P1"
    assert campaign.completed(current, "P0")
    events = len(current["events"])
    campaign.run_with_repairs("P0", current)
    assert len(current["events"]) == events
    fingerprint["revision"] = 2
    assert not campaign.completed(current, "P0")
    with pytest.raises(ValueError, match="prerequisite"):
        campaign.run_phase("P1", current)


def test_output_tamper_invalidates_completion(tmp_path, monkeypatch):
    current, _ = controller(tmp_path, monkeypatch)
    monkeypatch.setattr(campaign, "work", lambda *args: {"status": "CHECKED"})
    campaign.run_phase("P0", current)
    path = tmp_path / current["phases"]["P0"]["directory"] / "result.json"
    write(path, {"status": "CHECKED", "forged": True})
    assert not campaign.completed(current, "P0")


def test_arbitrary_failure_cannot_trigger_repair(tmp_path, monkeypatch):
    current, _ = controller(tmp_path, monkeypatch)
    def fail(*args):
        raise ValueError("Invalid mathematical target")
    monkeypatch.setattr(campaign, "work", fail)
    with pytest.raises(ValueError, match="mathematical"):
        campaign.run_with_repairs("P0", current)
    assert current["phases"]["P0"]["status"] == "FAILED"
    assert not any(e["event"] == "repair" for e in current["events"])


def test_changed_code_during_run_cannot_get_current_receipt(tmp_path, monkeypatch):
    current, fingerprint = controller(tmp_path, monkeypatch)
    monkeypatch.setattr(campaign, "completed", lambda state, phase: phase in ("P0", "P1"))
    def mutate(*args):
        fingerprint["revision"] += 1
        return {"status": "CHECKED"}
    monkeypatch.setattr(campaign, "work", mutate)
    with pytest.raises(ValueError, match="changed while"):
        campaign.run_phase("P2", current)
