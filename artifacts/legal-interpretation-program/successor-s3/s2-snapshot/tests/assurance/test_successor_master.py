"""Controller integrity tests without providers, document builds or long tests."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture
def master(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('successor_controller_fixture',ROOT/'scripts/run_assurance_successor.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    for key,value in {'ROOT':tmp_path,'OUT':tmp_path/'out','DOC':tmp_path/'docs',
                      'PLAN':tmp_path/'plan.md','GRANT':tmp_path/'out/grant.json'}.items():monkeypatch.setattr(m,key,value)
    m.DOC.mkdir();m.PLAN.write_text('Controlled controller test')
    (tmp_path/'src/legalmath').mkdir(parents=True);(tmp_path/'src/legalmath/example.py').write_text('value=1\n')
    m.save(m.DOC/'allowlist.json',json.loads((ROOT/'docs/implementation/assurance-successor/allowlist.json').read_text()))
    monkeypatch.setattr(m.subprocess,'check_output',lambda *a,**kw:'fixture-commit')
    def baseline(work):
        (work/'result.txt').write_text('Controlled baseline evidence')
        return {'status':'FIXTURE_EXECUTED'}
    monkeypatch.setattr(m,'baseline',baseline)
    return m


def test_owned_phase_manifest_is_saved_before_execution(master,monkeypatch):
    def check(work):
        assert (work/'start-manifest.json').exists()
        return {'status':'FIXTURE_EXECUTED'}
    monkeypatch.setattr(master,'baseline',check)
    master.phase('S0')
    assert master.state()['phases']['S0']['status']=='PASSED'
    assert master.read(master.OUT/'next-phase-plan.json')['next_phase']=='S1'
    import zipfile
    m=master.read(master.OUT/'S0/attempt-01/manifest.json');ref=m['implementation_archive']
    assert master.sha(master.ROOT/ref['path'])==ref['sha256']
    with zipfile.ZipFile(master.ROOT/ref['path']) as z:
        assert z.read('src/legalmath/example.py')==b'value=1\n'
        assert z.read('controller/run_assurance_successor.py')==(ROOT/'scripts/run_assurance_successor.py').read_bytes()


def test_tampered_predecessor_cannot_remain_a_passing_receipt(master):
    master.phase('S0')
    (master.OUT/'S0/attempt-01/result.txt').write_text('Changed evidence')
    updated=master.refresh(master.state())
    assert updated['invalid_evidence_phases']==['S0']
    assert master.state()['phases']['S0']['status']=='STALE_EVIDENCE'
    with pytest.raises(RuntimeError):master.phase('S1')


def test_changed_material_file_invalidates_a_final_report_without_resetting_attempts(master):
    master.phase('S0');file=master.ROOT/'src/legalmath/example.py'
    original={'status':'ENGINEERING_EXECUTION_COMPLETED_WITH_RETAINED_UNCERTAINTY',
              'material_inputs':{master.rel(file):master.sha(file)},'retained_evidence':{}}
    master.save(master.OUT/'final-report.json',original);file.write_text('value=2\n')
    master.refresh(master.state());new=master.read(master.OUT/'final-report.json')
    assert new['status']=='STALE_REVALIDATION_REQUIRED'
    assert master.read(master.ROOT/new['superseded_report'])==original
    assert len(master.state()['phases']['S0']['attempts'])==1


def test_unexecuted_or_changed_repair_cannot_authorize_retry(master,monkeypatch):
    def fail(work):raise RuntimeError('Controlled failure')
    monkeypatch.setattr(master,'baseline',fail)
    with pytest.raises(RuntimeError):master.phase('S0')
    failed=master.read(master.OUT/'S0/attempt-01/manifest.json')
    master.save(master.DOC/'S0-repair-1.json',{'focused_check_passed':True})
    with pytest.raises(RuntimeError,match='XML'):master.phase('S0')
    xml=master.DOC/'S0-repair-1.xml';xml.write_text('<testsuite tests="1" skipped="1"/>')
    master.save(master.DOC/'S0-repair-1.json',{'focused_check_passed':True,'focused_xml_sha256':master.sha(xml)})
    with pytest.raises(RuntimeError,match='without skips'):master.phase('S0')
    assert master.read(master.OUT/'S0/attempt-01/manifest.json')==failed


def test_attempt_limit_survives_repair_and_staleness(master):
    master.OUT.mkdir();s=master.state();s['phases']['S0'].update(status='STALE_EVIDENCE',attempts=[{},{},{}]);master.save(master.OUT/'state.json',s)
    with pytest.raises(RuntimeError,match='ceiling'):master.phase('S0')


def test_status_does_not_write_while_a_phase_owns_the_controller(master):
    import fcntl
    master.phase('S0')
    state_before=(master.OUT/'state.json').read_bytes()
    next_before=(master.OUT/'next-phase-plan.json').read_bytes()
    (master.OUT/'S0/attempt-01/result.txt').write_text('Changed diagnostic evidence')
    with (master.OUT/'.master.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        status=master.status_report()
        assert status['active_phase_writer'] and status['invalid_evidence_phases']==['S0']
        assert (master.OUT/'state.json').read_bytes()==state_before
        assert (master.OUT/'next-phase-plan.json').read_bytes()==next_before
    assert not master.status_report()['active_phase_writer']
    assert master.state()['phases']['S0']['status']=='STALE_EVIDENCE'


def test_wrong_phase_receipt_cannot_satisfy_a_predecessor(master):
    from copy import deepcopy
    master.phase('S0');s=master.state();s['phases']['S1']=deepcopy(s['phases']['S0']);master.save(master.OUT/'state.json',s)
    with pytest.raises(RuntimeError,match='Wrong predecessor'):master.phase('S2')
    assert 'S1' in master.refresh(master.state())['invalid_evidence_phases']


def test_documented_s6_amendment_never_resets_or_permits_a_seventh_attempt(master):
    master.OUT.mkdir();s=master.state();s['phases']['S6'].update(status='FAILED',attempts=[{},{},{},{},{}])
    master.save(master.OUT/'state.json',s)
    status=master.refresh(master.state())
    assert status['phases']['S6']['attempts_consumed']==5 and status['phases']['S6']['attempts_remaining']==1
    s=master.state();s['phases']['S6']['attempts'].append({});master.save(master.OUT/'state.json',s)
    assert master.refresh(master.state())['phases']['S6']['attempts_remaining']==0
    assert master.attempt_limit('S0')==3
    assert master.attempt_limit('S8')==9


def test_incomplete_phase_keeps_its_structured_result_without_claiming_pass(master,monkeypatch):
    result={'status':'CONTROLLED_INCOMPLETE','execution_complete':False,'missing':['required evidence']}
    monkeypatch.setattr(master,'baseline',lambda work:result)
    with pytest.raises(RuntimeError,match='structured result retained'):master.phase('S0')
    manifest=master.read(master.OUT/'S0/attempt-01/manifest.json')
    assert manifest['result']==result and manifest['status']=='FAILED'
    assert master.state()['phases']['S0']['status']=='FAILED'


def failed_study(master,*,error='E_RESOURCE_LIMIT'):
    s=master.state()
    for phase in master.PHASES[:8]:
        p=master.OUT/phase/'manifest.json';master.save(p,{'phase':phase,'status':'PASSED','outputs':{},'result':{}})
        s['phases'][phase]={'status':'PASSED','attempts':[{'manifest':master.rel(p),'sha256':master.sha(p)}]}
    master.save(master.OUT/'task-freeze.json',{'tasks':[{'task_id':'a'},{'task_id':'b'}]})
    result={'execution_complete':False,'tasks':[{'task_id':k,'single':{'status':'INCOMPLETE','error':error},
        'ensemble':{'status':'INCOMPLETE','error':error}} for k in ('a','b')]}
    p=master.OUT/'S8/manifest.json';master.save(p,{'phase':'S8','status':'FAILED','outputs':{},'result':result})
    s['phases']['S8']={'status':'FAILED','attempts':[{'manifest':master.rel(p),'sha256':master.sha(p),'status':'FAILED'}]}
    master.save(master.OUT/'state.json',s);return s,p


def test_assessment_keeps_resource_failed_study_failed_and_binds_its_attempt(master,monkeypatch):
    s,p=failed_study(master)
    import assurance_successor_phases as phases
    monkeypatch.setattr(phases,'execute',lambda phase,work:{'assessment_complete':True,'overall_execution_complete':False})
    with pytest.raises(RuntimeError,match='Predecessor incomplete'):master.phase('S9')
    master.phase('S9',assessment=True)
    s=master.state();assert s['phases']['S8']['status']=='FAILED' and s['phases']['S9']['status']=='PASSED'
    m=master.read(master.ROOT/s['phases']['S9']['attempts'][-1]['manifest'])
    assert m['incomplete_study_assessment']['study_attempt']==s['phases']['S8']['attempts'][-1]
    assert not m['result']['overall_execution_complete']
    s['phases']['S8']['attempts'].append({'manifest':'changed','sha256':'a'*64,'status':'FAILED'})
    master.save(master.OUT/'state.json',s)
    assert 'S9' in master.refresh(s)['invalid_evidence_phases']


@pytest.mark.parametrize('failure',['implementation','omitted_task','tamper','integrity'])
def test_incomplete_assessment_rejects_unbound_or_ineligible_evidence(master,failure):
    s,p=failed_study(master,error='E_INTEGRITY' if failure=='integrity' else 'E_REFERENCE' if failure=='implementation' else 'E_RESOURCE_LIMIT')
    if failure in ('omitted_task','tamper'):
        m=master.read(p);m['result']['tasks'].pop();master.save(p,m)
        if failure=='omitted_task':s['phases']['S8']['attempts'][-1]['sha256']=master.sha(p)
    with pytest.raises(RuntimeError):master.incomplete_assessment_basis(s)
