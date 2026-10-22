"""Retain a named verification, including failures, in its current admission."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "scripts/prospectus_verify_task.py"
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from legalmath.prospectus.execution_authority import Authority, CODE, digest, file_hash, read, write
from legalmath.prospectus import execution_acceptance as checks


@contextmanager
def cooperative_cancellation():
    """Finalize cooperative timeouts; SIGKILL and filesystem failure are excluded."""
    previous = signal.getsignal(signal.SIGTERM)
    def terminate(signum, frame):
        raise TimeoutError("Verification interrupted by SIGTERM")
    signal.signal(signal.SIGTERM, terminate)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


@contextmanager
def retained_evidence_only():
    """Named retained-evidence checks must not launch fresh native workers."""
    previous = subprocess.Popen
    def refuse(*args, **kwargs):
        raise RuntimeError("Subprocess prohibited in retained-evidence verification")
    subprocess.Popen = refuse
    try:
        yield
    finally:
        subprocess.Popen = previous


def dispatch(authority, attempt, task, admitted):
    root = authority.root
    if task.get("validator") == "recovery-sequence.v1":
        return checks.recovery_evidence(root, task)
    if task.get("validator") == "native-binding-files.v1":
        return checks.native_binding_evidence(root, task)
    if task.get("validator") == "native-installed-profile.v1":
        return checks.native_installed_evidence(root, task)
    if task.get("validator") == "authority-audit.v1":
        tests = task.get("acceptance_tests",
            "docs/implementation/prospectus-execution-authority/finite-acceptance-defensive-tests.xml")
        if tests not in task["inputs"] or file_hash(root / tests) != admitted["binding"][tests]:
            raise ValueError("Current reviewed test report must be an admitted unchanged input")
        with (attempt / "tests.xml").open("xb") as stream:
            stream.write((root / tests).read_bytes())
        return checks.authority_evidence(root)
    raise ValueError("Only reviewed named finite verification is supported")


def verify_task(authority, attempt_name):
    """Return a CLI exit code and summary; never record or accept a task here."""
    root = authority.root
    attempt = authority.path(attempt_name)
    if not attempt.is_relative_to(authority.base / "attempts"):
        raise ValueError("Verification requires an authority attempt path")
    admitted = read(attempt / "admission.json")
    program, tasks, _ = authority.spec()
    task = tasks[admitted["task"]]
    row = next(r for r in authority.status()["tasks"] if r["id"] == task["id"])
    if row["state"] != "ADMITTED" or row["attempt"] != attempt_name:
        raise ValueError("Existing current admission required; never start duplicate work")
    if (admitted["binding"] != authority.binding(task)
            or admitted["program_sha256"] != digest(program)
            or admitted["task_sha256"] != digest(task)):
        raise ValueError("Admitted source/method or program changed")
    if any((attempt / name).exists() for name in ("started.json", "result.json", "outputs.json", "verification.json")):
        raise FileExistsError("Verification already started; preserve and reconcile existing evidence")
    methods = {p: file_hash(root / p) for p in [*CODE, SCRIPT]}
    tick = time.monotonic()
    write(attempt / "started.json", {
        "started_at": datetime.now(timezone.utc).isoformat(), "git_commit": admitted["git_commit"],
        "command": ["timeout", "120", ".venv/bin/python", SCRIPT, "--attempt", attempt_name],
        "environment": sys.executable, "cpu_gpu": "N/A retained evidence checks; no GPU/framework used",
        "random_seeds": "N/A deterministic", "plan": task["dossier"],
        "methods": methods, "program_revision": program["revision"],
        "result_file": attempt_name + "/result.json"}, exclusive=True)
    phase, error, code = "method snapshots", None, 0
    try:
        with cooperative_cancellation(), retained_evidence_only():
            for name, expected in methods.items():
                data = (root / name).read_bytes()
                target = attempt / "method" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write(data)
                if file_hash(target) != expected:
                    raise ValueError("Verification method changed before capture: " + name)
            phase = "validator"
            verification = dispatch(authority, attempt, task, admitted)
            if not isinstance(verification, dict):
                raise ValueError("Named validator returned no evidence object")
            write(attempt / "verification.json", verification, exclusive=True)
            phase = "final bindings"
            current, current_tasks, _ = authority.spec()
            if (digest(current) != admitted["program_sha256"]
                    or digest(current_tasks[task["id"]]) != admitted["task_sha256"]
                    or authority.binding(task) != admitted["binding"]
                    or any(file_hash(root / p) != h for p, h in methods.items())):
                raise ValueError("Admitted method/input changed during verification")
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc), "phase": phase}
        code = 124 if isinstance(exc, TimeoutError) else 130 if isinstance(exc, KeyboardInterrupt) else 1
        with (attempt / "error.log").open("x") as stream:
            stream.write(traceback.format_exc())
    result = {"status": "FAIL" if error else "PASS", "task": task["id"],
        "scope": "FINITE_ENGINEERING_ONLY", "whole_program_complete": False,
        "wall_seconds": time.monotonic() - tick, "ended_at": datetime.now(timezone.utc).isoformat(),
        "acceptance_pending": error is None, "exit_code": code,
        "next_action": "Record the actual result through the authority, inspect its event and refresh; no retry or acceptance implied"}
    if error:
        result["error"] = error
    write(attempt / "result.json", result, exclusive=True)
    verdict = ("The named validator failed. Its actual exception is retained in error.log; "
               "this attempt is not eligible for acceptance." if error else
               "The named validator returned retained evidence in verification.json. "
               "The authority must independently recheck it before acceptance.")
    note = ("# Finite engineering verification\n\n" + verdict + "\n\n"
        "Current method snapshots and the actual command are retained. No test total, "
        "native call count or source result is inferred from a historical narrative. "
        "Source acquisition, independent review, portability and broader product "
        "requirements remain governed by their original obligations.\n\n"
        "| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Limit |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        f"| {'Reject verification' if error else 'Submit verification'} | {result['status']} | "
        f"{'Actual failure retained' if error else 'No named-check failure detected'} | "
        "Finite evidence and shared implementation | Authority record and refresh | "
        "No independent legal acceptance or whole-program completion |\n\n"
        "A retained failure identifies the condition that prevented this verification; "
        "it does not establish a fundamental external-package defect. Successful "
        "checks remain limited by their named validator and source coverage. "
        "Cooperative termination is handled; hard kills and storage failures require "
        "separate interruption reconciliation.\n")
    with (attempt / "RESULT.md").open("x") as stream:
        stream.write(note)
    manifest = {str(p.relative_to(attempt)): file_hash(p) for p in sorted(attempt.rglob("*"))
                if p.is_file() and "__pycache__" not in p.parts and p.name != "outputs.json"}
    write(attempt / "outputs.json", manifest, exclusive=True)
    return code, {"status": "FAILED_RETAINED_PENDING_AUTHORITY_RECORD" if error else "VERIFIED_PENDING_AUTHORITY_RECORD",
        "task": task["id"], "wall_seconds": result["wall_seconds"], "files": len(manifest), "error": error}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    code, summary = verify_task(Authority(ROOT), args.attempt)
    print(json.dumps(summary))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
