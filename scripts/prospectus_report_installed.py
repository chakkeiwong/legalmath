"""Admitted offline installation of the final report-integrity repair."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts.prospectus_installed_current import tree
from scripts.prospectus_installed_consumer import package_files
from scripts.prospectus_report_integrity import save, size

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
REVIEW = BASE / "reviews/report-installed-146"
HISTORICAL = BASE / "attempts/source-bes-dep-08/attempt-007"
WORKER = ROOT / "scripts/prospectus_report_installed_worker.py"
HELPER = ROOT / "scripts/prospectus_fy2010_installed_worker.py"
STAGES = ("prepare", "old-boundary", "build", "install", "inventory", "reports", "report-controls",
          "audit-qualifications", "committee-context", "committee-dates", "fy-matched", "fy-controls", "prior-profiles", "seal")
COMMANDS = tuple(s for s in STAGES if s not in ("prepare", "inventory", "seal"))


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def package():
    return package_files(ROOT / "src/legalmath")


def workspace(folder):
    path = Path(read(folder / "workspace.json")["directory"])
    require(path.parent == ROOT / ".localresources/prospectus" and path.name.startswith("report-installed-")
            and path.resolve() == path, "Owned installation directory required")
    return path


def old_environment():
    return Path(read(HISTORICAL / "workspace.json")["directory"]) / "environment"


def prepare(folder):
    old = old_environment()
    old_package = read(HISTORICAL / "source-package.json")
    require(package_files(old / "lib/python3.11/site-packages/legalmath") == old_package, "Historical package changed")
    deps = tree(old, dependencies=True)
    require(deps == read(HISTORICAL / "dependencies.json"), "Historical dependencies changed")
    source = package()
    changed = [k for k in sorted(set(old_package) | set(source)) if old_package.get(k) != source.get(k)]
    require(changed == ["prospectus/successor/service.py"], "Unexpected final package delta")
    work = Path(tempfile.mkdtemp(prefix="report-installed-", dir=ROOT / ".localresources/prospectus"))
    save(folder, "workspace.json", {"directory": str(work), "cloned_from": str(old)})
    shutil.copytree(old, work / "environment", symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    require(tree(work / "environment", dependencies=True) == deps, "Cloned dependencies differ")
    save(folder, "dependencies.json", deps)
    save(folder, "old-package.json", old_package)
    save(folder, "source-package.json", source)
    (work / "source").mkdir()
    shutil.copyfile(ROOT / "pyproject.toml", work / "source/pyproject.toml")
    shutil.copytree(ROOT / "src", work / "source/src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"))
    require(package_files(work / "source/src/legalmath") == source, "Copied source differs")
    shutil.copyfile(WORKER, work / "worker.py")
    shutil.copyfile(HELPER, work / "fy_worker.py")
    save(folder, "harness.json", {"worker_sha256": file_hash(WORKER), "fy_helper_sha256": file_hash(HELPER)})
    save(folder, "outer-budget.json", {"maximum": 11, "commands": list(COMMANDS),
        "prior_installed_outer_commands": 43, "prior_installed_native_reservations": 8,
        "native_allowance": 0, "pip_internal_forks_counted": False})
    return {"package_files": len(source), "dependencies": len(deps), "changed_package_files": changed,
            "workspace_bytes": size(work)}


def execute(folder, stage):
    work = workspace(folder)
    python = str((old_environment() if stage == "old-boundary" else work / "environment") / "bin/python")
    if stage == "build":
        argv = [python, "-I", "-B", "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--no-index",
                "--wheel-dir", str(folder / "wheel"), str(work / "source")]
    elif stage == "install":
        wheel = read(folder / "built-wheel.json")
        require(file_hash(folder / wheel["file"]) == wheel["sha256"], "Wheel bytes changed")
        argv = [python, "-I", "-B", "-m", "pip", "install", "--no-deps", "--no-index", "--force-reinstall", str(folder / wheel["file"])]
    else:
        require(file_hash(work / "worker.py") == file_hash(WORKER) and file_hash(work / "fy_worker.py") == file_hash(HELPER),
                "Copied installed harness changed")
        argv = [python, "-I", "-B", str(work / "worker.py"), str(ROOT), str(folder), stage]
    target = folder / "commands" / stage
    target.mkdir(parents=True, exist_ok=False)
    prior = list((folder / "commands").glob("*/command.json"))
    require(len(prior) == COMMANDS.index(stage) and len(prior) < 11, "Outer command order/budget")
    env = {"CUDA_VISIBLE_DEVICES": "-1", "PYTHONPATH": "", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
           "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_CACHE_DIR": "1"}
    save(folder, "commands/" + stage + "/command.json", {"argv": argv, "cwd": str(work), "env": env,
        "timeout": 110, "reservation": len(prior) + 1, "historical_installed_outer_commands": 43})
    tick, code, error = time.monotonic(), None, None
    try:
        with (target / "stdout").open("xb") as out, (target / "stderr").open("xb") as err:
            code = subprocess.run(argv, cwd=work, env={**os.environ, **env}, stdout=out, stderr=err, timeout=110).returncode
    except BaseException as exc:
        error = str(exc)
        raise
    finally:
        save(folder, "commands/" + stage + "/result.json", {"returncode": code, "error": error, "wall_seconds": time.monotonic() - tick}, final=True)
    require(code == 0, "Installed command failed: " + stage + "; see retained result/stderr")
    if stage == "build":
        wheels = list((folder / "wheel").glob("*.whl"))
        require(len(wheels) == 1, "Exactly one wheel required")
        with zipfile.ZipFile(wheels[0]) as archive:
            content = {p.removeprefix("legalmath/"): hashlib.sha256(archive.read(p)).hexdigest()
                       for p in archive.namelist() if p.startswith("legalmath/") and not p.endswith("/")}
        require(content == read(folder / "source-package.json"), "Wheel payload differs")
        save(folder, "built-wheel.json", {"file": str(wheels[0].relative_to(folder)), "sha256": file_hash(wheels[0])})
    elif stage != "install":
        require(read(target / "installed-result.json")["status"] == "PASS", "Installed worker did not pass")
    return {"outer_command": stage, "returncode": code}


def inventory(folder):
    work = workspace(folder)
    require(package_files(work / "environment/lib/python3.11/site-packages/legalmath") == read(folder / "source-package.json") == package(),
            "Installed/source package differs")
    deps = read(folder / "dependencies.json")
    require(tree(work / "environment", dependencies=True) == deps, "Installed dependencies changed")
    require(package_files(old_environment() / "lib/python3.11/site-packages/legalmath") == read(folder / "old-package.json") and
            tree(old_environment(), dependencies=True) == deps, "Historical environment changed")
    return {"installed_package_equal": True, "dependencies_equal": True, "historical_environment_unchanged": True}


def run(attempt, stage):
    a = Authority(ROOT)
    folder = a.path(attempt)
    program, tasks, _ = a.spec()
    task = tasks["source-bes-dep-09"]
    admitted = read(folder / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == attempt and admitted["program_sha256"] == digest(program)
            and admitted["binding"] == a.binding(task), "Current unchanged admission required")
    require(task.get("installed_report_review") == str(REVIEW.relative_to(ROOT)) and not (folder / "outputs.json").exists(),
            "Wrong or sealed admission")
    history = read(REVIEW / "history.json")
    require(all(a.retained_evidence_valid(e) for e in history["events"]), "Retained installed/source evidence changed")
    results = [read(p) for p in (folder / "stages").glob("*/result.json")]
    starts = list((folder / "stages").glob("*/started.json"))
    require(len(results) == len(starts) == STAGES.index(stage) and all(r["status"] == "PASS" for r in results),
            "Repeated/skipped/interrupted/failed stage")
    spent = sum(r["wall_seconds"] for r in results)
    require(spent < 1000 and history["source003_004_seconds"] + spent < 1960 and len(results) + history["source003_004_stages"] < 24,
            "Cumulative execution budget exhausted")
    save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
        "command": ["timeout", "120", ".venv/bin/python", "scripts/prospectus_report_installed.py", "--attempt", attempt, "--stage", stage],
        "git_commit": admitted["git_commit"], "interpreter": sys.executable, "cpu_gpu": "CPU only; GPUs intentionally hidden",
        "random_seeds": "N/A deterministic comparison", "inputs": admitted["binding"], "plan": task["dossier"],
        "result": str((folder / "result.json").relative_to(ROOT)), "new_prior_stage_seconds": spent,
        "source003_004_seconds": history["source003_004_seconds"], "earlier_history": history["earlier_history"]})
    tick, error, details = time.monotonic(), None, None
    try:
        if stage == "prepare":
            details = prepare(folder)
        elif stage == "inventory":
            details = inventory(folder)
        elif stage == "seal":
            require((folder / "RESULT.md").is_file(), "Actual result review required")
            details = inventory(folder)
            require(len(list((folder / "commands").glob("*/command.json"))) == 11, "Missing outer commands")
            for name in COMMANDS:
                require(read(folder / "commands" / name / "result.json")["returncode"] == 0, "Failed outer command")
            details.update(installed_report_repair_evaluated=True, outer_commands=11, new_native_calls=0,
                           cumulative_installed_outer_commands=54, cumulative_installed_native_reservations=8)
        else:
            details = execute(folder, stage)
        require(admitted["binding"] == a.binding(task), "Admitted methods/inputs changed")
        require(size(folder) < 96 * 1024**2 and size(folder) + history["source003_004_bytes"] < 200 * 1024**2,
                "Cumulative evidence cap")
        require(size(workspace(folder)) < 512 * 1024**2, "Workspace cap")
        require(spent + time.monotonic() - tick < 1000 and history["source003_004_seconds"] + spent + time.monotonic() - tick < 1960,
                "Execution time cap")
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        save(folder, "stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, final=True)
    result = {"status": "FAIL" if error else "PASS", "stage": stage, "error": error, "details": details, "wall_seconds": time.monotonic() - tick}
    save(folder, "stages/" + stage + "/result.json", result, final=True)
    if error or stage == "seal":
        save(folder, "result.json", {**result, "task": task["id"], "task_complete": False, "independent_acceptance": False,
                                    "native_acceptance_refreshed": False}, final=True)
        save(folder, "outputs.json", {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*")) if p.is_file()}, final=True)
    print(json.dumps({k: result[k] for k in ("status", "stage", "error", "wall_seconds")}))
    return int(error is not None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--stage", choices=STAGES, required=True)
    args = parser.parse_args()
    def expired(*_):
        raise TimeoutError("Installed report stage exceeded115 seconds")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(115)
    try:
        return run(args.attempt, args.stage)
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
