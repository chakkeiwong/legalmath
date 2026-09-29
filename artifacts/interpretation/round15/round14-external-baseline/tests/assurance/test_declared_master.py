import importlib.util
from pathlib import Path
import sys
import pytest
from legalmath.canonical import loads,digest


def runner(monkeypatch):
    root=Path(__file__).resolve().parents[2];monkeypatch.syspath_prepend(str(root/'scripts'))
    spec=importlib.util.spec_from_file_location('declared_private_supervisor',root/'scripts/run_interpretation_plan.py')
    supervisor=importlib.util.module_from_spec(spec);spec.loader.exec_module(supervisor)
    monkeypatch.setitem(sys.modules,'run_interpretation_plan',supervisor)
    spec=importlib.util.spec_from_file_location('declared_runner_test',root/'scripts/run_declared_plan.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module,supervisor


def test_fixed_jobs_budget_and_no_heldout_claim(monkeypatch,tmp_path,root):
    module,_=runner(monkeypatch)
    assert module.commands('G2',tmp_path)[0][1][1:]==['scripts/run_declared_study.py','--out',str(tmp_path/'live')]
    doc=root/'docs/implementation/interpretation-round9'
    frozen=loads((doc/'study.json').read_bytes());contract=loads((doc/'live-contract.json').read_bytes())
    assert contract['study_hash']==digest(frozen)
    assert len(frozen['study']['jobs'])==16 and not frozen['study']['heldout']
    assert frozen['study']['required_call_reservation']==384
    assert contract['used_before']+384==contract['reservation_ceiling']<=500
    assert module.protect()['new_allowance']['maximum']==500
    for public in frozen['public_interfaces'].values():assert set(public)=={'packet','issue','at'}


def test_execution_requires_predecessors_and_current_review(monkeypatch,tmp_path):
    module,supervisor=runner(monkeypatch);supervisor.OUT=tmp_path
    state=supervisor.state()
    with pytest.raises(ValueError,match='Missing/stale'):module.run('G0',state)
    with pytest.raises(ValueError,match='Predecessor'):module.run('G2',state)
    state['phases']['G0']['status']='REPAIR_REQUIRED'
    with pytest.raises(ValueError,match='executed repair'):module.run('G0',state)


def test_completed_job_is_not_silently_overwritten_by_recovery(monkeypatch,tmp_path,root):
    from legalmath.errors import LegalMathError
    from legalmath.interpretation.assurance.monitor import save
    spec=importlib.util.spec_from_file_location('declared_study_recovery_test',root/'scripts/run_declared_study.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'OUT',tmp_path)
    save(tmp_path/'state.json',{'phases':{'G2':{'status':'RUNNING'}}})
    with pytest.raises(LegalMathError):module.recover_job('job.0')
    save(tmp_path/'state.json',{'phases':{'G2':{'status':'REPAIR_REQUIRED'}}})
    save(tmp_path/'jobs/job.0/scored.json',{'retained':True})
    with pytest.raises(LegalMathError) as error:module.recover_job('job.0')
    assert error.value.code=='E_IDEMPOTENCY'
