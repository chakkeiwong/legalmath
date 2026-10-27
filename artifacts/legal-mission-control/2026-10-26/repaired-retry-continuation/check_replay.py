from pathlib import Path
from types import SimpleNamespace
import sys,json,os
ROOT=Path('/home/chakwong/python/legalmath');TREE=Path('/tmp/legalmath-repaired-retry-continuation')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation'
os.environ['CUDA_VISIBLE_DEVICES']='-1';sys.path[:0]=[str(TREE/'src'),str(TREE)]
from legalmath.interpretation.assurance.phased.capacity_checkpoint import retained
from legalmath.interpretation.assurance.bounded_context import Limits
from legalmath.interpretation.assurance.integration_contract import evidence_file,read_evidence
from legalmath.canonical import digest
from scripts.legal_mission_execution import save
out=[]
for qid,arm in [('p14','baseline'),('gatecoin','baseline'),('gatecoin','bm25')]:
    path=WORK/'checkpoints'/qid/(arm+'.json');checkpoint=json.loads(path.read_text())
    product=SimpleNamespace(root=ROOT,capacity_checkpoint=evidence_file(path,ROOT),
        route=SimpleNamespace(input_hash=checkpoint['input_hash'],limits=Limits(),encode=lambda s:list(s.split())))
    for mode in ['VALIDATED','REVIEWED_FAILURE_RETRY','RETAINED_FAILURE']:
        rows=[(k,v) for k,v in checkpoint['calls'].items() if v['mode']==mode]
        if not rows:continue
        key,row=rows[-1];request=read_evidence(row['request'],ROOT);schema=read_evidence(row['schema'],ROOT)
        previous=read_evidence(row['result'],ROOT)
        profile={'AUDIT_EXPLICIT_DEPENDENCY_CONTEXT':('context_reference_profile','exact-context-answer-and-needs.v1'),
            'ASSESS_REVIEW_WARRANT':('warrant_reference_profile','exact-warrant-answer-fields.v1')}.get(request['task'])
        if profile:request[profile[0]]=profile[1]
        seen=[]
        value=retained(product,dict(key=key,request=request,schema=schema,validate=lambda v:seen.append(digest(v))))
        if mode=='VALIDATED':assert value['value']==previous['value'] and seen==[digest(previous['value'])]
        elif mode=='REVIEWED_FAILURE_RETRY':assert value is None
        else:assert value==previous
        out.append(dict(question=qid,arm=arm,mode=mode,key=key,passed=True))
save(WORK/'real-checkpoint-replay.json',dict(verdict='PASS',provider_calls=0,checks=out,legal_acceptance=False))
print(json.dumps(out,indent=2))
