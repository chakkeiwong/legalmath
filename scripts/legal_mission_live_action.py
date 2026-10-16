#!/usr/bin/env python3
"""Fixed reviewed live actions; bounded requests, immutable history, no shell."""
from datetime import datetime, timezone
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time
os.environ['CUDA_VISIBLE_DEVICES']='-1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import legal_mission_response_qualification as q

OUT=q.OUT/'answer-correction'

class CorrectionAllowance:
    def __init__(self):
        self.path=OUT/'allowance.json';self.grant_path=OUT/'protocol.json'
        self.expected=None;self.stage=None
    def check(self):
        protocol=q.read(self.grant_path)
        for item in protocol['bindings']:q.verify(ROOT,item)
        q.require(protocol['maximum']==17 and protocol['deadline_utc']==q.DEADLINE,'Changed correction allowance')
        q.require(datetime.now(timezone.utc)<datetime.fromisoformat(q.DEADLINE),'Original deadline reached')
        state=q.read(self.path);prior=q.read(q.OUT/'allowance.json')
        q.require(state['maximum']==400 and len(prior['calls'])==15 and state['calls'][:15]==prior['calls']
            and len(state['calls'])<=17,'Changed or excessive aggregate spending')
        return state
    def reserve(self,request_hash):
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);state=self.check()
            q.require(request_hash==self.expected and self.stage in ('proposal','review'),'Unbound request')
            q.require(len(state['calls'])<17 and not any(r.get('stage')==self.stage for r in state['calls'][15:]),'Correction reservation exhausted')
            q.require((datetime.fromisoformat(q.DEADLINE)-datetime.now(timezone.utc)).total_seconds()>=305,'Original clock insufficient')
            state['calls'].append({'request_hash':request_hash,'issued_at_ns':str(time.time_ns()),
                                  'branch':'answer-correction','stage':self.stage})
            q.save(self.path,state);return len(state['calls'])

def validate_review(value,request):
    q.Draft202012Validator(q.REVIEW_SCHEMA).validate(value)
    q.require(sorted(x['case_id'] for x in value['case_findings'])==sorted(x['case_id'] for x in request['cases']),'Reviewer omitted or duplicated a case')
    units={u['unit_id']:u['text'] for u in request['source_packet']['units']}
    for finding in value['findings']:
        for source in finding['source_support']:
            q.require(source['unit_id'] in units and source['quote'] and source['quote'] in units[source['unit_id']],'Reviewer quotation not exact')

def execute():
    q.require(q.Execution().summary()['tasks']['answer-correction']['status']=='RUNNING','Correction node not reserved')
    settings=q.Settings(timeout_seconds=300,max_input_bytes=200000,max_output_bytes=80000)
    allowance=CorrectionAllowance();before=allowance.check();protocol=q.read(allowance.grant_path)
    q.require(not (OUT/'manifest.json').exists(),'Started correction cannot be silently replayed')
    provider=q.CodexProvider(allowance=allowance);provider.routing=q.deepcopy(protocol['route'])
    request=q.read(OUT/'proposal-request.json');started=time.monotonic()
    manifest={'command':'.venv/bin/python scripts/legal_mission_live_action.py execute answer-correction',
        'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'environment':str(Path(sys.executable).absolute()),'devices':'CPU only; CUDA_VISIBLE_DEVICES=-1',
        'seeds':'N/A: provider seed unavailable','protocol':q.ref(ROOT,allowance.grant_path),
        'started_utc':datetime.now(timezone.utc).isoformat(),'calls_before':len(before['calls']),'status':'RUNNING'}
    q.save(OUT/'manifest.json',manifest);rows=[]
    try:
        for stage in ('proposal','review'):
            if stage=='review':
                request=q.read(q.OUT/'request.json')
                request.update(task='REVIEW_CORRECTED_ORIGINAL_ANSWER',proposed_answer=proposal,
                    observed_prior_failures=q.read(OUT/'review-focus.json'),
                    instructions='Review independently against the entire retained source and the original questions and cases. Accept no source-to-conclusion inference merely because it was requested as a repair. Check P10 alone versus overall P10/P11 compliance, retain strongest outcome and accountability rivals and missing governing standards; preserve P14 main-text/footnote-5 and confidence-scope rivals; distinguish direct intermediary rules and relevant incorporation through 26EC22. Reject invented facts or silently settled ambiguities. Assess all five cases. Use exact source substrings in quotation fields, preserving Unicode whitespace; a short exact substring is preferable to a normalized quotation. Return the review schema.')
                q.save(OUT/'review-request.json',request)
            allowance.check();allowance.stage=stage;allowance.expected=q.digest(request)
            schema=q.SCHEMA if stage=='proposal' else q.REVIEW_SCHEMA
            print('Dispatch answer-correction/'+stage+'; aggregate '+str(len(allowance.check()['calls'])),flush=True)
            began=time.monotonic();answer=provider.complete(request,schema,settings)
            q.save(OUT/(stage+'-response.json'),{'value':answer.value,'provenance':answer.provenance})
            if stage=='proposal':q.validate_proposal(answer.value,request);proposal=answer.value
            else:validate_review(answer.value,request)
            rows.append({'stage':stage,'wall_seconds':round(time.monotonic()-began,3),'response':q.ref(ROOT,OUT/(stage+'-response.json'))})
        result={'status':'REVIEW_READY','stages':rows,'full_route_qualified':False,'legal_acceptance':'EXECUTOR_REVIEW_REQUIRED'}
    except Exception as exc:
        result={'status':'FAILED','stages':rows,'error':getattr(exc,'code',type(exc).__name__),
                'details':str(getattr(exc,'details',None) or exc),'full_route_qualified':False}
    result.update(calls_total=len(q.read(allowance.path)['calls']),wall_seconds=round(time.monotonic()-started,3))
    q.save(OUT/'result.json',result)
    manifest.update(status=result['status'],calls_after=result['calls_total'],wall_seconds=result['wall_seconds'],
                    finished_utc=datetime.now(timezone.utc).isoformat(),result=q.ref(ROOT,OUT/'result.json'))
    q.save(OUT/'manifest.json',manifest);print(result,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['execute']);parser.add_argument('task',choices=['answer-correction'])
    parser.parse_args();execute()
