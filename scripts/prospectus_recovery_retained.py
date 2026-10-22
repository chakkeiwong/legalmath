"""Finish current recovery checks using complete immutable state executions."""
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
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from legalmath.prospectus.execution_acceptance import checked_tests
from scripts import prospectus_recovery_current as prior
from scripts.prospectus_installed_profile_worker import execution_guard

BASE = prior.BASE
OLD = BASE + "/attempts/recovery/attempt-013"
REVIEW = BASE + "/reviews/retained-recovery-156"
SCRIPT = "scripts/prospectus_recovery_retained.py"
PLAN = "docs/plans/prospectus-retained-recovery-repair-2026-10-16.md"
TESTS = ("tests/prospectus_successor/test_closure_program.py", "tests/prospectus_successor/test_closure_correction_images.py")
STAGES = ("reconstruct", "tests", "verify", "seal")
SELECTOR = {"version": "retained-current-recovery.v1", "source_attempt": OLD, "stages": list(STAGES),
    "work_seconds": 110, "stage_seconds": 115, "execution_seconds": 400,
    "prepacking_bytes": 256 * 1024**2, "packed_bytes": 64 * 1024**2,
    "native_calls": 0, "subprocess_calls": 0, "test_starts": 1, "unchanged_retries": 0}
require, save = prior.require, prior.save


def original_envelope(root):
    a = Authority(root)
    event = read(root / REVIEW / "history.json")["rejected_event"]
    require(event in a.events() and event["kind"] == "REJECT" and event["seq"] == 1150 and
        event["attempt"] == OLD and a.retained_evidence_valid(event), "Actual recovery rejection changed")
    folder = root / OLD
    require(read(folder / "result.json")["error"] == {"type": "ValueError", "message": "Recovery isolated workspace limit"},
        "Original recovery failure differs")
    require({p.name for p in (folder / "stages").iterdir()} == set(prior.STAGES[:-2]), "Original recovery stage denominator differs")
    stages = [read(folder / "stages" / s / "result.json") for s in prior.STAGES[:-2]]
    require(all(r["status"] == ("FAIL" if s == "final-restored" else "PASS") and
        r["stage"] == s and 0 <= r["wall_seconds"] < 115 for s, r in zip(prior.STAGES[:-2], stages)),
        "Unexpected original recovery stage failure")
    require(sum(r["wall_seconds"] for r in stages) < 1080, "Original recovery time bound exceeded")
    started = read(folder / "started.json")
    require(started["states"] == list(prior.STATES) and all(file_hash(root / p) == h
        for p, h in {**started["methods"], **started["sources"]}.items()), "Original current methods/sources changed")
    states = [read(folder / "steps" / s / "result.json") for s in prior.STATES]
    require(all(r["state"] == s and r["status"] == "PASS" and r["actual_equals_clean"] is True and
        r["invalidated_before_marker"] is True for s, r in zip(prior.STATES, states)), "Original complete state evidence failed")
    require(not (folder / "tests.xml").exists(), "Original focused suite unexpectedly exists")
    return {"rejected_event": event["seq"], "source_attempt": OLD, "state_count": len(states),
        "state_seconds": sum(r["wall_seconds"] for r in states),
        "wrapper_seconds": sum(r["wall_seconds"] for r in stages), "historical_failure_preserved": True}


def methods(root):
    original = read(root / OLD / "started.json")["methods"]
    paths = {*original, SCRIPT, prior.SCRIPT, PLAN, REVIEW + "/history.json", REVIEW + "/prepare.py",
        REVIEW + "/REVIEW.md", "scripts/prospectus_installed_profile_worker.py", *TESTS}
    return {p: file_hash(root / p) for p in sorted(paths)}


def copied_files(root):
    folder = root / OLD
    paths = [folder / p for p in ("started.json", "correction-baseline-request.json", "probe.py",
        "run_tests.py", "finalize_recovery.py", "WORK-PLAN.md")]
    paths.extend(p for p in (folder / "steps").rglob("*") if p.is_file())
    return {str(p.relative_to(folder)): file_hash(p) for p in sorted(paths)}


def selector(task):
    require(task.get("id") == "recovery" and not task.get("validator") and
        task.get("retained_recovery") == SELECTOR, "Unreviewed retained recovery admission")


def run(name, stage):
    a = Authority(ROOT)
    with a.lock():
        folder = a.path(name)
        program, tasks, _ = a.spec(); task = tasks["recovery"]
        selector(task)
        admitted = read(folder / "admission.json")
        event = next(e for e in reversed(a.events()) if e.get("task") == "recovery")
        require(folder.parent == a.base / "attempts/recovery" and event["kind"] == "ADMIT" and event["attempt"] == name and
            admitted["program_sha256"] == digest(program) and admitted["task_spec"] == task and
            admitted["binding"] == a.binding(task), "Current unchanged retained recovery admission required")
        require(not (folder / "outputs.json").exists() and not (folder / "result.json").exists(), "Sealed retained recovery")
        index = STAGES.index(stage)
        require({p.parent.name for p in (folder / "stages").glob("*/started.json")} ==
            {p.parent.name for p in (folder / "stages").glob("*/result.json")} == set(STAGES[:index]),
            "Repeated/skipped/interrupted retained recovery stage")
        rows = [read(folder / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["error"] is None and r["wall_seconds"] < 115 and
            r["process_guard"] == {"starts": 0, "blocked": 0} for r in rows), "Failed retained recovery predecessor")
        spent = sum(r["wall_seconds"] for r in rows)
        require(spent < 400, "Retained recovery aggregate bound exceeded")
        current = methods(ROOT)
        if index:
            require(read(folder / "validation-methods.json") == current, "Retained recovery validation methods changed")
        else:
            save(folder, "validation-methods.json", current)
        save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
            "command": ["timeout", "120", ".venv/bin/python", SCRIPT, "--attempt", name, "--stage", stage],
            "git_commit": admitted["git_commit"], "python": sys.executable, "cpu_gpu": "CPU only; GPUs intentionally hidden",
            "random_seeds": "N/A deterministic retained recovery", "inputs": admitted["binding"], "plan": PLAN,
            "source_execution": OLD, "result": name + "/result.json"})
        tick, details, error, guard = time.monotonic(), None, None, None
        try:
            with prior.bounded_stage(min(110, 400 - spent)), execution_guard() as guard:
                if stage == "reconstruct":
                    envelope = original_envelope(ROOT)
                    copy_map = copied_files(ROOT)
                    require(sum((ROOT / OLD / p).stat().st_size for p in copy_map) + prior.storage(folder)["unique_bytes"] <
                        252 * 1024**2, "Retained recovery copies exceed prepacking bound")
                    for path, expected in copy_map.items():
                        target = folder / path; target.parent.mkdir(parents=True, exist_ok=True)
                        with target.open("xb") as stream:
                            stream.write((ROOT / OLD / path).read_bytes())
                        require(file_hash(target) == expected, "Retained recovery copy changed")
                    save(folder, "source-copy.json", {"source_attempt": OLD, "files": copy_map})
                    save(folder, "original-envelope.json", envelope)
                    for path, expected in current.items():
                        target = folder / "method" / path; target.parent.mkdir(parents=True, exist_ok=True)
                        with target.open("xb") as stream:
                            stream.write((ROOT / path).read_bytes())
                        require(file_hash(target) == expected, "Retained recovery method snapshot changed")
                    details = {**envelope, "copied_files": len(copy_map)}
                elif stage == "tests":
                    with (folder / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
                        import pytest
                        code = int(pytest.main(["-q", "-p", "no:cacheprovider", *TESTS, "--junitxml=" + str(folder / "tests.xml")]))
                    require(code == 0, "Retained recovery focused tests failed")
                    details = {"status": "PASS", "returncode": code, "tests": checked_tests(folder / "tests.xml", 44),
                        "junit_sha256": file_hash(folder / "tests.xml"), "runner": "in-process pytest;original test modules unchanged"}
                    save(folder, "tests-result.json", details)
                elif stage == "verify":
                    details = prior.load(folder / "finalize_recovery.py").validate()
                    save(folder, "comparison.json", details)
                else:
                    require((folder / "RESULT.md").is_file(), "Actual retained recovery result review required")
                    require(read(folder / "comparison.json")["status"] == "PASS", "Retained recovery comparison incomplete")
                    prior.pack(folder)
                    details = {**prior.storage(folder), "source_execution": OLD, "historical_rejection_preserved": True}
                copy_map = read(folder / "source-copy.json")["files"]
                require(copy_map == copied_files(ROOT) and all(file_hash(folder / p) == h for p, h in copy_map.items()),
                    "Complete retained recovery evidence changed")
                require(current == methods(ROOT) and admitted["binding"] == a.binding(task), "Retained recovery methods/inputs changed")
                require(guard.result() == {"starts": 0, "blocked": 0}, "Unexpected retained recovery process action")
            require(time.monotonic() - tick < 115 and spent + time.monotonic() - tick < 400, "Retained recovery recorded bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save(folder, "stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, final=True)
        value = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error, "details": details,
            "process_guard": guard.result() if guard is not None else None, "wall_seconds": time.monotonic() - tick}
        save(folder, "stages/" + stage + "/result.json", value, final=True)
        if error or stage == "seal":
            save(folder, "result.json", {**value, "task": "recovery", "scope": "RETAINED_CURRENT_RECOVERY",
                "source_execution": OLD, "historical_rejection_preserved": True, "new_native_calls": 0,
                "new_subprocess_calls": 0, "whole_program_complete": False, "independent_legal_acceptance": False}, final=True)
            save(folder, "outputs.json", prior.files(folder), final=True)
        print(json.dumps({k: value[k] for k in ("stage", "status", "error", "wall_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--stage", choices=STAGES, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.attempt, args.stage))
