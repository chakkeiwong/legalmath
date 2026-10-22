"""Admitted zero-subprocess acceptance preparation and retained verification."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
import difflib
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
sys.dont_write_bytecode = True
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts import prospectus_current_acceptance as check
from scripts.prospectus_native_campaign import bounded_stage


def admission(authority, name):
    folder = check.preparation.prep.local(authority.root, name)
    prefix = str((authority.base / "attempts").relative_to(authority.root))
    check.require(re.fullmatch(re.escape(prefix) + r"/(native-binding|native-confinement)/attempt-[0-9]{3,}", name), "Current acceptance attempt path required")
    ad = read(folder / "admission.json")
    program, tasks, _ = authority.spec(); task = tasks[ad["task"]]
    events = [e for e in authority.events() if e.get("task") == task["id"]]
    check.require(events and events[-1]["kind"] == "ADMIT" and events[-1]["attempt"] == name
        and events[-1]["admission_sha256"] == file_hash(folder / "admission.json"), "Current unclosed acceptance admission required")
    check.require(ad["attempt"] == name and ad["task_spec"] == task and ad["task_sha256"] == digest(task)
        and ad["program_sha256"] == digest(program) and ad["binding"] == authority.binding(task), "Acceptance admission changed")
    check.require(task.get("native_call_allowance") == 0 and
        ((task.get("acceptance_preparation") is True and not task.get("validator")) or task.get("retained_acceptance_only") is True), "Zero-call acceptance scope required")
    check.require(not (folder / "outputs.json").exists() and not (folder / "result.json").exists(), "Sealed acceptance attempt refused")
    check.preparation.prep.files(folder)
    return folder, ad, task


def tests(authority, name):
    with authority.lock():
        folder, ad, task = admission(authority, name)
        check.require(not (folder / "started.json").exists(), "Tests must precede acceptance freeze")
        runs = sorted((folder / "validation").glob("run-*"))
        check.require(len(runs) < 2 and all((r / "result.json").exists() for r in runs), "Acceptance test bound exhausted/interrupted")
        target = folder / "validation" / f"run-{len(runs)+1:03d}"; target.mkdir(parents=True)
        current = check.methods(authority.root)
        check.helper.save(target / "methods.json", current)
        check.helper.save(target / "method-snapshots.json.gz", {p: (authority.root / p).read_bytes().hex() for p in current})
        start = check.preparation.start(ad, task, name, "tests"); start["command"][3] = check.RUNNER
        check.helper.save(target / "started.json", start)
        tick, code, error = time.monotonic(), 1, None
        try:
            with bounded_stage(), check.live.offline(), (target / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
                import pytest
                code = int(pytest.main(["-q", "-p", "no:cacheprovider", check.TEST,
                    "tests/prospectus/test_execution_acceptance.py", "tests/prospectus/test_execution_authority.py", "--junitxml=" + str(target / "tests.xml")]))
                check.require(check.methods(authority.root) == current, "Acceptance test methods changed")
        except BaseException as exc:
            code, error = 1, str(exc); (target / "error.log").write_text(traceback.format_exc())
        value = {"status": "PASS" if code == 0 else "FAIL", "exit_code": code, "error": error,
            "wall_seconds": time.monotonic()-tick, "tests_sha256": file_hash(target / "tests.xml") if (target / "tests.xml").exists() else None}
        check.helper.save(target / "result.json", value)
        return code, value


def seal(folder, task, result):
    check.helper.save(folder / "result.json", {**result, "task": task["id"], "scope": "FINITE_ENGINEERING_ONLY",
        "whole_program_complete": False, "acceptance_preparation": bool(task.get("acceptance_preparation")), "new_native_calls": 0})
    (folder / "RESULT.md").write_text("# Current retained evidence validation\n\nActual result: " + result["status"] +
        ". Full inputs, current method snapshots, command and actual comparison results are retained. No native or supervised subprocess call was launched.\n\n"
        "| Decision | Primary criterion | Veto | Main uncertainty | Next action | Limit |\n|---|---|---|---|---|---|\n"
        f"| Submit actual result | {result['status']} | See validation evidence | Same-host shared interpretation | Record through named authority and refresh | No independent legal/financial truth, portability or whole-program completion |\n\n"
        "Post-run review: exact source and own-parent consumers constrain integration errors; shared substantive interpretation errors remain outside this finite acceptance.\n")
    check.helper.save(folder / "outputs.json", check.preparation.prep.files(folder))


def run(authority, name, stage):
    check.require(stage in ("prepare", "check-installed", "check-native", "finalize"), "Unknown acceptance stage")
    with authority.lock():
        folder, ad, task = admission(authority, name)
        target = folder / "stages" / stage
        check.require(not target.exists(), "Acceptance stage already started")
        if stage != "prepare":
            check.require(read(folder / "stages/prepare/result.json")["status"] == "PASS" and read(folder / "methods.json") == check.methods(authority.root), "Acceptance methods or predecessor changed")
        target.mkdir(parents=True)
        start = check.preparation.start(ad, task, name, stage); start["command"][3] = check.RUNNER
        if stage == "prepare": check.helper.save(folder / "started.json", start)
        check.helper.save(target / "started.json", start)
        tick, error, details = time.monotonic(), None, None
        try:
            with bounded_stage(), check.live.offline():
                tested = check.checked_current_tests(authority.root, folder)
                if stage == "prepare":
                    current = check.methods(authority.root)
                    check.helper.save(folder / "methods.json", current)
                    check.helper.save(folder / "method-snapshots.json.gz", {p: (authority.root / p).read_bytes().hex() for p in current})
                    if task.get("acceptance_preparation"):
                        before = (authority.root / check.REGISTRY).read_text(); after = check.registry_candidate(before)
                        (folder / "registry-before.py").write_text(before)
                        (folder / "registry-candidate.py").write_text(after)
                        (folder / "registration.patch").write_text("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile="a/" + check.REGISTRY, tofile="b/" + check.REGISTRY)))
                        check.helper.save(folder / "registration-review.json", {"baseline_sha256": file_hash(folder / "registry-before.py"),
                            "candidate_sha256": file_hash(folder / "registry-candidate.py"), "scope": "Two additive named mappings and dispatch branch; original validator paths unchanged"})
                    details = {"tests": tested, "native_calls": 0}
                elif stage.startswith("check-"):
                    is_native = stage == "check-native"
                    check.require((is_native and task["id"] == "native-binding") or (not is_native and task["id"] == "native-confinement"), "Wrong acceptance evidence task")
                    result = check.native_evidence(authority.root) if is_native else check.installed_evidence(authority.root)
                    check.helper.save(folder / "verification.json", {**result, "current_tests": tested})
                    details = {"version": result["version"], "new_native_calls": 0}
                else:
                    previous = "check-native" if task["id"] == "native-binding" else "check-installed"
                    check.require(read(folder / "stages" / previous / "result.json")["status"] == "PASS", "Actual retained validation required")
                    details = {"verification_sha256": file_hash(folder / "verification.json"), "native_calls": 0}
                admission(authority, name)
                check.require(read(folder / "methods.json") == check.methods(authority.root), "Acceptance method change during stage")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            (target / "error.log").write_text(traceback.format_exc())
        code = 0 if not error else 1
        value = {"status": "PASS" if not error else "FAIL", "stage": stage, "error": error, "exit_code": code,
            "wall_seconds": time.monotonic()-tick, "details": details}
        check.helper.save(target / "result.json", value)
        if error or stage == "finalize": seal(folder, task, value)
        return code, {k: value[k] for k in ("status", "stage", "error", "wall_seconds")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True); parser.add_argument("--stage", required=True)
    args = parser.parse_args(); authority = Authority(ROOT)
    code, value = tests(authority, args.attempt) if args.stage == "tests" else run(authority, args.attempt, args.stage)
    print(json.dumps(value)); return code


if __name__ == "__main__": raise SystemExit(main())
