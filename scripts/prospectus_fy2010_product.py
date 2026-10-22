"""Bounded public-product evaluation of the retained FY2010 statement reading."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import difflib
import gzip
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
from legalmath.prospectus.execution_authority import Authority, digest as authority_digest, file_hash
from legalmath.prospectus.successor import service, statement_cells
from legalmath.prospectus.successor.contracts import digest

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
SOURCE = BASE / "attempts/source-bes-dep-08/attempt-005"
REVIEW = BASE / "reviews/fy2010-product-142"
STAGES = ("focused", "matched", "input-controls", "phase-controls", "prior-profiles", "seal")


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == ".gz" else data)


def size(folder):
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def save(folder, name, value, *, final=False):
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode()
    data = gzip.compress(raw, mtime=0) if name.endswith(".gz") else raw
    require(size(folder) + len(data) < (35 if final else 34) * 1024**2, "New evidence cap exceeded")
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def methods():
    paths = sorted((ROOT / "src/legalmath/prospectus").rglob("*.py"))
    paths += [Path(__file__), ROOT / "tests/prospectus_successor/test_statement_cells.py",
              ROOT / "tests/prospectus_successor/fixtures/bes_fy2010_statement_cells.json.gz",
              ROOT / "docs/prospectus/statement-cells.md"]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in paths}


def p1_from(request, graph):
    return service.seal("P1", request["bundle"], {"request": digest(request)}, {"request": request, "graph": graph})


def products(p1, supplied):
    p2 = service.construction_product(p1, ROOT)
    p3 = service.interpretation_product(p1, p2, supplied)
    return {"P1": p1, "P2": p2, "P3": p3, "P4": service.law_product(p1, p3),
            "P5": service.financial_product(p1, p2, p3)}


def consume(values):
    return service.consume(values, ROOT, include_artifacts=True, mode="frozen")


def keep_products(folder, prefix, values):
    original = SOURCE / "P1.json.gz"
    reference = {"original_P1": str(original.relative_to(ROOT)), "file_sha256": file_hash(original),
                 "request": values["P1"]["payload"]["request"], "expected_sha256": values["P1"]["sha256"]}
    reconstructed = p1_from(reference["request"], read(original)["payload"]["graph"])
    require(reconstructed == values["P1"], "Retained P1 reconstruction differs")
    save(folder, prefix + "-P1-reference.json.gz", reference)
    save(folder, prefix + "-P2-P5.json.gz", {k: v for k, v in values.items() if k != "P1"})


def load_products(folder, prefix):
    ref = read(folder / (prefix + "-P1-reference.json.gz"))
    original = ROOT / ref["original_P1"]
    require(file_hash(original) == ref["file_sha256"], "Retained P1 bytes changed")
    p1 = p1_from(ref["request"], read(original)["payload"]["graph"])
    require(p1["sha256"] == ref["expected_sha256"], "Retained P1 identity differs")
    return {"P1": p1, **read(folder / (prefix + "-P2-P5.json.gz"))}


def focused(folder):
    baseline = read(REVIEW / "baseline-methods.json")
    patch = ""
    for name, ref in baseline.items():
        patch += "".join(difflib.unified_diff((ROOT / ref["path"]).read_text().splitlines(True),
            (ROOT / name).read_text().splitlines(True), fromfile="before/" + name, tofile="after/" + name))
    save(folder, "reviewed-diff.json", {"patch": patch, "baseline": baseline})
    with (folder / "focused.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
        import pytest
        code = int(pytest.main(["-q", "-p", "no:cacheprovider", "--junitxml=" + str(folder / "focused-tests.xml"),
                               "tests/prospectus_successor/test_statement_cells.py"]))
    require(code == 0, "Focused statement-cell tests failed")
    return {"pytest_exit": code}


def matched(folder):
    original = read(SOURCE / "P1.json.gz")
    before = products(original, read(SOURCE / "corrected-P3.json.gz")["payload"]["interpretation_input"])
    keep_products(folder, "baseline", before)
    baseline = consume(before)
    save(folder, "baseline-answer.json.gz", baseline)
    require(baseline == read(SOURCE / "corrected-answer.json.gz"), "Complete005 corrected baseline changed")
    for phase in ("P2", "P3", "P4", "P5"):
        path = SOURCE / ("P2.json.gz" if phase == "P2" else "corrected-" + phase + ".json.gz")
        require(before[phase] == read(path), "Rebuilt original phase changed: " + phase)
    request = deepcopy(original["payload"]["request"])
    graph = original["payload"]["graph"]
    reading = read(SOURCE / "cell-reading.json")
    request["source_statement_cells"] = {"version": "source-statement-cells.v1",
        "profile": "bes-fy2010-statement-cells.v1", "document": "bes-release-fy10",
        "graph_sha256": digest(graph), "reading": reading,
        "review": {"kind": "DEVELOPMENT", "reviewer": "retained FY2010 original image review",
                   "reason": "Complete200-cell reading from source-bes-dep-08 attempt005; supplied interpretation"}}
    after = products(p1_from(request, graph), before["P3"]["payload"]["interpretation_input"])
    keep_products(folder, "after", after)
    answer = consume(after)
    save(folder, "after-answer.json.gz", answer)
    allowed = {"source_statement_cells", "request_sha256", "consumed_products", "report_sha256"}
    require({k: v for k, v in answer.items() if k not in allowed} ==
            {k: v for k, v in baseline.items() if k not in allowed}, "Protected whole answer changed")
    require(set(answer) == set(baseline) | {"source_statement_cells"}, "Unexpected answer fields")
    cell_answer = answer["source_statement_cells"]
    require(all(cell_answer[k] == reading[k] for k in ("rows", "tables", "source_context")), "Incomplete FY reading exposed")
    require(cell_answer["consumed"] and not cell_answer["independent_financial_acceptance"], "Unsupported financial acceptance")
    for phase in ("P2", "P3", "P4", "P5"):
        expected = deepcopy(before[phase]["payload"])
        if phase == "P2": expected["source_statement_cells"] = after[phase]["payload"]["source_statement_cells"]
        if phase == "P3": expected["source_statement_cells_sha256"] = after[phase]["payload"]["source_statement_cells_sha256"]
        require(expected == after[phase]["payload"], "Unexpected payload change: " + phase)
    ids = {d["id"] for d in request["bundle"]["dependencies"]}
    deps = {d["id"]: d for d in answer["dependencies"]}
    require(len(ids) == 14 and all(deps[k]["status"] == "UNRESOLVED" for k in ids), "Original dependency status changed")
    require(answer["questions"]["Q3"]["status"] == "PARTIAL" and not answer["may_execute_transaction"]
            and not answer["independent_legal_acceptance"], "Unsupported legal promotion")
    return {"exact005_baseline": True, "protected_answer_equal": True, "cells_consumed": 200,
            "original_dependencies_unresolved": 14, "baseline_report": baseline["report_sha256"],
            "after_report": answer["report_sha256"], "installed_profile_evaluated": False}


def refused(thunk, expected):
    try:
        thunk()
    except ValueError as exc:
        require(expected in str(exc), "Unexpected rejection: " + str(exc))
        return {"rejected": True, "reason": str(exc)}
    raise ValueError("Altered input accepted")


def input_controls(folder):
    after = load_products(folder, "after")
    graph, request = after["P1"]["payload"]["graph"], after["P1"]["payload"]["request"]
    cases = {}
    paths = sorted((SOURCE / "cell-controls").glob("*.json.gz"))
    require(len(paths) == 14, "Expected14 retained adverse cell inputs")
    for path in paths:
        bad_request = deepcopy(request)
        bad_request["source_statement_cells"]["reading"] = read(path)
        bad = p1_from(bad_request, graph)
        result = refused(lambda: service.construction_product(bad, ROOT), "reading differs")
        result.update(input={"path": str(path.relative_to(ROOT)), "sha256": file_hash(path)},
                      P1_sha256=bad["sha256"])
        cases[path.name] = result
        save(folder, "input-controls/" + path.stem + "-result.json", result)
    for change in ("crossed-profile", "crossed-reading", "geometry", "edition"):
        bad_request, bad_graph = deepcopy(request), deepcopy(graph)
        changed = None
        if change == "crossed-profile": bad_request["source_statement_cells"]["profile"] = "bes-q111-statement-cells.v1"
        elif change == "crossed-reading":
            bad_request["source_statement_cells"]["reading"] = read(BASE / "attempts/source-bes-dep-11/attempt-003/cell-reading.json")
        else:
            changed = next(u for u in bad_graph["units"] if u["document"] == "bes-release-fy10" and u["page"] == 41)
            if change == "geometry": changed["words"][0]["bbox"][0] += 1
            else: changed["source_sha256"] = "0" * 64
        bad_request["source_statement_cells"]["graph_sha256"] = digest(bad_graph)
        bad = p1_from(bad_request, bad_graph)
        delta = {"source_statement_cells": bad_request["source_statement_cells"], "changed_unit": changed,
                 "expected_P1_sha256": bad["sha256"], "reconstruction": "after P1 request with supplied field and optional named unit replaced, then reseal"}
        save(folder, "input-controls/" + change + "-input.json.gz", delta)
        expected = "Unsupported" if change == "crossed-profile" else "reading differs" if change == "crossed-reading" else "original pages"
        cases[change] = refused(lambda: service.construction_product(bad, ROOT), expected)
        save(folder, "input-controls/" + change + "-result.json", cases[change])
    return {"actual_public_construction_rejections": len(cases), "cases": cases}


def reseal(values):
    p1 = values["P1"]
    values["P1"] = p1_from(p1["payload"]["request"], p1["payload"]["graph"])
    parents = {"P2": ("P1",), "P3": ("P1", "P2"), "P4": ("P1", "P3"), "P5": ("P2", "P3")}
    for phase, source in parents.items():
        values[phase] = service.seal(phase, p1["payload"]["request"]["bundle"],
            {k: values[k]["sha256"] for k in source}, values[phase]["payload"])
    return values


def phase_controls(folder):
    after = load_products(folder, "after")
    cases = {}
    for change in ("missing-p2", "changed-p2", "missing-p3", "changed-p3", "unsupplied"):
        bad = deepcopy(after)
        if change == "missing-p2": del bad["P2"]["payload"]["source_statement_cells"]
        elif change == "changed-p2": bad["P2"]["payload"]["source_statement_cells"]["reading"]["rows"][0]["cells"][0]["value"] += 1
        elif change == "missing-p3": del bad["P3"]["payload"]["source_statement_cells_sha256"]
        elif change == "changed-p3": bad["P3"]["payload"]["source_statement_cells_sha256"] = "0" * 64
        else: del bad["P1"]["payload"]["request"]["source_statement_cells"]
        reseal(bad)
        save(folder, "phase-controls/" + change + "-input.json", {"mutation": change,
            "reconstruction": "Named mutation applied to after products by the bound phase_controls function; reseal all dependent products",
            "product_hashes": {k: v["sha256"] for k, v in bad.items()}})
        cases[change] = refused(lambda: consume(bad), "Consumed statement cells")
        save(folder, "phase-controls/" + change + "-result.json", cases[change])
    return {"actual_public_consumer_rejections": len(cases), "cases": cases}


def prior_profiles(folder):
    nine = BASE / "attempts/source-bes-dep-01/attempt-005"
    values = read(nine / "after-products.json.gz")
    actual = consume(values)
    reference = read(nine / "answer-reconstruction.json")
    require(digest(actual) == reference["expected_complete_answer_sha256"], "Complete9M public answer changed")
    require(actual["source_statement_cells"] == read(nine / "answer-addition.json"), "9M statement changed")
    nine_hash = actual["report_sha256"]
    q1 = BASE / "attempts/source-bes-dep-11/attempt-004"
    ref = read(q1 / "after-P1-reference.json.gz")
    original = ROOT / ref["original_p1"]
    require(file_hash(original) == ref["original_p1_file_sha256"], "Q1 original bytes changed")
    p1 = p1_from(ref["request"], read(original)["payload"]["graph"])
    require(p1["sha256"] == ref["expected_P1_sha256"], "Q1 original identity changed")
    values = {"P1": p1, **read(q1 / "after-P2-P5.json.gz")}
    # The retained Q1 answer deliberately omits bulky graph artifacts.
    actual = service.consume(values, ROOT, mode="frozen")
    require(actual == read(q1 / "after-answer.json.gz"), "CompleteQ1 public answer changed")
    result = {"nine_month_complete_answer_equal": True, "nine_month_report": nine_hash,
              "q1_complete_answer_equal": True, "q1_report": actual["report_sha256"],
              "new_native_calls": 0, "original_replay_sources": [str(nine.relative_to(ROOT)), str(q1.relative_to(ROOT))]}
    save(folder, "prior-profile-comparison.json", result)
    return result


def run(attempt, stage):
    a = Authority(ROOT)
    folder = a.path(attempt)
    program, tasks, _ = a.spec()
    task = tasks["source-bes-dep-08"]
    admission = read(folder / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == attempt
            and admission["program_sha256"] == authority_digest(program)
            and admission["binding"] == a.binding(task), "Current unchanged admission required")
    require(not (folder / "outputs.json").exists(), "Sealed attempt refused")
    prior = read(REVIEW / "retained-history.json")
    require(a.retained_evidence_valid(prior["event"]), "Source result changed")
    starts = list((folder / "stages").glob("*/started.json"))
    results = [read(p) for p in (folder / "stages").glob("*/result.json")]
    require(len(starts) == len(results) == STAGES.index(stage) and len(results) + len(prior["stages"]) < 11,
            "Duplicate, skipped or interrupted stage refused")
    require(all(r["status"] == "PASS" for r in results), "Predecessor failed")
    spent = sum(r["wall_seconds"] for r in results)
    require(spent < 480 and prior["wall_seconds"] + spent < 960, "Execution budget exhausted")
    frozen = methods()
    if stage == "focused":
        save(folder, "methods.json", frozen)
        save(folder, "method-snapshots.json.gz", {p: (ROOT / p).read_text() for p in frozen if p.endswith(".py")})
    else: require(read(folder / "methods.json") == frozen, "Methods changed after focused validation")
    save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
        "command": ["timeout", "120", ".venv/bin/python", "scripts/prospectus_fy2010_product.py", "--attempt", attempt, "--stage", stage],
        "git_commit": admission["git_commit"], "interpreter": sys.executable, "module": service.__file__,
        "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic comparison",
        "methods": frozen, "inputs": admission["binding"], "prior_stage_seconds": prior["wall_seconds"] + spent,
        "plan": task["dossier"], "result": str((folder / "result.json").relative_to(ROOT))})
    tick, error, details = time.monotonic(), None, None
    try:
        require(Path(service.__file__).resolve().is_relative_to(ROOT / "src"), "Wrong product import")
        if stage == "seal":
            require((folder / "RESULT.md").is_file(), "Actual result review required")
            details = {"production_cell_integration": True, "installed_profile_evaluated": False,
                       "independent_acceptance": False, "whole_program_complete": False}
        else: details = {"focused": focused, "matched": matched, "input-controls": input_controls,
                        "phase-controls": phase_controls, "prior-profiles": prior_profiles}[stage](folder)
        require(methods() == frozen and admission["binding"] == a.binding(task), "Methods or admitted inputs changed")
        require(spent + time.monotonic() - tick < 480 and prior["wall_seconds"] + spent + time.monotonic() - tick < 960,
                "Cumulative execution cap exceeded")
        require(size(folder) < 35 * 1024**2 and size(folder) + prior["bytes"] < 120 * 1024**2, "Cumulative evidence cap exceeded")
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        save(folder, "stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, final=True)
    result = {"status": "FAIL" if error else "PASS", "stage": stage, "error": error,
              "wall_seconds": time.monotonic() - tick, "details": details}
    save(folder, "stages/" + stage + "/result.json", result, final=True)
    if error or stage == "seal":
        save(folder, "result.json", {**result, "task": task["id"], "whole_program_complete": False,
            "installed_profile_evaluated": False, "independent_acceptance": False}, final=True)
        save(folder, "outputs.json", {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*")) if p.is_file()}, final=True)
    print(json.dumps({k: result[k] for k in ("status", "stage", "error", "wall_seconds")}))
    return int(error is not None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--stage", choices=STAGES, required=True)
    args = parser.parse_args()
    def blocked(event, _):
        if event in ("subprocess.Popen", "os.system", "os.posix_spawn", "os.fork", "socket.connect"):
            raise RuntimeError("FY product validation forbids native/network processes: " + event)
    sys.addaudithook(blocked)
    def expired(*_): raise TimeoutError("FY product stage exceeded115 seconds")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(115)
    try: return run(args.attempt, args.stage)
    finally: signal.alarm(0)


if __name__ == "__main__": raise SystemExit(main())
