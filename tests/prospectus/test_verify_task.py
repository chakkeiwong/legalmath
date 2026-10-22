"""The real wrapper retains failures while refusing stale or duplicate work."""
import json
import signal
import subprocess

import pytest

from legalmath.prospectus.execution_authority import digest, file_hash
from scripts import prospectus_verify_task as worker


@pytest.fixture
def admitted(tmp_path):
    class LocalAuthority:
        root = tmp_path
        base = tmp_path / "authority"
        state = "ADMITTED"

        def path(self, name):
            return (self.root / name).resolve()

        def spec(self):
            return program, {task["id"]: task}, None

        def status(self):
            return {"tasks": [{"id": task["id"], "state": self.state, "attempt": name}]}

        def binding(self, task):
            return {"source.txt": file_hash(self.root / "source.txt")}

    task = {"id": "native-binding", "validator": "native-binding-files.v1",
            "inputs": ["source.txt"], "dossier": "plan.md"}
    program = {"revision": 1, "tasks": [task]}
    authority = LocalAuthority()
    name = "authority/attempts/native-binding/attempt-001"
    attempt = authority.path(name)
    attempt.mkdir(parents=True)
    (tmp_path / "source.txt").write_text("original source")
    for path in [*worker.CODE, worker.SCRIPT]:
        p = tmp_path / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("retained method: " + path)
    (attempt / "admission.json").write_text(json.dumps({"task": task["id"], "git_commit": "fixture",
        "binding": authority.binding(task), "program_sha256": digest(program), "task_sha256": digest(task)}))
    return authority, name, attempt


def check_manifest(attempt):
    manifest = json.loads((attempt / "outputs.json").read_text())
    assert {"started.json", "result.json", "RESULT.md", "admission.json"} <= manifest.keys()
    assert all(file_hash(attempt / p) == h for p, h in manifest.items())
    return json.loads((attempt / "result.json").read_text())


def test_success_remains_pending_actual_authority_acceptance(admitted, monkeypatch):
    authority, name, attempt = admitted
    monkeypatch.setattr(worker.checks, "native_binding_evidence", lambda *args: {"actual_evidence": [1, 2]})
    code, summary = worker.verify_task(authority, name)
    result = check_manifest(attempt)
    assert code == 0 and result["status"] == "PASS" and result["acceptance_pending"]
    assert not result["whole_program_complete"] and authority.state == "ADMITTED"
    assert json.loads((attempt / "verification.json").read_text()) == {"actual_evidence": [1, 2]}


@pytest.mark.parametrize("error,expected_code", [(ValueError("stale native methods"), 1),
    (TimeoutError("bounded validator timeout"), 124), (KeyboardInterrupt("cancelled"), 130)])
def test_validator_failure_is_truthful_and_recordable(admitted, monkeypatch, error, expected_code):
    authority, name, attempt = admitted
    def fail(*args):
        raise error
    monkeypatch.setattr(worker.checks, "native_binding_evidence", fail)
    code, summary = worker.verify_task(authority, name)
    result = check_manifest(attempt)
    assert code == expected_code and result["status"] == "FAIL"
    assert not result["acceptance_pending"] and result["error"]["message"] == str(error)
    assert result["error"]["phase"] == "validator" and not (attempt / "verification.json").exists()
    assert type(error).__name__ in (attempt / "error.log").read_text()
    assert summary["status"] == "FAILED_RETAINED_PENDING_AUTHORITY_RECORD"


def test_cooperative_sigterm_retains_failure_and_restores_handler(admitted, monkeypatch):
    authority, name, attempt = admitted
    previous = signal.getsignal(signal.SIGTERM)
    def interrupted(*args):
        signal.raise_signal(signal.SIGTERM)
    monkeypatch.setattr(worker.checks, "native_binding_evidence", interrupted)
    code, _ = worker.verify_task(authority, name)
    assert code == 124 and check_manifest(attempt)["error"]["type"] == "TimeoutError"
    assert signal.getsignal(signal.SIGTERM) == previous


def test_subprocess_is_refused_before_launch_and_guard_restored(admitted, monkeypatch):
    authority, name, attempt = admitted
    previous = subprocess.Popen
    def attempted(*args):
        subprocess.Popen(["forbidden-native-worker"])
    monkeypatch.setattr(worker.checks, "native_binding_evidence", attempted)
    code, _ = worker.verify_task(authority, name)
    result = check_manifest(attempt)
    assert code == 1 and result["error"]["type"] == "RuntimeError"
    assert "Subprocess prohibited" in result["error"]["message"]
    assert subprocess.Popen is previous


@pytest.mark.parametrize("change", ["source", "method", "program"])
def test_change_during_verification_vetoes_success(admitted, monkeypatch, change):
    authority, name, attempt = admitted
    def changed(*args):
        if change == "program":
            authority.spec()[0]["revision"] += 1
        else:
            path = "source.txt" if change == "source" else worker.SCRIPT
            (authority.root / path).write_text("changed during validator")
        return {"candidate": "would otherwise pass"}
    monkeypatch.setattr(worker.checks, "native_binding_evidence", changed)
    code, _ = worker.verify_task(authority, name)
    result = check_manifest(attempt)
    assert code == 1 and result["status"] == "FAIL" and result["error"]["phase"] == "final bindings"
    assert (attempt / "verification.json").exists()


def test_duplicate_preserves_every_retained_byte(admitted, monkeypatch):
    authority, name, attempt = admitted
    monkeypatch.setattr(worker.checks, "native_binding_evidence", lambda *args: {"ok": True})
    worker.verify_task(authority, name)
    before = {str(p.relative_to(attempt)): file_hash(p) for p in attempt.rglob("*") if p.is_file()}
    with pytest.raises(FileExistsError, match="already started"):
        worker.verify_task(authority, name)
    assert before == {str(p.relative_to(attempt)): file_hash(p) for p in attempt.rglob("*") if p.is_file()}


@pytest.mark.parametrize("change", ["completed", "binding", "program", "outside", "started"])
def test_preflight_refuses_without_new_evidence(admitted, change):
    authority, name, attempt = admitted
    if change == "completed": authority.state = "COMPLETE"
    elif change == "binding": (authority.root / "source.txt").write_text("new source")
    elif change == "program": authority.spec()[0]["revision"] += 1
    elif change == "outside": name = str(authority.root / "outside")
    else: (attempt / "started.json").write_text("original interrupted marker")
    before = {str(p.relative_to(attempt)): file_hash(p) for p in attempt.rglob("*") if p.is_file()}
    with pytest.raises((ValueError, FileExistsError)):
        worker.verify_task(authority, name)
    assert before == {str(p.relative_to(attempt)): file_hash(p) for p in attempt.rglob("*") if p.is_file()}
