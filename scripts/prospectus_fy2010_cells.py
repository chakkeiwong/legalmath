"""Admitted finite FY2010 source-cell reading and whole-source report comparison."""
import argparse
from collections import Counter
from copy import deepcopy
import csv
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
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from legalmath.prospectus.execution_authority import Authority, digest as authority_digest, file_hash, read as plain, write
from legalmath.prospectus.successor import service, report_scope, reviewed_references
from legalmath.prospectus.successor.contracts import digest

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
ORIGINAL = BASE / "attempts/source-bes-dep-08/attempt-001"
SECOND = ORIGINAL.parent / "attempt-002"
REVIEW = BASE / "reviews/fy2010-cells-139"
SOURCE = "b28420dced99cbb219a3f447ed43fa603d6ae1bc0086fb7705876e25631a569f"
DOCUMENT = "bes-release-fy10"
PLAN = "docs/plans/prospectus-fy2010-statement-cells-2026-10-16.md"
PERIODS = {41: ["2009-12-31", "2010-06-30", "2010-12-31"],
           42: ["year_ended_2009-12-31", "year_ended_2010-12-31"]}
WINDOWS = {41: [(350, 410), (414, 475), (479, 540)], 42: [(410, 472), (480, 542)]}
BODY = {41: (150, 778), 42: (178, 620)}
PROTECTED = ("questions", "dependencies", "assembly", "source_map",
             "independent_legal_acceptance", "may_execute_transaction")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith(".gz") else raw)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(gzip.compress(raw, mtime=0) if path.suffix == ".gz" else raw)


def no_process(event, args):
    if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec", "os.fork"}:
        raise RuntimeError("FY2010 package forbids subprocesses: " + event)


def methods():
    files = list((ROOT / "src/legalmath/prospectus").rglob("*.py")) + [Path(__file__)]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in sorted(files)}


def inputs():
    return {**read(REVIEW / "reviewed-inputs.json")["inputs"],
            **{str(p.relative_to(ROOT)): file_hash(p) for p in (REVIEW / "printed-cells.tsv", ROOT / PLAN)}}


def specs():
    with (REVIEW / "printed-cells.tsv").open() as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def source():
    value = read(ORIGINAL / "source-product.json.gz")
    service.verify(value, "P1")
    require(file_hash(ORIGINAL / "release.pdf") == SOURCE, "Original release changed")
    graph = value["payload"]["graph"]
    selected = sorted((u for u in graph["units"] if u["document"] == DOCUMENT and u["page"] in (41, 42)),
                      key=lambda u: (u["page"], u["order"], u["id"]))
    require(len(selected) == 300 and len({u["id"] for u in selected}) == 300, "Original page denominator changed")
    require(all(u["visible"] and u["source_sha256"] == SOURCE for u in selected), "Wrong or invisible source occurrence")
    return graph, selected


def anchor(unit):
    return {"source_unit": unit["id"], "source_sha256": unit["source_sha256"],
            "page": unit["page"], "start": 0, "end": len(unit["raw"]),
            "quote": unit["raw"], "bbox": unit["bbox"],
            "word_spans": [[w["start"], w["end"]] for w in unit["words"]]}


def semantic(literal):
    if literal == "-":
        return {"status": "PRINTED_DASH_UNKNOWN", "value": None, "sign_context": "UNKNOWN"}
    require(bool(re.fullmatch(r"(?:[0-9][0-9 ]*|\([ 0-9]+\))", literal)), "Unexpected numeric literal: " + literal)
    value = int(literal.strip("()").replace(" ", ""))
    return {"status": "PRINTED_AMOUNT", "value": -value if literal.startswith("(") else value,
            "sign_context": "PARENTHESIZED_NEGATIVE" if literal.startswith("(") else "POSITIVE_PRINTED"}


def numeric(units):
    return [u for u in units if BODY[u["page"]][0] <= u["bbox"][1] <= BODY[u["page"]][1]
            and u["bbox"][0] >= WINDOWS[u["page"]][0][0]]


def make_reading(graph, units, transcription):
    require(Counter(int(s["page"]) for s in transcription) == {41: 48, 42: 28}, "Image row inventory differs")
    used, rows = {}, []
    numbers = numeric(units)
    require(len(numbers) == 200, "Numeric occurrence denominator differs")
    for spec in transcription:
        pg = int(spec["page"])
        labels = sorted((u for u in units if u["page"] == pg and u["raw"] == spec["label"] and u["id"] not in used),
                        key=lambda u: u["bbox"][1])
        require(bool(labels), "Missing printed label: " + spec["label"])
        label = labels[0]
        row_id = "p{}-r{:02d}".format(pg, 1 + sum(r["page"] == pg for r in rows))
        used[label["id"]] = {"role": "ROW_LABEL", "row": row_id}
        cells = []
        for i, (left, right) in enumerate(WINDOWS[pg]):
            candidates = [u for u in numbers if u["page"] == pg and abs(u["bbox"][1] - label["bbox"][1]) < 2
                          and left <= (u["bbox"][0] + u["bbox"][2]) / 2 < right]
            require(len(candidates) == 1, "Ambiguous/missing printed cell: " + spec["label"])
            cell = candidates[0]
            require(cell["id"] not in used, "Source occurrence used twice")
            printed = spec[("first", "second", "third")[i]]
            require("".join(cell["raw"].split()) == "".join(printed.split()), "Image transcription mismatch: " + spec["label"])
            require(all(left <= (w["bbox"][0] + w["bbox"][2]) / 2 < right for w in cell["words"]), "Cell crosses period boundary")
            used[cell["id"]] = {"role": "NUMERIC_CELL", "row": row_id, "period": PERIODS[pg][i]}
            cells.append({"period": PERIODS[pg][i], "unit": "EUR_thousands", "source": anchor(cell), **semantic(cell["raw"])})
        non_additive = spec["role"] == "MEMORANDUM_SIGNED"
        parent = rows[-1]["row_id"] if non_additive else None
        require(not non_additive or rows[-1]["label"] == "Net income", "Memorandum parent differs")
        rows.append({"row_id": row_id, "page": pg, "section": spec["section"], "label": spec["label"],
                     "label_source": anchor(label), "role": spec["role"], "non_additive": non_additive,
                     "parent_row": parent, "cells": cells})
    allowed = {
        41: Counter({"BANCO ESPÍRITO SANTO, S.A.": 1, "CONSOLIDATED BALANCE SHEET AS OF 31 DECEMBER 2010": 1,
                     "Dec. 09": 1, "Jun.10": 1, "Dec. 10": 1, "(eur '000)": 3,
                     "ASSETS": 1, "LIABILITIES": 1, "EQUITY": 1, "2010FY Results Release": 1,
                     "Lisbon, 31 January 2011": 1, "Page 41 of 42": 1}),
        42: Counter({"BANCO ESPÍRITO SANTO, S.A.": 1, "CONSOLIDATED INCOME STATEMENT": 1,
                     "2009": 1, "2010": 1, "(eur '000)": 2, "Income tax": 1,
                     "2010FY Results Release": 1, "Lisbon, 31 January 2011": 1, "Page 42 of 42": 1}),
    }
    remaining = [u for u in units if u["id"] not in used]
    for pg in (41, 42):
        require(Counter(u["raw"] for u in remaining if u["page"] == pg) == allowed[pg], "Unaccounted/changed page context")
    tables = {}
    for pg, headers in ((41, ["Dec. 09", "Jun.10", "Dec. 10"]), (42, ["2009", "2010"])):
        header_units = sorted((u for u in remaining if u["page"] == pg and u["raw"] in headers), key=lambda u: u["bbox"][0])
        require([u["raw"] for u in header_units] == headers, "Wrong column order")
        unit_headers = sorted((u for u in remaining if u["page"] == pg and u["raw"] == "(eur '000)"), key=lambda u: u["bbox"][0])
        tables[str(pg)] = {"periods": PERIODS[pg], "headers": [anchor(u) for u in header_units],
                           "units": [anchor(u) for u in unit_headers], "measure": "STOCK_AT_DATE" if pg == 41 else "ANNUAL_FLOW"}
    for unit in remaining:
        used[unit["id"]] = {"role": "HEADER_OR_CONTEXT", "source": anchor(unit)}
    require(set(used) == {u["id"] for u in units}, "Page occurrence accounting differs")
    return {"version": "bes-fy2010-source-cell-reading.v1", "source_sha256": SOURCE,
            "graph_sha256": digest(graph), "page_occurrences_sha256": authority_digest(units),
            "tables": tables, "rows": rows, "occurrence_inventory": used,
            "source_context": {"unaudited_source": True, "printed_release_date": "2011-01-31",
                "source_authenticity": "NOT_ESTABLISHED", "independent_financial_review": False,
                "incorporation_status": "UNRESOLVED", "context_pages_do_not_expand_incorporation": True},
            "production_consumed": False, "independent_review": False}


def validate_reading(value, graph, units, transcription):
    require(value == make_reading(graph, units, transcription), "Reading differs from complete source-bound transcription")
    spans = [(c["source"]["source_unit"], a, b) for r in value["rows"] for c in r["cells"] for a, b in c["source"]["word_spans"]]
    expected = [(u["id"], w["start"], w["end"]) for u in numeric(units) for w in u["words"]]
    require(Counter(spans) == Counter(expected) and len(spans) == len(set(spans)), "Numeric words omitted/reused")
    return {"rows": 76, "cells": 200, "numeric_words": len(spans), "source_page_occurrences": 300}


def arithmetic(value):
    def row(pg, label):
        match, = [r for r in value["rows"] if r["page"] == pg and r["label"] == label]
        result = [c["value"] for c in match["cells"]]
        require(all(v is not None for v in result), "No imputed dash allowed in arithmetic")
        return result
    equations = [(41, "TOTAL ASSETS", [(1, "TOTAL LIABILITIES"), (1, "TOTAL EQUITY")]),
        (41, "TOTAL ASSETS", [(1, "TOTAL LIABILITIES AND EQUITY")]),
        (42, "Net interest income", [(1, "Interest and similar income"), (-1, "Interest expense and similar charges")]),
        (42, "Net income", [(1, "Net income before income tax and minorities"), (-1, "Current tax"), (-1, "Deferred tax")]),
        (42, "Consolidated net income for the period", [(1, "Net income"), (-1, "Minority interests")])]
    results = []
    for pg, label, terms in equations:
        lhs = row(pg, label)
        rhs = [sum(sign * row(pg, name)[i] for sign, name in terms) for i in range(len(lhs))]
        results.append({"page": pg, "reported_row": label, "terms": terms, "reported": lhs,
                        "computed": rhs, "residual_EUR_thousands": [a-b for a, b in zip(lhs, rhs)]})
    return {"role": "EXPLANATORY_ONLY", "checks": results, "full_sum_with_unknown_dashes": "NOT_COMPUTED",
            "financial_truth_certified": False}


def cells(folder):
    graph, units = source()
    transcription = specs()
    value = make_reading(graph, units, transcription)
    counts = validate_reading(value, graph, units, transcription)
    save(folder / "cell-reading.json", value)
    save(folder / "arithmetic.json", arithmetic(value))
    controls = {}
    for name in ("omitted-cell", "swapped-period", "dash-as-zero", "positive-expense-negated", "additive-memorandum",
                 "wrong-memorandum-parent", "changed-amount", "changed-source-span", "duplicated-word", "omitted-context",
                 "wrong-unit", "unaudited-erased", "false-production-integration", "quarter-for-year"):
        bad = deepcopy(value)
        first = bad["rows"][0]["cells"][0]
        if name == "omitted-cell": bad["rows"][0]["cells"].pop()
        elif name == "swapped-period": first["period"] = PERIODS[41][1]
        elif name == "dash-as-zero": next(c for r in bad["rows"] for c in r["cells"] if c["value"] is None)["value"] = 0
        elif name == "positive-expense-negated": next(r for r in bad["rows"] if r["role"] == "EXPENSE")["cells"][0]["value"] *= -1
        elif name == "additive-memorandum": next(r for r in bad["rows"] if r["non_additive"])["non_additive"] = False
        elif name == "wrong-memorandum-parent": next(r for r in bad["rows"] if r["non_additive"])["parent_row"] = "p42-r01"
        elif name == "changed-amount": first["value"] += 1
        elif name == "changed-source-span": first["source"]["start"] += 1
        elif name == "duplicated-word": first["source"]["word_spans"].append(first["source"]["word_spans"][0])
        elif name == "omitted-context": bad["occurrence_inventory"].pop(next(iter(bad["occurrence_inventory"])))
        elif name == "wrong-unit": first["unit"] = "EUR"
        elif name == "unaudited-erased": bad["source_context"]["unaudited_source"] = False
        elif name == "false-production-integration": bad["production_consumed"] = True
        else: bad["tables"]["42"]["measure"] = "QUARTER_FLOW"
        save(folder / "cell-controls" / (name + ".json.gz"), bad)
        try:
            validate_reading(bad, graph, units, transcription)
        except ValueError as exc:
            controls[name] = {"rejected": True, "reason": str(exc)}
        else: raise ValueError("Invalid reading accepted: " + name)
    save(folder / "cell-controls.json", controls)
    return {"counts": counts, "adverse_rejections": len(controls), "production_cell_integration": False}


def products(p1, p2, supplied):
    p3 = service.interpretation_product(p1, p2, supplied)
    return {"P1": p1, "P2": p2, "P3": p3, "P4": service.law_product(p1, p3), "P5": service.financial_product(p1, p2, p3)}


def consumers(folder):
    graph, units = source()
    validate_reading(read(folder / "cell-reading.json"), graph, units, specs())
    request = read(ORIGINAL / "request-with-readings.json")
    p1 = service.seal("P1", request["bundle"], {"request": digest(request)}, {"request": request, "graph": graph})
    p2 = service.construction_product(p1, ROOT)
    require(p2["payload"]["source_report_readings"] == read(ORIGINAL / "selected-reading.json"), "Complete original report reading changed")
    reference = read(ORIGINAL / "reference-admission.json")
    base_scope = read(ORIGINAL / "scope-admission.json")
    corrected = read(SECOND / "corrected-original-scope.json")
    save(folder / "P1.json.gz", p1)
    save(folder / "P2.json.gz", p2)
    results = {}
    for mode, scope in (("baseline", base_scope), ("corrected", corrected)):
        values = products(p1, p2, {"source_report_scope": scope, "reference_admission": reference})
        for stage in ("P3", "P4", "P5"): save(folder / (mode + "-" + stage + ".json.gz"), values[stage])
        answer = service.consume(values, ROOT, mode="frozen", include_artifacts=True)
        save(folder / (mode + "-answer.json.gz"), answer)
        results[mode] = (values, answer)
    baseline, current = results["baseline"][1], results["corrected"][1]
    checks = {k: baseline[k] == current[k] for k in PROTECTED}
    checks.update({"law_payload": results["baseline"][0]["P4"]["payload"] == results["corrected"][0]["P4"]["payload"],
                   "financial_payload": results["baseline"][0]["P5"]["payload"] == results["corrected"][0]["P5"]["payload"]})
    require(all(checks.values()), "Matched whole-source surrounding answer changed: " + str(checks))
    report, = current["source_reports"]
    require(current["source_reports"] == read(SECOND / "corrected-original-explanation.json.gz"), "Corrected original source report differs")
    require(report["use_assessment"]["unaudited_financial_release"] == "SUPPLIED_SOURCE_DESCRIPTION"
            and report["facts"]["conclusion"]["status"] == "UNKNOWN", "Unaudited source description or independent conclusion changed")
    require(current["questions"]["Q3"]["status"] == "PARTIAL" and not current["may_execute_transaction"]
            and not current["independent_legal_acceptance"], "Unsupported legal promotion")
    ids = {d["id"] for d in request["bundle"]["dependencies"]}
    deps = {d["id"]: d for d in current["dependencies"]}
    require(len(ids) == 14 and all(deps[k]["status"] == "UNRESOLVED" for k in ids), "Original dependencies changed")
    link = deps["reviewed-reference:BES-DEP-08-conditional-statement-link"]
    require({t["unit"] for t in link["targets"]} == {u["id"] for u in units}, "Complete statement target differs")
    comparison = {"status": "PASS", "protected": checks, "whole_graph_units": len(graph["units"]),
        "statement_units": len(units), "original_dependencies_unresolved": len(ids),
        "baseline_answer_sha256": baseline["report_sha256"], "corrected_answer_sha256": current["report_sha256"],
        "P1_source_mode": "RETAINED_ORIGINAL_PDF_GRAPH", "current_report_consumed": True,
        "cell_map_consumed_by_product": False, "new_native_calls": 0}
    save(folder / "consumer-comparison.json", comparison)
    return comparison


def controls(folder):
    p1, p2 = read(folder / "P1.json.gz"), read(folder / "P2.json.gz")
    scope = read(SECOND / "corrected-original-scope.json")
    reference = read(ORIGINAL / "reference-admission.json")
    cases = {}
    for name in ("audit-instead-of-release", "lost-unaudited-word", "wrong-target-source", "forged-source-product"):
        bad_scope, bad_reference = deepcopy(scope), deepcopy(reference)
        if name == "audit-instead-of-release":
            bad_scope["reports"][0]["facts"]["identity"]["value"] = "STATUTORY_FINANCIAL_AUDIT"
        elif name == "lost-unaudited-word":
            fact = bad_scope["reports"][0]["facts"]["assurance_level"]
            fact.update(status="UNKNOWN", reason="Deliberately withheld source word")
            fact.pop("value"); fact.pop("spans")
        elif name == "wrong-target-source":
            bad_reference["references"][0]["targets"][0]["source"]["source_sha256"] = "0" * 64
        else:
            bad = deepcopy(p1)
            next(u for u in bad["payload"]["graph"]["units"] if u["document"] == DOCUMENT and u["page"] == 41)["raw"] = "Forged"
            save(folder / "consumer-controls" / (name + ".json.gz"), bad)
            try: service.verify(bad, "P1")
            except ValueError as exc: cases[name] = {"rejected": True, "reason": str(exc)}
            else: raise ValueError("Forged original source accepted")
            continue
        save(folder / "consumer-controls" / (name + "-input.json"), {"scope": bad_scope, "reference": bad_reference})
        if name == "lost-unaudited-word":
            values = products(p1, p2, {"source_report_scope": bad_scope, "reference_admission": bad_reference})
            answer = service.consume(values, ROOT, mode="frozen", include_artifacts=True)
            save(folder / "consumer-controls" / (name + "-answer.json.gz"), answer)
            require(answer["source_reports"][0]["use_assessment"]["unaudited_financial_release"] == "NOT_ESTABLISHED_BY_THIS_READING",
                    "Missing qualification still supported")
            positive = read(folder / "corrected-answer.json.gz")
            require(all(answer[k] == positive[k] for k in PROTECTED), "Adverse surrounding answer differs")
            cases[name] = {"withheld": True, "actual_current_consumer": True}
        else:
            try: service.interpretation_product(p1, p2, {"source_report_scope": bad_scope, "reference_admission": bad_reference})
            except ValueError as exc: cases[name] = {"rejected": True, "reason": str(exc)}
            else: raise ValueError("Invalid original-source admission accepted: " + name)
    save(folder / "consumer-controls.json", cases)
    return {"cases": len(cases), "actual_adverse_consumer": 1}


def run(attempt, stage):
    global REVIEW, PLAN
    authority = Authority(ROOT)
    folder = authority.path(attempt)
    ad = plain(folder / "admission.json")
    program, tasks, _ = authority.spec()
    task = tasks["source-bes-dep-08"]
    event = next(e for e in reversed(authority.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == attempt and ad["binding"] == authority.binding(task)
            and ad["task_sha256"] == authority_digest(task) and ad["program_sha256"] == authority_digest(program), "Current unchanged admission required")
    require(not (folder / "outputs.json").exists(), "Sealed attempt refused")
    REVIEW = authority.path(task["cell_review"])
    PLAN = task["dossier"]
    require(all(str((REVIEW / n).relative_to(ROOT)) in task["inputs"] for n in
                ("printed-cells.tsv", "reviewed-inputs.json")), "Reviewed transcription inputs must be admitted")
    historical = []
    historical_bytes = 0
    for name in task.get("cell_repair_history", []):
        old = authority.path(name)
        terminal = next(e for e in reversed(authority.events()) if e.get("attempt") == name)
        require(terminal["kind"] == "REJECT" and authority.retained_evidence_valid(terminal), "Rejected repair history changed")
        old_results = [read(p) for p in sorted((old / "stages").glob("*/result.json"))]
        require(len(list((old / "stages").glob("*/started.json"))) == len(old_results), "Interrupted historical stage")
        historical += old_results
        historical_bytes += sum(p.stat().st_size for p in old.rglob("*") if p.is_file())
    runs = sorted((folder / "stages").glob("*/result.json"))
    require(len(list((folder / "stages").glob("*/started.json"))) == len(runs)
            and len(runs) + len(historical) < 5, "Cumulative stage bound/interrupted stage")
    spent = sum(read(p)["wall_seconds"] for p in runs) + sum(r["wall_seconds"] for r in historical)
    require(spent < 480, "Cumulative execution bound exceeded")
    target = folder / "stages" / stage
    require(not target.exists(), "Duplicate stage refused")
    if stage not in ("cells", "resume-consumers"):
        prior_stage = "resume-consumers" if task.get("cell_recovery_attempt") else "cells"
        require(read(folder / "stages" / prior_stage / "result.json")["status"] == "PASS", "Mapping/consumer predecessor must pass")
        require(read(folder / "methods.json") == methods(), "Frozen methods changed")
    frozen = methods()
    pinned = inputs()
    require(all(file_hash(ROOT / p) == h for p, h in pinned.items()), "Retained input changed")
    if stage in ("cells", "resume-consumers"):
        save(folder / "methods.json", frozen)
        save(folder / "method-snapshots.json.gz", {p: (ROOT / p).read_text() for p in frozen})
    save(target / "started.json", {"at": datetime.now(timezone.utc).isoformat(), "command": ["timeout", "120", ".venv/bin/python",
        "scripts/prospectus_fy2010_cells.py", "--attempt", attempt, "--stage", stage],
        "interpreter": sys.executable, "module": service.__file__, "git_commit": ad["git_commit"],
        "inputs": pinned, "methods": frozen, "plan": PLAN, "result": str((target / "result.json").relative_to(ROOT)),
        "historical_stages": historical, "prior_recorded_stage_seconds": spent,
        "cpu_gpu": "CPU only; GPU intentionally hidden", "random_seeds": "N/A deterministic source comparison"})
    tick, error, details = time.monotonic(), None, None
    try:
        require(Path(service.__file__).resolve().is_relative_to(ROOT / "src"), "Wrong product import")
        if stage == "cells": details = cells(folder)
        elif stage == "consumers": details = consumers(folder)
        elif stage == "resume-consumers":
            recovery = authority.path(task["cell_recovery_attempt"])
            recovered_event = next(e for e in reversed(authority.events()) if e.get("attempt") == task["cell_recovery_attempt"])
            require(recovered_event["kind"] == "REJECT" and authority.retained_evidence_valid(recovered_event), "Recovered map origin changed")
            require(read(recovery / "stages/cells/result.json")["status"] == "PASS", "Successful map required")
            old_methods = read(recovery / "methods.json")
            own_script = str(Path(__file__).relative_to(ROOT))
            require(set(old_methods) == set(frozen) and all(h == frozen[p] for p, h in old_methods.items() if p != own_script),
                    "Product methods changed since successful map")
            names = ["cell-reading.json", "arithmetic.json", "cell-controls.json"]
            names += [str(p.relative_to(recovery)) for p in sorted((recovery / "cell-controls").glob("*.json.gz"))]
            recovered = {}
            for name in names:
                target_file = folder / name
                target_file.parent.mkdir(parents=True, exist_ok=True)
                with target_file.open("xb") as stream: stream.write((recovery / name).read_bytes())
                recovered[name] = file_hash(target_file)
            save(folder / "cell-recovery.json", {"attempt": task["cell_recovery_attempt"], "event": recovered_event,
                "files": recovered, "successful_stage": read(recovery / "stages/cells/result.json")})
            details = {"consumer": consumers(folder), "controls": controls(folder),
                       "cell_controls_reused": 14, "production_cell_integration": False}
        elif stage == "controls":
            require(read(folder / "stages/consumers/result.json")["status"] == "PASS", "Original consumer must pass")
            details = controls(folder)
        elif stage == "seal":
            required_stages = ("resume-consumers",) if task.get("cell_recovery_attempt") else ("cells", "consumers", "controls")
            require(all(read(folder / "stages" / s / "result.json")["status"] == "PASS" for s in required_stages), "Incomplete evidence")
            require((folder / "RESULT.md").is_file(), "Reviewed actual result note required")
            details = {"new_native_calls": 0, "task_complete": False, "production_cell_integration": False}
        else: raise ValueError("Unknown stage")
        require(methods() == frozen and all(file_hash(ROOT / p) == h for p, h in pinned.items()), "Methods or inputs changed during execution")
        require(historical_bytes + sum(p.stat().st_size for p in folder.rglob("*") if p.is_file()) < 80 * 1024 * 1024, "Cumulative evidence cap exceeded")
        require(spent + time.monotonic() - tick < 480, "Cumulative execution cap exceeded")
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        (target / "error.log").write_text(traceback.format_exc())
    value = {"status": "PASS" if error is None else "FAIL", "stage": stage, "error": error,
             "wall_seconds": time.monotonic()-tick, "details": details}
    save(target / "result.json", value)
    if stage == "seal" or error:
        save(folder / "result.json", {**value, "task": task["id"], "whole_program_complete": False,
            "production_cell_integration": False, "independent_acceptance": False})
        save(folder / "outputs.json", {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*")) if p.is_file()})
    print(json.dumps({k: value[k] for k in ("status", "stage", "error", "wall_seconds")}))
    return int(error is not None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--stage", choices=("cells", "consumers", "controls", "resume-consumers", "seal"), required=True)
    args = parser.parse_args()
    sys.addaudithook(no_process)
    def expired(signum, frame): raise TimeoutError("FY2010 stage exceeded115 seconds")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(115)
    try: return run(args.attempt, args.stage)
    finally: signal.alarm(0)


if __name__ == "__main__": raise SystemExit(main())
