"""Prepare all newly unresolved assignments; never dispatch to a provider."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import os
import sys
import time
os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import legal_integration_phased_live as live,legal_integration_campaign as campaign
from scripts import legal_review_context_isolation as isolation
from scripts.legal_mission_execution import read,save,ref,require,digest
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import context_disposition
from legalmath.interpretation.assurance.phased.source_review import assignments
class Captured(BaseException): pass
start=time.monotonic()
seed=read(ROOT/isolation.HERE/'seed.json')
program=deepcopy(read(ROOT/live.PROGRAM))
tag=digest(dict(seed=seed,script=Path(__file__).read_bytes().hex()))[:16]
program['review_repair']['deployment'].update(runtime=str(isolation.HERE/'delta-preflight'/tag),
    arm_checkpoints=seed['arm_checkpoints'])
live.ROOT=campaign.ROOT=ROOT
service=campaign.provider()
def forbidden(*a,**k): raise AssertionError('Offline preparation attempted provider dispatch')
service.complete=service.check_service=forbidden
service.check=lambda:read(ROOT/live.BASE/'live-calls.json')
captured={}
def audit(product,qid,question,answer,details,**kwargs):
    captured.update(product=product,qid=qid,question=question,answer=answer)
    raise Captured()
selected=lambda path:program if Path(path)==ROOT/live.PROGRAM else read(path)
with patch.object(live,'read',selected),patch.object(live,'phase_admit',lambda owner:
        lambda name,count:dict(offline=True,owner=owner,name=name,count=count)),patch.object(PhasedProduct,'audit_answer',audit):
    try: live.product_route('p14',None,service)
    except Captured: pass
require(captured.get('qid')=='p14','Wrong product entry')
p=captured['product']; answer=captured['answer']; question=captured['question']
table={r['id']:r for r in assignments(p,'p14',p.current_dependencies)}
delta=read(ROOT/isolation.HERE/'continuation-decisions.json')
population=read(ROOT/isolation.SOURCE/'arms/p14/baseline/contextual-group-review-p14.json')['reviews']
rows=[]
for row in delta:
    if row['decision']['verdict']!='UNRESOLVED': continue
    review=population[row['index']]
    require(review['value']==row['decision'],'New decision alignment changed')
    item=table[row['assignment']]
    try:
        request,shape,needs,receipts,failures=context_disposition.prepare(p,'p14',question,answer,item,review)
        result=dict(index=row['index'],assignment=row['assignment'],source_delivery_failures=failures,
            routes=[r['route'] for r in needs],source_selection=receipts,
            request_hash=digest(request),schema_hash=digest(shape),
            measurement=p.dispatch.measure(request,shape))
    except Exception as exc:
        result=dict(index=row['index'],assignment=row['assignment'],failure=p.failure(exc))
    rows.append(result)
    print(dict(prepared=len(rows),index=row['index'],failed=bool(result.get('failure') or result.get('source_delivery_failures'))),flush=True)
require(len(rows)==24,'Lost new unresolved assignment')
save(ROOT/isolation.HERE/'continuation-preflight-population.json',rows)
journal=p.directory/'calls/dispatch.json'
require(not journal.exists() or not read(journal)['calls'],'Offline diagnostic reserved a call')
result=dict(verdict='PASS' if not any(r.get('failure') or r.get('source_delivery_failures') for r in rows) else 'BLOCKS_FOUND',
    assignments=24,provider_calls=0,legal_acceptance=False,
    failures=[r for r in rows if r.get('failure') or r.get('source_delivery_failures')],
    maximum_bytes=max((r['measurement']['bytes'] for r in rows if 'measurement' in r),default=0),
    maximum_tokens=max((r['measurement']['local_tokens'] for r in rows if 'measurement' in r),default=0),
    population=ref(ROOT,isolation.HERE/'continuation-preflight-population.json'),seconds=time.monotonic()-start)
save(ROOT/isolation.HERE/'continuation-preflight.json',result)
print(result,flush=True)
