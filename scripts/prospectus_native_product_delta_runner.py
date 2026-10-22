"""Bounded admitted replay of unchanged native evidence under reviewed product edits."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import gzip
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
from scripts import prospectus_native_product_delta as check


def size(folder):
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def save(folder, name, value, *, final=False):
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
    if name.endswith(".gz"):
        data = gzip.compress(data, mtime=0)
    check.require(size(folder) + len(data) < (32 if final else 30) * 1024**2, "Native compatibility evidence cap")
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def admission(a, name):
    folder, admitted, task = check.prior.preparation.prep.local(a.root, name), None, None
    check.require(folder.parent == a.base / "attempts/native-binding", "Wrong native compatibility attempt path")
    admitted = read(folder / "admission.json")
    program, tasks, _ = a.spec()
    task = tasks["native-binding"]
    check.selector(task)
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    check.require(event["kind"] == "ADMIT" and event["attempt"] == name and
        event["admission_sha256"] == file_hash(folder / "admission.json") and
        admitted["program_sha256"] == digest(program) and admitted["task_sha256"] == digest(task) and
        admitted["task_spec"] == task and admitted["binding"] == a.binding(task), "Current unchanged admission required")
    check.require(not (folder / "outputs.json").exists() and not (folder / "result.json").exists(), "Sealed attempt refused")
    check.prior.preparation.prep.files(folder)
    return folder, admitted, task


def tests(folder):
    target = folder / "tests"
    target.mkdir()
    code = 1
    with (target / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
        import pytest
        code = int(pytest.main(["-q", "-p", "no:cacheprovider", check.TEST, check.prior.TEST,
                               "--junitxml=" + str(target / "results.xml")]))
    result = {"exit_code": code, "status": "PASS" if code == 0 else "FAIL",
              "junit_sha256": file_hash(target / "results.xml") if (target / "results.xml").exists() else None}
    save(folder, "tests/result.json", result)
    check.require(code == 0, "Native product-delta tests failed; see retained tests.log")
    return check.check_tests(folder)


def finish(folder, task, result):
    save(folder, "result.json", {**result, "task": task["id"], "scope": "FINITE_CURRENT_NATIVE_COMPATIBILITY",
        "new_native_calls": 0, "new_subprocess_calls": 0, "independent_legal_acceptance": False,
        "portability_established": False, "whole_program_complete": False}, final=True)
    save(folder, "outputs.json", check.prior.preparation.prep.files(folder), final=True)


def run(name, stage):
    a = Authority(ROOT)
    with a.lock():
        folder, admitted, task = admission(a, name)
        index = check.STAGES.index(stage)
        started = {p.parent.name for p in (folder / "stages").glob("*/started.json")}
        completed = {p.parent.name for p in (folder / "stages").glob("*/result.json")}
        check.require(started == completed == set(check.STAGES[:index]), "Repeated/skipped/interrupted stage")
        records = [read(folder / "stages" / s / "result.json") for s in check.STAGES[:index]]
        check.require(all(r["status"] == "PASS" for r in records), "Failed predecessor stage")
        spent = sum(r["wall_seconds"] for r in records)
        check.require(spent < check.SELECTOR["execution_seconds"], "Native compatibility execution budget exhausted")
        current = check.methods(ROOT)
        if index:
            check.require(read(folder / "methods.json") == current, "Native compatibility methods changed")
        else:
            save(folder, "methods.json", current)
            save(folder, "method-snapshots.json.gz", {p: (ROOT / p).read_bytes().hex() for p in current})
        save(folder, "stages/" + stage + "/started.json", {
            "at": datetime.now(timezone.utc).isoformat(),
            "command": ["timeout", "120", ".venv/bin/python", check.RUNNER, "--attempt", name, "--stage", stage],
            "git_commit": admitted["git_commit"], "interpreter": sys.executable,
            "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic comparison",
            "inputs": admitted["binding"], "methods_sha256": digest(current), "plan": task["dossier"],
            "result": name + "/result.json"})
        tick, details, error = time.monotonic(), None, None
        try:
            with check.prior.bounded_stage(min(115, check.SELECTOR["execution_seconds"] - spent)), check.prior.live.offline():
                if stage == "tests":
                    details = tests(folder)
                elif stage == "historical-evidence":
                    details = check.historical_evidence(ROOT)
                    save(folder, "historical-evidence.json", details)
                elif stage.startswith("replay-"):
                    route = stage.removeprefix("replay-")
                    details = check.route(ROOT, route, rebuild=True)
                    save(folder, "routes/" + route + ".json", details)
                elif stage == "adverse":
                    details = check.adverse(ROOT)
                    save(folder, "adverse.json", details)
                elif stage == "seal":
                    check.require((folder / "RESULT.md").is_file(), "Actual result review required before seal")
                    details = {"current_routes_rebuilt": list(check.ROUTES), "new_native_calls": 0,
                               "independent_authority_validation": "pending"}
                check.require(admitted["binding"] == a.binding(task) and current == check.methods(ROOT),
                              "Methods or input bindings changed during stage")
                check.require(spent + time.monotonic() - tick < 720 and size(folder) < 30 * 1024**2,
                              "Native compatibility cumulative bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save(folder, "stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, final=True)
        result = {"status": "FAIL" if error else "PASS", "stage": stage, "error": error,
                  "details": details, "wall_seconds": time.monotonic() - tick}
        save(folder, "stages/" + stage + "/result.json", result, final=True)
        if error or stage == "seal":
            finish(folder, task, result)
        print(json.dumps({k: result[k] for k in ("status", "stage", "error", "wall_seconds")}))
        return int(error is not None)


def record(name):
    """Time the normal independent authority record without editing sealed evidence."""
    a = Authority(ROOT)
    tick = time.monotonic()
    value = a.record(name)
    event = next(e for e in reversed(a.events()) if e.get("attempt") == name)
    result = {"attempt": name, "authority_event": event, "wall_seconds": time.monotonic() - tick,
              "command": ["timeout", "210", ".venv/bin/python", check.RUNNER, "--attempt", name, "--stage", "record"]}
    save(ROOT / check.REVIEW, "actual-record.json", result)
    print(json.dumps({"kind": event["kind"], "reason": event.get("reason"),
                      "seq": event["seq"], "wall_seconds": result["wall_seconds"]}))
    return int(event["kind"] != "ACCEPT")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--attempt", required=True)
    p.add_argument("--stage", choices=(*check.STAGES, "record"), required=True)
    args = p.parse_args()
    return record(args.attempt) if args.stage == "record" else run(args.attempt, args.stage)


if __name__ == "__main__":
    raise SystemExit(main())
