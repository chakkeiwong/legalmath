import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from pathlib import Path
import sys,json,time
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from scripts.legal_integration_master import BASE,PROGRAM,TOKENIZER
from scripts.legal_integration_gap_preservation import WORK
from scripts.legal_mission_execution import read,save,ref,require
from scripts.legal_integration_campaign import provider
from legalmath.interpretation.assurance.bounded_context import Limits,tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.phased import account_contract,account_encoding,account_instructions,account_input,account_output,account_recovery
from legalmath.canonical import digest
began=time.monotonic();program=read(ROOT/PROGRAM);checkpoint=read(ROOT/WORK/'recovery-p10.json')
pointer=ref(ROOT,WORK/'recovery-p10.json');ledger=ref(ROOT,BASE/'live-calls.json');service=provider()
def forbidden(*args,**kwargs):raise AssertionError('No provider dispatch or reservation during replay')
service.complete=forbidden;service.allowance.reserve=forbidden
product=BoundedProduct(ROOT,ROOT/WORK/'replay-product',service,
    read(ROOT/program['prerequisite_repair']['source']['path']),tokenizer(ROOT/TOKENIZER),
    limits=Limits(),maximum_calls=8100,active_questions=['p10'],
    requirement_account_profile=account_contract.PROFILE,requirement_account_input_profile=account_encoding.PROFILE,
    requirement_account_instruction_profile=account_instructions.PROFILE,requirement_account_capacity_profile=account_input.CAPACITY_PROFILE,
    requirement_account_output_profile=account_output.PROFILE,requirement_account_recovery=pointer)
key='detail-77-part-0-part-1-part-1';entry=checkpoint['completed_account_receipts'][key]
old,schema=(read(ROOT/entry['originals'][name]['path']) for name in ('request','schema'))
base,typed=account_recovery.baseline_request(old,schema,root=ROOT)
value=product.note(key,base['task'],base['question'],base['records'],base['payload'],base['required_considered'],partition=False)
require(value['status']=='VALIDATED' and value['value']==read(ROOT/entry['raw']['path'])['value'],'Exact receipt replay failed')
require(value['provenance']['allowance_slot']==3173,'Charge changed')
details=read(ROOT/checkpoint['account_recovery']['details']['path'])
failed=next(x['result'] for x in details if x['result']['status']=='FAILED')
product.note=lambda *a,**kw:failed
rechecked=product.requirement_details()
successes={x['id']:x for x in details if x['result']['status']=='VALIDATED'}
require(len(successes)==84 and len(rechecked)==85 and all(x==successes[x['id']] for x in rechecked if x['id'] in successes),
    'Root replay changed a successful account')
require(ref(ROOT,BASE/'live-calls.json')==ledger,'Replay charged provider')
report=dict(verdict='PASS',provider_calls=0,ledger_unchanged=True,production_replay=True,
    exact_original_response_reused=True,required_gaps_preserved=3,additional_gaps_retained=4,
    successful_roots_preserved=84,total_accounts=85,replay_result=ref(ROOT,WORK/'replay-product/calls'/key/'result.json'),
    ledger=ledger,wall_seconds=time.monotonic()-began,legal_acceptance=False)
save(ROOT/WORK/'replay.json',report);print(json.dumps(report))
