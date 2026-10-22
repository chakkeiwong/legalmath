"""Current installed scope, package identity and actual control denominator."""
from copy import deepcopy
from pathlib import Path

import pytest
from legalmath.prospectus.execution_authority import write
from scripts import prospectus_installed_profile_refresh as check
from scripts import prospectus_installed_profile_worker as worker


def task():
    return {"id": "native-confinement", "validator": check.prior.INSTALLED,
            "product_delta_acceptance": deepcopy(check.SELECTOR), "native_call_allowance": 4,
            "retained_acceptance_only": False}


def test_installed_selector_refuses_changed_allowances():
    value = task()
    check.selector(value)
    for field, wrong in (("native_calls", 5), ("outer_commands", 19), ("historical_native", 0),
                         ("historical_outer", 0), ("execution_seconds", 0)):
        bad = deepcopy(value); bad["product_delta_acceptance"][field] = wrong
        with pytest.raises(ValueError, match="Unreviewed installed"):
            check.selector(bad)
    for field, wrong in (("id", "native-binding"), ("native_call_allowance", 0), ("retained_acceptance_only", True)):
        with pytest.raises(ValueError, match="Unreviewed installed"):
            check.selector({**value, field: wrong})
    assert len(check.COMMANDS) == 18 and len(check.STAGES) == 24 and len(set(check.STAGES)) == 24
    assert sum(stage.startswith("source-") for stage in check.COMMANDS) == 2


def test_control_denominator_and_specific_refusal():
    expected = {"wrong-pin": "Pinned profile", "changed-source": "Source bytes changed"}
    good = [{"case": k, "refused": True, "error": "ValueError: " + v} for k, v in expected.items()]
    check.checked_controls(good, expected)
    for bad in (good[:1], good + good[:1], [good[0], {**good[1], "error": "unrelated failure"}],
                [good[0], {**good[1], "refused": False}]):
        with pytest.raises(ValueError, match="denominator|expected reason"):
            check.checked_controls(bad, expected)


def test_current_package_change_is_detected(tmp_path, monkeypatch):
    installed = tmp_path / check.INSTALLED
    environment = tmp_path / "environment"
    write(installed / "workspace.json", {"directory": str(tmp_path)})
    expected = {"prospectus/successor/service.py": "reviewed"}
    write(installed / "source-package.json", expected)
    write(installed / "dependencies.json", {"dependency": "fixed"})
    monkeypatch.setattr(check.helper, "package_files", lambda p: expected)
    monkeypatch.setattr(check.prior.preparation, "tree", lambda *a, **k: {"dependency": "fixed"})
    assert check.package_check(tmp_path) == (environment, expected)
    monkeypatch.setattr(check.helper, "package_files", lambda p: {**expected, "unexpected.py": "changed"} if Path(p) == tmp_path / "src/legalmath" else expected)
    with pytest.raises(ValueError, match="package differs"):
        check.package_check(tmp_path)
    monkeypatch.setattr(check.helper, "package_files", lambda p: expected)
    monkeypatch.setattr(check.prior.preparation, "tree", lambda *a, **k: {"dependency": "changed"})
    with pytest.raises(ValueError, match="dependencies differ"):
        check.package_check(tmp_path)


def test_missing_current_lifecycle_is_not_acceptance(tmp_path):
    (tmp_path / "stages/capture").mkdir(parents=True)
    write(tmp_path / "result.json", {"status": "PASS", "scope": "CURRENT_INSTALLED_NATIVE_PROFILE", "whole_program_complete": False})
    with pytest.raises(ValueError, match="stages incomplete"):
        check.validate_submission(tmp_path, tmp_path, task())


def test_process_guard_blocks_direct_bypasses():
    import os
    import socket
    import subprocess
    with worker.execution_guard() as guard:
        for action in (lambda: os.system("forbidden-command"), os.fork,
                       lambda: socket.getaddrinfo("example.invalid", 443),
                       lambda: subprocess.Popen(["forbidden-command"])):
            with pytest.raises(RuntimeError, match="forbidden|Unreviewed subprocess"):
                action()
        assert guard.result() == {"starts": 0, "blocked": 4}
    assert guard.enabled is False


def test_process_guard_requires_exact_ordered_argv():
    commands = [["/explicit/python", "-I", "worker.py", "capture"]]
    guard = worker.ExecutionGuard(commands)
    guard.enabled = True
    for wrong in (["/bin/sh", "-c", "true"], [*commands[0], "extra"]):
        with pytest.raises(RuntimeError, match="Unreviewed subprocess"):
            guard.audit("subprocess.Popen", (wrong[0], wrong, None, None))
    guard.audit("subprocess.Popen", (commands[0][0], commands[0], None, None))
    with pytest.raises(RuntimeError, match="exhausted allowance"):
        guard.audit("subprocess.Popen", (commands[0][0], commands[0], None, None))
    assert guard.starts == 1


def test_native_guard_checks_whole_namespace_command():
    manifest = {"directories": ["/input"], "files": [{"mode": 0o555, "path": "/input/tool"}], "environment": {"CUDA_VISIBLE_DEVICES": "-1"}}
    inner = ["/input/tool", "--fixed"]
    actual = ["/usr/bin/bwrap", "--die-with-parent", "--new-session", "--unshare-all",
              "--unshare-user", "--cap-drop", "ALL", "--clearenv", "--chdir", "/",
              "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--dir", "/input",
              "--perms", "555", "--ro-bind-data", "7", "/input/tool",
              "--setenv", "CUDA_VISIBLE_DEVICES", "-1", "--remount-ro", "/", "--", *inner]
    variants = [actual[:], actual[:], actual[:], actual[:]]
    variants[0][3] = "--share-net"
    variants[1][21] = "2"
    variants[2][22] = "/other/tool"
    variants[3][-1] = "--different"
    guard = worker.ExecutionGuard([inner], manifest)
    guard.enabled = True
    for wrong in variants:
        with pytest.raises(RuntimeError, match="Unreviewed subprocess"):
            guard.audit("subprocess.Popen", (wrong[0], wrong, None, None))
    guard.audit("subprocess.Popen", (actual[0], actual, None, None))
    assert guard.starts == 1
