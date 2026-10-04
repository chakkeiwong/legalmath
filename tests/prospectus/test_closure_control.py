from datetime import datetime, timedelta, timezone

import pytest

from legalmath.prospectus import evidence_closure as ec, closure_phases as p


def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(ec, "ROOT", tmp_path)
    monkeypatch.setattr(ec, "OUT", tmp_path / "out")
    monkeypatch.setattr(ec, "DATA", tmp_path / "data")
    monkeypatch.setattr(ec, "PLAN", tmp_path / "plan.md")
    monkeypatch.setattr(ec.c, "ROOT", tmp_path)
    ec.OUT.mkdir(); ec.DATA.mkdir()
    monkeypatch.setattr(ec, "method", lambda: {"method": "v1"})
    monkeypatch.setattr(ec, "preserve", lambda: {"files": 1})
    monkeypatch.setattr(ec, "policy", lambda: {"max_execution_seconds": 14400, "max_command_seconds": 900,
                                               "max_failures_per_input": 3})
    monkeypatch.setattr(ec.subprocess, "check_output", lambda *a, **k: "commit\n")
    monkeypatch.setattr(ec, "execute", lambda *a: {"status": "QUALIFIED", "remaining": ["Source evidence absent"]})
    ec.c.write(ec.OUT / "baseline.json", {"files": {}})
    return ec.state()


def test_resume_noop_and_open_evidence_does_not_block_independent_work(tmp_path, monkeypatch):
    current = setup(tmp_path, monkeypatch)
    for phase in ec.PHASES: ec.run_phase(phase, current)
    original = ec.c.digest(current)
    for phase in ec.PHASES: ec.run_phase(phase, current)
    assert ec.c.digest(current) == original
    verified = ec.verify(current)
    assert verified["status"] == "PASS" and not verified["next"]["all_gaps_closed"]
    assert verified["next"]["remaining"] == ["Source evidence absent"]


def test_later_input_invalidates_all_consumers_but_not_independent_phase(tmp_path, monkeypatch):
    current = setup(tmp_path, monkeypatch)
    for phase in ec.PHASES: ec.run_phase(phase, current)
    ec.c.write(ec.DATA / "facts.json", {"new": True})
    assert ec.current_phase("S2", current)
    assert not ec.current_phase("S3", current) and not ec.current_phase("S5", current)
    assert not ec.current_phase("S7", current)
    assert ec.refresh(current)["ready"] == ["S3"]


@pytest.mark.parametrize("filename", ["result.json", "receipt.json", "manifest.json"])
def test_tampered_artifact_rejected(tmp_path, monkeypatch, filename):
    current = setup(tmp_path, monkeypatch)
    item = ec.run_phase("S0", current)
    (tmp_path / item["directory"] / filename).write_text("{}")
    with pytest.raises(ValueError, match="changed"):
        ec.verify(current)


def test_crash_charges_budget_and_preserves_unsealed_result(tmp_path, monkeypatch):
    current = setup(tmp_path, monkeypatch)
    folder = ec.OUT / "phases/S0/attempt-001"
    folder.mkdir(parents=True)
    ec.c.write(folder / "result.json", {"not_sealed": True})
    current["phases"]["S0"] = {"status": "RUNNING", "directory": "out/phases/S0/attempt-001",
        "inputs": ec.fingerprint("S0", current), "started_at": (datetime.now(timezone.utc) - timedelta(seconds=20)).isoformat()}
    ec.recover(current)
    assert current["wall_seconds"] >= 20 and current["phases"]["S0"]["status"] == "INTERRUPTED"
    assert (folder / "unsealed-result.json").exists()
    ec.run_phase("S0", current)
    assert len(current["attempts"]) == 2


def test_crash_after_receipt_does_not_rewrite_accepted_receipt(tmp_path, monkeypatch):
    current = setup(tmp_path, monkeypatch)
    item = ec.run_phase("S0", current)
    current["attempts"] = []; current["wall_seconds"] = 0
    current["phases"]["S0"]["status"] = "RUNNING"
    expected = item["receipt_sha256"]
    ec.recover(current)
    assert current["phases"]["S0"]["receipt_sha256"] == expected
    ec.verify(current)


def test_failure_repair_and_finite_identical_retry_budget(tmp_path, monkeypatch):
    current = setup(tmp_path, monkeypatch)
    good = ec.execute
    def failed(*args): raise ValueError("defect")
    monkeypatch.setattr(ec, "execute", failed)
    for _ in range(3): assert ec.run_phase("S0", current)["status"] == "FAILED"
    with pytest.raises(ValueError, match="failure budget"): ec.run_phase("S0", current)
    monkeypatch.setattr(ec, "method", lambda: {"method": "causal repair v2"})
    monkeypatch.setattr(ec, "execute", good)
    assert ec.run_phase("S0", current)["status"] == "QUALIFIED"
    assert len(current["attempts"]) == 4


def test_source_recovery_does_not_reset_inherited_budget(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    monkeypatch.setattr(ec, "policy", lambda: {"public_hosts": ["example.org"],
        "max_http_requests_including_continuation": 12, "max_requests_per_url": 2})
    inherited = []
    for i in range(12):
        path = tmp_path / f"request-{i}.json"
        ec.c.write(path, {"url": "https://example.org/" + str(i), "status": "RESERVED"})
        inherited.append(path)
    monkeypatch.setattr(p, "all_requests", lambda: inherited)
    with pytest.raises(ValueError, match="Cumulative HTTP budget"):
        p.acquire({"key": "next", "url": "https://example.org/new"})
