"""Current bounded authority tests and evidence, without changing its validator."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
from legalmath.prospectus.execution_authority import Authority, CODE, digest, file_hash, read
from legalmath.prospectus import execution_acceptance as checks
from scripts.prospectus_native_campaign import bounded_stage
from scripts.prospectus_installed_profile_worker import execution_guard

BASE = "docs/implementation/prospectus-execution-authority"
REVIEW = BASE + "/reviews/current-authority-158"
SCRIPT = "scripts/prospectus_authority_current.py"
PLAN = "docs/plans/prospectus-current-finite-acceptance-2026-10-16.md"
TESTS = tuple("tests/prospectus/test_" + name + ".py" for name in
    ("execution_authority", "execution_acceptance", "verify_task", "continuation_review"))
STAGES = ("tests", "verify", "seal")
SELECTOR = {"version": "current-authority.v1", "stages": list(STAGES), "work_seconds": 110,
    "stage_seconds": 115, "execution_seconds": 300, "evidence_bytes": 32 * 1024**2,
    "test_starts": 1, "native_calls": 0, "subprocess_calls": 0, "unchanged_retries": 0}


def require(value, message):
    if not value:
        raise ValueError(message)


def methods(root):
    paths = {*CODE, SCRIPT, *TESTS, "scripts/prospectus_verify_task.py", "scripts/prospectus_continuation.py",
        "scripts/prospectus_native_campaign.py", "scripts/prospectus_installed_profile_worker.py",
        "src/legalmath/prospectus/execution_acceptance.py", "src/legalmath/prospectus/successor/closure_program.py"}
    return {p: file_hash(root / p) for p in sorted(paths)}


def files(folder):
    return {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*"))
        if p.is_file() and p.name != "outputs.json" and "__pycache__" not in p.parts}


def save(folder, name, value, *, final=False):
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
    require(sum(p.stat().st_size for p in folder.rglob("*") if p.is_file()) + len(data) <
        (32 if final else 30) * 1024**2, "Authority evidence bound exceeded")
    path = folder / name; path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def selector(task):
    require(task.get("id") == "authority-acceptance" and task.get("validator") == "authority-audit.v1" and
        task.get("current_authority") == SELECTOR, "Unreviewed current authority admission")


def run(name, stage):
    a = Authority(ROOT)
    with a.lock():
        folder = a.path(name)
        program, tasks, _ = a.spec(); task = tasks["authority-acceptance"]
        selector(task)
        admitted = read(folder / "admission.json")
        event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
        require(folder.parent == a.base / "attempts/authority-acceptance" and event["kind"] == "ADMIT" and
            event["attempt"] == name and admitted["program_sha256"] == digest(program) and
            admitted["task_spec"] == task and admitted["binding"] == a.binding(task), "Current unchanged authority admission required")
        require(not (folder / "outputs.json").exists() and not (folder / "result.json").exists(), "Authority attempt is sealed")
        index = STAGES.index(stage)
        require({p.parent.name for p in (folder / "stages").glob("*/started.json")} ==
            {p.parent.name for p in (folder / "stages").glob("*/result.json")} == set(STAGES[:index]),
            "Repeated/skipped/interrupted authority stage")
        rows = [read(folder / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["error"] is None and r["wall_seconds"] < 115 and
            r["process_guard"] == {"starts": 0, "blocked": 0} for r in rows), "Failed authority predecessor")
        spent = sum(r["wall_seconds"] for r in rows)
        require(spent < 300, "Authority aggregate bound exceeded")
        current = methods(ROOT)
        if index:
            require(read(folder / "methods.json") == current, "Authority methods changed")
        else:
            save(folder, "methods.json", current)
            for path, expected in current.items():
                target = folder / "method" / path
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write((ROOT / path).read_bytes())
                require(file_hash(target) == expected, "Authority snapshot changed")
        save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
            "command": ["timeout", "120", ".venv/bin/python", SCRIPT, "--attempt", name, "--stage", stage],
            "git_commit": admitted["git_commit"], "python": sys.executable, "cpu_gpu": "CPU only; GPUs intentionally hidden",
            "random_seeds": "N/A deterministic authority checks", "inputs": admitted["binding"],
            "plan": PLAN, "result": name + "/result.json"})
        tick, details, error, guard = time.monotonic(), None, None, None
        try:
            with bounded_stage(min(110, 300 - spent)), execution_guard() as guard:
                if stage == "tests":
                    with (folder / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
                        import pytest
                        code = int(pytest.main(["-q", "-p", "no:cacheprovider", *TESTS, "--junitxml=" + str(folder / "tests.xml")]))
                    require(code == 0, "Current authority tests failed")
                    details = {"tests": checks.checked_tests(folder / "tests.xml", 1), "exit_code": code,
                        "junit_sha256": file_hash(folder / "tests.xml")}
                elif stage == "verify":
                    evidence = checks.authority_evidence(ROOT)
                    save(folder, "verification.json", evidence)
                    details = {"tasks": len(evidence["tasks"]) + 1, "obligations": len(evidence["obligations"]),
                        "recovery": evidence["recovery_accepted_attempt"], "whole_program_complete": False}
                else:
                    require((folder / "RESULT.md").is_file(), "Actual authority result review required")
                    require(read(folder / "verification.json") == checks.authority_evidence(ROOT), "Current authority evidence changed")
                    details = {"current_evidence_rechecked": True, "acceptance_pending": True}
                require(current == methods(ROOT) and admitted["binding"] == a.binding(task), "Authority methods/inputs changed")
                require(guard.result() == {"starts": 0, "blocked": 0}, "Unexpected authority process action")
            require(time.monotonic() - tick < 115 and spent + time.monotonic() - tick < 300, "Authority recorded bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save(folder, "stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, final=True)
        value = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error, "details": details,
            "process_guard": guard.result() if guard is not None else None, "wall_seconds": time.monotonic() - tick}
        save(folder, "stages/" + stage + "/result.json", value, final=True)
        if error or stage == "seal":
            save(folder, "result.json", {**value, "task": task["id"], "scope": "FINITE_ENGINEERING_ONLY",
                "whole_program_complete": False, "independent_legal_acceptance": False}, final=True)
            save(folder, "outputs.json", files(folder), final=True)
        print(json.dumps({k: value[k] for k in ("stage", "status", "error", "wall_seconds")}))
        return int(error is not None)


def record(name):
    a = Authority(ROOT); tick = time.monotonic()
    a.record(name)
    event = next(e for e in reversed(a.events()) if e.get("attempt") == name)
    value = {"attempt": name, "authority_event": event, "wall_seconds": time.monotonic() - tick,
        "command": ["timeout", "120", ".venv/bin/python", SCRIPT, "--attempt", name, "--stage", "record"]}
    save(ROOT / REVIEW, "actual-record.json", value)
    print(json.dumps({"kind": event["kind"], "seq": event["seq"], "reason": event.get("reason"), "wall_seconds": value["wall_seconds"]}))
    return int(event["kind"] != "ACCEPT")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--stage", choices=(*STAGES, "record"), required=True)
    args = parser.parse_args()
    raise SystemExit(record(args.attempt) if args.stage == "record" else run(args.attempt, args.stage))
