"""Admitted offline source rehearsal; retained bytes are never fresh calls."""
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
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
    LEGALMATH_OCR_PYTHON="/home/chakwong/miniconda3/envs/tfgpu/bin/python")
from legalmath.prospectus.execution_authority import Authority, file_hash, read, write
from legalmath.prospectus import native_source_rehearsal as source
from legalmath.prospectus import native_current_preparation as preparation
from scripts.prospectus_native_campaign import bounded_stage, no_subprocess, save, seal

STAGES = ("prepare", *("rehearse-" + r for r in preparation.ROUTES), "finalize")


def check_tests(folder, current):
    runs = sorted((folder / "validation").glob("run-*/result.json"))
    preparation.require(1 <= len(runs) <= 2, "Source rehearsal test allowance differs")
    result = read(runs[-1])
    preparation.require(result["status"] == "PASS" and result["exit_code"] == 0
        and 0 <= result["wall_seconds"] <= 120 and read(runs[-1].parent / "methods.json") == current
        and file_hash(runs[-1].parent / "tests.xml") == result["tests_sha256"], "Current source tests do not match")
    import xml.etree.ElementTree as ET
    tree = ET.parse(runs[-1].parent / "tests.xml")
    suites = list(tree.getroot().iter("testsuite"))
    preparation.require(suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ("errors", "failures", "skipped")),
                        "Source rehearsal tests failed or skipped")
    names = {r.get("name", "").split("[")[0] for r in tree.getroot().iter("testcase")}
    preparation.require(preparation.REQUIRED_TESTS | {
        "test_actual_source_runtime_executes_recorded_boundary", "test_recorded_boundary_refuses_changed_dispatch",
        "test_missing_or_extra_recorded_calls_refuse", "test_recorded_boundary_restores_after_failure",
        "test_rehearsal_driver_retains_source_failure", "test_rehearsal_rejects_fresh_stage"} <= names,
        "Source rehearsal refusal tests missing")
    return {"tests": sum(int(s.get("tests", 0)) for s in suites), "starts": len(runs),
            "tests_sha256": result["tests_sha256"]}


def tests(authority, attempt_name):
    with authority.lock():
        folder, admitted, task = preparation.current_admission(authority, attempt_name)
        preparation.require(not (folder / "started.json").exists(), "Tests must precede source method freeze")
        runs = sorted((folder / "validation").glob("run-*"))
        preparation.require(len(runs) < 2 and all((r / "result.json").exists() for r in runs), "Test budget exhausted/interrupted")
        target = folder / "validation" / f"run-{len(runs)+1:03d}"
        target.mkdir(parents=True)
        current = source.methods(authority.root)
        write(target / "methods.json", current, exclusive=True)
        save(folder, str(target.relative_to(folder)) + "/method-snapshots.json.gz",
             {p: (authority.root / p).read_text() for p in current})
        write(target / "started.json", run_start(admitted, task, attempt_name, "tests"), exclusive=True)
        tick, code, error = time.monotonic(), 1, None
        try:
            with (target / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
                with bounded_stage(), no_subprocess({"attempts": 0}):
                    import pytest
                    code = int(pytest.main(["-q", "-p", "no:cacheprovider", *source.TESTS,
                                           "--junitxml=" + str(target / "tests.xml")]))
                    preparation.require(source.methods(authority.root) == current, "Source methods changed during tests")
        except BaseException as exc:
            code = 124 if isinstance(exc, TimeoutError) else 130 if isinstance(exc, KeyboardInterrupt) else 1
            error = {"type": type(exc).__name__, "message": str(exc)}
            with (target / "error.log").open("x") as stream: stream.write(traceback.format_exc())
        result = {"status": "PASS" if code == 0 else "FAIL", "exit_code": code, "error": error,
            "wall_seconds": time.monotonic() - tick,
            "tests_sha256": file_hash(target / "tests.xml") if (target / "tests.xml").exists() else None}
        write(target / "result.json", result, exclusive=True)
        return code, result


def run_start(admitted, task, name, stage):
    return {"stage": stage, "started_at": datetime.now(timezone.utc).isoformat(),
        "command": ["timeout", "120", ".venv/bin/python", source.SCRIPT, "--attempt", name, "--stage", stage],
        "environment": sys.executable, "git_commit": admitted["git_commit"],
        "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic",
        "plan": task["dossier"], "program_revision": admitted["revision"],
        "scope": "Recorded-byte source rehearsal; no fresh native execution"}


def prepare(root, folder):
    current = source.methods(root)
    tested = check_tests(folder, current)
    save(folder, "methods.json", current)
    save(folder, "method-snapshots.json.gz", {p: (root / p).read_text() for p in current})
    save(folder, "offline-ledger.json", {"version": preparation.VERSION, "native_call_allowance": 0,
        "historical_lower_bound": 50, "reservations": [],
        "scope": "Offline preparation; historical floor is not a successful-call total"})
    save(folder, "historical-evidence.json", preparation.history(root))
    return {"methods": len(current), "tests": tested, "native_calls": 0}


def rehearse(root, folder, route):
    baseline_folder = preparation.local(root, preparation.ROUTES[route])
    old, old_answer = preparation.historical.products(baseline_folder)
    p1, raw, dispatch = source.source_product(root, route)
    save(folder, "routes/" + route + "/dispatch.json", dispatch)
    if not dispatch["consumed_P1_complete_equality"] or dispatch["raw_complete_equality"] is False:
        save(folder, "routes/" + route + "/actual-raw-P1.json.gz", raw)
        save(folder, "routes/" + route + "/actual-P1.json.gz", p1)
        raise ValueError("Complete current source P1 differs from retained baseline")
    values, answer = source.downstream(root, p1, old)
    refs, equal = {}, {}
    for key, obj in {**values, "answer": answer}.items():
        equal[key] = obj == (old_answer if key == "answer" else old[key])
        path = baseline_folder / (key + ".json.gz")
        if not equal[key]:
            relative = "routes/" + route + "/" + key + ".json.gz"
            save(folder, relative, obj)
            path = folder / relative
        refs[key] = {"path": str(path.relative_to(root)), "sha256": file_hash(path)}
    save(folder, "routes/" + route + "/comparison.json", {"route": route, "objects": refs,
        "complete_equality": equal, "scope": source.VERSION, "fresh_native_execution_established": False})
    preparation.require(all(equal.values()), "Current source/downstream full comparison differs")
    return {"route": route, "recorded_byte_deliveries": 2, "native_processes": 0,
            "complete_source_and_downstream_equality": True}


def run_stage(authority, name, stage):
    preparation.require(stage in STAGES, "Fresh native or unknown rehearsal stage refused")
    with authority.lock():
        folder, admitted, task = preparation.current_admission(authority, name)
        target = folder / "stages" / stage
        preparation.require(not target.exists(), "Source rehearsal stage already started")
        for marker in (folder / "stages").glob("*/started.json"):
            preparation.require((marker.parent / "result.json").exists(), "Interrupted stage needs reconciliation")
        if stage == "prepare":
            preparation.require(not (folder / "started.json").exists(), "Preparation already started")
        else:
            preparation.require(read(folder / "stages/prepare/result.json")["status"] == "PASS", "Preparation required")
            source.check_methods(authority.root, folder)
            preparation.check_zero_ledger(folder)
        tick, error, details, counter = time.monotonic(), None, None, {"attempts": 0}
        start = run_start(admitted, task, name, stage)
        if stage == "prepare": save(folder, "started.json", start)
        save(folder, "stages/" + stage + "/started.json", start)
        try:
            with bounded_stage(), no_subprocess(counter):
                if stage == "prepare": details = prepare(authority.root, folder)
                elif stage == "finalize":
                    tested = check_tests(folder, source.methods(authority.root))
                    details = source.evidence(authority.root, folder)
                    details["tests"] = tested
                    save(folder, "source-rehearsal.json", details)
                else: details = rehearse(authority.root, folder, stage.removeprefix("rehearse-"))
                preparation.current_admission(authority, name)
                source.check_methods(authority.root, folder)
                preparation.check_zero_ledger(folder)
                preparation.require(counter["attempts"] == 0, "Unexpected subprocess during source rehearsal")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            with (target / "error.log").open("x") as stream: stream.write(traceback.format_exc())
        code = 0 if error is None else 124 if error["type"] == "TimeoutError" else 130 if error["type"] == "KeyboardInterrupt" else 1
        result = {"status": "PASS" if error is None else "FAIL", "stage": stage, "error": error,
            "wall_seconds": time.monotonic()-tick, "subprocess_attempts": counter["attempts"],
            "exit_code": code, "details": details, "fresh_native_execution_established": False}
        write(target / "result.json", result, exclusive=True)
        if error is not None or stage == "finalize": seal(folder, task, result)
        return code, {k: result[k] for k in ("status", "stage", "error", "wall_seconds", "subprocess_attempts")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--stage", required=True)
    args = parser.parse_args()
    authority = Authority(ROOT)
    code, result = tests(authority, args.attempt) if args.stage == "tests" else run_stage(authority, args.attempt, args.stage)
    print(json.dumps(result))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
