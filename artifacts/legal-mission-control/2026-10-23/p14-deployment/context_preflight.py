"""Prepare every original unresolved decision through the production product, offline."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json
import os
import sys
import time
ROOT=Path('/home/chakwong/python/legalmath')
CANDIDATE=Path('/tmp/legalmath-p14-repair-20261023')
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(CANDIDATE/'src'),str(CANDIDATE)]
from scripts import legal_integration_phased_live as live, legal_integration_campaign as campaign
from scripts.legal_mission_execution import read,save,ref
from scripts.legal_review_deployment import HERE
from legalmath.canonical import digest
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import context_disposition, review_contract, service_prerequisite
from legalmath.interpretation.assurance.phased.source_review import assignments

def runtime_tag(checkpoints):
    files = read(ROOT/HERE/'implementation-files.json')
    code = {p:(CANDIDATE/p).read_bytes().hex() for p in files if (CANDIDATE/p).is_file()}
    return digest(dict(checkpoints=checkpoints, code=code,
        diagnostic=Path(__file__).read_bytes().hex()))[:16]

class CapturedProduct(BaseException): pass


def capture():
    live.ROOT=campaign.ROOT=ROOT
    original=read(ROOT/live.PROGRAM)
    program=deepcopy(original)
    checkpoints=read(ROOT/HERE/'checkpoints.json')['arm_checkpoints']
    program['review_repair'].update(review_assignment_profile=review_contract.PROFILE,
        service_prerequisite_profile=service_prerequisite.PROFILE,
        deployment=dict(runtime=str(HERE/'offline-context-preflight'/runtime_tag(checkpoints)),
            arm_checkpoints=checkpoints))
    service=campaign.provider()
    captured={}
    def forbidden(*a,**k): raise AssertionError('Offline analysis attempted provider dispatch')
    service.complete=service.check_service=forbidden
    def audit(product,qid,question,answer,details,**kwargs):
        captured.update(product=product,qid=qid,question=question,answer=answer,details=details)
        raise CapturedProduct()
    selected=lambda path:program if Path(path)==ROOT/live.PROGRAM else read(path)
    with patch.object(live,'read',selected),patch.object(live,'phase_admit',lambda owner:
            lambda name,count:dict(offline=True,owner=owner,name=name,count=count)),patch.object(PhasedProduct,'audit_answer',audit):
        try: live.product_route('p14',None,service)
        except CapturedProduct: pass
    assert captured and captured['qid']=='p14'
    return captured


def run():
    start=time.monotonic()
    captured=capture()
    product=captured['product']; answer=captured['answer']; question=captured['question']
    table={r['id']:r for r in assignments(product,'p14',product.current_dependencies)}
    original=read(ROOT/HERE/'individual-reviews.json')
    population=read(ROOT/original['population']['path'])
    rows=[];examples={};calls=0
    for review in population['reviews']:
        if review['status']!='VALIDATED' or review['value']['verdict']!='UNRESOLVED': continue
        identity,=review['value']['considered']
        item=table[identity]
        request,shape,needs,receipts,failures=context_disposition.prepare(product,'p14',question,answer,item,review)
        row=dict(assignment_id=identity,original_decision_hash=digest(review['value']),
            request_hash=digest(request),schema_hash=digest(shape),routes=[n['route'] for n in needs],
            source_delivery_failures=failures,delivered_record_ids=[r['id'] for r in request['records']],
            source_selection=receipts)
        try: row['measurement']=product.dispatch.measure(request,shape)
        except Exception as exc: row['capacity_failure']=product.failure(exc)
        for route in row['routes']:
            if route not in examples:
                path=HERE/'context-preflight-examples'/route
                save(ROOT/path/'request.json',request);save(ROOT/path/'schema.json',shape)
                examples[route]=dict(request=ref(ROOT,path/'request.json'),schema=ref(ROOT,path/'schema.json'))
        rows.append(row)
        if len(rows)%100==0: print(json.dumps(dict(prepared=len(rows))),flush=True)
    assert len(rows)==672 and len({r['assignment_id'] for r in rows})==672
    path=HERE/'context-preflight-population.json'
    save(ROOT/path,rows)
    result=dict(verdict='PASS' if not any(r.get('capacity_failure') for r in rows) else 'CAPACITY_BLOCKS',
        assignments=len(rows), routes=dict(Counter(k for r in rows for k in r['routes'])),
        preparation_failures=sum(bool(r['source_delivery_failures']) for r in rows),
        capacity_failures=[r for r in rows if r.get('capacity_failure')],
        provider_calls=calls,legal_acceptance=False,original_verdicts_unchanged=True,
        answer_hash=digest(answer),population=ref(ROOT,path),examples=examples,
        seconds=time.monotonic()-start,devices='CPU; CUDA_VISIBLE_DEVICES=-1')
    save(ROOT/HERE/'context-preflight.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__': run()
