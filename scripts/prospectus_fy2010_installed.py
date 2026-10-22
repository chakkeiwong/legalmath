"""Admitted offline wheel installation and finite FY2010 consumer evaluation."""
import argparse
from datetime import datetime, timezone
import gzip
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

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
REVIEW = BASE / "reviews/fy2010-installed-143"
HISTORICAL = BASE / "attempts/native-confinement/attempt-004"
WORKER = ROOT / "scripts/prospectus_fy2010_installed_worker.py"
STAGES = ("prepare", "old-profile", "build", "install", "inventory", "matched", "controls", "prior-profiles", "seal")
COMMANDS = ("old-profile", "build", "install", "matched", "controls", "prior-profiles")


def require(ok, message):
    if not ok: raise ValueError(message)


def size(folder):
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file() and not p.is_symlink())


def save(folder, name, value, *, final=False):
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode()
    data = gzip.compress(raw, mtime=0) if name.endswith(".gz") else raw
    require(size(folder) + len(data) < (64 if final else 63) * 1024**2, "Evidence cap")
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream: stream.write(data)


def package():
    return package_files(ROOT / "src/legalmath")


def workspace(folder):
    path = Path(read(folder / "workspace.json")["directory"])
    require(path.parent == ROOT / ".localresources/prospectus" and path.name.startswith("fy2010-installed-")
            and path.resolve() == path, "Owned installation directory required")
    return path


def old_environment():
    return Path(read(HISTORICAL / "workspace.json")["directory"]) / "environment"


def prepare(folder):
    a = Authority(ROOT)
    old = old_environment()
    event = next(e for e in reversed(a.events()) if e.get("attempt") == str(HISTORICAL.relative_to(ROOT)))
    require(a.retained_evidence_valid(event), "Historical installation evidence changed")
    old_package = read(HISTORICAL / "source-package.json")
    require(package_files(old / "lib/python3.11/site-packages/legalmath") == old_package, "Old installed package changed")
    deps = tree(old, dependencies=True)
    require(deps == read(HISTORICAL / "dependencies.json"), "Old dependencies changed")
    work = Path(tempfile.mkdtemp(prefix="fy2010-installed-", dir=ROOT / ".localresources/prospectus"))
    save(folder, "workspace.json", {"directory": str(work), "cloned_from": str(old)})
    shutil.copytree(old, work / "environment", symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    require(tree(work / "environment", dependencies=True) == deps, "Cloned dependency bytes differ")
    save(folder, "dependencies.json", deps)
    save(folder, "old-package.json", old_package)
    source = package()
    save(folder, "source-package.json", source)
    (work / "source").mkdir()
    shutil.copyfile(ROOT / "pyproject.toml", work / "source/pyproject.toml")
    shutil.copytree(ROOT / "src", work / "source/src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"))
    require(package_files(work / "source/src/legalmath") == source, "Copied source differs")
    shutil.copyfile(WORKER, work / "worker.py")
    save(folder, "outer-budget.json", {"maximum": 6, "commands": list(COMMANDS),
        "prior_installed_outer_commands": 37, "prior_installed_native_reservations": 8,
        "native_allowance": 0, "pip_internal_forks_counted": False})
    return {"package_files": len(source), "dependencies": len(deps), "workspace_bytes": size(work)}


def execute(folder, stage):
    work = workspace(folder)
    python = str(work / "environment/bin/python")
    if stage == "old-profile": python = str(old_environment() / "bin/python")
    if stage == "build":
        argv = [python, "-I", "-B", "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--no-index",
                "--wheel-dir", str(folder / "wheel"), str(work / "source")]
    elif stage == "install":
        wheel = read(folder / "built-wheel.json")
        require(file_hash(folder / wheel["file"]) == wheel["sha256"], "Built wheel changed")
        argv = [python, "-I", "-B", "-m", "pip", "install", "--no-deps", "--no-index", "--force-reinstall", str(folder / wheel["file"])]
    else:
        require(file_hash(work / "worker.py") == file_hash(WORKER), "Copied worker changed")
        argv = [python, "-I", "-B", str(work / "worker.py"), str(ROOT), str(folder), stage]
    target = folder / "commands" / stage
    target.mkdir(parents=True, exist_ok=False)
    previous = list((folder / "commands").glob("*/command.json"))
    require(len(previous) == COMMANDS.index(stage) and len(previous) < 6, "Outer command order/budget")
    env = {"CUDA_VISIBLE_DEVICES": "-1", "PYTHONPATH": "", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
           "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_CACHE_DIR": "1"}
    save(folder, "commands/" + stage + "/command.json", {"argv": argv, "cwd": str(work), "env": env,
        "timeout": 110, "reservation": len(previous) + 1, "historical_installed_outer_commands": 37})
    tick, code, error = time.monotonic(), None, None
    try:
        with (target / "stdout").open("xb") as out, (target / "stderr").open("xb") as err:
            code = subprocess.run(argv, cwd=work, env={**os.environ, **env}, stdout=out, stderr=err, timeout=110).returncode
    except BaseException as exc:
        error = str(exc)
        raise
    finally:
        save(folder, "commands/" + stage + "/result.json", {"returncode": code, "error": error, "wall_seconds": time.monotonic() - tick}, final=True)
    require(code == 0, "Installed command failed: " + stage + "; see retained stderr")
    if stage == "build":
        wheels = list((folder / "wheel").glob("*.whl"))
        require(len(wheels) == 1, "One wheel expected")
        with zipfile.ZipFile(wheels[0]) as archive:
            content = {p.removeprefix("legalmath/"): hashlib.sha256(archive.read(p)).hexdigest()
                for p in archive.namelist() if p.startswith("legalmath/") and not p.endswith("/")}
        require(content == read(folder / "source-package.json"), "Built wheel content differs")
        save(folder, "built-wheel.json", {"file": str(wheels[0].relative_to(folder)), "sha256": file_hash(wheels[0])})
    elif stage not in ("install",):
        require(read(target / "installed-result.json")["status"] == "PASS", "Installed worker did not pass")
    return {"outer_command": stage, "returncode": code}


def inventory(folder):
    work = workspace(folder)
    expected = read(folder / "source-package.json")
    require(package_files(work / "environment/lib/python3.11/site-packages/legalmath") == expected == package(), "Installed/source package differs")
    require(tree(work / "environment", dependencies=True) == read(folder / "dependencies.json"), "Installed dependency bytes changed")
    require(package_files(old_environment() / "lib/python3.11/site-packages/legalmath") == read(folder / "old-package.json"), "Historical environment changed")
    require(tree(old_environment(), dependencies=True) == read(folder / "dependencies.json"), "Historical dependencies changed")
    return {"installed_package_equal": True, "dependencies_equal": True, "historical_environment_unchanged": True}


def run(attempt, stage):
    a = Authority(ROOT)
    folder = a.path(attempt)
    program, tasks, _ = a.spec()
    task = tasks["source-bes-dep-08"]
    admitted = read(folder / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == attempt and admitted["program_sha256"] == digest(program)
            and admitted["binding"] == a.binding(task), "Current unchanged admission required")
    require(task.get("installed_fy_review") == str(REVIEW.relative_to(ROOT)) and not (folder / "outputs.json").exists(), "Wrong or sealed admission")
    results = [read(p) for p in (folder / "stages").glob("*/result.json")]
    starts = list((folder / "stages").glob("*/started.json"))
    require(len(results) == len(starts) == STAGES.index(stage) and all(r["status"] == "PASS" for r in results), "Stage repeated/skipped/interrupted/failed")
    history = read(REVIEW / "history.json")
    spent = sum(r["wall_seconds"] for r in results)
    require(len(results) + history["stage_starts"] < 20 and spent < 600 and spent + history["stage_seconds"] < 1440, "Cumulative budget exhausted")
    save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(), "git_commit": admitted["git_commit"],
        "command": ["timeout", "120", ".venv/bin/python", "scripts/prospectus_fy2010_installed.py", "--attempt", attempt, "--stage", stage],
        "interpreter": sys.executable, "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic",
        "inputs": admitted["binding"], "plan": task["dossier"], "result": str((folder / "result.json").relative_to(ROOT)),
        "historical_stage_seconds": history["stage_seconds"], "new_prior_stage_seconds": spent})
    tick, error, details = time.monotonic(), None, None
    try:
        if stage == "prepare": details = prepare(folder)
        elif stage == "inventory": details = inventory(folder)
        elif stage == "seal":
            require((folder / "RESULT.md").is_file(), "Actual result note required")
            details = inventory(folder)
            require(len(list((folder / "commands").glob("*/command.json"))) == 6, "Missing outer execution")
            for name in COMMANDS:
                require(read(folder / "commands" / name / "result.json")["returncode"] == 0, "Failed command")
            details.update(installed_profile_evaluated=True, new_native_calls=0, outer_commands=6,
                           cumulative_installed_outer_commands=43, cumulative_installed_native_reservations=8)
        else: details = execute(folder, stage)
        require(admitted["binding"] == a.binding(task), "Admitted methods/input changed")
        require(size(folder) + history["evidence_bytes"] < 184 * 1024**2 and size(folder) < 64 * 1024**2, "Cumulative evidence cap")
        require(size(workspace(folder)) < 512 * 1024**2, "Workspace cap")
        require(spent + time.monotonic() - tick < 600 and history["stage_seconds"] + spent + time.monotonic() - tick < 1440, "Execution time cap")
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        save(folder, "stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, final=True)
    result = {"status": "FAIL" if error else "PASS", "stage": stage, "error": error, "details": details, "wall_seconds": time.monotonic() - tick}
    save(folder, "stages/" + stage + "/result.json", result, final=True)
    if error or stage == "seal":
        save(folder, "result.json", {**result, "task": task["id"], "whole_program_complete": False,
                                   "independent_acceptance": False, "native_acceptance_refreshed": False}, final=True)
        save(folder, "outputs.json", {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*")) if p.is_file()}, final=True)
    print(json.dumps({k: result[k] for k in ("status", "stage", "error", "wall_seconds")}))
    return int(error is not None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--stage", choices=STAGES, required=True)
    args = parser.parse_args()
    def expired(*_): raise TimeoutError("Installed FY stage exceeded115 seconds")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(115)
    try: return run(args.attempt, args.stage)
    finally: signal.alarm(0)


if __name__ == "__main__": raise SystemExit(main())
