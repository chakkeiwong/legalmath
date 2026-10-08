"""Exercise supervisor failures without launching a provider or long suite."""
import importlib.util
from pathlib import Path
import json

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def master(tmp_path, monkeypatch):
    spec=importlib.util.spec_from_file_location('dossier_master',ROOT/'scripts/run_proof_carrying_master.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setattr(module,'OUT',tmp_path/'out')
    # Unit controller artifacts live under tmp_path; repository inputs are fixed by this test.
    monkeypatch.setattr(module,'ROOT',tmp_path)
    monkeypatch.setattr(module,'material_inputs',lambda:{'files':{'fixture':'v1'},'digest':'v1'})
    monkeypatch.setattr(module.subprocess,'check_output',lambda *a,**k:'test-commit')
    monkeypatch.setattr(module,'PLAN',tmp_path/'plan.md')
    return module


def test_exact_allowlist_rejects_injected_flags_and_paths(tmp_path):
    spec=importlib.util.spec_from_file_location('allowlist_master',ROOT/'scripts/run_proof_carrying_master.py')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    out=m.OUT/'P1/attempt-01'; argv=m.fixed_command('contract',out)
    assert m.command_allowed(argv,out)
    assert not m.command_allowed(argv+['-k','skip_everything'],out)
    assert not m.command_allowed([*argv[:-1],'--junitxml=/tmp/elsewhere.xml'],out)
    assert not m.command_allowed(m.fixed_command('contract',tmp_path),tmp_path)


def test_junit_requires_complete_nonempty_no_skip_result(master,tmp_path):
    p=tmp_path/'result.xml'
    for text in ['<testsuites/>','<testsuite tests="1" skipped="1"/>','<testsuite tests="1" failures="1"/>']:
        p.write_text(text)
        with pytest.raises(RuntimeError): master.junit(p)
    p.write_text('<testsuite tests="2" errors="0" failures="0" skipped="0"/>')
    assert master.junit(p)['tests']==2


def test_environment_fingerprint_ignores_duplicate_paths_but_retains_version_conflicts(master,monkeypatch):
    from types import SimpleNamespace
    first=SimpleNamespace(metadata={'Name':'example'},version='1.0')
    second=SimpleNamespace(metadata={'Name':'example'},version='2.0')
    monkeypatch.setattr(master.importlib.metadata,'distributions',lambda:[first,first,second])
    repeated=master.environment_fingerprint()
    monkeypatch.setattr(master.importlib.metadata,'distributions',lambda:[second,first])
    assert master.environment_fingerprint()==repeated
    assert repeated['packages']==[['example','1.0'],['example','2.0']]


def test_failed_attempt_survives_and_cannot_retry_without_repair(master,monkeypatch):
    def fail(*args): raise RuntimeError('intentional failure')
    monkeypatch.setattr(master,'phase_work',fail)
    current=master.state()
    with pytest.raises(RuntimeError): master.run_phase('P0',current)
    original=current['phases']['P0']['attempts'][0]
    old_bytes=(master.ROOT/original['path']).read_bytes()
    assert current['phases']['P0']['status']=='REPAIR_REQUIRED'
    with pytest.raises(RuntimeError,match='repair'): master.run_phase('P0',current)
    assert (master.ROOT/original['path']).read_bytes()==old_bytes


def test_mid_phase_input_change_cannot_pass(master,monkeypatch):
    def change(*args):
        monkeypatch.setattr(master,'material_inputs',lambda:{'files':{'fixture':'v2'},'digest':'v2'})
        return {'status':'looks_good'}
    monkeypatch.setattr(master,'phase_work',change)
    with pytest.raises(RuntimeError,match='Inputs changed'): master.run_phase('P0',master.state())


def test_output_tampering_invalidates_acceptance(master,monkeypatch):
    def produce(phase,directory,current):
        (directory/'result.txt').write_text('checked')
        return {'status':'checked'}
    monkeypatch.setattr(master,'phase_work',produce)
    current=master.state(); master.run_phase('P0',current)
    ref=current['phases']['P0']['attempts'][-1]
    master.verify_manifest(ref,current_inputs=master.material_inputs())
    (master.ROOT/ref['path']).with_name('result.txt').write_text('forged')
    master.invalidate(current)
    assert current['phases']['P0']['status']=='STALE'


def test_controller_plan_change_has_no_compatibility_bypass(master,monkeypatch):
    monkeypatch.setattr(master,'phase_work',lambda *args:{})
    current=master.state(); master.run_phase('P0',current)
    monkeypatch.setattr(master,'material_inputs',lambda:{'files':{'controller':'changed'},'digest':'v2'})
    master.invalidate(current)
    assert current['phases']['P0']['status']=='STALE'


def test_changed_inputs_cannot_leave_a_current_passing_final_report(master,monkeypatch):
    monkeypatch.setattr(master,'phase_work',lambda *args:{})
    current=master.state(); master.run_phase('P0',current)
    master.write(master.OUT/'final-report.json',{'status':'ENGINEERING_PASS_WITH_RETAINED_UNCERTAINTY',
                                              'release_eligible':False})
    old=(master.OUT/'final-report.json').read_bytes()
    monkeypatch.setattr(master,'material_inputs',lambda:{'files':{'source':'changed'},'digest':'v2'})
    master.invalidate(current)
    report=master.read(master.OUT/'final-report.json')
    assert report['status']=='STALE_REVALIDATION_REQUIRED'
    assert (master.ROOT/report['superseded_report']).read_bytes()==old


def test_interruption_is_preserved_before_retry(master,monkeypatch):
    def stop(*args): raise KeyboardInterrupt()
    monkeypatch.setattr(master,'phase_work',stop)
    current=master.state()
    with pytest.raises(KeyboardInterrupt): master.run_phase('P0',current)
    ref=current['phases']['P0']['attempts'][-1]
    assert master.read(master.ROOT/ref['path'])['failure'].startswith('KeyboardInterrupt')
    assert current['phases']['P0']['status']=='REPAIR_REQUIRED'


def test_attempt_ceiling_is_not_reset_by_staleness(master):
    current=master.state(); current['phases']['P0'].update(status='STALE',attempts=[{}, {}, {}])
    with pytest.raises(RuntimeError,match='ceiling'): master.run_phase('P0',current)


def test_repair_executes_check_preserves_failure_and_refreshes_next_phase(master,monkeypatch,tmp_path):
    def fail(*args): raise RuntimeError('fault requiring repair')
    monkeypatch.setattr(master,'phase_work',fail)
    current=master.state()
    with pytest.raises(RuntimeError): master.run_phase('P0',current)
    failed=current['phases']['P0']['attempts'][0]
    before=(master.ROOT/failed['path']).read_bytes()
    doc=tmp_path/'notes'; doc.mkdir(); monkeypatch.setattr(master,'DOC',doc)
    note=doc/'repair.json'; note.write_text(json.dumps({'failure':'fault','changes':['repair implementation'],
                                                      'regression':['contract']}))
    calls=[]
    def checked(kind,directory):
        calls.append(kind); return {'status':'PASSED','kind':kind}
    monkeypatch.setattr(master,'run_command',checked)
    master.repair('P0',note)
    assert calls==['contract']
    repaired=master.state()
    assert repaired['phases']['P0']['status']=='REPAIRED_PENDING_RETRY'
    monkeypatch.setattr(master,'phase_work',lambda *args:{'fixed':True})
    master.run_phase('P0',repaired)
    assert len(repaired['phases']['P0']['attempts'])==2
    assert (master.ROOT/failed['path']).read_bytes()==before
    assert master.read(master.OUT/'next-phase-plan.json')['next_phase']=='P1'
