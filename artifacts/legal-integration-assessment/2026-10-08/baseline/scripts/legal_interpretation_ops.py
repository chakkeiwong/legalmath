#!/usr/bin/env python3
"""Fixed local operations for the legal interpretation program; no shell pass-through."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
PREFIX = [".venv/bin/python", "scripts/legal_interpretation_ops.py"]
EDITOR = [".venv/bin/python", "scripts/edit_workspace_files.py"]
BASE = Path("docs/implementation/legal-interpretation-program")
OPS = BASE / "execution"
RUNS = Path("artifacts/legal-interpretation-program/operations")
INSTALL = Path("/home/chakwong/.codex/rules/legalmath-legal-interpretation-program.rules")
DOC_PY = "/home/chakwong/miniconda3/envs/tfgpu/bin/python"
PROTECTED = {".git", ".codex", ".agents", ".ssh", ".aws", ".gnupg", ".venv"}
ACTIONS = ("status", "verify-handoff", "policy-check", "install-rules", "self-test",
           "phase-tests", "regression", "build-docs", "files", "read", "search", "json", "edit")
PHASE_TESTS = {
    "P0": ("test_operative.py",),
    "P1": ("test_records.py", "test_legacy_adapter.py"),
    "P2": ("test_clauses.py", "test_pilot_readings.py"),
    "P3": ("test_arguments.py", "test_pyarg_adapter.py"),
    "P4": ("test_precedent.py", "test_case_citations.py"),
    "P5": ("test_evidence.py", "test_applicability.py"),
    "P6": ("test_lowering.py", "test_rendering.py", "test_integration.py"),
    "P7": ("test_invariants.py", "test_faults.py"),
    "P8": ("test_coverage.py", "test_observation_boundary.py"),
}
REGRESSIONS = {
    "contracts": ("tests/interpretation/test_contracts.py",),
    "sources": ("tests/assurance/test_closure_references.py",
                "tests/assurance/test_source_derivative.py"),
    "integration": ("tests/assurance/test_investigation_observations.py",
                    "tests/assurance/test_continuation_qualification.py",
                    "tests/assurance/test_integrated_workflow.py"),
    "translation": ("tests/translation/test_frontend.py",
                    "tests/translation/test_qualification_execution.py"),
}
TOOL_TEST = "tests/tooling/test_legal_interpretation_ops.py"
PUBLIC_ACTIONS = tuple(a for a in ACTIONS if a != "install-rules")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def safe_path(value, root=ROOT):
    root = Path(root).resolve()
    p = Path(value)
    lexical = p if p.is_absolute() else root / p
    forbidden = lambda parts: any(
        part in PROTECTED or part == ".env" or part.startswith(".env.")
        or part in {"auth.json", "credentials.json"} for part in parts)
    if forbidden(lexical.parts):
        raise ValueError("Protected metadata or credential path")
    resolved = lexical.resolve()
    if not resolved.is_relative_to(root) or forbidden(resolved.relative_to(root).parts):
        raise ValueError("Path escapes the worktree or protected metadata")
    return resolved


def save_json(path, value):
    path = safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def rule_text():
    lines = [
        "# User-requested LegalMath legal-interpretation local execution setup.",
        "# The fixed runner rejects undeclared actions and extra arguments.",
    ]
    for action in PUBLIC_ACTIONS:
        lines.append("prefix_rule(pattern=" + json.dumps(PREFIX + [action])
                     + ', decision="allow")')
    lines.append("prefix_rule(pattern=" + json.dumps(EDITOR) + ', decision="allow")')
    return "\n".join(lines) + "\n"


def command_examples():
    commands = [PREFIX + [a] for a in ("status", "verify-handoff", "policy-check",
                                      "self-test", "build-docs", "edit")]
    commands += [PREFIX + ["phase-tests", p] for p in PHASE_TESTS]
    commands += [PREFIX + ["regression", p] for p in REGRESSIONS]
    commands += [
        PREFIX + ["files", "src/legalmath/interpretation"],
        PREFIX + ["read", "docs/plans/legal-interpretation-master-program.md", "1", "80"],
        PREFIX + ["search", "request", "docs/plans/legal-interpretation-program"],
        PREFIX + ["json", str(BASE / "phase-manifest.json"), "status"],
        EDITOR + ["--self-test"],
    ]
    return commands


def policy_check(installed=False):
    rule = INSTALL if installed else ROOT / OPS / "allow.rules"
    if not rule.is_file() or rule.is_symlink() or rule.read_text() != rule_text():
        raise ValueError("Rule file is missing or differs from the reviewed command policy")
    declared = read_json(ROOT / OPS / "allowlist.json")
    if declared["commands"] != command_examples():
        raise ValueError("Allowlist differs from the runner's fixed command forms")
    codex = shutil.which("codex")
    if not codex:
        raise ValueError("Codex execpolicy checker is unavailable")
    positives = []
    negatives = [
        ["python3", "scripts/legal_interpretation_ops.py", "status"],
        [".venv/bin/python", "-c", "print(1)"],
        [".venv/bin/python", "scripts/assurance_evidence_master.py", "ops-run"],
        PREFIX + ["run"],
        PREFIX + ["install-rules"],
        ["bash", "-c", " ".join(PREFIX + ["status"])],
        [str(ROOT / ".venv/bin/python"), str(ROOT / PREFIX[1]), "status"],
    ]
    checks = []
    for command, intended in [(x, True) for x in command_examples()] + [(x, False) for x in negatives]:
        p = subprocess.run([codex, "execpolicy", "check", "--rules", str(rule), *command],
                           capture_output=True, text=True, timeout=30, check=True)
        answer = json.loads(p.stdout)
        allowed = answer.get("decision") == "allow"
        if allowed != intended:
            raise ValueError("Dedicated policy decision mismatch for " + repr(command))
        checks.append({"argv": command, "decision": answer.get("decision"),
                       "expected_dedicated_match": intended})
        if intended:
            positives.append(command)
    result = {
        "status": "PASS", "installed_rule_checked": installed, "rule_path": str(rule),
        "rule_sha256": sha(rule), "runner_sha256": sha(Path(__file__)),
        "positive_commands": len(positives), "negative_commands": len(negatives),
        "checks": checks,
        "limits": "Checks this dedicated rule. Inherited broad rules and managed-session policy are separate.",
    }
    save_json(ROOT / OPS / ("installed-policy-check.json" if installed else "policy-check.json"), result)
    return result


def install_file(target, content):
    target = Path(target)
    if any(p.is_symlink() for p in (target, *target.parents)):
        raise ValueError("Rule installation does not follow symlinks")
    if not target.parent.is_dir():
        raise ValueError("Expected existing Codex rules directory")
    if target.exists():
        if target.read_text() != content:
            raise ValueError("Dedicated rule already has different content; preserved unchanged")
        return False
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        # A partial file remains visible and fails identity validation; never overwrite it silently.
        raise
    if target.read_text() != content:
        raise ValueError("Installed rule bytes differ")
    return True


def install_rules():
    preflight = policy_check()
    result = read_json(ROOT / OPS / "self-test-result.json")
    if (result.get("status") != "PASS" or result.get("runner_sha256") != sha(Path(__file__))
            or result.get("tool_test_sha256") != sha(ROOT / TOOL_TEST)):
        raise ValueError("Run self-test on this exact runner and test suite before installing")
    created = install_file(INSTALL, rule_text())
    checked = policy_check(installed=True)
    receipt = {
        "status": "INSTALLED_AND_MATCH_CHECKED", "created": created,
        "installed_path": str(INSTALL), "sha256": sha(INSTALL),
        "runner_sha256": preflight["runner_sha256"],
        "positive_commands": checked["positive_commands"],
        "negative_commands": checked["negative_commands"],
        "approval_scope": "Fixed local program operations plus guarded local editing; no new model grant",
        "session_reload": "Not inferred from file installation; exercise exact commands in the live session.",
    }
    save_json(ROOT / OPS / "installation.json", receipt)
    return receipt


def handoff(root=ROOT):
    root = Path(root)
    path = root / BASE / "handoff.sha256"
    mismatches = []
    rows = path.read_text().splitlines()
    for line in rows:
        digest, rel = line.split("  ", 1)
        p = safe_path(rel, root)
        if not p.is_file() or sha(p) != digest:
            mismatches.append(rel)
    return {"status": "PASS" if not mismatches else "CHANGED",
            "entries": len(rows), "mismatches": mismatches,
            "scope": "Frozen review package only; no semantic correctness or phase completion"}


def cpu_environment():
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES="-1", PYTHONDONTWRITEBYTECODE="1", PYTEST_ADDOPTS="")
    for name in list(env):
        if name in {"ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
                    "OPENAI_ADMIN_KEY", "AZURE_OPENAI_API_KEY", "PYTHONSTARTUP", "PYTHONINSPECT"}:
            env.pop(name, None)
    return env


def test_command(group, phase=False, root=ROOT):
    paths = (["tests/interpretation/semantics/" + p for p in PHASE_TESTS[group]]
             if phase else list(REGRESSIONS[group]))
    missing = [p for p in paths if not safe_path(p, root).is_file()]
    if missing:
        raise ValueError("NOT_IMPLEMENTED: required tests do not exist: " + ", ".join(missing))
    if phase:
        manifest = read_json(Path(root) / BASE / "phase-manifest.json")
        declared = next(p for p in manifest["phases"] if p["id"] == group)["future_tests"]
        if paths != declared:
            raise ValueError("Phase test specification changed; review the fixed command mapping")
    return [str(Path(root) / ".venv/bin/python"), "-m", "pytest", *paths, "-q"]


def terminate_group(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)


def run_job(label, command, timeout, root=ROOT):
    root = Path(root)
    attempt = safe_path(RUNS / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                               + "-" + uuid.uuid4().hex[:10]), root)
    attempt.mkdir(parents=True)
    record = {
        "status": "RUNNING", "label": label, "argv": command, "cwd": str(root),
        "pid": None, "timeout_seconds": timeout, "started_at": datetime.now(timezone.utc).isoformat(),
        "cpu_mode": "CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden",
        "provider_dispatch_requested": False, "phase_completion": False,
        "runner_sha256": sha(Path(__file__)),
    }
    # Tests may use an isolated root; all record paths still stay within that root.
    def persist():
        temporary = attempt / "result.json.tmp"
        with temporary.open("w") as stream:
            json.dump(record, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, attempt / "result.json")
    persist()
    start = time.monotonic()
    with (attempt / "output.log").open("w") as log:
        try:
            process = subprocess.Popen(command, cwd=root, env=cpu_environment(),
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as error:
            record.update(status="LAUNCH_FAILED", exit_code=127, reason=str(error),
                          elapsed_seconds=round(time.monotonic() - start, 3),
                          attempt=str(attempt.relative_to(root)))
            persist()
            return record
        record["pid"] = process.pid
        persist()
        try:
            code = process.wait(timeout=timeout)
            record.update(status="PASS" if code == 0 else "FAIL", exit_code=code)
        except subprocess.TimeoutExpired:
            terminate_group(process)
            record.update(status="TIMEOUT", exit_code=124)
        except BaseException:
            terminate_group(process)
            record.update(status="INTERRUPTED", exit_code=130)
            record["elapsed_seconds"] = round(time.monotonic() - start, 3)
            persist()
            raise
    record["elapsed_seconds"] = round(time.monotonic() - start, 3)
    record["log_sha256"] = sha(attempt / "output.log")
    record["attempt"] = str(attempt.relative_to(root))
    persist()
    return record


def status():
    phase = read_json(ROOT / BASE / "phase-manifest.json")
    attempts = []
    path = safe_path(RUNS)
    if path.exists():
        for p in sorted(path.glob("*/result.json"))[-12:]:
            r = read_json(safe_path(p))
            if r["status"] == "RUNNING":
                try:
                    os.kill(r["pid"], 0) if r["pid"] else (_ for _ in ()).throw(ProcessLookupError())
                    r["process_observation"] = "PID_PRESENT_NOT_COMPLETION_EVIDENCE"
                except (ProcessLookupError, PermissionError):
                    r["process_observation"] = "NO_ACCESSIBLE_PROCESS_RESULT_UNCONFIRMED"
            attempts.append(r)
    return {
        "phase_statuses": {p["id"]: p["status"] for p in phase["phases"]},
        "runtime": "Local operations only; no automatic P0-P8 implementation",
        "installed_rule_matches": INSTALL.is_file() and not INSTALL.is_symlink() and INSTALL.read_text() == rule_text(),
        "available_phase_tests": {p: all((ROOT / "tests/interpretation/semantics" / f).is_file()
                                        for f in fs) for p, fs in PHASE_TESTS.items()},
        "attempts": attempts,
    }


def parser():
    p = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = p.add_subparsers(dest="action", required=True)
    for name in ("status", "verify-handoff", "install-rules", "self-test", "build-docs", "edit"):
        sub.add_parser(name, allow_abbrev=False)
    sub.add_parser("policy-check", allow_abbrev=False).add_argument("--installed", action="store_true")
    sub.add_parser("phase-tests", allow_abbrev=False).add_argument("phase", choices=PHASE_TESTS)
    sub.add_parser("regression", allow_abbrev=False).add_argument("group", choices=REGRESSIONS)
    sub.add_parser("files", allow_abbrev=False).add_argument("path")
    rd = sub.add_parser("read", allow_abbrev=False)
    rd.add_argument("path"); rd.add_argument("start", type=int); rd.add_argument("end", type=int)
    sr = sub.add_parser("search", allow_abbrev=False)
    sr.add_argument("literal"); sr.add_argument("path")
    js = sub.add_parser("json", allow_abbrev=False)
    js.add_argument("path"); js.add_argument("key", nargs="?", default="")
    return p


def inspect(args):
    path = safe_path(args.path)
    if args.action == "read":
        if not 1 <= args.start <= args.end or args.end - args.start >= 400:
            raise ValueError("Read one to 400 lines per command")
        if path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("Text exceeds eight-MiB inspection limit")
        lines = path.read_text().splitlines()
        text = "\n".join(f"{i+1}: {lines[i]}" for i in range(args.start-1, min(args.end, len(lines))))
        print(text[:50000])
    elif args.action == "json":
        if path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("JSON exceeds eight-MiB inspection limit")
        value = read_json(path)
        for key in args.key.split(".") if args.key else []:
            value = value[int(key)] if isinstance(value, list) else value[key]
        print(json.dumps(value, indent=2, ensure_ascii=False)[:50000])
    else:
        rg = shutil.which("rg")
        if not rg:
            raise ValueError("ripgrep is required for bounded file discovery")
        command = [rg, "--files", "--hidden"] if args.action == "files" else [rg, "-n", "-F", "--max-count", "20"]
        for pattern in (".git/**", ".codex/**", ".agents/**", ".venv/**", ".env", ".env.*", "**/auth.json", "**/credentials.json"):
            command += ["-g", "!" + pattern]
        if args.action == "files":
            command += ["--", str(path)]
        else:
            if not 1 <= len(args.literal) <= 300:
                raise ValueError("Search literal must contain one to 300 characters")
            command += ["--", args.literal, str(path)]
        r = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=20)
        if r.returncode not in (0, 1):
            raise ValueError(r.stderr[:1000])
        print("\n".join(r.stdout.splitlines()[:250])[:50000])


def guarded_edit():
    """Receive one JSON line through stdin; it is data, never shell text."""
    settings = None
    if sys.stdin.isatty():
        import termios
        settings = termios.tcgetattr(sys.stdin.fileno())
        raw = termios.tcgetattr(sys.stdin.fileno())
        raw[3] &= ~(termios.ECHO | termios.ICANON)
        raw[6][termios.VMIN], raw[6][termios.VTIME] = 1, 0
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, raw)
    try:
        print("READY_FOR_GUARDED_EDIT_JSON", flush=True)
        payload = sys.stdin.readline(64 * 1024 * 1024 + 1)
        if not payload.endswith("\n") or len(payload.encode()) > 64 * 1024 * 1024:
            raise ValueError("Supply one complete JSON line within 64 MiB")
        spec = importlib.util.spec_from_file_location("workspace_edit", ROOT / EDITOR[1])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return {"status": "PASS", "edits": module.apply(json.loads(payload))}
    finally:
        if settings is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, settings)


def main(argv=None):
    args = parser().parse_args(argv)
    if Path.cwd().resolve() != ROOT:
        raise ValueError("Use the exact command from " + str(ROOT))
    if args.action in ("files", "read", "search", "json"):
        inspect(args)
        return 0
    if args.action == "edit":
        result = guarded_edit()
    elif args.action == "status":
        result = status()
    elif args.action == "verify-handoff":
        result = handoff()
    elif args.action == "policy-check":
        result = policy_check(args.installed)
    elif args.action == "install-rules":
        result = install_rules()
    else:
        if args.action == "self-test":
            command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", TOOL_TEST, "-q"]
            timeout = 120
        elif args.action == "phase-tests":
            command = test_command(args.phase, phase=True)
            timeout = 300
        elif args.action == "regression":
            command = test_command(args.group)
            timeout = 300
        else:
            command = [DOC_PY, "scripts/build_reader_facing_monograph.py"]
            timeout = 300
        result = run_job(args.action, command, timeout)
        if args.action == "self-test":
            result["tool_test_sha256"] = sha(ROOT / TOOL_TEST)
            save_json(ROOT / OPS / "self-test-result.json", result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") not in {"FAIL", "TIMEOUT", "CHANGED", "LAUNCH_FAILED"} else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError, KeyError) as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error), "phase_completion": False}))
        raise SystemExit(2)
