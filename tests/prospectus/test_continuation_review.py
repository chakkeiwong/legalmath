"""Empty dispatch is not evidence that all authorized substantive work is blocked."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.prospectus_continuation import inspect, review
from legalmath.prospectus.execution_authority import digest, file_hash


@pytest.fixture
def case():
    tasks = [
        {"id": "binding", "handler": "agent", "budget_key": "binding",
         "depends_on": [], "priority": 20},
        {"id": "confinement", "handler": "agent", "budget_key": "confinement",
         "depends_on": ["binding"], "priority": 30},
        {"id": "readings", "handler": "external", "budget_key": "readings",
         "depends_on": [], "priority": 10},
    ]
    program = {"revision": 3, "tasks": tasks,
               "obligations": [{"id": "G", "tasks": ["binding", "confinement"]},
                               {"id": "E", "tasks": ["readings"]}],
               "budgets": {t["budget_key"]: {"maximum_new_attempts": 2} for t in tasks}}
    state = {"program_sha256": digest(program), "event_head": "retained-event",
             "tasks": [{"id": "binding", "state": "RESULT_RECORDED"},
                       {"id": "confinement", "state": "WAITING_DEPENDENCY"},
                       {"id": "readings", "state": "WAITING_EXTERNAL"}],
             "obligations": [{"id": "G", "complete": False}, {"id": "E", "complete": False}],
             "budget_admissions": {"binding": 2, "confinement": 0, "readings": 0},
             "running": [], "next_task": None, "program_complete": False,
             "completion": {"engineering": False, "assisted": False}}
    routes = {"version": "prospectus-continuation-routes.v1", "tasks": []}
    for task in tasks:
        external = task["handler"] == "external"
        routes["tasks"].append({
            "task": task["id"], "task_sha256": digest(task),
            "mode": "external" if external else "local", "phase": 6 if external else 1,
            "remaining": "Actual current product or independent evidence is missing.",
            "next_action": "Review the exact supported product criterion.",
            "acceptance": "Actual source-bound downstream evidence.",
            "external_inputs": ["Genuine unexposed independent readings."] if external else [],
            "stop_condition": "Corrupt comparator or exhausted reviewed experiment.",
        })
    return program, state, routes


def test_empty_queue_requires_review_without_granting_retry(case):
    before = deepcopy(case)
    report = inspect(*case)
    assert report["decision"] == "REVIEW_REQUIRED"
    assert report["local_review_tasks"] == ["binding", "confinement"]
    assert report["partial_at_admission_limit"] == ["binding"]
    assert report["waiting_input_tasks"] == ["readings"]
    assert report["authority_next_task"] is None
    assert report["permission_or_admission_granted"] is False
    assert report["whole_program_stop_supported"] is False
    assert report["routes"][1]["incomplete_predecessors"] == ["binding"]
    assert case == before


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown"])
def test_exact_task_coverage_is_required(case, mutation):
    routes = case[2]["tasks"]
    if mutation == "missing":
        routes.pop()
    elif mutation == "duplicate":
        routes.append(deepcopy(routes[0]))
    else:
        routes[0]["task"] = "invented"
    with pytest.raises(ValueError, match="every task"):
        inspect(*case)


def test_genuine_external_only_work_can_wait_without_completion(case):
    for route in case[2]["tasks"]:
        route.update(mode="evidence", external_inputs=["Exact unavailable source document."])
    result = inspect(*case)
    assert result["decision"] == "WAITING_FOR_INPUT"
    assert result["whole_program_stop_supported"] is True
    assert not result["program_complete"]
    assert not any(result["completion"].values())


def test_changed_external_task_needs_review_even_when_old_map_says_wait(case):
    program, state, routes = case
    for route in routes["tasks"]:
        route.update(mode="evidence", external_inputs=["Original source."])
    program["tasks"][0]["new_condition"] = "A real new substantive case"
    state["program_sha256"] = digest(program)
    result = inspect(*case)
    assert result["decision"] == "REVIEW_REQUIRED"
    assert result["routes"][0]["action"] == "REVIEW_CHANGED_TASK_ROUTE"


def test_undefined_external_blocker_cannot_justify_stop(case):
    case[2]["tasks"][0]["mode"] = "external"
    with pytest.raises(ValueError, match="specific missing input"):
        inspect(*case)


def test_running_work_requires_polling_not_new_work(case):
    state = case[1]
    state["tasks"][0]["state"] = "RUNNING"
    state["running"] = ["binding"]
    result = inspect(*case)
    assert result["decision"] == "RESUME_REQUIRED"
    assert not result["whole_program_stop_supported"]


def test_admitted_work_has_priority_over_refinement(case):
    state = case[1]
    state["tasks"][0]["state"] = "ADMITTED"
    state["next_task"] = "binding"
    assert inspect(*case)["decision"] == "CONTINUE_ADMITTED_WORK"


def test_corrupted_external_evidence_requires_local_review(case):
    for route in case[2]["tasks"]:
        route.update(mode="evidence", external_inputs=["Original source."])
    case[1]["tasks"][2]["state"] = "REPAIR_REQUIRED"
    report = inspect(*case)
    assert report["decision"] == "REVIEW_REQUIRED"
    assert report["local_review_tasks"] == ["readings"]


@pytest.mark.parametrize("mutation", ["program", "obligation", "obligation_missing",
                                     "status_hash", "running", "selection", "over_budget"])
def test_inconsistent_authority_projection_is_refused(case, mutation):
    state = case[1]
    if mutation == "program":
        state["program_complete"] = True
    elif mutation == "obligation":
        state["obligations"][0]["complete"] = True
    elif mutation == "obligation_missing":
        state["obligations"].pop()
    elif mutation == "status_hash":
        state["program_sha256"] = "stale"
    elif mutation == "running":
        state["running"] = ["binding"]
    elif mutation == "selection":
        state["next_task"] = "binding"
    else:
        state["budget_admissions"]["binding"] = 3
    with pytest.raises(ValueError):
        inspect(*case)


def test_all_accepted_obligations_can_complete(case):
    for row in case[1]["tasks"]:
        row["state"] = "COMPLETE"
    for row in case[1]["obligations"]:
        row["complete"] = True
    case[1]["program_complete"] = True
    case[1]["completion"] = {"engineering": True, "assisted": True}
    result = inspect(*case)
    assert result["decision"] == "COMPLETE"
    assert result["whole_program_stop_supported"] is True


@pytest.fixture
def retained_review(case, tmp_path):
    program, state, routes = case
    inspector = Path("scripts/prospectus_continuation.py").resolve()
    copied = tmp_path / "scripts/prospectus_continuation.py"
    copied.parent.mkdir()
    copied.write_bytes(inspector.read_bytes())
    (tmp_path / "plan.md").write_text("Reviewed diagnostic with no native execution.\n")
    (tmp_path / "routes.json").write_text(json.dumps(routes))
    program["continuation_review"] = {
        "version": "prospectus-continuation-review.v1", "plan": "plan.md",
        "routes": "routes.json", "inspector": "scripts/prospectus_continuation.py",
        "bindings": {p: file_hash(tmp_path / p) for p in
                     ["plan.md", "routes.json", "scripts/prospectus_continuation.py"]},
    }
    state["program_sha256"] = digest(program)

    class RetainedAuthority:
        def __init__(self):
            self.event_head = "retained-event"
        def path(self, name):
            return tmp_path / name
        def spec(self):
            return program, {}, []
        def status(self):
            return state
        def events(self):
            return [{"sha256": self.event_head}]
        def __getattr__(self, name):
            pytest.fail("Unexpected mutation/dispatch method: " + name)

    return RetainedAuthority(), tmp_path


def test_review_checks_retained_files_and_does_not_mutate(retained_review):
    authority, folder = retained_review
    before = {str(p): file_hash(p) for p in folder.rglob("*") if p.is_file()}
    result = review(authority)
    assert result["decision"] == "REVIEW_REQUIRED"
    assert {str(p): file_hash(p) for p in folder.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("name", ["plan.md", "routes.json", "scripts/prospectus_continuation.py"])
def test_changed_review_files_are_refused(retained_review, name):
    authority, folder = retained_review
    (folder / name).write_text("changed after review\n")
    with pytest.raises(ValueError, match="changed"):
        review(authority)


def test_advancing_authority_cannot_produce_mixed_report(retained_review, monkeypatch):
    authority, _ = retained_review
    previous = authority.status
    def advancing():
        authority.event_head = "new-event"
        return previous()
    monkeypatch.setattr(authority, "status", advancing)
    with pytest.raises(ValueError, match="advanced"):
        review(authority)
