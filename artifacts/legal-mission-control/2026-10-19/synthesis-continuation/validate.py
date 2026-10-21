import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from pathlib import Path
import json,subprocess,sys,time
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from scripts.legal_integration_synthesis_continuation import WORK
from scripts.legal_mission_execution import save,read,ref,require
tests=['tests/assurance/test_time_authority.py','tests/assurance/test_preparation_diagnosis.py',
    'tests/assurance/test_phased_admission.py','tests/assurance/test_delayed_service_recovery.py',
    'tests/assurance/test_terminal_cancellation_recovery.py','tests/assurance/test_phased_phase.py',
    'tests/assurance/test_phased_product.py','tests/assurance/test_synthesis_successor.py',
    'tests/assurance/test_synthesis_lineage.py','tests/tooling/test_integration_campaign.py',
    'tests/tooling/test_synthesis_continuation_registration.py','tests/tooling/test_gap_preservation_registration.py']
command=['.venv-context/bin/python','-m','pytest','-q',*tests]
began=time.monotonic();result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
(ROOT/WORK/'tests.stdout').write_text(result.stdout);(ROOT/WORK/'tests.stderr').write_text(result.stderr)
save(ROOT/WORK/'tests.json',dict(command=command,exit_code=result.returncode,wall_seconds=time.monotonic()-began,
    stdout=ref(ROOT,WORK/'tests.stdout'),stderr=ref(ROOT,WORK/'tests.stderr'),devices='CPU; CUDA_VISIBLE_DEVICES=-1'))
require(result.returncode==0,'Focused regression failed')
replay=read(ROOT/WORK/'replay.json')
require(replay['verdict']=='PASS' and replay['successful_roots_preserved']==85
    and replay['provider_calls']==0 and replay['ledger_unchanged'],'Production replay incomplete')
save(ROOT/WORK/'local-result.json',dict(verdict='PASS',provider_calls=0,ledger_unchanged=True,production_replay=True,
    legal_acceptance=False,evidence=[ref(ROOT,WORK/'replay.json'),ref(ROOT,WORK/'tests.json')]))
print(json.dumps(dict(verdict='PASS',tests=result.stdout.strip(),provider_calls=0,successful_roots_preserved=85)))
