"""Build a versioned successor; preserve rejected diagnostics and all charges."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from pathlib import Path
import sys, time, json
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, save, ref, require
from scripts.legal_integration_master import BASE, PROGRAM
from legalmath.interpretation.assurance.phased import account_recovery
WORK = Path('artifacts/legal-mission-control/2026-10-17/gap-refresh/settled-recovery')
began = time.monotonic()
target = WORK / 'recovery-p10-v2.json'
require(not (ROOT / target).exists(), 'Versioned checkpoint already exists')
p = read(ROOT / PROGRAM)
before = ref(ROOT, BASE / 'live-calls.json')
directory = ROOT / p['repair_execution']['common_directories']['p10']
checkpoint = account_recovery.build(ROOT, directory / 'calls', read(directory / 'requirement-details.json'),
    predecessor=p['repair_execution']['recoveries']['p10'], complete_details_path=ROOT / WORK / 'p10-complete-details.json')
require(checkpoint['completed_account_receipts']['detail-10']['allowance_slot'] == 2190, 'Lost charged response')
save(ROOT / target, checkpoint)
account_recovery.load(ROOT, ref(ROOT, target), checkpoint['input_hash'])
require(before == ref(ROOT, BASE / 'live-calls.json'), 'Production ledger changed')
result = dict(verdict='PASS', provider_calls=0, recovery=ref(ROOT,target),
    rejected_checkpoint=ref(ROOT,WORK/'recovery-p10.json'), rejected_replay=ref(ROOT,WORK/'replay-p10.json'),
    reason='Earlier successor lost completed receipt and replay would duplicate slot 2190.',
    retained_receipt_slots=[2190], wall_seconds=time.monotonic()-began, legal_acceptance=False)
save(ROOT / WORK / 'receipt-preservation.json', result)
print(json.dumps(result),flush=True)
