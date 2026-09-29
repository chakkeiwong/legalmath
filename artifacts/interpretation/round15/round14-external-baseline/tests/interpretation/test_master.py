import importlib.util
from pathlib import Path
import pytest

@pytest.fixture
def master(root,tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('master',root/'scripts/run_interpretation_plan.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'OUT',tmp_path/'out')
    monkeypatch.setattr(module,'inputs',lambda: {'files':{},'digest':'test'})
    monkeypatch.setattr(module,'ROOT',tmp_path)
    return module

def test_predecessor_and_repair_blocks(master):
    s=master.state()
    with pytest.raises(ValueError,match='Predecessor'): master.run('P1',s)
    s['phases']['P0']['status']='REPAIR_REQUIRED'
    with pytest.raises(ValueError,match='repair'): master.run('P0',s)
    s['phases']['P0']['status']='RUNNING'
    with pytest.raises(ValueError,match='recover'): master.run('P0',s)

def test_budget_and_stale_review(master):
    s=master.state();s['phases']['P0']['attempts']=[{'status':'FAILED'}]*6
    with pytest.raises(ValueError,match='budget'): master.run('P0',s)
    s['phases']['P0']['attempts']=[]
    master.refresh('P0',s)
    with pytest.raises(ValueError,match='stale'): master.run('P0',s)

def test_interrupted_attempt_is_preserved(master):
    s=master.state();s['phases']['P0']['status']='RUNNING'
    path=master.OUT/'P0/attempt-01/run-manifest.json'
    master.write(path,{'status':'RUNNING'})
    master.recover('P0',s)
    assert master.read(path)['failure']=='SUPERVISOR_INTERRUPTED'
    assert len(s['phases']['P0']['attempts'])==1
    assert s['phases']['P0']['status']=='REPAIR_REQUIRED'
    refreshed=master.refresh('P1',s)
    assert refreshed['predecessors']['P0']['attempts'][0]['failure']=='SUPERVISOR_INTERRUPTED'

def test_fixed_commands(master,tmp_path):
    for phase in master.PHASES:
        for name, argv in master.commands(phase,tmp_path):
            assert argv[0]==str(master.PYTHON)
            assert 'shell' not in argv
