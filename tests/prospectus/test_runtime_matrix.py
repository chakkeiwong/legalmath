"""Current live-selector, cumulative ledger and unchanged fallback controls."""
from copy import deepcopy
from pathlib import Path
import subprocess
import pytest

from legalmath.prospectus.successor import process_ledger
from scripts import prospectus_runtime_matrix as matrix
from scripts import prospectus_native_current as driver
from scripts import prospectus_current_acceptance as dispatch


def task():
    return {'id': 'native-binding', 'handler': 'agent', 'validator': 'native-retained-current.v3',
            'current_runtime_matrix': deepcopy(matrix.SELECTOR), 'preparation_only': False,
            'retained_acceptance_only': False, 'native_call_allowance': 11}


@pytest.mark.parametrize('field,value', [('id','native-confinement'), ('validator',None),
    ('preparation_only',True), ('retained_acceptance_only',True), ('native_call_allowance',0),
    ('current_runtime_matrix',None)])
def test_matrix_rejects_altered_grant(field, value):
    supplied = task(); matrix.selector(supplied); supplied[field] = value
    with pytest.raises(ValueError, match='grant'): matrix.selector(supplied)


def test_matrix_ledger_refuses_old_floor_and_counts_failed_start(tmp_path, monkeypatch):
    path = tmp_path / 'process-ledger.json'
    process_ledger.create(path, 11, 50, 'obsolete')
    with pytest.raises(ValueError, match='cumulative'): matrix.ledger(tmp_path)
    value = process_ledger.checked(path); value['historical_lower_bound'] = 61; process_ledger.save(path, value)
    matrix.ledger(tmp_path, 0)
    def failed(*args, **kwargs): raise OSError('controlled spawn failure')
    monkeypatch.setattr(subprocess, 'Popen', failed)
    with driver.native_calls(tmp_path, 1, ledger=matrix.ledger):
        with pytest.raises(OSError, match='controlled'): subprocess.Popen(['controlled-fixture'])
        with pytest.raises(ValueError, match='allowance'): subprocess.Popen(['must-not-launch'])
    rows = matrix.ledger(tmp_path)['reservations']
    assert len(rows) == 1 and rows[0]['state'] == 'SPAWN_FAILED'
    with pytest.raises(ValueError, match='failed'): matrix.ledger(tmp_path, 1)


def test_exact_dispatch_addition_preserves_historical_branches():
    before = (matrix.ROOT / matrix.REVIEW / 'before/scripts/prospectus_current_acceptance.py').read_text()
    marker = 'def validate_submission(root, attempt, task):\n'
    added = ('    if "current_runtime_matrix" in task:\n'
             '        from scripts.prospectus_runtime_matrix import validate_submission as validate_matrix\n'
             '        return validate_matrix(root, attempt, task)\n')
    assert before.count(marker) == 1
    assert (matrix.ROOT / 'scripts/prospectus_current_acceptance.py').read_text() == before.replace(marker, marker + added)


def test_actual_dispatch_reaches_matrix_and_rejects_missing_evidence(tmp_path):
    with pytest.raises((ValueError, FileNotFoundError)):
        dispatch.validate_submission(matrix.ROOT, tmp_path, task())


def test_driver_defaults_remain_original():
    assert driver.prepare.__kwdefaults__['historical_floor'] == 50
    for function in (driver.native_calls.__wrapped__, driver.controls, driver.route, driver.probe):
        assert function.__kwdefaults__['ledger'] is matrix.checks.ledger
