"""Trace actual continuation until its first new request; dispatch is prohibited."""
from pathlib import Path
from unittest.mock import patch
import json,runpy,sys,os
ROOT=Path('/home/chakwong/python/legalmath');WORK=Path('artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation')
os.environ['CUDA_VISIBLE_DEVICES']='-1'
driver=runpy.run_path(str(ROOT/WORK/'deploy.py'));driver['candidate_imports']()
from scripts import legal_integration_phased_live as live,legal_integration_campaign as campaign
from scripts.legal_mission_execution import save
q=sys.argv[1]
service=campaign.provider()
class BeforeDispatch(BaseException):pass
seen=[]
def admission(owner):
    def admit(name,count):
        seen.append(dict(owner=owner,phase=name,logical_calls=count));raise BeforeDispatch()
    return admit
def no_transport(*a,**k):raise AssertionError('Preview attempted provider transport')
service.complete=no_transport
program=json.loads((ROOT/WORK/'registration-stage/program.json').read_text())
original=Path.read_text
def read_text(path,*a,**k):
    if path==ROOT/live.PROGRAM:return json.dumps(program)
    return original(path,*a,**k)
try:
    with patch.object(Path,'read_text',read_text),patch.object(live,'phase_admit',admission), \
         patch.object(live,'active_live',lambda p:WORK/'preview-live'):
        result=live.product_route(q,None,service)
    outcome=dict(status='RETURNED_BEFORE_DISPATCH',result=result)
except BeforeDispatch:
    outcome=dict(status='READY_FOR_FIRST_NEW_REQUEST',next_requests=seen)
except BaseException as exc:
    import traceback
    outcome=dict(status='PREVIEW_FAILED',error=type(exc).__name__,reason=str(getattr(exc,'details',None) or exc),traceback=traceback.format_exc())
outcome.update(provider_calls=0,legal_acceptance=False)
save(ROOT/WORK/('preview-'+q+'.json'),outcome)
print(json.dumps(outcome,indent=2))
