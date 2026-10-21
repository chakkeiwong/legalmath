import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from pathlib import Path
import sys,json
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from scripts.legal_integration_master import BASE,PROGRAM,TOKENIZER
from scripts.legal_mission_execution import read,save,ref,require
from scripts.legal_integration_gap_preservation import WORK,REVIEW
from legalmath.interpretation.assurance.phased import account_recovery,failure_recovery,account_gap_preservation
from legalmath.canonical import digest
key='detail-77-part-0-part-1-part-1'
previous=Path('artifacts/legal-mission-control/2026-10-19/failure-recovery/live/pass-1/next-checkpoint.json')
checkpoint=read(ROOT/previous)
originals=checkpoint['account_recovery']['originals'][key]
folder=Path(originals['request']['path']).parent
binding=read(ROOT/folder/'reference-binding.json')
raw=read(ROOT/folder/'raw.json');slot=raw['provenance']['allowance_slot']
manifest=ref(ROOT,BASE/'provider-evidence'/f'{slot}-{digest(binding["request"])[:16]}'/'manifest.json')
save(ROOT/WORK/'receipt-review.json',dict(profile='account-gap-preservation-review.v1',verdict='PASS',
    provider_calls_authorized=0,review=ref(ROOT,REVIEW),diagnostic=ref(ROOT,WORK/'diagnostic.json'),
    approved_receipts={key:manifest},legal_acceptance=False))
baseline=read(ROOT/WORK/'baseline.json')
held={x['previous']['path']:x['archive'] for x in baseline['archived']}
entry=dict(profile=account_gap_preservation.PROFILE,originals=originals,
    dispatch=checkpoint.get('original_dispatches',{}).get(key,checkpoint['dispatch']),
    amendment=ref(ROOT,WORK/'receipt-review.json'),provider_manifest=manifest,
    allowance_slot=slot,prior_ledger=held[str(BASE/'live-calls.json')],
    reference_binding=ref(ROOT,folder/'reference-binding.json'),raw=ref(ROOT,folder/'raw.json'),
    tokenizer=ref(ROOT,TOKENIZER))
checkpoint.setdefault('completed_account_receipts',{})[key]=entry
checkpoint=failure_recovery.diagnose(ROOT,checkpoint,provider_directory=BASE,
    predecessor=checkpoint['predecessor_recovery'])
require(checkpoint['failure_recovery']['actions']=={key:'REASSESS_COMPLETE_RESPONSE'},'Wrong reassessment')
save(ROOT/WORK/'recovery-p10.json',checkpoint)
pointer=ref(ROOT,WORK/'recovery-p10.json')
account_recovery.load(ROOT,pointer,checkpoint['input_hash'])
old,schema,value,measurement=account_gap_preservation.checked(ROOT,checkpoint,key,entry)
print(json.dumps(dict(verdict='PASS',provider_calls=0,actions=checkpoint['failure_recovery']['actions'],
    gaps=len(value['source_gaps']),measurement=measurement,recovery=pointer)))
