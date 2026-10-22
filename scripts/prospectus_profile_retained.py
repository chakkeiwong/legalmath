"""Validate complete installed012 evidence without repeating native execution."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
import types

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts import prospectus_profile_installed as prior

BASE = prior.BASE
OLD = BASE + "/attempts/native-confinement/attempt-012"
REVIEW = BASE + "/reviews/installed-summary-197"
SCRIPT = "scripts/prospectus_profile_retained.py"
TEST = "tests/prospectus/test_profile_retained.py"
PLAN = "docs/plans/prospectus-installed-summary-repair-2026-10-17.md"
STAGES = ("tests", "envelope", "evidence", "seal")
SELECTOR = {"version": "installed-current-retained.v1", "source_attempt": OLD,
    "stages": list(STAGES), "work_seconds": 110, "stage_seconds": 115,
    "evidence_work_seconds": 210, "evidence_stage_seconds": 215,
    "execution_seconds": 600, "validation_seconds": 210,
    "new_native_calls": 0, "new_subprocess_calls": 0, "evidence_bytes": 32 * 1024**2, "unchanged_retries": 0}
require = prior.require


def dispatch_candidate(before):
    marker = "def validate_submission(root, attempt, task):\n"
    require(before.count(marker) == 1, "Unexpected installed dispatch baseline")
    return before.replace(marker, marker +
        '    if "retained_current_profile" in task:\n'
        '        from scripts.prospectus_profile_retained import validate_submission as validate_retained\n'
        '        return validate_retained(root, attempt, task)\n')


def exact_bridge(frozen, snapshots, current):
    require(set(frozen) == set(snapshots) == set(current), "Installed method inventory differs")
    require(all(hashlib.sha256(bytes.fromhex(snapshots[p])).hexdigest() == h for p, h in frozen.items()),
        "Forged installed method snapshot")
    require(all(current[p] == h for p, h in frozen.items() if p != prior.SCRIPT), "Unreviewed installed method change")
    candidate = dispatch_candidate(bytes.fromhex(snapshots[prior.SCRIPT]).decode()).encode()
    require(current[prior.SCRIPT] == hashlib.sha256(candidate).hexdigest(), "Unreviewed installed dispatch bytes")
    return frozen


def frozen_checker(root):
    frozen = read(root / OLD / "methods.json")
    snapshots = prior.helper.read(root / OLD / "method-snapshots.json.gz")
    exact_bridge(frozen, snapshots, prior.methods(root))
    module = types.ModuleType("frozen_installed_012")
    module.__file__ = str(root / prior.SCRIPT)
    exec(compile(bytes.fromhex(snapshots[prior.SCRIPT]).decode(), module.__file__, "exec"), module.__dict__)
    module.methods = lambda selected: exact_bridge(frozen, snapshots, prior.methods(Path(selected)))
    return module


def methods(root):
    return {**prior.methods(root), SCRIPT: file_hash(root / SCRIPT), TEST: file_hash(root / TEST)}


def selector(task):
    require(task.get("id") == "native-confinement" and task.get("validator") == prior.prior.INSTALLED and
        task.get("annual_profile_compatibility") == prior.SELECTOR and task.get("retained_current_profile") == SELECTOR and
        task.get("native_call_allowance") == 0 and task.get("retained_acceptance_only") is True,
        "Unreviewed zero-call current retained selector")


def stage_envelope(rows):
    require([r["stage"] for r in rows] == list(prior.STAGES[:-1]), "Retained installed stages differ")
    require(all(r["status"] == "PASS" and r["error"] is None and 0 <= r["wall_seconds"] < 115
        for r in rows[:-1]), "Retained execution predecessor failed")
    last = rows[-1]
    require(last["stage"] == "validate" and last["status"] == "FAIL" and
        last["error"] == {"type": "TimeoutError", "message": "Current native preparation stage exceeded its time bound"} and
        last["wall_seconds"] == 111.0746665536426, "Unexpected retained summary failure")
    require(sum(r["wall_seconds"] for r in rows) < 1200, "Retained aggregate bound exceeded")


def envelope(root):
    a = Authority(root); event = read(root / REVIEW / "history.json")["rejected_event"]
    require(event in a.events() and event["seq"] == 1387 and event["kind"] == "REJECT" and
        event["attempt"] == OLD and a.retained_evidence_valid(event), "Retained rejection missing or changed")
    old = root / OLD
    require({p.name for p in (old / "stages").iterdir()} == set(prior.STAGES[:-1]) and
        not (old / "verification.json").exists(), "Unexpected retained stage or verification")
    rows = [read(old / "stages" / s / "result.json") for s in prior.STAGES[:-1]]
    stage_envelope(rows)
    result = read(old / "result.json")
    require(result["status"] == "FAIL" and result["stage"] == "validate", "Historical failure relabeled")
    checker = frozen_checker(root)
    env, profile, manifest = checker.profile_context(root, old)
    return {"rejected_event": event["seq"], "failed_summary_preserved": True,
        "old_stage_seconds": sum(r["wall_seconds"] for r in rows),
        "profile_sha256": checker.product.digest(profile), "profile_files": len(manifest["files"]),
        "environment": str(env), "new_native_calls": 0, "new_subprocess_calls": 0}


def storage(folder):
    parents = [folder, ROOT / REVIEW, ROOT / SCRIPT, ROOT / TEST, ROOT / PLAN,
        ROOT / BASE / "proposals/installed-summary-197.json", ROOT / BASE / "proposals/installed-summary-197-review.json",
        ROOT / BASE / "closure-routes-2026-10-17-installed-summary-197.json", ROOT / BASE / "revisions/0197.json"]
    unique = {}
    for parent in parents:
        for p in (parent.rglob("*") if parent.is_dir() else [parent]):
            require(not p.is_symlink(), "Retained validation symlink refused")
            if p.is_file():
                st = p.stat(); unique[st.st_dev, st.st_ino] = st.st_size
    return sum(unique.values())


def save(folder, name, value, *, final=False):
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
    if name.endswith(".gz"): data = gzip.compress(data, mtime=0)
    require(storage(folder) + len(data) < (32 if final else 30) * 1024**2, "Retained evidence storage bound")
    path = folder / name; path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream: stream.write(data)


def checked_tests(folder):
    tree = prior.ET.parse(folder / "tests.xml").getroot(); suites = list(tree.iter("testsuite"))
    require(suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ("errors", "failures", "skipped")), "Retained checks failed/skipped")
    names = {r.get("name") for r in tree.iter("testcase")}
    require({"test_current_retained_exact_bridge", "test_current_retained_exact_timeout_envelope",
        "test_current_retained_selector_zero_calls", "test_current_retained_dispatch_preserves_fallback"} <= names, "Retained adverse checks missing")
    return sum(int(s.get("tests", 0)) for s in suites)


def validate_submission(root, attempt, task):
    selector(task); root, attempt = Path(root).resolve(), Path(attempt).resolve()
    with prior.prior.bounded_stage(210), prior.prior.live.offline(), prior.execution_guard() as guard:
        require(read(attempt / "methods.json") == methods(root), "Retained checker methods changed")
        require({p.name for p in (attempt / "stages").iterdir()} == set(STAGES), "Retained stage incomplete")
        rows = [read(attempt / "stages" / s / "result.json") for s in STAGES]
        require(all(r["stage"] == s and r["status"] == "PASS" and r["error"] is None and
            r["process_guard"] == {"starts": 0, "blocked": 0} and
            0 <= r["wall_seconds"] < (215 if s == "evidence" else 115) for s, r in zip(STAGES, rows)) and
            sum(r["wall_seconds"] for r in rows) < 600, "Retained stage or budget failed")
        result = read(attempt / "result.json")
        require(result["status"] == "PASS" and result["scope"] == "CURRENT_INSTALLED_RETAINED_VALIDATION" and
            result["new_native_calls"] == result["new_subprocess_calls"] == 0 and result["whole_program_complete"] is False, "Unsupported retained result")
        checked_tests(attempt)
        require(read(attempt / "envelope.json") == envelope(root), "Retained envelope changed")
        actual = frozen_checker(root).evidence(root, root / OLD)
        require(actual == read(attempt / "verification.json"), "Complete retained installed evidence differs")
        require(guard.result() == {"starts": 0, "blocked": 0} and storage(attempt) < SELECTOR["evidence_bytes"], "Retained process/storage bound")
    return True


def run(name, stage):
    a = Authority(ROOT)
    with a.lock():
        folder = a.path(name); admitted = read(folder / "admission.json")
        program, tasks, _ = a.spec(); task = tasks["native-confinement"]; selector(task)
        event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
        require(folder.parent == a.base / "attempts/native-confinement" and event["kind"] == "ADMIT" and event["attempt"] == name and
            admitted["program_sha256"] == digest(program) and admitted["task_spec"] == task and admitted["binding"] == a.binding(task), "Current unchanged retained admission required")
        require(not (folder / "outputs.json").exists() and not (folder / "result.json").exists(), "Sealed retained attempt")
        index = STAGES.index(stage)
        require({p.parent.name for p in (folder / "stages").glob("*/started.json")} ==
            {p.parent.name for p in (folder / "stages").glob("*/result.json")} == set(STAGES[:index]), "Repeated/skipped/interrupted stage")
        rows = [read(folder / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" for r in rows), "Failed predecessor")
        spent = sum(r["wall_seconds"] for r in rows); require(spent < 600, "Retained aggregate bound")
        current = methods(ROOT)
        if index: require(current == read(folder / "methods.json"), "Retained methods changed")
        else:
            save(folder, "methods.json", current)
            save(folder, "method-snapshots.json.gz", {p: (ROOT / p).read_bytes().hex() for p in current})
        outer = 240 if stage == "evidence" else 120
        save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
            "command": ["timeout", str(outer), ".venv/bin/python", "-m", SCRIPT.removesuffix(".py").replace("/", "."), "--attempt", name, "--stage", stage],
            "git_commit": admitted["git_commit"], "python": sys.executable, "cpu_gpu": "CPU only; GPUs intentionally hidden",
            "random_seeds": "N/A deterministic retained validation", "input_binding_sha256": digest(admitted["binding"]),
            "input_binding_file": name + "/admission.json", "plan": PLAN, "result": name + "/result.json"})
        tick, error, details, guard = time.monotonic(), None, None, None
        try:
            with prior.prior.bounded_stage(min(210 if stage == "evidence" else 110, 600 - spent)), prior.prior.live.offline(), prior.execution_guard() as guard:
                if stage == "tests":
                    with (folder / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
                        import pytest
                        code = int(pytest.main(["-q", "-p", "no:cacheprovider", TEST, prior.TEST, "--junitxml=" + str(folder / "tests.xml")]))
                    require(code == 0, "Retained focused tests failed"); details = {"tests": checked_tests(folder)}
                elif stage == "envelope":
                    details = envelope(ROOT); save(folder, "envelope.json", details)
                elif stage == "evidence":
                    details = frozen_checker(ROOT).evidence(ROOT, ROOT / OLD); save(folder, "verification.json", details)
                else:
                    require((folder / "RESULT.md").is_file(), "Actual retained result review required")
                    details = {"independent_record_pending": True, "new_native_calls": 0}
                require(current == methods(ROOT) and admitted["binding"] == a.binding(task), "Retained method/input changed")
                require(guard.result() == {"starts": 0, "blocked": 0}, "Unexpected retained process")
            require(time.monotonic() - tick < (215 if stage == "evidence" else 115) and spent + time.monotonic() - tick < 600, "Retained timing bound")
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
    a = Authority(ROOT); tick = time.monotonic(); a.record(name)
    event = next(e for e in reversed(a.events()) if e.get("attempt") == name)
    value = {"attempt": name, "authority_event": event, "wall_seconds": time.monotonic() - tick,
        "command": ["timeout", "240", ".venv/bin/python", "-m", SCRIPT.removesuffix(".py").replace("/", "."), "--attempt", name, "--stage", "record"]}
    save(ROOT / REVIEW, "actual-record.json", value)
    print(json.dumps({"kind": event["kind"], "reason": event.get("reason"), "seq": event["seq"], "wall_seconds": value["wall_seconds"]}))
    return int(event["kind"] != "ACCEPT")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--attempt", required=True); p.add_argument("--stage", choices=(*STAGES, "record"), required=True)
    args = p.parse_args()
    raise SystemExit(record(args.attempt) if args.stage == "record" else run(args.attempt, args.stage))
