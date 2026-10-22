"""Bounded downstream integration of the reviewed annual capital-note reading."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import difflib
import gzip
import hashlib
import importlib.util
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
from legalmath.prospectus.execution_authority import Authority, digest as authority_digest, file_hash, read
from legalmath.prospectus.execution_authority import digest
from scripts.prospectus_installed_profile_worker import execution_guard
from scripts import prospectus_2010_capital_product_cases as cases

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
HERE = BASE / "attempts/source-bes-dep-09/attempt-011"
REVIEW = BASE / "reviews/2010-capital-product-190"
SOURCE = BASE / "attempts/source-bes-dep-09"
PLAN = "docs/plans/prospectus-2010-capital-product-2026-10-17.md"
PRODUCTION = "src/legalmath/prospectus/successor/statement_cells.py"
FIXTURE = "tests/prospectus_successor/fixtures/bes_annual2010_statement_cells_v2.json.gz"
STAGES = (
    "prepare", "focused", "baseline-products", "baseline-answer", "candidate-products",
    "candidate-answer", "composition", "input-a", "input-b", "input-c", "input-d",
    "phase-a", "phase-b", "phase-c", "prior-profiles", "wheel", "install",
    "installed-candidate-products", "installed-candidate-answer", "installed-input-a",
    "installed-input-b", "installed-input-c", "installed-input-d", "installed-phase-a",
    "installed-phase-b", "installed-phase-c", "seal",
)
CHILDREN = (
    "wheel", "install", "installed-candidate-products", "installed-candidate-answer",
    "installed-input-a", "installed-input-b", "installed-input-c", "installed-input-d",
    "installed-phase-a", "installed-phase-b", "installed-phase-c",
)
SELECTOR = {
    "version": "bes-annual2010-capital-product.v1", "stages": list(STAGES),
    "source_pages": list(cases.PAGES), "source_occurrences": cases.OCCURRENCES,
    "new_seconds": 720, "combined003_onward_seconds": 1960,
    "new_bytes": 20 * 1024**2, "combined003_onward_bytes": 200 * 1024**2,
    "reserve_bytes": 512 * 1024, "work_seconds": 45, "stage_seconds": 50,
    "children": list(CHILDREN), "child_seconds": 35,
    "production_edits": [PRODUCTION], "extraction_OCR_render_network_model_GPU_retries": 0,
}
OLD_PROFILE_KEYS = (
    "bes-9m10-statement-cells.v1", "bes-q111-statement-cells.v1",
    "bes-fy2010-statement-cells.v1", "bes-annual2010-statements-notes.v1",
)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def support_paths():
    return [p for p in REVIEW.rglob("*") if p.is_file()] + [
        Path(__file__), Path(cases.__file__), ROOT / PLAN, ROOT / FIXTURE,
        ROOT / "tests/prospectus_successor/test_annual_capital_statement_cells.py",
        BASE / "proposals/2010-capital-product-190.json",
        BASE / "proposals/2010-capital-product-190-review.json",
        BASE / "closure-routes-2026-10-17-2010-capital-product-190.json",
    ]


def storage():
    history = read(BASE / "reviews/2010-capital-notes-189/history.json")
    new = sum(p.stat().st_size for p in set(support_paths()) if p.is_file())
    new += sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file())
    return {"previous_seconds": history["previous_seconds"],
            "previous_bytes": history["previous_bytes"], "new_bytes": new,
            "combined_bytes": history["previous_bytes"] + new}


def save(name, value, failure=False):
    path = HERE / name
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    data = gzip.compress(raw, mtime=0) if path.suffix == ".gz" else raw + b"\n"
    state = storage()
    reserve = 0 if failure else SELECTOR["reserve_bytes"]
    require(state["new_bytes"] + len(data) < SELECTOR["new_bytes"] - reserve and
            state["combined_bytes"] + len(data) < SELECTOR["combined_bytes"] - reserve,
            "Capital-product retained storage ceiling exceeded")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def old_package_and_history():
    history = read(BASE / "reviews/2010-capital-notes-189/history.json")
    old_source = history["protected"][PRODUCTION]
    snapshot = HERE / "baseline/statement_cells.py"
    require(file_hash(snapshot) == old_source, "Old adapter snapshot differs from sealed source010 history")
    package = cases.legacy.package_files(ROOT / "src/legalmath")
    old = history["package"]
    relative = PRODUCTION.removeprefix("src/legalmath/")
    require(set(package) == set(old) and package[relative] != old[relative],
            "The live adapter must be the reviewed production transition")
    require(all(package[name] == value for name, value in old.items() if name != relative),
            "Unreviewed production package change")
    for path, value in history["protected"].items():
        if path == PRODUCTION:
            continue
        require(file_hash(ROOT / path) == value, "Historical source changed: " + path)
    return history, old_source, package


def bindings():
    authority = Authority(ROOT)
    program, tasks, _ = authority.spec()
    task = tasks["source-bes-dep-09"]
    admission = read(HERE / "admission.json")
    event = next(e for e in reversed(authority.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT)) and
            task.get("capital_product") == SELECTOR and admission["task_spec"] == task and
            admission["program_sha256"] == digest(program) and admission["binding"] == authority.binding(task),
            "Current unchanged capital-product admission required")
    require(not (HERE / "outputs.json").exists(), "Capital-product attempt already sealed")
    old_package_and_history()
    if (HERE / "frozen-methods.json").exists():
        frozen = read(HERE / "frozen-methods.json")
        require(all(file_hash(ROOT / p) == h for p, h in frozen["live"].items()), "Frozen live method changed")
        require(all(file_hash(Path(p)) == h for p, h in frozen["attempt"].items()), "Frozen attempt method changed")
    return admission


def load_baseline_module():
    spec = importlib.util.spec_from_file_location(
        "old_statement_cells", HERE / "baseline/statement_cells.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare():
    history, old_source, package = old_package_and_history()
    current = cases.legacy.package_files(ROOT / "src/legalmath")
    old = load_baseline_module()
    from legalmath.prospectus.successor import statement_cells
    require(all(statement_cells.PROFILES[k] == old.PROFILES[k] for k in OLD_PROFILE_KEYS),
            "Existing release/annual profiles changed")
    retained = read(ROOT / FIXTURE)
    graph, reading = retained["graph"], retained["reading"]
    selected = sorted(graph["units"], key=lambda u: (u["page"], u["order"], u["id"]))
    require(len(selected) == cases.OCCURRENCES and digest(selected) == statement_cells.PROFILES[cases.PROFILE]["pages_digest"],
            "Combined fixture geometry differs")
    require(digest(reading) == statement_cells.PROFILES[cases.PROFILE]["reading"],
            "Combined fixture reading differs")
    cap = read(SOURCE / "attempt-010/profile.json"); analysis = read(SOURCE / "attempt-010/analysis.json")
    require(reading["capital_notes"]["profile"] == cap and reading["capital_notes"]["analysis"] == analysis,
            "Capital-note reading was changed while combining")
    require(set(u["page"] for u in selected) == set(SELECTOR["source_pages"]), "Combined page scope differs")
    annual_pages = {92, 93, 94, 95, 96, 114, 129, 130}
    capital_pages = {108, 109, 158, 159, 160, 161}
    require(not ({u["id"] for u in selected if u["page"] in annual_pages} &
                 {u["id"] for u in selected if u["page"] in capital_pages}), "Source scopes overlap")
    save("combined-fixture.json.gz", retained)
    save("old-source-manifest.json", {"path": PRODUCTION, "sha256": old_source,
         "snapshot": "baseline/statement_cells.py", "transition": "optional v2 profile only"})
    save("frozen-methods.json", {"live": {PRODUCTION: file_hash(ROOT / PRODUCTION),
         "tests/prospectus_successor/fixtures/bes_annual2010_statement_cells_v2.json.gz": file_hash(ROOT / FIXTURE)},
         "attempt": {str(p.relative_to(HERE)): file_hash(p) for p in
                      [HERE / "baseline/statement_cells.py", HERE / "baseline/statement-cells.md"]}})
    save("final-package.json", current)
    save("prepared.json", {"old_source_sha256": old_source, "new_source_sha256": current[PRODUCTION.removeprefix("src/legalmath/")],
         "package_files": len(current), "source_occurrences": cases.OCCURRENCES,
         "old_profiles_unchanged": True, "capital_profile_exact": True,
         "previous_seconds": history["previous_seconds"], "previous_bytes": history["previous_bytes"]})
    return {"production_files": len(package), "changed_production_files": 1,
            "source_occurrences": cases.OCCURRENCES, "old_profiles_unchanged": True}


def focused():
    with (HERE / "focused.log").open("xb") as log, redirect_stdout(log), redirect_stderr(log):
        import pytest
        code = int(pytest.main(["-q", "-p", "no:cacheprovider", "--junitxml=" + str(HERE / "focused.xml"),
            "tests/prospectus_successor/test_statement_cells.py",
            "tests/prospectus_successor/test_annual_statement_cells.py",
            "tests/prospectus_successor/test_annual_capital_statement_cells.py",
            "tests/prospectus_successor/test_report_integrity.py"]))
    require(code == 0, "Focused annual/capital/report regression failed")
    return {"pytest_exit": code, "capital_profile_tests": True}


def composition():
    candidate = read(HERE / "candidate-answer.json")
    baseline, refs = cases.complete010()
    require(candidate["complete_composed_sha256"] == refs["complete_composed_answer_sha256"],
            "Complete010 composition identity differs")
    return {"complete010_baseline_equal": True, "candidate_composed_equal": True,
            "baseline_sha256": authority_digest(baseline), "composition_sha256": refs["complete_composed_answer_sha256"]}


def command(stage):
    env_path = Path(read(BASE / "reviews/2010-annual-resume-188/history.json")["build_environment"]["path"])
    python = str(env_path / "bin/python")
    if stage == "wheel":
        return [python, "-I", "-B", "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--no-index",
                "--wheel-dir", str(HERE / "wheel"), str(HERE / "build-source")]
    if stage == "install":
        wheel = read(HERE / "built-wheel.json")
        require(file_hash(HERE / wheel["path"]) == wheel["sha256"], "Wheel changed")
        return [python, "-I", "-B", "-m", "pip", "install", "--no-deps", "--no-index", "--no-compile",
                "--target", str(HERE / "installed"), str(HERE / wheel["path"])]
    return [python, "-I", "-B", str(ROOT / "scripts/prospectus_2010_capital_product_cases.py"),
            str(ROOT), str(HERE), stage.removeprefix("installed-")]


def child(stage):
    if stage == "wheel":
        build = HERE / "build-source"
        build.mkdir()
        shutil.copyfile(ROOT / "pyproject.toml", build / "pyproject.toml")
        shutil.copytree(ROOT / "src/legalmath", build / "src/legalmath",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        require(cases.legacy.package_files(build / "src/legalmath") == read(HERE / "final-package.json"),
                "Copied package differs")
    elif stage == "install":
        require(not (HERE / "installed").exists(), "Existing installation target refused")
    argv = command(stage)
    env = {"CUDA_VISIBLE_DEVICES": "-1", "PYTHONPATH": "", "PYTHONNOUSERSITE": "1",
           "PYTHONDONTWRITEBYTECODE": "1", "PIP_NO_INDEX": "1",
           "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_CACHE_DIR": "1", "PIP_CONFIG_FILE": "/dev/null"}
    target = HERE / "commands" / stage
    save("commands/" + stage + "/command.json", {"argv": argv, "cwd": str(HERE), "environment": env,
         "timeout": 35, "reservation": CHILDREN.index(stage) + 1,
         "build_backend_internal_processes_counted": False})
    target.mkdir(parents=True, exist_ok=True)
    tick = time.monotonic()
    with (target / "stdout").open("xb") as out, (target / "stderr").open("xb") as err:
        result = subprocess.run(argv, cwd=HERE, env={**os.environ, **env}, stdout=out, stderr=err, timeout=35)
    save("commands/" + stage + "/result.json", {"returncode": result.returncode,
         "wall_seconds": time.monotonic() - tick})
    require(result.returncode == 0, "Capital-product child failed: " + stage)
    if stage == "wheel":
        wheel, = (HERE / "wheel").glob("*.whl")
        with zipfile.ZipFile(wheel) as archive:
            content = {p.removeprefix("legalmath/"): hashlib.sha256(archive.read(p)).hexdigest()
                       for p in archive.namelist() if p.startswith("legalmath/") and not p.endswith("/")}
        require(content == read(HERE / "final-package.json"), "Wheel package differs")
        save("built-wheel.json", {"path": str(wheel.relative_to(HERE)), "sha256": file_hash(wheel),
             "package_files": len(content)})
    elif stage == "install":
        require(cases.legacy.package_files(HERE / "installed/legalmath") == read(HERE / "final-package.json"),
                "Installed package differs")
    else:
        action = stage.removeprefix("installed-")
        require(read(HERE / ("installed-" + action + ".json"))["status"] == "PASS",
                "Installed comparison did not pass")
    return {"command": stage, "returncode": result.returncode}


def seal():
    require((HERE / "RESULT.md").is_file(), "Actual result review required")
    for name in cases.INPUT_GROUPS:
        values = read(HERE / (name + ".json"))
        require(set(values) == set(cases.INPUT_GROUPS[name]) and all(v["refused"] for v in values.values()),
                "Missing input controls: " + name)
    for name in cases.PHASE_GROUPS:
        values = read(HERE / (name + ".json"))
        require(set(values) == set(cases.PHASE_GROUPS[name]) and all(v["refused"] for v in values.values()),
                "Missing phase controls: " + name)
    for action in ("candidate-products", "candidate-answer", "input-a", "input-b", "input-c", "input-d",
                   "phase-a", "phase-b", "phase-c"):
        require(read(HERE / ("installed-" + action + ".json"))["status"] == "PASS",
                "Missing installed check: " + action)
    require(read(HERE / "candidate-answer.json")["complete010_protected_equal"], "Complete010 answer changed")
    save("verified-result.json", {"actual_product_consumption": True, "offline_installed_consumption": True,
         "production_transition": "optional v2 only", "new_extractions": 0,
         "actual_public_refusals": sum(len(v) for v in cases.INPUT_GROUPS.values()) + sum(len(v) for v in cases.PHASE_GROUPS.values()),
         "candidate": read(HERE / "candidate-answer.json"), "composition": read(HERE / "composition.json"),
         "result_note_sha256": file_hash(HERE / "RESULT.md"), "independent_acceptance": False,
         "task_complete": False})
    return {"actual_product_consumption": True, "offline_installed_consumption": True, "task_complete": False}


def run(stage):
    with Authority(ROOT).lock():
        admission = bindings()
        index = STAGES.index(stage)
        require({p.parent.name for p in (HERE / "stages").glob("*/started.json")} ==
                {p.parent.name for p in (HERE / "stages").glob("*/result.json")} == set(STAGES[:index]),
                "Repeated/skipped/interrupted capital-product stage")
        rows = [read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < 50 for r in rows),
                "Failed capital-product predecessor")
        spent, before = sum(r["wall_seconds"] for r in rows), storage()
        def within(state, elapsed=0):
            return (spent + elapsed < SELECTOR["new_seconds"] and
                    state["previous_seconds"] + spent + elapsed < SELECTOR["combined003_onward_seconds"] and
                    state["new_bytes"] < SELECTOR["new_bytes"] - SELECTOR["reserve_bytes"] and
                    state["combined_bytes"] < SELECTOR["combined003_onward_bytes"] - SELECTOR["reserve_bytes"])
        require(within(before), "Cumulative capital-product bounds exhausted")
        save("stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
             "command": ["timeout", "55", ".venv/bin/python", "-m", "scripts.prospectus_2010_capital_product", stage],
             "git_commit": admission["git_commit"], "python": sys.executable,
             "cpu_gpu": "CPU only; GPU devices intentionally hidden", "random_seeds": "N/A deterministic",
             "data_version": "source09 attempt003 plus sealed010 and combined v2 fixture", "plan": PLAN,
             "result": str((HERE / "RESULT.md").relative_to(ROOT))})
        tick, details, error = time.monotonic(), None, None
        def expire(*_): raise TimeoutError("Capital-product stage/cumulative bound; no unchanged retry")
        old_signal = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(45, SELECTOR["new_seconds"] - spent,
                                                  SELECTOR["combined003_onward_seconds"] - before["previous_seconds"] - spent))
        try:
            commands = [command(stage)] if stage in CHILDREN else []
            with execution_guard(commands) as guard:
                if stage in CHILDREN: details = child(stage)
                elif stage == "prepare": details = prepare()
                elif stage == "focused": details = focused()
                elif stage == "composition": details = composition()
                elif stage == "seal": details = seal()
                else:
                    details = cases.dispatch(stage)
            require(guard.result() == {"starts": len(commands), "blocked": 0}, "Unexpected process/network action")
            if stage not in {"prepare", "focused", "composition", "seal"}:
                save("checks/" + stage + ".json", details)
            bindings()
            require(time.monotonic() - tick < 50 and within(storage(), time.monotonic() - tick),
                    "Capital-product cumulative bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, failure=True)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_signal)
        result = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error,
                  "details": details, "wall_seconds": time.monotonic() - tick,
                  "bounds": storage(), "timing_scope": "Stage body and final identity verification; excludes startup/final receipt writing"}
        result["cumulative_seconds"] = spent + result["wall_seconds"]
        save("stages/" + stage + "/result.json", result, failure=bool(error))
        if error or stage == "seal":
            save("result.json", {**result, "task": "source-bes-dep-09", "task_complete": False,
                 "whole_program_complete": False, "independent_legal_acceptance": False}, failure=bool(error))
            save("outputs.json", cases.legacy.package_files(HERE), failure=bool(error))
        print(json.dumps({k: result[k] for k in ("stage", "status", "error", "wall_seconds", "cumulative_seconds")}))
        return int(error is not None)


def installed_main():
    root, folder, action = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    require(sys.flags.isolated == 1, "Isolated interpreter required")
    sys.path.insert(0, str(folder / "installed"))
    cases.configure(root, folder)
    def block(event, args):
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.fork", "os.posix_spawn", "os.exec"}:
            raise RuntimeError("Installed capital-product worker forbids network/native processes: " + event)
    sys.addaudithook(block)
    expected = read(folder / "final-package.json")
    package = (folder / "installed/legalmath").resolve()
    require(cases.legacy.package_files(package) == expected, "Installed package differs")
    result = cases.dispatch(action)
    modules = {}
    for name, module in list(sys.modules.items()):
        if name == "legalmath" or name.startswith("legalmath."):
            path = Path(module.__file__).resolve()
            require(path.is_relative_to(package), "Checkout import: " + name)
            require(cases.sha(path) == expected[str(path.relative_to(package))], "Loaded module differs")
            modules[name] = str(path)
    require(cases.legacy.package_files(package) == expected, "Installed package drift")
    cases.save("installed-" + action + ".json", {"status": "PASS", "details": result,
         "python": sys.executable, "isolated": sys.flags.isolated, "modules": modules,
         "sys_path": sys.path, "package_files": len(expected), "native_calls": 0})
    print(json.dumps({"status": "PASS", "action": action, "package_files": len(expected)}))


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[3] in {s.removeprefix("installed-") for s in STAGES if s.startswith("installed-")}: 
        installed_main()
    else:
        run(sys.argv[1])
