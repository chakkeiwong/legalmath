import pytest
from legalmath.errors import LegalMathError

def test_root_inherited_and_auth_revision(svc,run,proposal):
    rid=run['run_id'];c=svc.propose('author','p',rid,proposal)
    issue=svc.raise_issue('author','issue',rid,'DEFINITION',['p10'],[c['candidate_id']],'Which type?','Two readings')
    child=svc.raise_issue('author','child',rid,'DEFINITION',['p10'],[c['candidate_id']],'Risk class?','Narrower question',issue['issue_id'])
    assert child['root_id']==issue['root_id']
    args=(rid,issue['issue_id'],0,c['candidate_id'],'RESOLVE_MEANING','Scoped decision','Alternative rejected because context',['p10'])
    with pytest.raises(LegalMathError): svc.decide_issue('author','forged',*args)
    decision=svc.decide_issue('meaning','decision',*args)
    assert decision['authority']=='LOCAL_SYNTHETIC'
    with pytest.raises(LegalMathError): svc.decide_issue('meaning','stale',*args)
    issues=svc.read('meaning',rid)['records']['issue']
    assert issues[0]['resolution_state']=='RESOLVED_ADJUDICATION'
    assert issues[1]['resolution_state']=='UNRESOLVED'

def test_missing_dependency_cannot_be_voted_away(svc,packet,proposal):
    packet['source_key']='synthetic.missing-dependency'
    packet['dependencies']=[{'dependency_id':'code','source_hash':None}]
    run=svc.create('author','r2',packet);proposal['source_packet_hash']=run['source_packet_hash']
    c=svc.propose('author','p',run['run_id'],proposal)
    with pytest.raises(LegalMathError): svc.decide_issue('meaning','bad',run['run_id'],run['issue_ids'][0],0,c['candidate_id'],'RESOLVE_MEANING','Agree','Agree',['p10'])

def test_adjudication_retains_validated_evidence(svc,run,proposal):
    from legalmath.interpretation.reports import Reports
    rid=run['run_id'];c=svc.propose('author','p',rid,proposal)
    issue=svc.raise_issue('author','issue',rid,'DEFINITION',['p10'],[c['candidate_id']],'Definition','Ambiguity')
    decision=svc.decide_issue('meaning','resolve',rid,issue['issue_id'],0,c['candidate_id'],'RESOLVE_MEANING','Scoped interpretation','Address alternative',['p10'])
    records=svc.read('meaning',rid)['records'];e=records['evidence'][0]
    assert e['kind']=='HUMAN_ADJUDICATION' and e['review_decision_id']==decision['decision_id']
    assert records['issue'][0]['resolution_evidence_refs']==[e['evidence_id']]
    Reports(svc).finish(rid,'HUMAN_REQUIRED');Reports(svc).verify('meaning',rid)
