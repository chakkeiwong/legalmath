import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from pathlib import Path
import sys,json,time
ROOT = Path.cwd();sys.path.insert(0,str(ROOT))
from scripts.legal_integration_master import BASE,PROGRAM
from scripts.legal_integration_synthesis_continuation import WORK,PREVIOUS
from scripts.legal_mission_execution import read,save,ref,require
from scripts.legal_integration_campaign import provider
from scripts import legal_integration_phased_live as live
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.errors import LegalMathError
from unittest.mock import patch
began = time.monotonic()
ledger = ref(ROOT,BASE/'live-calls.json')
checkpoint = ref(ROOT,PREVIOUS/'live/pass-1/next-checkpoint.json')
prior = read(ROOT/PREVIOUS/'live/pass-1/product/phases/reduction-p10-0/phase.json')
prior_refusal = ref(ROOT,PREVIOUS/'live/pass-1/product/phases/reduction-p10-0/outcome.json')
seen = []
def forbidden(*args,**kwargs): raise AssertionError('No provider dispatch or reservation during replay')
service = provider();service.complete = forbidden;service.allowance.reserve = forbidden
def measured_only(product,name,calls):
    require(name == 'reduction-p10-0','Successful accounts unexpectedly redispatched')
    prepared = product.prepare_calls(calls)
    identities = [{'key':c['key'],'identity':product.dispatch.request_identity(c['request'],c['schema'])} for c in prepared]
    require(identities == prior['contract']['calls'],'Pending synthesis request population changed')
    measurements = [{'key':c['key'],'measurement':product.dispatch.measure(c['request'],c['schema'])} for c in prepared]
    require(measurements == prior['measurements'],'Synthesis measurement changed')
    seen.append(dict(phase=name,calls=len(calls),exact_identities=True,exact_measurements=True))
    raise LegalMathError('E_RESOURCE_LIMIT',details='Deliberate zero-call replay boundary after exact synthesis reconstruction')
folder = WORK/'production-replay'
with patch.object(PhasedProduct,'run_phase',measured_only):
    result = live.product_route('p10',None,service,preparation_only=True,
        recovery_context=dict(recovery=checkpoint,common_directory=str(folder),phase_directory=str(WORK/'replay-admission')))
require(seen and seen[0]['calls'] == 105,'Pending synthesis not reached')
details = read(ROOT/folder/'requirement-details.json')
require(details == read(ROOT/PREVIOUS/'live/pass-1/product/requirement-details.json')
    and len(details) == 85 and all(x['result']['status'] == 'VALIDATED' for x in details),'Account reuse differs')
require(ref(ROOT,BASE/'live-calls.json') == ledger,'Replay charged provider')
require(ref(ROOT,PREVIOUS/'live/pass-1/product/phases/reduction-p10-0/outcome.json') == prior_refusal,'Historical refusal changed')
report = dict(verdict='PASS',provider_calls=0,ledger_unchanged=True,production_replay=True,
    successful_roots_preserved=85,phases=seen,original_refusal=prior_refusal,ledger=ledger,
    details=ref(ROOT,folder/'requirement-details.json'),wall_seconds=time.monotonic()-began,legal_acceptance=False)
save(ROOT/WORK/'replay.json',report);print(json.dumps(report))
