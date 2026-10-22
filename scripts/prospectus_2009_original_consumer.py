"""Bounded original two-document2009 report consumption; no fresh extraction."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
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
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from legalmath.prospectus.execution_authority import Authority, digest as authority_digest, file_hash
from legalmath.prospectus.successor import report_scope, service
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_report_integrity import read, save, size, require, p1_from, products, consume, protected

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
PRIOR = BASE / "attempts/source-bes-dep-06/attempt-001"
SOURCE = PRIOR.parent / "attempt-002"
REVIEW = BASE / "reviews/original-2009-147"
STAGES = ("baseline", "candidate", "adverse-a", "adverse-b", "adverse-c", "roles", "integrity", "seal")


def keep(folder, label, values):
    original = PRIOR / "source-product.json.gz"
    ref = {"original_P1": str(original.relative_to(ROOT)), "file_sha256": file_hash(original),
           "request": values["P1"]["payload"]["request"], "expected_sha256": values["P1"]["sha256"]}
    require(p1_from(ref["request"], read(original)["payload"]["graph"]) == values["P1"], "Original P1 reference differs")
    save(folder, label + "-P1-reference.json.gz", ref)
    save(folder, label + "-P2-P5.json.gz", {k: v for k, v in values.items() if k != "P1"})


def load(folder, label):
    ref = read(folder / (label + "-P1-reference.json.gz"))
    path = ROOT / ref["original_P1"]
    require(file_hash(path) == ref["file_sha256"], "Original P1 bytes changed")
    p1 = p1_from(ref["request"], read(path)["payload"]["graph"])
    require(p1["sha256"] == ref["expected_sha256"], "Original P1 identity changed")
    return {"P1": p1, **read(folder / (label + "-P2-P5.json.gz"))}


def baseline(folder):
    original = read(PRIOR / "source-product.json.gz")
    request = deepcopy(original["payload"]["request"])
    graph = original["payload"]["graph"]
    require(len(graph["units"]) == 47750 and len(request["bundle"]["documents"]) == 2, "Wrong original bundle")
    request["source_report_readings"] = read(PRIOR / "reading-admission.json")
    p1 = p1_from(request, graph)
    p2 = service.construction_product(p1, ROOT)
    selected = p2["payload"]["source_report_readings"]
    require(selected == read(PRIOR / "selected-reading.json"), "Original selection differs")
    diagnostic = read(SOURCE / "diagnostic-P2.json.gz")["payload"]["source_report_readings"]
    actual = read(SOURCE / "original-corrected-scope.json")
    diagnostic_scope = read(SOURCE / "diagnostic-scope.json")
    require(selected["reports"][0]["text"] == diagnostic["reports"][0]["text"] and
            actual["reports"][0]["facts"] == diagnostic_scope["reports"][0]["facts"], "Negative fact transfer invalid")
    values = products(p1, p2, read(PRIOR / "scope-admission.json"))
    answer = consume(values)
    require(answer["source_reports"] == [read(SOURCE / "original-before-current.json.gz")], "Original incomplete explanation changed")
    require(answer["source_reports"][0]["status"] == "INCOMPLETE_SOURCE_READING", "Baseline must retain missing context")
    keep(folder, "baseline", values)
    save(folder, "baseline-answer.json.gz", answer)
    return {"documents": 2, "source_units": 47750, "baseline_report": answer["report_sha256"],
            "original_explanation_equal": True, "diagnostic_text_facts_equal": True}


def candidate(folder):
    before = load(folder, "baseline")
    scope = read(SOURCE / "original-corrected-scope.json")
    values = products(before["P1"], before["P2"], scope)
    answer = consume(values)
    require(values["P3"]["payload"]["source_report_scope"] == read(SOURCE / "original-corrected-admitted.json.gz") and
            answer["source_reports"] == [read(SOURCE / "original-corrected-answer.json.gz")], "Complete original scope/explanation changed")
    require(protected(answer) == protected(read(folder / "baseline-answer.json.gz")), "Surrounding complete answer changed")
    for phase in ("P4", "P5"):
        require(values[phase]["payload"] == before[phase]["payload"], "Law/financial payload changed")
    ids = {d["id"] for d in before["P1"]["payload"]["request"]["bundle"]["dependencies"]}
    deps = {d["id"]: d for d in answer["dependencies"]}
    require(len(ids) == 14 and all(deps[k]["status"] == "UNRESOLVED" for k in ids), "Original dependencies changed")
    require(answer["questions"]["Q3"]["status"] == "PARTIAL" and not answer["independent_legal_acceptance"] and
            not answer["may_execute_transaction"], "Unsupported legal promotion")
    keep(folder, "candidate", values)
    save(folder, "candidate-answer.json.gz", answer)
    return {"original_admission_and_explanation_equal": True, "protected_answer_equal": True,
            "law_finance_payload_equal": True, "original_unresolved_dependencies": 14, "report_sha256": answer["report_sha256"]}


def rebound_scope(values, label):
    scope = read(SOURCE / ("control-" + label + "-scope.json"))
    selected = values["P2"]["payload"]["source_report_readings"]
    require(len(scope["reports"]) == len(selected["reports"]) == 1 and
            scope["reports"][0]["id"] == selected["reports"][0]["id"], "Wrong negative report")
    scope["readings_sha256"] = digest(selected)
    scope["reports"][0]["reading_sha256"] = selected["reports"][0]["sha256"]
    return scope


def adverse(folder, labels):
    good = load(folder, "candidate")
    positive = read(folder / "candidate-answer.json.gz")
    results = {}
    for label in labels:
        scope = rebound_scope(good, label)
        save(folder, "controls/" + label + "-scope.json", scope)
        values = products(good["P1"], good["P2"], scope)
        answer = consume(values)
        field = "report_date" if label == "both_dates" else label.removeprefix("unknown_")
        report = answer["source_reports"][0]
        require(report["status"] == "INCOMPLETE_SOURCE_READING" and field in report["unresolved_english_report_fields"],
                "Original source failed to withhold: " + label)
        require(protected(answer) == protected(positive), "Protected answer changed: " + label)
        delta = {k: v for k, v in answer.items() if positive.get(k) != v}
        require({**positive, **delta} == answer, "Incomplete answer reconstruction")
        save(folder, "controls/" + label + "-answer-delta.json.gz", {"baseline": "candidate-answer.json.gz",
            "replace": delta, "complete_answer_sha256": digest(answer), "products": {k: v["sha256"] for k, v in values.items()}})
        results[label] = {"withheld": True, "protected_answer_equal": True, "report_sha256": answer["report_sha256"]}
        save(folder, "controls/" + label + "-result.json", results[label])
    return results


def roles(folder):
    good = load(folder, "candidate")
    results = {}
    for kind in ("COMMITTEE_REPORT", "LIMITED_FINANCIAL_REVIEW", "LIMITED_SUSTAINABILITY_ASSURANCE", "UNAUDITED_FINANCIAL_RELEASE"):
        scope = rebound_scope(good, kind)
        if kind == "UNAUDITED_FINANCIAL_RELEASE":
            scope["reports"][0]["facts"]["conclusion"] = {"status": "UNKNOWN", "reason": "No independent opinion for the internally consistent false-release control"}
        save(folder, "roles/" + kind + "-scope.json", scope)
        try:
            service.interpretation_product(good["P1"], good["P2"], {"source_report_scope": scope})
        except ValueError as exc:
            require("English report contradicts supplied report category" in str(exc), "Wrong source-category refusal: " + str(exc))
            results[kind] = {"rejected": True, "reason": str(exc)}
        else:
            raise ValueError("False original report category accepted")
        save(folder, "roles/" + kind + "-result.json", results[kind])
    return results


def integrity(folder):
    from test_report_integrity import changed
    good = load(folder, "candidate")
    results = {}
    for case in ("missing-p2", "changed-p2", "unsupplied-readings", "missing-p3", "changed-p3", "unsupplied-scope"):
        bad = changed(good, case)
        save(folder, "integrity/" + case + "-input.json", {"mutation": case,
            "reconstruction": "Bound test_report_integrity.changed(candidate products, mutation)",
            "products": {k: v["sha256"] for k, v in bad.items()}})
        try:
            consume(bad)
        except ValueError as exc:
            require("report" in str(exc).lower(), "Wrong integrity refusal")
            results[case] = {"rejected": True, "reason": str(exc)}
        else:
            raise ValueError("Original2009 integrity attack accepted")
        save(folder, "integrity/" + case + "-result.json", results[case])
    return results


def run(attempt, stage):
    a = Authority(ROOT)
    folder = a.path(attempt)
    program, tasks, _ = a.spec()
    task = tasks["source-bes-dep-06"]
    admission = read(folder / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == attempt and admission["program_sha256"] == authority_digest(program)
            and admission["binding"] == a.binding(task), "Current unchanged admission required")
    require(not (folder / "outputs.json").exists(), "Sealed attempt refused")
    history = read(REVIEW / "history.json")
    require(all(a.retained_evidence_valid(e) for e in history["events"]), "Retained evidence changed")
    starts = list((folder / "stages").glob("*/started.json"))
    results = [read(p) for p in (folder / "stages").glob("*/result.json")]
    require(len(starts) == len(results) == STAGES.index(stage) and all(r["status"] == "PASS" for r in results),
            "Duplicate/skipped/interrupted/failed stage")
    spent = sum(r["wall_seconds"] for r in results)
    require(spent < 720, "Execution budget exhausted")
    save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
        "command": ["timeout", "120", ".venv/bin/python", "scripts/prospectus_2009_original_consumer.py", "--attempt", attempt, "--stage", stage],
        "git_commit": admission["git_commit"], "interpreter": sys.executable, "module": service.__file__,
        "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic comparison",
        "inputs": admission["binding"], "history": history, "new_prior_stage_seconds": spent,
        "plan": task["dossier"], "result": str((folder / "result.json").relative_to(ROOT))})
    tick, error, details = time.monotonic(), None, None
    try:
        if stage == "seal":
            require((folder / "RESULT.md").is_file(), "Actual substantive result review required")
            details = {"original2009_report_consumed": True, "source_dependencies_complete": False,
                       "independent_acceptance": False, "new_native_calls": 0}
        else:
            actions = {"baseline": baseline, "candidate": candidate,
                "adverse-a": lambda p: adverse(p, ("assurance_level", "report_date", "conclusion")),
                "adverse-b": lambda p: adverse(p, ("unknown_purpose", "unknown_translation_status")),
                "adverse-c": lambda p: adverse(p, ("unknown_criteria", "both_dates")), "roles": roles, "integrity": integrity}
            details = actions[stage](folder)
        require(admission["binding"] == a.binding(task), "Admitted inputs/methods changed")
        require(spent + time.monotonic() - tick < 720 and size(folder) < 96 * 1024**2, "Execution/evidence cap exceeded")
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        save(folder, "stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, final=True)
    result = {"status": "FAIL" if error else "PASS", "stage": stage, "error": error,
              "wall_seconds": time.monotonic() - tick, "details": details}
    save(folder, "stages/" + stage + "/result.json", result, final=True)
    if error or stage == "seal":
        save(folder, "result.json", {**result, "task": task["id"], "task_complete": False, "independent_acceptance": False}, final=True)
        save(folder, "outputs.json", {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*")) if p.is_file()}, final=True)
    print(json.dumps({k: result[k] for k in ("status", "stage", "error", "wall_seconds")}))
    return int(error is not None)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--attempt", required=True)
    p.add_argument("--stage", choices=STAGES, required=True)
    args = p.parse_args()
    def block(event, _):
        if event in ("subprocess.Popen", "os.system", "os.fork", "os.posix_spawn", "socket.connect"):
            raise RuntimeError("Original2009 consumer forbids native/network: " + event)
    sys.addaudithook(block)
    def expired(*_):
        raise TimeoutError("Original2009 stage exceeded115 seconds")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(115)
    try:
        return run(args.attempt, args.stage)
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
