"""Meaningful current installation admission, failure and comparator checks."""
from contextlib import contextmanager
from copy import deepcopy
import subprocess

import pytest

from legalmath.prospectus.execution_authority import read, write, digest, file_hash
from scripts import prospectus_installed_current as worker
from scripts import prospectus_installed_consumer as helper


@pytest.fixture
def installed(tmp_path):
    class LocalAuthority:
        root = tmp_path
        base = tmp_path / "authority"
        @contextmanager
        def lock(self): yield
        def spec(self): return program, {task["id"]: task}, None
        def events(self): return events
        def binding(self, task): return {"input": file_hash(tmp_path / "input")}
    authority = LocalAuthority()
    name = "authority/attempts/native-confinement/attempt-004"
    folder = tmp_path / name
    folder.mkdir(parents=True)
    (tmp_path / "input").write_text("protected")
    task = {"id": "native-confinement", "dossier": "plan", "preparation_only": True,
        "native_call_allowance": 0, "completion_validation_pending": {"validator": "old"},
        "installed_preparation": deepcopy(worker.GRANT)}
    program = {"revision": 130, "tasks": [task]}
    write(folder / "admission.json", {"task": task["id"], "task_spec": task, "attempt": name,
        "task_sha256": digest(task), "program_sha256": digest(program), "binding": authority.binding(task), "git_commit": "fixture"})
    events = [{"task": task["id"], "kind": "ADMIT", "attempt": name, "admission_sha256": file_hash(folder / "admission.json")}]
    return authority, name, folder


@pytest.mark.parametrize("change", ["none", "closed", "historical", "input", "program", "admission", "grant", "symlink", "absolute", "outside"])
def test_installed_admission_refuses_before_writes(installed, change):
    a, name, folder = installed
    if change == "none":
        assert worker.admission(a, name)[0] == folder
        return
    if change == "closed": a.events()[-1]["kind"] = "RECORD"
    elif change == "historical": name = name.replace("004", "002")
    elif change == "input": (a.root / "input").write_text("changed")
    elif change == "program": a.spec()[0]["revision"] += 1
    elif change == "admission": write(folder / "admission.json", {})
    elif change == "grant": a.spec()[1]["native-confinement"]["native_call_allowance"] = 1
    elif change == "symlink": (folder / "stages").symlink_to(a.root, target_is_directory=True)
    elif change == "absolute": name = str(folder)
    else: name = "../outside"
    before = sorted(str(p.relative_to(folder)) for p in folder.rglob("*"))
    with pytest.raises((ValueError, FileNotFoundError, KeyError)):
        worker.run_stage(a, name, "prepare")
    assert sorted(str(p.relative_to(folder)) for p in folder.rglob("*")) == before


@pytest.mark.parametrize("error", [ValueError("real failure"), TimeoutError("bounded"), KeyboardInterrupt("cancel")])
def test_installed_failure_is_sealed_and_never_retried(installed, monkeypatch, error):
    a, name, folder = installed
    def fail(*_): raise error
    monkeypatch.setattr(worker, "prepare", fail)
    code, result = worker.run_stage(a, name, "prepare")
    assert code and result["status"] == "FAIL" and result["error"]["message"] == str(error)
    manifest = read(folder / "outputs.json")
    assert "result.json" in manifest and all(file_hash(folder / n) == h for n, h in manifest.items())
    with pytest.raises(ValueError, match="Sealed"):
        worker.run_stage(a, name, "prepare")


def test_installed_predecessor_and_duplicate_refuse(installed):
    a, name, folder = installed
    with pytest.raises(ValueError, match="Prior installed stage"):
        worker.run_stage(a, name, "install")
    (folder / "stages/prepare").mkdir(parents=True)
    with pytest.raises(ValueError, match="already started"):
        worker.run_stage(a, name, "prepare")
    assert not (folder / "stages/install").exists()


def test_installed_native_stage_not_authorized(installed):
    a, name, folder = installed
    with pytest.raises(ValueError, match="Native or unknown"):
        worker.run_stage(a, name, "source-fresh")
    assert not (folder / "stages").exists()


def test_installed_full_comparator_does_not_normalize_or_drop_fields():
    expected = {n: {"data": "exact text", "status": "UNRESOLVED"} for n in ("P1", "P2", "P3", "P4", "P5", "answer")}
    helper.compare_objects(expected, deepcopy(expected))
    for name in expected:
        value = deepcopy(expected)
        value[name]["data"] = "exact  text"
        with pytest.raises(ValueError, match=name): helper.compare_objects(value, expected)
    missing = deepcopy(expected); missing.pop("P5")
    with pytest.raises(ValueError, match="denominator"): helper.compare_objects(missing, expected)


def test_installed_caught_subprocess_still_counted_and_restored():
    original = subprocess.Popen
    counter = {"attempts": 0}
    with helper.no_native(counter):
        with pytest.raises(RuntimeError, match="forbidden"): subprocess.Popen(["not-executed"])
    assert counter == {"attempts": 1} and subprocess.Popen is original


def test_installed_package_symlink_rejected(tmp_path):
    package = tmp_path / "package"; package.mkdir()
    target = tmp_path / "outside.py"; target.write_text("outside")
    (package / "module.py").symlink_to(target)
    with pytest.raises(ValueError, match="symlink"): helper.package_files(package)


def test_dependency_inventory_excludes_only_product_and_bytecode(tmp_path):
    names = ["bin/legalmath", "bin/pip", "lib/python3.11/site-packages/legalmath/x.py",
        "lib/python3.11/site-packages/legalmath-0.1.dist-info/METADATA",
        "lib/python3.11/site-packages/other/x.py", "lib/python3.11/site-packages/other/__pycache__/x.pyc"]
    for name in names:
        path = tmp_path / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(name)
    actual = worker.tree(tmp_path, dependencies=True)
    assert set(actual) == {names[1], names[4]}


def test_installed_method_snapshot_detects_rehashed_current_change(tmp_path, monkeypatch):
    folder = tmp_path / "attempt"; folder.mkdir()
    (tmp_path / "code").write_text("original")
    current = {"code": file_hash(tmp_path / "code")}
    write(folder / "methods.json", current)
    helper.save(folder / "method-snapshots.json.gz", {"code": b"different".hex()})
    monkeypatch.setattr(worker, "methods", lambda root: current)
    with pytest.raises(ValueError, match="snapshot differs"): worker.checked_methods(tmp_path, folder)


def test_failed_outer_spawn_consumes_one_reservation(tmp_path, monkeypatch):
    from legalmath.prospectus.successor import process_ledger
    folder = tmp_path / "attempt"; folder.mkdir()
    process_ledger.create(folder / "outer-ledger.json", 10, 18, "test")
    def failed(*args, **kwargs): raise FileNotFoundError("injected spawn failure")
    monkeypatch.setattr(subprocess, "Popen", failed)
    with pytest.raises(FileNotFoundError): worker.command(folder, tmp_path, "build", ["fixture"])
    ledger = process_ledger.checked(folder / "outer-ledger.json")
    assert len(ledger["reservations"]) == 1 and ledger["reservations"][0]["state"] == "SPAWN_FAILED"
    assert "injected" in read(folder / "commands/build/result.json")["error"]


def test_fabricated_preparation_pass_without_routes_refuses(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "checked_methods", lambda *args: {})
    with pytest.raises(FileNotFoundError): worker.validate(tmp_path, tmp_path)
