"""Exercise supervisor refusal paths without running experiments or modifying evidence."""
import importlib.util
from pathlib import Path
import sys
import pytest


def runner(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root / 'scripts'))
    # Load a private supervisor so this test cannot mutate other runners' globals.
    spec = importlib.util.spec_from_file_location('assurance_supervisor_test', root / 'scripts/run_interpretation_plan.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setitem(sys.modules, 'run_interpretation_plan', module)
    spec = importlib.util.spec_from_file_location('assurance_runner_test', root / 'scripts/run_interpretation_assurance_plan.py')
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result, module


def test_baseline_is_protected(monkeypatch):
    r, _ = runner(monkeypatch)
    assert r.protect()['frozen_files'] == 191
    assert r.protect()['protected_evidence'] > 100


def test_no_phase_can_skip_predecessor_or_executed_repair(monkeypatch, tmp_path):
    r, s = runner(monkeypatch)
    s.OUT = tmp_path
    state = s.state()
    with pytest.raises(ValueError, match='Predecessor'):
        s.run('A1', state)
    state['phases']['A0']['status'] = 'REPAIR_REQUIRED'
    with pytest.raises(ValueError, match='executed repair'):
        s.run('A0', state)


def test_missing_review_cannot_execute(monkeypatch, tmp_path):
    r, s = runner(monkeypatch)
    s.OUT = tmp_path
    with pytest.raises(ValueError, match='Missing/stale'):
        s.run('A0', s.state())


def test_fixed_commands_bound_live_pilot(monkeypatch, tmp_path):
    r, s = runner(monkeypatch)
    assert len(r.commands('A1', tmp_path)) == 1
    live = r.commands('A7', tmp_path)[1][1]
    assert live[1] == 'scripts/interpretation_assurance_pilot.py'
    assert live[live.index('--allowance')+1].endswith('round2/live-allowance.json')
    assert live[live.index('--recover')+1].endswith('round3/recovered-source-inventory.json')
