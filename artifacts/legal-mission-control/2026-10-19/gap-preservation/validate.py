import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from pathlib import Path
import sys,json,subprocess,time
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from scripts.legal_integration_master import BASE
from scripts.legal_integration_gap_preservation import WORK,IMPLEMENTATION
from scripts.legal_mission_execution import save,read,ref,require
files=['tests/assurance/test_account_gap_preservation.py','tests/assurance/test_account_gap_receipt.py',
    'tests/assurance/test_failure_recovery.py','tests/tooling/test_failure_recovery_registration.py',
    'tests/tooling/test_gap_preservation_registration.py',
    'tests/assurance/test_account_recovery_lineage.py','tests/assurance/test_completed_account_receipt.py',
    'tests/assurance/test_bounded_product.py','tests/tooling/test_integration_continuation_hook.py']
command=['.venv-context/bin/python','-m','pytest','-q',*files]
began=time.monotonic();ledger=ref(ROOT,BASE/'live-calls.json')
result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
(ROOT/WORK/'tests.stdout').write_text(result.stdout);(ROOT/WORK/'tests.stderr').write_text(result.stderr)
require(result.returncode==0,'Regression tests failed; inspect retained logs')
diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,text=True)
require(diff.returncode==0,'Whitespace check failed')
replay=read(ROOT/WORK/'replay.json');require(replay['verdict']=='PASS','Replay failed')
require(ref(ROOT,BASE/'live-calls.json')==ledger,'Tests changed provider ledger')
report=dict(verdict='PASS',provider_calls=0,ledger_unchanged=True,production_replay=True,legal_acceptance=False,
    command=command,environment='.venv-context; CPU only (CUDA_VISIBLE_DEVICES=-1)',
    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),wall_seconds=time.monotonic()-began,
    evidence=[ref(ROOT,WORK/name) for name in ('diagnostic.json','receipt-review.json','replay.json','tests.stdout','tests.stderr')]+[ref(ROOT,p) for p in files],
    implementation={p:ref(ROOT,p) for p in sorted(IMPLEMENTATION)},
    interpretation='Exact complete response passes repaired preservation rule and unchanged source validators; full P10 preparation remains to execute.')
save(ROOT/WORK/'local-result.json',report);print(json.dumps(dict(verdict='PASS',tests=result.stdout.strip(),provider_calls=0)))
