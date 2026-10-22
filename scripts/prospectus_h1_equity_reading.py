"""Finite agent source reading of the intact parts of BES H1 page59."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import re
import signal
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
HERE = BASE / "attempts/source-bes-dep-05/attempt-010"
SCOPE = HERE.parent / "attempt-007"
NATIVE = HERE.parent / "attempt-008/original-page59-units.json"
DIAGNOSIS = HERE.parent / "attempt-009"
REVIEW = BASE / "reviews/h1-equity-reading-166"
PLAN = "docs/plans/prospectus-h1-equity-readable-columns-2026-10-16.md"
STAGES = ("prepare", "profile", "evaluate", "controls", "answer", "seal")
SELECTOR = {"version": "bes-h1-equity-readable-columns.v1", "stages": list(STAGES),
    "work_seconds": 110, "stage_seconds": 115, "execution_seconds": 600,
    "combined006_010_seconds": 1800, "combined006_010_bytes": 700*1024**2,
    "new_bytes": 80*1024**2, "additional_source_actions_children": 0,
    "production_edits": 0, "unchanged_retries": 0, "actual_controls": 12}
LABELS = [5,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,24,25,26,250,260,351,352,353,354,355,
          357,358,359,360,371,372,373,374,375,376,377,456]
COLUMNS = ["share_capital", "share_premium", "treasury_stock", "preference_shares", "fair_value_reserve",
           "other_reserves_retained_earnings", "profit_attributable_to_bank_holders", "equity_attributable_to_bank_holders",
           "non_controlling_interest", "total_equity"]
HEADERS = [[4],[27,28],[29,30],[31,32],[33,34],[36,37,38],[39,40,41,42,43],[44,45,46],[47,48,49],[50,51]]
BALANCES = {5: "2008-12-31", 22: "2009-06-30", 355: "2009-12-31", 456: "2010-06-30"}
MISSING_TOTAL = [12,14,16,372]
LIMITS = {"financial_values_validated": False, "source_authenticity_established": False,
    "independent_legal_acceptance": False, "actual_incorporation_resolved": False,
    "complete_financial_reading": False, "production_integration_claimed": False,
    "automatic_extraction": False, "total_equity_reconstructed": False}
FOOTNOTES = {
    "ordinary": {"units": [457,458], "category": "ORDINARY_SHARE_DIVIDEND",
        "per_share": [{"year": 2010, "currency": "EUR", "value": "0.14"}, {"year": 2009, "currency": "EUR", "value": "0.16"}],
        "note_coupon": False},
    "preference": {"units": [459,460], "category": "PREFERENCE_SHARE_DIVIDEND", "issuer": "BES Finance",
        "annual_interest_rate_percent": "5.58", "note_reference": "37", "note_coupon": False,
        "standalone_accounts_supplied": False},
    "integral_notes": {"units": [461], "notes_are_integral": True, "notes_fully_read": False}}
REFUSALS = {
    "changed-number": "Numeric cell reading differs from original source",
    "dash-as-zero": "Dash is unknown, not numeric zero",
    "clipped-total-as-number": "All total-equity cells remain unresolved",
    "omitted-row": "Complete39 ordered statement rows required",
    "duplicate-cell": "Exact original row/column association required",
    "swapped-columns": "Exact ordered statement headers required",
    "wrong-period": "Original stock/flow period association required",
    "preference-as-note-coupon": "Exact share-dividend categories and original footnotes required",
    "wrong-dividend-year": "Exact share-dividend categories and original footnotes required",
    "selected-incorporation": "Conditional reading cannot establish financial/legal authority or integration",
    "missing-metadata": "All original source characters must be retained once",
    "stale-pin": "Pinned source reading or complete prior consumer changed"}


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    with path.open("xb") as stream:
        stream.write(gzip.compress(raw, mtime=0) if path.suffix == ".gz" else raw+b"\n")


def storage():
    previous = [HERE.parent / ("attempt-"+str(i).zfill(3)) for i in range(6,10)]
    environments = [Path(read(p / "workspace.json")["directory"]) for p in previous if (p / "workspace.json").exists()]
    return {"previous_seconds": sum(read(p / "result.json")["cumulative_seconds"] for p in previous),
        "combined_bytes": sum(f.stat().st_size for p in [*previous, HERE, *environments] for f in p.rglob("*") if f.is_file()),
        "new_bytes": sum(f.stat().st_size for f in HERE.rglob("*") if f.is_file())}


def bindings():
    a = Authority(ROOT)
    program, tasks, _ = a.spec()
    task = tasks["source-bes-dep-05"]
    admitted = read(HERE / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT))
        and task.get("equity_readable_columns") == SELECTOR and admitted["program_sha256"] == digest(program)
        and admitted["task_spec"] == task and admitted["binding"] == a.binding(task), "Current unchanged equity-reading admission required")
    require(not (HERE / "outputs.json").exists(), "Equity reading already sealed")
    history = read(REVIEW / "history.json")
    require(all(file_hash(ROOT / p) == h for p, h in history["protected"].items()), "Prior source/evidence changed")
    require(files(ROOT / "src/legalmath") == history["package"], "Production files changed")
    if (HERE / "reading-methods.json").exists():
        require(all(file_hash(ROOT / p) == h for p, h in read(HERE / "reading-methods.json").items()), "Frozen reading review changed")
    return admitted


def period(label):
    if label in BALANCES:
        return {"kind": "BALANCE", "date": BALANCES[label]}
    at = LABELS.index(label)
    return {"kind": "MOVEMENT_OR_SUBTOTAL", "start": "2009-01-01" if at < 16 else "2009-07-01" if at < 26 else "2010-01-01",
        "end": "2009-06-30" if at < 16 else "2009-12-31" if at < 26 else "2010-06-30"}


def cell_value(raw, total=False):
    if total:
        return {"status": "SOURCE_INCOMPLETE", "value": None}
    text = "".join(raw.split())
    if text == "-":
        return {"status": "DASH_UNKNOWN", "value": None}
    require(re.fullmatch(r"(?:\d+|\(\d+\))", text) is not None, "Unexpected intact-cell numeric text")
    return {"status": "SOURCE_NUMBER", "value": -int(text[1:-1]) if text.startswith("(") else int(text)}


def map_source(units):
    require(len(units) == 463 and [u["order"] for u in units] == list(range(463)), "Original463 ordered occurrences required")
    rows = [{"label": i, "period": period(i), "cells": []} for i in LABELS]
    cells = [u for u in units if u["bbox"][0] >= 200 and 145 < u["bbox"][1] < 465]
    assigned = {}
    for cell in cells:
        cy = (cell["bbox"][1]+cell["bbox"][3])/2
        distances = sorted((abs((units[i]["bbox"][1]+units[i]["bbox"][3])/2-cy), i) for i in LABELS)
        require(distances[0][0] < 0.6 and distances[1][0]-distances[0][0] > 1, "Ambiguous or distant statement row")
        col = sum(cell["bbox"][0] >= x for x in (270,310,350,395,438,483,525,585,625))
        key = (distances[0][1], col)
        require(key not in assigned, "Multiple native occurrences in one statement cell")
        assigned[key] = cell["order"]
    require(len(cells) == 386 and sum(col < 9 for _,col in assigned) == 351, "Complete intact-column census required")
    require([(i,c) for i in LABELS for c in range(10) if (i,c) not in assigned] == [(i,9) for i in MISSING_TOTAL], "Unexpected missing statement cell")
    for row in rows:
        for col, name in enumerate(COLUMNS):
            index = assigned.get((row["label"], col))
            row["cells"].append({"column": name, "source_unit": index,
                "raw": None if index is None else units[index]["raw"],
                **cell_value("" if index is None else units[index]["raw"], col == 9)})
    used = set(LABELS) | set(assigned.values())
    metadata = [i for i in range(463) if i not in used]
    require(len(metadata) == 38 and all(i in metadata for header in HEADERS for i in header), "Original headers/metadata missing")
    return rows, metadata


def make_profile(units, prior):
    rows, metadata = map_source(units)
    return {"version": SELECTOR["version"], "source_units_sha256": digest(units), "prior_sha256": digest(prior),
        "columns": [{"name": name, "header_units": HEADERS[i]} for i,name in enumerate(COLUMNS)],
        "rows": rows, "metadata_units": metadata, "unit": {"source_unit": 35, "raw": units[35]["raw"],
            "scale": "thousands", "currency": None, "reason": "Currency suffix truncated on this page"},
        "footnotes": deepcopy(FOOTNOTES), "limits": deepcopy(LIMITS),
        "note_dependencies": ["12", "37", "38"], "source_review_basis": "AGENT_EXPOSED_DEVELOPMENT_READING"}


def evaluate_reading(units, prior, p, expected_pin):
    require(digest(p) == expected_pin and p["source_units_sha256"] == digest(units)
        and p["prior_sha256"] == digest(prior), REFUSALS["stale-pin"])
    require(p["limits"] == LIMITS and p["source_review_basis"] == "AGENT_EXPOSED_DEVELOPMENT_READING",
        REFUSALS["selected-incorporation"])
    expected_rows, metadata = map_source(units)
    require(p["columns"] == [{"name": name, "header_units": HEADERS[i]} for i,name in enumerate(COLUMNS)], REFUSALS["swapped-columns"])
    require([r["label"] for r in p["rows"]] == LABELS, REFUSALS["omitted-row"])
    for row, original in zip(p["rows"], expected_rows):
        require(row["period"] == original["period"], REFUSALS["wrong-period"])
        require(len(row["cells"]) == 10, REFUSALS["duplicate-cell"])
        for col, (cell, target) in enumerate(zip(row["cells"], original["cells"])):
            require({k: cell[k] for k in ("column", "source_unit", "raw")} == {k: target[k] for k in ("column", "source_unit", "raw")}, REFUSALS["duplicate-cell"])
            if col == 9:
                require(cell["status"] == "SOURCE_INCOMPLETE" and cell["value"] is None, REFUSALS["clipped-total-as-number"])
            elif target["status"] == "DASH_UNKNOWN":
                require(cell["status"] == "DASH_UNKNOWN" and cell["value"] is None, REFUSALS["dash-as-zero"])
            else:
                require(cell["status"] == target["status"] and type(cell["value"]) is int and cell["value"] == target["value"], REFUSALS["changed-number"])
    used = p["metadata_units"]+[r["label"] for r in p["rows"]]+[c["source_unit"] for r in p["rows"] for c in r["cells"] if c["source_unit"] is not None]
    require(p["metadata_units"] == metadata and Counter(used) == Counter(range(463)), REFUSALS["missing-metadata"])
    require(p["unit"] == {"source_unit": 35, "raw": units[35]["raw"], "scale": "thousands", "currency": None,
        "reason": "Currency suffix truncated on this page"}, "Original clipped unit must remain explicit")
    require(p["footnotes"] == FOOTNOTES and p["note_dependencies"] == ["12", "37", "38"], REFUSALS["preference-as-note-coupon"])
    balances = []
    for row in p["rows"]:
        if row["label"] not in BALANCES:
            continue
        cells = row["cells"]
        require(all(c["status"] == "SOURCE_NUMBER" for c in cells[:9]), "Four complete intact balance rows required")
        computed = sum(c["value"] for c in cells[:7])
        balances.append({"date": BALANCES[row["label"]], "component_sum": computed,
            "printed_bank_holders_equity": cells[7]["value"], "difference": computed-cells[7]["value"],
            "non_controlling_interest": cells[8]["value"], "total_equity": None,
            "cell_units": [c["source_unit"] for c in cells], "diagnostic_role": "INTERNAL_CONSISTENCY_ONLY"})
    require(all(r["difference"] == 0 for r in balances), "Bank-equity component identity requires source review")
    statuses = dict(Counter(c["status"] for r in p["rows"] for c in r["cells"]))
    return {"status": "PARTIAL_SOURCE_READING", "profile_sha256": digest(p), "source_units": deepcopy(units),
        "rows": deepcopy(p["rows"]), "columns": deepcopy(p["columns"]), "metadata_units": metadata,
        "unit": deepcopy(p["unit"]), "footnotes": deepcopy(p["footnotes"]), "note_dependencies": p["note_dependencies"],
        "limits": deepcopy(LIMITS), "cell_statuses": statuses, "balances": balances,
        "all463_original_occurrences_and_characters_once": True, "missing_total_positions": MISSING_TOTAL}


def prepare():
    units, prior = read(NATIVE), load(SCOPE / "scope-consumer.json.gz")
    require(read(DIAGNOSIS / "verified-analysis.json")["classification"] == "ENCODED_STRINGS_TRUNCATED", "Prior source diagnosis required")
    profile = make_profile(units, prior)
    save("draft-profile.json", profile)
    save("source-units.json", units)
    save("source-pins.json", {"units": file_hash(NATIVE), "image": file_hash(SCOPE / "equity-059.png"),
        "prior": file_hash(SCOPE / "scope-consumer.json.gz"), "diagnosis": file_hash(DIAGNOSIS / "verified-analysis.json")})
    lines = ["label | period | source label | " + " | ".join(COLUMNS)]
    for row in profile["rows"]:
        lines.append(str(row["label"])+" | "+json.dumps(row["period"])+" | "+units[row["label"]]["raw"]+" | "+" | ".join(
            "MISSING" if c["source_unit"] is None else str(c["source_unit"])+":"+c["raw"] for c in row["cells"]))
    (HERE / "mapped-table.txt").write_text("\n".join(lines)+"\n")
    return {"rows": 39, "intact_cells": 351, "total_fragments": 35, "missing_total": 4, "metadata": 38}


def profile():
    for name in ("SOURCE-REVIEW.md", "IMPLEMENTATION-REVIEW.md"):
        require((HERE / name).is_file(), "Actual source and implementation review required")
    p = read(HERE / "draft-profile.json")
    require(p == make_profile(read(NATIVE), load(SCOPE / "scope-consumer.json.gz")), "Draft must preserve original values")
    save("profile.json", p)
    save("profile-pin.json", {"sha256": digest(p)})
    save("reading-methods.json", {str(path.relative_to(ROOT)): file_hash(path) for path in
        (Path(__file__), HERE / "SOURCE-REVIEW.md", HERE / "IMPLEMENTATION-REVIEW.md", HERE / "mapped-table.txt", HERE / "draft-profile.json")})
    save("intended-refusals.json", REFUSALS)
    return {"frozen": True, "actual_controls_required": 12}


def evaluate():
    result = evaluate_reading(read(NATIVE), load(SCOPE / "scope-consumer.json.gz"), read(HERE / "profile.json"), read(HERE / "profile-pin.json")["sha256"])
    save("reading.json.gz", result)
    save("reading-summary.json", {"rows": len(result["rows"]), "source_occurrences": 463,
        "cell_statuses": result["cell_statuses"], "balances": result["balances"], "limits": result["limits"]})
    return {"status": result["status"], "cell_statuses": result["cell_statuses"], "balance_checks": len(result["balances"])}


def altered(p, name):
    v = deepcopy(p)
    if name == "changed-number": v["rows"][0]["cells"][0]["value"] += 1
    elif name == "dash-as-zero": v["rows"][1]["cells"][0].update(status="SOURCE_NUMBER", value=0)
    elif name == "clipped-total-as-number": v["rows"][0]["cells"][9].update(status="SOURCE_NUMBER", value=465294)
    elif name == "omitted-row": v["rows"].pop()
    elif name == "duplicate-cell": v["rows"][0]["cells"][1] = deepcopy(v["rows"][0]["cells"][0])
    elif name == "swapped-columns": v["columns"][0],v["columns"][1] = v["columns"][1],v["columns"][0]
    elif name == "wrong-period": v["rows"][19]["period"]["start"] = "2009-01-01"
    elif name == "preference-as-note-coupon": v["footnotes"]["preference"]["note_coupon"] = True
    elif name == "wrong-dividend-year": v["footnotes"]["ordinary"]["per_share"][0]["year"] = 2009
    elif name == "selected-incorporation": v["limits"]["actual_incorporation_resolved"] = True
    elif name == "missing-metadata": v["metadata_units"].pop()
    elif name == "stale-pin": v["rows"][0]["cells"][0]["value"] += 1
    else: raise ValueError("Unreviewed equity control")
    return v


def controls():
    units, prior, p = read(NATIVE), load(SCOPE / "scope-consumer.json.gz"), read(HERE / "profile.json")
    results = []
    for name, reason in REFUSALS.items():
        value = altered(p, name)
        pin = digest(p) if name == "stale-pin" else digest(value)
        save("adverse-inputs/"+name+".json", {"profile": value, "expected_pin": pin})
        try:
            evaluate_reading(units, prior, value, pin)
        except ValueError as exc:
            row = {"case": name, "refused": True, "repinned": name != "stale-pin", "reason": str(exc)}
            save("adverse-results/"+name+".json", row)
            require(str(exc) == reason, "Unintended equity refusal: "+name+": "+str(exc))
            results.append(row)
        else:
            raise ValueError("Invalid equity reading accepted: "+name)
    save("actual-controls.json", results)
    return {"actual_refusals": len(results), "repinned": sum(r["repinned"] for r in results)}


def answer():
    prior, reading = load(SCOPE / "scope-consumer.json.gz"), load(HERE / "reading.json.gz")
    q3, dependencies = prior["answer"]["questions"]["Q3"], prior["answer"]["dependencies"]
    require(q3["status"] == "PARTIAL" and len(dependencies) == 432
        and prior["answer"]["may_execute_transaction"] is False, "Original partial answer required")
    original_ids = {"BES-DEP-"+str(i).zfill(2) for i in range(1,12)} | {"BES-DEP-AGENCY-"+str(i).zfill(2) for i in range(1,4)}
    original = [d for d in dependencies if d["id"] in original_ids]
    require(len(original) == 14 and all(d["status"] == "UNRESOLVED" for d in original), "All14 original BES dependencies required")
    explanation = {"question": "What remains readable on the equity statement under each incorporation construction?",
        "incorporation": [{"construction": c["id"], "page59_included": 59 in c["pages"],
            "legal_selection": False} for c in prior["h1_scope_review"]["candidates"]],
        "readable_evidence": {"rows": 39, "intact_columns": COLUMNS[:9], "intact_cell_positions": 351,
            "cell_statuses": reading["cell_statuses"], "balance_component_checks": reading["balances"]},
        "unit": reading["unit"], "ordinary_share_dividends": reading["footnotes"]["ordinary"],
        "preference_share_dividend": reading["footnotes"]["preference"],
        "financial_interpretation": ["Four complete Bank-equity component sums agree with the printed attributable-equity balances.",
            "Dashes remain unknown; subtotal, capital-increase subitem, flow and balance rows must not be double-counted.",
            "Second-half2009 profit flow and full-year2009 closing profit balance describe different periods.",
            "All39 total-equity positions remain unresolved; component arithmetic is not a source transcription.",
            "The ordinary and preference dividend footnotes do not establish a bond coupon or BES Finance standalone accounts."],
        "required_note_readings": ["12", "37", "38"], "notes_are_integral": True,
        "answer_status": "PARTIAL", "original_dependency_resolution": "UNCHANGED",
        "limits": deepcopy(LIMITS)}
    supplement = {**prior, "h1_equity_agent_reading": reading, "h1_equity_agent_explanation": explanation}
    require({k: supplement[k] for k in prior} == prior, "Complete original consumer changed")
    save("answer-supplement.json.gz", supplement)
    save("answer-explanation.json", explanation)
    save("comparison.json", {"complete_prior_consumer_equal": True, "prior_sha256": digest(prior),
        "supplement_sha256": digest(supplement), "dependencies_preserved": 432,
        "original_BES_dependencies_unresolved": 14, "Q3": "PARTIAL", "production_integration_claimed": False})
    return {"complete_prior_consumer_equal": True, "Q3": "PARTIAL", "source_reading_added": True}


def seal():
    require((HERE / "RESULT.md").is_file(), "Actual substantive interpretation and result required")
    controls = read(HERE / "actual-controls.json")
    require(len(controls) == 12 and all(r["reason"] == REFUSALS[r["case"]] for r in controls), "All actual refusals required")
    require(read(HERE / "comparison.json")["complete_prior_consumer_equal"], "Complete prior comparison required")
    save("verified-result.json", {**read(HERE / "reading-summary.json"), **read(HERE / "comparison.json"),
        "actual_refusals": len(controls), "repinned": 11, "source_actions_added": 0,
        "task_complete": False, "result_sha256": file_hash(HERE / "RESULT.md")})
    return {"substantive_reading_retained": True, "task_complete": False}


def run(stage):
    with Authority(ROOT).lock():
        admitted = bindings()
        index = STAGES.index(stage)
        started = {p.parent.name for p in (HERE / "stages").glob("*/started.json")}
        ended = {p.parent.name for p in (HERE / "stages").glob("*/result.json")}
        require(started == ended == set(STAGES[:index]), "Repeated/skipped/interrupted equity-reading stage")
        rows = [read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < 115 for r in rows), "Failed reading predecessor")
        spent, limits = sum(r["wall_seconds"] for r in rows), storage()
        require(spent < 600 and limits["previous_seconds"]+spent < 1800
            and limits["new_bytes"] < 79*1024**2 and limits["combined_bytes"] < 698*1024**2, "Cumulative reading bounds exhausted")
        save("stages/"+stage+"/started.json", {"command": ["timeout", "120", ".venv/bin/python", "-m", "scripts.prospectus_h1_equity_reading", stage],
            "at": datetime.now(timezone.utc).isoformat(), "git_commit": admitted["git_commit"], "python": sys.executable,
            "cpu_gpu": "CPU only; GPU devices intentionally hidden", "random_seeds": "N/A deterministic supplied source reading",
            "plan": PLAN, "data_version": str((SCOPE / "outputs.json").relative_to(ROOT)), "result": str((HERE / "RESULT.md").relative_to(ROOT))})
        tick, details, error = time.monotonic(), None, None
        def expire(signum, frame):
            raise TimeoutError("Equity reading time bound; no unchanged retry")
        old = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(110, 600-spent, 1800-limits["previous_seconds"]-spent))
        try:
            with execution_guard() as guard:
                details = globals()[stage]()
                require(guard.result() == {"starts": 0, "blocked": 0}, "Unexpected process/network action")
            bindings()
            elapsed, current = time.monotonic()-tick, storage()
            require(elapsed < 115 and spent+elapsed < 600 and limits["previous_seconds"]+spent+elapsed < 1800
                and current["new_bytes"] < 79*1024**2 and current["combined_bytes"] < 698*1024**2, "Equity reading bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/"+stage+"/error.json", {"traceback": traceback.format_exc()})
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
        value = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error,
            "details": details, "wall_seconds": time.monotonic()-tick, "bounds": storage()}
        value["cumulative_seconds"] = spent+value["wall_seconds"]
        save("stages/"+stage+"/result.json", value)
        if error or stage == "seal":
            save("result.json", {**value, "task": "source-bes-dep-05", "task_complete": False,
                "whole_program_complete": False, "independent_legal_acceptance": False})
            save("outputs.json", files(HERE))
        print(json.dumps({k: value[k] for k in ("stage", "status", "error", "wall_seconds", "cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    require(len(sys.argv) == 2 and sys.argv[1] in STAGES, "Choose equity-reading prepare/profile/evaluate/controls/answer/seal")
    raise SystemExit(run(sys.argv[1]))
