"""Bounded original Note22 source preparation for the admitted supplied reader."""
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
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from legalmath.prospectus.successor import process_ledger

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
HERE = BASE / "attempts/basf-references/attempt-005"
PRIOR = BASE / "attempts/basf-references/attempt-004"
REVIEW = BASE / "reviews/basf-pension-159"
PLAN = "docs/plans/prospectus-basf-pension-note-2026-10-16.md"
DOCUMENT = "basf-annual-2022-exchange"
STAGES = ("prepare", "render", "profile", "baseline", "compare", "controls", "tests",
          "install-prepare", "build", "install", "replay", "verify", "seal")
SELECTOR = {"version": "basf-pension-supplied.v1", "stages": list(STAGES),
    "work_seconds": 110, "stage_seconds": 115, "execution_seconds": 900,
    "storage_bytes": 500 * 1024**2, "outer_children": 4, "native_renders": 1,
    "extractions": 0, "source_http": 0, "unchanged_retries": 0}


def require(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    path = Path(path)
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    with path.open("xb") as stream:
        stream.write(gzip.compress(raw, mtime=0) if path.suffix == ".gz" else raw + b"\n")


def files(folder):
    return {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.name != "outputs.json"}


def storage():
    folders = [HERE]
    if (HERE / "workspace.json").is_file():
        folders.append(Path(read(HERE / "workspace.json")["directory"]))
    return sum(p.stat().st_size for folder in folders for p in folder.rglob("*") if p.is_file())


def bindings():
    a = Authority(ROOT)
    program, tasks, _ = a.spec()
    task = tasks["basf-references"]
    require(task.get("pension_review") == SELECTOR, "Unreviewed pension scope")
    admitted = read(HERE / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == "basf-references")
    require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT)) and
            admitted["program_sha256"] == digest(program) and admitted["task_spec"] == task and
            admitted["binding"] == a.binding(task), "Current unchanged pension admission required")
    require(not (HERE / "outputs.json").exists(), "Pension evidence already sealed")
    for name in ("protected-inputs.json", "source-methods.json", "methods.json"):
        if (HERE / name).is_file():
            require(all(file_hash(ROOT / p) == h for p, h in read(HERE / name).items()),
                    "Changed pension input or frozen method: " + name)
    return admitted


def prepare():
    protected = {str((PRIOR / p).relative_to(ROOT)): h for p, h in read(PRIOR / "outputs.json").items()}
    protected[str((PRIOR / "outputs.json").relative_to(ROOT))] = file_hash(PRIOR / "outputs.json")
    require(all(file_hash(ROOT / p) == h for p, h in protected.items()), "Previous source evidence changed")
    save("protected-inputs.json", protected)
    paths = [Path(__file__), ROOT / PLAN, REVIEW / "REVIEW.md", REVIEW / "history.json",
             Path(process_ledger.__file__)]
    save("source-methods.json", {str(p.relative_to(ROOT)): file_hash(p) for p in paths})
    shutil.copyfile(PRIOR / "products.json.gz", HERE / "products.json.gz")
    products = load(HERE / "products.json.gz")
    doc = next(d for d in products["P1"]["payload"]["request"]["bundle"]["documents"] if d["id"] == DOCUMENT)
    require(file_hash(ROOT / doc["path"]) == doc["sha256"] ==
            "77264ca8062e9ad095ad0f6b62c7114360a107622e6223e4d384030afc7a38f6", "Original annual2022 changed")
    save("original-source.json", doc)
    units = [u for u in products["P1"]["payload"]["graph"]["units"]
             if u["document"] == DOCUMENT and 261 <= u["page"] <= 266]
    require([sum(u["page"] == p for u in units) for p in range(261, 267)] == [97,143,98,165,150,100],
            "Complete pension source inventory changed")
    save("source-units.json", units)
    renderer = Path(shutil.which("pdftoppm")).resolve(strict=True)
    save("renderer.json", {"path": str(renderer), "sha256": file_hash(renderer)})
    process_ledger.create(HERE / "native-ledger.json", 1, 0, "Note22 source render; distinct from other native ledgers")
    process_ledger.create(HERE / "command-ledger.json", 4, 0, "One source render, offline build, install and replay")
    return {"source_occurrences": len(units), "prior_source_render_lower_bound": 79,
            "prior_counter_scope": "BASF source-render history through references004; not a global process total"}


def child(name, argv):
    folder = HERE / "commands" / name
    folder.mkdir(parents=True, exist_ok=False)
    save("commands/" + name + "/started.json", {"argv": argv, "timeout_seconds": 100,
            "cpu_gpu": "CPU only; GPU devices intentionally hidden"})
    tick = time.monotonic()
    with (folder / "stdout").open("xb") as out, (folder / "stderr").open("xb") as err:
        with process_ledger.observe(HERE / "command-ledger.json"):
            result = subprocess.run(argv, stdout=out, stderr=err, timeout=100,
                env={**os.environ, "CUDA_VISIBLE_DEVICES": "-1", "PYTHONDONTWRITEBYTECODE": "1"})
    save("commands/" + name + "/result.json", {"returncode": result.returncode,
            "wall_seconds": time.monotonic() - tick})
    require(result.returncode == 0, "Pension child failed: " + name)


def render():
    renderer, doc = read(HERE / "renderer.json"), read(HERE / "original-source.json")
    require(file_hash(Path(renderer["path"])) == renderer["sha256"], "Renderer changed")
    require(file_hash(ROOT / doc["path"]) == doc["sha256"], "Original PDF changed")
    require(not list(HERE.glob("note-*.png")), "Render already started")
    with process_ledger.observe(HERE / "native-ledger.json"):
        child("render", [renderer["path"], "-f", "261", "-l", "266", "-scale-to", "1800", "-png",
                         str(ROOT / doc["path"]), str(HERE / "note")])
    images = [{"page": p, "path": str((HERE / ("note-" + str(p) + ".png")).relative_to(ROOT)),
               "sha256": file_hash(HERE / ("note-" + str(p) + ".png"))} for p in range(261, 267)]
    save("rendered-source.json", {"document": DOCUMENT, "path": doc["path"], "sha256": doc["sha256"],
                                 "images": images, "renderer": renderer})
    return {"rendered_pages": 6, "native_source_renders": 1, "extractions": 0, "source_http": 0}


def run(stage, action):
    a = Authority(ROOT)
    with a.lock():
        admitted = bindings()
        index = STAGES.index(stage)
        actual = {p.parent.name for p in (HERE / "stages").glob("*/started.json")}
        results = {p.parent.name for p in (HERE / "stages").glob("*/result.json")}
        require(actual == results == set(STAGES[:index]), "Repeated, skipped or interrupted pension stage")
        rows = [read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < 115 for r in rows), "Failed pension predecessor")
        spent = sum(r["wall_seconds"] for r in rows)
        require(spent < 900 and storage() < 498 * 1024**2, "Pension cumulative bound exhausted")
        save("stages/" + stage + "/started.json", {"command": ["timeout", "120", ".venv/bin/python", "-m",
            "scripts.prospectus_basf_pension_source" if index < 2 else "scripts.prospectus_basf_pension_note", stage],
            "at": datetime.now(timezone.utc).isoformat(), "git_commit": admitted["git_commit"],
            "python": sys.executable, "cpu_gpu": "CPU only; GPU devices intentionally hidden",
            "random_seeds": "N/A deterministic supplied source analysis", "plan": PLAN,
            "result": str((HERE / "RESULT.md").relative_to(ROOT))})
        tick, details, error = time.monotonic(), None, None
        def expire(signum, frame):
            raise TimeoutError("Pension work bound; no automatic retry")
        old_handler = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(110, 900-spent))
        try:
            details = action()
            bindings()
            require(storage() < 498 * 1024**2, "Pension evidence/installation storage bound")
            require(time.monotonic()-tick < 115 and spent+time.monotonic()-tick < 900, "Pension recorded time bound")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/" + stage + "/error.json", {"traceback": traceback.format_exc()})
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
        value = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error,
                 "details": details, "wall_seconds": time.monotonic()-tick, "retained_bytes": storage()}
        save("stages/" + stage + "/result.json", value)
        if error or stage == "seal":
            save("result.json", {**value, "task": "basf-references", "task_complete": False,
                "whole_program_complete": False, "independent_legal_acceptance": False})
            save("outputs.json", files(HERE))
        print(json.dumps({k: value[k] for k in ("stage", "status", "error", "wall_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    stage = sys.argv[1]
    require(stage in ("prepare", "render"), "Choose source prepare or render")
    raise SystemExit(run(stage, {"prepare": prepare, "render": render}[stage]))
