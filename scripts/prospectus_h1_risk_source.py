"""Bounded original risk-page investigation; retained OCR is never rewritten."""
from datetime import datetime, timezone
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

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
    PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_CACHE_DIR="1",
    PYTHONNOUSERSITE="1", PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from legalmath.prospectus.successor import process_ledger
from legalmath.prospectus.successor.contracts import digest as product_digest
from scripts.prospectus_basf_pension_source import files, load, require
from scripts.prospectus_installed_profile_worker import execution_guard

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
HERE = BASE / "attempts/source-bes-dep-05/attempt-006"
ORIGINAL = HERE.parent / "attempt-001"
PRIOR = HERE.parent / "attempt-005"
REVIEW = BASE / "reviews/h1-risk-tables-162"
PLAN = "docs/plans/prospectus-h1-risk-tables-2026-10-16.md"
DOCUMENT = "bes-interim-h1-2010"
STAGES = ("prepare", "render", "baseline", "profile", "compare", "controls-a", "controls-b", "controls-c", "controls-d", "tests",
    "install-prepare", "build", "install", "installed-positive", "installed-controls-a", "installed-controls-b", "installed-controls-c", "installed-controls-d", "verify", "seal")
SELECTOR = {"version": "bes-h1-risk-tables-supplied.v1", "stages": list(STAGES),
    "work_seconds": 110, "stage_seconds": 115, "child_seconds": 100,
    "execution_seconds": 1800, "storage_bytes": 700 * 1024**2,
    "outer_children": 8, "native_renders": 1, "extractions": 0, "ocr_calls": 0,
    "network_calls": 0, "unchanged_retries": 0, "controls": 32, "control_partition_sizes": [8,8,8,8]}


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    with path.open("xb") as stream:
        stream.write(gzip.compress(raw, mtime=0) if path.suffix == ".gz" else raw + b"\n")


def storage():
    folders = [HERE]
    if (HERE / "workspace.json").is_file():
        folders.append(Path(read(HERE / "workspace.json")["directory"]))
    return sum(p.stat().st_size for folder in folders for p in folder.rglob("*") if p.is_file())


def bindings():
    a = Authority(ROOT)
    program, tasks, _ = a.spec()
    task = tasks["source-bes-dep-05"]
    require(task.get("risk_table_reading") == SELECTOR, "Unreviewed H1 risk-table scope")
    admitted = read(HERE / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT))
        and admitted["program_sha256"] == digest(program) and admitted["task_spec"] == task
        and admitted["binding"] == a.binding(task), "Current unchanged H1 risk admission required")
    require(not (HERE / "outputs.json").exists(), "Risk evidence already sealed")
    for name in ("protected-inputs.json", "source-methods.json", "methods.json"):
        if (HERE / name).is_file():
            require(all(file_hash(ROOT / p) == h for p, h in read(HERE / name).items()), "Frozen risk evidence/method changed: " + name)
    return admitted


def prepare():
    history = read(REVIEW / "history.json")
    require(all(file_hash(ROOT / p) == h for p, h in history["protected"].items()), "Original risk/source evidence changed")
    save("protected-inputs.json", history["protected"])
    paths = [Path(__file__), ROOT / PLAN, REVIEW / "REVIEW.md", REVIEW / "history.json",
        Path(process_ledger.__file__), ROOT / "scripts/prospectus_installed_profile_worker.py"]
    save("source-methods.json", {str(p.relative_to(ROOT)): file_hash(p) for p in paths})
    shutil.copyfile(PRIOR / "products.json.gz", HERE / "products.json.gz")
    products = load(HERE / "products.json.gz")
    graph = products["P1"]["payload"]["graph"]
    require(len(graph["units"]) == 33221, "Complete original graph changed")
    units = [u for u in graph["units"] if u["document"] == DOCUMENT and u["page"] in (162,163)]
    require([sum(u["page"] == p for u in units) for p in (162,163)] == [704,229], "Complete risk occurrences changed")
    save("source-units.json", units)
    doc = next(d for d in products["P1"]["payload"]["request"]["bundle"]["documents"] if d["id"] == DOCUMENT)
    require(file_hash(ROOT / doc["path"]) == doc["sha256"] == "b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7", "Original H1 PDF changed")
    save("original-source.json", doc)
    renderer = Path(shutil.which("pdftoppm")).resolve(strict=True)
    save("renderer.json", {"path": str(renderer), "sha256": file_hash(renderer)})
    process_ledger.create(HERE / "native-ledger.json", 1, 0, "One newly reviewed high-resolution risk render; earlier source actions remain in historical attempts")
    process_ledger.create(HERE / "command-ledger.json", 8, 0, "Risk render, offline build/install and five isolated replays; historical attempts and pip internals outside this narrow count")
    return {"source_units": 33221, "risk_occurrences": 933, "previous_admissions": 5}


def child(name, argv):
    folder = HERE / "commands" / name
    folder.mkdir(parents=True, exist_ok=False)
    save("commands/" + name + "/started.json", {"argv": argv, "timeout_seconds": 100,
        "cpu_gpu": "CPU only; GPU devices intentionally hidden"})
    tick, result, error = time.monotonic(), None, None
    with (folder / "stdout").open("xb") as out, (folder / "stderr").open("xb") as err:
        with execution_guard([argv]) as guard, process_ledger.observe(HERE / "command-ledger.json"):
            try:
                result = subprocess.run(argv, stdout=out, stderr=err, timeout=100, env=dict(os.environ))
            except BaseException as exc:
                error = {"type": type(exc).__name__, "message": str(exc)}
            finally:
                save("commands/" + name + "/result.json", {"returncode": None if result is None else result.returncode,
                    "error": error, "wall_seconds": time.monotonic() - tick, "process_guard": guard.result()})
    require(error is None and result is not None and result.returncode == 0 and guard.result() == {"starts": 1, "blocked": 0}, "Risk child failed: " + name)


def render():
    doc, renderer = read(HERE / "original-source.json"), read(HERE / "renderer.json")
    require(file_hash(ROOT / doc["path"]) == doc["sha256"] and file_hash(Path(renderer["path"])) == renderer["sha256"], "Source/renderer changed")
    require(not list(HERE.glob("risk-*.png")), "Risk render already started")
    with process_ledger.observe(HERE / "native-ledger.json"):
        child("render", [renderer["path"], "-f", "162", "-l", "163", "-scale-to", "2600", "-png",
            str(ROOT / doc["path"]), str(HERE / "risk")])
    images = [{"page": p, "path": str((HERE / ("risk-" + str(p) + ".png")).relative_to(ROOT)),
        "sha256": file_hash(HERE / ("risk-" + str(p) + ".png"))} for p in (162,163)]
    save("rendered-source.json", {"document": DOCUMENT, "path": doc["path"], "sha256": doc["sha256"], "images": images, "renderer": renderer})
    return {"rendered_pages": 2, "native_source_renders": 1, "new_extractions": 0, "new_ocr": 0}


def baseline():
    from legalmath.prospectus import h1_cash_flow
    profile = read(PRIOR / "profile.json")
    current = h1_cash_flow.consume(load(HERE / "products.json.gz"), profile, ROOT, expected_profile_sha256=product_digest(profile))
    require(current == load(PRIOR / "cash-flow-consumer.json.gz"), "Complete retained cash-flow consumer differs")
    save("cash-flow-profile.json", profile)
    save("baseline-consumer.json.gz", current)
    return {"complete_prior_consumer_equal": True, "complete_original_answer_equal": True}


def run(stage, action):
    with Authority(ROOT).lock():
        admitted = bindings()
        index = STAGES.index(stage)
        started = {p.parent.name for p in (HERE / "stages").glob("*/started.json")}
        finished = {p.parent.name for p in (HERE / "stages").glob("*/result.json")}
        require(started == finished == set(STAGES[:index]), "Repeated, skipped or interrupted risk stage")
        rows = [read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < 115 for r in rows), "Failed risk predecessor")
        spent = sum(r["wall_seconds"] for r in rows)
        require(spent < 1800 and storage() < 698 * 1024**2, "Risk cumulative allowance exhausted")
        save("stages/" + stage + "/started.json", {"command": ["timeout", "120", ".venv/bin/python", "-m",
            "scripts.prospectus_h1_risk_source" if index < 3 else "scripts.prospectus_h1_risk_tables", stage],
            "at": datetime.now(timezone.utc).isoformat(), "git_commit": admitted["git_commit"], "python": sys.executable,
            "cpu_gpu": "CPU only; GPU devices intentionally hidden", "random_seeds": "N/A deterministic supplied risk reading",
            "plan": PLAN, "data_version": str((PRIOR / "outputs.json").relative_to(ROOT)),
            "result": str((HERE / "RESULT.md").relative_to(ROOT))})
        tick, details, error = time.monotonic(), None, None
        def expire(signum, frame):
            raise TimeoutError("Risk work limit; no unchanged retry")
        old_handler = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(110, 1800 - spent))
        try:
            details = action()
            bindings()
            require(storage() < 698 * 1024**2, "Risk storage bound")
            require(time.monotonic() - tick < 115 and spent + time.monotonic() - tick < 1800, "Risk recorded time bound")
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
            save("result.json", {**value, "task": "source-bes-dep-05", "task_complete": False,
                "whole_program_complete": False, "independent_legal_acceptance": False})
            save("outputs.json", files(HERE))
        print(json.dumps({k: value[k] for k in ("stage", "status", "error", "wall_seconds", "cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    require(len(sys.argv) == 2 and sys.argv[1] in STAGES[:3], "Choose risk source prepare/render/baseline")
    stage = sys.argv[1]
    def guarded():
        if stage == "render":
            return render()
        with execution_guard() as guard:
            result = globals()[stage]()
            require(guard.result() == {"starts": 0, "blocked": 0}, "Unexpected source process")
        return {**result, "process_guard": guard.result()}
    raise SystemExit(run(stage, guarded))
