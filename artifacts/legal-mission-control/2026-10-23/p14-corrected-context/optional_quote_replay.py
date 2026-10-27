"""Revalidate a fixed live receipt snapshot offline; preserve all originals."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import hashlib
import importlib.util
import json
import os
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from scripts import legal_integration_phased_live as live, legal_integration_campaign as campaign
from scripts import legal_review_context_isolation as isolation
from scripts.legal_mission_execution import read, save, ref, require, digest
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import context_disposition as installed
from legalmath.interpretation.assurance.phased.source_review import assignments

class Captured(BaseException):
    pass

HERE = isolation.HERE
SOURCE = ROOT/isolation.RUNTIME/'arms/p14/baseline'
started = time.monotonic()
inputs = [(ref(ROOT,path),read(path)) for path in sorted(SOURCE.glob('context-review-*.json'))]
require(inputs, 'No completed context receipts')
seed = read(ROOT/HERE/'seed.json')
candidate_path = HERE/'optional-quote-candidate/context_disposition.py'
candidate_hash = ref(ROOT,candidate_path)
tag = digest(dict(candidate=candidate_hash,inputs=[r[0] for r in inputs],
    script=Path(__file__).read_bytes().hex()))[:16]
folder = HERE/'optional-quote-replay'/tag
require(not (ROOT/folder/'result.json').exists(), 'Completed replay exists; inspect it')
save(ROOT/folder/'input-snapshot.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),
    inputs=[pointer for pointer,_ in inputs],candidate=candidate_hash,provider_calls=0))
program = deepcopy(read(ROOT/live.PROGRAM))
program['review_repair']['deployment'].update(runtime=str(folder/'runtime'),
    arm_checkpoints=seed['arm_checkpoints'])
live.ROOT = campaign.ROOT = ROOT
service = campaign.provider()
def forbidden(*args,**kwargs):
    raise AssertionError('Offline replay attempted provider dispatch')
service.complete = service.check_service = forbidden
service.check = lambda: read(ROOT/live.BASE/'live-calls.json')
captured = {}
def stop_at_audit(product,qid,question,answer,details,**kwargs):
    captured.update(product=product,qid=qid,question=question,answer=answer,details=details)
    raise Captured()
selected = lambda path: program if Path(path)==ROOT/live.PROGRAM else read(path)
print(dict(snapshot_receipts=len(inputs),provider_calls=0),flush=True)
with (patch.object(live,'read',selected),patch.object(live,'phase_admit',
    lambda owner:lambda name,count:dict(offline=True,owner=owner,name=name,count=count)),
    patch.object(PhasedProduct,'audit_answer',stop_at_audit)):
    try:
        live.product_route('p14',None,service)
    except Captured:
        pass
require(captured.get('qid')=='p14','Wrong product entry')
p=captured['product']; answer=captured['answer']
require(p.directory.is_relative_to(ROOT/folder),'Replay escaped offline directory')
name='legalmath.interpretation.assurance.phased.optional_quote_replay_candidate'
spec=importlib.util.spec_from_file_location(name,ROOT/candidate_path)
candidate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)
table={r['id']:r for r in assignments(p,'p14',p.current_dependencies)}
rows=[]
for pointer,retained in inputs:
    require(ref(ROOT,ROOT/pointer['path'])==pointer,'Receipt changed during offline replay')
    require(table[retained['item']['id']]==retained['item'] and
        digest(answer)==retained['answer_hash'],'Changed original answer/assignment')
    result=retained['result']
    row=dict(assignment=retained['item']['id'],receipt=pointer,stored_status=result['status'],
        stored_verdict=result.get('value',{}).get('verdict'))
    if result['status']=='VALIDATED':
        records=[p.route.records[rid] for rid in retained['delivered_ids']]
        arguments=(p,'p14',result['value'],answer,retained['item'],retained['prior_needs'],
            records,retained['source_delivery_failures'])
        for label,module in [('installed',installed),('candidate',candidate)]:
            try:
                module.validate(*arguments)
                row[label]=dict(status='VALIDATED')
            except Exception as exc:
                row[label]=dict(status='FAILED',error=type(exc).__name__,
                    reason=str(getattr(exc,'details',None) or exc))
    rows.append(row)
journal=p.directory/'calls/dispatch.json'
require(not journal.exists() or not read(journal)['calls'],'Replay reserved a call')
installation=read(ROOT/HERE/'installation-manifest.json')
require(all(ref(ROOT,r['path'])==r for r in installation['installed']),'Installed files changed')
require(ref(ROOT,candidate_path)==candidate_hash,'Candidate changed after testing')
out=dict(at_utc=datetime.now(timezone.utc).isoformat(),receipt_count=len(rows),
    installed_rejected=[r for r in rows if r.get('installed',{}).get('status')=='FAILED'],
    candidate_rejected=[r for r in rows if r.get('candidate',{}).get('status')=='FAILED'],
    input_snapshot=ref(ROOT,folder/'input-snapshot.json'),candidate=candidate_hash,
    provider_calls=0,originals_unchanged=True,installed_files_unchanged=True,
    deployed=False,legal_acceptance=False,rows=rows,wall_seconds=time.monotonic()-started,
    limits='Stricter structural replay, not a new legal judgment. New live receipts after this snapshot remain outside the replay.')
save(ROOT/folder/'result.json',out)
print(json.dumps({k:v for k,v in out.items() if k!='rows'}|{'result':str(folder/'result.json')},indent=2),flush=True)
