"""Successor restart, dependency, budget and integrity contracts."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from legalmath.prospectus import evidence_continuation as ec


def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(ec, "ROOT", tmp_path)
    monkeypatch.setattr(ec, "OUT", tmp_path / "out")
    monkeypatch.setattr(ec, "DATA", tmp_path / "data")
    monkeypatch.setattr(ec, "PLAN", tmp_path / "plan.md")
    monkeypatch.setattr(ec.c, "ROOT", tmp_path)
    monkeypatch.setattr(ec, "method", lambda: {"reader.py": "one"})
    monkeypatch.setattr(ec, "verify_parent", lambda: {"status": "PASS"})
    monkeypatch.setattr(ec.subprocess, "check_output", lambda *a, **k: "commit\n")
    ec.OUT.mkdir()
    ec.DATA.mkdir()
    ec.c.write(ec.OUT / "parent-snapshot.json", {"files": {}})
    ec.c.write(ec.DATA / "public-queue.json", {"requests": []})
    monkeypatch.setattr(ec, "execute", lambda phase, directory, current: {
        "status": "PASS", "repairs": ["Executed " + phase], "remaining": ["Unresolved source applicability"]})
    return ec.state()


def test_resume_is_noop_and_refresh_binds_actual_result(tmp_path, monkeypatch):
    current = setup(tmp_path, monkeypatch)
    for phase in ec.PHASES:
        ec.run_phase(phase, current)
    before = ec.c.digest(current)
    for phase in ec.PHASES:
        ec.run_phase(phase, current)
    assert ec.c.digest(current) == before
    assert ec.verify(current)["status"] == "PASS"
    for item in current["attempts"]:
        directory = tmp_path / item["directory"]
        plan = ec.c.read(directory / "next-phase-plan.json")
        assert plan["result_sha256"] == ec.c.sha(directory / "result.json")
        assert plan["repairs_executed"] == ["Executed " + item["phase"]]


def test_later_review_invalidates_only_consumers(tmp_path, monkeypatch):
    current = setup(tmp_path, monkeypatch)
    for phase in ec.PHASES:
        ec.run_phase(phase, current)
    ec.c.write(ec.DATA / "reader-review.json", {"changed": True})
    assert ec.current_phase("C0", current) and ec.current_phase("C1", current)
    assert not ec.current_phase("C2", current)
    assert ec.verify(current)["status"] == "INCOMPLETE"
    monkeypatch.setattr(ec, "method", lambda: {"reader.py": "two"})
    assert not ec.current_phase("C0", current)


@pytest.mark.parametrize("target", ["result.json", "receipt.json", "next-phase-plan.json"])
def test_tampering_is_rejected(tmp_path, monkeypatch, target):
    current = setup(tmp_path, monkeypatch)
    item = ec.run_phase("C0", current)
    (tmp_path / item["directory"] / target).write_text("{}")
    with pytest.raises(ValueError, match="changed"):
        ec.verify(current)


def test_failure_then_repair_preserves_failed_attempt(tmp_path, monkeypatch):
    current = setup(tmp_path, monkeypatch)
    good = ec.execute
    def fail(*args):
        raise ValueError("Causal implementation defect")
    monkeypatch.setattr(ec, "execute", fail)
    first = ec.run_phase("C0", current)
    assert first["status"] == "FAILED"
    monkeypatch.setattr(ec, "execute", good)
    second = ec.run_phase("C0", current)
    assert second["status"] == "PASS" and first["directory"] != second["directory"]
    assert ec.c.read(tmp_path / first["directory"] / "result.json")["research_direction_rejected"] is False


def test_interrupt_charges_budget_and_preserves_attempt(tmp_path, monkeypatch):
    current = setup(tmp_path, monkeypatch)
    folder = ec.OUT / "phases/C0/attempt-001"
    folder.mkdir(parents=True)
    current["phases"]["C0"] = {"status": "RUNNING", "directory": "out/phases/C0/attempt-001",
        "inputs": ec.fingerprint("C0", current), "started_at": (datetime.now(timezone.utc)-timedelta(seconds=30)).isoformat()}
    ec.recover_interruption(current)
    assert current["wall_seconds"] >= 30
    assert current["phases"]["C0"]["status"] == "INTERRUPTED"
    assert (folder / "receipt.json").exists()
    second = ec.run_phase("C0", current)
    assert second["directory"].endswith("attempt-002")
    ec.verify(current)


def test_crash_after_receipt_recovers_without_mutating_it(tmp_path, monkeypatch):
    current = setup(tmp_path, monkeypatch)
    item = ec.run_phase("C0", current)
    expected_hash = item["receipt_sha256"]
    current["phases"]["C0"] = {**item, "status": "RUNNING"}
    current["attempts"] = []
    current["wall_seconds"] = 0
    ec.recover_interruption(current)
    assert current["phases"]["C0"]["receipt_sha256"] == expected_hash
    assert current["phases"]["C0"]["status"] == "PASS"
    ec.verify(current)


def test_identical_failures_have_a_bound(tmp_path, monkeypatch):
    current = setup(tmp_path, monkeypatch)
    def fail(*args):
        raise ValueError("same failure")
    monkeypatch.setattr(ec, "execute", fail)
    for _ in range(ec.MAX_FAILURES):
        ec.run_phase("C0", current)
    with pytest.raises(ValueError, match="failure budget"):
        ec.run_phase("C0", current)


def test_http_reservation_survives_timeout(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    directory = ec.OUT / "phases/C3/attempt-001"
    directory.mkdir(parents=True)
    policy = {"public_hosts": ["example.org"], "max_http_requests": 1, "max_requests_per_url": 1,
              "max_http_seconds": 1, "max_response_bytes": 100}
    def timeout(*args, **kwargs):
        raise ec.subprocess.TimeoutExpired(args[0], 1)
    monkeypatch.setattr(ec.subprocess, "run", timeout)
    row = {"key": "source", "url": "https://example.org/source", "gap": "G12"}
    path = ec.acquire(row, directory, policy)
    assert ec.c.read(path)["status"] == "TIMEOUT"
    with pytest.raises(ValueError, match="HTTP budget"):
        ec.acquire(row, directory, policy)


def test_equal_inventory_length_cannot_hide_substituted_obligation():
    a = {"bank_investigation": {"inventory": [{"rule_id": str(i)} for i in range(14)]}}
    b = {"bank_investigation": {"inventory": [{"rule_id": str(i)} for i in range(1, 15)]}}
    assert ec.obligations(a) != ec.obligations(b)
    b["bank_investigation"]["inventory"][0] = {"rule_id": "2"}
    with pytest.raises(ValueError, match="duplicate"):
        ec.obligations(b)


def test_public_phase_can_continue_after_reader_failure_and_refresh_returns_to_repair(tmp_path, monkeypatch):
    current = setup(tmp_path, monkeypatch)
    ec.run_phase("C0", current)
    good = ec.execute
    monkeypatch.setattr(ec, "execute", lambda phase, directory, current: {
        "status": "FAILED", "remaining": ["Repair the reader"]} if phase == "C1" else good(phase, directory, current))
    assert ec.run_phase("C1", current)["status"] == "FAILED"
    assert ec.run_phase("C3", current)["status"] == "PASS"
    refreshed = ec.refresh(current)
    assert refreshed["next_phase"] == "C1"
    assert "Repair the reader" in refreshed["remaining"]
    with pytest.raises(ValueError, match="Stale predecessor"):
        ec.run_phase("C2", current)



def test_completed_refresh_keeps_only_consolidated_remaining_work(tmp_path, monkeypatch):
    current = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(ec, "execute", lambda phase, directory, current: {
        "status": "QUALIFIED",
        "remaining": ["Actual external evidence still needed"] if phase == "C4"
        else ["Temporary review requirement for " + phase],
    })
    for phase in ec.PHASES:
        ec.run_phase(phase, current)
    refreshed = ec.refresh(current)
    assert refreshed["next_phase"] is None
    assert refreshed["remaining"] == ["Actual external evidence still needed"]
    assert len(refreshed["required_results"]) == len(ec.PHASES)


def test_each_phase_plan_routes_from_actual_dependencies(tmp_path, monkeypatch):
    current = setup(tmp_path, monkeypatch)
    ec.run_phase("C0", current)
    good = ec.execute
    monkeypatch.setattr(ec, "execute", lambda phase, directory, current: {
        "status": "FAILED", "remaining": ["Repair reader"]
    } if phase == "C1" else good(phase, directory, current))
    ec.run_phase("C1", current)
    ec.run_phase("C3", current)
    local = ec.c.read(tmp_path / current["phases"]["C3"]["directory"] / "next-phase-plan.json")
    assert local["next_phase"] == "C1"
    assert ec.c.read(ec.OUT / "next-phase-plan.json")["next_phase"] == "C1"
    monkeypatch.setattr(ec, "execute", good)
    ec.run_phase("C1", current)
    ec.run_phase("C2", current)
    local = ec.c.read(tmp_path / current["phases"]["C2"]["directory"] / "next-phase-plan.json")
    assert local["next_phase"] == "C4"
    assert ec.c.read(ec.OUT / "next-phase-plan.json")["next_phase"] == "C4"
