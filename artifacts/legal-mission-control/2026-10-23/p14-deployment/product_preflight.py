"""Exercise the actual live product entry locally, stopping before any dispatch."""
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
from scripts import legal_integration_phased_live as live,legal_integration_campaign as campaign
from scripts.legal_mission_execution import read,save,ref,digest
from scripts.legal_review_deployment import HERE
from legalmath.interpretation.assurance.phased.review_contract import PROFILE as CONTRACT
from legalmath.interpretation.assurance.phased.service_prerequisite import PROFILE as SERVICE

def runtime_tag(checkpoints):
    files = read(ROOT/HERE/'implementation-files.json')
    code = {p:(CANDIDATE/p).read_bytes().hex() for p in files if (CANDIDATE/p).is_file()}
    return digest(dict(checkpoints=checkpoints, code=code,
        diagnostic=Path(__file__).read_bytes().hex()))[:16]

class ReachedDispatch(BaseException):
    pass

def run():
    start=time.monotonic()
    live.ROOT=campaign.ROOT=ROOT
    original=read(ROOT/live.PROGRAM)
    program=deepcopy(original)
    checkpoints=read(ROOT/HERE/'checkpoints.json')['arm_checkpoints']
    runtime=HERE/'offline-preflight'/runtime_tag(checkpoints)
    program['review_repair'].update(review_assignment_profile=CONTRACT,service_prerequisite_profile=SERVICE,
        deployment=dict(runtime=str(runtime),arm_checkpoints=checkpoints))
    service=campaign.provider()
    # The old binding deliberately protects the pre-deployment plan/code. This
    # diagnostic tests product reuse and the pre-reservation boundary only;
    # atomic registration separately validates the successor authority.
    # Keep provider identity unchanged so authenticated historical dispatch
    # hashes still match; substitute only the authority check in this fixture.
    service.check=lambda:read(ROOT/live.BASE/'live-calls.json')
    captured={}
    def forbidden(*args,**kwargs):
        raise AssertionError('Local preflight attempted provider dispatch')
    service.complete=forbidden
    def prerequisite(request,schema):
        captured.update(task=request['task'],targets=request.get('required_considered'),
            profile=request.get('review_assignment_profile'))
        raise ReachedDispatch()
    service.check_service=prerequisite
    selected=lambda path:program if Path(path)==ROOT/live.PROGRAM else read(path)
    with patch.object(live,'read',selected),patch.object(live,'phase_admit',lambda owner:
            lambda name,count:dict(offline=True,owner=owner,name=name,count=count)):
        try:
            live.product_route('p14',None,service)
        except ReachedDispatch:
            pass
    arm=ROOT/runtime/'arms/p14/baseline'
    imported=read(arm/'review-import-validation-p14.json')
    assert captured['task']=='AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS' and captured['profile']==CONTRACT
    assert len(captured['targets'])==1 and imported['validated_individuals']==1699
    assert imported['failed_continuations']==52
    journal=arm/'calls/dispatch.json'
    assert not journal.exists() or not read(journal)['calls']
    value=dict(verdict='PASS',provider_calls=0,imported=imported,next_request=captured,
        entry='scripts.legal_integration_phased_live.product_route -> run_product',
        service_prerequisite_before_reservation=True,authority_checked=False,
        authority_check='Required separately by atomic registration; offline provider cannot dispatch.',
        legal_acceptance=False,seconds=time.monotonic()-start)
    save(ROOT/HERE/'product-preflight.json',value)
    print(json.dumps(value,indent=2))

if __name__=='__main__': run()
