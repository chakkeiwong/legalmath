import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from pathlib import Path
import sys,time,json
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from scripts.legal_integration_master import PROGRAM, BASE
from scripts.legal_mission_execution import read,save,ref,require
from scripts.legal_integration_failure_recovery import WORK
from legalmath.interpretation.assurance.phased import account_recovery,failure_recovery
began=time.monotonic();program=read(ROOT/PROGRAM)
old=program['settled_recovery'];directory=ROOT/old['common_directories']['p10']
checkpoint=account_recovery.build(ROOT,directory/'calls',read(directory/'requirement-details.json'),
    predecessor=old['recoveries']['p10'])
checkpoint=failure_recovery.diagnose(ROOT,checkpoint,provider_directory=BASE,predecessor=old['recoveries']['p10'])
save(ROOT/WORK/'recovery-p10.json',checkpoint)
pointer=ref(ROOT,WORK/'recovery-p10.json')
account_recovery.load(ROOT,pointer,checkpoint['input_hash'])
diagnosis=checkpoint['failure_recovery']
require(len(diagnosis['actions'])==7 and len(checkpoint['account_recovery']['roots'])==7, 'Incomplete failure diagnosis')
details=read(directory/'requirement-details.json')
result=dict(verdict='PASS',provider_calls=0,accounts=len(details),validated=sum(r['result']['status']=='VALIDATED' for r in details),
    failed=sum(r['result']['status']=='FAILED' for r in details),actions=diagnosis['actions'],
    reused_calls=len(checkpoint['calls']),recovery=pointer,wall_seconds=time.monotonic()-began,legal_acceptance=False)
save(ROOT/WORK/'diagnosis.json',result);print(json.dumps(result),flush=True)
