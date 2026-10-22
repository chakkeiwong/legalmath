"""Bounded supplied reading of original 2010 liability/equity policies and notes."""
from datetime import datetime, timezone
import gzip
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts.prospectus_basf_pension_source import files, load, require
from scripts.prospectus_installed_profile_worker import execution_guard

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
SOURCE = BASE / "attempts/source-bes-dep-09"
HERE = SOURCE / "attempt-010"
REVIEW = BASE / "reviews/2010-capital-notes-189"
PLAN = "docs/plans/prospectus-2010-capital-notes-2026-10-17.md"
ORIGINAL = SOURCE / "attempt-002/original-P1.json.gz"
PRIMARY = SOURCE / "attempt-006/profile.json"
EPS = SOURCE / "attempt-007/profile.json"
BASELINE = SOURCE / "attempt-009/after-answer.json.gz"
KEY = "original2010_capital_notes_agent_reading"
STAGES = ("prepare", "render-policy", "render-debt", "render-equity", "profile", "answer", "controls", "seal")
GROUPS = {"policy": [108, 109], "debt": [158, 159], "equity": [160, 161]}
COUNTS = {108: 52, 109: 47, 158: 177, 159: 195, 160: 110, 161: 65}
SELECTOR = {"version": "bes-2010-capital-notes.v1", "stages": list(STAGES),
    "source_pages": list(COUNTS), "source_occurrences": 646, "minimum_semantic_controls": 30,
    "new_seconds": 240, "combined003_onward_seconds": 1960, "new_bytes": 12 * 1024**2,
    "combined003_onward_bytes": 200 * 1024**2, "reserve_bytes": 512 * 1024,
    "work_seconds": 45, "stage_seconds": 50, "render_children": 3, "child_seconds": 20,
    "render_scale": 2200, "extraction_OCR_network_model_GPU_install_production_edits_retries": 0}
LIMITS = {"financial_values_validated": False, "source_authenticity_established": False,
    "independent_acceptance": False, "production_integration": False, "automatic_discovery": False,
    "accounting_standard_compliance_determined": False, "official_policy_correction_selected": False,
    "current_law_verified": False, "controlling_edition_selected": False, "all_notes_read": False,
    "BES_Finance_standalone_accounts_supplied": False, "transaction_entitlement_established": False}


def support_paths():
    return [p for p in REVIEW.rglob("*") if p.is_file()] + [Path(__file__), ROOT / PLAN,
        BASE / "proposals/2010-capital-notes-189.json", BASE / "proposals/2010-capital-notes-189-review.json",
        BASE / "closure-routes-2026-10-17-2010-capital-notes-189.json"]


def storage():
    history = read(REVIEW / "history.json")
    new = sum(p.stat().st_size for p in set(support_paths()) if p.is_file())
    new += sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file())
    return {"previous_seconds": history["previous_seconds"], "previous_bytes": history["previous_bytes"],
        "new_bytes": new, "combined_bytes": history["previous_bytes"] + new}


def save(name, value, failure=False):
    path = HERE / name
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    data = gzip.compress(raw, mtime=0) if path.suffix == ".gz" else raw + b"\n"
    state = storage()
    reserve = 0 if failure else SELECTOR["reserve_bytes"]
    require(state["new_bytes"] + len(data) < SELECTOR["new_bytes"] - reserve and
        state["combined_bytes"] + len(data) < SELECTOR["combined003_onward_bytes"] - reserve,
        "Capital-note retained storage ceiling exceeded")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def bindings():
    a = Authority(ROOT)
    program, tasks, _ = a.spec()
    task = tasks["source-bes-dep-09"]
    admitted = read(HERE / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT)) and
        task.get("capital_notes_reading") == SELECTOR and admitted["task_spec"] == task and
        admitted["program_sha256"] == digest(program) and admitted["binding"] == a.binding(task),
        "Current unchanged capital-note admission required")
    require(not (HERE / "outputs.json").exists(), "Capital-note attempt already sealed")
    history = read(REVIEW / "history.json")
    require(all(file_hash(ROOT / p) == h for p, h in history["protected"].items()), "Historical evidence changed")
    require(files(ROOT / "src/legalmath") == history["package"], "Production package changed")
    if (HERE / "reading-methods.json").exists():
        require(all(file_hash(ROOT / p) == h for p, h in read(HERE / "reading-methods.json").items()),
            "Frozen capital-note reading changed")
    return admitted


def prepare():
    product = load(ORIGINAL)
    document, = product["payload"]["request"]["bundle"]["documents"]
    require(document["id"] == "bes-2010-en" and file_hash(ROOT / document["path"]) == document["sha256"],
        "Exact original 2010 PDF required")
    units = [u for u in product["payload"]["graph"]["units"] if u["document"] == document["id"] and u["page"] in COUNTS]
    require(len(units) == len({u["id"] for u in units}) == 646 and
        {p: sum(u["page"] == p for u in units) for p in COUNTS} == COUNTS, "All646 original occurrences required")
    save("source-units.json.gz", units)
    save("source-document.json", document)
    refs = {}
    for name, path in (("primary", PRIMARY), ("EPS", EPS), ("baseline009", BASELINE),
                       ("composition009", SOURCE / "attempt-009/checks/composition.json")):
        refs[name] = {"path": str(path.relative_to(ROOT)), "file_sha256": file_hash(path), "content_sha256": digest(load(path))}
    save("comparison-references.json", refs)
    renderer = read(REVIEW / "history.json")["renderer"]
    for name, pages in GROUPS.items():
        prefix = "original2010-" + name
        save("render-spec-" + name + ".json", {"source": document, "renderer": renderer, "pages": pages,
            "prefix": prefix, "argv": [renderer["path"], "-f", str(pages[0]), "-l", str(pages[-1]),
                "-scale-to", "2200", "-gray", "-png", str(ROOT / document["path"]), str(HERE / prefix)]})
    return {"source_occurrences": 646, "new_extractions": 0, "large_answer_copies": 0}


def render_group(name):
    spec = read(HERE / ("render-spec-" + name + ".json"))
    require(file_hash(ROOT / spec["source"]["path"]) == spec["source"]["sha256"] and
        file_hash(Path(spec["renderer"]["path"])) == spec["renderer"]["sha256"], "Source/renderer changed")
    with (HERE / (spec["prefix"] + ".stdout")).open("xb") as out, (HERE / (spec["prefix"] + ".stderr")).open("xb") as err:
        result = subprocess.run(spec["argv"], stdout=out, stderr=err, timeout=20, env=dict(os.environ))
    images = sorted(HERE.glob(spec["prefix"] + "-*.png"))
    require(result.returncode == 0 and [int(p.stem.split("-")[-1]) for p in images] == spec["pages"],
        "Exact complete original render required")
    save("images-" + name + ".json", [{"document": "bes-2010-en", "page": int(p.stem.split("-")[-1]),
        "path": str(p.relative_to(ROOT)), "sha256": file_hash(p)} for p in images])
    if name == "equity":
        save("images.json", [r for group in GROUPS for r in read(HERE / ("images-" + group + ".json"))])
    return {"rendered_pages": len(images), "children": 1}


def evaluator():
    spec = importlib.util.spec_from_file_location("original2010_capital_reading", HERE / "reading.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(value, pin):
    require(digest(value) == pin, "Capital-note profile pin changed")
    require(value["version"] == SELECTOR["version"] and value["limits"] == LIMITS,
        "Capital-note authority/integration limits required")
    require(value["images"] == read(HERE / "images.json") and len(value["images"]) == 6 and
        all(file_hash(ROOT / i["path"]) == i["sha256"] for i in value["images"]), "All six inspected images required")
    refs = read(HERE / "comparison-references.json")
    require(value["comparison_references"] == refs and
        all(file_hash(ROOT / r["path"]) == r["file_sha256"] for r in refs.values()), "Original comparators changed")
    return evaluator().evaluate(load(HERE / "source-units.json.gz"), value["reading"], load(PRIMARY), load(EPS))


def profile():
    names = ("reading.py", "prepare-reading.py", "SOURCE-REVIEW.md", "IMPLEMENTATION-REVIEW.md", "draft-profile.json")
    require(all((HERE / n).is_file() for n in names), "Source and implementation reviews required")
    value = read(HERE / "draft-profile.json")
    analysis = validate(value, digest(value))
    cases = evaluator().CASES
    require(len(cases) >= 30, "At least30 substantive altered-reading controls required")
    save("reading-methods.json", {str(p.relative_to(ROOT)): file_hash(p) for p in
        [HERE / n for n in names] + [Path(__file__), ROOT / PLAN, REVIEW / "REVIEW.md",
            HERE / "source-units.json.gz", HERE / "images.json", HERE / "comparison-references.json"]})
    save("profile.json", value)
    save("profile-pin.json", {"sha256": digest(value)})
    save("intended-refusals.json", cases)
    return {"reading_frozen": True, "intended_controls": len(cases), "source_occurrences": analysis["source_occurrences"]}


def complete_baseline():
    composition = read(SOURCE / "attempt-009/checks/composition.json")
    require(file_hash(BASELINE) == composition["candidate_answer_file_sha256"], "Original009 answer bytes changed")
    answer = load(BASELINE)
    for name in ("previous_overlay", "overlay"):
        ref = composition["original_overlay_references"][name]
        part = load(ROOT / ref["path"])
        require(file_hash(ROOT / ref["path"]) == ref["file_sha256"] and digest(part) == ref["content_sha256"],
            "Original006/007 overlay changed")
        require(not set(answer) & set(part), "Duplicate baseline key")
        answer.update(part)
    require(digest(answer) == composition["after_composed_sha256"] ==
        "e85a5e137458f47d5b2d47d8b701a40fbaa2ccd768a766c878ac1e3d1db79e15", "Complete009 composed baseline differs")
    return answer


def answer():
    value = read(HERE / "profile.json")
    analysis = validate(value, read(HERE / "profile-pin.json")["sha256"])
    baseline = complete_baseline()
    unresolved = {"BES-DEP-" + str(i).zfill(2) for i in range(1, 12)} | {"BES-DEP-AGENCY-" + str(i).zfill(2) for i in range(1, 4)}
    require({d["id"] for d in baseline["dependencies"] if d["id"] in unresolved and d["status"] == "UNRESOLVED"} == unresolved and
        baseline["questions"]["Q3"]["status"] == "PARTIAL" and not baseline["may_execute_transaction"] and
        not baseline["independent_legal_acceptance"], "Original dependency and legal limits required")
    overlay = {KEY: {"source_units": load(HERE / "source-units.json.gz"), "profile": value, "analysis": analysis, "limits": LIMITS}}
    require(KEY not in baseline, "Capital-note addition already present")
    combined = {**baseline, **overlay}
    require({k: combined[k] for k in baseline} == baseline, "Complete009 answer changed")
    save("answer-overlay.json.gz", overlay)
    save("analysis.json", analysis)
    save("answer-composition.json", {"baseline": read(HERE / "comparison-references.json")["baseline009"],
        "composition009": read(HERE / "comparison-references.json")["composition009"],
        "prior_complete_answer_sha256": digest(baseline),
        "overlay": {"path": str((HERE / "answer-overlay.json.gz").relative_to(ROOT)),
            "file_sha256": file_hash(HERE / "answer-overlay.json.gz"), "content_sha256": digest(overlay)},
        "complete_composed_answer_sha256": digest(combined), "complete_prior_consumer_equal": True,
        "materialized_in_memory": True, "large_answer_copies": 0, "source_occurrences": 646,
        "original_BES_dependencies_unresolved": 14, "Q3": "PARTIAL", "production_integration": False})
    return {"complete009_composed_answer_preserved": True, "new_large_answer_copies": 0}


def controls():
    value, method = read(HERE / "profile.json"), evaluator()
    rows = []
    for name, reason in read(HERE / "intended-refusals.json").items():
        bad = method.altered(value, name)
        pin = digest(bad)
        save("adverse-inputs/" + name + ".json.gz", {"profile": bad, "expected_pin": pin})
        try:
            validate(bad, pin)
        except ValueError as exc:
            row = {"case": name, "refused": True, "repinned": True, "reason": str(exc)}
            save("adverse-results/" + name + ".json", row)
            require(str(exc) == reason, "Wrong substantive refusal: " + name + ": " + str(exc))
            rows.append(row)
        else:
            raise ValueError("Changed capital-note reading accepted: " + name)
    save("actual-controls.json", rows)
    return {"actual_refusals": len(rows), "repinned": len(rows)}


def seal():
    require((HERE / "RESULT.md").is_file(), "Actual source result required before seal")
    rows, intended = read(HERE / "actual-controls.json"), read(HERE / "intended-refusals.json")
    require(len(rows) == len(intended) >= 30 and {r["case"] for r in rows} == set(intended) and
        all(r["refused"] and r["repinned"] and r["reason"] == intended[r["case"]] for r in rows),
        "Complete intended actual refusals required")
    save("verified-result.json", {**read(HERE / "answer-composition.json"), "actual_refusals": len(rows),
        "task_complete": False, "result_note_sha256": file_hash(HERE / "RESULT.md")})
    return {"conditional_capital_note_reading_retained": True, "task_complete": False}


def run(stage):
    with Authority(ROOT).lock():
        admission = bindings()
        index = STAGES.index(stage)
        require({p.parent.name for p in (HERE / "stages").glob("*/started.json")} ==
            {p.parent.name for p in (HERE / "stages").glob("*/result.json")} == set(STAGES[:index]),
            "Repeated/skipped/interrupted capital-note stage")
        rows = [read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < 50 for r in rows), "Failed capital-note predecessor")
        spent, before = sum(r["wall_seconds"] for r in rows), storage()
        def within(now, elapsed=0):
            return spent + elapsed < 240 and now["previous_seconds"] + spent + elapsed < 1960 and \
                now["new_bytes"] < SELECTOR["new_bytes"] - SELECTOR["reserve_bytes"] and \
                now["combined_bytes"] < SELECTOR["combined003_onward_bytes"] - SELECTOR["reserve_bytes"]
        require(within(before), "Cumulative capital-note bound exhausted")
        save("stages/" + stage + "/started.json", {"command": ["timeout", "55", ".venv/bin/python", "-m",
            "scripts.prospectus_2010_capital_notes", stage], "at": datetime.now(timezone.utc).isoformat(),
            "git_commit": admission["git_commit"], "python": sys.executable,
            "environment": "Existing worktree .venv; no installs or shared-environment writes",
            "cpu_gpu": "CPU only; GPU devices intentionally hidden", "random_seeds": "N/A deterministic source reading",
            "plan": PLAN, "data_version": str(ORIGINAL.relative_to(ROOT)), "result": str((HERE / "RESULT.md").relative_to(ROOT))})
        tick, details, error = time.monotonic(), None, None
        def expire(_signum, _frame):
            raise TimeoutError("Capital-note stage/cumulative bound; no unchanged retry")
        old = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(45, 240 - spent, 1960 - before["previous_seconds"] - spent))
        try:
            rendering = stage.startswith("render-")
            commands = [read(HERE / ("render-spec-" + stage[7:] + ".json"))["argv"]] if rendering else []
            with execution_guard(commands) as guard:
                details = render_group(stage[7:]) if rendering else globals()[stage]()
            require(guard.result() == {"starts": len(commands), "blocked": 0}, "Unexpected process/network action")
            details["process_guard"] = guard.result()
            bindings()
            require(time.monotonic() - tick < 50 and within(storage(), time.monotonic() - tick), "Capital-note cumulative bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, failure=True)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
        result = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error, "details": details,
            "wall_seconds": time.monotonic() - tick, "bounds": storage(),
            "timing_scope": "Stage body and final identity checks; excludes startup/final receipt writing"}
        result["cumulative_seconds"] = spent + result["wall_seconds"]
        save("stages/" + stage + "/result.json", result, failure=bool(error))
        if error or stage == "seal":
            save("result.json", {**result, "task": "source-bes-dep-09", "task_complete": False,
                "whole_program_complete": False, "independent_legal_acceptance": False}, failure=bool(error))
            save("outputs.json", files(HERE), failure=bool(error))
        print(json.dumps({k: result[k] for k in ("stage", "status", "error", "wall_seconds", "cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1]))
