"""Bounded complete recovery with compact isolated-probe serialization."""
import argparse
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
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts.prospectus_native_campaign import bounded_stage

BASE = "docs/implementation/prospectus-execution-authority"
OLD = BASE + "/attempts/recovery/attempt-009"
REVIEW = BASE + "/reviews/compact-recovery-198"
SCRIPT = "scripts/prospectus_recovery_compact.py"
PLAN = "docs/plans/prospectus-compact-current-recovery-2026-10-17.md"
STATES = ("baseline", "environment-changed", "model-missing", "model-restored",
          "correction-image-wrong", "correction-restored", "correction-map-wrong", "final-restored")
STAGES = ("init", *STATES, "tests", "seal")
SELECTOR = {"version": "compact-current-recovery.v1", "stages": list(STAGES), "work_seconds": 110, "stage_seconds": 115,
    "execution_seconds": 1080, "prepacking_bytes": 256 * 1024**2, "packed_bytes": 64 * 1024**2,
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
    parents = [folder, ROOT / REVIEW, ROOT / SCRIPT, ROOT / PLAN,
        ROOT / "tests/prospectus/test_recovery_compact.py",
        ROOT / BASE / "proposals/compact-recovery-198.json",
        ROOT / BASE / "proposals/compact-recovery-198-review.json",
        ROOT / BASE / "closure-routes-2026-10-17-compact-recovery-198.json",
        ROOT / BASE / "revisions/0198.json"]
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
    return ["timeout", "120", ".venv/bin/python", "-m", SCRIPT.removesuffix(".py").replace("/", "."), "--attempt", name, "--stage", stage]


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
            extra = [SCRIPT, PLAN, REVIEW + "/history.json", REVIEW + "/prepare.py", REVIEW + "/REVIEW.md", REVIEW + "/probe.py",
                REVIEW + "/run_tests.py", "tests/prospectus/test_recovery_compact.py",
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
    require(usage["unique_bytes"] < 60 * 1024**2, "Recovery packed evidence limit")
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
        require(task.get("compact_recovery") == SELECTOR and not task.get("validator") and
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
        spent = sum(r["wall_seconds"] for r in previous)
        require(spent < 1080, "Recovery execution bound exhausted")
        save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
            "command": command(name, stage), "git_commit": admitted["git_commit"], "python": sys.executable,
            "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic recovery",
            "input_binding_sha256": digest(admitted["binding"]),
            "input_binding_file": name + "/admission.json", "plan": PLAN, "result": name + "/result.json"})
        tick, details, error = time.monotonic(), None, None
        try:
            with bounded_stage(min(110, 1080 - spent)):
                if stage == "init":
                    for helper in ("probe.py", "run_tests.py", "finalize_recovery.py"):
                        source = ROOT / REVIEW / helper if helper in ("probe.py", "run_tests.py") else ROOT / OLD / helper
                        shutil.copyfile(source, folder / helper)
                    shutil.copyfile(ROOT / PLAN, folder / "WORK-PLAN.md")
                    driver(folder).init()
                    details = {"states": list(STATES), "original_helpers": OLD, "probe_only_serialization_change": REVIEW + "/probe.py"}
                elif stage in STATES:
                    driver(folder).step(stage)
                    details = read(folder / "steps" / stage / "result.json")
                elif stage == "tests":
                    argv = [sys.executable, str(folder / "run_tests.py")]
                    with (folder / "focused-stdout").open("xb") as out, (folder / "focused-stderr").open("xb") as err:
                        result = subprocess.run(argv, cwd=ROOT, stdout=out, stderr=err, timeout=110)
                    require(result.returncode == 0 and read(folder / "tests-result.json")["status"] == "PASS", "Recovery focused tests failed")
                    details = {"argv": argv, "returncode": result.returncode, "result": read(folder / "tests-result.json")}
                else:
                    require((folder / "RESULT.md").is_file(), "Review actual recovery result before sealing")
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
                if (folder / "started.json").exists():
                    started = read(folder / "started.json")
                    require(all(file_hash(ROOT / p) == h for p, h in {**started["methods"], **started["sources"]}.items()), "Recovery methods/sources changed")
                    isolated = Path(started["isolated_root"])
                    # The fixture has its own git metadata; symlinks, if any,
                    # remain ordinary fixture files and are not retained outputs.
                    usage = sum(p.stat().st_size for p in isolated.rglob("*") if p.is_file())
                    require(usage < SELECTOR["workspace_bytes"], "Recovery isolated workspace limit")
                require(admitted["binding"] == a.binding(task) and spent + time.monotonic() - tick < 1080,
                        "Recovery admission changed or aggregate bound exceeded")
                require(charged_storage(folder)["unique_bytes"] < (60 if stage == "seal" else 252) * 1024**2,
                        "Recovery charged storage bound exceeded")
            require(time.monotonic() - tick < 115, "Recovery recorded stage bound exceeded")
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--stage", choices=STAGES, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.attempt, args.stage))
