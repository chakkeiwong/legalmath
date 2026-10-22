"""Admitted current installation preparation; immutable history and zero native calls."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
sys.dont_write_bytecode = True
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
from legalmath.prospectus.execution_authority import Authority, CODE, digest, file_hash, read, write
from legalmath.prospectus import native_profile, native_current_preparation as prep
from legalmath.prospectus.successor import process_ledger
from scripts.prospectus_native_campaign import bounded_stage, no_subprocess
from scripts import prospectus_installed_consumer as helper

VERSION = "installed-current-preparation.v1"
SCRIPT = "scripts/prospectus_installed_current.py"
HELPER = "scripts/prospectus_installed_consumer.py"
TEST = "tests/prospectus/test_installed_current.py"
ROUTES = tuple(prep.ROUTES)
COMMANDS = ("build", "install", "capture", "check", *("replay-" + r for r in ROUTES), "controls")
STAGES = ("prepare", "build", "install", "inventory", *COMMANDS[2:], "finalize")
GRANT = {"version": VERSION, "maximum_outer_commands": 10, "maximum_test_starts": 2,
    "historical_installed_outer_starts": 18, "historical_installed_native_starts": 4,
    "native_call_allowance": 0, "stage_timeout_seconds": 120, "evidence_bytes": 536870912,
    "workspace_bytes": 2147483648, "network": False, "gpu": False, "local_wheel_only": True}
require = prep.require


def admission(authority, name):
    folder = prep.local(authority.root, name)
    prefix = str((authority.base / "attempts/native-confinement").relative_to(authority.root))
    require(re.fullmatch(re.escape(prefix) + r"/attempt-[0-9]{3,}", name), "Current installed attempt path required")
    admitted = read(folder / "admission.json")
    program, tasks, _ = authority.spec()
    task = tasks["native-confinement"]
    events = [e for e in authority.events() if e.get("task") == task["id"]]
    require(events and events[-1]["kind"] == "ADMIT" and events[-1]["attempt"] == name
        and events[-1]["admission_sha256"] == file_hash(folder / "admission.json"), "Current unclosed admission required")
    require(admitted["attempt"] == name and admitted["task"] == task["id"]
        and admitted["task_sha256"] == digest(task) and admitted["task_spec"] == task
        and admitted["program_sha256"] == digest(program) and admitted["binding"] == authority.binding(task),
        "Installed admission changed")
    require(task.get("installed_preparation") == GRANT and task.get("preparation_only") is True
        and task.get("native_call_allowance") == 0 and not task.get("validator")
        and bool(task.get("completion_validation_pending")), "Explicit installed preparation grant required")
    require(not (folder / "outputs.json").exists() and not (folder / "result.json").exists(), "Sealed installed attempt refused")
    prep.files(folder)
    return folder, admitted, task


def methods(root):
    names = {str(p.relative_to(root)) for p in (root / "src/legalmath").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    names.update((*CODE, SCRIPT, HELPER, TEST, "pyproject.toml", "tests/prospectus/test_native_profile.py",
        "scripts/prospectus_native_campaign.py", "scripts/prospectus_verify_task.py"))
    return {n: file_hash(prep.local(root, n)) for n in sorted(names)}


def checked_methods(root, folder):
    current = methods(root)
    require(current == read(folder / "methods.json"), "Current installed methods changed after freeze")
    snapshot = helper.read(folder / "method-snapshots.json.gz")
    from hashlib import sha256
    require(set(snapshot) == set(current) and all(sha256(bytes.fromhex(snapshot[p])).hexdigest() == h for p, h in current.items()),
            "Current installed method snapshot differs")
    return current


def tree(folder, *, dependencies=False):
    result = {}
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder)
        if "__pycache__" in rel.parts or p.suffix == ".pyc": continue
        if dependencies and (str(rel) == "bin/legalmath" or "legalmath" in rel.parts or any(n.startswith("legalmath-") and n.endswith(".dist-info") for n in rel.parts)):
            continue
        if p.is_symlink(): result[str(rel)] = {"symlink": os.readlink(p)}
        elif p.is_file(): result[str(rel)] = file_hash(p)
    return result


def workspace(root, folder):
    path = Path(read(folder / "workspace.json")["directory"])
    require(path.is_relative_to(root / ".localresources/prospectus") and path.name.startswith("installed-current-"),
            "Owned installation workspace required")
    require(path.resolve() == path and not path.is_symlink(), "Symlink workspace refused")
    return path


def bounded_storage(folder, work=None):
    def size(base):
        rows = {}
        for p in base.rglob("*"):
            if p.is_file() and not p.is_symlink():
                s = p.stat(); rows[(s.st_dev, s.st_ino)] = s.st_size
        return sum(rows.values())
    value = {"evidence_unique_bytes": size(folder)}
    require(value["evidence_unique_bytes"] < GRANT["evidence_bytes"], "Installed evidence storage cap exceeded")
    if work:
        value["workspace_unique_bytes"] = size(work)
        require(value["workspace_unique_bytes"] < GRANT["workspace_bytes"], "Installed workspace storage cap exceeded")
    return value


def test_evidence(root, folder):
    rows = sorted((folder / "validation").glob("run-*/result.json"))
    require(1 <= len(rows) <= 2, "Installed test starts differ")
    result = read(rows[-1]); target = rows[-1].parent
    require(result["status"] == "PASS" and result["exit_code"] == 0 and result["wall_seconds"] <= 120
        and read(target / "methods.json") == methods(root) and file_hash(target / "tests.xml") == result["tests_sha256"],
        "Current installed tests failed or changed")
    suites = list(ET.parse(target / "tests.xml").getroot().iter("testsuite"))
    require(suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ("errors", "failures", "skipped")), "Installed tests failed or skipped")
    return {"tests": sum(int(s.get("tests", 0)) for s in suites), "starts": len(rows), "sha256": result["tests_sha256"]}


def start(admitted, task, name, stage):
    return {"started_at": datetime.now(timezone.utc).isoformat(), "stage": stage,
        "command": ["timeout", "120", ".venv/bin/python", SCRIPT, "--attempt", name, "--stage", stage],
        "git_commit": admitted["git_commit"], "plan": task["dossier"], "environment": sys.executable,
        "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic",
        "data_version": "Accepted native-binding017 full products and protected006 explicit files",
        "result_file": name + "/stages/" + stage + "/result.json"}


def tests(authority, name):
    with authority.lock():
        folder, ad, task = admission(authority, name)
        require(not (folder / "started.json").exists(), "Tests must precede freeze and installation")
        runs = sorted((folder / "validation").glob("run-*"))
        require(len(runs) < 2 and all((r / "result.json").exists() for r in runs), "Test allowance exhausted/interrupted")
        target = folder / "validation" / f"run-{len(runs)+1:03d}"
        target.mkdir(parents=True)
        current = methods(authority.root)
        write(target / "methods.json", current, exclusive=True)
        helper.save(target / "method-snapshots.json.gz", {p: (authority.root / p).read_bytes().hex() for p in current})
        write(target / "started.json", start(ad, task, name, "tests"), exclusive=True)
        tick, code, error, counter = time.monotonic(), 1, None, {"attempts": 0}
        try:
            with bounded_stage(), no_subprocess(counter), (target / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
                import pytest
                code = int(pytest.main(["-q", "-p", "no:cacheprovider", TEST, "tests/prospectus/test_native_profile.py", "--junitxml=" + str(target / "tests.xml")]))
                require(current == methods(authority.root), "Test methods changed during suite")
        except BaseException as exc:
            code = 124 if isinstance(exc, TimeoutError) else 1
            error = str(exc)
            (target / "error.log").write_text(traceback.format_exc())
        result = {"status": "PASS" if code == 0 else "FAIL", "exit_code": code, "error": error,
            "wall_seconds": time.monotonic()-tick, "subprocess_attempts": counter["attempts"],
            "tests_sha256": file_hash(target / "tests.xml") if (target / "tests.xml").exists() else None}
        write(target / "result.json", result, exclusive=True)
        return code, result


def prepare(authority, folder):
    root = authority.root
    tested = test_evidence(root, folder)
    current = methods(root)
    helper.save(folder / "methods.json", current)
    helper.save(folder / "method-snapshots.json.gz", {p: (root / p).read_bytes().hex() for p in current})
    event = next(e for e in reversed(authority.events()) if e.get("task") == "native-binding")
    require(event["kind"] == "ACCEPT" and event["seq"] == 981 and authority.retained_evidence_valid(event), "Accepted current native baseline required")
    helper.save(folder / "baseline.json", {"attempt": event["attempt"], "event": event["seq"], "outputs_sha256": event["outputs_sha256"]})
    old = authority.base / "attempts/native-confinement/attempt-002"
    prep.historical.verify_files(old, read(old / "outputs.json"))
    old_env = Path(read(old / "workspace.json")["directory"]) / "environment"
    prep.historical.verify_files(old_env / "lib/python3.11/site-packages/legalmath", read(old / "installed-methods.json"))
    dependencies = tree(old_env, dependencies=True)
    work = Path(tempfile.mkdtemp(prefix="installed-current-", dir=root / ".localresources/prospectus"))
    helper.save(folder / "workspace.json", {"directory": str(work), "environment_cloned_from": str(old_env)})
    shutil.copytree(old_env, work / "environment", symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    require(tree(work / "environment", dependencies=True) == dependencies, "Cloned dependency bytes differ")
    helper.save(folder / "dependencies.json", dependencies)
    source = work / "source"
    source.mkdir()
    shutil.copyfile(root / "pyproject.toml", source / "pyproject.toml")
    shutil.copytree(root / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"))
    source_map = helper.package_files(root / "src/legalmath")
    require(helper.package_files(source / "src/legalmath") == source_map, "Copied source differs")
    helper.save(folder / "source-package.json", source_map)
    shutil.copyfile(root / HELPER, work / "installed_consumer.py")
    process_ledger.create(folder / "outer-ledger.json", 10, 18, "Ten current outer commands; historical installed18 retained; pip internal forks excluded")
    helper.save(folder / "native-ledger.json", {"version": VERSION, "allowance": 0, "reservations": [], "historical_installed_starts": 4})
    return {"tests": tested, "package_files": len(source_map), "dependencies": len(dependencies), "workspace": str(work)}


def command(folder, work, stage, argv):
    target = folder / "commands" / stage
    target.mkdir(parents=True, exist_ok=False)
    env = {"CUDA_VISIBLE_DEVICES": "-1", "PYTHONPATH": "", "PYTHONNOUSERSITE": "1",
        "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_CACHE_DIR": "1"}
    helper.save(target / "command.json", {"argv": argv, "cwd": str(work), "environment": env, "timeout": 110})
    tick, code, error = time.monotonic(), None, None
    try:
        with process_ledger.observe(folder / "outer-ledger.json"), (target / "stdout").open("xb") as out, (target / "stderr").open("xb") as err:
            completed = subprocess.run(argv, cwd=work, env={**os.environ, **env}, stdout=out, stderr=err, timeout=110)
            code = completed.returncode
    except BaseException as exc:
        error = type(exc).__name__ + ": " + str(exc)
        raise
    finally:
        helper.save(target / "result.json", {"returncode": code, "error": error, "wall_seconds": time.monotonic()-tick})
    require(code == 0, "Installed command failed: " + stage + "; see retained stderr")


def inventory(root, folder, work):
    package = work / "environment/lib/python3.11/site-packages/legalmath"
    expected = read(folder / "source-package.json")
    require(helper.package_files(package) == expected, "Installed package differs from frozen source")
    require(tree(work / "environment", dependencies=True) == read(folder / "dependencies.json"), "Installed dependency bytes changed")
    prior = root / prep.BASE / "attempts/native-binding/attempt-006"
    original = prep.historical.snapshot(prior / "snapshot")
    rows = deepcopy(original["files"])
    for name in ("ocr_worker.py", "native_inputs.py"):
        path = package / "prospectus/successor" / name
        rows.append({"path": str(path), "sha256": file_hash(path), "size": path.stat().st_size, "mode": 0o444})
    private = work / "capture-inputs"
    private.mkdir()
    sources = {}
    for row in rows:
        target = private / (row["sha256"] + "." + str(row["mode"]))
        if not target.exists():
            old = prior / "snapshot/blobs" / row["sha256"]
            shutil.copyfile(old if old.exists() else Path(row["path"]), target)
            target.chmod(row["mode"])
        require(file_hash(target) == row["sha256"], "Capture input differs")
        sources[row["path"]] = str(target)
    directories = set(original["directories"])
    for row in rows: directories.update(str(p) for p in Path(row["path"]).parents if str(p) != "/")
    helper.save(folder / "capture-spec.json", {"repository": str(root), "sources": sources, "directories": sorted(directories),
        "ocr_python": "/home/chakwong/miniconda3/envs/tfgpu/bin/python", "native_text_max_stream": 64 * 1024 * 1024})
    helper.save(folder / "expected-snapshot.json", {**original, "files": sorted(rows, key=lambda r: r["path"]), "directories": sorted(directories)})
    for mode in ("fresh", "retained"):
        baseline = root / read(folder / "baseline.json")["attempt"] / "routes" / ("2010-" + mode)
        helper.save(folder / (mode + "-request.json"), helper.read(baseline / "P1.json.gz")["payload"]["request"])
    helper.save(folder / "installed-methods.json", {n: h for n, h in expected.items() if n in native_profile.methods()})
    return {"package_files": len(expected), "profile_files": len(rows)}


def validate(root, folder):
    current = checked_methods(root, folder)
    work = workspace(root, folder)
    require(helper.package_files(work / "environment/lib/python3.11/site-packages/legalmath") == read(folder / "source-package.json"), "Final installed package changed")
    require(tree(work / "environment", dependencies=True) == read(folder / "dependencies.json"), "Final dependencies changed")
    require(read(folder / "native-ledger.json") == {"version": VERSION, "allowance": 0, "reservations": [], "historical_installed_starts": 4}, "Preparation native accounting changed")
    outer = process_ledger.checked(folder / "outer-ledger.json")
    require(outer["limit"] == 10 and outer["historical_lower_bound"] == 18 and len(outer["reservations"]) == 10
        and all(r["state"] == "STARTED" for r in outer["reservations"]), "Installed outer accounting incomplete")
    for stage, reservation in zip(COMMANDS, outer["reservations"]):
        command_row = read(folder / "commands" / stage / "command.json")
        require(command_row["argv"] == reservation["argv"] and read(folder / "commands" / stage / "result.json")["returncode"] == 0, "Installed command evidence differs")
        if stage not in ("build", "install"):
            proof = read(folder / "commands" / stage / "installed-proof.json")
            require(proof["isolated"] == 1 and proof["prefix"] == str(work / "environment") and proof["modules"], "Installed import evidence missing")
            package = work / "environment/lib/python3.11/site-packages/legalmath"
            for row in proof["modules"].values():
                p = Path(row["path"])
                require(p.is_relative_to(package) and row["sha256"] == file_hash(p), "Installed module location or bytes differ")
            result = read(folder / "commands" / stage / "installed-result.json")
            require(result["status"] == "PASS" and result["native_processes"] == 0 and result["blocked_native_attempts"] == (1 if stage == "controls" else 0), "Installed result or native refusal differs")
    require(read(folder / "profile/snapshot/manifest.json") == read(folder / "expected-snapshot.json"), "Actual profile files differ")
    comparisons = []
    for route in ROUTES:
        baseline = root / read(folder / "baseline.json")["attempt"] / "routes" / route
        actual = helper.read(folder / "replays" / route / "actual.json.gz")
        expected = {n: helper.read(baseline / (n + ".json.gz")) for n in ("P1", "P2", "P3", "P4", "P5", "answer")}
        helper.compare_objects(actual, expected)
        comparisons.append(read(folder / "replays" / route / "comparison.json"))
    return {"version": VERSION, "methods_sha256": digest(current), "tests": test_evidence(root, folder),
        "routes": comparisons, "outer_starts": 10, "historical_installed_outer_starts": 18, "native_starts": 0,
        "storage": bounded_storage(folder, work), "fresh_native_execution_established": False,
        "task_acceptance_established": False, "whole_program_complete": False}


def seal(folder, task, result):
    helper.save(folder / "result.json", {**result, "task": task["id"], "scope": "INSTALLED_PREPARATION_ONLY",
        "whole_program_complete": False, "task_acceptance_established": False})
    (folder / "RESULT.md").write_text("# Current installed preparation\n\n"
        + ("Current isolated wheel, profile checks and all five complete installed consumer comparisons pass." if result["status"] == "PASS" else "The actual preparation failure and partial files are retained; see the failing stage.")
        + "\n\nNo fresh native extraction or independent legal acceptance is established. Historical installations and current native017 are preserved.\n\n"
        "| Decision | Primary criterion | Veto | Main uncertainty | Next action | Limit |\n|---|---|---|---|---|---|\n"
        f"| Retain actual preparation | {result['status']} | See stage evidence | Fresh installed source routes remain unevaluated | Record, refresh, review explicit live continuation | Finite same-host engineering only |\n\n"
        "Post-run review: shared consumer/comparator errors remain possible. A full-object mismatch, changed package/import or unexpected process would invalidate this candidate.\n")
    helper.save(folder / "outputs.json", prep.files(folder))


def run_stage(authority, name, stage):
    require(stage in STAGES, "Native or unknown installation stage refused")
    with authority.lock():
        folder, ad, task = admission(authority, name)
        target = folder / "stages" / stage
        require(not target.exists(), "Installed stage already started")
        for previous in STAGES[:STAGES.index(stage)]:
            marker = folder / "stages" / previous / "result.json"
            require(marker.exists() and read(marker)["status"] == "PASS", "Prior installed stage required: " + previous)
        if stage != "prepare": checked_methods(authority.root, folder)
        target.mkdir(parents=True)
        value = start(ad, task, name, stage)
        if stage == "prepare": helper.save(folder / "started.json", value)
        helper.save(target / "started.json", value)
        tick, error, details = time.monotonic(), None, None
        try:
            with bounded_stage():
                if stage == "prepare":
                    counter = {"attempts": 0}
                    with no_subprocess(counter): details = prepare(authority, folder)
                    require(counter["attempts"] == 0, "Unexpected preparation subprocess attempt")
                else:
                    work = workspace(authority.root, folder)
                    python = str(work / "environment/bin/python")
                    if stage in ("inventory", "finalize"):
                        counter = {"attempts": 0}
                        with no_subprocess(counter):
                            details = inventory(authority.root, folder, work) if stage == "inventory" else validate(authority.root, folder)
                        require(counter["attempts"] == 0, "Unexpected offline subprocess attempt")
                        if stage == "finalize": helper.save(folder / "verification.json", details)
                    else:
                        if stage == "build":
                            argv = [python, "-I", "-B", "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--no-index", "--wheel-dir", str(folder / "wheel"), str(work / "source")]
                        elif stage == "install":
                            wheel = read(folder / "built-wheel.json")
                            require(file_hash(folder / wheel["file"]) == wheel["sha256"], "Built wheel changed")
                            argv = [python, "-I", "-B", "-m", "pip", "install", "--no-index", "--no-deps", "--force-reinstall", str(folder / wheel["file"])]
                        else: argv = [python, "-I", "-B", str(work / "installed_consumer.py"), str(folder), str(authority.root), stage]
                        command(folder, work, stage, argv)
                        if stage == "build":
                            wheels = list((folder / "wheel").glob("*.whl"))
                            require(len(wheels) == 1, "Expected one current local wheel")
                            expected = read(folder / "source-package.json")
                            with zipfile.ZipFile(wheels[0]) as archive:
                                from hashlib import sha256
                                require({n.removeprefix("legalmath/"): sha256(archive.read(n)).hexdigest() for n in archive.namelist() if n.startswith("legalmath/") and not n.endswith("/")} == expected, "Wheel package content differs")
                            helper.save(folder / "built-wheel.json", {"file": str(wheels[0].relative_to(folder)), "sha256": file_hash(wheels[0])})
                        details = {"command": stage, "returncode": 0}
                checked_methods(authority.root, folder)
                admission(authority, name)
                bounded_storage(folder, workspace(authority.root, folder))
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            (target / "error.log").write_text(traceback.format_exc())
        code = 0 if error is None else 124 if error["type"] == "TimeoutError" else 1
        result = {"status": "PASS" if not error else "FAIL", "stage": stage, "error": error,
            "wall_seconds": time.monotonic()-tick, "exit_code": code, "details": details}
        helper.save(target / "result.json", result)
        if error or stage == "finalize": seal(folder, task, result)
        return code, {k: result[k] for k in ("status", "stage", "error", "wall_seconds")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--stage", required=True)
    args = parser.parse_args()
    a = Authority(ROOT)
    code, result = tests(a, args.attempt) if args.stage == "tests" else run_stage(a, args.attempt, args.stage)
    print(json.dumps(result))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
