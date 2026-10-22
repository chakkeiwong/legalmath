"""Acceptance and recovery failures that must not become prospectus completion."""
from copy import deepcopy
import fcntl
import os
from pathlib import Path

import pytest

from legalmath.prospectus.execution_authority import (
    Authority, CODE, REL, digest, file_hash, process_identity, read, write,
)
from legalmath.prospectus import execution_workers


@pytest.fixture
def authority(tmp_path, monkeypatch):
    for name in CODE:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# fixed method\n")
    (tmp_path / "source.txt").write_text("Source qualifier: no investor reliance\n")
    (tmp_path / "dossier.md").write_text("Read source; test qualifier preservation and actual consumer\n")
    monkeypatch.setattr("legalmath.prospectus.execution_authority.subprocess.check_output", lambda *a, **k: "fixture-commit\n")
    a = Authority(tmp_path)
    inventory = [{"id": "G01", "origin": {"sha256": file_hash(tmp_path / "source.txt")}, "scope": "engineering"},
                 {"id": "E02", "origin": {"sha256": file_hash(tmp_path / "source.txt")}, "scope": "assisted"}]
    tasks = [{"id": "source", "title": "Actual source consumer", "handler": "agent", "depends_on": [],
              "obligations": ["G01"], "inputs": ["source.txt"], "dossier": "dossier.md", "priority": 10,
              "acceptance": "Actual downstream evidence", "budget_key": "source", "timeout_seconds": 10,
              "reason": "Substantive work remains despite validation PASS", "stream": "engineering"},
             {"id": "readers", "title": "Genuine independent readings", "handler": "external", "depends_on": [],
              "obligations": ["E02"], "inputs": ["source.txt"], "dossier": "dossier.md",
              "acceptance": "Unexposed genuine readings", "budget_key": "readers", "timeout_seconds": 10,
              "reason": "Real independent evidence needed", "external_input": "Qualified readers", "stream": "assisted"}]
    program = {"version": "prospectus-authority.v1", "revision": 1, "plan": "dossier.md",
               "inventory_sha256": digest(inventory), "baseline_files": {},
               "obligations": [{**i, "tasks": [t["id"]], "budget_keys": [t["budget_key"]]} for i, t in zip(inventory, tasks)],
               "tasks": tasks, "budgets": {t["id"]: {"maximum_new_attempts": 2} for t in tasks}}
    write(a.base / "baseline/inventory.json", inventory)
    write(a.base / "revisions/0001.json", program)
    write(a.base / "program.json", program)
    with a.lock():
        a.append("REVISION", revision=1, program_sha256=digest(program))
    return a


def propose(a, mutate):
    p = deepcopy(a.spec()[0])
    baseline = digest(p)
    p["revision"] += 1
    mutate(p)
    write(a.root / "proposal.json", p)
    write(a.root / "review.json", {"baseline": baseline, "changes": "Focused repair",
          "skeptical_audit": "Preserve scope and baseline", "evidence_contract": "Same substantive downstream criterion",
          "scope_unchanged": True, "budget_unchanged": True})
    return a.revise("proposal.json", "review.json")


def result_files(a, admission, **values):
    attempt = a.path(admission["attempt"])
    write(attempt / "result.json", {"status": "PASS", "task": admission["task"], **values})
    write(attempt / "outputs.json", {p.name: file_hash(p) for p in attempt.iterdir() if p.is_file() and p.name != "outputs.json"})
    return attempt


def verified_fixture(a, monkeypatch):
    admitted = a.admit()
    result_files(a, admitted)
    # Models an independently recomputing domain validator for state-machine
    # tests; real cohort/callback validators are exercised in the cutover run.
    monkeypatch.setattr(execution_workers, "validate", lambda *args: True)
    a.record(admitted["attempt"])
    return admitted


def test_passing_validation_receipts_do_not_close_missing_work(authority):
    write(authority.base / "old-validation.json", {"R" + str(i): "PASS" for i in range(9)})
    state = authority.status()
    assert not state["program_complete"]
    assert state["next_task"] == "source"
    assert state["tasks"][1]["state"] == "WAITING_EXTERNAL"


def test_current_build_contract_cannot_silently_drop_requirements(authority):
    with pytest.raises(ValueError, match='Delivery scope change'):
        propose(authority, lambda p: p.update(build_contract={'authorization': {'path': 'dossier.md'}}))


def test_arbitrary_pass_record_does_not_establish_substantive_completion(authority):
    admitted = authority.admit()
    result_files(authority, admitted, done=True, independent=True, all_tests_pass=True)
    state = authority.record(admitted["attempt"])
    assert state["tasks"][0]["state"] == "RESULT_RECORDED"
    assert not state["completion"]["engineering"]


def test_verified_engineering_can_finish_while_human_acceptance_waits(authority, monkeypatch):
    verified_fixture(authority, monkeypatch)
    state = authority.status()
    assert state["completion"]["engineering"]
    assert not state["completion"]["assisted"]
    assert not state["program_complete"]


@pytest.mark.parametrize('change', ['none', 'source', 'method', 'output', 'criterion'])
def test_scoped_proof_is_current_bound_and_never_original_acceptance(authority, monkeypatch, change):
    from legalmath.prospectus import build_contract
    monkeypatch.setitem(build_contract.VALIDATORS, 'pension-rounding.v1', ('source', 'pension-rounding'))
    monkeypatch.setattr(build_contract, 'validate_submission', lambda *_a: ['pension-rounding'])
    def revision(alter):
        p = deepcopy(authority.spec()[0])
        before = digest(p)
        p['revision'] += 1
        alter(p)
        write(authority.root / 'proposal.json', p)
        # Every review is immutable after it enters history.
        review_name = 'scope-review-' + str(p['revision']) + '.json'
        write(authority.root / review_name, {'baseline': before, 'changes': 'Bound conditional component',
            'skeptical_audit': 'No original completion; require all original requirements',
            'evidence_contract': 'State machine only; domain validator tested separately',
            'scope_unchanged': True, 'budget_unchanged': True, 'delivery_scope_changed': True,
            'delivery_authorization': p['build_contract']['authorization'], 'original_obligations_preserved': True})
        return authority.revise('proposal.json', review_name)
    def setup(p):
        original = deepcopy(p['tasks'][1])
        for name in build_contract.DEFERRED:
            p['tasks'].append({**deepcopy(original), 'id': name, 'repair_of': 'readers'})
            p['obligations'][1]['tasks'].append(name)
        p['build_contract'] = {'version': 'general-build.v2',
            'authorization': {'path': 'dossier.md', 'sha256': file_hash(authority.root / 'dossier.md')},
            'required_tasks': ['source', 'readers'], 'deferred_tasks': dict(build_contract.DEFERRED),
            'real_case': 'AFTER_GENERAL_BUILD', 'external_opinion_required': False, 'cdm_receiver': None,
            'portability': 'DEFERRED', 'claim': 'CONDITIONAL_CORRECTNESS_IN_DECLARED_SUPPORTED_DOMAIN',
            'criteria': {'source': [
                {'id': 'pension-rounding', 'basis': 'NAMED_CONDITIONAL_CHECK', 'validator': 'pension-rounding.v1', 'description': 'Arithmetic component'},
                {'id': 'remaining-reference-coverage', 'basis': 'ORIGINAL_TASK_ACCEPTANCE', 'validator': None, 'description': 'All original requirements'}]}}
    revision(setup)
    admitted = authority.admit()
    attempt = result_files(authority, admitted)
    state = authority.record(admitted['attempt'])
    assert state['tasks'][0]['state'] == 'RESULT_RECORDED'
    assert len(state['current_build']['verified_criteria']) == 1
    assert state['completion']['engineering'] is False and state['current_build']['complete'] is False
    if change in ('source', 'method'):
        (authority.root / ('source.txt' if change == 'source' else CODE[0])).write_text('changed\n')
    elif change == 'output':
        write(attempt / 'result.json', {'status': 'PASS', 'tampered': True})
    elif change == 'criterion':
        revision(lambda p: p['build_contract']['criteria']['source'][0].update(description='Changed proof obligation'))
    assert len(authority.status()['current_build']['verified_criteria']) == (1 if change == 'none' else 0)


@pytest.mark.parametrize("mutation", ["source", "method", "dossier"])
def test_stale_success_is_not_current_and_changed_work_can_resume(authority, monkeypatch, mutation):
    verified_fixture(authority, monkeypatch)
    name = {"source": "source.txt", "method": CODE[0], "dossier": "dossier.md"}[mutation]
    (authority.root / name).write_text("changed\n")
    state = authority.status()
    assert not state["program_complete"]
    assert state["next_task"] == "source"
    assert not state["completion"]["engineering"]


def test_corrupt_success_does_not_authorize_unchanged_retry(authority, monkeypatch):
    admitted = verified_fixture(authority, monkeypatch)
    write(authority.path(admitted["attempt"]) / "result.json", {"status": "PASS", "forged": True})
    assert authority.status()["tasks"][0]["state"] == "REPAIR_REQUIRED"
    assert authority.status()["next_task"] is None


def test_admission_tampering_refused(authority):
    admitted = authority.admit()
    path = authority.path(admitted["attempt"]) / "admission.json"
    changed = read(path)
    changed["task_spec"]["handler"] = "native-cohort"
    write(path, changed)
    with pytest.raises(ValueError, match="Admission changed"):
        authority.admit()


@pytest.mark.parametrize("case", ["deleted", "empty", "scope", "origin"])
def test_obligation_loss_refuses_revision(authority, case):
    def mutate(program):
        if case == "deleted":
            program["obligations"].pop()
        elif case == "empty":
            program["obligations"][0]["tasks"] = []
        else:
            program["obligations"][0][case] = "changed"
    with pytest.raises((ValueError, TypeError)):
        propose(authority, mutate)


def test_refresh_idempotent_and_projection_recoverable(authority):
    state = authority.refresh()
    count = len(authority.events())
    assert authority.refresh() == state
    assert len(authority.events()) == count
    (authority.base / "state.json").unlink()
    # Rebuild can add a retained refresh reason; task/obligation decisions agree.
    rebuilt = authority.refresh()
    assert rebuilt["tasks"] == state["tasks"]
    assert rebuilt["obligations"] == state["obligations"]


def test_event_history_tampering_refused(authority):
    path = authority.base / "history/000001.json"
    event = read(path)
    event["program_sha256"] = "forged"
    write(path, event)
    with pytest.raises(ValueError, match="event history"):
        authority.status()


def test_unchanged_failure_refused_but_changed_repair_admitted(authority):
    admitted = authority.admit()
    result_files(authority, admitted, status="FAIL")
    authority.record(admitted["attempt"])
    with pytest.raises(ValueError, match="next admitted"):
        authority.admit()
    (authority.root / "source.txt").write_text("Reviewed changed source\n")
    assert authority.admit()["attempt"].endswith("attempt-002")


def test_renamed_repair_shares_failure_trigger_and_budget(authority):
    admitted = authority.admit()
    result_files(authority, admitted, status="FAIL")
    authority.record(admitted["attempt"])
    def mutate(p):
        repair = deepcopy(p["tasks"][0])
        repair.update(id="source-repair", repair_of="source", reason="Changed failing boundary")
        p["tasks"].append(repair)
        p["obligations"][0]["tasks"].append("source-repair")
    state = propose(authority, mutate)
    assert state["next_task"] == "source-repair"
    second = authority.admit()
    assert authority.status()["budget_admissions"]["source"] == 2
    result_files(authority, second, status="FAIL")
    authority.record(second["attempt"])
    (authority.root / "source.txt").write_text("Another change\n")
    assert authority.status()["next_task"] is None


def test_budget_increase_refused_without_separate_authorization(authority):
    with pytest.raises(ValueError, match="Scope/budget"):
        propose(authority, lambda p: p["budgets"]["source"].update(maximum_new_attempts=99))


def test_cycle_and_unknown_dependency_refused(authority):
    with pytest.raises(ValueError, match="cycle"):
        propose(authority, lambda p: p["tasks"][0].update(depends_on=["source"]))


def test_running_process_is_not_redispatched(authority, monkeypatch):
    propose(authority, lambda p: p["tasks"][0].update(handler="native-cohort"))
    calls = []
    class Child:
        pid = os.getpid()
    monkeypatch.setattr("legalmath.prospectus.execution_authority.subprocess.Popen", lambda *a, **k: calls.append(a) or Child())
    assert authority.run()["execution"] == "RUNNING"
    with pytest.raises(ValueError, match="next admitted"):
        authority.run()
    assert authority.resume()["running"] == ["source"]
    assert len(calls) == 1


def test_dead_worker_is_interrupted_without_duplicate_launch(authority):
    admitted = authority.admit()
    identity = {"pid": 999999999, "start_ticks": "1", "boot_id": "absent"}
    write(authority.path(admitted["attempt"]) / "job.json", {"identity": identity})
    with authority.lock():
        authority.append("START", task="source", attempt=admitted["attempt"], identity=identity)
    state = authority.resume()
    assert state["tasks"][0]["state"] == "REPAIR_REQUIRED"
    assert state["next_task"] is None


def test_finished_output_recovered_after_worker_exit(authority, monkeypatch):
    admitted = authority.admit()
    result_files(authority, admitted)
    monkeypatch.setattr(execution_workers, "validate", lambda *args: True)
    assert authority.resume()["tasks"][0]["state"] == "COMPLETE"


def test_writer_lock_excludes_second_dispatcher(authority):
    with authority.lock():
        with pytest.raises(BlockingIOError):
            authority.admit()


def test_path_escape_refused(authority):
    with pytest.raises(ValueError, match="escapes"):
        authority.path("../../outside.json")


def test_process_identity_distinguishes_pid_reuse():
    identity = process_identity(os.getpid())
    assert identity and identity["start_ticks"] and identity["boot_id"]
    assert identity != {**identity, "start_ticks": "0"}


def test_changed_running_program_cannot_accept_old_result(authority, monkeypatch):
    admitted = authority.admit()
    result_files(authority, admitted)
    propose(authority, lambda p: p["tasks"][1].update(reason="Clarified human input"))
    monkeypatch.setattr(execution_workers, "validate", lambda *args: True)
    assert authority.record(admitted["attempt"])["tasks"][0]["state"] == "REPAIR_REQUIRED"


def test_successful_named_repair_satisfies_original_criterion(authority, monkeypatch):
    admitted = authority.admit()
    result_files(authority, admitted, status="FAIL")
    authority.record(admitted["attempt"])
    def mutate(p):
        repair = deepcopy(p["tasks"][0])
        repair.update(id="source-repair", repair_of="source", reason="Changed failing boundary")
        p["tasks"].append(repair)
        p["obligations"][0]["tasks"].append("source-repair")
    propose(authority, mutate)
    second = authority.admit()
    result_files(authority, second)
    monkeypatch.setattr(execution_workers, "validate", lambda *args: True)
    state = authority.record(second["attempt"])
    assert state["tasks"][0]["satisfied_by"] == "source-repair"
    assert state["completion"]["engineering"]


def test_launch_crash_before_process_registration_is_retained(authority):
    admitted = authority.admit()
    with authority.lock():
        authority.append("LAUNCH", task="source", attempt=admitted["attempt"], argv=[])
    assert authority.resume()["tasks"][0]["state"] == "REPAIR_REQUIRED"


def test_partial_history_write_is_not_an_accepted_event(authority):
    (authority.base / "history/000002.json.1.pending").write_text('{"partial":')
    assert authority.status()["next_task"] == "source"


def test_missing_external_requirement_blocks_check(authority):
    program = deepcopy(authority.spec()[0])
    program["obligations"] = [r for r in program["obligations"] if not r["id"].startswith("E")]
    with pytest.raises(ValueError, match="Missing or invented"):
        authority.validate_program(program)


def test_attempt_lease_survives_different_pid_namespace(authority):
    admitted = authority.admit()
    attempt = authority.path(admitted["attempt"])
    foreign = {"pid": 999999999, "start_ticks": "1", "boot_id": "same-host", "pid_namespace": "other"}
    with (attempt / "worker.lock").open("a") as lease:
        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert authority.worker_alive(attempt, foreign)
    assert not authority.worker_alive(attempt, foreign)


def test_human_acceptance_cannot_be_replaced_by_automatic_handler(authority):
    with pytest.raises(ValueError, match="cannot become an automatic"):
        propose(authority, lambda p: p["tasks"][1].update(handler="native-cohort"))


def test_ordinary_revision_cannot_move_automatic_task_into_assisted_scope(authority):
    with pytest.raises(ValueError, match="reclassify"):
        propose(authority, lambda p: p["tasks"][0].update(stream="assisted"))


def test_explicit_budget_extension_retains_used_admissions(authority):
    admitted = authority.admit()
    result_files(authority, admitted, status="FAIL")
    authority.record(admitted["attempt"])
    old = authority.spec()[0]
    new = deepcopy(old)
    new["revision"] += 1
    new["budgets"]["source"]["maximum_new_attempts"] += 1
    write(authority.root / "proposal.json", new)
    review = {"baseline": digest(old), "changes": "One located API repair",
              "skeptical_audit": "Same source baseline and criterion", "evidence_contract": "Actual downstream evidence",
              "scope_unchanged": True, "budget_unchanged": False,
              "budget_revision": {"budget_key": "source", "previous_maximum": 2, "new_maximum": 3,
                  "retained_attempts": [admitted["attempt"]], "reason": "Located UTF-8 versus JSON hash mismatch",
                  "next_discriminating_check": "Use the original retained byte convention",
                  "stop_condition": "No further extension under this review",
                  "same_scope_authorization": "Authorized local implementation repair"}}
    write(authority.root / "review.json", review)
    state = authority.revise("proposal.json", "review.json")
    assert state["budget_admissions"]["source"] == 1
    assert authority.spec()[0]["budgets"]["source"]["maximum_new_attempts"] == 3


def test_reviewed_partial_followup_reuses_original_budget(authority):
    first = authority.admit()
    result_files(authority, first, task_complete=False)
    authority.record(first["attempt"])
    assert authority.status()["next_task"] is None
    state = propose(authority, lambda p: p["tasks"][0].update(reason="Reviewed next bounded source package"))
    assert state["next_task"] == "source"
    second = authority.admit()
    assert second["attempt"].endswith("attempt-002")
    assert authority.status()["budget_admissions"]["source"] == 2


def test_bound_external_files_allow_review_but_not_automatic_acceptance(authority):
    source = authority.admit()
    result_files(authority, source)
    authority.record(source["attempt"])
    evidence = authority.root / "supplied-reader.json"
    write(evidence, {"note": "Supplied input awaiting actual substantive verification"})
    def refine(p):
        task = p["tasks"][1]
        task["inputs"].append("supplied-reader.json")
        task["external_evidence"] = [{"path": "supplied-reader.json", "sha256": file_hash(evidence)}]
    state = propose(authority, refine)
    assert state["next_task"] == "readers"
    admission = authority.admit()
    assert admission["task_spec"]["handler"] == "external"
    result_files(authority, admission, independent=True)
    state = authority.record(admission["attempt"])
    row = next(t for t in state["tasks"] if t["id"] == "readers")
    assert row["state"] == "RESULT_RECORDED"
    assert not state["completion"]["assisted"]


def test_controller_change_does_not_requeue_unchanged_partial_work(authority):
    admitted = authority.admit()
    result_files(authority, admitted)
    authority.record(admitted["attempt"])
    (authority.root / CODE[0]).write_text("# reviewed controller repair\n")
    assert authority.status()["tasks"][0]["state"] == "RESULT_RECORDED"
    assert authority.status()["next_task"] is None


def test_corrupt_partial_cannot_be_retried_by_task_refinement(authority):
    admitted = authority.admit()
    attempt = result_files(authority, admitted)
    authority.record(admitted["attempt"])
    write(attempt / "result.json", {"status": "PASS", "altered": True})
    state = propose(authority, lambda p: p["tasks"][0].update(reason="Next source package"))
    assert state["tasks"][0]["state"] == "REPAIR_REQUIRED"
    assert state["next_task"] is None


@pytest.mark.parametrize("available", ["missing", "wrong_hash"])
def test_external_evidence_waits_when_missing_or_changed(authority, available):
    path = authority.root / "reader.json"
    write(path, {"unverified": True})
    expected = file_hash(path)
    if available == "missing":
        path.unlink()
    else:
        write(path, {"changed": True})
    def refine(p):
        p["tasks"][1]["inputs"].append("reader.json")
        p["tasks"][1]["external_evidence"] = [{"path": "reader.json", "sha256": expected}]
    state = propose(authority, refine)
    assert state["tasks"][1]["state"] == "WAITING_EXTERNAL"
    assert state["next_task"] == "source"


def test_external_evidence_must_be_admitted_input(authority):
    def refine(p):
        p["tasks"][1]["external_evidence"] = [{"path": "source.txt", "sha256": "1" * 64}]
        p["tasks"][1]["inputs"] = []
    with pytest.raises(ValueError, match="hashed admitted input"):
        propose(authority, refine)


def test_empty_output_manifest_cannot_accept_result(authority, monkeypatch):
    admission = authority.admit()
    attempt = result_files(authority, admission)
    write(attempt / "outputs.json", {})
    monkeypatch.setattr(execution_workers, "validate", lambda *args: True)
    assert authority.record(admission["attempt"])["tasks"][0]["state"] == "REPAIR_REQUIRED"
