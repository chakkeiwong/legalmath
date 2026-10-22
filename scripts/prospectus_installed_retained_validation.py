"""Current installed acceptance from preserved actual executions, with zero calls."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import os
import sys
import time
import traceback
import types

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts import prospectus_installed_profile_refresh as prior

BASE = prior.BASE
OLD = BASE + "/attempts/native-confinement/attempt-010"
REVIEW = BASE + "/reviews/installed-retained-154"
SCRIPT = "scripts/prospectus_installed_retained_validation.py"
TEST = "tests/prospectus/test_installed_retained_validation.py"
PLAN = "docs/plans/prospectus-installed-validation-repair-2026-10-16.md"
STAGES = ("tests", "retained-envelope", "compare-fresh", "compare-retained", "seal")
SELECTOR = {"version": "installed-retained-validation.v1", "review": REVIEW, "source_attempt": OLD,
    "new_native_calls": 0, "new_subprocess_calls": 0, "stages": list(STAGES),
    "work_seconds": 110, "stage_seconds": 115, "execution_seconds": 400,
    "validation_seconds": 210, "evidence_bytes": 32 * 1024**2}
require = prior.require


def dispatch_candidate(before):
    marker = "def validate_submission(root, attempt, task):\n"
    require(before.count(marker) == 1, "Unexpected installed dispatch baseline")
    return before.replace(marker, marker +
        '    if "retained_profile_validation" in task:\n'
        '        from scripts.prospectus_installed_retained_validation import validate_submission as validate_retained\n'
        '        return validate_retained(root, attempt, task)\n')


def exact_bridge(frozen, snapshots, current):
    require(set(frozen) == set(snapshots) == set(current), "Installed method inventory differs")
    require(all(hashlib.sha256(bytes.fromhex(snapshots[p])).hexdigest() == h for p, h in frozen.items()), "Forged installed method snapshot")
    require(all(current[p] == h for p, h in frozen.items() if p != prior.SCRIPT), "Unreviewed installed method change")
    candidate = dispatch_candidate(bytes.fromhex(snapshots[prior.SCRIPT]).decode()).encode()
    require(current[prior.SCRIPT] == hashlib.sha256(candidate).hexdigest(), "Unreviewed installed dispatch bytes")
    return frozen


def frozen_checker(root):
    folder = root / OLD
    frozen = read(folder / "methods.json")
    snapshots = prior.helper.read(folder / "method-snapshots.json.gz")
    checked = exact_bridge(frozen, snapshots, prior.methods(root))
    module = types.ModuleType("frozen_installed_010")
    module.__file__ = str(root / prior.SCRIPT)
    source = bytes.fromhex(snapshots[prior.SCRIPT]).decode()
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    # The sole allowed live change is the dispatch proven above. All actual
    # evidence functions below execute their exact previously frozen bytes.
    module.methods = lambda selected_root: exact_bridge(checked, snapshots, prior.methods(Path(selected_root)))
    return module


def methods(root):
    return {**prior.methods(root), SCRIPT: file_hash(root / SCRIPT), TEST: file_hash(root / TEST)}


def selector(task):
    require(task.get("id") == "native-confinement" and task.get("validator") == prior.prior.INSTALLED and
        task.get("product_delta_acceptance") == prior.SELECTOR and task.get("retained_profile_validation") == SELECTOR and
        task.get("native_call_allowance") == 0 and task.get("retained_acceptance_only") is True, "Unreviewed retained installed selector")


def stage_envelope(rows):
    require(len(rows) == len(prior.STAGES) and [r["stage"] for r in rows] == list(prior.STAGES), "Retained installed stages differ")
    require(all(r["status"] == "PASS" and r["error"] is None and 0 <= r["wall_seconds"] <
        (120 if r["stage"] == "validate" else 115) for r in rows), "Retained execution stage failed or exceeded bound")
    require([r["stage"] for r in rows if r["wall_seconds"] >= 115] == ["validate"] and
        next(r["wall_seconds"] for r in rows if r["stage"] == "validate") == 115.07405699742958,
        "Unexpected retained timing failure")
    require(sum(r["wall_seconds"] for r in rows) < 1200, "Retained aggregate bound exceeded")


def envelope(root):
    a = Authority(root)
    history = read(root / REVIEW / "history.json")
    event = history["rejected_event"]
    require(event in a.events() and event["seq"] == 1137 and event["kind"] == "REJECT" and event["attempt"] == OLD and
        event["reason"] == "Installed current stage failed or exceeded bound" and a.retained_evidence_valid(event), "Actual installed rejection missing or changed")
    old = root / OLD
    require({p.name for p in (old / "stages").iterdir()} == set(prior.STAGES), "Retained stage denominator differs")
    rows = [read(old / "stages" / s / "result.json") for s in prior.STAGES]
    stage_envelope(rows)
    checker = frozen_checker(root)
    env, profile, manifest = checker.profile_context(root, old)
    return {"rejected_event": event["seq"], "historical_timing_failure_preserved": True,
        "old_stage_seconds": sum(r["wall_seconds"] for r in rows), "old_methods_sha256": digest(read(old / "methods.json")),
        "profile_sha256": checker.product.digest(profile), "profile_files": len(manifest["files"]), "environment": str(env),
        "new_native_calls": 0, "new_subprocess_calls": 0}


def save(folder, name, value, *, final=False):
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
    if name.endswith(".gz"):
        data = gzip.compress(data, mtime=0)
    require(sum(p.stat().st_size for p in folder.rglob("*") if p.is_file()) + len(data) < (32 if final else 30) * 1024**2, "Retained validation storage limit")
    path = folder / name; path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def checked_tests(folder):
    result = read(folder / "tests/result.json")
    require(result["status"] == "PASS" and result["exit_code"] == 0 and result["junit_sha256"] == file_hash(folder / "tests/results.xml"), "Retained validation tests failed/changed")
    tree = prior.ET.parse(folder / "tests/results.xml").getroot()
    suites = list(tree.iter("testsuite"))
    require(suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ("errors", "failures", "skipped")), "Retained validation failed/skipped tests")
    names = {row.get("name") for row in tree.iter("testcase")}
    require({"test_exact_bridge_refuses_any_other_change", "test_envelope_refuses_other_timing_failures",
        "test_retained_selector_requires_zero_calls", "test_retained_dispatch_preserves_old_validator"} <= names, "Required retained validation tests missing")
    return {"tests": sum(int(s.get("tests", 0)) for s in suites), "junit_sha256": result["junit_sha256"]}


def validate_submission(root, attempt, task):
    selector(task)
    root, attempt = Path(root).resolve(), Path(attempt).resolve()
    with prior.prior.bounded_stage(210), prior.prior.live.offline(), prior.execution_guard() as guard:
        require(read(attempt / "methods.json") == methods(root), "Retained checker methods changed")
        require({p.name for p in (attempt / "stages").iterdir()} == set(STAGES), "Retained validator stages incomplete")
        rows = [read(attempt / "stages" / s / "result.json") for s in STAGES]
        require(all(r["stage"] == s and r["status"] == "PASS" and r["error"] is None and
                    r["process_guard"] == {"starts": 0, "blocked": 0} and
                    0 <= r["wall_seconds"] < 115 for r, s in zip(rows, STAGES)) and
                sum(r["wall_seconds"] for r in rows) < 400, "Retained validation bound or stage failed")
        require(sum(p.stat().st_size for p in attempt.rglob("*") if p.is_file()) < SELECTOR["evidence_bytes"],
                "Retained validation storage limit")
        result = read(attempt / "result.json")
        require(result["status"] == "PASS" and result["scope"] == "CURRENT_INSTALLED_RETAINED_VALIDATION" and
                result["new_native_calls"] == result["new_subprocess_calls"] == 0 and result["whole_program_complete"] is False, "Unsupported retained result")
        checked_tests(attempt)
        require(read(attempt / "envelope.json") == envelope(root), "Retained installed envelope changed")
        checker = frozen_checker(root)
        actual = checker.evidence(root, root / OLD)
        require(actual == read(root / OLD / "verification.json"), "Independent complete installed evidence differs")
        require(all(value == read(attempt / ("compare-" + value["mode"] + ".json")) for value in actual["cases"]), "Current source comparison differs")
        require(guard.result() == {"starts": 0, "blocked": 0}, "Unexpected retained validation process action")
    return True


def run(name, stage):
    a = Authority(ROOT)
    with a.lock():
        folder = a.path(name); admitted = read(folder / "admission.json")
        program, tasks, _ = a.spec(); task = tasks["native-confinement"]
        selector(task)
        event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
        require(folder.parent == a.base / "attempts/native-confinement" and event["kind"] == "ADMIT" and event["attempt"] == name and
            admitted["program_sha256"] == digest(program) and admitted["task_spec"] == task and admitted["binding"] == a.binding(task), "Current unchanged retained validation admission required")
        require(not (folder / "outputs.json").exists() and not (folder / "result.json").exists(), "Sealed retained validation attempt")
        index = STAGES.index(stage)
        require({p.parent.name for p in (folder / "stages").glob("*/started.json")} ==
            {p.parent.name for p in (folder / "stages").glob("*/result.json")} == set(STAGES[:index]), "Repeated/skipped/interrupted retained stage")
        records = [read(folder / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" for r in records), "Failed retained predecessor")
        spent = sum(r["wall_seconds"] for r in records)
        require(spent < 400, "Retained validation budget exhausted")
        current = methods(ROOT)
        if index:
            require(read(folder / "methods.json") == current, "Retained methods changed")
        else:
            save(folder, "methods.json", current)
            save(folder, "method-snapshots.json.gz", {p: (ROOT / p).read_bytes().hex() for p in current})
        save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
            "command": ["timeout", "120", ".venv/bin/python", SCRIPT, "--attempt", name, "--stage", stage],
            "git_commit": admitted["git_commit"], "python": sys.executable, "cpu_gpu": "CPU only; GPUs intentionally hidden",
            "random_seeds": "N/A deterministic comparison", "inputs": admitted["binding"], "plan": PLAN, "result": name + "/result.json"})
        tick, error, details, guard = time.monotonic(), None, None, None
        try:
            with prior.prior.bounded_stage(min(110, 400 - spent)), prior.prior.live.offline(), prior.execution_guard() as guard:
                if stage == "tests":
                    target = folder / "tests"; target.mkdir()
                    with (target / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
                        import pytest
                        code = int(pytest.main(["-q", "-p", "no:cacheprovider", TEST, "--junitxml=" + str(target / "results.xml")]))
                    save(folder, "tests/result.json", {"status": "PASS" if code == 0 else "FAIL", "exit_code": code,
                        "junit_sha256": file_hash(target / "results.xml") if (target / "results.xml").exists() else None})
                    details = checked_tests(folder)
                elif stage == "retained-envelope":
                    details = envelope(ROOT); save(folder, "envelope.json", details)
                elif stage.startswith("compare-"):
                    details = frozen_checker(ROOT).compare(ROOT, ROOT / OLD, stage.removeprefix("compare-"))
                    save(folder, stage + ".json", details)
                else:
                    require((folder / "RESULT.md").is_file(), "Actual retained result review required")
                    details = {"independent_complete_authority_check": "pending", "new_native_calls": 0}
                require(current == methods(ROOT) and admitted["binding"] == a.binding(task), "Retained input/method changed")
                require(guard.result() == {"starts": 0, "blocked": 0}, "Unexpected retained stage process action")
            require(time.monotonic() - tick < 115 and spent + time.monotonic() - tick < 400, "Retained recorded stage bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save(folder, "stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, final=True)
        value = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error, "details": details,
            "process_guard": guard.result() if guard is not None else None, "wall_seconds": time.monotonic() - tick}
        save(folder, "stages/" + stage + "/result.json", value, final=True)
        if error or stage == "seal":
            save(folder, "result.json", {**value, "task": task["id"], "scope": "CURRENT_INSTALLED_RETAINED_VALIDATION",
                "new_native_calls": 0, "new_subprocess_calls": 0, "whole_program_complete": False}, final=True)
            save(folder, "outputs.json", prior.prior.preparation.prep.files(folder), final=True)
        print(json.dumps({k: value[k] for k in ("stage", "status", "error", "wall_seconds")}))
        return int(error is not None)


def record(name):
    a = Authority(ROOT); tick = time.monotonic()
    a.record(name)
    event = next(e for e in reversed(a.events()) if e.get("attempt") == name)
    value = {"attempt": name, "authority_event": event, "wall_seconds": time.monotonic() - tick,
        "command": ["timeout", "240", ".venv/bin/python", SCRIPT, "--attempt", name, "--stage", "record"]}
    save(ROOT / REVIEW, "actual-record.json", value)
    print(json.dumps({"kind": event["kind"], "seq": event["seq"], "reason": event.get("reason"), "wall_seconds": value["wall_seconds"]}))
    return int(event["kind"] != "ACCEPT")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--stage", choices=(*STAGES, "record"), required=True)
    args = parser.parse_args()
    raise SystemExit(record(args.attempt) if args.stage == "record" else run(args.attempt, args.stage))
