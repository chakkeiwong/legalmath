"""Bounded same-task reading of the retained bilingual individual statements."""
from datetime import datetime, timezone
import gzip
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTHONNOUSERSITE="1", PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts.prospectus_basf_pension_source import files, load, require
from scripts.prospectus_installed_profile_worker import execution_guard

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
SOURCE = BASE / "attempts/source-bes-dep-07"
HERE = SOURCE / "attempt-008"
PREVIOUS = [SOURCE / f"attempt-{n:03d}" for n in range(3, 8)]
ORIGINAL = PREVIOUS[0] / "original-P1.json.gz"
COMPOSITION = PREVIOUS[-1] / "answer-composition.json"
PRIMARY = SOURCE / "attempt-004/analysis.json"
REVIEW = BASE / "reviews/2008-individual-193"
CONTINUATION = BASE / "continuation-reviews/2026-10-17-after-capital013"
PLAN = "docs/plans/prospectus-2008-individual-scope-proposal-2026-10-17.md"
ROUTES = BASE / "closure-routes-2026-10-17-2008-individual-193.json"
REVIEW_FILE = BASE / "proposals/2008-individual-193-review.json"
KEY = "original2008_individual_statement_agent_reading"
STAGES = ("prepare", "render-en-a", "render-en-b", "render-pt-a", "render-pt-b", "profile", "answer", "controls", "seal")
SELECTOR = {"version": "bes-2008-individual-statements.v1", "stages": list(STAGES),
            "source_pages": list(range(165, 171)), "source_occurrences": 1928,
            "new_seconds": 100, "combined003_onward_seconds": 1080,
            "new_bytes": 8 * 1024**2, "combined003_onward_bytes": 168 * 1024**2,
            "reserve_bytes": 256 * 1024, "work_seconds": 45, "stage_seconds": 50,
            "render_children": 4, "child_seconds": 15, "render_scale": 1800,
            "render_gray": True, "render_file_bytes": 512 * 1024, "minimum_semantic_controls": 20,
            "extraction_OCR_network_model_GPU_install_production_edits_retries": 0}
LIMITS = {"source_authenticity": False, "controlling_incorporation": False,
          "independent_acceptance": False, "financial_values_validated": False,
          "accounting_compliance": False, "automatic_discovery": False,
          "production_integration": False, "BES_Finance_standalone_accounts": False,
          "Note46_resolved": False, "intangibles_conflict_resolved": False,
          "all_notes_read": False, "transaction_execution": False}


def support():
    return ({p for folder in (REVIEW, CONTINUATION) for p in folder.rglob("*") if p.is_file()}
            | {Path(__file__), ROOT / PLAN, ROUTES, REVIEW_FILE})


def storage():
    previous_bytes = sum(p.stat().st_size for folder in PREVIOUS for p in folder.rglob("*") if p.is_file())
    current = support() | {p for p in HERE.rglob("*") if p.is_file()}
    new_bytes = sum(p.stat().st_size for p in current if p.is_file())
    seconds = sum(read(p)["wall_seconds"] for folder in PREVIOUS for p in (folder / "stages").glob("*/result.json"))
    return {"previous_bytes": previous_bytes, "new_bytes": new_bytes,
            "combined_bytes": previous_bytes + new_bytes, "previous_seconds": seconds}


def space(additional=0, failure=False):
    state = storage()
    reserve = 0 if failure else SELECTOR["reserve_bytes"]
    require(state["new_bytes"] + additional < SELECTOR["new_bytes"] - reserve and
            state["combined_bytes"] + additional < SELECTOR["combined003_onward_bytes"] - reserve,
            "Individual-statement cumulative storage/reserve exhausted")
    return state


def save(name, value, failure=False):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    data = gzip.compress(raw, mtime=0) if name.endswith(".gz") else raw + b"\n"
    space(len(data), failure)
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def bindings():
    authority = Authority(ROOT)
    program, tasks, _ = authority.spec()
    task = tasks["source-bes-dep-07"]
    admitted = read(HERE / "admission.json")
    event = next(e for e in reversed(authority.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT)) and
            file_hash(HERE / "admission.json") == event["admission_sha256"] and
            admitted["task_spec"] == task and task["individual_reading"] == SELECTOR and
            admitted["program_sha256"] == digest(program) and admitted["binding"] == authority.binding(task),
            "Current unchanged individual-statement admission required")
    require(not (HERE / "outputs.json").exists(), "Individual reading already sealed")
    history = read(REVIEW / "history.json")
    for row in history["retained_events"]:
        require(authority.retained_evidence_valid(row), "Historical source07 evidence changed")
    require(files(ROOT / "src/legalmath") == history["package"], "Production files changed")
    require(not (REVIEW / "proposal.pending.json").exists() and (REVIEW / "transport-retirement.json").is_file(),
            "Verified proposal transport retirement required before execution")
    if (HERE / "reading-methods.json").exists():
        require(all(file_hash(ROOT / p) == h for p, h in read(HERE / "reading-methods.json").items()),
                "Frozen individual reading changed")
    return admitted


def prepare():
    product = load(ORIGINAL)
    documents = product["payload"]["request"]["bundle"]["documents"]
    require({d["id"] for d in documents} == {"bes-2008-en", "bes-2008-pt"}, "Exact bilingual originals required")
    require(all(file_hash(ROOT / d["path"]) == d["sha256"] for d in documents), "Original PDF changed")
    units = [u for u in product["payload"]["graph"]["units"] if u["document"] in {d["id"] for d in documents}
             and u["page"] in SELECTOR["source_pages"]]
    require(len(units) == len({u["id"] for u in units}) == 1928, "All1928 source occurrences required")
    save("source-units.json.gz", units)
    save("baseline-reference.json", {"path": str(COMPOSITION.relative_to(ROOT)), "sha256": file_hash(COMPOSITION)})
    renderer = read(REVIEW / "history.json")["renderer"]
    for doc in documents:
        for name, pages in (("a", [165, 166, 167]), ("b", [168, 169, 170])):
            key = doc["language"] + "-" + name
            save("render-spec-" + key + ".json", {"source": doc, "renderer": renderer, "pages": pages,
                 "argv": [renderer["path"], "-f", str(pages[0]), "-l", str(pages[-1]),
                          "-scale-to", "1800", "-gray", "-png", str(ROOT / doc["path"]),
                          str(HERE / ("individual-" + key))]})
    return {"source_occurrences": len(units), "new_extractions": 0}


def render(key):
    spec = read(HERE / ("render-spec-" + key + ".json"))
    require(file_hash(ROOT / spec["source"]["path"]) == spec["source"]["sha256"] and
            file_hash(Path(spec["renderer"]["path"])) == spec["renderer"]["sha256"], "Source/renderer changed")
    space(1600 * 1024)
    def file_limit():
        resource.setrlimit(resource.RLIMIT_FSIZE, (SELECTOR["render_file_bytes"], SELECTOR["render_file_bytes"]))
    result = subprocess.run(spec["argv"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                            timeout=15, env=dict(os.environ), preexec_fn=file_limit)
    require(len(result.stderr) <= 8192, "Renderer diagnostic exceeds retained bound")
    save("render-" + key + ".json", {"returncode": result.returncode,
         "stderr": result.stderr.decode("utf-8", errors="replace"), "per_file_limit": SELECTOR["render_file_bytes"]})
    paths = sorted(HERE.glob("individual-" + key + "-*.png"))
    require(result.returncode == 0 and [int(p.stem.split("-")[-1]) for p in paths] == spec["pages"], "Three exact original pages required")
    save("images-" + key + ".json", [{"document": spec["source"]["id"], "page": int(p.stem.split("-")[-1]),
          "path": str(p.relative_to(ROOT)), "sha256": file_hash(p)} for p in paths])
    if key == "pt-b":
        save("images.json", [image for k in ("en-a", "en-b", "pt-a", "pt-b") for image in read(HERE / ("images-" + k + ".json"))])
    return {"images": len(paths), "bytes": sum(p.stat().st_size for p in paths)}


def evaluator():
    spec = importlib.util.spec_from_file_location("original2008_individual_reading", HERE / "reading.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(value, pin):
    require(digest(value) == pin, "Individual profile pin changed")
    require(value["version"] == SELECTOR["version"] and value["limits"] == LIMITS, "Original authority/scope limits required")
    require(value["images"] == read(HERE / "images.json") and
            all(file_hash(ROOT / i["path"]) == i["sha256"] for i in value["images"]), "Twelve original images required")
    require(value["baseline_reference"] == read(HERE / "baseline-reference.json") and
            file_hash(COMPOSITION) == value["baseline_reference"]["sha256"], "Complete original EPS composition required")
    return evaluator().evaluate(load(HERE / "source-units.json.gz"), value["reading"], read(PRIMARY))


def profile():
    names = ("reading.py", "prepare-reading.py", "SOURCE-REVIEW.md", "IMPLEMENTATION-REVIEW.md", "draft-profile.json.gz")
    require(all((HERE / name).is_file() for name in names), "Actual source/implementation reviews and profile required")
    paths = [Path(__file__), ROOT / PLAN, REVIEW / "REVIEW.md", HERE / "source-units.json.gz", HERE / "images.json"] + [HERE / name for name in names]
    value = load(HERE / "draft-profile.json.gz")
    validate(value, digest(value))
    cases = evaluator().CASES
    require(len(cases) >= 20, "Twenty meaningful refusals required")
    save("reading-methods.json", {str(p.relative_to(ROOT)): file_hash(p) for p in paths})
    save("profile.json.gz", value)
    save("profile-pin.json", {"sha256": digest(value)})
    save("intended-refusals.json", cases)
    return {"reading_frozen": True, "intended_controls": len(cases)}


def answer():
    value = load(HERE / "profile.json.gz")
    analysis = validate(value, read(HERE / "profile-pin.json")["sha256"])
    composition = read(COMPOSITION)
    chunks = []
    for role in ("baseline", "overlay"):
        reference = composition[role]
        path = ROOT / reference["path"]
        require(file_hash(path) == reference["file_sha256"], "Saved answer reference changed")
        chunk = load(path)
        require(digest(chunk) == reference["content_sha256"], "Saved answer content changed")
        chunks.append(chunk)
    require(not chunks[0].keys() & chunks[1].keys(), "Baseline/overlay keys collide")
    baseline = {**chunks[0], **chunks[1]}
    require(digest(baseline) == composition["complete_composed_answer_sha256"], "Complete EPS predecessor changed")
    expected = {"BES-DEP-" + str(i).zfill(2) for i in range(1, 12)} | {"BES-DEP-AGENCY-" + str(i).zfill(2) for i in range(1, 4)}
    require({d["id"] for d in baseline["dependencies"] if d["id"] in expected and d["status"] == "UNRESOLVED"} == expected
            and baseline["questions"]["Q3"]["status"] == "PARTIAL" and KEY not in baseline, "Original unresolved answer required")
    overlay = {KEY: {"source_units": load(HERE / "source-units.json.gz"), "profile": value, "analysis": analysis, "limits": LIMITS}}
    combined = {**baseline, **overlay}
    require({k: combined[k] for k in baseline} == baseline, "Prior answer changed")
    save("analysis.json.gz", analysis)
    save("answer-overlay.json.gz", overlay)
    save("answer-composition.json", {"predecessor": read(HERE / "baseline-reference.json"),
         "baseline_content_sha256": digest(baseline),
         "overlay": {"path": str((HERE / "answer-overlay.json.gz").relative_to(ROOT)),
                     "file_sha256": file_hash(HERE / "answer-overlay.json.gz"), "content_sha256": digest(overlay)},
         "complete_composed_answer_sha256": digest(combined), "complete_prior_consumer_equal": True,
         "composition_rule": "Reconstruct the complete verified007 baseline then add the sole new field; reject duplicates",
         "materialized_in_memory": True, "large_answer_copies": 0, "source_occurrences": 1928,
         "original_BES_dependencies_unresolved": 14, "Q3": "PARTIAL"})
    return {"complete_prior_consumer_equal": True, "individual_reading_added": True}


def controls():
    value, method = load(HERE / "profile.json.gz"), evaluator()
    results = []
    for name, reason in read(HERE / "intended-refusals.json").items():
        bad = method.altered(value, name)
        pin = digest(bad)
        save("adverse-inputs/" + name + ".json.gz", {"profile": bad, "expected_pin": pin})
        try:
            validate(bad, pin)
        except ValueError as exc:
            row = {"case": name, "refused": True, "repinned": True, "reason": str(exc)}
            save("adverse-results/" + name + ".json", row)
            require(str(exc) == reason, "Wrong individual semantic refusal: " + name + ": " + str(exc))
            results.append(row)
        else:
            raise ValueError("Malformed individual reading accepted: " + name)
    save("actual-controls.json", results)
    return {"actual_refusals": len(results)}


def seal():
    require((HERE / "RESULT.md").is_file(), "Actual source result required")
    controls = read(HERE / "actual-controls.json")
    expected = read(HERE / "intended-refusals.json")
    require(len(controls) == len(expected) >= 20 and {r["case"] for r in controls} == set(expected) and
            all(r["refused"] and r["repinned"] and r["reason"] == expected[r["case"]] for r in controls),
            "All exact actual semantic refusals required")
    save("verified-result.json", {**read(HERE / "answer-composition.json"), "actual_refusals": len(controls),
         "task_complete": False, "independent_acceptance": False, "result_sha256": file_hash(HERE / "RESULT.md")})
    return {"reading_retained": True, "task_complete": False}


def run(stage):
    with Authority(ROOT).lock():
        admitted = bindings()
        index = STAGES.index(stage)
        require({p.parent.name for p in (HERE / "stages").glob("*/started.json")} ==
                {p.parent.name for p in (HERE / "stages").glob("*/result.json")} == set(STAGES[:index]), "Repeated/skipped/interrupted stage")
        previous = [read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < 50 for r in previous), "Failed predecessor stage")
        spent = sum(r["wall_seconds"] for r in previous)
        before = space()
        require(spent < 100 and before["previous_seconds"] + spent < 1080, "Cumulative time exhausted")
        save("stages/" + stage + "/started.json", {"command": ["timeout", "55", ".venv/bin/python", "-m", "scripts.prospectus_2008_individual", stage],
             "at": datetime.now(timezone.utc).isoformat(), "git_commit": admitted["git_commit"], "python": sys.executable,
             "cpu_gpu": "CPU only; CUDA_VISIBLE_DEVICES=-1 intentionally hides GPUs", "random_seeds": "N/A deterministic",
             "plan": PLAN, "data_version": str(ORIGINAL.relative_to(ROOT)), "result": str((HERE / "RESULT.md").relative_to(ROOT))})
        tick, details, error = time.monotonic(), None, None
        def expire(signum, frame):
            raise TimeoutError("Individual stage limit; no unchanged retry")
        old = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(45, 100 - spent, 1080 - before["previous_seconds"] - spent))
        try:
            commands = [read(HERE / ("render-spec-" + stage[7:] + ".json"))["argv"]] if stage.startswith("render-") else []
            with execution_guard(commands) as guard:
                details = render(stage[7:]) if commands else globals()[stage]()
            require(guard.result() == {"starts": len(commands), "blocked": 0}, "Unexpected process/network action")
            details["process_guard"] = guard.result()
            bindings()
            space()
            elapsed = time.monotonic() - tick
            require(elapsed < 50 and spent + elapsed < 100 and before["previous_seconds"] + spent + elapsed < 1080, "Cumulative execution limit exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, failure=True)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
        result = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error, "details": details,
                  "wall_seconds": time.monotonic() - tick, "bounds": storage(),
                  "timing_scope": "Stage body plus final binding checks; startup/final-receipt exclusion retained"}
        result["cumulative_seconds"] = spent + result["wall_seconds"]
        save("stages/" + stage + "/result.json", result, failure=bool(error))
        if error or stage == "seal":
            save("result.json", {**result, "task": "source-bes-dep-07", "task_complete": False,
                 "whole_program_complete": False, "independent_acceptance": False}, failure=bool(error))
            save("outputs.json", files(HERE), failure=bool(error))
        print(json.dumps({k: result[k] for k in ("stage", "status", "error", "wall_seconds", "cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1]))
