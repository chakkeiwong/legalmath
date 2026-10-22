"""Read-only continuation review of the existing prospectus authority.

This inspector neither admits tasks nor validates product acceptance. A reviewed
local next action may still require task refinement and a cumulative budget review.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read

MODES = {"local", "mixed", "evidence", "external", "accepted"}
STATES = {"READY", "ADMITTED", "STARTING", "RUNNING", "COMPLETE", "RESULT_RECORDED",
          "REPAIR_REQUIRED", "INVALIDATED", "WAITING_EXTERNAL", "WAITING_DEPENDENCY",
          "WAITING_TRIGGER", "BUDGET_EXHAUSTED"}


def inspect(program, state, routes):
    """Pure projection; no new admission, permission, retry or completion."""
    tasks = {t["id"]: t for t in program["tasks"]}
    rows = {r["id"]: r for r in state["tasks"]}
    mapping = {r["task"]: r for r in routes["tasks"]}
    if (len(tasks) != len(program["tasks"]) or len(rows) != len(state["tasks"])
            or len(mapping) != len(routes["tasks"]) or tasks.keys() != rows.keys()
            or tasks.keys() != mapping.keys()):
        raise ValueError("Continuation map must cover every task exactly once")
    if routes.get("version") != "prospectus-continuation-routes.v1":
        raise ValueError("Unsupported continuation map")
    if state["program_sha256"] != digest(program):
        raise ValueError("Status belongs to a different program")
    obligations = {r["id"]: r for r in program["obligations"]}
    state_obligations = {r["id"]: r for r in state["obligations"]}
    if (len(obligations) != len(program["obligations"])
            or len(state_obligations) != len(state["obligations"])
            or obligations.keys() != state_obligations.keys()):
        raise ValueError("Status omits or duplicates obligations")
    expected_complete = {}
    for key, obligation in obligations.items():
        if not obligation["tasks"] or not set(obligation["tasks"]) <= tasks.keys():
            raise ValueError("Obligation has missing task coverage")
        expected_complete[key] = all(rows[t]["state"] == "COMPLETE" for t in obligation["tasks"])
        if state_obligations[key]["complete"] != expected_complete[key]:
            raise ValueError("Obligation completion contradicts task evidence")
    if state["program_complete"] != (bool(obligations) and all(expected_complete.values())):
        raise ValueError("Program completion contradicts obligation evidence")

    details, local, waiting = [], [], []
    required = {"task_sha256", "mode", "phase", "remaining", "next_action",
                "acceptance", "external_inputs", "stop_condition"}
    for key, task in tasks.items():
        row, route = rows[key], mapping[key]
        if (not required <= route.keys() or route["mode"] not in MODES
                or type(route["phase"]) is not int or not 0 <= route["phase"] <= 6
                or any(not isinstance(route[k], str) or not route[k].strip()
                       for k in ("task_sha256", "remaining", "next_action", "acceptance", "stop_condition"))
                or not isinstance(route["external_inputs"], list)
                or any(not isinstance(v, str) or not v.strip() for v in route["external_inputs"])):
            raise ValueError("Incomplete continuation route: " + key)
        if route["mode"] in {"external", "evidence"} and not route["external_inputs"]:
            raise ValueError("Waiting route must name a specific missing input: " + key)
        if row["state"] not in STATES:
            raise ValueError("Unknown authority state: " + row["state"])
        used = state["budget_admissions"][task["budget_key"]]
        cap = program["budgets"][task["budget_key"]]["maximum_new_attempts"]
        if type(used) is not int or type(cap) is not int or used < 0 or cap < used:
            raise ValueError("Invalid cumulative admission accounting: " + key)
        stale = route["task_sha256"] != digest(task)
        predecessors = [d for d in task["depends_on"] if rows[d]["state"] != "COMPLETE"]
        if row["state"] == "COMPLETE":
            action = "ACCEPTED"
        elif row["state"] in {"RUNNING", "STARTING"}:
            action = "POLL_EXISTING_JOB"
        elif row["state"] in {"READY", "ADMITTED"}:
            action = "FOLLOW_AUTHORITY_ADMISSION"
        elif stale:
            action = "REVIEW_CHANGED_TASK_ROUTE"
        elif row["state"] in {"REPAIR_REQUIRED", "INVALIDATED"}:
            action = "REVIEW_FAILED_OR_CHANGED_EVIDENCE"
        elif route["mode"] in {"local", "mixed", "accepted"}:
            action = "REVIEW_LOCAL_CONTINUATION"
        else:
            action = "WAIT_FOR_SPECIFIC_INPUT"
        detail = {
            "task": key, "state": row["state"], "phase": route["phase"],
            "action": action, "next_action": route["next_action"],
            "remaining": route["remaining"], "acceptance": route["acceptance"],
            "external_inputs": route["external_inputs"], "stop_condition": route["stop_condition"],
            "admissions_used": used, "admission_limit": cap,
            "budget_review_needed_for_new_attempt": used >= cap,
            "incomplete_predecessors": predecessors, "route_requires_refresh": stale,
            "acceptance_implementation": task.get("validator") or
                (task["handler"] if task["handler"] in {"native-cohort", "native-interfaces"} else None),
            "attempt": row.get("attempt"),
        }
        details.append(detail)
        if action.startswith("REVIEW_"):
            local.append(detail)
        elif action == "WAIT_FOR_SPECIFIC_INPUT":
            waiting.append(detail)

    local.sort(key=lambda r: (r["phase"], tasks[r["task"]].get("priority", 100), r["task"]))
    active = [r["task"] for r in details if r["action"] == "POLL_EXISTING_JOB"]
    if set(active) != set(state["running"]):
        raise ValueError("Active jobs disagree with authority state")
    next_task = state["next_task"]
    if next_task is not None and (next_task not in rows or rows[next_task]["state"] not in {"READY", "ADMITTED"}):
        raise ValueError("Invalid authority next-task selection")
    if active:
        decision, next_action = "RESUME_REQUIRED", "Poll or reconcile the existing job; do not duplicate it."
    elif next_task is not None:
        decision, next_action = "CONTINUE_ADMITTED_WORK", mapping[next_task]["next_action"]
    elif state["program_complete"]:
        decision, next_action = "COMPLETE", "Report the scope actually accepted."
    elif local:
        decision, next_action = "REVIEW_REQUIRED", local[0]["next_action"]
    elif waiting and len(waiting) == sum(r["state"] != "COMPLETE" for r in details):
        decision, next_action = "WAITING_FOR_INPUT", "Collect the specific retained inputs; preserve conditional results."
    else:
        decision, next_action = "REVIEW_REQUIRED", "Reconcile uncovered readiness or dependencies before a blocked handoff."
    return {
        "version": "prospectus-continuation-report.v1", "revision": program["revision"],
        "program_sha256": digest(program), "event_head": state["event_head"],
        "obligations": len(obligations), "tasks": len(tasks),
        "state_counts": dict(Counter(r["state"] for r in details)),
        "decision": decision, "next_action": next_action,
        "whole_program_stop_supported": decision in {"COMPLETE", "WAITING_FOR_INPUT"},
        "authority_next_task": next_task, "running": active,
        "local_review_tasks": [r["task"] for r in local],
        "waiting_input_tasks": [r["task"] for r in waiting],
        "partial_at_admission_limit": [r["task"] for r in details
                                     if r["state"] == "RESULT_RECORDED"
                                     and r["budget_review_needed_for_new_attempt"]],
        "unfinished_without_acceptance_implementation": [r["task"] for r in details
            if r["state"] != "COMPLETE" and r["acceptance_implementation"] is None],
        "completion": state["completion"], "program_complete": state["program_complete"],
        "permission_or_admission_granted": False,
        "scope": "Reviewed continuation advice; no product acceptance or agent-lifetime guarantee.",
        "routes": details,
    }


def review(authority):
    program, _, _ = authority.spec()
    spec = program.get("continuation_review")
    if not isinstance(spec, dict) or spec.get("version") != "prospectus-continuation-review.v1":
        raise ValueError("No reviewed continuation map in the active program")
    bindings = spec.get("bindings", {})
    if not {spec.get("plan"), spec.get("routes"), spec.get("inspector")} <= bindings.keys():
        raise ValueError("Continuation plan, map and inspector must be bound")
    if spec["inspector"] != "scripts/prospectus_continuation.py":
        raise ValueError("Unexpected continuation inspector")
    for name, expected in bindings.items():
        if file_hash(authority.path(name)) != expected:
            raise ValueError("Reviewed continuation file changed: " + name)
    before = authority.events()[-1]["sha256"]
    state = authority.status()
    result = inspect(program, state, read(authority.path(spec["routes"])))
    if authority.events()[-1]["sha256"] != before:
        raise ValueError("Authority advanced during review; inspect its new state")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--output", help="New JSON filename inside continuation-reviews/")
    args = parser.parse_args()
    authority = Authority(ROOT)
    result = review(authority)
    if args.output:
        output = authority.path(args.output)
        allowed = authority.base / "continuation-reviews"
        if not output.is_relative_to(allowed) or output == allowed:
            parser.error("--output must be a new file inside the authority continuation-reviews directory")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    if not args.full:
        result = {k: v for k, v in result.items() if k not in {"routes",
            "partial_at_admission_limit", "unfinished_without_acceptance_implementation"}}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
