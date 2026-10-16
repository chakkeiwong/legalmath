#!/usr/bin/env python3
"""Record the reviewed offline legal gap decision; never dispatch a provider."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import legal_mission_control as control
from legalmath.interpretation.assurance.route_admission import admission, workload

BASE = ROOT / "docs/implementation/legal-mission-control"
MISSION = BASE / "mission.json"
TOOLS = BASE / "tools.json"
PLAN = ROOT / "docs/plans/legal-mission-gap-closure.md"
REVIEW = BASE / "gap-closure-review.md"
WARRANT = BASE / "gap-closure-warrant-review.md"
OUT = ROOT / "artifacts/legal-mission-control/2026-10-11/gap-closure"
RESULT_DOC = BASE / "results/gap-closure.md"
ROUTE_RESULT = ROOT / "artifacts/legal-mission-control/2026-10-11/route-repair/final-result.json"
ROUTE_DOC = BASE / "results/route-repair.md"
LEDGER = ROOT / "artifacts/legal-mission-control/2026-10-10/live-pilot-400/allowance.json"
GRANT = ROOT / "artifacts/legal-mission-control/2026-10-10/live-pilot-400/authorization.json"
INVENTORY = ROOT / "artifacts/legal-integration-assessment/2026-10-08/input-inventory.json"
QUESTIONS = ROOT / "artifacts/legal-tool-comparison/2026-10-06/T0/attempt-1/questions.json"
UNRELATED_ALLOWANCE = ROOT / "artifacts/assurance-new-grant/2026-09-29/live-allowance.json"
EXCERPTS = {
    "p10": ROOT / "artifacts/legal-mission-control/2026-10-09/continuation/p10-standard/source-excerpts.json",
    "evidence": ROOT / "artifacts/legal-mission-control/2026-10-10/evidence-route-design/source-excerpts.json",
    "p14": ROOT / "artifacts/legal-mission-control/2026-10-09/continuation/p14-attachment/source-excerpts.json",
    "gatecoin": ROOT / "artifacts/legal-mission-control/2026-10-09/continuation/gatecoin-transfer/source-excerpts.json",
}
GATECOIN_2023 = ROOT / "artifacts/legal-interpretation-program/successor-s2/acquisition/gatecoin-2023-official/text.txt"
QUALIFIED_CONTEXT = ROOT / "artifacts/legal-mission-control/2026-10-10/live-pilot-400/qualified-source-context.json"
PYTHON = ".venv/bin/python"
DEADLINE = "2026-10-12T04:28:01+00:00"
SELECTED = ("bm25", "legalruleml", "pyarg", "carneades", "clingo", "logical-english")
QUESTION_ORDER = ("p10", "p14", "evidence", "gatecoin")


def read(path: Path):
    return json.loads(path.read_bytes())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path: Path) -> dict[str, str]:
    path = path.resolve()
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path)}


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.exists(), f"Refuse to overwrite retained artifact: {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    temporary.replace(path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.exists(), f"Refuse to overwrite retained artifact: {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value)
    temporary.replace(path)


def preflight():
    mission, tools = read(MISSION), read(TOOLS)
    state = control.validate(mission, tools, ROOT)
    admitted = control.admit(mission, tools, "product-contribution", ROOT)
    require(state["detours_since_advance"] == 8 and mission["current_task"] == "product-contribution",
            "Current mission or cumulative detour bound changed")
    task = next(t for t in mission["tasks"] if t["id"] == "product-contribution")
    require(task["resource_bounds"] == {"live_calls": 0, "minutes": 120, "repair_attempts": 0},
            "Current admission is not the reviewed offline task")
    require(PLAN.is_file() and REVIEW.is_file() and WARRANT.is_file(), "Missing reviewed plan or warrant")
    require(f"`{digest(PLAN)}`" in REVIEW.read_text(), "Review does not bind current plan")
    route, ledger, grant = read(ROUTE_RESULT), read(LEDGER), read(GRANT)
    require(route["status"] == "LOCAL_REPAIR_VERIFIED_LIVE_REFUSED", "Unexpected route result")
    require(route["resources"]["new_live_calls"] == 0
            and route["resources"]["total_live_calls_used"] == 13,
            "Retained route accounting changed")
    require(grant["maximum"] == ledger["maximum"] == 400 and len(ledger["calls"]) == 13,
            "Original live ledger changed")
    require(grant["deadline_utc"] == route["resources"]["live_deadline_utc"] == DEADLINE,
            "Original deadline changed")
    require(datetime.now(timezone.utc) < datetime.fromisoformat(DEADLINE), "Original live window expired")
    require(digest(UNRELATED_ALLOWANCE) ==
            "d2d8d59338f65453fadf9b6b18c90e4d9158841e48975a06f046b254b48c9eaa",
            "Unrelated allowance changed")
    context = read(QUALIFIED_CONTEXT)
    require(len(context["unit_hashes"]) == 55, "P10/evidence pilot source count changed")
    for path in EXCERPTS.values():
        control.verify_refs(ROOT, read(path))
    return mission, tools, state, admitted, route, ledger, grant


def source_ledger(mission, route):
    inventory, questions = read(INVENTORY), read(QUESTIONS)
    by_question = {r["id"]: r for r in questions}
    require(set(by_question) == set(QUESTION_ORDER), "Original question set changed")
    explicit = {}
    for task in mission["tasks"]:
        if task["kind"] != "source_analysis":
            continue
        for oid in task["original_obligation_ids"]:
            for qid in task["questions"]:
                explicit.setdefault(oid, {}).setdefault(qid, []).append(task["id"])
    obligations = []
    for row in inventory["original_obligations"]:
        mapped = explicit.get(row["obligation_id"], {})
        obligations.append({
            "ordinal": row["ordinal"], "obligation_id": row["obligation_id"],
            "original_hash": row["original_hash"], "status": row["status"],
            "first_unresolved_step": row["first_unresolved_step"],
            "missing_premises": row["missing_premises"], "closure_requires": row["closure_requires"],
            "question_ids": [q for q in QUESTION_ORDER if q in mapped],
            "mapping_basis": {q: mapped[q] for q in mapped},
            "mapping_status": "EXPLICIT_SOURCE_TASK" if mapped else "NOT_REVIEWED",
            "obligation_specific_source_warrant": "NOT_REVIEWED_HERE",
            "original_inventory": ref(INVENTORY), "closure_evidence": None,
        })
    readings = [{
        "reading_id": row["reading_id"],
        "retained_statement_sha256": hashlib.sha256(row["retained_statement"].encode()).hexdigest(),
        "citation_unit_ids": [c["unit_id"] for c in row.get("citations", [])],
        "status": row["status"], "formalized_in_original_register": bool(row.get("formalization")),
        "source_equivalence": row.get("source_equivalence"),
        "question_mapping_status": "P10_FOCUSED_REGISTER_NOT_INDEPENDENTLY_REMAPPED",
        "complete_current_dossier_candidate": False,
    } for row in inventory["original_readings"]]
    dossier = {
        "p10": [BASE / "results/p10-standard.md", BASE / "results/p10-effective-mitigation.md"],
        "evidence": [BASE / "results/p10-standard.md", BASE / "results/p10-effective-mitigation.md"],
        "p14": [BASE / "results/p14-attachment.md"],
        "gatecoin": [BASE / "results/gatecoin-transfer.md"],
    }
    qrows = []
    for qid in QUESTION_ORDER:
        sources = [EXCERPTS[qid]]
        if qid == "gatecoin":
            sources.append(GATECOIN_2023)
        if qid in {"p10", "evidence"}:
            sources.append(QUALIFIED_CONTEXT)
        qrows.append({
            "question_id": qid, "exact_question": by_question[qid]["question"],
            "target": next(q["target"] for q in mission["questions"] if q["id"] == qid),
            "source_evidence": [ref(p) for p in sources],
            "retained_analysis": [ref(p) for p in dossier[qid]] + [ref(WARRANT)],
            "population_status": "PARTIAL_55_UNIT_P10_EVIDENCE_PILOT" if qid in {"p10", "evidence"}
                                 else "SEPARATE_COMPLETE_POPULATION_NOT_ENUMERATED",
            "answer_status": "CONDITIONAL_REFERENCE_ONLY_NO_COMPLETE_PRODUCT_ANSWER",
        })
    require(len(obligations) == len({r["obligation_id"] for r in obligations}) == 46,
            "Original obligation identity mismatch")
    require(len(readings) == len({r["reading_id"] for r in readings}) == 35,
            "Original reading identity mismatch")
    return {
        "profile": "legal-mission-gap-source-coverage.v2",
        "questions": qrows, "obligations": obligations, "readings": readings,
        "pilot_only": {"source_units": 55, "partial_reader_source_coverage": 53,
                       "partial_claims": 78, "historical_candidates": 12,
                       "independent_reader_inventories_complete": False,
                       "route_result": ref(ROUTE_RESULT)},
        "original_question_count": 4, "original_obligation_count": 46,
        "original_reading_count": 35, "four_question_source_population_complete": False,
        "administrative_coverage_not_legal_closure": True,
    }


def budget_record(route, ledger, grant):
    original = route["resources"]["live_admission"]
    baseline_remaining = original["remaining"]
    candidate_remaining = grant["allocations"]["candidate"]
    charged = len(ledger["calls"])
    reserved = sum(grant["allocations"]["baseline"].values()) + sum(candidate_remaining.values())
    require(reserved == 374 and charged == 13 and baseline_remaining["core"] == 23,
            "Original paired reservation changed")
    common = dict(pieces=5, reader_claims=[78, 78], selected_claims=67, all_claims=78,
                  candidates=12, formalized_candidates=6, source_batch=40,
                  context_passes=1, interaction_batches=0, search_calls=6,
                  abstraction_calls=3, semantic_rounds=0, other_core_calls=0,
                  output_repairs=0, scoped_rounds=1, question_calls=3,
                  dossier_groups=64)
    scenarios = []
    for label, core_batch, scoped_batch in (
        ("retained-32-12", 32, 12), ("hypothesis-64-32", 64, 32),
        ("hypothesis-64-48", 64, 48),
    ):
        baseline = workload(**common, core_batch=core_batch, scoped_batch=scoped_batch,
                            tool_enabled=False)
        candidate = workload(**common, core_batch=core_batch, scoped_batch=scoped_batch,
                             tool_enabled=True)
        require(baseline["stages"] == candidate["stages"]
                and baseline["optional_tool_actions"] == 0, "Unequal model workload or baseline tools")
        if label == "retained-32-12":
            require(candidate["stages"] == original["required"]["stages"]
                    and candidate["optional_tool_actions"] == original["required"]["optional_tool_actions"],
                    "Retained workload not reproduced")
        paired_fresh = baseline["total_calls"] + candidate["total_calls"]
        scenarios.append({
            "id": label, "core_batch": core_batch, "scoped_batch": scoped_batch,
            "population": "P10_EVIDENCE_PARTIAL_HYBRID_NOT_UPPER_BOUND",
            "baseline": baseline, "candidate": candidate,
            "existing_baseline_gate": admission(baseline, baseline_remaining, deadline_utc=DEADLINE),
            "existing_candidate_gate": admission(candidate, candidate_remaining,
                                                  deadline_utc=DEADLINE, tool_remaining=200),
            "fresh_paired_calls": paired_fresh, "charged_plus_fresh": charged + paired_fresh,
            "paired_reservation_remaining": reserved - charged,
            "paired_arithmetic_fits": paired_fresh <= reserved - charged,
            "global_unspent_calls": grant["maximum"] - charged,
            "candidate_only_tool_actions": candidate["optional_tool_actions"],
            "source_population_qualified": False, "actual_response_qualified": False,
            "repairs_and_deadline_headroom_qualified": False, "live_method_qualified": False,
        })
    sensitivity = []
    for candidates, formalized, repairs in ((12, 6, 1), (20, 6, 0), (20, 20, 0)):
        w = workload(**(common | {"candidates": candidates, "formalized_candidates": formalized,
                                 "output_repairs": repairs}),
                     core_batch=64, scoped_batch=48, tool_enabled=True)
        sensitivity.append({"candidates": candidates, "formalized": formalized,
                            "output_repairs": repairs, "calls_per_arm": w["total_calls"],
                            "charged_plus_new_pair": charged + 2 * w["total_calls"],
                            "candidate_only_tool_actions": w["optional_tool_actions"],
                            "scenario_not_population_prediction": True})
    return {
        "profile": "legal-mission-gap-budget.v2", "grant": ref(GRANT), "ledger": ref(LEDGER),
        "paired_original_reservation": reserved, "paired_remaining": reserved - charged,
        "global_unspent": grant["maximum"] - charged,
        "unallocated_calls_not_transferred": grant["unallocated_calls"],
        "assessment_calls_not_transferred": grant["optional_assessment_calls"],
        "scenarios": scenarios, "sensitivity": sensitivity,
        "decision": "LIVE_NOT_ADMITTED",
        "reason": "Existing baseline core allocation refuses every scenario; larger batches have only input-size evidence and partial populations. No reviewed successor allocation or actual response qualification.",
        "live_dispatch": False,
    }


def gap_register():
    return [
        {"id": "source-populations", "status": "OPEN", "needed": "Separate complete P10/evidence, P14 and Gatecoin populations; both independent pilot readers and all contrary readings"},
        {"id": "route-admission", "status": "CURRENT_ALLOCATION_REFUSED", "needed": "Reviewed equal-arm successor allocation with actual complete populations, candidate-only actions, finite repairs and deadline headroom"},
        {"id": "responses-and-interactions", "status": "UNOBSERVED", "needed": "Actual expanded responses, source reviews, nonlocal interactions, omission review and final synthesis"},
        {"id": "complete-answers", "status": "UNOBSERVED", "needed": "Matched complete original-target answers with source and contrary review"},
        {"id": "tool-answer-effect", "status": "UNOBSERVED", "needed": "Per-tool and combined downstream benefit/no-effect/harm, including false-warrant controls"},
        {"id": "p10-standard", "status": "CONDITIONAL", "needed": "Applicable allocation/conduct/outcome standard and arrangement facts"},
        {"id": "p14-attachment", "status": "CONDITIONAL", "needed": "Authority on main-text/footnote attachment; actual request and satisfaction evidence for an arrangement"},
        {"id": "gatecoin-transfer", "status": "CONDITIONAL", "needed": "Target terms, parties, property/right, current later treatment and scenario-seven resolution"},
    ]


def tool_register(tools):
    rows = []
    for tool in tools:
        if tool["id"] not in SELECTED:
            continue
        rows.append({
            "id": tool["id"], "disposition": tool["disposition"],
            "current_use": tool["current_use"], "remaining_gap": tool["remaining_gap"],
            "fully_integrated": tool["fully_integrated"], "evaluation": tool.get("evaluation"),
            "stages": {k: v["level"] for k, v in tool["stages"].items()},
            "retained_evidence": tool["evidence"],
            "negative_control": ref(BASE / "results/product-contribution.md"),
            "answer_effect": "UNTESTED_ON_COMPLETE_ORIGINAL_TARGET",
        })
    require(len(rows) == 6 and all(not r["fully_integrated"] for r in rows),
            "Selected-tool disposition changed")
    return {"selected": rows, "selected_fully_evaluated": 0,
            "scripted_delivery_is_not_answer_contribution": True}


def result_markdown(result, budget):
    scenarios = budget["scenarios"]
    lines = [
        "# Legal interpretation gap-closure work package", "",
        "11 October 2026. **The offline package is complete; live work is not admitted.**",
        "The source-bound reference covers the four original questions conditionally. The",
        "coverage ledger retains all 46 obligations and 35 readings without invented",
        "question mappings or closure decisions. It is not a complete product answer.", "",
        "## Decision and evidence", "",
        "| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |",
        "|---|---|---|---|---|---|",
        "| Retain conditional source reference | Each question has its own retained source and strongest contrary | No legal closure decision | Governing P10/P14 standards, source applicability and Gatecoin later treatment | Use as rubric for a complete product answer | Current law or client-specific result |",
        "| Refuse current live method | Whole-route equal-arm allocation and qualified actual responses | Baseline core shortfall; incomplete inventories and responses | Whether larger batches remain faithful and timely | Review one bounded successor method only if complete populations and response qualification can be obtained | Tool failure or legal-direction rejection |",
        "| Retain six controlled tools | Matched source-supported answer effect | No complete original-target pair | Downstream contribution | Preserve receipts and false-warrant controls | Full integration or ranking |", "",
        "## Resource screen", "",
        "These are declared **partial-hybrid** workloads, not a completed four-question bound:", "",
        "| Setting | Calls per arm | New paired calls | Candidate tool actions | Existing baseline gate |",
        "|---|---:|---:|---:|---|",
    ]
    for s in scenarios:
        failures = ", ".join(x["boundary"] for x in s["existing_baseline_gate"]["failures"])
        lines.append(f"| {s['id']} | {s['baseline']['total_calls']} | {s['fresh_paired_calls']} | {s['candidate_only_tool_actions']} | refuse: {failures} |")
    lines += [
        "", f"The original pair has {budget['paired_remaining']} calls left after thirteen spent;",
        f"{budget['global_unspent']} are globally unspent, including unallocated and assessment",
        "slots that have not been transferred. The 64/32 and 64/48 totals fit the paired",
        "reservation arithmetically but are not live-qualified. Their larger-batch output,",
        "latency, complete populations, repair bounds and successor allocation are missing.", "",
        "## Inference status", "",
        "| Evidence class | Status |",
        "|---|---|",
        "| Hard veto screen | Current stage allocation refuses all three scenarios; actual target inventories and responses are missing. |",
        "| Statistically supported ranking | None. |",
        "| Descriptive-only differences | Input-size and call arithmetic plus prior scripted tool delivery. |",
        "| Default readiness | None; no batch setting or tool is promoted. |",
        "| Next evidence | Complete populations, bounded actual response/latency check, reviewed equal-arm allocation, then matched answer review. |", "",
        "The original questions and obligations remain open. No new provider call, tool invocation,",
        "repair attempt or source download occurred. The next task remains `product-contribution`.",
        "The strongest false-success explanation is that byte-fit batches silently lose a",
        "contrary reading or that a supplied solver premise lacks a legal warrant. A complete",
        "source-reviewed answer would test this; this offline record cannot.", "",
        "See `../gap-closure-warrant-review.md` for the conditional legal reference.",
    ]
    return "\n".join(lines) + "\n"


def execute():
    started_clock = time.monotonic()
    require(not OUT.exists() and not RESULT_DOC.exists(), "Work package already started; inspect retained artifacts")
    mission, tools, state, admitted, route, ledger, grant = preflight()
    started = datetime.now(timezone.utc)
    OUT.mkdir(parents=True)
    source = source_ledger(mission, route)
    budget = budget_record(route, ledger, grant)
    gaps = gap_register()
    selected_tools = tool_register(tools)
    require(budget["decision"] == "LIVE_NOT_ADMITTED"
            and all(not s["existing_baseline_gate"]["admitted"] for s in budget["scenarios"]),
            "Live admission unexpectedly changed; stop for a new review")
    save(OUT / "mission-before.json", mission)
    save(OUT / "source-ledger.json", source)
    save(OUT / "budget.json", budget)
    save(OUT / "gap-register.json", gaps)
    save(OUT / "tool-register.json", selected_tools)
    save(OUT / "preflight.json", {"mission_state": state, "admission": admitted,
                                  "route": ref(ROUTE_RESULT), "ledger": ref(LEDGER),
                                  "plan": ref(PLAN), "review": ref(REVIEW)})
    write_text(RESULT_DOC, result_markdown(source, budget))
    manifest = {
        "profile": "legal-mission-gap-closure-manifest.v2",
        "command": f"{PYTHON} scripts/legal_mission_gap_closure.py execute",
        "plan": ref(PLAN), "review": ref(REVIEW), "executor": ref(Path(__file__)),
        "warrant_review": ref(WARRANT),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "environment": {"cwd": str(ROOT), "interpreter": str(ROOT / PYTHON),
                        "python": sys.version, "platform": platform.platform(),
                        "gpu": "CPU-only; CUDA_VISIBLE_DEVICES=-1 before project imports",
                        "seeds": "N/A: deterministic offline accounting"},
        "inputs": [ref(p) for p in (TOOLS, ROUTE_RESULT, ROUTE_DOC, LEDGER,
                                     GRANT, INVENTORY, QUESTIONS, QUALIFIED_CONTEXT,
                                     UNRELATED_ALLOWANCE, GATECOIN_2023, *EXCERPTS.values())],
        "outputs": [ref(p) for p in (OUT / "mission-before.json", OUT / "source-ledger.json", OUT / "budget.json",
                                      OUT / "gap-register.json", OUT / "tool-register.json",
                                      OUT / "preflight.json", RESULT_DOC)],
        "started_utc": started.isoformat(), "finished_utc": datetime.now(timezone.utc).isoformat(),
        "wall_milliseconds": int((time.monotonic() - started_clock) * 1000),
        "new_live_calls": 0, "repair_attempts": 0,
    }
    save(OUT / "run-manifest.json", manifest)
    next_reason = (
        "The four-question conditional warrant reference and honest source identities are retained. "
        "The 64/32 and 64/48 partial-hybrid workloads fit the paired reservation only arithmetically: "
        "existing baseline core allocation, incomplete inventories, actual response/output/latency, "
        "repair headroom and separate P14/Gatecoin populations block live admission. "
        "Return to product-contribution; review a concrete bounded successor method only if these "
        "prerequisites and the original deadline can be met. No automatic repair or live dispatch."
    )
    result = {
        "profile": "legal-mission-gap-closure-result.v2", "status": "OFFLINE_COMPLETE_LIVE_NOT_ADMITTED",
        "outcome": "no_advance", "plan": ref(PLAN), "review": ref(REVIEW),
        "warrant_review": ref(WARRANT), "result_document": ref(RESULT_DOC),
        "run_manifest": ref(OUT / "run-manifest.json"),
        "source_ledger": ref(OUT / "source-ledger.json"),
        "budget": ref(OUT / "budget.json"), "gap_register": ref(OUT / "gap-register.json"),
        "tool_register": ref(OUT / "tool-register.json"),
        "original_questions": 4, "original_obligations": 46, "original_readings": 35,
        "selected_tools_fully_evaluated": 0, "legal_quality_evaluated": False,
        "tool_benefit_evaluated": False, "new_live_calls": 0, "repair_attempts": 0,
        "detours_since_substantive_advance": state["detours_since_advance"],
        "live_calls_used": len(ledger["calls"]), "live_deadline_utc": DEADLINE,
        "next_task": "product-contribution", "next_task_reason": next_reason,
    }
    save(OUT / "result.json", result)
    save(OUT / "next-phase.json", {"after": "offline-gap-closure", "next_task": "product-contribution",
                                   "decision": "LIVE_NOT_ADMITTED", "reason": next_reason,
                                   "result": ref(OUT / "result.json")})
    evidence = [ref(p) for p in (PLAN, REVIEW, WARRANT, RESULT_DOC, OUT / "result.json",
                                  OUT / "source-ledger.json", OUT / "budget.json",
                                  OUT / "gap-register.json", OUT / "tool-register.json")]
    task = next(t for t in mission["tasks"] if t["id"] == "product-contribution")
    task["baseline_evidence"].extend(evidence)
    task["remaining_work_review"] = "docs/implementation/legal-mission-control/results/gap-closure.md"
    mission["history"].append({
        "id": "gap-closure-offline-result-2026-10-11", "task_id": "product-contribution",
        "kind": "product_evaluation", "outcome": "no_advance", "recorded_at_utc": started.isoformat(),
        "decision": "Conditional source reference and corrected resource hypotheses retained; no complete product answer or live admission.",
        "result_evidence": evidence, "next_task": "product-contribution",
        "next_task_reason": next_reason,
        "local_resource_accounting": {"new_live_calls": 0, "repair_attempts": 0,
                                      "total_grant_used": len(ledger["calls"]),
                                      "cumulative_enabling_detours": 8,
                                      "detours_reset": False, "deadline_utc": DEADLINE},
    })
    mission["next_task_reason"] = next_reason
    mission["gap_closure_result"] = ref(OUT / "result.json")
    control.validate(mission, tools, ROOT)
    replace_mission(mission)
    print(json.dumps({"status": result["status"], "result": ref(OUT / "result.json"),
                      "new_live_calls": 0, "detours": 8}, indent=2))


def replace_mission(mission):
    temporary = MISSION.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(mission, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    temporary.replace(MISSION)


def status():
    mission, tools, state, admitted, route, ledger, grant = preflight()
    print(json.dumps({"status": "RECORDED" if (OUT / "result.json").exists() else "READY",
                      "task": mission["current_task"], "admission": admitted["admission"],
                      "detours": state["detours_since_advance"],
                      "live_calls": len(ledger["calls"]), "deadline_utc": DEADLINE}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "execute"))
    args = parser.parse_args()
    if args.action == "status":
        status()
    else:
        execute()


if __name__ == "__main__":
    main()
