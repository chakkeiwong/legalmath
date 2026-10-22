"""Bounded source09 continuation: report integrity and full original consumers."""
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
sys.path[:0] = [str(ROOT / "src"), str(ROOT), str(ROOT / "tests/prospectus_successor")]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
from legalmath.prospectus.execution_authority import Authority, digest as authority_digest, file_hash
from legalmath.prospectus.successor import report_scope, service
from legalmath.prospectus.successor.contracts import digest

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
SOURCE = BASE / "attempts/source-bes-dep-09/attempt-002"
REVIEW = BASE / "reviews/report-integrity-144"
SERVICE = "src/legalmath/prospectus/successor/service.py"
TEST = "tests/prospectus_successor/test_report_integrity.py"
STAGES = ("reproduce", "baseline", "focused", "matched", "audit-controls",
          "committee-controls", "integrity-controls", "regressions", "seal")


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def size(folder):
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def save(folder, name, value, *, final=False):
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
    data = gzip.compress(raw, mtime=0) if name.endswith(".gz") else raw
    require(size(folder) + len(data) < (96 if final else 94) * 1024**2, "New evidence cap exceeded")
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def methods():
    paths = sorted((ROOT / "src/legalmath/prospectus").rglob("*.py"))
    paths += sorted((ROOT / "tests/prospectus_successor").glob("test_*.py"))
    paths += [Path(__file__), ROOT / "scripts/prospectus_fy2010_product.py"]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in paths}


def p1_from(request, graph):
    return service.seal("P1", request["bundle"], {"request": digest(request)}, {"request": request, "graph": graph})


def products(p1, p2, scope):
    p3 = service.interpretation_product(p1, p2, {"source_report_scope": scope})
    return {"P1": p1, "P2": p2, "P3": p3, "P4": service.law_product(p1, p3),
            "P5": service.financial_product(p1, p2, p3)}


def consume(values):
    return service.consume(values, ROOT, include_artifacts=True, mode="frozen")


def keep_products(folder, label, values):
    original = SOURCE / "original-P1.json.gz"
    reference = {"original_P1": str(original.relative_to(ROOT)), "file_sha256": file_hash(original),
                 "request": values["P1"]["payload"]["request"], "expected_sha256": values["P1"]["sha256"]}
    require(p1_from(reference["request"], read(original)["payload"]["graph"]) == values["P1"], "P1 reference differs")
    save(folder, label + "-P1-reference.json.gz", reference)
    save(folder, label + "-P2-P5.json.gz", {k: v for k, v in values.items() if k != "P1"})


def load_products(folder, label):
    ref = read(folder / (label + "-P1-reference.json.gz"))
    original = ROOT / ref["original_P1"]
    require(file_hash(original) == ref["file_sha256"], "Original P1 bytes changed")
    p1 = p1_from(ref["request"], read(original)["payload"]["graph"])
    require(p1["sha256"] == ref["expected_sha256"], "Original P1 identity differs")
    return {"P1": p1, **read(folder / (label + "-P2-P5.json.gz"))}


def protected(answer):
    return {k: v for k, v in answer.items() if k not in {"source_reports", "consumed_products", "report_sha256"}}


def reproduce(folder):
    from test_report_scope import fixture, products as synthetic_products
    from test_report_integrity import CONSUMER_CASES, INTERPRETATION_CASES, changed
    sandbox = folder / "synthetic"
    sandbox.mkdir()
    _, p1, p2, scope = fixture(sandbox)
    good = synthetic_products(p1, p2, scope)
    save(folder, "synthetic-honest-products.json.gz", good)
    results = {}
    for case in CONSUMER_CASES:
        bad = changed(good, case)
        answer = service.consume(bad, sandbox, mode="frozen")
        save(folder, "before/" + case + "-products.json.gz", bad)
        save(folder, "before/" + case + "-answer.json.gz", answer)
        results[case] = {"incorrectly_accepted": True, "report_sha256": answer["report_sha256"]}
    for case in INTERPRETATION_CASES:
        bad = changed(good, case)
        p3 = service.interpretation_product(bad["P1"], bad["P2"], bad["P3"]["payload"]["interpretation_input"])
        save(folder, "before/interpretation-" + case + ".json.gz", p3)
        results["interpretation-" + case] = {"incorrectly_accepted": True, "P3_sha256": p3["sha256"]}
    save(folder, "reproduced-counterexamples.json", results)
    return {"actual_accepted_counterexamples": len(results), "classification": "local missing source revalidation"}


def baseline(folder):
    original = read(SOURCE / "original-P1.json.gz")
    request = deepcopy(original["payload"]["request"])
    request["source_report_readings"] = read(SOURCE / "original-reading-admission.json")
    p1 = p1_from(request, original["payload"]["graph"])
    p2 = service.construction_product(p1, ROOT)
    selected = p2["payload"]["source_report_readings"]
    require(selected == read(SOURCE / "original-selected.json.gz"), "Original readings changed")
    scope = read(SOURCE / "original-scope.json")
    diagnostic = read(SOURCE / "diagnostic-P2.json.gz")["payload"]["source_report_readings"]
    diagnostic_scope = read(SOURCE / "diagnostic-scope.json")
    for a, b, x, y in zip(selected["reports"], diagnostic["reports"], scope["reports"], diagnostic_scope["reports"], strict=True):
        require(a["id"] == b["id"] == x["id"] == y["id"] and a["text"] == b["text"] and x["facts"] == y["facts"],
                "Original and diagnostic text/facts differ; negative transfer invalid")
    unknown = deepcopy(scope)
    for row in unknown["reports"]:
        row["facts"] = {k: {"status": "UNKNOWN", "reason": "Not established in matched unknown-fact baseline"}
                        for k in sorted(report_scope.FACTS)}
    answers = {}
    for label, supplied in (("unknown", unknown), ("candidate", scope)):
        values = products(p1, p2, supplied)
        answer = consume(values)
        keep_products(folder, label, values)
        save(folder, label + "-answer.json.gz", answer)
        answers[label] = answer
    require(answers["candidate"]["source_reports"] == read(SOURCE / "original-reports.json.gz"), "Original explanation changed")
    require(protected(answers["unknown"]) == protected(answers["candidate"]), "Protected answer changed")
    require(len(original["payload"]["graph"]["units"]) == 35291, "Wrong complete source graph")
    ids = {d["id"] for d in request["bundle"]["dependencies"]}
    deps = {d["id"]: d for d in answers["candidate"]["dependencies"]}
    require(len(ids) == 14 and all(deps[k]["status"] == "UNRESOLVED" for k in ids), "Original dependencies changed")
    require(answers["candidate"]["questions"]["Q3"]["status"] == "PARTIAL" and
            not answers["candidate"]["independent_legal_acceptance"] and not answers["candidate"]["may_execute_transaction"],
            "Unsupported legal promotion")
    for phase in ("P4", "P5"):
        require(read(folder / "unknown-P2-P5.json.gz")[phase]["payload"] ==
                read(folder / "candidate-P2-P5.json.gz")[phase]["payload"], "Law/finance payload changed")
    return {"source_units": 35291, "source_pages": 256, "original_dependencies_unresolved": 14,
            "reports_exact": True, "protected_answer_equal": True,
            "answers": {k: v["report_sha256"] for k, v in answers.items()}}


def focused(folder):
    baseline_method = read(REVIEW / "baseline-methods.json")[SERVICE]
    patch = "".join(difflib.unified_diff((ROOT / baseline_method["path"]).read_text().splitlines(True),
        (ROOT / SERVICE).read_text().splitlines(True), fromfile="before/" + SERVICE, tofile="after/" + SERVICE))
    require(bool(patch), "No reviewed service repair")
    save(folder, "service-repair.json", {"patch": patch, "baseline": baseline_method})
    tests = ["test_report_integrity.py", "test_report_scope.py", "test_source_discrepancies.py",
             "test_english_report_context.py", "test_english_2010_reports.py", "test_interim_review.py",
             "test_unaudited_release.py", "test_q1_release.py", "test_statement_cells.py"]
    with (folder / "focused.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
        import pytest
        code = int(pytest.main(["-q", "-p", "no:cacheprovider", "--junitxml=" + str(folder / "focused.xml"),
                               *["tests/prospectus_successor/" + t for t in tests]]))
    require(code == 0, "Focused report integrity regression failed")
    return {"pytest_exit": code, "test_files": tests}


def matched(folder):
    rows = {}
    for label in ("unknown", "candidate"):
        old = load_products(folder, label)
        p1 = old["P1"]
        fresh = products(p1, service.construction_product(p1, ROOT), old["P3"]["payload"]["interpretation_input"]["source_report_scope"])
        require(fresh == old, "Honest full products changed: " + label)
        actual = consume(fresh)
        require(actual == read(folder / (label + "-answer.json.gz")), "Honest whole answer changed: " + label)
        rows[label] = {"all_products_equal": True, "whole_answer_equal": True, "report_sha256": actual["report_sha256"]}
    save(folder, "matched-comparison.json", rows)
    return rows


def adverse_controls(folder, labels):
    good = load_products(folder, "candidate")
    positive = read(folder / "candidate-answer.json.gz")
    selected = good["P2"]["payload"]["source_report_readings"]
    results = {}
    for label in labels:
        scope = read(SOURCE / ("control-" + label + "-scope.json"))
        scope["readings_sha256"] = digest(selected)
        for row, reading in zip(scope["reports"], selected["reports"], strict=True):
            require(row["id"] == reading["id"], "Negative report order changed")
            row["reading_sha256"] = reading["sha256"]
        save(folder, "controls/" + label + "-scope.json", scope)
        if label.startswith("false-"):
            try:
                service.interpretation_product(good["P1"], good["P2"], {"source_report_scope": scope})
            except ValueError as exc:
                require("contradicts supplied report category" in str(exc), "Wrong role-swap refusal: " + str(exc))
                results[label] = {"rejected": True, "reason": str(exc)}
            else:
                raise ValueError("False report role accepted")
        else:
            values = products(good["P1"], good["P2"], scope)
            answer = consume(values)
            index = 0 if label in ("paragraph8", "audit_translation") else 1
            field = {"borrowed_date": "report_date", "both_dates": "report_date",
                     "committee_purpose": "purpose", "audit_translation": "translation_status"}.get(label, "conclusion")
            report = answer["source_reports"][index]
            require(report["status"] == "INCOMPLETE_SOURCE_READING" and field in report["unresolved_english_report_fields"],
                    "Missing qualification did not withhold finding: " + label)
            require(answer["source_reports"][1-index] == positive["source_reports"][1-index] and
                    protected(answer) == protected(positive), "Unrelated answer changed: " + label)
            delta = {k: v for k, v in answer.items() if positive.get(k) != v}
            require({**positive, **delta} == answer, "Answer delta fails reconstruction")
            save(folder, "controls/" + label + "-answer-delta.json.gz", {"baseline": "candidate-answer.json.gz",
                "replace": delta, "complete_answer_sha256": digest(answer), "products": {k: v["sha256"] for k, v in values.items()}})
            results[label] = {"withheld": True, "other_report_and_surrounding_answer_equal": True,
                              "report_sha256": answer["report_sha256"]}
        save(folder, "controls/" + label + "-result.json", results[label])
    return results


def integrity_controls(folder):
    from test_report_integrity import changed
    good = load_products(folder, "candidate")
    results = {}
    for case in ("missing-p2", "changed-p2", "unsupplied-readings", "missing-p3", "changed-p3", "unsupplied-scope"):
        bad = changed(good, case)
        save(folder, "original-integrity/" + case + "-input.json", {"mutation": case,
            "reconstruction": "Bound test_report_integrity.changed(candidate products, mutation)",
            "products": {k: v["sha256"] for k, v in bad.items()}})
        try:
            consume(bad)
        except ValueError as exc:
            require("Report" in str(exc) or "report" in str(exc), "Unexpected integrity rejection: " + str(exc))
            results[case] = {"rejected": True, "reason": str(exc)}
        else:
            raise ValueError("Original-source counterexample accepted: " + case)
        save(folder, "original-integrity/" + case + "-result.json", results[case])
    return results


def regressions(folder):
    from scripts import prospectus_fy2010_product as fy
    prior = fy.prior_profiles(folder)
    source = BASE / "attempts/source-bes-dep-08/attempt-006"
    for label in ("baseline", "after"):
        values = fy.load_products(source, label)
        answer = consume(values)
        require(answer == read(source / (label + "-answer.json.gz")), "FY2010 whole answer changed: " + label)
        prior["FY2010-" + label] = answer["report_sha256"]
    y = BASE / "attempts/source-bes-dep-06/attempt-002"
    selected = read(y.parent / "attempt-001/selected-reading.json")
    admitted = report_scope.admit(selected, read(y / "original-corrected-scope.json"))
    require(admitted == read(y / "original-corrected-admitted.json.gz") and
            report_scope.explain(admitted)[0] == read(y / "original-corrected-answer.json.gz"), "2009 original report changed")
    prior["2009_direct_scope_and_explanation_equal"] = True
    save(folder, "regression-comparison.json", prior)
    return prior


def run(attempt, stage):
    a = Authority(ROOT)
    folder = a.path(attempt)
    program, tasks, _ = a.spec()
    task = tasks["source-bes-dep-09"]
    admission = read(folder / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == attempt and
            admission["program_sha256"] == authority_digest(program) and admission["binding"] == a.binding(task),
            "Unchanged current admission required")
    require(not (folder / "outputs.json").exists(), "Sealed attempt refused")
    prior = read(REVIEW / "retained-history.json")
    require(all(a.retained_evidence_valid(e) for e in prior["events"]), "Earlier results changed")
    starts = list((folder / "stages").glob("*/started.json"))
    results = [read(p) for p in (folder / "stages").glob("*/result.json")]
    require(len(starts) == len(results) == STAGES.index(stage), "Duplicate, skipped or interrupted stage refused")
    require(all(r["status"] == "PASS" for r in results), "Predecessor failed")
    spent = sum(r["wall_seconds"] for r in results)
    require(spent < 720, "Execution budget exhausted")
    frozen = methods()
    if stage == "reproduce":
        require(file_hash(ROOT / SERVICE) == read(REVIEW / "baseline-methods.json")[SERVICE]["sha256"], "Baseline service changed")
        save(folder, "before-methods.json", frozen)
    elif stage == "baseline":
        require(frozen == read(folder / "before-methods.json"), "Baseline methods changed")
    elif stage == "focused":
        before = read(folder / "before-methods.json")
        require({k: v for k, v in before.items() if k != SERVICE} == {k: v for k, v in frozen.items() if k != SERVICE},
                "Unreviewed method edit beyond service repair")
        save(folder, "final-methods.json", frozen)
        save(folder, "final-service-and-test.json.gz", {p: (ROOT / p).read_text() for p in (SERVICE, TEST)})
    else:
        require(frozen == read(folder / "final-methods.json"), "Methods changed after focused validation")
    save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
        "command": ["timeout", "120", ".venv/bin/python", "scripts/prospectus_report_integrity.py", "--attempt", attempt, "--stage", stage],
        "git_commit": admission["git_commit"], "interpreter": sys.executable, "module": service.__file__,
        "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic comparison",
        "methods": frozen, "inputs": admission["binding"], "earlier_attempt_history": prior,
        "new_attempt_seconds_before_stage": spent, "plan": task["dossier"], "result": str((folder / "result.json").relative_to(ROOT))})
    tick, error, details = time.monotonic(), None, None
    try:
        require(Path(service.__file__).resolve().is_relative_to(ROOT / "src"), "Wrong product import")
        if stage == "seal":
            require((folder / "RESULT.md").is_file(), "Actual substantive result review required")
            details = {"report_integrity_repaired": True, "original_2010_consumer_evaluated": True,
                       "installed_repair_evaluated": False, "independent_acceptance": False}
        else:
            actions = {"reproduce": reproduce, "baseline": baseline, "focused": focused, "matched": matched,
                "audit-controls": lambda p: adverse_controls(p, ("paragraph8", "audit_translation", "false-COMMITTEE_REPORT")),
                "committee-controls": lambda p: adverse_controls(p, ("knowledge", "recommendation", "borrowed_date", "both_dates", "committee_purpose", "false-STATUTORY_FINANCIAL_AUDIT")),
                "integrity-controls": integrity_controls, "regressions": regressions}
            details = actions[stage](folder)
        require(frozen == methods() and admission["binding"] == a.binding(task), "Methods/inputs changed during stage")
        require(spent + time.monotonic() - tick < 720 and size(folder) < 96 * 1024**2, "Cumulative stage/evidence limit exceeded")
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        save(folder, "stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, final=True)
    result = {"status": "FAIL" if error else "PASS", "stage": stage, "error": error,
              "wall_seconds": time.monotonic() - tick, "details": details}
    save(folder, "stages/" + stage + "/result.json", result, final=True)
    if error or stage == "seal":
        save(folder, "result.json", {**result, "task": task["id"], "task_complete": False,
            "installed_repair_evaluated": False, "independent_acceptance": False}, final=True)
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
            raise RuntimeError("Report integrity validation forbids native/network processes: " + event)
    sys.addaudithook(blocked)
    def expired(*_):
        raise TimeoutError("Report integrity stage exceeded 115 seconds")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(115)
    try:
        return run(args.attempt, args.stage)
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
