"""Finish the retained pension reader in bounded, isolated installation stages."""
from datetime import datetime, timezone
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

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PIP_NO_INDEX="1",
    PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_CACHE_DIR="1",
    PYTHONNOUSERSITE="1", PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from legalmath.prospectus.successor import process_ledger
from scripts.prospectus_installed_profile_worker import execution_guard
from scripts.prospectus_basf_pension_source import files, load, require

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
OLD = BASE / "attempts/basf-references/attempt-005"
HERE = BASE / "attempts/basf-references/attempt-006"
REVIEW = BASE / "reviews/basf-pension-install-160"
PLAN = "docs/plans/prospectus-basf-pension-install-repair-2026-10-16.md"
RUNNER = ROOT / "scripts/prospectus_installed_pension_split.py"
STAGES = ("prepare", "build", "install", "positive", "controls-a", "controls-b", "verify", "seal")
SELECTOR = {"version": "basf-pension-installed-split.v1", "stages": list(STAGES),
    "work_seconds": 110, "stage_seconds": 115, "child_seconds": 100,
    "execution_seconds": 900, "storage_bytes": 500 * 1024**2,
    "new_outer_children": 5, "cumulative_outer_children": 6,
    "new_native_renders": 0, "extractions": 0, "source_http": 0,
    "unchanged_retries": 0, "further_repairs": 0}


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        stream.write("\n")


def workspace():
    return Path(read(HERE / "workspace.json")["directory"])


def storage():
    folders = [OLD, HERE]
    if (HERE / "workspace.json").is_file():
        folders.append(workspace())
    return sum(p.stat().st_size for folder in folders for p in folder.rglob("*") if p.is_file())


def dependencies(env):
    site = env / "lib/python3.11/site-packages"
    return {str(p.relative_to(site)): file_hash(p) for p in sorted(site.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        and not p.relative_to(site).parts[0].startswith("legalmath")}


def bindings():
    a = Authority(ROOT)
    program, tasks, _ = a.spec()
    task = tasks["basf-references"]
    require(task.get("pension_install_repair") == SELECTOR, "Unreviewed pension installation repair")
    admitted = read(HERE / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == "basf-references")
    require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT))
        and admitted["program_sha256"] == digest(program) and admitted["task_spec"] == task
        and admitted["binding"] == a.binding(task), "Current unchanged installation admission required")
    require(not (HERE / "outputs.json").exists(), "Installation evidence already sealed")
    history = read(REVIEW / "history.json")
    require(all(file_hash(ROOT / p) == h for p, h in history["protected"].items()),
        "Retained pension evidence or original methods changed")
    require(files(ROOT / "src/legalmath") == history["source_package"], "Source package changed")
    return admitted


def prepare():
    history = read(REVIEW / "history.json")
    env = Path(history["environment"])
    require(files(env / "lib/python3.11/site-packages/legalmath") == history["original_package"],
        "Retained 434-file installed baseline changed")
    needed = sum(p.stat().st_size for p in env.rglob("*") if p.is_file())
    needed += sum(p.stat().st_size for p in (ROOT / "src").rglob("*") if p.is_file())
    require(storage() + needed + 64 * 1024**2 < 498 * 1024**2,
        "Measured installation cannot fit with 64MiB reserve")
    temp = Path(tempfile.mkdtemp(prefix="installed-basf-pension-", dir=ROOT / ".localresources/prospectus"))
    save("workspace.json", {"directory": str(temp), "cloned_from": str(env), "measured_copy_bytes": needed})
    shutil.copytree(env, temp / "environment", symlinks=True)
    (temp / "source").mkdir()
    shutil.copyfile(ROOT / "pyproject.toml", temp / "source/pyproject.toml")
    shutil.copytree(ROOT / "src", temp / "source/src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"))
    shutil.copyfile(RUNNER, temp / "runner.py")
    require(files(temp / "source/src/legalmath") == history["source_package"], "Copied source differs")
    require(file_hash(temp / "runner.py") == file_hash(RUNNER), "Copied runner differs")
    save("source-package.json", history["source_package"])
    save("dependency-files.json", dependencies(temp / "environment"))
    save("package-preservation.json", {"preexisting_files": 434, "unchanged": True,
        "new_files": ["prospectus/basf_pension_note.py", "prospectus/basf_pension_spec.py"]})
    save("control-partitions.json", {"controls-a": history["control_cases"][:15],
        "controls-b": history["control_cases"][15:]})
    process_ledger.create(HERE / "command-ledger.json", 5, 1,
        "Five installation children; one retained source render in references005; pip internals excluded")
    return {"source_files": 436, "preserved_files": 434,
        "dependency_entries": len(read(HERE / "dependency-files.json")), "development_reexecutions": 0}


def child(name, argv):
    folder = HERE / "commands" / name
    folder.mkdir(parents=True, exist_ok=False)
    save("commands/" + name + "/started.json", {"argv": argv, "timeout_seconds": 100,
        "cpu_gpu": "CPU only; GPU devices intentionally hidden"})
    tick = time.monotonic()
    error = None
    result = None
    with (folder / "stdout").open("xb") as out, (folder / "stderr").open("xb") as err:
        with execution_guard([argv]) as guard, process_ledger.observe(HERE / "command-ledger.json"):
            try:
                result = subprocess.run(argv, stdout=out, stderr=err, timeout=100, env=dict(os.environ))
            except BaseException as exc:
                error = {"type": type(exc).__name__, "message": str(exc)}
            finally:
                save("commands/" + name + "/result.json", {"returncode": None if result is None else result.returncode,
                    "error": error, "wall_seconds": time.monotonic() - tick, "process_guard": guard.result()})
    require(error is None and result is not None and result.returncode == 0, "Installation child failed: " + name)
    require(guard.result() == {"starts": 1, "blocked": 0}, "Unexpected installation process action")


def build():
    (HERE / "wheel").mkdir()
    child("build", [str(workspace() / "environment/bin/python"), "-m", "pip", "wheel", "--no-deps",
        "--no-build-isolation", "--no-index", "--wheel-dir", str(HERE / "wheel"), str(workspace() / "source")])
    wheels = list((HERE / "wheel").glob("*.whl"))
    require(len(wheels) == 1, "Exactly one offline wheel required")
    result = {"path": str(wheels[0].relative_to(HERE)), "sha256": file_hash(wheels[0])}
    save("built-wheel.json", result)
    return result


def install():
    wheel = read(HERE / "built-wheel.json")
    require(file_hash(HERE / wheel["path"]) == wheel["sha256"], "Built wheel changed")
    child("install", [str(workspace() / "environment/bin/python"), "-m", "pip", "install", "--no-index",
        "--no-deps", "--force-reinstall", str(HERE / wheel["path"])])
    require(dependencies(workspace() / "environment") == read(HERE / "dependency-files.json"), "Dependencies changed")
    require(files(workspace() / "environment/lib/python3.11/site-packages/legalmath") == read(HERE / "source-package.json"),
        "Installed package differs from source")
    return {"installed": True, "dependencies_unchanged": True, "package_files": 436}


def replay(mode):
    require(file_hash(workspace() / "runner.py") == file_hash(RUNNER), "Installed runner changed")
    child(mode, [str(workspace() / "environment/bin/python"), "-I", str(workspace() / "runner.py"),
        str(HERE), str(OLD), str(ROOT), mode])
    result = read(HERE / "installed-results" / mode / "result.json")
    require(result["status"] == "PASS" and result["mode"] == mode, "Installed replay did not pass")
    return result


def verify():
    package = workspace() / "environment/lib/python3.11/site-packages/legalmath"
    expected = read(HERE / "source-package.json")
    require(files(package) == expected == files(ROOT / "src/legalmath"), "Installed or current package drift")
    require(dependencies(workspace() / "environment") == read(HERE / "dependency-files.json"), "Dependency drift")
    for mode in ("positive", "controls-a", "controls-b"):
        folder = HERE / "installed-results" / mode
        result, proof = read(folder / "result.json"), read(folder / "import-proof.json")
        require(result["status"] == "PASS" and result["mode"] == mode
            and result["process_guard"] == {"starts": 0, "blocked": 0}, "Invalid isolated result")
        require(read(folder / "package-files.json") == expected and proof["isolated"] == 1
            and Path(proof["prefix"]).resolve() == (workspace() / "environment").resolve(), "Wrong installed package or prefix")
        for item in proof["modules"].values():
            p = Path(item["path"]).resolve()
            require(p.is_relative_to(package) and file_hash(p) == item["sha256"] == expected[str(p.relative_to(package))],
                "Wrong installed import identity")
    positive = HERE / "installed-results/positive"
    require(load(positive / "pension-consumer.json.gz") == load(OLD / "pension-consumer.json.gz"), "Full installed output differs")
    controls = sum([read(HERE / "installed-results" / mode / "controls.json") for mode in ("controls-a", "controls-b")], [])
    require(controls == read(OLD / "actual-controls.json"), "Installed ordered control union differs")
    partitions = read(HERE / "control-partitions.json")
    for mode in ("controls-a", "controls-b"):
        require([r["case"] for r in read(HERE / "installed-results" / mode / "controls.json")] == partitions[mode],
            "Installed partition differs")
    ledger = process_ledger.checked(HERE / "command-ledger.json")
    require(len(ledger["reservations"]) == 5 and ledger["historical_lower_bound"] == 1, "Wrong new process count")
    for name in ("command-ledger.json", "native-ledger.json"):
        require(len(process_ledger.checked(OLD / name)["reservations"]) == 1, "Retained render count changed")
    result = {**read(OLD / "comparison.json"), "installed_complete_output_equal": True,
        "earlier_outputs_unchanged": True, "actual_refusals": 29, "repinned": 28,
        "exact_package_files": len(expected), "preexisting_package_files_unchanged": 434,
        "unchanged_dependency_entries": len(read(HERE / "dependency-files.json")),
        "new_outer_children": 5, "cumulative_outer_children": 6,
        "new_native_renders": 0, "new_extractions": 0, "source_http_calls": 0,
        "different_host_portability": False, "independent_legal_acceptance": False}
    save("verified-result.json", result)
    return result


def seal():
    require((HERE / "RESULT.md").is_file(), "Actual installation analysis required")
    require(read(HERE / "verified-result.json")["status"] == "PASS", "Verified installation missing")
    return {"validated": True, "task_complete": False, "independent_legal_acceptance": False}


def run(stage):
    with Authority(ROOT).lock():
        admitted = bindings()
        index = STAGES.index(stage)
        started = {p.parent.name for p in (HERE / "stages").glob("*/started.json")}
        finished = {p.parent.name for p in (HERE / "stages").glob("*/result.json")}
        require(started == finished == set(STAGES[:index]), "Repeated, skipped or interrupted installation stage")
        rows = [read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < 115 for r in rows), "Failed predecessor")
        prior_seconds = read(REVIEW / "history.json")["prior_seconds"]
        spent = prior_seconds + sum(r["wall_seconds"] for r in rows)
        require(spent < 900 and storage() < 498 * 1024**2, "Cumulative installation allowance exhausted")
        save("stages/" + stage + "/started.json", {"command": ["timeout", "120", ".venv/bin/python", "-m",
            "scripts.prospectus_basf_pension_install", stage], "at": datetime.now(timezone.utc).isoformat(),
            "git_commit": admitted["git_commit"], "dirty_source_hashes": str((HERE / "source-package.json").relative_to(ROOT)),
            "python": sys.executable, "cpu_gpu": "CPU only; GPU devices intentionally hidden",
            "random_seeds": "N/A deterministic installed replay", "plan": PLAN,
            "data_version": str((OLD / "outputs.json").relative_to(ROOT)),
            "result": str((HERE / "RESULT.md").relative_to(ROOT)), "prior_execution_seconds": spent})
        tick, details, error = time.monotonic(), None, None
        def expire(signum, frame):
            raise TimeoutError("Installation work limit; no unchanged retry or further repair")
        old_handler = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(110, 900 - spent))
        try:
            if stage in ("positive", "controls-a", "controls-b"):
                details = replay(stage)
            elif stage in ("build", "install"):
                details = globals()[stage]()
            else:
                with execution_guard() as guard:
                    details = globals()[stage]()
                    require(guard.result() == {"starts": 0, "blocked": 0}, "Unexpected process action")
                details = {**details, "process_guard": guard.result()}
            bindings()
            require(storage() < 498 * 1024**2, "Cumulative storage limit")
            require(time.monotonic() - tick < 115 and spent + time.monotonic() - tick < 900, "Recorded time limit")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/" + stage + "/error.json", {"traceback": traceback.format_exc()})
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
        value = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error, "details": details,
            "wall_seconds": time.monotonic() - tick, "retained_bytes": storage()}
        value["cumulative_seconds"] = spent + value["wall_seconds"]
        save("stages/" + stage + "/result.json", value)
        if error or stage == "seal":
            save("result.json", {**value, "task": "basf-references", "task_complete": False,
                "whole_program_complete": False, "independent_legal_acceptance": False})
            save("outputs.json", files(HERE))
        print(json.dumps({k: value[k] for k in ("stage", "status", "error", "wall_seconds", "cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    require(len(sys.argv) == 2 and sys.argv[1] in STAGES, "Choose one admitted installation stage")
    raise SystemExit(run(sys.argv[1]))
