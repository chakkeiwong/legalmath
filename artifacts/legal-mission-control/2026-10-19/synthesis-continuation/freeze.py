from pathlib import Path
import json,hashlib,subprocess,sys
from datetime import datetime,timezone
root = Path.cwd();sys.path.insert(0,str(root))
from scripts.legal_integration_synthesis_continuation import WORK,PREVIOUS,BASE,PROGRAM,STATE,DOC,PLAN,IMPLEMENTATION
from scripts.legal_mission_execution import process_alive
assert (PREVIOUS/'execution/result.json').exists(), 'Previous supervisor unsettled'
assert not process_alive(json.loads((PREVIOUS/'execution/armed.json').read_text())['process'])
state = json.loads(STATE.read_text())
assert not any(x['status'] == 'RUNNING' for x in state['tasks'].values())
assert state['tasks']['acquire-p10']['status'] == 'FAILED'
assert len(state['tasks']['acquire-p10']['attempts']) == 11
assert not (WORK/'baseline.json').exists(), 'Already frozen'
paths = sorted({Path(p) for p in IMPLEMENTATION} | {PLAN,PROGRAM,DOC/'mission.json',STATE}
    | {BASE/n for n in ('current-binding.json','live-grant.json','live-calls.json')})
def pointer(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
rows = []
for p in paths:
    dest = WORK/'before'/p;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(p.read_bytes())
    rows.append(dict(previous=pointer(p),archive=pointer(dest)))
report = dict(profile='synthesis-continuation-baseline.v1',archived=rows,calls=len(json.loads((BASE/'live-calls.json').read_text())['calls']),
    prior_detours=56,running_owners=0,prior_execution=pointer(PREVIOUS/'execution/result.json'),
    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),at_utc=datetime.now(timezone.utc).isoformat())
(WORK/'baseline.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k != 'archived'}))
