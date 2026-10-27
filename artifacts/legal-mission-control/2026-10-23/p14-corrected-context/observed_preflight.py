"""Check the observed contracts through production wiring without provider calls."""
from copy import deepcopy
from collections import Counter
from pathlib import Path
from unittest.mock import patch
import os
import sys
import time
os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path(__file__).resolve().parents[4]
CANDIDATE=Path('/tmp/legalmath-p14-corrected-context-20261023')
sys.path[:0]=[str(CANDIDATE/'src'),str(CANDIDATE),str(ROOT)]
import scripts
scripts.__path__=[str(CANDIDATE/'scripts'),*list(scripts.__path__)]
from scripts import legal_integration_phased_live as live,legal_integration_campaign as campaign
from scripts import legal_review_context_isolation as isolation
from scripts.legal_mission_execution import read,save,ref,require,digest
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import context_disposition,capacity_checkpoint
from legalmath.interpretation.assurance.phased.source_review import assignments
class Captured(BaseException): pass
started=time.monotonic()
seed=read(ROOT/isolation.HERE/'seed.json')
tag=digest(dict(seed=seed,code={p:(CANDIDATE/p).read_bytes().hex() for p in isolation.CHANGED}))[:16]
program=deepcopy(read(ROOT/live.PROGRAM))
program['review_repair']['deployment'].update(runtime=str(isolation.HERE/'offline'/tag),
    arm_checkpoints=seed['arm_checkpoints'])
live.ROOT=campaign.ROOT=ROOT
service=campaign.provider()
def forbidden(*a,**k): raise AssertionError('Offline preflight attempted provider dispatch')
service.complete=service.check_service=forbidden
service.check=lambda:read(ROOT/live.BASE/'live-calls.json')
captured={}
def audit(product,qid,question,answer,details,**kwargs):
    captured.update(product=product,qid=qid,question=question,answer=answer,details=details)
    raise Captured()
selected=lambda path:program if Path(path)==ROOT/live.PROGRAM else read(path)
with patch.object(live,'read',selected),patch.object(live,'phase_admit',lambda owner:
        lambda name,count:dict(offline=True,owner=owner,name=name,count=count)),patch.object(PhasedProduct,'audit_answer',audit):
    try: live.product_route('p14',None,service)
    except Captured: pass
require(captured.get('qid')=='p14','Product entry did not reach the required answer')
p=captured['product']; answer=captured['answer']; question=captured['question']
source=ROOT/isolation.SOURCE/'arms/p14/baseline'
population=read(source/'contextual-group-review-p14.json')['reviews']
assessed,warranted,settled=p.review_warrants('p14',question,dict(value=answer),population,captured['details'])
require(len(assessed)==34 and all(a['result']['status']=='VALIDATED' for a in assessed),
    'Retained warrant replay failed')
excluded=sum(len(a.get('not_answer_corrections',[])) for a in assessed)
require(excluded==7 and all(a['result']['provenance']['new_provider_calls']==0 for a in assessed),
    'Retained warrant exclusion or reuse differs')
require(all(r.get('issue_assessments') and len(r['issues'])==len(r['issue_assessments']) for r in warranted),
    'Correction lost full assessment reasons')
old=source/'calls/audit-context-disposition-p14-f27ee3e41f98d678fc3e4711'
prior=read(old/'request.json'); identity=prior['required_considered'][0]
item=next(r for r in assignments(p,'p14',p.current_dependencies) if r['id']==identity)
initial=next(r for r in population if r['value']['considered']==[identity])
request,shape,needs,receipts,failures=context_disposition.prepare(p,'p14',question,answer,item,initial)
require(not failures and request['payload']['answer']==prior['payload']['answer'],
    'Context source delivery or answer changed')
require(request['records']==prior['records'] and request['required_considered']==prior['required_considered'],
    'Context sources or assignment changed')
call=dict(key=old.name,request=request,schema=shape,validate=lambda value:
    context_disposition.validate(p,'p14',value,answer,item,needs,request['records'],failures))
prepared=p.prepare_calls([call])[0]
require(capacity_checkpoint.retained(p,prepared) is None,'Changed context contract reused failed response')
measure=p.dispatch.measure(request,shape)
failed=read(old/'result.json')
require(failed['status']=='FAILED' and failed['reason']=='Ambiguous numbered citation',
    'Historical context failure changed')
journal=p.directory/'calls/dispatch.json'
require(not journal.exists() or not read(journal)['calls'],'Offline preflight reserved calls')
result=dict(verdict='PASS',provider_calls=0,legal_acceptance=False,answer_hash=digest(answer),
    retained_warrants=len(assessed),excluded_issue_occurrences=excluded,
    correction_issues=sum(len(r['issues']) for r in warranted),correction_reviews=len(warranted),
    warrant_dispositions=dict(Counter(d['disposition'] for a in assessed for d in a['result']['value']['decisions'])),
    full_reasons_preserved=True,changed_context_requires_new_call=True,
    source_and_answer_unchanged=True,measurement=measure,
    historical_failed_context=ref(ROOT,old/'result.json'),
    warrant_replay=ref(ROOT,p.directory/'correction-p14-warrants.json'),
    seconds=time.monotonic()-started,devices='CPU; CUDA_VISIBLE_DEVICES=-1')
save(ROOT/isolation.HERE/'observed-preflight.json',result)
print(result,flush=True)
