"""Reproduce ways the legal mission drifted; these are process, not law, tests."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pytest
from scripts import legal_mission_control as control


def test_source_span_configuration_counts_one_more_detour_and_cannot_repeat():
    from scripts import legal_mission_live_pilot as pilot
    mission = control.read(pilot.OUT / 'mission-before.json')
    tools = control.read(ROOT / control.BASE / 'tools.json')
    task = next(t for t in mission['tasks'] if t['id'] == 'product-contribution')
    task['live_method_revision'] = {'id': 'source-spans',
        'plan': pilot.ref(ROOT / 'docs/plans/legal-mission-live-pilot-source-spans.md')}
    row = result(mission, task, 'product-contribution')
    row['result_evidence'].append(task['live_method_revision']['plan'])
    row['bounded_method_revision'] = {'id': 'source-spans', 'prior_detours': 4,
        'enabling_deadline_utc': '2026-10-10T06:35:00+00:00', 'additional_attempts': 1}
    mission['history'].append(row)
    assert control.validate(mission, tools)['detours_since_advance'] == 5
    again = deepcopy(row); again['id'] += '-repeated'
    mission['history'].append(again)
    with pytest.raises(control.Refused, match='repeated source-span'):
        control.validate(mission, tools)


def retained_source_fixture(mission):
    """In-memory historical fixture projection; preserve old source/hash on disk."""
    old_path = 'src/legalmath/interpretation/assurance/complete_investigation.py'
    archive = 'artifacts/legal-mission-control/2026-10-10/context-boundary/before/' + old_path
    expected = hashlib.sha256((ROOT / archive).read_bytes()).hexdigest()
    def visit(value):
        if isinstance(value, dict):
            if value.get('path') == old_path and value.get('sha256') == expected:
                value['path'] = archive
            for item in value.values(): visit(item)
        elif isinstance(value, list):
            for item in value: visit(item)
    visit(mission)
    return mission


@pytest.fixture
def context_records(monkeypatch):
    from datetime import datetime, timezone
    class DuringWindow(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 9, 17, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(control, 'datetime', DuringWindow)
    path = ROOT / 'artifacts/legal-mission-control/2026-10-10/context-boundary/mission-at-admission.json'
    return retained_source_fixture(control.read(path)), control.read(ROOT / control.BASE / 'tools.json')


def test_user_approved_consolidated_attempt_keeps_two_spent_detours(context_records):
    mission, tools = context_records
    assert control.validate(mission, tools)['detours_since_advance'] == 2
    assert mission['maximum_detours_without_advance'] == 1
    assert control.admit(mission, tools)['task']['id'] == control.CONTEXT_TASK


@pytest.mark.parametrize('fault', ['name', 'minutes', 'calls', 'approval', 'expiry', 'prior'])
def test_consolidated_exception_cannot_expand_or_change_approval(context_records, fault):
    mission, tools = context_records
    e = mission['approved_context_boundary_attempt']
    if fault == 'name': e['task_id'] = 'renamed-repair'
    if fault == 'minutes': e['minutes'] = 121
    if fault == 'calls': e['live_calls'] = 1
    if fault == 'approval': e['approval']['sha256'] = '0' * 64
    if fault == 'expiry': e['expires_utc'] = '2027-10-09T18:38:48+00:00'
    if fault == 'prior': e['prior_detours'] = 0
    with pytest.raises(control.Refused): control.admit(mission, tools)


def test_consolidated_result_records_three_and_cannot_repeat(context_records):
    mission, tools = context_records
    task = next(t for t in mission['tasks'] if t['id'] == control.CONTEXT_TASK)
    mission['history'].append(result(mission, task, 'product-contribution'))
    mission['current_task'] = 'product-contribution'
    state = control.validate(mission, tools)
    assert state['detours_since_advance'] == 3 and state['context_exception_used']
    parent = next(t for t in mission['tasks'] if t['id'] == 'product-contribution')
    mission['history'].append(result(mission, parent, control.CONTEXT_TASK))
    mission['current_task'] = control.CONTEXT_TASK
    with pytest.raises(control.Refused, match='already used'): control.admit(mission, tools)


def test_consolidated_window_cannot_renew(context_records, monkeypatch):
    from datetime import datetime, timezone
    class AfterWindow(datetime):
        @classmethod
        def now(cls, tz=None): return cls(2026, 10, 9, 19, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(control, 'datetime', AfterWindow)
    with pytest.raises(control.Refused, match='window expired'): control.admit(*context_records)


@pytest.fixture
def staging_records(monkeypatch):
    from datetime import datetime, timezone
    class DuringWindow(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 9, 11, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(control, 'datetime', DuringWindow)
    # Preserve the exact pre-attempt register even after the task is returned.
    path = ROOT / 'artifacts/legal-mission-control/2026-10-09/answer-staging/mission-at-admission.json'
    return retained_source_fixture(control.read(path)), control.read(ROOT / control.BASE / 'tools.json')


def test_named_exception_keeps_the_spent_detour_and_default_bound(staging_records):
    mission, tools = staging_records
    state = control.validate(mission, tools)
    assert state['detours_since_advance'] == 1
    assert mission['maximum_detours_without_advance'] == 1
    assert control.admit(mission, tools)['task']['id'] == control.STAGING_TASK


@pytest.mark.parametrize('fault', ['name', 'cap', 'minutes', 'review', 'expiry'])
def test_detour_exception_cannot_expand_or_change_identity(staging_records, fault):
    mission, tools = staging_records
    e = mission['one_time_detour_exception']
    if fault == 'name': e['task_id'] = 'another-name'
    if fault == 'cap': mission['maximum_detours_without_advance'] = 2
    if fault == 'minutes': e['minutes'] = 121
    if fault == 'review': e['review']['sha256'] = '0' * 64
    if fault == 'expiry': e['expires_utc'] = '2027-10-09T12:35:00+00:00'
    with pytest.raises(control.Refused):
        control.admit(mission, tools)


def test_used_exception_is_recorded_but_cannot_run_again(staging_records):
    mission, tools = staging_records
    task = next(t for t in mission['tasks'] if t['id'] == control.STAGING_TASK)
    mission['history'].append(result(mission, task, 'product-contribution'))
    mission['current_task'] = 'product-contribution'
    state = control.validate(mission, tools)
    assert state['detours_since_advance'] == 2 and state['detour_exception_used']
    parent = next(t for t in mission['tasks'] if t['id'] == 'product-contribution')
    mission['history'].append(result(mission, parent, control.STAGING_TASK))
    mission['current_task'] = control.STAGING_TASK
    with pytest.raises(control.Refused, match='already used'):
        control.admit(mission, tools)


def test_expired_exception_does_not_renew_on_restart(staging_records, monkeypatch):
    from datetime import datetime, timezone
    class AfterWindow(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 9, 13, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(control, 'datetime', AfterWindow)
    with pytest.raises(control.Refused, match='window expired'):
        control.admit(*staging_records)


@pytest.fixture
def records():
    # Transition scenarios start at the preserved setup, not mutable live state.
    baseline = ROOT / "artifacts/legal-mission-control/2026-10-09/continuation/setup-source"
    mission = control.read(baseline / control.BASE / "mission.json")
    tools = control.read(baseline / control.BASE / "tools.json")
    # Historical snapshots still reference the editable old adapter. Project
    # only those exact bytes to their retained copy in this in-memory fixture.
    old = 'scripts/legal_integration_tools.py'
    kept = 'artifacts/legal-mission-control/2026-10-10/tool-integration/before/' + old
    expected = hashlib.sha256((ROOT / kept).read_bytes()).hexdigest()
    def visit(value):
        if isinstance(value, dict):
            if value.get('path') == old and value.get('sha256') == expected:
                value['path'] = kept
            for item in value.values(): visit(item)
        elif isinstance(value, list):
            for item in value: visit(item)
    visit(mission); visit(tools)
    # This historical setup recorded code evidence at editable paths. Project
    # identical pre-repair bytes into memory, without rewriting any snapshot.
    snapshots = control.read(ROOT / 'artifacts/legal-mission-control/2026-10-11/route-repair/source-before.json')
    retained = {(r['original_path'], r['retained']['sha256']): r['retained']['path'] for r in snapshots}
    def project(value):
        if isinstance(value, dict):
            key=(value.get('path'),value.get('sha256'))
            if key in retained:value['path']=retained[key]
            for child in value.values():project(child)
        elif isinstance(value,list):
            for child in value:project(child)
    project(mission);project(tools)
    return mission, tools


def test_integration_revision_preserves_prior_attempts_and_expires(monkeypatch):
    from datetime import datetime, timezone
    mission = control.read(ROOT / 'artifacts/legal-mission-control/2026-10-10/tool-integration/mission-at-admission.json')
    tools = control.read(ROOT / control.BASE / 'tools.json')
    class During(datetime):
        @classmethod
        def now(cls, tz=None): return cls(2026,10,9,20,0,tzinfo=timezone.utc)
    monkeypatch.setattr(control,'datetime',During)
    # Preserve pre-edit CompleteInvestigation evidence in memory.
    retained_source_fixture(mission)
    state = control.validate(mission,tools)
    assert state['detours_since_advance']==3 and not state['integration_exception_used']
    assert control.admit(mission,tools)['task']['id']==control.INTEGRATION_TASK
    e=mission['approved_tool_integration_attempt']
    e['expires_utc']='2027-10-09T21:56:51+00:00'
    with pytest.raises(control.Refused):control.admit(mission,tools)


def engineering(mission, tid):
    task = deepcopy(mission["tasks"][0])
    task.update(id=tid, kind="engineering", status="ready", blocked_task="p10-standard",
                return_to="p10-standard", blocker_evidence=task["baseline_evidence"])
    task["resource_bounds"]["repair_attempts"] = 1
    mission["tasks"].append(task)
    return task


def result(mission, task, next_task, outcome="no_advance"):
    return {"id": f"result-{len(mission['history'])}", "task_id": task["id"],
            "kind": task["kind"], "outcome": outcome, "result_evidence": task["baseline_evidence"],
            "decision": "Simulated process-control result; no new legal finding.",
            "next_task": next_task, "next_task_reason": "Return to the original legal question."}


def test_question_first_successor_is_one_spent_local_attempt(monkeypatch):
    from datetime import datetime, timezone
    mission = control.read(ROOT / 'artifacts/legal-mission-control/2026-10-11/question-first-successor/mission-at-admission.json')
    tools = control.read(ROOT / control.BASE / 'tools.json')
    class During(datetime):
        @classmethod
        def now(cls, tz=None): return cls(2026, 10, 11, 11, 45, tzinfo=timezone.utc)
    monkeypatch.setattr(control, 'datetime', During)
    assert control.validate(mission,tools)['detours_since_advance']==9
    assert control.admit(mission,tools)['task']['resource_bounds']=={'live_calls':0,'minutes':120,'repair_attempts':1}
    task=next(t for t in mission['tasks'] if t['id']=='product-contribution')
    row=result(mission,task,'product-contribution')
    row['bounded_method_revision']=mission['question_first_successor_admission']['revision']
    mission['history'].append(row)
    task['resource_bounds']['repair_attempts']=0
    assert control.validate(mission,tools)['detours_since_advance']==9
    again=deepcopy(row);again['id']='repeated-question-first-successor'
    mission['history'].append(again)
    with pytest.raises(control.Refused,match='repeated question-first successor'):
        control.validate(mission,tools)


def test_question_first_successor_expires_without_live_allowance(monkeypatch):
    from datetime import datetime, timezone
    mission = control.read(ROOT / 'artifacts/legal-mission-control/2026-10-11/question-first-successor/mission-at-admission.json')
    tools = control.read(ROOT / control.BASE / 'tools.json')
    class After(datetime):
        @classmethod
        def now(cls, tz=None): return cls(2026, 10, 11, 13, 33, tzinfo=timezone.utc)
    monkeypatch.setattr(control, 'datetime', After)
    with pytest.raises(control.Refused,match='local window expired'):control.admit(mission,tools)
    mission['question_first_successor_admission']['admission']['sha256']='0'*64
    with pytest.raises(control.Refused):control.validate(mission,tools)


def simulated_advance(mission, next_task):
    """Hypothetical source result for transition testing, never written to the mission."""
    task = mission["tasks"][0]
    row = result(mission, task, next_task, "substantive_advance")
    row["advance"] = {
        "answer_before": "Hypothetical unresolved source premise.",
        "answer_after": "Hypothetical newly supported conditional relation.",
        "inference": "Test fixture only; no real legal advance is asserted.",
        "contrary": "Retained competing interpretation.",
        "remaining_dependency": "Actual facts still absent.", "evidence_kind": "source_argument",
        "primary_evidence": task["baseline_evidence"], "obligation_ids": task["original_obligation_ids"]}
    mission["history"].append(row)


def test_real_register_admits_the_hard_question_and_keeps_mission_open(records):
    mission, tools = records
    report = control.status(mission, tools)
    assert report["mission"] == "OPEN"
    assert report["original_obligations_open_in_baseline"] == 46
    assert report["original_readings"] == 35
    assert report["selected_tools_fully_evaluated"] == 0
    assert report["surveyed_tools"] == 26
    assert report["detours_since_substantive_advance"] == 1
    assert report["detours_are_lower_bound"]
    admitted = control.admit(mission, tools)
    assert admitted["task"]["id"] == "p10-standard"
    assert admitted["task"]["kind"] == "source_analysis"
    assert admitted["task"]["resource_bounds"]["live_calls"] == 0


def test_rewritten_question_is_rejected_even_with_same_id(records):
    mission, tools = records
    mission["questions"][0]["question"] = "Has the duty been activated?"
    with pytest.raises(control.Refused, match="Original question changed"):
        control.admit(mission, tools)


def test_trigger_answer_cannot_impersonate_fulfillment(records):
    mission, tools = records
    mission["tasks"][0]["answer_targets"]["p10"] = "duty_trigger"
    with pytest.raises(control.Refused, match="substitutes another answer target"):
        control.admit(mission, tools)


@pytest.mark.parametrize("field", ["original_obligation_ids", "original_reading_ids"])
def test_new_denominator_cannot_hide_original_work(records, field):
    mission, tools = records
    mission[field].pop()
    with pytest.raises(control.Refused, match="Original denominator changed"):
        control.validate(mission, tools)


def test_changed_baseline_is_not_resealed_from_mutable_registry(records, tmp_path):
    mission, tools = records
    path, _ = control.ANCHORS["questions"]
    target = tmp_path / path
    target.parent.mkdir(parents=True)
    rewritten = deepcopy(mission["questions"])
    rewritten[0]["question"] = "Has a request occurred?"
    target.write_text(json.dumps(rewritten))
    mission["questions"] = rewritten
    with pytest.raises(control.Refused, match="Changed evidence"):
        control.validate(mission, tools, root=tmp_path)


def test_finished_repair_does_not_finish_mission(records):
    mission, tools = records
    task = engineering(mission, "repair-a")
    simulated_advance(mission, task["id"])
    task["status"] = "done"
    mission["history"].append(result(mission, task, "p10-standard"))
    report = control.status(mission, tools)
    assert report["mission"] == "OPEN"
    assert report["detours_since_substantive_advance"] == 1
    mission["mission_acceptance"] = "complete"
    with pytest.raises(control.Refused, match="cannot certify mission completion"):
        control.validate(mission, tools)


def test_completed_task_needs_actual_result_and_refresh(records):
    mission, tools = records
    mission["tasks"][0]["status"] = "done"
    with pytest.raises(control.Refused, match="completion lacks a result"):
        control.validate(mission, tools)


def test_survey_tool_cannot_disappear(records):
    mission, tools = records
    tools[:] = [t for t in tools if t["id"] != "logical-english"]
    with pytest.raises(control.Refused, match="Surveyed tool omitted"):
        control.validate(mission, tools)


def test_invocations_are_insufficient_for_full_integration(records):
    mission, tools = records
    tools[0]["fully_integrated"] = True
    with pytest.raises(control.Refused, match="acceptance is incomplete"):
        control.validate(mission, tools)


def test_scripted_full_workflow_does_not_prove_live_contribution(records):
    mission, tools = records
    tool = tools[0]
    tool["fully_integrated"] = True
    tool["stages"] = {name: {"level": "controlled", "evidence": tool["evidence"]}
                      for name in control.STAGES}
    with pytest.raises(control.Refused, match="scripted workflow"):
        control.validate(mission, tools)


def test_deferred_is_not_integrated(records):
    mission, tools = records
    next(t for t in tools if t["id"] == "sara-ie")["fully_integrated"] = True
    with pytest.raises(control.Refused, match="Deferred is not integrated"):
        control.validate(mission, tools)


def test_plain_pass_is_not_evidence(records):
    mission, tools = records
    tools[0]["evidence"] = ["PASS: all tools integrated"]
    with pytest.raises(control.Refused, match="file/hash references"):
        control.validate(mission, tools)


def test_first_reproduced_detour_allowed_but_renaming_and_no_advance_do_not_reset(records):
    mission, tools = records
    first = engineering(mission, "repair-a")
    simulated_advance(mission, first["id"])
    mission["current_task"] = first["id"]
    assert control.admit(mission, tools)["admission"] == "ADMITTED_OFFLINE"
    first["status"] = "done"
    mission["history"].append(result(mission, first, "p10-standard"))
    second = engineering(mission, "repair-b-in-a-new-directory")
    mission["history"].append(result(mission, mission["tasks"][0], second["id"]))
    mission["current_task"] = second["id"]
    with pytest.raises(control.Refused, match="Detour allowance exhausted"):
        control.admit(mission, tools)


def test_repair_cannot_reset_detours_by_calling_itself_substantive(records):
    mission, tools = records
    task = engineering(mission, "repair-a")
    mission["history"].append(result(mission, task, "p10-standard", "substantive_advance"))
    with pytest.raises(control.Refused, match="engineering repair cannot itself reset"):
        control.validate(mission, tools)


def test_new_control_does_not_grant_a_fresh_engineering_attempt(records):
    mission, tools = records
    task = engineering(mission, "new-control-repair")
    mission["current_task"] = task["id"]
    with pytest.raises(control.Refused, match="Detour allowance exhausted"):
        control.admit(mission, tools)
    mission["inherited_detour_floor"] = 0
    with pytest.raises(control.Refused, match="cannot disappear on restart"):
        control.validate(mission, tools)


def test_selected_tool_cannot_be_relabelled_to_hide_an_integration_gap(records):
    mission, tools = records
    tools[0]["disposition"] = "deferred"
    with pytest.raises(control.Refused, match="silently deferred"):
        control.validate(mission, tools)


def test_test_count_is_not_a_substantive_advance(records):
    mission, tools = records
    row = result(mission, mission["tasks"][0], "p10-standard", "substantive_advance")
    row["advance"] = {"answer_before": "353 tests", "answer_after": "400 tests",
                      "inference": "More tests passed.", "contrary": "Missing standard.",
                      "remaining_dependency": "Legal meaning.", "evidence_kind": "test_count"}
    mission["history"].append(row)
    with pytest.raises(control.Refused, match="Tests/counts alone"):
        control.validate(mission, tools)


def test_missing_client_facts_do_not_halt_source_research(records):
    mission, tools = records
    task = mission["tasks"][0]
    task.update(status="blocked", blocker_kind="client_facts")
    with pytest.raises(control.Refused, match="do not block conditional source analysis"):
        control.validate(mission, tools)


def test_real_source_block_allows_independent_substantive_work(records):
    mission, tools = records
    task = mission["tasks"][0]
    task.update(status="blocked", blocker_kind="authority_source",
                blocker_scope="Named external authority unavailable for this inference.",
                blocker_evidence=task["baseline_evidence"])
    mission["current_task"] = "p14-attachment"
    mission["next_task_reason"] = "Investigate the independent attachment dispute while the named authority is absent."
    assert control.admit(mission, tools)["task"]["id"] == "p14-attachment"


def test_cannot_launch_product_comparison_or_switch_without_refresh(records):
    mission, tools = records
    with pytest.raises(control.Refused, match="Refresh the current task"):
        control.admit(mission, tools, "product-contribution")
    mission["current_task"] = "product-contribution"
    with pytest.raises(control.Refused, match="Task is not ready"):
        control.admit(mission, tools)


def test_source_tasks_do_not_renew_live_grants(records):
    mission, tools = records
    mission["tasks"][0]["resource_bounds"]["live_calls"] = 200
    with pytest.raises(control.Refused, match="bounded offline work only"):
        control.admit(mission, tools)


def test_stale_evidence_and_worktree_escapes_are_rejected(records):
    mission, tools = records
    tools[0]["evidence"][0]["sha256"] = "0" * 64
    with pytest.raises(control.Refused, match="Changed evidence"):
        control.validate(mission, tools)
    with pytest.raises(control.Refused, match="worktree-relative"):
        control.verify_ref(ROOT, {"path": "/tmp/anything", "sha256": "0" * 64})


def test_refresh_is_read_only_and_exposes_next_substantive_task(capsys, records, monkeypatch):
    paths = [ROOT / control.BASE / name for name in ("mission.json", "tools.json")]
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    original_read = control.read
    monkeypatch.setattr(control, 'read', lambda p: deepcopy(records[0]) if p == paths[0]
                        else deepcopy(records[1]) if p == paths[1] else original_read(p))
    assert control.main(["refresh"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"]["mission"] == "OPEN"
    assert output["admission"]["task"]["id"] == "p10-standard"
    assert before == [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]


def test_cli_has_no_execute_shell_or_budget_override():
    for args in (["execute"], ["admit", "--budget", "200"], ["check", "anything"]):
        with pytest.raises(SystemExit) as error:
            control.main(args)
        assert error.value.code == 2
