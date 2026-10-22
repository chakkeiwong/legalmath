"""Current live controls without launching native processes."""
from contextlib import contextmanager
from copy import deepcopy
import subprocess

import pytest

from legalmath.prospectus import native_current_acceptance as check
from legalmath.prospectus.execution_authority import read, write, digest, file_hash
from legalmath.prospectus.successor import process_ledger
from scripts import prospectus_native_current as worker
from tests.prospectus.test_native_current_preparation import admitted, manifest


def grant_value():
    return {"version": check.VERSION, "routes": list(check.ROUTES), "maximum_reservations": 11,
        "historical_lower_bound": 50, "repair_reservations": 0, "storage_unique_bytes": check.STORAGE_CAP,
        "stage_timeout_seconds": 120, "canary": "2009-fresh", "source_calls_per_route": 2,
        "boundary_calls": 1, "network": False, "gpu": False, "installations": False}


@pytest.fixture
def live(admitted):
    authority, name, folder = admitted
    program, tasks, _ = authority.spec()
    task = tasks["native-binding"]
    task.update(preparation_only=False, native_call_allowance=11, validator=check.VERSION,
                native_campaign=grant_value())
    row = read(folder / "admission.json")
    row.update(task_spec=task, task_sha256=digest(task), program_sha256=digest(program))
    write(folder / "admission.json", row)
    authority.events()[-1]["admission_sha256"] = file_hash(folder / "admission.json")
    return authority, name, folder


@pytest.mark.parametrize("field", ["none", "native_campaign", "maximum_reservations", "historical_lower_bound", "repair_reservations",
                                  "routes", "storage_unique_bytes", "stage_timeout_seconds", "network", "validator"])
def test_live_grant_refuses_missing_or_altered_limits(live, field):
    authority, _, _ = live
    task = deepcopy(authority.spec()[1]["native-binding"])
    if field == "none":
        assert check.grant(task) == grant_value()
        return
    if field == "native_campaign": task.pop(field)
    elif field == "validator": task[field] = "native-binding-files.v1"
    elif field == "routes": task["native_campaign"][field].pop()
    elif field == "network": task["native_campaign"][field] = True
    else: task["native_campaign"][field] += 1
    with pytest.raises(ValueError, match="explicit current live grant"):
        check.grant(task)


@pytest.mark.parametrize("change", ["none", "closed", "historical", "source", "program", "admission", "grant", "symlink"])
def test_live_admission_refuses_before_writes(live, change):
    authority, name, folder = live
    if change == "none":
        assert check.admission(authority, name)[0] == folder
        return
    if change == "closed": authority.events()[-1]["kind"] = "RECORD"
    elif change == "historical": name = name.replace("014", "008")
    elif change == "source": (authority.root / "source.txt").write_text("changed")
    elif change == "program": authority.spec()[0]["revision"] += 1
    elif change == "admission": write(folder / "admission.json", {})
    elif change == "grant": authority.spec()[1]["native-binding"]["native_call_allowance"] = 12
    else: (folder / "stages").symlink_to(authority.root, target_is_directory=True)
    before = sorted(str(p.relative_to(folder)) for p in folder.rglob("*"))
    with pytest.raises((ValueError, KeyError, FileNotFoundError)):
        worker.run_stage(authority, name, "prepare")
    assert sorted(str(p.relative_to(folder)) for p in folder.rglob("*")) == before


@pytest.mark.parametrize("error", [ValueError("actual native failed"), TimeoutError("time bound"), KeyboardInterrupt("cancelled")])
def test_live_failure_is_sealed_and_recordable(live, monkeypatch, error):
    authority, name, folder = live
    def fail(*args): raise error
    monkeypatch.setattr(worker, "prepare", fail)
    code, result = worker.run_stage(authority, name, "prepare")
    assert code and result["error"]["message"] == str(error)
    actual = manifest(folder)
    assert actual["status"] == "FAIL" and actual["scope"] == "FINITE_ENGINEERING_ONLY"
    before = check.prep.files(folder)
    with pytest.raises(ValueError, match="Sealed"):
        worker.run_stage(authority, name, "prepare")
    assert check.prep.files(folder) == before


def prepare_fixture(live, monkeypatch):
    authority, name, folder = live
    monkeypatch.setattr(check, "check_methods", lambda *args: {"fixture": True})
    def fake_prepare(*args):
        process_ledger.create(folder / "process-ledger.json", 11, 50, "fixture")
        return {"fixture": True}
    monkeypatch.setattr(worker, "prepare", fake_prepare)
    assert worker.run_stage(authority, name, "prepare")[0] == 0


def test_live_stage_requires_canary_and_refuses_duplicate(live, monkeypatch):
    authority, name, folder = live
    prepare_fixture(live, monkeypatch)
    before = check.prep.files(folder)
    with pytest.raises(ValueError, match="canary"):
        worker.run_stage(authority, name, "route-2009-default")
    with pytest.raises(ValueError, match="already started"):
        worker.run_stage(authority, name, "prepare")
    assert check.prep.files(folder) == before


def test_live_ledger_rejects_unaccounted_reservation(live, monkeypatch):
    authority, _, folder = live
    prepare_fixture(live, monkeypatch)
    process_ledger.reserve(folder / "process-ledger.json", ["unaccounted-fixture"])
    with pytest.raises(ValueError, match="Unexpected or failed"):
        check.ledger(folder, 0)


def test_stage_call_limit_preserves_failed_launch_and_refuses_extra(live, monkeypatch):
    _, _, folder = live
    process_ledger.create(folder / "process-ledger.json", 11, 50, "fixture")
    attempted = []
    def fail(argv, **kwargs):
        attempted.append(argv)
        raise FileNotFoundError("injected spawn failure")
    monkeypatch.setattr(subprocess, "Popen", fail)
    with worker.native_calls(folder, 1):
        with pytest.raises(FileNotFoundError): subprocess.Popen(["fixture-executable"])
        with pytest.raises(ValueError, match="allowance exhausted"): subprocess.Popen(["second-executable"])
    rows = process_ledger.checked(folder / "process-ledger.json")["reservations"]
    assert len(rows) == 1 and rows[0]["state"] == "SPAWN_FAILED" and len(attempted) == 1


def test_current_validator_rejects_missing_matrix(live, monkeypatch):
    authority, _, folder = live
    monkeypatch.setattr(check, "check_methods", lambda *args: {"fixture": True})
    monkeypatch.setattr(check, "tests", lambda *args: {"fixture": True})
    with pytest.raises(ValueError, match="Missing current native stage"):
        check.evidence(authority.root, folder, authority.spec()[1]["native-binding"])


def test_live_default_captures_actual_failure(tmp_path, monkeypatch):
    calls = []
    def failed(argv, **kwargs):
        calls.append(kwargs)
        raise subprocess.CalledProcessError(7, argv, output=b"partial source", stderr=b"actual diagnostic")
    monkeypatch.setattr(subprocess, "run", failed)
    with worker.capture_default(tmp_path / "native"), pytest.raises(subprocess.CalledProcessError):
        subprocess.run(["fixture"], capture_output=True, timeout=90, check=True)
    assert calls[0]["timeout"] == 60
    assert read(tmp_path / "native/0/result.json")["returncode"] == 7
    assert (tmp_path / "native/0/stdout").read_bytes() == b"partial source"
    assert (tmp_path / "native/0/stderr").read_bytes() == b"actual diagnostic"


@pytest.mark.parametrize("field", ["text", "geometry", "receipt", "unknown", "qualification"])
def test_full_source_comparator_does_not_hide_changes(field):
    baseline = {"text": "original : punctuation", "geometry": None, "receipt": {"sha256": "old"},
                "unknown": ["missing source"], "qualification": "limited review only"}
    check.exact_source(deepcopy(baseline), baseline)
    changed = deepcopy(baseline)
    changed[field] = "different"
    with pytest.raises(ValueError, match="Complete raw source differs"):
        check.exact_source(changed, baseline)


def test_current_acceptance_refuses_forged_evidence(live, monkeypatch):
    authority, _, folder = live
    write(folder / "result.json", {"status": "PASS", "task": "native-binding", "scope": "FINITE_ENGINEERING_ONLY", "whole_program_complete": False})
    write(folder / "verification.json", {"forged": True})
    monkeypatch.setattr(check, "check_methods", lambda *args: {"fixture": True})
    monkeypatch.setattr(check, "tests", lambda *args: {"fixture": True})
    with pytest.raises(ValueError, match="Missing current native stage"):
        check.validate_submission(authority.root, folder, authority.spec()[1]["native-binding"])


def test_rehashed_answer_requires_actual_current_consumer(tmp_path, monkeypatch):
    values, answer = {"P1": {"sha256": "same"}}, {"report_sha256": "rehash", "wrong": True}
    monkeypatch.setattr(check.prep.historical, "products", lambda *args: (values, answer))
    monkeypatch.setattr(check, "check_source", lambda *args: values["P1"])
    monkeypatch.setattr(check.service, "consume", lambda *args, **kwargs: {"actual": "different"})
    with pytest.raises(ValueError, match="not consumed"):
        check.check_route(tmp_path, tmp_path, "2009-fresh", consume=True)
