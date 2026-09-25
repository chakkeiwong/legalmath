"""The fixed continuation may spend only the reviewed additional-call grant."""
import importlib.util
from pathlib import Path
import sys
import pytest


def runner(monkeypatch):
    root=Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root/'scripts'))
    spec=importlib.util.spec_from_file_location('checkpoint_private_supervisor',root/'scripts/run_interpretation_plan.py')
    supervisor=importlib.util.module_from_spec(spec);spec.loader.exec_module(supervisor)
    monkeypatch.setitem(sys.modules,'run_interpretation_plan',supervisor)
    spec=importlib.util.spec_from_file_location('checkpoint_runner_test',root/'scripts/run_checkpoint_plan.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module,supervisor


def test_fixed_commands_and_separate_allowance_history(monkeypatch,tmp_path):
    module,_=runner(monkeypatch)
    assert module.commands('E2',tmp_path)[0][1][1:] == [
        'scripts/run_checkpoint_phase.py','--phase','E2','--out',str(tmp_path/'live')]
    protected=module.protect()
    assert protected['earlier_used_calls']==97 and protected['new_allowance']['maximum']==500
    assert protected['protected_files']>=1084


def test_unreviewed_execution_failed_repair_and_accepted_overwrite_are_blocked(monkeypatch,tmp_path):
    module,supervisor=runner(monkeypatch);supervisor.OUT=tmp_path
    state=supervisor.state()
    with pytest.raises(ValueError,match='Missing/stale'):module.run('E0',state)
    state['phases']['E0']['status']='REPAIR_REQUIRED'
    with pytest.raises(ValueError,match='executed repair'):module.run('E0',state)
    state['phases']['E0']['status']='PASSED'
    with pytest.raises(ValueError,match='already passed'):module.run('E0',state)


def test_frozen_contracts_stay_inside_initial_170_calls(root):
    from legalmath.canonical import loads,digest
    folder=root/'docs/implementation/interpretation-round7/contracts'
    for phase in ('E1','E2','E3'):
        contract=loads((folder/(phase+'.json')).read_bytes())
        assert contract['reservation_ceiling']<=170
        plan=loads((folder/contract['plan_file']).read_bytes())
        assert digest(plan)==contract['plan_hash']
        assert plan['maximum_attempts']<=3
