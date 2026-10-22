"""Current installed-target checks must not relabel predecessor executions."""
from copy import deepcopy
from pathlib import Path
import types

import pytest
from legalmath.prospectus.execution_authority import write
from scripts import prospectus_profile_installed as check


def task():
    return {"id": "native-confinement", "validator": check.prior.INSTALLED,
        "annual_profile_compatibility": deepcopy(check.SELECTOR),
        "product_delta_acceptance": deepcopy(check.previous.SELECTOR),
        "native_call_allowance": 4, "retained_acceptance_only": False}


def test_current_target_selector_keeps_exact_call_and_scope_limits():
    value = task(); check.selector(value)
    for key, wrong in (("native_call_allowance", 0), ("native_call_allowance", 5),
        ("id", "native-binding"), ("retained_acceptance_only", True),
        ("product_delta_acceptance", {}), ("annual_profile_compatibility", {}),
        ("retained_profile_validation", {})):
        with pytest.raises(ValueError, match="Unreviewed"):
            check.selector({**value, key: wrong})
    assert len(check.STAGES) == 24 and len(check.COMMANDS) == 18
    assert len(check.PROFILE_ERRORS) == 11 and len(check.LIFECYCLE_ERRORS) == 4


def test_current_target_execution_proof_refuses_other_package(tmp_path):
    env, package = tmp_path / "environment", tmp_path / "target/legalmath"
    methods = {"prospectus/native_profile.py": "hash"}
    good = {"module_path": str(package / "prospectus/native_profile.py"),
        "python": str(env / "bin/python"), "methods": methods}
    assert check.installed_proof(good, env, package, methods) == package
    for key, bad in (("module_path", str(env / "lib/python3.11/site-packages/legalmath/prospectus/native_profile.py")),
        ("python", "/other/python"), ("methods", {})):
        with pytest.raises(ValueError, match="execution identity"):
            check.installed_proof({**good, key: bad}, env, package, methods)


def test_current_target_required_files_preserve_all_other_sources(tmp_path):
    package = tmp_path / "target/legalmath"
    required = {"/source/original.pdf": "source", "/runtime/python": "runtime"}
    target = {}
    for n in ("ocr_worker.py", "native_inputs.py"):
        required[str(Path(check.product.extraction.__file__).with_name(n).resolve())] = n
        target[str(package / "prospectus/successor" / n)] = n
    manifest = {"files": [{"path": p, "sha256": h} for p, h in target.items()]}
    assert check.installed_requirements(required, manifest, package) == {
        "/source/original.pdf": "source", "/runtime/python": "runtime", **target}
    for bad in ({**required, **target}, {"/source/original.pdf": "source"}):
        with pytest.raises(ValueError, match="mapping"):
            check.installed_requirements(bad, manifest, package)
    with pytest.raises(ValueError, match="bytes"):
        check.installed_requirements(required, {"files": []}, package)


def test_installed_target_dispatch_retains_strict_fallback(monkeypatch):
    before = 'def validate_submission(root, attempt, task):\n    return "old-strict"\n'
    after = check.dispatch_candidate(before); mod = types.ModuleType("installed_dispatch_candidate")
    exec(compile(after, "installed_dispatch_candidate", "exec"), mod.__dict__)
    assert mod.validate_submission(None, None, {}) == "old-strict"
    def validate(root, attempt, value):
        check.selector(value)
        return "current"
    monkeypatch.setattr(check, "validate_submission", validate)
    assert mod.validate_submission(None, None, task()) == "current"
    for bad in ({"annual_profile_compatibility": None}, {**task(), "id": "native-binding"}):
        with pytest.raises(ValueError, match="Unreviewed"):
            mod.validate_submission(None, None, bad)


def test_current_target_package_checks_source_install_and_dependencies(tmp_path, monkeypatch):
    runtime = tmp_path / check.RUNTIME; installed = tmp_path / check.INSTALLED
    environment = tmp_path / "runtime/environment"
    write(runtime / "workspace.json", {"directory": str(environment.parent)})
    write(runtime / "dependencies.json", {"dependency": "fixed"})
    expected = {"prospectus/successor/service.py": "current"}
    write(installed / "final-package.json", expected)
    monkeypatch.setattr(check.helper, "package_files", lambda path: expected)
    monkeypatch.setattr(check.prior.preparation, "tree", lambda *a, **k: {"dependency": "fixed"})
    assert check.package_check(tmp_path) == (environment, expected)
    for target in (tmp_path / "src/legalmath", installed / "installed/legalmath"):
        monkeypatch.setattr(check.helper, "package_files", lambda path: {} if path == target else expected)
        with pytest.raises(ValueError, match="package differs"):
            check.package_check(tmp_path)
    monkeypatch.setattr(check.helper, "package_files", lambda path: expected)
    monkeypatch.setattr(check.prior.preparation, "tree", lambda *a, **k: {"dependency": "changed"})
    with pytest.raises(ValueError, match="dependencies differ"):
        check.package_check(tmp_path)


def test_current_target_missing_lifecycle_cannot_validate(tmp_path):
    (tmp_path / "stages/capture").mkdir(parents=True)
    write(tmp_path / "result.json", {"status": "PASS", "scope": "CURRENT_INSTALLED_NATIVE_PROFILE",
        "whole_program_complete": False})
    with pytest.raises(ValueError, match="stages incomplete"):
        check.validate_submission(tmp_path, tmp_path, task())
