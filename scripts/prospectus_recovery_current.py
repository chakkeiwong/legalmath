"""Bounded complete recovery with compact isolated-probe serialization."""
import argparse
from copy import deepcopy
import gzip
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read, write
from legalmath.prospectus.successor import process_ledger
from scripts.prospectus_native_campaign import bounded_stage

BASE = "docs/implementation/prospectus-execution-authority"
OLD = BASE + "/attempts/recovery/attempt-009"
REVIEW = BASE + "/reviews/current-recovery-247-r3"
FAILED_REVIEW = BASE + "/reviews/current-recovery-247"
FAILED_TEST_REVIEW = BASE + "/reviews/current-recovery-247-r2"
ORIGINAL_REVIEW = BASE + "/reviews/compact-recovery-198"
PROBE = "scripts/prospectus_recovery_probe.py"
TEST = "tests/prospectus/test_recovery_current.py"
SCRIPT = "scripts/prospectus_recovery_current.py"
PLAN = "docs/plans/prospectus-current-recovery-2026-10-18.md"
STATES = ("baseline", "environment-changed", "model-missing", "model-restored",
          "correction-image-wrong", "correction-restored", "correction-map-wrong", "final-restored")
STAGES = ("init", *STATES, "tests", "seal")
SELECTOR = {"version": "current-recovery.v2", "stages": list(STAGES), "work_seconds": 185, "stage_seconds": 190,
    "execution_seconds": 1600, "acceptance_reserve_seconds": 120, "preparation_seconds": 60, "parent_starts": 28, "native_probe_starts": 28, "prepacking_bytes": 256 * 1024**2, "packed_bytes": 96 * 1024**2,
    "workspace_bytes": 2 * 1024**3, "unchanged_retries": 0}


def require(value, message):
    if not value:
        raise ValueError(message)


def files(folder):
    return {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*"))
        if p.is_file() and p.name != "outputs.json" and "__pycache__" not in p.parts}


def storage(folder):
    unique, logical = {}, 0
    for path in folder.rglob("*"):
        require(not path.is_symlink(), "Recovery evidence symlink refused")
        if path.is_file():
            st = path.stat(); logical += st.st_size; unique[st.st_dev, st.st_ino] = st.st_size
    return {"logical_bytes": logical, "unique_bytes": sum(unique.values())}


def charged_storage(folder):
    parents = [folder, ROOT / REVIEW, ROOT / FAILED_REVIEW, ROOT / FAILED_TEST_REVIEW, ROOT / SCRIPT, ROOT / PLAN, ROOT / PROBE,
        ROOT / "tests/prospectus/test_recovery_current.py",
        ROOT / BASE / "proposals/current-recovery-247.json",
        ROOT / BASE / "proposals/current-recovery-247-review.json",
        ROOT / BASE / "closure-routes-2026-10-18-current-recovery-247.json",
        ROOT / BASE / "proposals/current-recovery-247-r2.json",
        ROOT / BASE / "proposals/current-recovery-247-r2-review.json",
        ROOT / BASE / "closure-routes-2026-10-18-current-recovery-247-r2.json",
        ROOT / BASE / "proposals/current-recovery-247-r3.json",
        ROOT / BASE / "proposals/current-recovery-247-r3-review.json",
        ROOT / BASE / "closure-routes-2026-10-18-current-recovery-247-r3.json",
        ROOT / BASE / "revisions/0247.json"]
    unique, logical = {}, 0
    for parent in parents:
        for path in (parent.rglob("*") if parent.is_dir() else [parent]):
            require(not path.is_symlink(), "Recovery charged evidence symlink refused")
            if path.is_file():
                st = path.stat(); logical += st.st_size; unique[st.st_dev, st.st_ino] = st.st_size
    return {"logical_bytes": logical, "unique_bytes": sum(unique.values())}


def save(folder, name, value, *, final=False):
    data = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    if name.endswith(".gz"):
        data = gzip.compress(data, mtime=0)
    require(charged_storage(folder)["unique_bytes"] + len(data) < (256 if final else 252) * 1024**2, "Recovery evidence limit")
    path = folder / name; path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def load(path):
    spec = importlib.util.spec_from_file_location("retained_recovery_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def command(name, stage):
    return [".venv/bin/python", "-m", SCRIPT.removesuffix(".py").replace("/", "."), "run", "--attempt", name, "--stage", stage]


def driver(folder):
    module = load(ROOT / OLD / "run_recovery.py")
    module.HERE = folder
    module.ROOT = ROOT
    name = str(folder.relative_to(ROOT))
    def retained_save(relative, value):
        if relative == "started.json":
            value["historical_plan_file"] = value["plan_file"]
            value["plan_file"] = PLAN
            value["command_template"] = command(name, "STAGE")
            extra = [SCRIPT, PLAN, PROBE, TEST, REVIEW + "/history.json",
                ORIGINAL_REVIEW + "/run_tests.py", ORIGINAL_REVIEW + "/probe.py", "tests/prospectus/test_recovery_compact.py",
                "scripts/prospectus_native_campaign.py", "tests/prospectus_successor/test_closure_program.py",
                "tests/prospectus_successor/test_closure_correction_images.py"]
            extra += [str(p.relative_to(ROOT)) for p in (ROOT / "src/legalmath").rglob("*")
                if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
            for path in extra:
                value["methods"][path] = file_hash(ROOT / path)
        if relative.startswith("steps/") and relative.endswith("/result.json"):
            value["command"] = command(name, value["state"])
        save(folder, relative, value)
    module.save = retained_save
    return module


def pack(folder):
    before = files(folder)
    retained = {}
    linked = 0
    for name, hashed in before.items():
        path = folder / name
        if hashed in retained:
            original = retained[hashed]
            require(path.read_bytes() == original.read_bytes(), "Packing collision")
            replacement = path.with_name(path.name + ".packing-link")
            os.link(original, replacement); os.replace(replacement, path)
            linked += 1
        else:
            retained[hashed] = path
    require(files(folder) == before, "Packing changed recovery bytes")
    usage = charged_storage(folder)
    require(usage["unique_bytes"] < 92 * 1024**2, "Recovery packed evidence limit")
    save(folder, "packing.json", {**usage, "linked": linked, "paths_and_bytes_preserved": True,
        "ordinary_checkout_may_expand_hard_links": True})


def run(name, stage):
    a = Authority(ROOT)
    with a.lock():
        folder = a.path(name)
        require(folder.parent == a.base / "attempts/recovery", "Wrong recovery attempt")
        program, tasks, _ = a.spec(); task = tasks["recovery"]
        admitted = read(folder / "admission.json")
        event = next(e for e in reversed(a.events()) if e.get("task") == "recovery")
        require(task.get("current_recovery") == SELECTOR and not task.get("validator") and
            event["kind"] == "ADMIT" and event["attempt"] == name and
            admitted["program_sha256"] == digest(program) and admitted["task_spec"] == task and
            admitted["binding"] == a.binding(task), "Current unchanged recovery admission required")
        require(not (folder / "outputs.json").exists() and not (folder / "result.json").exists(), "Sealed recovery attempt")
        index = STAGES.index(stage)
        require({p.parent.name for p in (folder / "stages").glob("*/started.json")} ==
                {p.parent.name for p in (folder / "stages").glob("*/result.json")} == set(STAGES[:index]),
                "Skipped/repeated/interrupted recovery stage")
        previous = [read(folder / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" for r in previous), "Failed recovery predecessor")
        spent = read(ROOT / REVIEW / "preparation.json")["seconds"] + sum(r["wall_seconds"] for r in previous)
        require(spent + 120 < 1600, "Recovery execution bound exhausted")
        save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
            "command": command(name, stage), "git_commit": admitted["git_commit"], "python": sys.executable,
            "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic recovery",
            "input_binding_sha256": digest(admitted["binding"]),
            "input_binding_file": name + "/admission.json", "plan": PLAN, "result": name + "/result.json"})
        tick, details, error = time.monotonic(), None, None
        try:
            with bounded_stage(min(185, 1600 - 120 - spent)):
                frozen(task)
                if stage == "init":
                    for helper in ("probe.py", "run_tests.py", "finalize_recovery.py"):
                        source = ROOT / PROBE if helper == "probe.py" else ROOT / ORIGINAL_REVIEW / helper if helper == "run_tests.py" else ROOT / OLD / helper
                        shutil.copyfile(source, folder / helper)
                    shutil.copyfile(ROOT / PLAN, folder / "WORK-PLAN.md")
                    process_ledger.create(folder / "parent-ledger.json", 28, 0,
                        "Incremental current recovery parent starts; preceding unmeasured history UNKNOWN")
                    with process_ledger.observe(folder / "parent-ledger.json"):
                        driver(folder).init()
                    checked_parent(folder, 3)
                    details = {"states": list(STATES), "original_helpers": OLD, "probe_accounting": PROBE}
                elif stage in STATES:
                    with process_ledger.observe(folder / "parent-ledger.json"):
                        driver(folder).step(stage)
                    checked_parent(folder, 3 + 3 * (STATES.index(stage) + 1))
                    capture_probe_ledgers(folder, stage)
                    details = read(folder / "steps" / stage / "result.json")
                elif stage == "tests":
                    argv = [sys.executable, str(folder / "run_tests.py")]
                    with process_ledger.observe(folder / "parent-ledger.json"), (folder / "focused-stdout").open("xb") as out, (folder / "focused-stderr").open("xb") as err:
                        result = subprocess.run(argv, cwd=ROOT, stdout=out, stderr=err, timeout=110)
                    require(result.returncode == 0 and read(folder / "tests-result.json")["status"] == "PASS", "Recovery focused tests failed")
                    checked_parent(folder, 28)
                    details = {"argv": argv, "returncode": result.returncode, "result": read(folder / "tests-result.json")}
                else:
                    process_check = check_processes(folder)
                    (folder / "RESULT.md").write_text(
                        "# Current eight-state recovery\n\n"
                        "All eight original states passed actual closure-executor versus clean complete recomputation, "
                        "specific missing-model/wrong-image/wrong-map refusals, pre-marker invalidation, unchanged reuse and exact restoration. "
                        "Original Portuguese source units and page images remain bound. The production package stayed frozen.\n\n"
                        "| Decision | Primary criterion | Veto | Uncertainty | Next action | Limit |\n| --- | --- | --- | --- | --- | --- |\n"
                        "| Submit recovery evidence | Eight full comparisons and original refusals pass | No source/method/order/resource veto | Shared consumer can share semantic error | Separate unchanged-validator acceptance,refresh,authority audit | Finite same-host recovery only |\n\n"
                        "Post-run red team: this establishes recovery consistency, not independent legal truth. Unseen source/domain coverage remains open.\n")
                    save(folder, "process-comparison.json", process_check)
                    finalizer = load(folder / "finalize_recovery.py")
                    details = finalizer.validate()
                    save(folder, "comparison.json", details)
                    shutil.copyfile(ROOT / PLAN, folder / "plan.md")
                    shutil.copyfile(ROOT / read(folder / "started.json")["original_plan_file"], folder / "original-plan.md")
                    for path, hashed in read(folder / "started.json")["methods"].items():
                        target = folder / "method" / path
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(ROOT / path, target)
                        require(file_hash(target) == hashed, "Recovery method snapshot changed")
                    pack(folder)
                frozen(task)
                if (folder / "started.json").exists():
                    started = read(folder / "started.json")
                    require(all(file_hash(ROOT / p) == h for p, h in {**started["methods"], **started["sources"]}.items()), "Recovery methods/sources changed")
                    isolated = Path(started["isolated_root"])
                    # The fixture has its own git metadata; symlinks, if any,
                    # remain ordinary fixture files and are not retained outputs.
                    usage = sum(p.stat().st_size for p in isolated.rglob("*") if p.is_file())
                    require(usage < SELECTOR["workspace_bytes"], "Recovery isolated workspace limit")
                require(admitted["binding"] == a.binding(task) and spent + time.monotonic() - tick + 120 < 1600,
                        "Recovery admission changed or aggregate bound exceeded")
                require(charged_storage(folder)["unique_bytes"] < (92 if stage == "seal" else 252) * 1024**2,
                        "Recovery charged storage bound exceeded")
            require(time.monotonic() - tick < 190, "Recovery recorded stage bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save(folder, "stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, final=True)
        result = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error,
            "details": details, "wall_seconds": time.monotonic() - tick}
        save(folder, "stages/" + stage + "/result.json", result, final=True)
        if error or stage == "seal":
            save(folder, "result.json", {**result, "task": "recovery", "scope": "CURRENT_FINITE_RECOVERY",
                "whole_program_complete": False, "independent_legal_acceptance": False}, final=True)
            save(folder, "outputs.json", files(folder), final=True)
        print(json.dumps({k: result[k] for k in ("stage", "status", "error", "wall_seconds")}))
        return int(error is not None)


def methods():
    names = {str(p.relative_to(ROOT)) for p in (ROOT / "src/legalmath").rglob("*")
             if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    names |= {SCRIPT, PLAN, PROBE, TEST, "scripts/prospectus_native_campaign.py",
        "scripts/prospectus_delivery.py", "pyproject.toml",
        "tests/prospectus/test_recovery_compact.py", "tests/prospectus_successor/test_closure_program.py",
        "tests/prospectus_successor/test_closure_correction_images.py",
        *(OLD + "/" + n for n in ("run_recovery.py", "finalize_recovery.py")),
        *(ORIGINAL_REVIEW + "/" + n for n in ("probe.py", "run_tests.py"))}
    return {n: file_hash(ROOT / n) for n in sorted(names)}


def selector(task):
    require(task.get("id") == "recovery" and task.get("handler") == "agent"
        and task.get("current_recovery") == SELECTOR and not task.get("validator")
        and not task.get("evidence_attempt"), "Wrong current recovery selector")


def frozen(task):
    selector(task)
    value = read(ROOT / REVIEW / "frozen.json")
    require(value["methods"] == methods(), "Recovery current methods changed")
    require(value["inputs"] == {n: file_hash(ROOT / n) for n in value["inputs"]}, "Recovery current inputs changed")
    from scripts.prospectus_component_revalidation import package_files
    donor = ROOT / BASE / "attempts/source-bes-dep-06/attempt-013"
    require(value["package"] == package_files(ROOT / "src/legalmath")
            == package_files(donor / "installed/legalmath"), "Recovery frozen package changed")
    return value


def checked_parent(folder, expected):
    value = process_ledger.checked(folder / "parent-ledger.json")
    require(value["limit"] == 28 and value["historical_lower_bound"] == 0
        and len(value["reservations"]) == expected
        and all(r["state"] == "STARTED" for r in value["reservations"]), "Recovery parent accounting differs")
    return value["reservations"]


def capture_probe_ledgers(folder, state):
    started = read(folder / "started.json"); isolated = Path(started["isolated_root"])
    step = folder / "steps" / state
    phase = isolated / read(step / "executor-receipt.json")["directory"]
    for source, name in ((phase / "assessment.json.processes.json", "actual-processes.json"),
                         (isolated / "clean" / (state + ".json.processes.json"), "clean-processes.json")):
        require(not (step / name).exists(), "Recovery native ledger already retained")
        process_ledger.checked(source)
        shutil.copyfile(source, step / name)
    check_probe_state(folder, state)


def check_probe_state(folder, state):
    isolated = Path(read(folder / "started.json")["isolated_root"])
    count = 0 if state == "model-missing" else 2
    expected = [] if not count else [
        ["pdftotext", "-bbox-layout", "-enc", "UTF-8",
         str(isolated / "docs/implementation/prospectus-integration-closure/inputs/R0/cases/portuguese/source.pdf"), "-"],
        ["/home/chakwong/miniconda3/envs/tfgpu/bin/python", str(isolated / "src/legalmath/prospectus/successor/ocr_worker.py")]]
    for name in ("actual-processes.json", "clean-processes.json"):
        value = process_ledger.checked(folder / "steps" / state / name)
        require(value["limit"] == 2 and value["historical_lower_bound"] == 0
            and [r["argv"] for r in value["reservations"]] == expected
            and all(r["state"] == "STARTED" for r in value["reservations"]), "Recovery native command accounting differs")
    return 2 * count


def check_processes(folder):
    rows = checked_parent(folder, 28)
    isolated = Path(read(folder / "started.json")["isolated_root"])
    python = read(folder / "started.json")["environment"]
    expected = [
        ["git", "init", "-q", str(isolated)],
        ["git", "-c", "user.name=Recovery fixture", "-c", "user.email=fixture@invalid", "commit", "--allow-empty", "-qm", "Isolated recovery comparator"],
        ["git", "rev-parse", "HEAD"]]
    native_count = 0
    for state in STATES:
        step = folder / "steps" / state
        expected.extend([["git", "rev-parse", "HEAD"], read(step / "phase-started.json")["argv"],
                         read(step / "clean-command.json")["argv"]])
        native_count += check_probe_state(folder, state)
    expected.append([python, str(folder / "run_tests.py")])
    require([r["argv"] for r in rows] == expected and native_count == 28, "Recovery complete process denominator differs")
    child = read(folder / "tests-command.json")
    require(child["argv"][:4] == [python, "-m", "pytest", "-q"] and child["timeout_seconds"] == 110,
            "Recovery focused child differs")
    return {"parent_starts": 28, "focused_pytest_child": 1, "native_probe_starts": 28,
        "preceding_unmeasured_recovery_processes": "UNKNOWN", "count_scope": "supervised Popen only; native library internals excluded"}


def preparation():
    tick = time.monotonic(); auth = Authority(ROOT); old, tasks, _ = auth.spec()
    require(old["revision"] == 246, "Wrong current recovery preparation baseline")
    folder = ROOT / REVIEW; folder.mkdir(parents=True, exist_ok=False)
    failed_seconds = sum(read(ROOT / n / "failure.json")["seconds"] for n in (FAILED_REVIEW, FAILED_TEST_REVIEW))
    write(folder / "started.json", {"at": datetime.now(timezone.utc).isoformat(),
        "command": [".venv/bin/python", "-m", "scripts.prospectus_recovery_current", "prepare"]}, exclusive=True)
    try:
        with bounded_stage(max(1, 60 - failed_seconds - (time.monotonic() - tick))):
            events = auth.events(); current = []
            for name, number in (("native-binding", "023"), ("native-confinement", "014")):
                event = next(e for e in reversed(events) if e.get("task") == name)
                require(event["kind"] == "ACCEPT" and event["attempt"].endswith("attempt-" + number)
                        and auth.attempt_valid(event, tasks[name]), "Current runtime prerequisite not accepted")
                current.append(event)
            admissions = [e for e in events if e["kind"] == "ADMIT" and e["budget_key"] == "recovery"]
            require(len(admissions) == old["budgets"]["recovery"]["maximum_new_attempts"] == 17, "Recovery cumulative history differs")
            retained = []
            for admission in admissions:
                event = next(e for e in reversed(events) if e.get("attempt") == admission["attempt"])
                require(event["kind"] in {"RECORD", "REJECT", "ACCEPT"} and auth.retained_evidence_valid(event),
                        "Retained recovery attempt changed")
                retained.append(event)
            original = read(ROOT / OLD / "started.json")
            require(original["states"] == list(STATES) and all(file_hash(ROOT / n) == h for n, h in original["sources"].items()),
                    "Original recovery source/state changed")
            from scripts.prospectus_component_revalidation import package_files
            donor = ROOT / BASE / "attempts/source-bes-dep-06/attempt-013"
            package = package_files(ROOT / "src/legalmath")
            require(len(package) == 452 and package == read(donor / "source-package.json")
                    == package_files(donor / "installed/legalmath"), "Current recovery package differs")
            write(folder / "REVIEW.json", {"verdict": "PASS", "plan": PLAN,
                "baseline": "Original Portuguese units/images and synthetic correction; unchanged actual/clean comparator",
                "proxy_audit": "Full products/refusals/invalidation/restoration are primary; tests/time only explanatory",
                "defaults": "Finite cohort,same host,compact complete JSON,current frozen452-file package",
                "stop": SELECTOR, "process_review": "Exact parent/probe ledgers; prior unmeasured recovery starts remain UNKNOWN",
                "stale_context": "Original child70s unchanged; current stage185s allows two children and serialization",
                "storage_repair": {"failed_preflight": FAILED_REVIEW, "forecast_bytes": 72539562,
                    "cause": "Current complete program/history exceeds old64MiB cap before source execution",
                    "revision": "96MiB packed includes failed preparation and4MiB failure reserve; no history removed",
                    "combined_preparation_ceiling": 60, "source_retries": 0},
                "test_fixture_repair": "Move failed-start assertions back to their ledger fixture; preserve r2 failure; one targeted test rerun; all costs charged",
                "scope": "Recovery consistency only; independent source/legal/domain coverage remains"}, exclusive=True)
            command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", TEST,
                       "tests/prospectus/test_recovery_compact.py", "--junitxml=" + str(folder / "tests.xml")]
            with (folder / "tests.log").open("xb") as out:
                result = subprocess.run(command, cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
                    stdout=out, stderr=subprocess.STDOUT, timeout=max(1, 50 - failed_seconds - (time.monotonic() - tick)))
            require(result.returncode == 0, "Current recovery preparation tests failed")
            from legalmath.prospectus.execution_acceptance import checked_tests
            count = checked_tests(folder / "tests.xml", 1)
            write(folder / "history.json", {"events": retained, "current_prerequisites": current,
                "original_sources": original["sources"], "preceding_unmeasured_processes": "UNKNOWN",
                "timing_scope": "Do not sum overlapping stage/state clocks or copied evidence"}, exclusive=True)
            task = tasks["recovery"]; inputs = set(task["inputs"]) | set(original["sources"]) | set(original["methods"])
            inputs |= {str(p.relative_to(ROOT)) for p in (ROOT / FAILED_REVIEW).rglob("*") if p.is_file()}
            inputs |= {str(p.relative_to(ROOT)) for p in (ROOT / FAILED_TEST_REVIEW).rglob("*") if p.is_file()}
            inputs |= {BASE + "/proposals/current-recovery-247.json", BASE + "/proposals/current-recovery-247-review.json",
                       BASE + "/closure-routes-2026-10-18-current-recovery-247.json"}
            for event in retained + current:
                name = event["attempt"]
                inputs |= {name + "/outputs.json"}
                if event in retained:
                    inputs |= {name + "/" + n for n in read(ROOT / name / "outputs.json")}
            current_methods = methods()
            write(folder / "frozen.json", {"methods": current_methods,
                "inputs": {n: file_hash(ROOT / n) for n in sorted(inputs)}, "package": package}, exclusive=True)
            new = deepcopy(old); new["revision"] = 247
            updated = next(t for t in new["tasks"] if t["id"] == "recovery")
            updated["historical_accepted_recovery017"] = {"validator": updated.pop("validator"), "evidence_attempt": updated.pop("evidence_attempt")}
            updated.update(dossier=PLAN, current_recovery=SELECTOR, timeout_seconds=200,
                reason="Execute original eight current recovery states from frozen452-file build with exact process ledgers; retain17 admissions; separate unchanged-validator acceptance follows")
            write(folder / "preparation.json", {"tests": count, "test_command": command, "seconds": failed_seconds + time.monotonic() - tick,
                "failed_preparation_seconds": failed_seconds, "failed_preparation": FAILED_REVIEW,
                "retained_admissions": [e["attempt"] for e in admissions], "historical_unmeasured_seconds": "UNKNOWN"}, exclusive=True)
            updated["inputs"] = sorted(inputs | set(current_methods) | {str(p.relative_to(ROOT)) for p in folder.iterdir() if p.is_file()})
            new["budgets"]["recovery"]["maximum_new_attempts"] = 18
            routes = read(ROOT / old["continuation_review"]["routes"]); routes["baseline_revision"] = 247
            row = next(r for r in routes["tasks"] if r["task"] == "recovery")
            row.update(task_sha256=digest(updated), dossier=PLAN, phase=0, mode="local", remaining=updated["reason"],
                next_action="Execute all eight states,focused checks,seal,record/refresh; then separately admit unchanged-validator acceptance",
                stop_condition=SELECTOR)
            route_name = BASE + "/closure-routes-2026-10-18-current-recovery-247-r3.json"
            write(ROOT / route_name, routes, exclusive=True)
            new["continuation_review"].update(plan=PLAN, routes=route_name)
            for name in (PLAN, SCRIPT, PROBE, route_name): new["continuation_review"]["bindings"][name] = file_hash(ROOT / name)
            review = {"baseline": digest(old), "changes": updated["reason"], "scope_unchanged": True, "budget_unchanged": False,
                "skeptical_audit": {"verdict": "PASS", "review": REVIEW + "/REVIEW.json", "plan": PLAN},
                "evidence_contract": PLAN, "budget_revision": {"budget_key": "recovery", "previous_maximum": 17,
                    "new_maximum": 18, "retained_attempts": [e["attempt"] for e in admissions], "reason": updated["reason"],
                    "next_discriminating_check": "Original actual versus clean eight-state sequence, exact sources/refusals/restoration",
                    "stop_condition": SELECTOR, "same_scope_authorization": "Continuing authorized general build; no external opinion prerequisite"}}
            auth.validate_program(new)
            write(ROOT / BASE / "proposals/current-recovery-247-r3.json", new, exclusive=True)
            write(ROOT / BASE / "proposals/current-recovery-247-r3-review.json", review, exclusive=True)
            # Forecast from actual complete prior answers, current methods and modeled admission.
            previous = ROOT / BASE / "attempts/recovery/attempt-016"
            unique = {}; logical = 0
            for p in (previous / "steps").rglob("*"):
                if p.is_file():
                    logical += p.stat().st_size; unique[file_hash(p)] = p.stat().st_size
            model = {"task_spec": updated, "binding": auth.binding(updated), "program_sha256": digest(new)}
            admission_size = len(json.dumps(model, ensure_ascii=False, indent=2).encode()) + 16384
            support = charged_storage(auth.base / "attempts/recovery/attempt-018")["unique_bytes"]
            support += (ROOT / BASE / "proposals/current-recovery-247-r3.json").stat().st_size
            method_size = sum((ROOT / n).stat().st_size for n in set(current_methods) | set(original["methods"]))
            overhead = admission_size + support + method_size + 2 * 1024**2
            packed, prepacked = sum(unique.values()) + overhead, logical + overhead
            oldwork = Path(read(previous / "started.json")["isolated_root"])
            workspace_bytes = sum(p.stat().st_size for p in oldwork.rglob("*") if p.is_file()) + 64 * 1024**2
            forecast = {"packed_bytes": packed, "prepacked_bytes": prepacked, "workspace_bytes": workspace_bytes,
                "basis": "Prior complete16 state outputs,current admission/support/method bytes,2MiB evidence and64MiB workspace reserve"}
            write(folder / "forecast.json", forecast, exclusive=True)
            require(packed < 92 * 1024**2 and prepacked < 252 * 1024**2
                and workspace_bytes < SELECTOR["workspace_bytes"], "Current recovery storage forecast blocks admission")
            preparation_value = read(folder / "preparation.json"); preparation_value["seconds"] = failed_seconds + time.monotonic() - tick
            write(folder / "preparation.json", preparation_value)
            print(json.dumps({"prepared_revision": 247, "tests": count, "seconds": preparation_value["seconds"], "forecast": forecast}))
    except BaseException as exc:
        write(folder / "failure.json", {"error": str(exc), "seconds": time.monotonic() - tick,
            "traceback": traceback.format_exc()}, exclusive=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--attempt"); parser.add_argument("--stage", choices=STAGES)
    args = parser.parse_args()
    if args.action == "prepare":
        preparation()
    else:
        if not args.attempt or not args.stage: parser.error("--attempt and --stage required")
        raise SystemExit(run(args.attempt, args.stage))

