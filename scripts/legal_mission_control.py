#!/usr/bin/env python3
"""Read-only admission checks for the legal mission; no dispatch or legal verdict."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BASE = Path("docs/implementation/legal-mission-control")
ANCHORS = {
    "questions": (
        "artifacts/legal-tool-comparison/2026-10-06/T0/attempt-1/questions.json",
        "c52821ffc76c676f3323a7b9aa8cb7d11e3554dde8d851a7cf90d2833528cc19"),
    "inventory": (
        "artifacts/legal-integration-assessment/2026-10-08/input-inventory.json",
        "0f07d5ebdcbcf817422fd2f32bf2cabcdb6de58ab1e5172ade37a349894b3f4b"),
    "cross_reference": (
        "docs/implementation/legal-interpretation-program/follow-up/problem-inventory.json",
        "b5a97ba5f8c5a4540c6436a84631de70d4dbab74c9477ab4c94b648c3d4cf789"),
}
TARGETS = {
    "p10": "responsibility_and_fulfillment",
    "p14": "request_object_standard_attachment",
    "evidence": "observation_to_legal_sufficiency",
    "gatecoin": "case_proposition_and_target_transfer",
}
PACKAGES = {"p10-standard", "p14-attachment", "gatecoin-transfer", "product-contribution"}
TOOL_IDS = {
    "bm25", "legalruleml", "pyarg", "carneades", "clingo", "logical-english",
    "eyecite", "hypo", "cato", "agatha", "sara-ie", "clerc", "mapie", "tweety",
    "scasp", "key", "langgraph", "docling", "ocr", "inspect", "pit", "java",
    "catala", "lean", "z3", "cvc5",
}
STAGES = (
    "available", "target_adapter", "product_invocation", "question_preservation",
    "downstream_delivery", "negative_and_unsupported", "answer_contribution",
)
KINDS = {"source_analysis", "product_evaluation", "engineering"}
DISPOSITIONS = {"selected", "deferred", "target_unsuitable", "conceptual", "supporting"}
INITIAL_DISPOSITIONS = {
    **dict.fromkeys(("bm25", "legalruleml", "pyarg", "carneades", "clingo", "logical-english"), "selected"),
    **dict.fromkeys(("hypo", "cato", "agatha"), "conceptual"),
    **dict.fromkeys(("sara-ie", "clerc", "mapie", "tweety", "scasp", "key", "langgraph"), "deferred"),
    **dict.fromkeys(("docling", "ocr", "inspect", "pit", "java", "catala", "lean", "z3", "cvc5"), "supporting"),
    "eyecite": "target_unsuitable",
}
STAGING_TASK = "answer-staging-preparation"
STAGING_REVIEW = {
    "path": "docs/implementation/legal-mission-control/answer-staging-admission.md",
    "sha256": "0b73b8e8891364524a2c0b86dc1a7ee412f8d3e54b7c897287e7b8a043b16e9a",
}
STAGING_EXCEPTION = {
    "task_id": STAGING_TASK, "review": STAGING_REVIEW,
    "expires_utc": "2026-10-09T12:35:00+00:00", "additional_attempts": 1,
    "prior_detours": 1, "minutes": 120, "live_calls": 0,
}
CONTEXT_TASK = "source-context-boundary-repair"
INTEGRATION_TASK = "tool-integration-completion"
SUCCESSOR_REVISION_ID = "question-first-successor"
INTEGRATION_EXCEPTION = {
    "task_id": INTEGRATION_TASK,
    "approval": {"path": "artifacts/legal-mission-control/2026-10-10/tool-integration/authorization.json",
                 "sha256": "8696c08c2a2445c9362d5eff8264f77a285272c2769ef9c46d4fa31e2ef97e84"},
    "plan": {"path": "docs/plans/legal-mission-tool-integration-execution.md",
             "sha256": "6e1c89ed0c5070f0baad230072fcc36e8edfc7beaf5e8903479a4cb6457acc01"},
    "started_utc": "2026-10-09T19:56:51+00:00",
    "expires_utc": "2026-10-09T21:56:51+00:00",
    "minutes": 120, "live_calls": 0, "additional_attempts": 1, "prior_detours": 3,
}
CONTEXT_EXCEPTION = {
    "task_id": CONTEXT_TASK,
    "approval": {
        "path": "artifacts/legal-mission-control/2026-10-10/context-boundary/approval.json",
        "sha256": "01c49e3559624ba17f4c100ae293401a27467d09c1d53d41e11f1d6178e60267",
    },
    "review": {
        "path": "docs/implementation/legal-mission-control/context-boundary-admission.md",
        "sha256": "ea93e54b74abe7737ce49da33bcba9e420923db21b1479096e71a279d083d09d",
    },
    "plan": {
        "path": "docs/plans/legal-mission-context-boundary-repair.md",
        "sha256": "f378103849a57367dcdc07427ef32f7e6fd8e1642be0046a731eb6d885d60a69",
    },
    "started_utc": "2026-10-09T16:38:48+00:00",
    "expires_utc": "2026-10-09T18:38:48+00:00",
    "additional_attempts": 1, "prior_detours": 2, "minutes": 120, "live_calls": 0,
}


class Refused(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Refused(message)


def read(path):
    return json.loads(path.read_text())


def safe_path(root, value):
    relative = Path(value)
    require(not relative.is_absolute() and ".." not in relative.parts,
            "Evidence must use a worktree-relative path")
    require(not set(relative.parts) & {".git", ".codex", ".agents", ".aws", ".ssh"},
            "Protected metadata is not mission evidence")
    resolved = (root / relative).resolve()
    require(resolved.is_relative_to(root.resolve()), "Evidence escapes the worktree")
    return resolved


def verify_ref(root, ref):
    path = safe_path(root, ref["path"])
    require(path.is_file(), f"Missing evidence: {ref['path']}")
    require(hashlib.sha256(path.read_bytes()).hexdigest() == ref["sha256"],
            f"Changed evidence: {ref['path']}")


def verify_refs(root, value):
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            verify_ref(root, value)
        for item in value.values():
            verify_refs(root, item)
    elif isinstance(value, list):
        for item in value:
            verify_refs(root, item)


def distinct(rows, field):
    index = {row[field]: row for row in rows}
    require(len(index) == len(rows), f"Duplicate {field}")
    return index


def text_fields(row, fields):
    for name in fields:
        require(isinstance(row.get(name), str) and row[name].strip(), f"Missing {name}")


def evidence_list(value, name):
    require(isinstance(value, list) and value
            and all(isinstance(ref, dict) and set(ref) >= {"path", "sha256"} for ref in value),
            f"{name} requires file/hash references, not a claim of PASS")


def execution_view(mission, root):
    """Current dependency program supplements the preserved historical register."""
    reference = mission.get('execution_program')
    if reference is None:
        return None
    verify_ref(root, reference)
    require(Path(reference['path']).parent == Path('docs/implementation/legal-mission-control')
            and Path(reference['path']).name.startswith('execution') and reference['path'].endswith('.json'),
            'Unexpected execution program')
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from scripts.legal_mission_execution import Execution
    execution = Execution(root, reference['path'])
    require(execution.program['prior_detours'] == 9
            and execution.program['deadline_utc'] == '2026-10-12T04:28:01+00:00'
            and execution.program['global_call_ceiling'] == 400,
            'Execution revision changed historical resources')
    return execution


def validate(mission, tools, root=ROOT):
    originals = {}
    for name, (path, sha) in ANCHORS.items():
        verify_ref(root, {"path": path, "sha256": sha})
        originals[name] = read(root / path)
    require(mission["profile"] == "legal-mission-control.v1", "Unknown mission profile")
    require(mission["mission_acceptance"] == "not_established",
            "Task completion cannot certify mission completion")
    require(mission["setup_live_call_budget"] == 0, "This setup does not renew live authorization")
    require(mission["maximum_detours_without_advance"] == 1,
            "A detour-cap change needs a reviewed program revision")
    require(mission["inherited_detour_floor"] == 1,
            "The latest repair without a legal answer change cannot disappear on restart")
    verify_refs(root, mission)
    verify_refs(root, tools)
    live_pilot = mission.get('recorded_live_pilot')
    if live_pilot is not None:
        require(set(live_pilot) == {'task_id', 'authorization', 'protocol', 'plan'}
                and live_pilot['task_id'] == 'product-contribution', 'Unreviewed live pilot registration')
        grant = read(safe_path(root, live_pilot['authorization']['path']))
        require(grant.get('schema') == 'legalmath.mission-pilot-grant.v1'
                and grant.get('authorization') == 'you have 400 calls and 48 hours.  continue'
                and grant.get('maximum') == 400
                and grant.get('started_utc') == '2026-10-10T04:28:01+00:00'
                and grant.get('deadline_utc') == '2026-10-12T04:28:01+00:00'
                and grant.get('historical_unused_transfer') is False
                and grant.get('plan') == live_pilot['plan'], 'Changed explicit live authorization')
    questions = distinct(mission["questions"], "id")
    require(set(questions) == set(TARGETS), "Original questions omitted or replaced")
    for original in originals["questions"]:
        q = questions[original["id"]]
        require(q["question"] == original["question"], "Original question changed")
        require(q["target"] == TARGETS[q["id"]], "Original substantive target changed")
        require(q["status"] in {"open", "review_ready"}, "Unsupported question completion claim")
        if q["status"] == "review_ready":
            evidence_list(q.get("result_evidence"), "Question review")
    inventory = originals["inventory"]
    obligation_ids = {r["obligation_id"] for r in inventory["original_obligations"]}
    reading_ids = {r["reading_id"] for r in inventory["original_readings"]}
    for key, expected in (("original_obligation_ids", obligation_ids),
                          ("original_reading_ids", reading_ids)):
        require(set(mission[key]) == expected and len(mission[key]) == len(expected),
                f"Original denominator changed: {key}")
    decisions = distinct(mission["obligation_review_decisions"], "obligation_id")
    require(set(decisions) <= obligation_ids, "Decision refers to a different obligation")
    for decision in decisions.values():
        evidence_list(decision.get("evidence"), "Obligation review")
        text_fields(decision, ("supported_answer", "remaining_dependency", "contrary"))

    tool_index = distinct(tools, "id")
    require(set(tool_index) == TOOL_IDS, "Surveyed tool omitted or silently replaced")
    for tool in tools:
        require(tool["disposition"] in DISPOSITIONS, "Unknown tool disposition")
        if tool["disposition"] != INITIAL_DISPOSITIONS[tool["id"]]:
            review = tool.get("disposition_review", {})
            require(review.get("previous") == INITIAL_DISPOSITIONS[tool["id"]],
                    "A selected tool cannot be silently deferred to finish integration")
            text_fields(review, ("reason", "impact_on_question"))
            evidence_list(review.get("evidence"), "Tool disposition revision")
        text_fields(tool, ("current_use", "remaining_gap", "next_test_or_reopen"))
        from scripts.legal_integration_acceptance import validate_evaluation
        try:
            disposition = validate_evaluation(tool, root)
        except ValueError as exc:
            raise Refused(str(exc)) from exc
        if disposition['effect_evaluated'] and tool.get('evaluation_completion'):
            require(all(questions.get(q, {}).get('question') == text
                        for q, text in tool.get('evaluation', {}).get('questions', {}).items()),
                    'Evaluation must preserve the original question text')
        evidence_list(tool.get("evidence"), "Tool disposition")
        require(type(tool["fully_integrated"]) is bool, "Integration claim must be a boolean")
        require(set(tool["stages"]) <= set(STAGES), "Unknown integration stage")
        for stage in tool["stages"].values():
            require(stage["level"] in {"code", "reported", "controlled", "live", "evaluated"},
                    "Integration stage needs classified evidence")
            evidence_list(stage.get("evidence"), "Integration stage")
        if tool["fully_integrated"]:
            require(tool["disposition"] == "selected", "Deferred is not integrated")
            require(set(tool["stages"]) == set(STAGES), "Integration acceptance is incomplete")
            require(all(s["level"] in {"controlled", "live", "evaluated"}
                        for s in tool["stages"].values()), "Code/report alone is not full integration")
            require(all(tool["stages"][s]["level"] == "live"
                        for s in ("product_invocation", "downstream_delivery")),
                    "A scripted workflow does not complete the live product evaluation")
            evaluation = tool.get("evaluation", {})
            require(evaluation.get("route") == "actual_product"
                    and evaluation.get("matched_inputs") is True
                    and evaluation.get("finding") in {"helps", "no_benefit", "harmful", "limited"}
                    and tool["stages"]["answer_contribution"]["level"] == "evaluated",
                    "Full integration needs a matched downstream contribution evaluation")
            require(evaluation.get("questions")
                    and all(questions.get(q, {}).get("question") == value
                            for q, value in evaluation["questions"].items()),
                    "Contribution evaluation must preserve original question text")
            for arm in ("baseline", "candidate", "assessment"):
                evidence_list(evaluation.get(arm), f"Contribution {arm}")
            bindings = evaluation.get("input_bindings", {})
            require(bindings.get("baseline") and bindings["baseline"] == bindings.get("candidate"),
                    "Contribution comparison changed its source/question inputs")

    tasks = distinct(mission["tasks"], "id")
    execution = execution_view(mission, root)
    exception = mission.get("one_time_detour_exception")
    if exception is not None:
        require(exception == STAGING_EXCEPTION, "Unreviewed or renamed detour exception")
        require(STAGING_TASK in tasks, "Exception lacks its named task")
        require(tasks[STAGING_TASK]["kind"] == "engineering"
                and tasks[STAGING_TASK].get("return_to") == "product-contribution"
                and tasks[STAGING_TASK]["resource_bounds"] == {
                    "live_calls": 0, "minutes": 120, "repair_attempts": 1},
                "Exception resource scope changed")
    context_exception = mission.get("approved_context_boundary_attempt")
    if context_exception is not None:
        require(context_exception == CONTEXT_EXCEPTION,
                "Unreviewed or renamed consolidated repair exception")
        require(CONTEXT_TASK in tasks and exception == STAGING_EXCEPTION,
                "Consolidated repair lost its named task or spent predecessor")
        require(tasks[CONTEXT_TASK]["kind"] == "engineering"
                and tasks[CONTEXT_TASK].get("return_to") == "product-contribution"
                and tasks[CONTEXT_TASK]["resource_bounds"] == {
                    "live_calls": 0, "minutes": 120, "repair_attempts": 1},
                "Consolidated repair resource scope changed")
    integration_exception = mission.get("approved_tool_integration_attempt")
    if integration_exception is not None:
        require(integration_exception == INTEGRATION_EXCEPTION,
                "Unreviewed integration completion exception")
        require(INTEGRATION_TASK in tasks and context_exception == CONTEXT_EXCEPTION,
                "Integration revision lost its spent predecessor")
        require(tasks[INTEGRATION_TASK]["kind"] == "engineering"
                and tasks[INTEGRATION_TASK].get("return_to") == "product-contribution"
                and tasks[INTEGRATION_TASK]["resource_bounds"] == {
                    "live_calls": 0, "minutes": 120, "repair_attempts": 1},
                "Integration revision resource scope changed")
    successor = mission.get("question_first_successor_admission")
    if successor is not None:
        require(set(successor) == {"revision", "plan", "review", "admission"}
                and successor["revision"] == {
                    "id": SUCCESSOR_REVISION_ID, "prior_detours": 8,
                    "additional_attempts": 1, "live_calls": 0,
                    "repair_attempts": 1, "task_id": "product-contribution"},
                "Unreviewed question-first successor revision")
        require(successor["plan"]["path"] == "docs/plans/legal-mission-question-first-successor.md"
                and successor["review"]["path"] == "docs/implementation/legal-mission-control/question-first-successor-review.md"
                and successor["admission"]["path"] == "artifacts/legal-mission-control/2026-10-11/question-first-successor/admission.json",
                "Question-first successor lost its reviewed method or admission")
        record = read(safe_path(root, successor["admission"]["path"]))
        require(record.get("authorization") == "repair the mission plan with your suggestions.  review the plan throughly and execute"
                and record.get("prior_detours") == 8
                and record.get("additional_attempts") == 1
                and record.get("live_calls") == 0
                and record.get("repair_attempts") == 1
                and record.get("status") == "REVIEWED_LOCAL"
                and 0 < (datetime.fromisoformat(record["expires_utc"]) -
                         datetime.fromisoformat(record["started_utc"])).total_seconds() <= 7200,
                "Question-first successor exceeds its reviewed local authority")
        require(tasks["product-contribution"]["resource_bounds"].get("repair_attempts") in {0, 1},
                "Question-first successor repair allowance changed")
    require({t["id"] for t in tasks.values() if t["kind"] != "engineering"} == PACKAGES,
            "The finite substantive program changed without revision")
    for task in tasks.values():
        require(task["kind"] in KINDS, "Unknown task kind")
        require(task["status"] in {"planned", "ready", "done", "blocked"}, "Unknown task status")
        require(task["questions"] and set(task["questions"]) <= set(TARGETS), "Task lacks original question")
        require(task["answer_targets"] == {q: TARGETS[q] for q in task["questions"]},
                "Task substitutes another answer target (a trigger cannot replace fulfillment)")
        require(task["original_obligation_ids"] and set(task["original_obligation_ids"]) <= obligation_ids,
                "Task lacks original obligation identities")
        require(set(task["tools"]) <= TOOL_IDS, "Task uses an unregistered tool")
        require(set(task["depends_on"]) <= set(tasks) - {task["id"]}, "Invalid task dependency")
        evidence_list(task.get("baseline_evidence"), "Task baseline")
        text_fields(task, ("gap", "expected_answer_change", "counterexample", "disconfirmation",
                           "result_path", "return_condition", "tool_reason", "stop_condition"))
        safe_path(root, task["result_path"])
        require(task["resource_bounds"]["live_calls"] == 0
                and 0 < task["resource_bounds"]["minutes"] <= 120,
                "Current admission covers bounded offline work only; review a live protocol first")
        if task["kind"] == "source_analysis" and task["status"] == "blocked":
            require(task.get("blocker_kind") != "client_facts",
                    "Missing client facts do not block conditional source analysis")
        if task["status"] == "blocked":
            text_fields(task, ("blocker_kind", "blocker_scope"))
            evidence_list(task.get("blocker_evidence"), "Task blocker")
        if task["kind"] == "engineering":
            parent = tasks.get(task.get("blocked_task"), {})
            require(parent.get("kind") in {"source_analysis", "product_evaluation"},
                    "Engineering needs a substantive parent task")
            require(parent.get("status") in {"ready", "blocked"}, "Detour parent is not an active task")
            evidence_list(task.get("blocker_evidence"), "Reproduced blocker")
            require(task.get("return_to") == parent.get("id"),
                    "Engineering needs a reproduced blocker and a return task")
            require(task["resource_bounds"].get("repair_attempts") == 1,
                    "Engineering detours have one attempt before returning")

    history = mission["history"]
    distinct(history, "id")
    # This is a lower bound from the final predecessor repair, not a recount of
    # every historical campaign. A new control directory cannot erase it.
    detours = mission["inherited_detour_floor"]
    exception_used = False
    context_exception_used = False
    integration_exception_used = False
    source_span_revision_used = False
    decomposed_revision_used = False
    inventory_window_revision_used = False
    route_repair_used = False
    successor_used = False
    execution_attempts = set()
    completed = set()
    for row in history:
        require(row["task_id"] in tasks, "History lost its originating task")
        task = tasks[row["task_id"]]
        require(row["kind"] == task["kind"], "History changes task kind")
        evidence_list(row["result_evidence"], "Refresh result")
        text_fields(row, ("decision", "next_task_reason"))
        require(row["next_task"] in tasks, "Refresh lacks a known next task")
        require(row["outcome"] in {"substantive_advance", "no_advance", "candidate_failed", "invalid_run"},
                "Unknown result classification")
        if 'execution_node' in row:
            require(execution is not None and row['execution_node'] in execution.tasks,
                    'Unregistered execution node')
            node = execution.tasks[row['execution_node']]
            key = (row['execution_node'], row.get('execution_attempt'))
            require(key not in execution_attempts and type(key[1]) is int
                    and 1 <= key[1] <= node['maximum_attempts'], 'Repeated execution attempt')
            execution_attempts.add(key)
            require(row['task_id'] == 'product-contribution' and row['next_task'] == 'product-contribution'
                    and row['outcome'] == 'no_advance', 'Execution result cannot claim legal closure')
            if node['kind'] == 'engineering':
                detours += 1
        revision = row.get('bounded_method_revision')
        if revision is not None and revision.get('id') == SUCCESSOR_REVISION_ID:
            require(successor is not None and not successor_used and detours == 8
                    and task['id'] == 'product-contribution' and row['outcome'] == 'no_advance'
                    and revision == successor['revision']
                    and successor['plan'] in row['result_evidence']
                    and successor['review'] in row['result_evidence'],
                    'Unreviewed or repeated question-first successor attempt')
            detours += 1
            successor_used = True
        elif revision is not None and revision.get('id') == 'evidence-route-repair':
            admission = mission.get('route_repair_admission', {})
            require(not route_repair_used and detours == 7
                    and task['id'] == 'product-contribution' and row['outcome'] == 'no_advance'
                    and revision == {'id': 'evidence-route-repair', 'prior_detours': 7,
                        'additional_attempts': 1, 'live_calls': 0}
                    and admission.get('revision') == revision,
                    'Unreviewed or repeated evidence-route repair')
            require(admission.get('plan', {}).get('path') == 'docs/plans/legal-mission-route-repair.md'
                    and admission.get('review', {}).get('path') == 'docs/implementation/legal-mission-control/route-repair-review.md'
                    and admission.get('authorization') == 'create a plan to do what you suggest.  review the plan thoroughly.  amend the allow list and all other necessary tools as well as structure your work to use the exact form to avoid generating approvals.  Ask any approvals upfront and in group to minimize distraction.  execute the plan'
                    and 0 < (datetime.fromisoformat(admission['expires_utc']) - datetime.fromisoformat(admission['started_utc'])).total_seconds() <= 7200,
                    'Evidence-route repair lacks bounded reviewed authorization')
            evidence_list([admission['plan'], admission['review']], 'Route repair review')
            detours += 1
            route_repair_used = True
        elif revision is not None and revision.get('id') == 'sol-inventory-window':
            require(not inventory_window_revision_used and decomposed_revision_used and detours == 6
                    and task['id'] == 'product-contribution' and row['outcome'] == 'no_advance'
                    and revision == {'id': 'sol-inventory-window', 'prior_detours': 6,
                        'enabling_deadline_utc': '2026-10-10T11:30:00+00:00',
                        'additional_attempts': 1},
                    'Unreviewed or repeated inventory-window enabling detour')
            require(any(r['path'] == 'docs/plans/legal-mission-sol-inventory-window.md'
                        for r in row['result_evidence']), 'Inventory-window detour lacks its reviewed method')
            detours += 1
            inventory_window_revision_used = True
        elif revision is not None and revision.get('id') == 'decomposed':
            require(not decomposed_revision_used and source_span_revision_used and detours == 5
                    and task['id'] == 'product-contribution' and row['outcome'] == 'no_advance'
                    and revision == {'id': 'decomposed', 'prior_detours': 5,
                        'enabling_deadline_utc': '2026-10-10T06:00:00+00:00',
                        'additional_attempts': 1},
                    'Unreviewed or repeated decomposed enabling detour')
            require(any(r['path'] == 'docs/plans/legal-mission-live-pilot-decomposed.md'
                        for r in row['result_evidence']), 'Decomposed detour lacks its reviewed method')
            detours += 1
            decomposed_revision_used = True
        elif revision is not None:
            require(not source_span_revision_used and detours == 4
                    and task['id'] == 'product-contribution'
                    and row['outcome'] == 'no_advance'
                    and revision == {'id': 'source-spans', 'prior_detours': 4,
                        'enabling_deadline_utc': '2026-10-10T06:35:00+00:00',
                        'additional_attempts': 1},
                    'Unreviewed or repeated source-span enabling detour')
            require(any(r['path'] == 'docs/plans/legal-mission-live-pilot-source-spans.md'
                        for r in row['result_evidence']),
                    'Source-span detour lacks its reviewed method')
            detours += 1
            source_span_revision_used = True
        if row["outcome"] == "substantive_advance":
            require(task["kind"] != "engineering", "An engineering repair cannot itself reset drift")
            advance = row.get("advance", {})
            text_fields(advance, ("answer_before", "answer_after", "inference", "contrary", "remaining_dependency"))
            require(advance["answer_before"] != advance["answer_after"], "No answer change recorded")
            require(advance.get("evidence_kind") in {"source_argument", "product_counterexample"},
                    "Tests/counts alone are not substantive progress")
            evidence_list(advance.get("primary_evidence"), "Substantive advance")
            require(set(advance.get("obligation_ids", [])) & set(task["original_obligation_ids"]),
                    "Advance does not address the original obligations")
            detours = 0
        elif task["kind"] == "engineering":
            is_exception = exception is not None and task["id"] == STAGING_TASK
            is_context_exception = context_exception is not None and task["id"] == CONTEXT_TASK
            is_integration_exception = integration_exception is not None and task["id"] == INTEGRATION_TASK
            if is_exception:
                require(not exception_used and detours == exception["prior_detours"],
                        "Detour exception already used or predecessor changed")
                exception_used = True
            if is_context_exception:
                require(not context_exception_used and exception_used
                        and detours == context_exception["prior_detours"],
                        "Consolidated repair already used or predecessor changed")
                context_exception_used = True
            if is_integration_exception:
                require(not integration_exception_used and context_exception_used
                        and detours == integration_exception["prior_detours"],
                        "Integration attempt already used or predecessor changed")
                integration_exception_used = True
            detours += 1
            require(is_exception or is_context_exception or is_integration_exception
                    or detours <= mission["maximum_detours_without_advance"],
                    "Recorded engineering work exceeded the cumulative detour allowance")
            require(row["next_task"] == task["return_to"], "A detour must return to substantive work")
        if task["status"] == "done":
            completed.add(task["id"])
    require(all(t["id"] in completed for t in tasks.values() if t["status"] == "done"),
            "Task completion lacks a result and refresh")
    if successor is not None:
        require(tasks['product-contribution']['resource_bounds']['repair_attempts'] ==
                (0 if successor_used else 1),
                'Question-first successor repair was consumed or not admitted correctly')
        if not successor_used:
            require(detours == 8, 'Question-first successor predecessor changed')
            detours += 1  # Reserved once at admission, then retained by its result row.
    local_completion = mission.get('local_completion_revision')
    if local_completion is not None:
        require(set(local_completion) == {'authorization', 'plan'}, 'Unknown local completion revision')
        require(local_completion['authorization']['path'] ==
                'artifacts/legal-mission-control/2026-10-12/completion/authorization.json'
                and local_completion['plan']['path'] ==
                'docs/plans/legal-mission-integration-completion-execution-2026-10-12.md',
                'Unexpected completion plan or authority')
        record = read(safe_path(root, local_completion['authorization']['path']))
        require(record.get('profile') == 'legal-mission-completion-local.v1'
                and record.get('prior_registered_detours') == detours == 14
                and record.get('reconciled_prior_attempts') == 1
                and record.get('additional_attempts') == 1 and record.get('live_calls') == 0
                and record.get('historical_charged_calls') == 41
                and local_completion['plan'] in record['protected_evidence']
                and 0 < (datetime.fromisoformat(record['deadline_utc']) -
                         datetime.fromisoformat(record['started_utc'])).total_seconds() <= 7200,
                'Completion revision changed its finite local scope')
        evidence_list(record['protected_evidence'], 'Completion baseline and review')
        verify_refs(root, record)
        require(any(r['id'] == 'integration-completion-register-2026-10-12'
                    and local_completion['authorization'] in r['result_evidence']
                    for r in history), 'Completion revision has no registered reconciliation')
        detours += 2  # Prior partial attempt and this single reserved local package.
    remaining_work = mission.get('remaining_work_revision')
    if remaining_work is not None:
        require(set(remaining_work) == {'authorization', 'plan'}, 'Unknown remaining-work revision')
        record = read(safe_path(root, remaining_work['authorization']['path']))
        require(remaining_work['authorization']['path'] ==
                'artifacts/legal-mission-control/2026-10-12/remaining-work/authorization.json'
                and remaining_work['plan']['path'] ==
                'docs/plans/legal-mission-remaining-work-2026-10-12.md'
                and record.get('profile') == 'legal-mission-remaining-local.v1'
                and record.get('prior_registered_detours') == detours == 16
                and record.get('additional_attempts') == 1 and record.get('live_calls') == 0
                and record.get('historical_charged_calls') == 41
                and remaining_work['plan'] in record['protected_evidence']
                and 0 < (datetime.fromisoformat(record['deadline_utc']) -
                         datetime.fromisoformat(record['started_utc'])).total_seconds() <= 7200,
                'Remaining-work revision changed its finite local scope')
        evidence_list(record['protected_evidence'], 'Remaining-work baseline and review')
        verify_refs(root, record)
        require(any(r['id'] == 'remaining-work-register-2026-10-12'
                    and remaining_work['authorization'] in r['result_evidence'] for r in history),
                'Remaining work lacks its reviewed registration')
        detours += 1
    context_revision = mission.get('context_integration_revision')
    if context_revision is not None:
        require(set(context_revision) == {'authorization', 'plan'}, 'Unknown context integration revision')
        record = read(safe_path(root, context_revision['authorization']['path']))
        require(record.get('profile') == 'legal-context-integration-local.v1'
                and record.get('prior_registered_detours') == detours == 17
                and record.get('additional_attempts') == 1 and record.get('live_calls') == 0
                and record.get('historical_charged_calls') == 41
                and context_revision['plan'] in record.get('protected_evidence', [])
                and record.get('user_instruction') == '1. document your survey thoroughly in the latex document.  2. repaire the /home/chakwong/python/legalmath/docs/plans/legal-mission-capacity-resolution-2026-10-12.md  with what you suggested.  review the plan and execute'
                and 0 < (datetime.fromisoformat(record['deadline_utc']) -
                         datetime.fromisoformat(record['started_utc'])).total_seconds() <= 7200,
                'Context integration changed its reviewed finite scope')
        verify_refs(root, record)
        require(any(r['id'] == 'context-integration-register-2026-10-12'
                    and context_revision['authorization'] in r['result_evidence'] for r in history),
                'Context integration lacks reviewed registration')
        detours += 1
    master = mission.get('integration_master')
    if master is not None:
        require(master.get('profile') == 'legal-integration-master-registration.v1'
                and master.get('prior_detours') == detours == 18
                and master.get('additional_consolidated_revision') == 1
                and master.get('historical_calls') == 41,
                'Integration master changed historical resources')
        require(master['program']['path'] == 'docs/implementation/legal-mission-control/integration-master.json'
                and master['plan']['path'] == 'docs/plans/legal-integration-master-2026-10-13.md'
                and master['contract']['path'] == 'docs/plans/legal-mission-integration-completion-contract-2026-10-12.md',
                'Unexpected master scope')
        from scripts.legal_integration_master import summary as master_summary
        verify_refs(root, master)
        master_state = master_summary(root)
        master_rows = [r for r in history if 'master_node' in r]
        identities = [(r['master_node'], r.get('master_attempt')) for r in master_rows]
        require(len(identities) == len(set(identities)), 'Duplicate master history')
        for row in master_rows:
            node = master_state['tasks'].get(row['master_node'])
            require(node is not None and type(row.get('master_attempt')) is int
                    and 1 <= row['master_attempt'] <= node['attempts_used'], 'Foreign master history')
        detours += 1
        reopening = master.get('reviewed_reopening')
        if reopening is not None:
            require(reopening.get('prior_detours') == detours == 19
                    and reopening.get('additional_consolidated_revision') == 1
                    and reopening.get('prior_charged_calls') == 175
                    and reopening.get('user_instruction'), 'Invalid reviewed master reopening')
            verify_refs(root, reopening)
            require(any(r['id'] == 'integration-master-reviewed-reopening-2026-10-13'
                        and reopening['review'] in r['result_evidence'] for r in history),
                    'Missing reviewed reopening history')
            detours += 1
        revision = master.get('acceptance_revision')
        if revision is not None:
            require(revision.get('prior_detours') == detours == 20
                    and revision.get('additional_consolidated_revision') == 1
                    and revision.get('prior_charged_calls') == 232
                    and revision.get('live_calls_added') == 0,
                    'Acceptance revision changed historical resources')
            program = read(safe_path(root, master['program']['path']))
            require(program.get('acceptance_revision') == revision,
                    'Acceptance registration differs from executable program')
            require(any(r['id'] == 'integration-master-acceptance-revision-2026-10-13'
                        and revision['review'] in r['result_evidence'] for r in history),
                    'Missing acceptance revision history')
            from scripts.legal_integration_acceptance import validate_inventory, validate_applicability
            try:
                validate_applicability(read(safe_path(root, revision['applicability']['path'])), root)
                inventory_rows = validate_inventory(read(safe_path(root, revision['inventory']['path'])),
                                                    obligation_ids, reading_ids, root)
            except ValueError as exc:
                raise Refused(str(exc)) from exc
            detours += 1
        continuation = master.get('remaining_work_revision')
        if continuation is not None:
            require(continuation.get('prior_detours') == detours == 21
                    and continuation.get('additional_consolidated_revision') == 1
                    and continuation.get('prior_charged_calls') == 232
                    and continuation.get('live_calls_added') == 0,
                    'Remaining work changed historical resources')
            program = read(safe_path(root, master['program']['path']))
            require(program.get('remaining_work_revision') == continuation,
                    'Remaining work registration differs from program')
            require(any(r['id'] == 'integration-master-remaining-work-2026-10-13'
                        and continuation['review'] in r['result_evidence'] for r in history),
                    'Missing remaining work review history')
            from scripts.legal_integration_acceptance import current_register
            try:
                validate_applicability(read(safe_path(root, current_register(program, 'applicability')['path'])), root)
                inventory_rows = validate_inventory(
                    read(safe_path(root, current_register(program, 'inventory')['path'])),
                    obligation_ids, reading_ids, root)
            except ValueError as exc:
                raise Refused(str(exc)) from exc
            detours += 1
        substantive = master.get('substantive_continuation_revision')
        if substantive is not None:
            require(substantive.get('profile') == 'legal-substantive-continuation.v1'
                    and substantive.get('prior_detours') == detours == 22
                    and substantive.get('additional_consolidated_revision') == 1
                    and substantive.get('prior_charged_calls') == 232
                    and substantive.get('live_calls_added') == 0,
                    'Substantive continuation changed historical resources')
            program = read(safe_path(root, master['program']['path']))
            require(program.get('substantive_continuation_revision') == substantive,
                    'Substantive continuation registration differs from program')
            require(any(r['id'] == 'integration-master-substantive-continuation-2026-10-14'
                        and substantive['review'] in r['result_evidence'] for r in history),
                    'Missing substantive continuation history')
            verify_refs(root, substantive)
            detours += 1
            correction = substantive.get('post_review')
            if correction:
                require(correction.get('profile') == 'legal-substantive-correction.v1'
                        and correction.get('prior_detours') == detours == 23
                        and correction.get('additional_consolidated_revision') == 1
                        and correction.get('live_calls_added') == 0,
                        'Substantive correction changed resource accounting')
                require(any(r['id'] == 'integration-master-substantive-correction-2026-10-14'
                            and correction['review'] in r['result_evidence'] for r in history),
                    'Missing substantive correction history')
                detours += 1
        execution_refresh = master.get('execution_refresh')
        if execution_refresh:
            require(execution_refresh.get('profile') == 'legal-execution-refresh.v1'
                    and execution_refresh.get('prior_detours') == detours == 24
                    and execution_refresh.get('additional_consolidated_revision') == 1
                    and execution_refresh.get('prior_charged_calls') == 232
                    and execution_refresh.get('live_calls_added') == 0,
                    'Execution refresh changed historical resources')
            program = read(safe_path(root, master['program']['path']))
            require(program.get('execution_refresh') == execution_refresh,
                    'Execution refresh registration differs from program')
            require(any(r['id'] == 'integration-master-execution-refresh-2026-10-14'
                        and execution_refresh['review'] in r['result_evidence'] for r in history),
                    'Missing execution refresh review history')
            verify_refs(root, execution_refresh)
            detours += 1
            repair = execution_refresh.get('post_review')
            if repair:
                require(repair.get('profile') == 'legal-execution-refresh-repair.v1'
                        and repair.get('prior_detours') == detours == 25
                        and repair.get('additional_consolidated_revision') == 1
                        and repair.get('live_calls_added') == 0,
                        'Execution refresh repair changed historical resources')
                require(any(r['id'] == 'integration-master-execution-refresh-repair-2026-10-14'
                            and repair['review'] in r['result_evidence'] for r in history),
                        'Missing failure-triggered repair history')
                detours += 1
                binding_fix = repair.get('binding_fix')
                if binding_fix:
                    require(binding_fix.get('profile') == 'legal-execution-binding-fix.v1'
                            and binding_fix.get('prior_detours') == detours == 26
                            and binding_fix.get('additional_consolidated_revision') == 1
                            and binding_fix.get('live_calls_added') == 0,
                            'Binding correction changed historical resources')
                    require(any(r['id'] == 'integration-master-binding-fix-2026-10-14'
                                and binding_fix['review'] in r['result_evidence'] for r in history),
                            'Missing binding correction history')
                    detours += 1
                response_repair = repair.get('response_repair')
                if response_repair:
                    require(response_repair.get('profile') == 'legal-execution-response-repair.v1'
                            and response_repair.get('prior_detours') == detours == 27
                            and response_repair.get('additional_consolidated_revision') == 1
                            and response_repair.get('live_calls_added') == 0,
                            'Response correction changed historical resources')
                    require(any(r['id'] == 'integration-master-response-repair-2026-10-14'
                                and response_repair['review'] in r['result_evidence'] for r in history),
                            'Missing response correction history')
                    detours += 1
                    account = response_repair.get('account_correction')
                    if account:
                        require(account.get('profile') == 'legal-requirement-account-correction.v1'
                                and account.get('prior_detours') == detours == 28
                                and account.get('additional_consolidated_revision') == 1
                                and account.get('live_calls_added') == 0,
                                'Account correction changed historical resources')
                        require(any(r['id'] == 'integration-master-account-correction-2026-10-14'
                                    and account['review'] in r['result_evidence'] for r in history),
                                'Missing account correction history')
                        detours += 1
        prerequisites = master.get('prerequisite_repair')
        if prerequisites:
            require(prerequisites.get('profile') == 'integration-prerequisites.v1'
                and prerequisites.get('prior_detours') == detours == 29
                and prerequisites.get('additional_consolidated_revision') == 1
                and prerequisites.get('live_calls_added') == 0, 'Prerequisite repair changed historical resources')
            require(program.get('prerequisite_repair') == prerequisites, 'Master prerequisite revision differs')
            require(any(r['id'] == 'integration-master-prerequisites-2026-10-14'
                and prerequisites['review'] in r['result_evidence'] for r in history), 'Missing prerequisite review history')
            verify_refs(root, prerequisites)
            detours += 1
        recovery = master.get('execution_recovery')
        if recovery:
            require(recovery.get('profile') == 'integration-execution-recovery.v1'
                and recovery.get('prior_detours') == detours == 30
                and recovery.get('additional_consolidated_revision') == 1
                and recovery.get('live_calls_added') == 0, 'Execution recovery changed historical resources')
            require(program.get('execution_recovery') == recovery, 'Master recovery revision differs')
            require(any(r['id'] == 'integration-master-execution-recovery-2026-10-14'
                and recovery['review'] in r['result_evidence'] for r in history), 'Missing recovery review history')
            verify_refs(root, recovery)
            detours += 1
        continuation = master.get('service_continuation')
        if continuation:
            require(continuation.get('profile') == 'integration-service-continuation.v1'
                and continuation.get('prior_detours') == detours == 31
                and continuation.get('additional_consolidated_revision') == 1
                and continuation.get('live_calls_added') == 0, 'Service continuation changed historical resources')
            require(program.get('service_continuation') == continuation, 'Master service revision differs')
            require(any(r['id'] == 'integration-master-service-continuation-2026-10-14'
                and continuation['review'] in r['result_evidence'] for r in history), 'Missing service continuation history')
            verify_refs(root, continuation)
            detours += 1
        delay_repair = master.get('retry_delay_repair')
        if delay_repair:
            require(delay_repair.get('profile') == 'integration-retry-delay-repair.v1'
                and delay_repair.get('prior_detours') == detours == 32
                and delay_repair.get('additional_consolidated_revision') == 1
                and delay_repair.get('live_calls_added') == 0, 'Retry-delay repair changed historical resources')
            require(program.get('retry_delay_repair') == delay_repair, 'Master retry-delay revision differs')
            require(any(r['id'] == 'integration-master-retry-delay-repair-2026-10-14'
                and delay_repair['review'] in r['result_evidence'] for r in history), 'Missing retry-delay repair history')
            verify_refs(root, delay_repair)
            detours += 1
        canary_repair = master.get('canary_validation_repair')
        if canary_repair:
            require(canary_repair.get('profile') == 'integration-canary-validation-repair.v1'
                and canary_repair.get('prior_detours') == detours == 33
                and canary_repair.get('additional_consolidated_revision') == 1
                and canary_repair.get('live_calls_added') == 0, 'Canary repair changed historical resources')
            require(program.get('canary_validation_repair') == canary_repair, 'Master canary repair differs')
            require(any(r['id'] == 'integration-master-canary-validation-repair-2026-10-14'
                and canary_repair['review'] in r['result_evidence'] for r in history), 'Missing canary repair history')
            verify_refs(root, canary_repair)
            detours += 1
        phased_repair = master.get('phased_acquisition_repair')
        if phased_repair:
            require(phased_repair.get('profile') == 'integration-phased-acquisition-repair.v1'
                and phased_repair.get('prior_detours') == detours == 34
                and phased_repair.get('additional_consolidated_revision') == 1
                and phased_repair.get('live_calls_added') == 0, 'Phased repair changed historical resources')
            require(program.get('phased_acquisition_repair') == phased_repair, 'Master phased repair differs')
            require(any(r['id'] == 'integration-master-phased-acquisition-repair-2026-10-15'
                and phased_repair['review'] in r['result_evidence'] for r in history), 'Missing phased repair history')
            verify_refs(root, phased_repair)
            detours += 1
        route_repair = master.get('route_context_repair')
        if route_repair:
            require(route_repair.get('profile') == 'integration-route-context-repair.v1'
                and route_repair.get('prior_detours') == detours == 35
                and route_repair.get('additional_consolidated_revision') == 1
                and route_repair.get('live_calls_added') == 0, 'Route repair changed historical resources')
            require(program.get('route_context_repair') == route_repair, 'Master route repair differs')
            require(any(r['id'] == 'integration-master-route-context-repair-2026-10-15'
                and route_repair['review'] in r['result_evidence'] for r in history), 'Missing route repair history')
            verify_refs(root, route_repair)
            detours += 1
        account_repair = master.get('account_capacity_repair')
        if account_repair:
            require(account_repair.get('profile') == 'integration-account-capacity-repair.v1'
                and account_repair.get('prior_detours') == detours == 36
                and account_repair.get('additional_consolidated_revision') == 1
                and account_repair.get('live_calls_added') == 0, 'Account repair changed historical resources')
            require(program.get('account_capacity_repair') == account_repair, 'Master account repair differs')
            require(any(r['id'] == 'integration-master-account-capacity-repair-2026-10-15'
                and account_repair['review'] in r['result_evidence'] for r in history), 'Missing account repair history')
            verify_refs(root, account_repair)
            detours += 1
        schema_repair = master.get('response_schema_repair')
        if schema_repair:
            require(schema_repair.get('profile') == 'integration-response-schema-repair.v1'
                and schema_repair.get('prior_detours') == detours == 37
                and schema_repair.get('additional_consolidated_revision') == 1
                and schema_repair.get('live_calls_added') == 0, 'Schema repair changed historical resources')
            require(program.get('response_schema_repair') == schema_repair, 'Master schema repair differs')
            require(any(r['id'] == 'integration-master-response-schema-repair-2026-10-15'
                and schema_repair['review'] in r['result_evidence'] for r in history), 'Missing schema repair history')
            verify_refs(root, schema_repair)
            detours += 1
        lossless_repair = master.get('lossless_account_repair')
        if lossless_repair:
            require(lossless_repair.get('profile') == 'integration-lossless-account-repair.v1'
                and lossless_repair.get('prior_detours') == detours == 38
                and lossless_repair.get('additional_consolidated_revision') == 1
                and lossless_repair.get('live_calls_added') == 0, 'Lossless repair changed historical resources')
            require(program.get('lossless_account_repair') == lossless_repair, 'Master lossless repair differs')
            require(any(r['id'] == 'integration-master-lossless-account-repair-2026-10-15'
                and lossless_repair['review'] in r['result_evidence'] for r in history), 'Missing lossless repair history')
            verify_refs(root, lossless_repair)
            detours += 1
        qualification = master.get('qualification_continuation')
        if qualification:
            require(qualification.get('profile') == 'integration-qualification-continuation.v1'
                and qualification.get('prior_detours') == detours == 39
                and qualification.get('additional_consolidated_revision') == 1
                and qualification.get('live_calls_added') == 0,
                'Qualification continuation changed historical resources')
            require(program.get('qualification_continuation') == qualification, 'Master qualification continuation differs')
            require(any(r['id'] == 'integration-master-qualification-continuation-2026-10-15'
                and qualification['review'] in r['result_evidence'] for r in history),
                'Missing qualification continuation history')
            verify_refs(root, qualification)
            detours += 1
        instructions = master.get('account_instruction_repair')
        if instructions:
            require(instructions.get('profile') == 'integration-account-instruction-repair.v1'
                and instructions.get('prior_detours') == detours == 40
                and instructions.get('additional_consolidated_revision') == 1
                and instructions.get('live_calls_added') == 0,
                'Instruction repair changed historical resources')
            require(program.get('account_instruction_repair') == instructions, 'Master instruction repair differs')
            require(any(r['id'] == 'integration-master-account-instruction-repair-2026-10-15'
                and instructions['review'] in r['result_evidence'] for r in history),
                'Missing instruction repair history')
            verify_refs(root, instructions)
            detours += 1
        reconstruction = master.get('account_reconstruction_repair')
        if reconstruction:
            require(reconstruction.get('profile') == 'integration-account-reconstruction-repair.v1'
                and reconstruction.get('prior_detours') == detours == 41
                and reconstruction.get('additional_consolidated_revision') == 1
                and reconstruction.get('live_calls_added') == 0,
                'Reconstruction repair changed historical resources')
            require(program.get('account_reconstruction_repair') == reconstruction,
                'Master reconstruction repair differs')
            require(any(r['id'] == 'integration-master-account-reconstruction-repair-2026-10-15'
                and reconstruction['review'] in r['result_evidence'] for r in history),
                'Missing reconstruction repair history')
            verify_refs(root, reconstruction)
            detours += 1
        capacity = master.get('complete_account_capacity_repair')
        if capacity:
            require(capacity.get('profile') == 'integration-complete-account-capacity-repair.v1'
                and capacity.get('prior_detours') == detours == 42
                and capacity.get('additional_consolidated_revision') == 1
                and capacity.get('live_calls_added') == 0, 'Capacity repair changed historical resources')
            require(program.get('complete_account_capacity_repair') == capacity, 'Master capacity repair differs')
            require(any(r['id'] == 'integration-master-complete-account-capacity-repair-2026-10-16'
                and capacity['review'] in r['result_evidence'] for r in history), 'Missing capacity repair history')
            verify_refs(root, capacity)
            detours += 1
        repair = master.get('repair_execution')
        if repair:
            require(repair.get('profile') == 'integration-repair-execution.v1'
                and repair.get('prior_detours') >= detours == 43
                and repair.get('additional_consolidated_revision') == 1
                and repair.get('live_calls_added') == 0, 'Repair execution changed historical resources')
            require(program.get('repair_execution') == repair, 'Master repair execution differs')
            require(any(r['id'] == 'integration-repair-execution-' + Path(repair['work']).name
                and repair['review'] in r['result_evidence'] for r in history), 'Missing bounded repair history')
            verify_refs(root, repair)
            detours = repair['prior_detours'] + 1
        local_refresh = master.get('local_refresh')
        if local_refresh:
            require(local_refresh.get('profile') == 'integration-post-r10-local-refresh.v1'
                and local_refresh.get('prior_detours') == detours == 50
                and local_refresh.get('additional_consolidated_revision') == 1
                and local_refresh.get('live_calls_added') == local_refresh.get('additional_task_attempts') == 0
                and program.get('local_refresh') == local_refresh, 'Local refresh changed historical resources')
            require(any(r['id'] == 'integration-master-local-refresh-2026-10-16'
                and local_refresh['review'] in r['result_evidence'] for r in history), 'Missing local refresh history')
            verify_refs(root, local_refresh)
            detours += 1
        delayed = master.get('delayed_service_recovery')
        if delayed:
            require(delayed.get('profile') == 'integration-delayed-service.v1'
                and delayed.get('prior_detours') == detours == 51
                and delayed.get('additional_consolidated_revision') == 1
                and delayed.get('live_calls_added') == delayed.get('additional_task_attempts') == 0
                and delayed.get('additional_transport_replacements') == 24
                and program.get('delayed_service_recovery') == delayed,
                'Delayed continuation changed historical resources')
            require(any(r['id'] == 'integration-master-delayed-service-2026-10-16'
                and delayed['review'] in r['result_evidence'] for r in history), 'Missing delayed service history')
            verify_refs(root, delayed)
            detours += 1
        frontier = master.get('frontier_refresh')
        if frontier:
            require(frontier.get('profile') == 'integration-frontier-refresh.v1'
                and frontier.get('prior_detours') == detours == 52
                and frontier.get('additional_consolidated_revision') == 1
                and frontier.get('live_calls_added') == frontier.get('additional_transport_replacements') == 0
                and frontier.get('additional_task_attempts') == 1
                and frontier.get('cumulative_additional_attempts') == 20
                and frontier.get('repair_allowance_added') == 0
                and program.get('frontier_refresh') == frontier,
                'Frontier refresh changed historical resources')
            require(any(r['id'] == 'integration-master-frontier-refresh-2026-10-17'
                and frontier['review'] in r['result_evidence'] for r in history), 'Missing frontier refresh history')
            verify_refs(root, frontier)
            detours += 1
        settled = master.get('settled_recovery')
        if settled:
            require(settled.get('profile') == 'integration-settled-recovery.v1'
                and settled.get('prior_detours') == detours == 53
                and settled.get('additional_consolidated_revision') == 1
                and settled.get('additional_task_attempts') == 2
                and settled.get('attempt_increments') == {'acquire-evidence': 1, 'acquire-p10': 1}
                and settled.get('live_calls_added') == settled.get('additional_transport_replacements') == 0
                and program.get('settled_recovery') == settled, 'Settled recovery changed reviewed authority')
            require(any(r['id'] == 'integration-master-settled-recovery-2026-10-17'
                and settled['review'] in r['result_evidence'] for r in history), 'Missing settled recovery history')
            verify_refs(root, settled)
            detours += 1
        failure_recovery = master.get('failure_recovery')
        if failure_recovery:
            require(failure_recovery.get('profile') == 'integration-failure-recovery.v1'
                and failure_recovery.get('prior_detours') == detours == 54
                and failure_recovery.get('additional_consolidated_revision') == 1
                and failure_recovery.get('additional_task_attempts') == 1
                and failure_recovery.get('reopened_nodes') == ['acquire-p10']
                and failure_recovery.get('maximum_passes') == 2
                and failure_recovery.get('live_calls_added') == 0
                and program.get('failure_recovery') == failure_recovery, 'Unreviewed bounded failure recovery')
            require(any(r['id'] == 'integration-master-failure-recovery-2026-10-19'
                and failure_recovery['review'] in r['result_evidence'] for r in history), 'Missing failure recovery history')
            verify_refs(root, failure_recovery)
            detours += 1
        gap_preservation = master.get('gap_preservation')
        if gap_preservation:
            require(gap_preservation.get('profile') == 'integration-gap-preservation.v1'
                and gap_preservation.get('prior_detours') == detours == 55
                and gap_preservation.get('additional_consolidated_revision') == 1
                and gap_preservation.get('additional_task_attempts') == 1
                and gap_preservation.get('reopened_nodes') == ['acquire-p10']
                and gap_preservation.get('maximum_passes') == 1
                and gap_preservation.get('live_calls_added') == 0
                and program.get('gap_preservation') == gap_preservation, 'Unreviewed gap preservation')
            require(any(r['id'] == 'integration-master-gap-preservation-2026-10-19'
                and gap_preservation['review'] in r['result_evidence'] for r in history), 'Missing gap-preservation history')
            verify_refs(root, gap_preservation)
            detours += 1
        synthesis_continuation = master.get('synthesis_continuation')
        if synthesis_continuation:
            require(synthesis_continuation.get('profile') == 'integration-synthesis-continuation.v1'
                and synthesis_continuation.get('prior_detours') == detours == 56
                and synthesis_continuation.get('additional_consolidated_revision') == 1
                and synthesis_continuation.get('additional_task_attempts') == 1
                and synthesis_continuation.get('reopened_nodes') == ['acquire-p10']
                and synthesis_continuation.get('maximum_passes') == 1
                and synthesis_continuation.get('live_calls_added') == 0
                and program.get('synthesis_continuation') == synthesis_continuation, 'Unreviewed synthesis continuation')
            require(any(r['id'] == 'integration-master-synthesis-continuation-2026-10-19'
                and synthesis_continuation['review'] in r['result_evidence'] for r in history), 'Missing synthesis continuation history')
            verify_refs(root, synthesis_continuation)
            detours += 1
        synthesis_resolution = master.get('synthesis_resolution')
        if synthesis_resolution:
            require(synthesis_resolution.get('profile') == 'integration-synthesis-resolution.v1'
                and synthesis_resolution.get('prior_detours') == detours == 57
                and synthesis_resolution.get('additional_consolidated_revision') == 1
                and synthesis_resolution.get('additional_task_attempts') == 1
                and synthesis_resolution.get('reopened_nodes') == ['acquire-p10','acquire-evidence','acquire-p14','acquire-gatecoin']
                and synthesis_resolution.get('maximum_passes') == 1
                and synthesis_resolution.get('live_calls_added') == 0
                and program.get('synthesis_resolution') == synthesis_resolution, 'Unreviewed synthesis resolution')
            require(any(r['id'] == 'integration-master-synthesis-resolution-2026-10-19'
                and synthesis_resolution['review'] in r['result_evidence'] for r in history), 'Missing synthesis resolution history')
            verify_refs(root, synthesis_resolution)
            detours += 1
        candidate_retry = master.get('candidate_capacity_retry')
        if candidate_retry:
            require(candidate_retry.get('profile') == 'integration-candidate-capacity-retry.v1'
                and candidate_retry.get('prior_detours') == detours == 58
                and candidate_retry.get('additional_consolidated_revision') == 1
                and candidate_retry.get('additional_task_attempts') == 1
                and candidate_retry.get('reopened_nodes') == ['acquire-p10','acquire-evidence','acquire-p14','acquire-gatecoin']
                and candidate_retry.get('live_calls_added') == 0
                and candidate_retry.get('additional_transport_replacements') == 0
                and program.get('candidate_capacity_retry') == candidate_retry, 'Unreviewed candidate capacity retry')
            require(any(r['id'] == 'integration-master-candidate-retry-2026-10-20'
                and candidate_retry['review'] in r['result_evidence'] for r in history), 'Missing candidate retry history')
            verify_refs(root, candidate_retry)
            detours += 1
        common_capacity = master.get('common_capacity')
        if common_capacity:
            require(common_capacity.get('profile') == 'integration-common-capacity.v1'
                and common_capacity.get('prior_detours') == detours == 59
                and common_capacity.get('additional_consolidated_revision') == 1
                and common_capacity.get('live_calls_added') == 0
                and common_capacity.get('additional_transport_replacements') == 0
                and common_capacity.get('attempts_reset') is False
                and program.get('common_capacity') == common_capacity, 'Unreviewed common capacity revision')
            require(any(r['id'] == 'integration-master-common-capacity-2026-10-20'
                and common_capacity['review'] in r['result_evidence'] for r in history), 'Missing common capacity history')
            verify_refs(root, common_capacity)
            detours += 1
        time_continuation = master.get('time_continuation')
        if time_continuation:
            require(time_continuation.get('profile') == 'integration-time-continuation.v1'
                and time_continuation.get('prior_detours') == detours == 60
                and time_continuation.get('additional_consolidated_revision') == 0
                and time_continuation.get('additional_task_attempts') == 0
                and time_continuation.get('live_calls_added') == 0
                and time_continuation.get('additional_transport_replacements') == 0
                and time_continuation.get('attempts_reset') is False
                and time_continuation.get('service_scope_reset') is False
                and program.get('time_continuation') == time_continuation, 'Unreviewed time continuation')
            require(any(r['id'] == 'integration-master-time-continuation-2026-10-21'
                and time_continuation['review'] in r['result_evidence'] for r in history), 'Missing time continuation history')
            verify_refs(root, time_continuation)
        retained_repair = master.get('retained_acquisition_repair')
        if retained_repair:
            require(retained_repair.get('profile') == 'integration-retained-acquisition-repair.v1'
                and retained_repair.get('prior_detours') == detours == 60
                and retained_repair.get('additional_consolidated_revision') == 1
                and retained_repair.get('additional_task_attempts') == 1
                and retained_repair.get('live_calls_added') == 0
                and retained_repair.get('additional_transport_replacements') == 0
                and retained_repair.get('attempts_reset') is False
                and retained_repair.get('service_scope_reset') is False
                and program.get('retained_acquisition_repair') == retained_repair,
                'Unreviewed retained acquisition repair')
            require(any(r['id'] == 'integration-master-retained-acquisition-repair-2026-10-21'
                and retained_repair['review'] in r['result_evidence'] for r in history),
                'Missing retained acquisition repair history')
            verify_refs(root, retained_repair)
            detours += 1
        review_repair = master.get('review_repair')
        if review_repair:
            require(review_repair.get('profile') == 'integration-source-review-repair.v1'
                and review_repair.get('prior_detours') == detours == 61
                and review_repair.get('additional_consolidated_revision') == 1
                and review_repair.get('live_calls_added') == 0
                and review_repair.get('additional_transport_replacements') == 64
                and review_repair.get('attempts_reset') is False
                and review_repair.get('service_scope_reset') is False
                and program.get('review_repair') == review_repair, 'Unreviewed source-review repair')
            require(any(r['id'] == 'integration-master-review-repair-2026-10-21'
                and review_repair['review'] in r['result_evidence'] for r in history),
                'Missing source-review repair history')
            verify_refs(root, review_repair)
            detours += 1
    else:
        master_state = None
    require(mission["current_task"] in tasks, "No current substantive task")
    if history:
        require(mission["current_task"] == history[-1]["next_task"], "Next task differs from the last refresh")
    text_fields(mission, ("next_task_reason",))
    return {"questions": questions, "tasks": tasks, "tools": tool_index,
            "detours_since_advance": detours, "baseline_open_obligations": len(obligation_ids),
            "obligation_decisions": len(decisions), "original_readings": len(reading_ids),
            "original_inventory_dispositions_complete": (all(r['disposition'] != 'unreviewed'
                for r in inventory_rows) if master and master.get('acceptance_revision') else False),
            "detour_exception_used": exception_used,
            "context_exception_used": context_exception_used,
            "integration_exception_used": integration_exception_used,
            "execution": execution.summary() if execution is not None else None,
            "local_completion": local_completion, "remaining_work": remaining_work,
            "context_integration": context_revision, "integration_master": master_state}


def admit(mission, tools, task_id=None, root=ROOT):
    state = validate(mission, tools, root)
    return _admit_validated(mission, state, task_id, root)


def _admit_validated(mission, state, task_id=None, root=ROOT):
    task_id = task_id or mission["current_task"]
    require(task_id in state["tasks"], "Task is not in the reviewed program")
    require(task_id == mission["current_task"], "Refresh the current task before changing work")
    task = state["tasks"][task_id]
    master = state.get('integration_master')
    if task_id == 'product-contribution' and master and master['execution'] == 'WORK_REMAINS' \
            and mission['integration_master'].get('reviewed_reopening'):
        require(all(state['tasks'][dep]['status']=='done' for dep in task['depends_on']),
                'Substantive predecessor result is missing')
        return {'admission':'ADMITTED_MASTER_WORK','task':task,'integration_master':master,
            'exact_questions':[state['questions'][q]['question'] for q in task['questions']],
            'limit':'Only the reviewed master frontier is admitted. The prior failed substantive '
                'result is retained; this grants no model calls, budget or legal acceptance.'}
    require(task["status"] == "ready", "Task is not ready; refresh its evidence/prerequisites first")
    require(all(state["tasks"][dep]["status"] == "done" for dep in task["depends_on"]),
            "Substantive predecessor result is missing")
    successor = mission.get('question_first_successor_admission')
    if successor is not None and task_id == 'product-contribution' and task['resource_bounds']['repair_attempts']:
        record = read(safe_path(root, successor['admission']['path']))
        now = datetime.now(timezone.utc)
        require(datetime.fromisoformat(record['started_utc']) <= now < datetime.fromisoformat(record['expires_utc']),
                'Question-first successor local window expired or not started')
    if task["kind"] == "engineering":
        exception = mission.get("one_time_detour_exception")
        context_exception = mission.get("approved_context_boundary_attempt")
        integration_exception = mission.get("approved_tool_integration_attempt")
        if integration_exception is not None and task_id == INTEGRATION_TASK:
            require(not state["integration_exception_used"] and state["context_exception_used"]
                    and state["detours_since_advance"] == integration_exception["prior_detours"],
                    "Integration attempt already used or predecessor changed")
            now = datetime.now(timezone.utc)
            require(datetime.fromisoformat(integration_exception["started_utc"]) <= now
                    < datetime.fromisoformat(integration_exception["expires_utc"]),
                    "Integration attempt window expired or not started")
        elif context_exception is not None and task_id == context_exception["task_id"]:
            require(not state["context_exception_used"] and state["detour_exception_used"]
                    and state["detours_since_advance"] == context_exception["prior_detours"],
                    "Consolidated repair already used or predecessor changed")
            now = datetime.now(timezone.utc)
            require(datetime.fromisoformat(context_exception["started_utc"]) <= now
                    < datetime.fromisoformat(context_exception["expires_utc"]),
                    "Approved consolidated repair window expired or not started")
        elif exception is not None and task_id == exception["task_id"]:
            require(not state["detour_exception_used"]
                    and state["detours_since_advance"] == exception["prior_detours"],
                    "Detour exception already used or predecessor changed")
            require(datetime.now(timezone.utc) < datetime.fromisoformat(exception["expires_utc"]),
                    "One-time local detour window expired")
        else:
            require(state["detours_since_advance"] < mission["maximum_detours_without_advance"],
                    "Detour allowance exhausted: return to substantive work; renaming does not reset it")
    local = state.get('local_completion')
    return {"admission": "ADMITTED_OFFLINE", "task": task,
            **({'integration_master': state['integration_master']} if state['integration_master'] else {}),
            **({'context_integration': completion_status(state['context_integration'], mission, root,
                 settlement='context-integration-assessment-2026-10-12')}
               if state.get('context_integration') else {}),
            **({'local_completion': completion_status(local, mission, root)}
               if local else {}),
            **({'remaining_work': completion_status(state['remaining_work'], mission, root,
                 settlement='remaining-work-assessment-2026-10-12')}
               if state.get('remaining_work') else {}),
            **({'execution': state['execution']} if state['execution'] is not None else {}),
            "recorded_live_pilot": mission.get('recorded_live_pilot'),
            "exact_questions": [state["questions"][q]["question"] for q in task["questions"]],
            "limit": "Admission checks structure and evidence identity, not legal validity or external permission."}


def completion_status(local, mission, root=ROOT, *, settlement='integration-completion-assessment-2026-10-12'):
    record = read(safe_path(root, local['authorization']['path']))
    settled = any(row['id'] == settlement
                  for row in mission['history'])
    now = datetime.now(timezone.utc)
    window_active = (datetime.fromisoformat(record['started_utc']) <= now <
                     datetime.fromisoformat(record['deadline_utc']))
    return {'revision': local, 'live_calls': 0, 'repair_attempts_reserved': 1,
            'repair_attempts_available': 0 if settled or not window_active else 1,
            'settled': settled, 'window_active': window_active,
            'execution_allowed': window_active and not settled}


def status(mission, tools, root=ROOT):
    state = validate(mission, tools, root)
    return _status_validated(mission, tools, state, root)


def _status_validated(mission, tools, state, root=ROOT):
    selected = [t for t in tools if t["disposition"] == "selected"]
    from scripts.legal_integration_acceptance import evaluation_summary
    evaluations = evaluation_summary(tools, root)
    ready = (all(q["status"] == "review_ready" for q in state["questions"].values())
             and (state['original_inventory_dispositions_complete'] if
                  mission.get('integration_master', {}).get('acceptance_revision') else
                  state["obligation_decisions"] == state["baseline_open_obligations"])
             and evaluations['all_selected_tool_dispositions_complete'])
    return {"mission": "READY_FOR_SUBSTANTIVE_ACCEPTANCE_REVIEW" if ready else "OPEN",
            **({'integration_master': state['integration_master']} if state['integration_master'] else {}),
            'context_integration': (completion_status(state['context_integration'], mission, root,
                                    settlement='context-integration-assessment-2026-10-12')
                                    if state.get('context_integration') else None),
            'local_completion': (completion_status(state['local_completion'], mission, root)
                                 if state.get('local_completion') else None),
            'remaining_work': (completion_status(state['remaining_work'], mission, root,
                                settlement='remaining-work-assessment-2026-10-12')
                               if state.get('remaining_work') else None),
            **({'execution': state['execution']} if state['execution'] is not None else {}),
            "original_obligations_open_in_baseline": state["baseline_open_obligations"],
            "obligation_review_decisions": state["obligation_decisions"],
            "original_readings": state["original_readings"],
            "original_inventory_dispositions_complete": state['original_inventory_dispositions_complete'],
            "questions": {q: row["status"] for q, row in state["questions"].items()},
            "surveyed_tools": len(tools), "selected_tools": len(selected),
            **evaluations,
            "tool_dispositions": {t["id"]: t["disposition"] for t in tools},
            "detours_since_substantive_advance": state["detours_since_advance"],
            "detours_are_lower_bound": not any(r["outcome"] == "substantive_advance"
                                                for r in mission["history"]),
            "next_task": mission["current_task"], "reason": mission["next_task_reason"],
            "question_first_successor": ('CONSUMED' if state['tasks']['product-contribution']['resource_bounds'].get('repair_attempts') == 0
                else 'ONE_LOCAL_ATTEMPT') if mission.get('question_first_successor_admission') else None,
            "live_authorization": (mission['recorded_live_pilot'] if mission.get('recorded_live_pilot')
                else "No renewal; historical ledgers and deadline remain unchanged.")}


def refresh(mission, tools, root=ROOT):
    """Derive both views from one local validation, never a persisted result."""
    state = validate(mission, tools, root)
    current = _status_validated(mission, tools, state, root)
    task = state['tasks'][mission['current_task']]
    master_active = current.get('integration_master', {}).get('execution') == 'WORK_REMAINS'
    admission = (_admit_validated(mission, state, root=root) if task['status'] == 'ready' or
                 (master_active and mission['integration_master'].get('reviewed_reopening')) else
                 {'admitted': False, 'task_id': task['id'], 'reason': task['status']})
    return {'status': current, 'admission': admission,
            'predecessor': mission['history'][-1] if mission['history'] else mission['baseline_evidence'],
            'refresh': 'Validated recorded selection; no task, budget or phase was created.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "status", "admit", "refresh"))
    parser.add_argument("task", nargs="?")
    args = parser.parse_args(argv)
    if args.task and args.action != "admit":
        parser.error("Only admit accepts an optional registered task id")
    try:
        mission = read(ROOT / BASE / "mission.json")
        tools = read(ROOT / BASE / "tools.json")
        if args.action == "admit":
            result = admit(mission, tools, args.task)
        elif args.action == "refresh":
            result = refresh(mission, tools)
        else:
            result = status(mission, tools)
            if args.action == "check":
                result = {"check": "PASS", "mission": result["mission"],
                          "scope": "Recorded mission constraints and evidence hashes only."}
        print(json.dumps(result, indent=2))
        return 0
    except (Refused, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"check": "REFUSED", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
