"""Boundary tests for the command policy and local operations runner."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("legal_interpretation_ops", ROOT / "scripts/legal_interpretation_ops.py")
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)


@pytest.mark.parametrize("value", ["../outside", "/etc/passwd", ".git/config", ".codex/rules/x",
                                  ".agents/x", ".env", "docs/.env.local", "auth.json"])
def test_inspection_rejects_protected_paths(tmp_path, value):
    with pytest.raises(ValueError):
        ops.safe_path(value, tmp_path)


def test_inspection_rejects_symlink_escape(tmp_path):
    (tmp_path / "escape").symlink_to("/etc", target_is_directory=True)
    with pytest.raises(ValueError):
        ops.safe_path("escape/passwd", tmp_path)


@pytest.mark.parametrize("argv", [
    ["status", "extra"], ["install-rules", "/tmp/arbitrary.rules"],
    ["phase-tests", "P9"], ["regression", "all"], ["run"],
    ["read", "--exec", "x"], ["policy-check", "--install"],
    ["build-docs", "--shell", "anything"],
])
def test_cli_rejects_undeclared_operations(argv):
    with pytest.raises(SystemExit) as raised:
        ops.parser().parse_args(argv)
    assert raised.value.code == 2


def test_missing_phase_is_not_a_successful_test_run(tmp_path):
    with pytest.raises(ValueError, match="NOT_IMPLEMENTED"):
        ops.test_command("P0", phase=True, root=tmp_path)


def test_phase_test_mapping_is_not_controlled_by_manifest(tmp_path):
    test = tmp_path / "tests/interpretation/semantics/test_operative.py"
    test.parent.mkdir(parents=True)
    test.write_text("def test_example(): pass\n")
    manifest = tmp_path / ops.BASE / "phase-manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"phases": [{"id": "P0", "future_tests": ["arbitrary.py"]}]}))
    with pytest.raises(ValueError, match="specification changed"):
        ops.test_command("P0", phase=True, root=tmp_path)
    manifest.write_text(json.dumps({"phases": [{"id": "P0", "future_tests":
                                              ["tests/interpretation/semantics/test_operative.py"]}]}))
    argv = ops.test_command("P0", phase=True, root=tmp_path)
    assert argv == [str(tmp_path / ".venv/bin/python"), "-m", "pytest",
                    "tests/interpretation/semantics/test_operative.py", "-q"]


def test_handoff_change_is_reported_without_refresh(tmp_path):
    p = tmp_path / "source.txt"
    p.write_text("original")
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    listing = tmp_path / ops.BASE / "handoff.sha256"
    listing.parent.mkdir(parents=True)
    listing.write_text(digest + "  source.txt\n")
    assert ops.handoff(tmp_path)["status"] == "PASS"
    p.write_text("changed")
    result = ops.handoff(tmp_path)
    assert result["status"] == "CHANGED" and result["mismatches"] == ["source.txt"]
    assert listing.read_text() == digest + "  source.txt\n"


def test_rule_installer_preserves_conflicts_and_rejects_symlink(tmp_path):
    target = tmp_path / "rule.rules"
    assert ops.install_file(target, "expected\n") is True
    assert ops.install_file(target, "expected\n") is False
    with pytest.raises(ValueError, match="different"):
        ops.install_file(target, "replacement\n")
    assert target.read_text() == "expected\n"
    link = tmp_path / "linked.rules"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlinks"):
        ops.install_file(link, "expected\n")


def test_offline_environment_hides_gpu_and_provider_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-never-transmit")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "test-only-never-transmit")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    env = ops.cpu_environment()
    assert env["CUDA_VISIBLE_DEVICES"] == "-1"
    assert "OPENAI_API_KEY" not in env and "ANTHROPIC_AUTH_TOKEN" not in env


def test_subprocess_failure_retains_log_and_never_completes_phase(tmp_path):
    result = ops.run_job("boundary", [sys.executable, "-c",
                                     "print('observed failure'); raise SystemExit(3)"], 5, tmp_path)
    assert result["status"] == "FAIL" and result["exit_code"] == 3
    assert result["phase_completion"] is False
    path = tmp_path / result["attempt"]
    assert "observed failure" in (path / "output.log").read_text()
    assert json.loads((path / "result.json").read_text())["status"] == "FAIL"


def test_timeout_is_retained_as_timeout_not_success(tmp_path):
    result = ops.run_job("timeout", [sys.executable, "-c", "import time; time.sleep(10)"], 0.05, tmp_path)
    assert result["status"] == "TIMEOUT" and result["exit_code"] == 124
    assert result["phase_completion"] is False


def test_successful_tool_job_is_not_product_completion(tmp_path):
    result = ops.run_job("local check", [sys.executable, "-c", "print('checked')"], 5, tmp_path)
    assert result["status"] == "PASS" and result["phase_completion"] is False


def test_policy_has_only_declared_actions_and_editor():
    text = ops.rule_text()
    assert '"install-rules"' not in text
    assert '"run"' not in text
    assert '"scripts/assurance_evidence_master.py"' not in text
    for a in ops.PUBLIC_ACTIONS:
        assert json.dumps(ops.PREFIX + [a]) in text


def test_failed_launch_is_explicit_and_durable(tmp_path):
    result = ops.run_job("unavailable runtime", [str(tmp_path / "missing-runtime")], 1, tmp_path)
    assert result["status"] == "LAUNCH_FAILED" and result["exit_code"] == 127
    assert result["phase_completion"] is False
    assert json.loads((tmp_path / result["attempt"] / "result.json").read_text())["status"] == "LAUNCH_FAILED"


def test_stdin_edit_preserves_literal_shell_characters(tmp_path):
    value = "Literal $() and backticks " + chr(96) + " must stay text.\n" + "x" * 12000
    path = tmp_path / "edited.txt"
    request = {"edits": [{"path": str(path), "content": value, "before_sha256": None}]}
    p = subprocess.run([sys.executable, str(ROOT / "scripts/legal_interpretation_ops.py"), "edit"],
                       input=json.dumps(request) + "\n", text=True, capture_output=True, cwd=ROOT, timeout=5)
    assert p.returncode == 0, p.stdout + p.stderr
    assert path.read_text() == value


def test_stdin_edit_cannot_change_agent_rules(tmp_path):
    p = subprocess.run([sys.executable, str(ROOT / "scripts/legal_interpretation_ops.py"), "edit"],
                       input=json.dumps({"edits": [{"path": str(tmp_path / ".codex/rules/x"),
                                                   "content": "x", "before_sha256": None}]}) + "\n",
                       text=True, capture_output=True, cwd=ROOT, timeout=5)
    assert p.returncode != 0
    assert not (tmp_path / ".codex/rules/x").exists()


def test_native_policy_matches_all_declared_examples():
    result = ops.policy_check()
    assert result["status"] == "PASS"
    assert result["positive_commands"] == len(ops.command_examples())
    assert result["negative_commands"] == 7
