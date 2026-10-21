import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from pathlib import Path
import sys,time,subprocess,json
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from scripts.legal_integration_master import BASE
from scripts.legal_integration_failure_recovery import WORK,IMPLEMENTATION
from scripts.legal_mission_execution import read,save,ref,require
began=time.monotonic()
tests=['tests/assurance/test_failure_recovery.py','tests/tooling/test_failure_recovery_registration.py',
    'tests/tooling/test_settled_recovery_registration.py','tests/assurance/test_account_recovery_lineage.py',
    'tests/assurance/test_bounded_product.py','tests/tooling/test_integration_continuation_hook.py']
command=['.venv-context/bin/python','-m','pytest','-q',*tests]
result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
(ROOT/WORK/'tests.stdout').write_text(result.stdout);(ROOT/WORK/'tests.stderr').write_text(result.stderr)
require(result.returncode==0,'Regression tests failed')
for name in ('diagnosis.json','replay.json','root-replay.json'):
    require(read(ROOT/WORK/name)['verdict']=='PASS','Local production proof failed')
baseline=read(ROOT/WORK/'baseline.json')
old=next(x['previous'] for x in baseline['archived'] if x['previous']['path']==str(BASE/'live-calls.json'))
require(ref(ROOT,BASE/'live-calls.json')==old,'Validation changed provider charges')
evidence=[ref(ROOT,WORK/name) for name in ('diagnosis.json','replay.json','root-replay.json','tests.stdout','tests.stderr')]
evidence += [ref(ROOT,p) for p in tests]
report=dict(verdict='PASS',provider_calls=0,ledger_unchanged=True,production_replay=True,legal_acceptance=False,
    command=command,environment='.venv-context; CPU only (CUDA_VISIBLE_DEVICES=-1)',
    git_commit=baseline['git_commit'],wall_seconds=time.monotonic()-began,evidence=evidence,
    implementation={p:ref(ROOT,p) for p in sorted(IMPLEMENTATION)},
    interpretation='Engineering controls passed. Corrected model outputs, full P10 preparation and legal acceptance remain unproved.')
save(ROOT/WORK/'local-result.json',report);print(json.dumps({'verdict':'PASS','tests':result.stdout.strip(),'provider_calls':0}),flush=True)
