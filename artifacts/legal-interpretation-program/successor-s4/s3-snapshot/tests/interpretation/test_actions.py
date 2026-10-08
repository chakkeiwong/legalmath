from concurrent.futures import ThreadPoolExecutor
import pytest
from legalmath.interpretation.actions import Actions
from legalmath.interpretation.contracts import reference_policy
from legalmath.interpretation.service import later
from legalmath.errors import LegalMathError

def initialize(svc,run):
    with svc.db.transaction() as con:
        r=svc._run(con,run['run_id']);r['status']='RESOLVING';svc._save_run(con,r)
    return svc.raise_issue('author','issue',run['run_id'],'DEFINITION',[],[],'Type?','Undefined')

def test_last_slot_race(svc,packet):
    run=svc.create('author','c',packet,{**reference_policy(),'max_actions_total':4,'max_resolution_rounds':10,'max_actions_per_issue_root':10})
    issue=initialize(svc,run);a=Actions(svc)
    def reserve(n):
        try: return a.reserve(run['run_id'],kind='REPAIR',issue_id=issue['issue_id'],inputs=[run['source_packet_hash']],question=f'Question {n}')
        except LegalMathError: return None
    for n in range(3): assert reserve(n)
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(reserve,[3,4]))
    assert sum(r is not None for r in results)==1
    assert svc.read('author',run['run_id'])['run']['actions_issued']==4

def test_crash_after_dispatch_no_refund_and_stale_worker(svc,run):
    a=Actions(svc);rid=run['run_id'];at=run['created_at'];svc.clock=lambda:at
    action=a.reserve(rid,role='inventory',inputs=[run['source_packet_hash']])
    owned=a.claim(rid,action['action_id'],'worker.one');a.dispatch(rid,action['action_id'],'worker.one',owned['fencing_token'])
    svc.clock=lambda:later(at,31);a.recover(rid)
    assert not a.complete(rid,action['action_id'],'worker.one',owned['fencing_token'],{'ok':True})
    record=svc.read('author',rid)
    assert record['run']['actions_issued']==1 and record['records']['action'][0]['state']=='RESULT_UNKNOWN'
    assert len(record['records']['observation'])==1
    with pytest.raises(LegalMathError): a.claim(rid,action['action_id'],'worker.two')

def test_reserved_lease_reclaimed_with_fence(svc,run):
    a=Actions(svc);rid=run['run_id'];at=run['created_at'];svc.clock=lambda:at
    v=a.reserve(rid,role='inventory',inputs=[run['source_packet_hash']]);first=a.claim(rid,v['action_id'],'worker.one')
    svc.clock=lambda:later(at,31);second=a.claim(rid,v['action_id'],'worker.two')
    assert second['fencing_token']>first['fencing_token']
    with pytest.raises(LegalMathError): a.dispatch(rid,v['action_id'],'worker.one',first['fencing_token'])
