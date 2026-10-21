"""Freeze verified local evidence; no provider dispatch or authority mutation."""
from pathlib import Path
from datetime import datetime, timezone
import sys, json, subprocess, xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from scripts.legal_mission_execution import read, save, ref, require, verify
from scripts.legal_integration_master import BASE, PROGRAM, STATE
from scripts.legal_integration_settled_recovery import WORK, REVIEW, MUTATED
require(not (ROOT/WORK/'local-result.json').exists(),'Local proof already frozen')
baseline=read(ROOT/WORK/'baseline.json')
for row in baseline['archived']:
    verify(ROOT,row['archive'])
    if row['previous']['path'] not in MUTATED:
        require(ref(ROOT,row['previous']['path'])==row['previous'],'Production comparator changed')
replays={q:ref(ROOT,WORK/name) for q,name in
    (('evidence','replay-evidence-final.json'),('p10','replay-p10-v2.json'))}
for q,pointer in replays.items():
    value=read(ROOT/pointer['path'])
    require(value['verdict']=='PASS' and value['provider_calls']==0
        and value['ledger_unchanged'] and value['old_dispatches_unchanged'],'Replay failed')
    verify(ROOT,value['source'])
    verify(ROOT,value['first_missing']['stage'])
    if q=='p10': require(value['reused_receipt_slots']==[2190] and value['first_missing']['key']=='detail-11','Duplicate completed request')
    else: require(value['correction_scope_verified'] and value['first_missing']['key']=='detail-25-part-1','Wrong correction')
tests=WORK/'tests-adoption.xml'
suites=list(ET.parse(ROOT/tests).getroot().iter('testsuite'))
require(sum(int(x.get('tests','0')) for x in suites)==66
    and all(int(x.get(k,'0'))==0 for x in suites for k in ('failures','errors','skipped')),'Incomplete regressions')
subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
paths=[tests,WORK/'receipt-preservation.json',WORK/'parent-mismatch.json',WORK/'independent-dispositions.md',
    Path('artifacts/legal-mission-control/2026-10-17/gap-refresh/execute-settled-recovery.py'),
    Path('tests/assurance/test_account_recovery_lineage.py'),Path('tests/assurance/test_retained_locator_order.py'),
    Path('tests/assurance/test_completed_account_constructor.py'),Path('tests/tooling/test_settled_recovery_registration.py')]
result=dict(profile='settled-recovery-local-result.v1',verdict='PASS',provider_calls=0,ledger_unchanged=True,
    legal_acceptance=False,replays=replays,evidence=[ref(ROOT,p) for p in paths],tests_passed=66,
    review=ref(ROOT,REVIEW),implementation={p:ref(ROOT,p) for p in sorted(MUTATED)},
    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    at_utc=datetime.now(timezone.utc).isoformat(),environment='.venv-context; CPU only',
    limits='One local package; evidence +1 owner attempt, P10 +1 owner attempt; no added calls/time/replacements',
    rejected_evidence=[ref(ROOT,WORK/n) for n in ('recovery-p10.json','replay-p10.json','tests-receipts.xml')],
    commands=['.venv-context/bin/python artifacts/legal-mission-control/2026-10-17/gap-refresh/replay-settled-recovery.py p10',
    '.venv-context/bin/python artifacts/legal-mission-control/2026-10-17/gap-refresh/replay-evidence-final.py evidence',
    '.venv-context/bin/python -m pytest tests/assurance/test_account_recovery_lineage.py tests/assurance/test_completed_account_constructor.py tests/assurance/test_retained_locator_order.py tests/tooling/test_settled_recovery_registration.py tests/tooling/test_gap_refresh_registration.py -q --tb=short --junitxml=artifacts/legal-mission-control/2026-10-17/gap-refresh/settled-recovery/tests-adoption.xml'])
save(ROOT/WORK/'local-result.json',result)
print(json.dumps({'verdict':'PASS','tests':66,'provider_calls':0,'replays':replays}),flush=True)
