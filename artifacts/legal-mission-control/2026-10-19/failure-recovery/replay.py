import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from pathlib import Path
import sys,time,json
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from scripts.legal_integration_master import BASE,PROGRAM,TOKENIZER
from scripts.legal_integration_failure_recovery import WORK
from scripts.legal_mission_execution import read,save,ref,require
from scripts.legal_integration_campaign import provider
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import Limits,tokenizer
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import account_contract,account_encoding,account_instructions,account_input,account_output,account_recovery,failure_recovery
from legalmath.interpretation.assurance.bounded_checkpoint import retained_response
from legalmath.interpretation.assurance.bounded_references import prepare
began=time.monotonic();p=read(ROOT/PROGRAM);checkpoint=read(ROOT/WORK/'recovery-p10.json');pointer=ref(ROOT,WORK/'recovery-p10.json')
ledger=ref(ROOT,BASE/'live-calls.json');service=provider()
def forbidden(*a,**kw):raise AssertionError('Provider calls prohibited during production replay')
service.complete=forbidden;service.allowance.reserve=forbidden
product=PhasedProduct(ROOT,ROOT/WORK/'replay-product',service,read(ROOT/p['prerequisite_repair']['source']['path']),
    tokenizer(ROOT/TOKENIZER),limits=Limits(),maximum_calls=8100,active_questions=['p10'],
    phase_admit=forbidden,phase_identity='offline-replay-no-live-admission',
    requirement_account_profile=account_contract.PROFILE,requirement_account_input_profile=account_encoding.PROFILE,
    requirement_account_instruction_profile=account_instructions.PROFILE,requirement_account_capacity_profile=account_input.CAPACITY_PROFILE,
    requirement_account_output_profile=account_output.PROFILE,requirement_account_recovery=pointer,
    downstream_input_profile=p['repair_execution']['downstream_input_profile'],
    downstream_instruction_profile=p['repair_execution']['downstream_instruction_profile'])
captures=[]
for key,action in checkpoint['failure_recovery']['actions'].items():
    refs=checkpoint['account_recovery']['originals'][key]
    old,schema=read(ROOT/refs['request']['path']),read(ROOT/refs['schema']['path'])
    original,typed=account_recovery.baseline_request(old,schema,root=ROOT)
    class Captured(BaseException):pass
    def capture(k,request,shape,validator):
        require(k==key,'Unexpected repair key')
        # Production note construction must preserve the exact failed base assignment.
        require(account_recovery.baseline_request(request,shape,root=ROOT)[0]==original,'Repair changed source or assignment')
        measurement=product.dispatch.measure(request,shape)
        if action=='CORRECT_REFERENCE_FORMAT':
            require('account_correction' in request,'Missing correction annotation')
            account_recovery.validate_retained_correction(ROOT,request['account_correction'],original)
            require(request['account_correction']['required_source_gaps']==read(ROOT/checkpoint['account_recovery']['corrections'][key]['raw']['path'])['value']['source_gaps'],'Changed gap')
        else:
            require(request==old and shape==schema,'Replay changed logical request')
            require(retained_response(ROOT,pointer,k,request,shape,product.dispatch.request_identity(request,shape),
                product.route.input_hash,limits=product.route.limits,encode=product.route.encode) is None,'Retry confused with saved success')
            wire=failure_recovery.replay_wire(ROOT,pointer,k,request,shape)
            require(wire==read(ROOT/checkpoint['recoverable_failures'][key]['wire_binding']['path']),'Exact provider packet changed')
        captures.append(dict(key=k,action=action,measurement=measurement,request_hash=digest(request)))
        raise Captured()
    product.dispatch.call=capture
    try:product.note(key,original['task'],original['question'],original['records'],original['payload'],original['required_considered'],partition=False)
    except Captured:pass
    else:raise AssertionError('Production dispatch constructor not reached')
require(len(captures)==7,'Missing failure path')
require(ref(ROOT,BASE/'live-calls.json')==ledger,'Replay charged provider')
report=dict(verdict='PASS',provider_calls=0,production_constructor=True,exact_failed_packets=True,
    gap_preservation=True,ledger_unchanged=True,captures=captures,ledger=ledger,wall_seconds=time.monotonic()-began,
    legal_acceptance=False,limitation='No corrected model output or complete synthesis is claimed.')
save(ROOT/WORK/'replay.json',report);print(json.dumps(report),flush=True)
