import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from pathlib import Path
import sys,time,json
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from scripts.legal_integration_master import BASE,PROGRAM,TOKENIZER
from scripts.legal_integration_failure_recovery import WORK
from scripts.legal_mission_execution import read,save,ref,require
from scripts.legal_integration_campaign import provider
from legalmath.interpretation.assurance.bounded_context import Limits,tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import account_contract,account_encoding,account_instructions,account_input,account_output
began=time.monotonic();p=read(ROOT/PROGRAM);checkpoint=read(ROOT/WORK/'recovery-p10.json');pointer=ref(ROOT,WORK/'recovery-p10.json')
ledger=ref(ROOT,BASE/'live-calls.json');service=provider()
def forbidden(*a,**kw):raise AssertionError('Provider calls prohibited during root replay')
service.complete=forbidden;service.allowance.reserve=forbidden
product=PhasedProduct(ROOT,ROOT/WORK/'root-replay-product',service,read(ROOT/p['prerequisite_repair']['source']['path']),
    tokenizer(ROOT/TOKENIZER),limits=Limits(),maximum_calls=8100,active_questions=['p10'],
    phase_admit=forbidden,phase_identity='offline-root-replay',
    requirement_account_profile=account_contract.PROFILE,requirement_account_input_profile=account_encoding.PROFILE,
    requirement_account_instruction_profile=account_instructions.PROFILE,requirement_account_capacity_profile=account_input.CAPACITY_PROFILE,
    requirement_account_output_profile=account_output.PROFILE,requirement_account_recovery=pointer)
details=read(ROOT/checkpoint['account_recovery']['details']['path']);by_id={r['id']:r for r in details};failed=[]
def hold_failed(key,task,question,records,payload,expected,**kw):
    require(key in checkpoint['account_recovery']['roots'],'Successful root unexpectedly reconstructed')
    failed.append(key);return by_id[expected[0]]['result']
product.note=hold_failed
actual=BoundedProduct.requirement_details(product)
require(actual==details and len(failed)==7,'Root reuse changed final census')
require(ref(ROOT,BASE/'live-calls.json')==ledger,'Root replay charged provider')
result=dict(verdict='PASS',provider_calls=0,validated_roots_rechecked=78,failed_roots_preserved=7,
    actual_census_unchanged=True,ledger_unchanged=True,wall_seconds=time.monotonic()-began,legal_acceptance=False)
save(ROOT/WORK/'root-replay.json',result);print(json.dumps(result),flush=True)
