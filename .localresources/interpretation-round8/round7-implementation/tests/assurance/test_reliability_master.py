"""The successor runner cannot spend live calls, skip review, or rerun acceptance."""
import importlib.util
from pathlib import Path
import sys
import pytest


def runner(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root/'scripts'))
    spec = importlib.util.spec_from_file_location('reliability_private_supervisor', root/'scripts/run_interpretation_plan.py')
    supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
    monkeypatch.setitem(sys.modules, 'run_interpretation_plan', supervisor)
    spec = importlib.util.spec_from_file_location('reliability_runner_test', root/'scripts/run_interpretation_reliability_plan.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module, supervisor


def test_fixed_offline_commands_and_protected_predecessor(monkeypatch, tmp_path):
    module, _ = runner(monkeypatch)
    commands = module.commands('B0', tmp_path)
    assert [name for name, command in commands] == ['tests', 'retained']
    assert commands[1][1][1] == 'scripts/interpretation_reliability_acceptance.py'
    assert '--allowance' not in commands[1][1] and '--new-tasks' not in commands[1][1]
    protected = module.protect()
    assert protected['frozen_files'] == 191 and protected['protected_A7_files'] >= 4676
    assert protected['new_live_calls'] == 0


def test_future_phase_is_not_executable_and_missing_review_blocks_current_phase(monkeypatch, tmp_path):
    module, supervisor = runner(monkeypatch); supervisor.OUT = tmp_path
    original_read = supervisor.read
    def disabled(path, *args):
        value = original_read(path, *args)
        if path == module.PLAN:
            value['phases'][1]['executable'] = False
        return value
    with monkeypatch.context() as m:
        m.setattr(supervisor, 'read', disabled)
        with pytest.raises(ValueError, match='not executable'):
            module.run('B1', supervisor.state())
    with pytest.raises(ValueError, match='Missing/stale'):
        module.run('B0', supervisor.state())


def test_failure_requires_executed_repair_and_accepted_result_cannot_be_overwritten(monkeypatch, tmp_path):
    module, supervisor = runner(monkeypatch); supervisor.OUT = tmp_path
    state = supervisor.state(); state['phases']['B0']['status'] = 'REPAIR_REQUIRED'
    with pytest.raises(ValueError, match='executed repair'):
        module.run('B0', state)
    state['phases']['B0']['status'] = 'PASSED'
    with pytest.raises(ValueError, match='already passed'):
        module.run('B0', state)
