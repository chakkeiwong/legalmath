"""Behavioral checks for offline admission, preservation and truthful results."""
from contextlib import contextmanager
from copy import deepcopy
import gzip
import json
import signal
import subprocess
import sys

import pytest

from legalmath.prospectus import native_current_preparation as check
from legalmath.prospectus.execution_authority import digest, file_hash, read, write
from legalmath.prospectus.execution_workers import validate
from scripts import prospectus_native_campaign as worker


@pytest.fixture
def admitted(tmp_path):
    class LocalAuthority:
        root = tmp_path
        base = tmp_path / "authority"

        @contextmanager
        def lock(self):
            yield

        def spec(self):
            return program, {task["id"]: task}, None

        def events(self):
            return events

        def binding(self, task):
            return {"source.txt": file_hash(self.root / "source.txt")}

    authority = LocalAuthority()
    name = "authority/attempts/native-binding/attempt-014"
    folder = tmp_path / name
    folder.mkdir(parents=True)
    task = {"id": "native-binding", "handler": "agent", "stream": "engineering",
        "dossier": "plan.md", "inputs": ["source.txt"], "preparation_only": True,
        "native_call_allowance": 0, "completion_validation_pending": {"validator": "native-binding-files.v1"}}
    program = {"revision": 126, "tasks": [task]}
    (tmp_path / "source.txt").write_text("protected original bytes")
    for name0 in check.method_names(tmp_path):
        path = tmp_path / name0
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("method fixture: " + name0)
    write(folder / "admission.json", {"task": task["id"], "task_spec": task,
        "task_sha256": digest(task), "program_sha256": digest(program), "binding": authority.binding(task),
        "attempt": name, "git_commit": "fixture", "revision": 126}, exclusive=True)
    events = [{"task": task["id"], "kind": "ADMIT", "attempt": name,
               "admission_sha256": file_hash(folder / "admission.json")}]
    return authority, name, folder


def frozen(authority, folder):
    current = check.methods(authority.root)
    worker.save(folder, "methods.json", current)
    worker.save(folder, "method-snapshots.json.gz", {p: (authority.root / p).read_text() for p in current})
    worker.save(folder, "offline-ledger.json", {"version": check.VERSION, "native_call_allowance": 0,
        "historical_lower_bound": 50, "reservations": [],
        "scope": "Offline preparation; historical floor is not a successful-call total"})
    return current


def prepared(admitted, monkeypatch):
    authority, name, folder = admitted
    def prepare(*args):
        frozen(authority, folder)
        return {"fixture": True}
    monkeypatch.setattr(worker, "prepare", prepare)
    assert worker.run_stage(authority, name, "prepare")[0] == 0


def manifest(folder):
    rows = read(folder / "outputs.json")
    assert {"admission.json", "started.json", "result.json", "RESULT.md"} <= rows.keys()
    assert all(file_hash(folder / p) == h for p, h in rows.items())
    return read(folder / "result.json")


@pytest.mark.parametrize("change", ["none", "historical", "outside", "absolute", "task", "closed", "input", "program", "admission", "live-grant"])
def test_current_admission_and_historical_destinations(admitted, change):
    authority, name, folder = admitted
    if change == "none":
        assert check.current_admission(authority, name)[0] == folder
        return
    if change == "historical": authority.events()[-1]["attempt"] = name.replace("014", "008")
    elif change == "outside": name = "../outside"
    elif change == "absolute": name = str(folder)
    elif change == "task": authority.spec()[1]["native-binding"]["id"] = "other"
    elif change == "closed": authority.events()[-1]["kind"] = "RECORD"
    elif change == "input": (authority.root / "source.txt").write_text("changed")
    elif change == "program": authority.spec()[0]["revision"] += 1
    elif change == "admission": (folder / "admission.json").write_text("{}")
    else: authority.spec()[1]["native-binding"]["native_call_allowance"] = 1
    before = check.files(folder)
    with pytest.raises((ValueError, KeyError)):
        worker.run_stage(authority, name, "prepare")
    assert check.files(folder) == before


@pytest.mark.parametrize("where", ["attempt", "stages", "evidence"])
def test_symlinks_refuse_before_writes(admitted, tmp_path, where):
    authority, name, folder = admitted
    outside = tmp_path / "other"
    outside.mkdir()
    (outside / "protected").write_text("original")
    if where == "attempt":
        link = folder.parent / "attempt-015"
        link.symlink_to(folder, target_is_directory=True)
        name = str(link.relative_to(tmp_path))
    else:
        (folder / where).symlink_to(outside, target_is_directory=True)
    before = (outside / "protected").read_bytes()
    with pytest.raises(ValueError, match="Symlink"):
        worker.run_stage(authority, name, "prepare")
    assert (outside / "protected").read_bytes() == before
    assert sorted(p.name for p in outside.iterdir()) == ["protected"]


@pytest.mark.parametrize("sealed", [False, True])
def test_duplicate_and_sealed_preserve_bytes(admitted, monkeypatch, sealed):
    authority, name, folder = admitted
    prepared(admitted, monkeypatch)
    if sealed: write(folder / "outputs.json", {"sealed": True})
    before = check.files(folder)
    with pytest.raises(ValueError, match="Sealed|already started"):
        worker.run_stage(authority, name, "prepare")
    assert check.files(folder) == before


@pytest.mark.parametrize("error", [ValueError("injected validator error"), KeyboardInterrupt("cancel"), TimeoutError("timeout")])
def test_failure_finalizes_complete_manifest(admitted, monkeypatch, error):
    authority, name, folder = admitted
    def fail(*args):
        raise error
    monkeypatch.setattr(worker, "prepare", fail)
    code, summary = worker.run_stage(authority, name, "prepare")
    result = manifest(folder)
    assert code and summary["status"] == "FAIL" and result["error"]["message"] == str(error)
    assert type(error).__name__ in (folder / "stages/prepare/error.log").read_text()


def test_cooperative_cancel_finalizes(admitted, monkeypatch):
    authority, name, folder = admitted
    previous = signal.getsignal(signal.SIGTERM)
    monkeypatch.setattr(worker, "prepare", lambda *args: signal.raise_signal(signal.SIGTERM))
    code, _ = worker.run_stage(authority, name, "prepare")
    assert code == 124 and manifest(folder)["status"] == "FAIL"
    assert signal.getsignal(signal.SIGTERM) == previous


@pytest.mark.parametrize("caught", [False, True])
def test_subprocess_attempt_is_retained(admitted, monkeypatch, caught):
    authority, name, folder = admitted
    prepared(admitted, monkeypatch)
    original = subprocess.Popen
    def attempted(*args):
        try:
            subprocess.Popen(["forbidden-worker"])
        except RuntimeError:
            if not caught: raise
        return {"candidate": True}
    monkeypatch.setattr(worker, "replay", attempted)
    code, summary = worker.run_stage(authority, name, "replay-2009-fresh")
    assert code == 1 and summary["subprocess_attempts"] == 1 and manifest(folder)["status"] == "FAIL"
    assert subprocess.Popen is original


@pytest.mark.parametrize("change", ["method", "addition", "snapshot"])
def test_changed_methods_refuse_before_stage(admitted, monkeypatch, change):
    authority, name, folder = admitted
    prepared(admitted, monkeypatch)
    if change == "method": (authority.root / check.SCRIPT).write_text("changed")
    elif change == "addition":
        path = authority.root / "src/legalmath/prospectus/successor/new.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("new module")
    else:
        (folder / "method-snapshots.json.gz").write_bytes(gzip.compress(b"{}"))
    before = check.files(folder)
    with pytest.raises(ValueError, match="method|Method"):
        worker.run_stage(authority, name, "replay-2009-fresh")
    assert check.files(folder) == before


def test_changed_method_during_stage_retains_failure(admitted, monkeypatch):
    authority, name, folder = admitted
    prepared(admitted, monkeypatch)
    def changed(*args):
        (authority.root / check.SCRIPT).write_text("changed during replay")
        return {"would_pass": True}
    monkeypatch.setattr(worker, "replay", changed)
    assert worker.run_stage(authority, name, "replay-2009-fresh")[0] == 1
    assert manifest(folder)["status"] == "FAIL"


def test_missing_matrix_arm_refuses(admitted, monkeypatch):
    authority, _, folder = admitted
    frozen(authority, folder)
    worker.save(folder, "historical-evidence.json", {"fixture": True})
    monkeypatch.setattr(check, "check_tests", lambda *args: {"fixture": True})
    monkeypatch.setattr(check, "history", lambda *args: {"fixture": True})
    with pytest.raises(ValueError, match="Missing current matrix arm"):
        check.evidence(authority.root, folder)


def test_changed_receipt_refuses(tmp_path):
    runtime = check.historical.runtime
    streams = {"stdin": b"", "stdout": b"original native bytes", "stderr": b""}
    manifest0 = {"version": runtime.VERSION, "files": [{"path": "/source", "mode": 0o444,
        "size": 3, "sha256": "a" * 64}], "directories": [], "environment": dict(runtime.ENVIRONMENT),
        "native_reuse_allowed": False}
    from hashlib import sha256
    receipt = {"version": "sealed-native-execution.v2", "returncode": 0,
        "manifest_sha256": runtime.digest(manifest0), "argv": ["/worker"],
        **{k: {"sha256": sha256(v).hexdigest(), "bytes": len(v)} for k, v in streams.items()},
        "trusted_runtime": {"historical_fixture": True}, "limits": {"max_stream_bytes": 1024},
        "file_namespace": "sealed explicit files; private proc/dev/tmp; no host directory mounts", "native_reuse_allowed": False}
    receipt["receipt_sha256"] = runtime.digest(receipt)
    for k, v in streams.items(): (tmp_path / k).write_bytes(v)
    write(tmp_path / "receipt.json", receipt)
    assert check.historical_receipt(tmp_path, manifest0) == receipt
    (tmp_path / "stdout").write_bytes(b"altered native bytes")
    with pytest.raises(ValueError, match="stream mismatch"):
        check.historical_receipt(tmp_path, manifest0)


def test_unaccounted_reservation_refuses(admitted):
    authority, _, folder = admitted
    frozen(authority, folder)
    ledger = read(folder / "offline-ledger.json")
    ledger["reservations"].append({"unexpected": True})
    write(folder / "offline-ledger.json", ledger)
    with pytest.raises(ValueError, match="Unexpected reservation"):
        check.check_zero_ledger(folder)


def test_preparation_cannot_accept_task(admitted):
    authority, _, folder = admitted
    write(folder / "result.json", {"status": "PASS", "task": "native-binding", "whole_program_complete": False})
    assert validate(authority.root, folder, authority.spec()[1]["native-binding"]) is False


def test_live_stage_refuses_without_writes(admitted):
    authority, name, folder = admitted
    before = check.files(folder)
    with pytest.raises(ValueError, match="Live or unknown"):
        worker.run_stage(authority, name, "source-2009-fresh")
    assert check.files(folder) == before


def test_successful_finalization_stays_partial(admitted, monkeypatch):
    authority, name, folder = admitted
    prepared(admitted, monkeypatch)
    monkeypatch.setattr(check, "evidence", lambda *args: {"fixture": True, "current_native_execution_established": False})
    assert worker.run_stage(authority, name, "finalize")[0] == 0
    result = manifest(folder)
    assert result["status"] == "PASS" and result["task_acceptance_established"] is False
    assert validate(authority.root, folder, authority.spec()[1]["native-binding"]) is False


def test_test_runner_postcheck_failure_has_nonzero_record(admitted, monkeypatch):
    from scripts import prospectus_native_preparation_tests as runner
    authority, name, folder = admitted
    monkeypatch.setattr(runner, "ROOT", authority.root)
    monkeypatch.setattr(runner, "Authority", lambda *args: authority)
    monkeypatch.setattr(sys, "argv", ["test-runner", "--attempt", name])
    def passed_then_changed(args):
        (authority.root / check.SCRIPT).write_text("changed after passing suite")
        return 0
    monkeypatch.setattr(pytest, "main", passed_then_changed)
    assert runner.main() == 1
    result = read(folder / "validation/run-001/result.json")
    assert result["status"] == "FAIL" and result["exit_code"] == 1
    assert result["error"]["message"] == "Methods changed during tests"
