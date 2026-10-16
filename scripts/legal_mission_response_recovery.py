#!/usr/bin/env python3
"""Declared recovery for qualification Settings construction; unchanged sources."""
from __future__ import annotations
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import legal_mission_response_qualification as q


def execute():
    q.require(q.Execution().summary()['tasks']['qualification-recovery']['status']=='RUNNING','Recovery not reserved')
    q.require(q.read(q.OUT/'primary/result.json')['status']=='FAILED','No recorded primary failure')
    settings=q.Settings(timeout_seconds=300,max_input_bytes=200000,max_output_bytes=80000)
    review=ROOT/'docs/implementation/legal-mission-control/response-qualification-recovery-review.md'
    declaration=q.read(q.OUT/'recovery-revision.json')
    q.require(declaration['reviewed'] and declaration['timeout_seconds']==300,'Unreviewed recovery')
    for reference in declaration['bindings']:q.verify(ROOT,reference)
    allowance=q.QualificationAllowance('recovery');before=allowance.check()
    folder=q.OUT/'recovery';folder.mkdir(parents=True,exist_ok=True)
    q.require(not (folder/'manifest.json').exists(),'Recovery already started; no blind redispatch')
    provider=q.CodexProvider(allowance=allowance);provider.routing=q.deepcopy(q.read(q.OUT/'protocol.json')['route'])
    request=q.read(q.OUT/'request.json')
    start=time.monotonic()
    manifest={'command':'.venv/bin/python scripts/legal_mission_response_recovery.py execute',
       'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
       'environment':str(Path(sys.executable).absolute()),'devices':'CPU only; CUDA_VISIBLE_DEVICES=-1',
       'seeds':'N/A: provider seed unavailable','source':q.ref(ROOT,q.OUT/'request.json'),
       'protocol':q.ref(ROOT,q.OUT/'protocol.json'),'recovery':q.ref(ROOT,q.OUT/'recovery-revision.json'),
       'started_utc':datetime.now(timezone.utc).isoformat(),'calls_before':len(before['calls']),
       'actual_timeout_seconds':300,'status':'RUNNING'}
    q.save(folder/'manifest.json',manifest);rows=[]
    try:
        for stage in ('proposal','review'):
            if stage=='review':
                request={**q.read(q.OUT/'request.json'),'task':'REVIEW_ORIGINAL_QUESTION_ANSWER',
                    'proposed_answer':proposal,'instructions':'Review the proposed answer skeptically against the complete retained source and each case. Identify unsupported source-to-conclusion inferences, contrary readings lost, unknown facts assumed, and fulfillment replaced by activation. Ground every substantive challenge in exact unit quotations when available. Do not treat agreement as legal adjudication. Return the review schema.'}
            schema=q.SCHEMA if stage=='proposal' else q.REVIEW_SCHEMA
            q.save(folder/(stage+'-request.json'),request)
            for reference in declaration['bindings']:q.verify(ROOT,reference)
            allowance.stage=stage;allowance.expected=q.digest(request)
            print('Dispatch recovery/'+stage+'; aggregate before '+str(len(allowance.check()['calls'])),flush=True)
            began=time.monotonic();answer=provider.complete(request,schema,settings)
            q.save(folder/(stage+'-response.json'),{'value':answer.value,'provenance':answer.provenance})
            q.Draft202012Validator(schema).validate(answer.value)
            if stage=='proposal':q.validate_proposal(answer.value,request);proposal=answer.value
            rows.append({'stage':stage,'wall_seconds':round(time.monotonic()-began,3),'response':q.ref(ROOT,folder/(stage+'-response.json'))})
        result={'status':'REVIEW_READY','stages':rows,'legal_acceptance':'REQUIRES_EXECUTOR_SOURCE_REVIEW','full_route_qualified':False}
    except Exception as exc:
        result={'status':'FAILED','stages':rows,'error':getattr(exc,'code',type(exc).__name__),'details':str(getattr(exc,'details',None) or exc),'full_route_qualified':False}
    result.update(calls_total=len(allowance.check()['calls']),wall_seconds=round(time.monotonic()-start,3))
    q.save(folder/'result.json',result)
    manifest.update(status=result['status'],calls_after=result['calls_total'],wall_seconds=result['wall_seconds'],
                    finished_utc=datetime.now(timezone.utc).isoformat(),result=q.ref(ROOT,folder/'result.json'))
    q.save(folder/'manifest.json',manifest)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    q.require(sys.argv[1:]==['execute'],'Only fixed execute command permitted')
    execute()
