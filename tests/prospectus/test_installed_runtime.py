"""Current installed evidence must retain exact sources, budgets and origins."""
from copy import deepcopy
from pathlib import Path
import hashlib
import types
import zipfile

import pytest
from legalmath.prospectus.execution_authority import write
from scripts import prospectus_installed_runtime as check
from scripts import prospectus_installed_runtime_worker as worker


def task():
    return {"id": "native-confinement", "handler": "agent", "validator": check.prior.INSTALLED,
        "current_installed_runtime": deepcopy(check.SELECTOR),
        "product_delta_acceptance": deepcopy(check.previous.SELECTOR),
        "native_call_allowance": 4, "retained_acceptance_only": False, "preparation_only": False}


def test_current_runtime_selector_rejects_wrong_history_or_scope():
    check.selector(task())
    for key, wrong in (("id", "native-binding"), ("handler", "external"), ("native_call_allowance", 5),
                       ("preparation_only", True), ("retained_acceptance_only", True),
                       ("annual_profile_compatibility", {}), ("retained_current_profile", {})):
        with pytest.raises(ValueError, match="Unreviewed"):
            check.selector({**task(), key: wrong})
    for key in ("historical_outer", "historical_native", "native_calls", "outer_commands", "baseline", "donor"):
        bad = task(); bad["current_installed_runtime"][key] = None
        with pytest.raises(ValueError, match="Unreviewed"):
            check.selector(bad)
    assert len(check.COMMANDS) == 18 and len(check.STAGES) == len(set(check.STAGES)) == 23
    assert [s for s in check.COMMANDS if s.startswith("source-")] == ["source-fresh", "source-retained"]


def test_current_runtime_dispatch_preserves_historical_branch(monkeypatch):
    before = 'def validate_submission(root, attempt, task):\n    return "historical"\n'
    module = types.ModuleType("current_runtime_dispatch")
    exec(compile(check.dispatch_candidate(before), "current_runtime_dispatch", "exec"), module.__dict__)
    def validate(root, attempt, value):
        check.selector(value)
        return "current"
    monkeypatch.setattr(check, "validate_submission", validate)
    assert module.validate_submission(None, None, {}) == "historical"
    assert module.validate_submission(None, None, task()) == "current"
    with pytest.raises(ValueError, match="Unreviewed"):
        module.validate_submission(None, None, {"current_installed_runtime": None})


def test_current_runtime_package_compares_source_install_wheel_and_dependencies(tmp_path, monkeypatch):
    installed = tmp_path / check.INSTALLED; runtime = tmp_path / check.RUNTIME
    env = tmp_path / "runtime/environment"
    write(runtime / "workspace.json", {"directory": str(env.parent)})
    write(runtime / "dependencies.json", {"runtime": "original"})
    content = {str(i) + ".py": ("source " + str(i)).encode() for i in range(452)}
    expected = {n: hashlib.sha256(v).hexdigest() for n, v in content.items()}
    write(installed / "source-package.json", expected)
    wheel = installed / "package.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, data in content.items(): archive.writestr("legalmath/" + name, data)
    write(installed / "wheel.json", {"file": wheel.name, "sha256": check.file_hash(wheel)})
    monkeypatch.setattr(check.helper, "package_files", lambda path: expected)
    monkeypatch.setattr(check.prior.preparation, "tree", lambda *a, **k: {"runtime": "original"})
    assert check.package_check(tmp_path) == (env, expected)
    for target in (tmp_path / "src/legalmath", installed / "installed/legalmath"):
        monkeypatch.setattr(check.helper, "package_files", lambda path: {} if path == target else expected)
        with pytest.raises(ValueError, match="package differs"):
            check.package_check(tmp_path)
    monkeypatch.setattr(check.helper, "package_files", lambda path: expected)
    with zipfile.ZipFile(wheel, "a") as archive: archive.writestr("legalmath/extra.py", b"extra")
    with pytest.raises(ValueError, match="wheel changed"):
        check.package_check(tmp_path)
    write(installed / "wheel.json", {"file": wheel.name, "sha256": check.file_hash(wheel)})
    with pytest.raises(ValueError, match="disagree"):
        check.package_check(tmp_path)


def test_current_runtime_proof_refuses_another_installation(tmp_path):
    env, package = tmp_path / "env", tmp_path / "installed/legalmath"
    methods = {"prospectus/native_profile.py": "original"}
    good = {"python": str(env / "bin/python"), "module_path": str(package / "prospectus/native_profile.py"), "methods": methods}
    assert check.installed_proof(good, env, package, methods) == package
    with pytest.raises(ValueError, match="identity differs"):
        check.installed_proof({**good, "module_path": str(tmp_path / "src/legalmath/prospectus/native_profile.py")}, env, package, methods)


def test_current_runtime_missing_lifecycle_cannot_validate(tmp_path, monkeypatch):
    monkeypatch.setattr(check, "ROOT", tmp_path)
    monkeypatch.setattr(check, "frozen", lambda task: {})
    (tmp_path / "stages/capture").mkdir(parents=True)
    write(tmp_path / "result.json", {"status": "PASS", "scope": "CURRENT_INSTALLED_NATIVE_PROFILE", "whole_program_complete": False})
    with pytest.raises(ValueError, match="stages incomplete"):
        check.validate_submission(tmp_path, tmp_path, task())


def test_current_runtime_preserves_every_control_and_its_reason():
    for expected in (check.PROFILE_ERRORS, check.LIFECYCLE_ERRORS):
        rows = [{"case": k, "refused": True, "error": "ValueError: " + v} for k, v in expected.items()]
        check.checked_controls(rows, expected)
        for bad in (rows[:-1], rows + rows[:1], [{**r, "error": "unrelated"} for r in rows]):
            with pytest.raises(ValueError, match="denominator|expected reason"):
                check.checked_controls(bad, expected)
    assert len(check.PROFILE_ERRORS) == 11 and len(check.LIFECYCLE_ERRORS) == 4


def test_current_worker_guard_matches_reviewed_original_and_rejects_bypass():
    from scripts import prospectus_profile_installed_worker as original
    import inspect
    assert inspect.getsource(worker.ExecutionGuard) == inspect.getsource(original.ExecutionGuard)
    guard = worker.ExecutionGuard([["/reviewed/python", "-I", "worker.py"]]); guard.enabled = True
    with pytest.raises(RuntimeError, match="Unreviewed"):
        guard.audit("subprocess.Popen", ("/other/python", ["/other/python", "-I", "worker.py"], None, None))
    with pytest.raises(RuntimeError, match="forbidden"):
        guard.audit("os.system", ("unreviewed",))
    assert guard.starts == 0 and guard.blocked == 2
