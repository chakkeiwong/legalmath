"""Finish only the missing isolated installation checks under original bounds."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTHONPATH="", PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts import prospectus_2010_capital_resume as previous

BASE, SOURCE, OLD = previous.BASE, previous.SOURCE, previous.HERE
HERE = SOURCE / "attempt-013"
REVIEW = BASE / "reviews/2010-capital-install-192"
PLAN = "docs/plans/prospectus-2010-capital-install-2026-10-17.md"
WRAPPER = ROOT / "scripts/prospectus_2010_capital_install_case.py"
ROUTES = BASE / "closure-routes-2026-10-17-2010-capital-install-192.json"
REVIEW_FILE = BASE / "proposals/2010-capital-install-192-review.json"
PENDING = REVIEW / "proposal.pending.json"
COMPRESSED = REVIEW / "proposal.json.gz"
INSTALLED = previous.INSTALLED
STAGES = ("prepare", "install", *INSTALLED, "seal")
CHILDREN = ("install", *INSTALLED)
SELECTOR = {"version": "bes-annual2010-capital-install.v1", "stages": list(STAGES),
            "new_seconds": 300, "combined003_onward_seconds": 1960,
            "combined003_onward_bytes": 209715200, "reserve_bytes": 524288,
            "work_seconds": 45, "stage_seconds": 50, "child_seconds": 35,
            "children": list(CHILDREN), "production_edits": [], "fresh_normal_build": False,
            "comparison_attempt": str(OLD.relative_to(ROOT)),
            "extraction_OCR_render_network_model_GPU_build_git_retries": 0}
require = previous.require


def rel(path):
    return str(path.relative_to(ROOT))


def support():
    return {p for p in REVIEW.rglob("*") if p.is_file()} | {Path(__file__), WRAPPER, ROOT / PLAN, ROUTES, REVIEW_FILE}


def storage():
    history = read(REVIEW / "history.json")
    paths = support() | {p for p in HERE.rglob("*") if p.is_file()}
    return {"previous_bytes": history["previous_bytes"], "new_bytes": sum(p.stat().st_size for p in paths if p.is_file()),
            "previous_seconds": history["previous_seconds"],
            "combined_bytes": history["previous_bytes"] + sum(p.stat().st_size for p in paths if p.is_file())}


def save(name, value, failure=False):
    data = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode() + b"\n"
    require(storage()["combined_bytes"] + len(data) < SELECTOR["combined003_onward_bytes"] -
            (0 if failure else SELECTOR["reserve_bytes"]), "Original cumulative storage/reserve exhausted")
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def historical():
    """Manifest indirection retains full original validation rather than dropping inputs."""
    h = read(REVIEW / "history.json")
    h191 = read(previous.REVIEW / "history.json")
    require(file_hash(previous.REVIEW / "history.json") == h["history191_sha256"], "191 history changed")
    old = read(OLD / "admission.json")
    require(file_hash(OLD / "admission.json") == h["admission012_sha256"] and
            Authority(ROOT).binding(old["task_spec"]) == old["binding"], "Original012 input binding changed")
    require(all(file_hash(ROOT / p) == value for p, value in h191["protected"].items()), "Protected191 evidence changed")
    require(file_hash(OLD / "outputs.json") == h["outputs012_sha256"] and
            all(file_hash(OLD / p) == value for p, value in read(OLD / "outputs.json").items()), "Sealed012 output changed")
    require(all(file_hash(ROOT / p) == value for p, value in read(OLD / "final-methods.json").items()), "Frozen191 methods changed")
    require(previous.cases.legacy.package_files(ROOT / "src/legalmath") == read(OLD / "final-package.json") == h191["package"],
            "Candidate package changed")
    sizes = {**h191["historical_storage"], **h["incremental_storage_through012"]}
    require(sum(sizes.values()) == h["previous_bytes"] and
            all((ROOT / p).stat().st_size == size for p, size in sizes.items()), "Cumulative historical storage changed")
    env_ref = h191["build_environment"]
    require(file_hash(ROOT / env_ref["manifest_path"]) == env_ref["manifest_sha256"], "Environment manifest changed")
    env = read(ROOT / env_ref["manifest_path"])["build_environment"]
    require(env["path"] == env_ref["path"] and previous.cases.legacy.environment_files(Path(env["path"])) == env["files"],
            "Read-only build environment changed")
    receipts = {p.parent.name: read(p) for p in (OLD / "stages").glob("*/result.json")}
    expected = set(previous.STAGES[:previous.STAGES.index("wheel-repack")])
    require(set(receipts) == expected | {"wheel-repack"} and all(receipts[s]["status"] == "PASS" for s in expected)
            and receipts["wheel-repack"]["status"] == "FAIL" and read(OLD / "result.json")["status"] == "FAIL",
            "Actual012 outcome/predecessors differ")
    require(abs(h191["previous_seconds"] + sum(r["wall_seconds"] for r in receipts.values()) - h["previous_seconds"]) < 1e-8,
            "Cumulative timing differs")
    events = Authority(ROOT).events()
    admissions = [e for e in events if e["kind"] == "ADMIT" and e.get("budget_key") == "source-bes-dep-09"]
    require(len(h["prior_outcomes"]) == 12 and [e["attempt"] for e in admissions[:12]] ==
            [r["attempt"] for r in h["prior_outcomes"]], "Original admission history changed")
    for row in h["prior_outcomes"]:
        require(file_hash(ROOT / row["result_path"]) == row["result_sha256"] and
                read(ROOT / row["result_path"])["status"] == row["actual_status"] and
                any(e["sha256"] == row["last_event_sha256"] for e in events), "Actual historical outcome changed")
    return {"original_input_bindings": len(old["binding"]), "protected191_files": len(h191["protected"]),
            "package_files": len(h191["package"]), "environment_files": len(env["files"]),
            "prior_outcomes": 12, "completed012_stages": len(expected), "attempt012_status": "FAIL"}


def validate_wheel():
    ref = read(SOURCE / "attempt-009/built-wheel.json")
    original, candidate = SOURCE / "attempt-009" / ref["path"], OLD / "wheel/legalmath-0.1.0-py3-none-any.whl"
    require(file_hash(original) == ref["sha256"], "Original009 wheel changed")
    with zipfile.ZipFile(original) as before, zipfile.ZipFile(candidate) as after:
        record = previous.validate_record(before)
        require(previous.validate_record(after) == record and before.namelist() == after.namelist(), "Wheel inventory differs")
        require(before.testzip() is None and after.testzip() is None, "Wheel ZIP integrity failed")
        changed = [n for n in before.namelist() if before.read(n) != after.read(n)]
        require(set(changed) == {"legalmath/prospectus/successor/statement_cells.py", record}, "Undeclared wheel change")
        hashes = {n.removeprefix("legalmath/"): hashlib.sha256(after.read(n)).hexdigest()
                  for n in after.namelist() if n.startswith("legalmath/")}
        old_hashes = {n.removeprefix("legalmath/"): hashlib.sha256(before.read(n)).hexdigest()
                      for n in before.namelist() if n.startswith("legalmath/")}
        require(hashes == read(OLD / "final-package.json") and
                old_hashes == read(previous.REVIEW / "history.json")["baseline_package"], "Wheel package differs")
        uncompressed = sum(e.file_size for e in after.infolist())
    source, target = io.BytesIO(), io.BytesIO()
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("first", b"x" * 64)
        archive.writestr("second", b"y")
    with zipfile.ZipFile(source) as archive:
        info = archive.getinfo("second")
        offset_before, data = info.header_offset, archive.read("second")
        with zipfile.ZipFile(target, "w") as output:
            output.writestr(info, data)
        offset_after = info.header_offset
    require(offset_before != offset_after, "Failed to reproduce ZipInfo mutation")
    return {"status": "PASS", "candidate_path": rel(candidate), "candidate_sha256": file_hash(candidate),
            "candidate_bytes": candidate.stat().st_size, "uncompressed_bytes": uncompressed,
            "original_path": rel(original), "original_sha256": ref["sha256"], "changed_entries": changed,
            "all_RECORD_rows_valid": True, "testzip_valid": True, "package_files": len(hashes),
            "ZipInfo_mutation_reproduced": {"before": offset_before, "after": offset_after},
            "attempt012_remains": "FAIL", "diagnosis": "local verification harness metadata mutation",
            "fresh_normal_build": False}


def bindings():
    authority = Authority(ROOT)
    program, tasks, _ = authority.spec()
    task = tasks["source-bes-dep-09"]
    admission = read(HERE / "admission.json")
    event = next(e for e in reversed(authority.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == rel(HERE) and admission["task_spec"] == task and
            admission["program_sha256"] == digest(program) and admission["binding"] == authority.binding(task) and
            task["capital_install"] == SELECTOR, "Current unchanged installation admission required")
    require(not (HERE / "outputs.json").exists() and not PENDING.exists(), "Sealed attempt or unretired transport")
    retirement = read(REVIEW / "transport-retired.json")
    require(retirement["status"] == "PASS" and retirement["canonical_program_sha256"] == digest(program) and
            retirement["compressed_sha256"] == file_hash(COMPRESSED), "Proposal retirement proof differs")
    historical()
    if (HERE / "final-methods.json").exists():
        require(all(file_hash(ROOT / p) == value for p, value in read(HERE / "final-methods.json").items()), "New methods changed")
    return admission


def command(stage):
    python = str(Path(read(previous.REVIEW / "history.json")["build_environment"]["path"]) / "bin/python")
    wheel = read(REVIEW / "diagnosis.json")["wheel"]
    if stage == "install":
        return [python, "-I", "-B", "-m", "pip", "install", "--no-deps", "--no-index", "--no-compile",
                "--target", str(HERE / "installed"), str(ROOT / wheel["candidate_path"])]
    return [python, "-I", "-B", str(WRAPPER), str(ROOT), str(OLD), str(HERE), INSTALLED[stage]]


def child(stage):
    require(stage != "install" or not (HERE / "installed").exists(), "Existing installation target refused")
    argv = command(stage)
    env = {"CUDA_VISIBLE_DEVICES": "-1", "PYTHONPATH": "", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
           "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_CACHE_DIR": "1", "PIP_CONFIG_FILE": "/dev/null"}
    save("commands/" + stage + "/command.json", {"argv": argv, "cwd": str(HERE), "environment": env,
         "timeout": SELECTOR["child_seconds"], "reservation": CHILDREN.index(stage) + 1})
    folder, tick = HERE / "commands" / stage, time.monotonic()
    with (folder / "stdout").open("xb") as out, (folder / "stderr").open("xb") as err:
        result = subprocess.run(argv, cwd=HERE, env={**os.environ, **env}, stdin=subprocess.DEVNULL,
                                stdout=out, stderr=err, timeout=SELECTOR["child_seconds"])
    save("commands/" + stage + "/result.json", {"returncode": result.returncode, "wall_seconds": time.monotonic() - tick})
    require(result.returncode == 0, "Installation comparison child failed: " + stage)
    require(previous.cases.legacy.package_files(HERE / "installed/legalmath") == read(OLD / "final-package.json"),
            "Installed package differs")
    if stage != "install":
        receipt = read(HERE / "installed-checks" / (INSTALLED[stage] + ".json"))
        require(receipt["status"] == "PASS" and receipt["details"] == read(OLD / "checks" / (INSTALLED[stage] + ".json")),
                "Missing/wrong installed comparison")
    return {"command": stage, "returncode": result.returncode, "package_files": 441}


def prepare():
    wheel = validate_wheel()
    require(wheel == read(REVIEW / "diagnosis.json")["wheel"], "Reopened wheel diagnostic differs")
    save("final-methods.json", {rel(p): file_hash(p) for p in sorted(support())})
    save("resource-contract.json", {"forecast": read(REVIEW / "forecast.json"), "current": storage(), "selector": SELECTOR})
    return {"wheel_valid": True, "reuse012_completed_stages": 17, "no_repack_or_product_retry": True}


def seal():
    require((HERE / "RESULT.md").is_file(), "Actual result review required")
    for stage, action in INSTALLED.items():
        receipt = read(HERE / "installed-checks" / (action + ".json"))
        require(receipt["status"] == "PASS" and receipt["details"] == read(OLD / "checks" / (action + ".json")),
                "Missing installed parity: " + stage)
    save("verified-result.json", {"actual_product_consumption": True, "offline_installed_consumption": True,
         "fresh_normal_build": False, "package_files": 441, "actual_installed_refusals": 14,
         "checkout_evidence": rel(OLD), "checkout_attempt_status": "FAIL", "new_installed_actions": 9,
         "candidate": read(OLD / "checks/candidate-answer.json"), "composition": read(OLD / "checks/composition.json"),
         "result_note_sha256": file_hash(HERE / "RESULT.md"), "independent_acceptance": False, "task_complete": False})
    return {"offline_installed_consumption": True, "actual_installed_refusals": 14, "task_complete": False}


def finish(result):
    failure = result["status"] == "FAIL"
    save("result.json", {**result, "task": "source-bes-dep-09", "task_complete": False,
         "whole_program_complete": False, "independent_acceptance": False}, failure=failure)
    save("outputs.json", previous.cases.legacy.package_files(HERE), failure=failure)


def run(stage):
    require(stage in STAGES, "Unknown installation stage")
    with Authority(ROOT).lock():
        require((HERE / "admission.json").is_file() and not (HERE / "outputs.json").exists(), "Unadmitted/sealed attempt")
        try:
            admission = bindings()
        except Exception as exc:
            save("preflight-failure.json", {"traceback": traceback.format_exc()}, failure=True)
            result = {"stage": stage, "status": "FAIL", "error": {"type": type(exc).__name__, "message": str(exc)}, "wall_seconds": 0}
            finish(result)
            print(json.dumps(result))
            return 1
        index = STAGES.index(stage)
        require({p.parent.name for p in (HERE / "stages").glob("*/started.json")} ==
                {p.parent.name for p in (HERE / "stages").glob("*/result.json")} == set(STAGES[:index]), "Repeated/skipped/interrupted stage")
        rows = [read(HERE / "stages" / name / "result.json") for name in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < SELECTOR["stage_seconds"] for r in rows), "Failed predecessor")
        spent, before = sum(r["wall_seconds"] for r in rows), storage()
        def within(elapsed=0):
            state = storage()
            return spent + elapsed < SELECTOR["new_seconds"] and \
                before["previous_seconds"] + spent + elapsed < SELECTOR["combined003_onward_seconds"] and \
                state["combined_bytes"] < SELECTOR["combined003_onward_bytes"] - SELECTOR["reserve_bytes"]
        require(within(), "Original cumulative installation bounds exhausted")
        save("stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
             "command": ["timeout", "55", ".venv/bin/python", "-m", "scripts.prospectus_2010_capital_install", stage],
             "git_commit": admission["git_commit"], "python": sys.executable, "cpu_gpu": "CPU only; GPUs intentionally hidden",
             "random_seeds": "N/A deterministic", "data_version": "sealed012 wheel/checks; original P1;009/006/007/010",
             "plan": PLAN, "result": rel(HERE / "RESULT.md")})
        tick, details, error = time.monotonic(), None, None
        def expire(*_):
            raise TimeoutError("Installation stage/cumulative bound; no unchanged retry")
        old_signal = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(SELECTOR["work_seconds"], SELECTOR["new_seconds"] - spent,
            SELECTOR["combined003_onward_seconds"] - before["previous_seconds"] - spent))
        try:
            commands = [command(stage)] if stage in CHILDREN else []
            with previous.execution_guard(commands) as guard:
                details = child(stage) if stage in CHILDREN else prepare() if stage == "prepare" else seal()
            require(guard.result() == {"starts": len(commands), "blocked": 0}, "Unexpected process/network action")
            bindings()
            require(time.monotonic() - tick < SELECTOR["stage_seconds"] and within(time.monotonic() - tick), "Cumulative bounds exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, failure=True)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_signal)
        result = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error, "details": details,
                  "wall_seconds": time.monotonic() - tick, "bounds": storage(),
                  "timing_scope": "Body and final identities; excludes startup/final receipt writing"}
        result["cumulative_seconds"] = spent + result["wall_seconds"]
        save("stages/" + stage + "/result.json", result, failure=bool(error))
        if error or stage == "seal":
            finish(result)
        print(json.dumps({k: result[k] for k in ("stage", "status", "error", "wall_seconds", "cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1]))
