import importlib.util
from pathlib import Path
import sys
import pytest
from legalmath.canonical import loads,digest


def runner(monkeypatch):
    root=Path(__file__).resolve().parents[2];monkeypatch.syspath_prepend(str(root/'scripts'))
    spec=importlib.util.spec_from_file_location('public_private_supervisor',root/'scripts/run_interpretation_plan.py')
    supervisor=importlib.util.module_from_spec(spec);spec.loader.exec_module(supervisor)
    monkeypatch.setitem(sys.modules,'run_interpretation_plan',supervisor)
    spec=importlib.util.spec_from_file_location('public_runner_test',root/'scripts/run_public_issue_plan.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module,supervisor


def test_fixed_public_run_and_existing_grant(monkeypatch,tmp_path,root):
    module,_=runner(monkeypatch)
    commands=module.commands('H1',tmp_path)
    live=commands[0][1]
    assert live[1:4]==['-m','legalmath.cli','assurance-interpret-issue']
    assert '--allowance' in live and '--max-calls' not in live
    assert commands[1][1][1]=='scripts/audit_public_issue.py'
    auth=loads((root/'docs/implementation/interpretation-round10/authorization.json').read_bytes())
    assert auth['maximum_new_calls']==24 and auth['allowance_maximum']==500
    assert module.protect()['new_allowance']['maximum']==500
    public=loads((root/'examples/interpretation-assurance/declared-issue.json').read_bytes())
    assert set(public)=={'packet','issue','at'}
    reviewed=module.inputs()['files']
    assert 'src/legalmath/java/runtime/Policy.java' in reviewed
    assert 'src/legalmath/schemas/rule-bundle.schema.json' in reviewed


def test_execution_requires_predecessors_and_current_review(monkeypatch,tmp_path):
    module,supervisor=runner(monkeypatch);supervisor.OUT=tmp_path
    state=supervisor.state()
    with pytest.raises(ValueError,match='Missing/stale'):module.run('H0',state)
    with pytest.raises(ValueError,match='Predecessor'):module.run('H1',state)
    state['phases']['H0']['status']='REPAIR_REQUIRED'
    with pytest.raises(ValueError,match='executed repair'):module.run('H0',state)
