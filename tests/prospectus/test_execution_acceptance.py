"""Finite acceptance must not turn arbitrary summaries into domain completion."""
from copy import deepcopy
from pathlib import Path

import pytest

from legalmath.prospectus import execution_acceptance as acceptance, execution_workers
from legalmath.prospectus.execution_authority import file_hash, write


def task():
    return {'id': 'recovery', 'handler': 'agent', 'stream': 'engineering', 'validator': 'recovery-sequence.v1'}


@pytest.mark.parametrize('change', [
    {'validator': 'anything'}, {'validator': ['recovery-sequence.v1']},
    {'id': 'readers'}, {'handler': 'external'}, {'stream': 'assisted'},
    {'id': 'authority-acceptance'},
])
def test_named_validator_cannot_accept_other_task_or_human_scope(change):
    value = task()
    value.update(change)
    with pytest.raises(ValueError, match='outside its named'):
        acceptance.check_task(value)


def test_recovery_selection_equivalence_rejects_other_behavior_changes():
    original = "JOBS={'R0':('p.py',None),'R4':('m.py','old'),'R6':('n.py','old')}\nVALUE=1\n"
    assert acceptance.selection_only_change(original, original.replace("'old'", "'new'"))
    assert not acceptance.selection_only_change(original, original.replace('VALUE=1', 'VALUE=2'))
    assert not acceptance.selection_only_change(original, original.replace("'p.py'", "'different.py'"))
    assert not acceptance.selection_only_change(original, original + "def f(): return False\n")
    assert not acceptance.selection_only_change(original, 'JOBS = unknown()')


def test_registered_validator_requires_actual_evidence(tmp_path):
    attempt = tmp_path / 'attempt'
    attempt.mkdir()
    write(attempt / 'result.json', {'task': 'recovery', 'status': 'PASS', 'all_tests_pass': True})
    with pytest.raises(ValueError, match='Named retained evidence'):
        execution_workers.validate(tmp_path, attempt, task())


def test_unregistered_agent_result_stays_partial(tmp_path):
    write(tmp_path / 'result.json', {'task': 'anything', 'status': 'PASS', 'done': True})
    assert not execution_workers.validate(tmp_path, tmp_path, {'id': 'anything', 'handler': 'agent'})


def fixture_attempt(tmp_path):
    root = tmp_path.resolve()
    relative = 'docs/implementation/prospectus-execution-authority/attempts/recovery/attempt-001'
    folder = root / relative
    folder.mkdir(parents=True)
    write(folder / 'result.json', {'task': 'recovery', 'status': 'PASS'})
    write(folder / 'outputs.json', {'result.json': file_hash(folder / 'result.json')})
    value = {**task(), 'evidence_attempt': relative,
             'inputs': [relative + '/result.json', relative + '/outputs.json']}
    return root, folder, value


def test_retained_acceptance_checks_each_bound_file_and_task_identity(tmp_path):
    root, folder, value = fixture_attempt(tmp_path)
    assert acceptance.retained_attempt(root, value) == folder
    omitted = deepcopy(value)
    omitted['inputs'].pop()
    with pytest.raises(ValueError, match='admitted input'):
        acceptance.retained_attempt(root, omitted)
    write(folder / 'result.json', {'task': 'recovery', 'status': 'PASS', 'changed': True})
    with pytest.raises(ValueError, match='identity changed'):
        acceptance.retained_attempt(root, value)


def test_recovery_evidence_requires_all_eight_states(tmp_path):
    root, folder, value = fixture_attempt(tmp_path)
    write(folder / 'started.json', {'states': ['baseline']})
    write(folder / 'outputs.json', {p.name: file_hash(p) for p in folder.iterdir() if p.name != 'outputs.json'})
    value['inputs'].append(str((folder / 'started.json').relative_to(root)))
    with pytest.raises(ValueError, match='state denominator'):
        acceptance.recovery_evidence(root, value)


@pytest.mark.parametrize('body', [
    '<not-closed',
    '<testsuite tests="many"/>',
    '<testsuites/>',
    '<testsuite tests="1" failures="1" errors="0" skipped="0"/>',
    '<testsuite tests="1" failures="0" errors="0" skipped="1"/>',
])
def test_empty_failed_or_skipped_required_checks_cannot_accept(tmp_path, body):
    path = tmp_path / 'tests.xml'
    path.write_text(body)
    with pytest.raises(ValueError, match='required evidence checks'):
        acceptance.checked_tests(path, 1)


def test_false_whole_program_claim_rejected_even_with_matching_finite_products(tmp_path, monkeypatch):
    expected = {'finite': True}
    monkeypatch.setattr(acceptance, 'recovery_evidence', lambda *args: expected)
    write(tmp_path / 'verification.json', expected)
    write(tmp_path / 'result.json', {'status': 'PASS', 'task': 'recovery',
                                   'scope': 'FINITE_ENGINEERING_ONLY', 'whole_program_complete': True})
    with pytest.raises(ValueError, match='whole-program completion'):
        execution_workers.validate(tmp_path, tmp_path, task())


def test_changed_finite_result_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(acceptance, 'recovery_evidence', lambda *args: {'states': 8})
    write(tmp_path / 'verification.json', {'states': 7})
    write(tmp_path / 'result.json', {'status': 'PASS', 'task': 'recovery'})
    with pytest.raises(ValueError, match='actual retained evidence'):
        execution_workers.validate(tmp_path, tmp_path, task())
