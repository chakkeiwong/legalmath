"""Bounded annual statement integration and offline installed-wheel checks."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import difflib
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                  PYTHONNOUSERSITE="1", PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts import prospectus_2010_annual_cases as cases
from scripts.prospectus_installed_profile_worker import execution_guard

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
HERE = BASE / "attempts/source-bes-dep-09/attempt-008"
REVIEW = BASE / "reviews/2010-annual-product-187"
PLAN = "docs/plans/prospectus-2010-annual-product-2026-10-17.md"
PRODUCTION = "src/legalmath/prospectus/successor/statement_cells.py"
MUTABLE = (PRODUCTION, "tests/prospectus_successor/test_annual_statement_cells.py",
           "tests/prospectus_successor/fixtures/bes_annual2010_statement_cells.json.gz",
           "docs/prospectus/statement-cells.md")
STAGES = ("prepare", "focused", "matched", "input-controls", "phase-controls", "prior-profiles",
          "wheel", "install", "installed-matched", "installed-input", "installed-phase", "seal")
CHILDREN = ("wheel", "install", "installed-matched", "installed-input", "installed-phase")
SELECTOR = {"version": "bes-annual2010-product.v1", "stages": list(STAGES),
            "source_pages": list(cases.PAGES), "source_occurrences": 1171,
            "new_seconds": 540, "combined003_onward_seconds": 1960,
            "new_bytes": 64 * 1024**2, "combined003_onward_bytes": 200 * 1024**2,
            "reserve_bytes": 512 * 1024, "work_seconds": 45, "stage_seconds": 50,
            "children": list(CHILDREN), "child_seconds": 35, "production_edits": [PRODUCTION],
            "extraction_OCR_network_model_GPU_retries": 0}
cases.configure(ROOT, HERE)
require = cases.require


def new_support():
    return [p for p in REVIEW.rglob("*") if p.is_file()] + [Path(__file__), Path(cases.__file__), ROOT / PLAN,
        BASE / "proposals/2010-annual-product-187.json", BASE / "proposals/2010-annual-product-187-review.json",
        BASE / "closure-routes-2026-10-17-2010-annual-product-187.json"]


def storage():
    history = read(REVIEW / "history.json") if (REVIEW / "history.json").exists() else {}
    support = set(new_support()) | {ROOT / p for p in MUTABLE if p != PRODUCTION}
    new = sum(p.stat().st_size for p in support if p.is_file())
    new += sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file())
    return {"previous_seconds": history.get("previous_seconds", 0), "new_bytes": new,
            "combined_bytes": history.get("previous_bytes", 0) + new,
            "previous_bytes": history.get("previous_bytes", 0)}


def save(name, value, failure=False):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    data = gzip.compress(raw, mtime=0) if name.endswith(".gz") else raw + b"\n"
    state = storage()
    reserve = 0 if failure else SELECTOR["reserve_bytes"]
    require(state["new_bytes"] + len(data) < SELECTOR["new_bytes"] - reserve and
            state["combined_bytes"] + len(data) < SELECTOR["combined003_onward_bytes"] - reserve, "Annual storage cap")
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream: stream.write(data)


def bindings():
    a = Authority(ROOT)
    program, tasks, _ = a.spec()
    task = tasks["source-bes-dep-09"]
    admission = read(HERE / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT)) and
            admission["task_spec"] == task and admission["program_sha256"] == digest(program) and
            task.get("annual_product") == SELECTOR and admission["binding"] == a.binding(task),
            "Current unchanged annual product admission required")
    require(not (HERE / "outputs.json").exists(), "Sealed annual attempt")
    history = read(REVIEW / "history.json")
    require(all(file_hash(ROOT / p) == h for p, h in history["protected"].items()), "Historical evidence changed")
    environment = history["build_environment"]
    require(cases.environment_files(Path(environment["path"])) == environment["files"], "Read-only build environment changed")
    package = cases.package_files(ROOT / "src/legalmath")
    expected = history["package"]
    relative = PRODUCTION.removeprefix("src/legalmath/")
    require(set(package) == set(expected) and all(package[p] == h for p, h in expected.items() if p != relative),
            "Unreviewed production edit")
    if (HERE / "final-package.json").exists():
        require(package == read(HERE / "final-package.json") and
                all(file_hash(ROOT / p) == h for p, h in read(HERE / "final-methods.json").items()), "Frozen annual methods changed")
    return admission


def prepare():
    profile = read(REVIEW / "profile.json")
    require(cases.cells.PROFILES[cases.PROFILE] == {**profile, "pages": tuple(profile["pages"]),
                "reading_fields": tuple(profile["reading_fields"])}, "Product profile differs from reviewed pins")
    require(file_hash(ROOT / MUTABLE[2]) == file_hash(REVIEW / "fixture.json.gz"), "Test fixture differs from source fixture")
    before = read(REVIEW / "baseline-methods.json")
    patch = ""
    for p, ref in before.items():
        patch += "".join(difflib.unified_diff((ROOT / ref["path"]).read_text().splitlines(True),
             (ROOT / p).read_text().splitlines(True), fromfile="before/" + p, tofile="after/" + p))
    save("reviewed-diff.json", {"patch": patch, "baseline": before})
    save("final-package.json", cases.package_files(ROOT / "src/legalmath"))
    save("final-methods.json", {p: file_hash(ROOT / p) for p in MUTABLE})
    save("final-methods-content.json.gz", {p: (ROOT / p).read_text() for p in MUTABLE if not p.endswith(".gz")})
    require(cases.package_files(ROOT / "src/legalmath")[PRODUCTION.removeprefix("src/legalmath/")] !=
            read(REVIEW / "history.json")["package"][PRODUCTION.removeprefix("src/legalmath/")], "Profile repair not applied")
    return {"production_files": 441, "changed_production_files": 1, "source_occurrences": 1171}


def focused():
    with (HERE / "focused.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
        import pytest
        code = int(pytest.main(["-q", "-p", "no:cacheprovider", "--junitxml=" + str(HERE / "focused.xml"),
            "tests/prospectus_successor/test_statement_cells.py", "tests/prospectus_successor/test_annual_statement_cells.py",
            "tests/prospectus_successor/test_report_integrity.py"]))
    require(code == 0, "Focused annual/report regression failed")
    return {"pytest_exit": code}


def command(stage):
    python = str(Path(read(REVIEW / "history.json")["build_environment"]["path"]) / "bin/python")
    if stage == "wheel":
        return [python, "-I", "-B", "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--no-index",
                "--wheel-dir", str(HERE / "wheel"), str(HERE / "build-source")]
    if stage == "install":
        wheel = read(HERE / "built-wheel.json")
        require(file_hash(HERE / wheel["path"]) == wheel["sha256"], "Wheel changed")
        return [python, "-I", "-B", "-m", "pip", "install", "--no-deps", "--no-index", "--no-compile",
                "--target", str(HERE / "installed"), str(HERE / wheel["path"])]
    return [python, "-I", "-B", str(ROOT / "scripts/prospectus_2010_annual_cases.py"), str(ROOT), str(HERE), stage[10:]]


def child(stage):
    if stage == "wheel":
        build = HERE / "build-source"
        build.mkdir()
        shutil.copyfile(ROOT / "pyproject.toml", build / "pyproject.toml")
        shutil.copytree(ROOT / "src/legalmath", build / "src/legalmath",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        require(cases.package_files(build / "src/legalmath") == read(HERE / "final-package.json"), "Copied source differs")
    elif stage == "install":
        require(not (HERE / "installed").exists(), "Existing installation target refused")
    argv = command(stage)
    env = {"CUDA_VISIBLE_DEVICES": "-1", "PYTHONPATH": "", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
           "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_CACHE_DIR": "1", "PIP_CONFIG_FILE": "/dev/null"}
    save("commands/" + stage + "/command.json", {"argv": argv, "cwd": str(HERE), "environment": env,
         "timeout": 35, "reservation": CHILDREN.index(stage) + 1, "build_backend_internal_processes_counted": False})
    target = HERE / "commands" / stage
    tick = time.monotonic()
    with (target / "stdout").open("xb") as out, (target / "stderr").open("xb") as err:
        result = subprocess.run(argv, cwd=HERE, env={**os.environ, **env}, stdout=out, stderr=err, timeout=35)
    save("commands/" + stage + "/result.json", {"returncode": result.returncode, "wall_seconds": time.monotonic() - tick})
    require(result.returncode == 0, "Annual child failed: " + stage + "; see retained stderr")
    if stage == "wheel":
        wheel, = (HERE / "wheel").glob("*.whl")
        with zipfile.ZipFile(wheel) as archive:
            content = {p.removeprefix("legalmath/"): hashlib.sha256(archive.read(p)).hexdigest()
                       for p in archive.namelist() if p.startswith("legalmath/") and not p.endswith("/")}
        require(content == read(HERE / "final-package.json"), "Wheel package differs")
        save("built-wheel.json", {"path": str(wheel.relative_to(HERE)), "sha256": file_hash(wheel), "package_files": len(content)})
    elif stage == "install":
        require(cases.package_files(HERE / "installed/legalmath") == read(HERE / "final-package.json"), "Installed package differs")
    else:
        require(read(HERE / (stage + ".json"))["status"] == "PASS", "Installed comparison did not pass")
    return {"command": stage, "returncode": result.returncode}


def seal():
    require((HERE / "RESULT.md").is_file(), "Actual result review required")
    for name in ("input-controls", "phase-controls"):
        values = read(HERE / (name + ".json"))
        require(len(values) == (8 if name == "input-controls" else 5) and all(v["refused"] for v in values.values()), "Missing adverse controls")
    for name in ("matched", "input", "phase"):
        require(read(HERE / ("installed-" + name + ".json"))["status"] == "PASS", "Missing installed result")
    require(cases.package_files(HERE / "installed/legalmath") == read(HERE / "final-package.json"), "Installed package changed")
    require(read(HERE / "prior-profiles.json")["complete_answers_equal"], "Missing older-profile equality")
    save("verified-result.json", {"actual_product_consumption": True, "offline_installed_consumption": True,
         "new_native_extractions": 0, "actual_public_refusals": 13, "actual_installed_refusals": 13,
         "matched": read(HERE / "matched.json"), "result_note_sha256": file_hash(HERE / "RESULT.md"),
         "independent_acceptance": False, "task_complete": False})
    return {"actual_product_consumption": True, "offline_installed_consumption": True, "task_complete": False}


def run(stage):
    with Authority(ROOT).lock():
        admission = bindings()
        index = STAGES.index(stage)
        require({p.parent.name for p in (HERE / "stages").glob("*/started.json")} ==
                {p.parent.name for p in (HERE / "stages").glob("*/result.json")} == set(STAGES[:index]),
                "Repeated/skipped/interrupted annual stage")
        rows = [read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < 50 for r in rows), "Failed predecessor")
        spent, before = sum(r["wall_seconds"] for r in rows), storage()
        def within(state, elapsed=0):
            return spent + elapsed < 540 and state["previous_seconds"] + spent + elapsed < 1960 and \
                state["new_bytes"] < SELECTOR["new_bytes"] - SELECTOR["reserve_bytes"] and \
                state["combined_bytes"] < SELECTOR["combined003_onward_bytes"] - SELECTOR["reserve_bytes"]
        require(within(before), "Cumulative annual bounds exhausted")
        save("stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
             "command": ["timeout", "55", ".venv/bin/python", "-m", "scripts.prospectus_2010_annual_product", stage],
             "git_commit": admission["git_commit"], "python": sys.executable, "cpu_gpu": "CPU only; GPUs intentionally hidden",
             "random_seeds": "N/A deterministic", "data_version": "original annual2010 P1 plus sealed006/007 profiles",
             "plan": PLAN, "result": str((HERE / "RESULT.md").relative_to(ROOT))})
        tick, details, error = time.monotonic(), None, None
        def expire(*_): raise TimeoutError("Annual stage/cumulative bound; no unchanged retry")
        old = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(45, 540-spent, 1960-before["previous_seconds"]-spent))
        try:
            commands = [command(stage)] if stage in CHILDREN else []
            with execution_guard(commands) as guard:
                if stage in CHILDREN: details = child(stage)
                else: details = {"prepare": prepare, "focused": focused, "matched": cases.matched,
                    "input-controls": cases.input_controls, "phase-controls": cases.phase_controls,
                    "prior-profiles": cases.prior_profiles, "seal": seal}[stage]()
            require(guard.result() == {"starts": len(commands), "blocked": 0}, "Unexpected process/network action")
            details["process_guard"] = guard.result()
            bindings()
            require(time.monotonic()-tick < 50 and within(storage(), time.monotonic()-tick), "Annual cumulative bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, failure=True)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
        result = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error, "details": details,
                  "wall_seconds": time.monotonic()-tick, "bounds": storage(),
                  "timing_scope": "Stage body and final identity verification; excludes startup/final receipt writing"}
        result["cumulative_seconds"] = spent + result["wall_seconds"]
        save("stages/" + stage + "/result.json", result, failure=bool(error))
        if error or stage == "seal":
            save("result.json", {**result, "task": "source-bes-dep-09", "task_complete": False,
                 "whole_program_complete": False, "independent_acceptance": False}, failure=bool(error))
            save("outputs.json", cases.package_files(HERE), failure=bool(error))
        print(json.dumps({k: result[k] for k in ("stage", "status", "error", "wall_seconds", "cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1]))
