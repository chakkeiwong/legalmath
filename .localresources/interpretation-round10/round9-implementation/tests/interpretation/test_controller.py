import copy
from legalmath.interpretation.controller import Controller
from legalmath.interpretation.reports import Reports
from legalmath.interpretation.service import later

def config(proposal):
    return {r:{'adapter':'scripted','proposals':[] if r=='inventory' else [copy.deepcopy(proposal)]} for r in ('inventory','normative','controlled-language','alternatives')}

def test_automatic_structural_repair_preserves_initial_readings(svc,run,proposal):
    proposal['family_ids']=['literal','alternative'];ctl=Controller(svc)
    repair={**proposal,'source_unit_ids':['p10','fn1'],'controlled_language':'Prior investment or product type route','revision_reason':'Include omitted footnote'}
    ctl.configure('author','cfg',run['run_id'],config(proposal),[{'adapter':'scripted','proposals':[repair]}])
    report=ctl.drive(run['run_id']);records=svc.read('meaning',run['run_id'])['records']
    assert report['actions_issued']==5
    assert len(records['candidate'])==4 and records['candidate'][0]['source_unit_ids']==['p10']
    omission=[i for i in records['issue'] if i['kind']=='SOURCE_COVERAGE'][0]
    assert omission['resolution_state']=='RESOLVED_EVIDENCE'
    assert not records['evidence'][0]['legal_source_commitment_resolved']
    assert report['run_status']=='BLOCKED_UNRESOLVED' and 'java-check' in report['incomplete_mandatory_checks']
    Reports(svc).verify('meaning',run['run_id'])

def test_persistent_ambiguity_and_unanimous_omission(svc,run,proposal):
    proposal['assumptions']=[dict(assumption_id='type',statement='What is product type?',provenance_refs=[],status='DISPUTED')]
    ctl=Controller(svc);ctl.configure('author','cfg',run['run_id'],config(proposal))
    report=ctl.drive(run['run_id'])
    assert report['run_status']=='BLOCKED_UNRESOLVED' and report['material_unresolved_issue_ids']
    assert len(svc.read('meaning',run['run_id'])['records']['candidate'])==3

def test_malformed_member_and_deadline_reports(svc,run,proposal):
    members=config(proposal);members['alternatives']['adapter']='malformed'
    ctl=Controller(svc);ctl.configure('author','cfg',run['run_id'],members)
    report=ctl.drive(run['run_id'])
    assert report['missing_initial_roles']==['alternatives']
    assert any(i['kind']=='MEMBER_FAILURE' for i in svc.read('meaning',run['run_id'])['records']['issue'])

def test_deadline_before_initial_is_complete_report(svc,run,proposal):
    ctl=Controller(svc);ctl.configure('author','cfg',run['run_id'],config(proposal))
    svc.clock=lambda:later(run['deadline'],1)
    report=ctl.drive(run['run_id'])
    assert report['processing_stop']=='DEADLINE' and report['actions_issued']==0 and len(report['missing_initial_roles'])==4

def test_cancel_is_durable_and_report_idempotent(svc,run):
    reports=Reports(svc);reports.cancel('author','cancel',run['run_id'])
    first=reports.finish(run['run_id'],'NO_PROGRESS');second=reports.finish(run['run_id'],'INTEGRITY_FAILURE')
    assert first==second and first['run_status']=='CANCELLED'

def test_breadth_reserves_a_slot_for_minority_family(svc,packet,proposal):
    from legalmath.interpretation.contracts import reference_policy
    run=svc.create('author','breadth',packet,{**reference_policy(),'max_candidates':2})
    proposal['source_packet_hash']=run['source_packet_hash'];cfg=config(proposal)
    cfg['normative']['proposals']=[copy.deepcopy(proposal),copy.deepcopy(proposal)]
    cfg['alternatives']['proposals'][0]['family_ids']=['alternative']
    ctl=Controller(svc);ctl.configure('author','cfg',run['run_id'],cfg);ctl.drive(run['run_id'])
    records=svc.read('meaning',run['run_id'])['records']
    assert {f for c in records['candidate'] for f in c['family_ids']}=={'literal','alternative'}
    assert records['frontier'] and any(i['kind']=='SEARCH_INCOMPLETE' for i in records['issue'])


def test_successor_carries_unresolved_questions(svc,run,packet,proposal):
    s=svc;rid=run['run_id'];c=s.propose('author','p',rid,proposal)
    original=s.raise_issue('author','q',rid,'DEFINITION',['p10'],[c['candidate_id']],'Which product type?','Classification is unsettled')
    Reports(s).finish(rid,'HUMAN_REQUIRED')
    successor=s.create('author','next',packet,predecessor=rid)
    records=s.read('meaning',successor['run_id'])['records']
    assert records['issue'][0]['root_id']==original['root_id']
    assert records['issue'][0]['resolution_state']=='UNRESOLVED'
    assert records['inherited-issue'][0]['predecessor_issue_id']==original['issue_id']
