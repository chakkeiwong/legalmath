"""Safety-relevant controller faults; tool integrations run in the sidecar phase."""
import importlib.util
import json
from pathlib import Path
import pytest
from legalmath.interpretation.assurance.diversity import (
    Investigation,assess_methods,identity,page_discrepancy,conclusion_support,
)


def test_same_tokens_in_different_order_are_a_discrepancy():
    r=page_discrepancy('Only gifts other than discounts are prohibited.','Only discounts other than gifts are prohibited.')
    assert not r['agreement'] and not r['left_only'] and not r['right_only']
    assert not page_discrepancy('must not offer','must offer')['agreement']
    assert not page_discrepancy('','')['agreement']


def test_unanimity_cannot_hide_missing_visual_route_or_stale_claim():
    rows=[{'method_id':m,'family':'shared-poppler','status':'AGREES','claim_hash':'claim',
           'evidence_hash':'hash','shared_dependencies':['Poppler']} for m in ('text','ra')]
    result=assess_methods(rows,['text','ra','ocr'],'claim')
    assert result['status']=='UNCERTAINTY_RETAINED' and not result['release_eligible']
    assert {'MISSING_REQUIRED_METHOD','INSUFFICIENT_METHOD_FAMILIES'}<={f['kind'] for f in result['findings']}
    rows.append({'method_id':'ocr','family':'pixels','status':'AGREES','claim_hash':'old','evidence_hash':'hash','shared_dependencies':[]})
    assert any(f['kind']=='STALE_INPUT' for f in assess_methods(rows,['text','ocr'],'claim')['findings'])


def test_conclusion_skepticism_requires_correct_quantifier_and_complete_nonempty_models():
    assert conclusion_support([['a'],['b']],{'a':'p','b':'p'},True)['skeptical_conclusions']==['p']
    assert not conclusion_support([],{'a':'p'},True)['skeptical_conclusions']
    assert not conclusion_support([['a']],{'a':'p'},False)['skeptical_conclusions']


def test_repair_actions_execute_to_budget_and_resume_without_dispatch(tmp_path):
    calls=[];p=tmp_path/'issue.json';make=lambda name:(name,lambda:calls.append(name) or {'text':'disputed'})
    actions=[make(n) for n in ('a','b','c')]
    result=Investigation(p,{'source':'v1'},2).run(actions)
    assert calls==['a','b'] and result['budget_exhausted'] and result['status']=='UNCERTAINTY_RETAINED'
    Investigation(p,{'source':'v1'},2).run(actions);assert calls==['a','b']
    with pytest.raises(ValueError):Investigation(p,{'source':'v2'},2).run(actions)
    with pytest.raises(ValueError):Investigation(p,{'source':'v1'},3).run(actions)


def test_crash_and_exception_consume_reserved_action_and_do_not_resolve(tmp_path):
    p=tmp_path/'issue.json'
    def crash():raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):Investigation(p,{},1).run([('crash',crash)])
    data=Investigation(p,{},1).run([('another',lambda:pytest.fail('over budget'))])
    assert data['actions'][0]['status']=='INTERRUPTED' and data['budget_exhausted']
    def fail():raise RuntimeError('failed extraction')
    data=Investigation(tmp_path/'failed.json',{},1).run([('fail',fail)])
    assert data['actions'][0]['status']=='FAILED' and not data['release_eligible']


def test_changed_completed_action_and_over_budget_history_are_rejected(tmp_path):
    p=tmp_path/'issue.json';Investigation(p,{},1).run([('a',lambda:{'text':'original'})])
    data=json.loads(p.read_text());data['actions'][0]['result']['text']='changed';p.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='changed'):Investigation(p,{},1).run([])
    data['actions'].append(data['actions'][0]);p.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='history'):Investigation(p,{},1).run([])


def test_required_methods_cannot_silently_drop_unknown_status_or_duplicate_identity():
    row={'method_id':'m','family':'f','status':'UNKNOWN','claim_hash':'c','evidence_hash':'h','shared_dependencies':[]}
    with pytest.raises(ValueError):assess_methods([row],['m'],'c')
    row['status']='AGREES'
    with pytest.raises(ValueError):assess_methods([row,row],['m'],'c')


def master():
    p=Path(__file__).resolve().parents[2]/'scripts/run_assurance_master.py'
    spec=importlib.util.spec_from_file_location('assurance_master_test',p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def test_allowlist_rejects_arbitrary_module_script_and_extra_install_args(tmp_path):
    m=master();attempt=m.OUT/'M1/attempt-test'
    good=m.commands('M1',attempt,True)[0][1]
    assert m.allowed(good,'M1',attempt,True)
    assert not m.allowed(good+['--arbitrary'],'M1',attempt,True)
    assert not m.allowed([str(m.PY),'-m','pip','install','anything'],'M1',attempt,True)
    assert not m.allowed(good,'M1',attempt,False)


def test_master_failure_requires_executed_repair_and_refresh(tmp_path,monkeypatch):
    m=master();monkeypatch.setattr(m,'OUT',tmp_path/'out');monkeypatch.setattr(m,'protect',lambda s:None)
    monkeypatch.setattr(m,'inputs',lambda phase:{'files':{},'digest':'fixed'})
    monkeypatch.setattr(m,'invoke',lambda argv,log,timeout:log.write_text('injected failure') and 1)
    s=m.state()
    with pytest.raises(ValueError):m.run_phase('M0',s)
    assert s['phases']['M0']['status']=='REPAIR_REQUIRED'
    with pytest.raises(ValueError,match='repair'):m.run_phase('M0',s)
    assert (m.OUT/'M0/repair-request.json').exists()


def test_completed_phase_refreshes_successor_without_overwriting(tmp_path,monkeypatch):
    m=master();monkeypatch.setattr(m,'OUT',tmp_path/'out');monkeypatch.setattr(m,'protect',lambda s:None)
    monkeypatch.setattr(m,'inputs',lambda phase:{'files':{},'digest':'fixed'})
    def ok(argv,log,timeout):log.write_text('success');return 0
    monkeypatch.setattr(m,'invoke',ok);s=m.state();m.run_phase('M0',s)
    assert s['phases']['M0']['status']=='PASSED' and (m.OUT/'M1/next-plan.json').exists()
    with pytest.raises(ValueError,match='overwritten'):m.run_phase('M0',s)


def test_changed_material_input_invalidates_accepted_successors_preserving_attempts(tmp_path,monkeypatch):
    m=master();monkeypatch.setattr(m,'OUT',tmp_path/'out');s=m.state()
    evidence=tmp_path/'accepted.json';evidence.write_text(json.dumps({'material_inputs':{'source':'old'}}))
    for phase in ('M0','M1'):
        s['phases'][phase]={'status':'PASSED','attempts':[{'path':str(evidence)}],'repairs':[]}
    monkeypatch.setattr(m,'material_inputs',lambda phase:{'source':'new'})
    monkeypatch.setattr(m,'refresh',lambda phase,state:None)
    assert m.invalidate_stale(s)=='M0'
    assert s['phases']['M0']['status']==s['phases']['M1']['status']=='STALE'
    assert len(s['phases']['M1']['attempts'])==1


def test_final_report_requires_completed_current_evidence_and_includes_m5(tmp_path,monkeypatch):
    m=master();monkeypatch.setattr(m,'OUT',tmp_path);s=m.state()
    monkeypatch.setattr(m,'protect',lambda state:None)
    monkeypatch.setattr(m,'material_inputs',lambda phase:{'source':'current'})
    with pytest.raises(ValueError,match='incomplete'):m.finalize(s)
    for phase in m.PHASES:
        path=tmp_path/phase/'run-manifest.json'
        m.write(path,{'status':'PASSED','material_inputs':{'source':'current'}})
        s['phases'][phase].update(status='PASSED',attempts=[{'path':str(path),'sha256':m.sha(path)}])
    m.write(tmp_path/'state.json',s)
    m.write(tmp_path/'M5/summary/result.json',{
        'engineering_status':'PASS','phase_evidence':{},'assurance_status':'UNCERTAINTY_RETAINED',
        'unresolved_issues':[{'issue_id':'unresolved-exception'}],
        'legal_correctness_established':False,'release_eligible':False,
        'next_phase_plan':{'refresh_from':{}}})
    m.finalize(s);result=m.read(tmp_path/'final-report.json')
    assert set(result['phase_evidence'])==set(m.PHASES)
    assert result['phase_evidence']['M5']['sha256']==m.sha(tmp_path/'M5/run-manifest.json')
    assert result['unresolved_issues']==[{'issue_id':'unresolved-exception'}]
    assert not result['legal_correctness_established'] and not result['release_eligible']
    assert set(m.read(tmp_path/'next-phase-plan.json')['refresh_from'])==set(m.PHASES)
    monkeypatch.setattr(m,'material_inputs',lambda phase:{'source':'changed'})
    with pytest.raises(ValueError,match='stale phase'):m.finalize(s)
