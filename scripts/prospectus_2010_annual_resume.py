"""Bounded continuation of the sealed annual comparison timeout."""
from datetime import datetime, timezone
import difflib
import gzip
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
from scripts import prospectus_2010_annual_resume_cases as cases
from scripts.prospectus_installed_profile_worker import execution_guard

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
HERE = BASE / "attempts/source-bes-dep-09/attempt-009"
REVIEW = BASE / "reviews/2010-annual-resume-188"
PRIOR = BASE / "attempts/source-bes-dep-09/attempt-008"
PLAN = "docs/plans/prospectus-2010-annual-resume-2026-10-17.md"
DOCUMENTATION = "docs/prospectus/statement-cells.md"
INSTALLED = {"installed-build": "candidate-products", "installed-answer": "candidate-answer",
             **{"installed-" + key: key for key in (*cases.INPUT_GROUPS, *cases.PHASE_GROUPS)}}
STAGES = ("prepare", "baseline-products", "baseline-answer", "candidate-products", "candidate-answer", "composition",
          *cases.INPUT_GROUPS, *cases.PHASE_GROUPS, "prior-9m", "prior-q1", "prior-fy", "wheel", "install", *INSTALLED, "seal")
CHILDREN = ("wheel", "install", *INSTALLED)
SELECTOR = {"version": "bes-annual2010-resume.v1", "stages": list(STAGES),
            "new_seconds": 720, "combined003_onward_seconds": 1960,
            "new_bytes": 56*1024**2, "combined003_onward_bytes": 200*1024**2,
            "reserve_bytes": 512*1024, "work_seconds": 45, "stage_seconds": 50,
            "children": list(CHILDREN), "child_seconds": 35,
            "production_edits": [], "extraction_OCR_render_network_model_GPU_retries": 0}
cases.configure(ROOT, HERE)
require = cases.require


def support():
    return [p for p in REVIEW.rglob("*") if p.is_file()] + [Path(__file__), Path(cases.__file__), ROOT / PLAN,
        BASE / "proposals/2010-annual-resume-188.json", BASE / "proposals/2010-annual-resume-188-review.json",
        BASE / "closure-routes-2026-10-17-2010-annual-resume-188.json"]


def storage():
    history = read(REVIEW / "history.json")
    new = sum(p.stat().st_size for p in set(support()) | {ROOT / DOCUMENTATION} if p.is_file())
    new += sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file())
    return {"previous_seconds": history["previous_seconds"], "previous_bytes": history["previous_bytes"],
            "new_bytes": new, "combined_bytes": history["previous_bytes"] + new}


def save(name, value, failure=False):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    data = gzip.compress(raw, mtime=0) if name.endswith(".gz") else raw + b"\n"
    state, reserve = storage(), 0 if failure else SELECTOR["reserve_bytes"]
    require(state["new_bytes"] + len(data) < SELECTOR["new_bytes"] - reserve and
            state["combined_bytes"] + len(data) < SELECTOR["combined003_onward_bytes"] - reserve, "Annual continuation storage cap")
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
            task.get("annual_resume") == SELECTOR and admission["binding"] == a.binding(task), "Current unchanged continuation admission required")
    require(not (HERE / "outputs.json").exists(), "Sealed continuation")
    history = read(REVIEW / "history.json")
    require(all(file_hash(ROOT / p) == h for p, h in history["protected"].items()), "Historical evidence changed")
    require(cases.legacy.package_files(ROOT / "src/legalmath") == history["package"], "Production changed after008 freeze")
    frozen = read(PRIOR / "final-methods.json")
    require(all(file_hash(ROOT / p) == h for p, h in frozen.items() if p != DOCUMENTATION), "008 test/source/fixture changed")
    env = history["build_environment"]
    require(cases.legacy.environment_files(Path(env["path"])) == env["files"], "Read-only environment changed")
    if (HERE / "final-methods.json").exists():
        require(all(file_hash(ROOT / p) == h for p, h in read(HERE / "final-methods.json").items()), "Frozen continuation methods changed")
    return admission


def prepare():
    before = cases.read(PRIOR / "final-methods-content.json.gz")[DOCUMENTATION]
    after = (ROOT / DOCUMENTATION).read_text()
    save("documentation-diff.json", {"patch": "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True)))})
    save("final-package.json", cases.legacy.package_files(ROOT / "src/legalmath"))
    save("final-methods.json", {p: file_hash(ROOT / p) for p in read(PRIOR / "final-methods.json")})
    save("documentation.md.json", {"path": DOCUMENTATION, "text": after})
    require(read(PRIOR / "stages/focused/result.json")["status"] == "PASS" and
            read(PRIOR / "stages/matched/result.json")["status"] == "FAIL", "Retained test/failure evidence missing")
    return {"unchanged_focused_tests": 85, "production_files": 441, "production_edits": 0,
            "failed008_preserved": True, "split_stages": len(STAGES)}


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
    return [python, "-I", "-B", str(ROOT / "scripts/prospectus_2010_annual_resume_cases.py"), str(ROOT), str(HERE), INSTALLED[stage]]


def child(stage):
    if stage == "wheel":
        build = HERE / "build-source"
        build.mkdir()
        shutil.copyfile(ROOT / "pyproject.toml", build / "pyproject.toml")
        shutil.copytree(ROOT / "src/legalmath", build / "src/legalmath", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        require(cases.legacy.package_files(build / "src/legalmath") == read(HERE / "final-package.json"), "Copied package differs")
    elif stage == "install": require(not (HERE / "installed").exists(), "Existing target refused")
    argv = command(stage)
    env = {"CUDA_VISIBLE_DEVICES": "-1", "PYTHONPATH": "", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
           "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_CACHE_DIR": "1", "PIP_CONFIG_FILE": "/dev/null"}
    save("commands/" + stage + "/command.json", {"argv": argv, "cwd": str(HERE), "environment": env,
         "timeout": 35, "reservation": CHILDREN.index(stage) + 1, "build_backend_internal_processes_counted": False})
    target, tick = HERE / "commands" / stage, time.monotonic()
    with (target / "stdout").open("xb") as out, (target / "stderr").open("xb") as err:
        result = subprocess.run(argv, cwd=HERE, env={**os.environ, **env}, stdout=out, stderr=err, timeout=35)
    save("commands/" + stage + "/result.json", {"returncode": result.returncode, "wall_seconds": time.monotonic()-tick})
    require(result.returncode == 0, "Annual continuation child failed: " + stage)
    if stage == "wheel":
        wheel, = (HERE / "wheel").glob("*.whl")
        import hashlib
        with zipfile.ZipFile(wheel) as archive:
            content = {p.removeprefix("legalmath/"): hashlib.sha256(archive.read(p)).hexdigest()
                       for p in archive.namelist() if p.startswith("legalmath/") and not p.endswith("/")}
        require(content == read(HERE / "final-package.json"), "Wheel package differs")
        save("built-wheel.json", {"path": str(wheel.relative_to(HERE)), "sha256": file_hash(wheel), "package_files": len(content)})
    elif stage == "install":
        require(cases.legacy.package_files(HERE / "installed/legalmath") == read(HERE / "final-package.json"), "Installed package differs")
    else:
        require(read(HERE / "installed-checks" / (INSTALLED[stage]+".json"))["status"] == "PASS", "Installed check missing")
    return {"command": stage, "returncode": result.returncode}


def seal():
    require((HERE / "RESULT.md").is_file(), "Actual result review required")
    for groups in (cases.INPUT_GROUPS, cases.PHASE_GROUPS):
        for name, expected in groups.items():
            controls = read(HERE / "checks" / (name+".json"))
            require(set(controls) == set(expected) and all(v["refused"] for v in controls.values()), "Missing actual controls")
    for action in INSTALLED.values():
        require(read(HERE / "installed-checks" / (action+".json"))["status"] == "PASS", "Missing installed check")
    require(cases.legacy.package_files(HERE / "installed/legalmath") == read(HERE / "final-package.json"), "Installed package changed")
    require(read(HERE / "checks/composition.json")["complete007_protected_equal"], "Missing later source answer")
    require(all(read(HERE / "checks" / (name+".json"))["complete_answer_equal"] for name in ("prior-9m", "prior-q1", "prior-fy")), "Missing older answer")
    save("verified-result.json", {"actual_product_consumption": True, "offline_installed_consumption": True,
        "production_changed_since008": False, "fresh_extractions": 0, "actual_public_refusals": 13,
        "actual_installed_refusals": 13, "candidate": read(HERE / "checks/candidate-answer.json"),
        "composition": read(HERE / "checks/composition.json"), "result_note_sha256": file_hash(HERE / "RESULT.md"),
        "independent_acceptance": False, "task_complete": False})
    return {"actual_product_consumption": True, "offline_installed_consumption": True, "task_complete": False}


def run(stage):
    with Authority(ROOT).lock():
        admission = bindings()
        index = STAGES.index(stage)
        require({p.parent.name for p in (HERE / "stages").glob("*/started.json")} ==
                {p.parent.name for p in (HERE / "stages").glob("*/result.json")} == set(STAGES[:index]), "Repeated/skipped/interrupted continuation stage")
        rows = [read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < 50 for r in rows), "Failed predecessor")
        spent, before = sum(r["wall_seconds"] for r in rows), storage()
        def within(state, elapsed=0):
            return spent+elapsed < 720 and state["previous_seconds"]+spent+elapsed < 1960 and \
                state["new_bytes"] < SELECTOR["new_bytes"]-SELECTOR["reserve_bytes"] and \
                state["combined_bytes"] < SELECTOR["combined003_onward_bytes"]-SELECTOR["reserve_bytes"]
        require(within(before), "Cumulative continuation bounds exhausted")
        save("stages/"+stage+"/started.json", {"at": datetime.now(timezone.utc).isoformat(),
            "command": ["timeout", "55", ".venv/bin/python", "-m", "scripts.prospectus_2010_annual_resume", stage],
            "git_commit": admission["git_commit"], "python": sys.executable, "cpu_gpu": "CPU only; GPUs intentionally hidden",
            "random_seeds": "N/A deterministic", "data_version": "original annual P1 plus sealed006/007 readings; frozen008 package",
            "plan": PLAN, "result": str((HERE / "RESULT.md").relative_to(ROOT))})
        tick, details, error = time.monotonic(), None, None
        def expire(*_): raise TimeoutError("Continuation stage/cumulative bound; no unchanged retry")
        old = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(45, 720-spent, 1960-before["previous_seconds"]-spent))
        try:
            commands = [command(stage)] if stage in CHILDREN else []
            with execution_guard(commands) as guard:
                if stage in CHILDREN: details = child(stage)
                elif stage == "prepare": details = prepare()
                elif stage == "seal": details = seal()
                else:
                    details = cases.dispatch(stage)
                    save("checks/"+stage+".json", details)
            require(guard.result() == {"starts": len(commands), "blocked": 0}, "Unexpected process/network action")
            bindings()
            require(time.monotonic()-tick < 50 and within(storage(), time.monotonic()-tick), "Continuation bounds exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/"+stage+"/error.json", {"traceback": traceback.format_exc()}, failure=True)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
        result = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error, "details": details,
            "wall_seconds": time.monotonic()-tick, "bounds": storage(),
            "timing_scope": "Stage body and final identity verification; excludes startup/final receipt writing"}
        result["cumulative_seconds"] = spent+result["wall_seconds"]
        save("stages/"+stage+"/result.json", result, failure=bool(error))
        if error or stage == "seal":
            save("result.json", {**result, "task": "source-bes-dep-09", "task_complete": False,
                "whole_program_complete": False, "independent_acceptance": False}, failure=bool(error))
            save("outputs.json", cases.legacy.package_files(HERE), failure=bool(error))
        print(json.dumps({k: result[k] for k in ("stage", "status", "error", "wall_seconds", "cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1]))
