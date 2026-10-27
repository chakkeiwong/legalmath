"""Replay the settled context census against old and installed validators."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import importlib.util
import json
import os
import sys
import time
os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import legal_optional_quote_validation as repair
from scripts import legal_integration_phased_live as live,legal_integration_campaign as campaign
from scripts.legal_mission_execution import read,save,ref,require,digest
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import context_disposition as installed
from legalmath.interpretation.assurance.phased.source_review import assignments

class Captured(BaseException):pass

def main():
    started=time.monotonic()
    inputs=[(ref(ROOT,p),read(p)) for p in sorted((ROOT/repair.SOURCE/'arms/p14/baseline').glob('context-review-*.json'))]
    require(len(inputs)==38,'Settled census changed')
    installation=read(ROOT/repair.HERE/'installation.json')
    for pointer in installation['installed']:repair.verify(ROOT,pointer)
    baseline_path=repair.HERE/'before'/repair.PRODUCT
    baseline_hash=ref(ROOT,baseline_path)
    tag=digest(dict(inputs=[p for p,_ in inputs],implementation=installation['installed'],
        script=ref(ROOT,Path(__file__))))[:16]
    folder=repair.HERE/'deployment-replay'/tag
    require(not (ROOT/folder/'result.json').exists(),'Completed replay already exists')
    save(ROOT/folder/'input-snapshot.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),
        inputs=[p for p,_ in inputs],baseline=baseline_hash,installation=ref(ROOT,repair.HERE/'installation.json')))
    program=deepcopy(read(ROOT/live.PROGRAM))
    selected=program['review_repair'].get('optional_quote_validation',program['review_repair']['deployment'])
    selected.update(runtime=str(folder/'runtime'),arm_checkpoints=read(ROOT/repair.HERE/'seed.json')['arm_checkpoints'])
    service=campaign.provider()
    def forbidden(*args,**kwargs):raise AssertionError('Offline replay attempted provider dispatch')
    service.complete=service.check_service=forbidden
    service.check=lambda:read(ROOT/live.BASE/'live-calls.json')
    captured={}
    def capture(product,qid,question,answer,details,**kwargs):
        captured.update(product=product,qid=qid,answer=answer)
        raise Captured()
    selected_read=lambda path:program if Path(path)==ROOT/live.PROGRAM else read(path)
    print(json.dumps(dict(replaying=len(inputs),provider_calls=0)),flush=True)
    with patch.object(live,'read',selected_read),patch.object(live,'phase_admit',lambda owner:lambda name,count:dict(offline=True)),patch.object(PhasedProduct,'audit_answer',capture):
        try:live.product_route('p14',None,service)
        except Captured:pass
    require(captured.get('qid')=='p14','Wrong product entry')
    product,answer=captured['product'],captured['answer']
    require(product.directory.is_relative_to(ROOT/folder),'Offline route escaped its directory')
    spec=importlib.util.spec_from_file_location('legalmath.interpretation.assurance.phased.pre_quote_validator',ROOT/baseline_path)
    baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
    table={r['id']:r for r in assignments(product,'p14',product.current_dependencies)}
    rows=[]
    for pointer,receipt in inputs:
        repair.verify(ROOT,pointer)
        require(table[receipt['item']['id']]==receipt['item'] and digest(answer)==receipt['answer_hash'],'Changed assignment or answer')
        result=receipt['result'];row=dict(assignment=receipt['item']['id'],receipt=pointer,stored_status=result['status'],stored_verdict=result.get('value',{}).get('verdict'))
        if result['status']=='VALIDATED':
            args=(product,'p14',result['value'],answer,receipt['item'],receipt['prior_needs'],
                [product.route.records[rid] for rid in receipt['delivered_ids']],receipt['source_delivery_failures'])
            for name,module in [('baseline',baseline),('installed',installed)]:
                try:module.validate(*args);row[name]=dict(status='VALIDATED')
                except Exception as exc:row[name]=dict(status='FAILED',error=getattr(exc,'code',type(exc).__name__),reason=str(getattr(exc,'details',None) or exc))
        else:row['retained_failure']=dict(error=result.get('error'),reason=result.get('reason'))
        rows.append(row)
    journal=product.directory/'calls/dispatch.json'
    require(not journal.exists() or not read(journal)['calls'],'Offline replay reserved a call')
    for pointer in installation['installed']:repair.verify(ROOT,pointer)
    rejected=[r for r in rows if r.get('installed',{}).get('status')=='FAILED']
    old_rejected=[r for r in rows if r.get('baseline',{}).get('status')=='FAILED']
    require(len(rejected)==1 and rejected[0]['assignment']=='dependency-4712f423197e017ddf84010e'
        and rejected[0]['installed']['error']=='E_SCHEMA' and not old_rejected,'Unexpected deployment replay difference')
    outcome=dict(at_utc=datetime.now(timezone.utc).isoformat(),verdict='PASS',receipt_count=len(rows),
        validated_under_installed=sum(r.get('installed',{}).get('status')=='VALIDATED' for r in rows),
        newly_failed=rejected,retained_failed=[r for r in rows if r['stored_status']=='FAILED'],
        provider_calls=0,originals_unchanged=True,installed_files_unchanged=True,legal_acceptance=False,
        input_snapshot=ref(ROOT,folder/'input-snapshot.json'),wall_seconds=time.monotonic()-started,rows=rows)
    save(ROOT/folder/'result.json',outcome)
    print(json.dumps({k:v for k,v in outcome.items() if k!='rows'}|{'result':str(folder/'result.json')},indent=2),flush=True)

if __name__=='__main__':main()
