from pathlib import Path
import json, hashlib, subprocess
from datetime import datetime, timezone
root = Path.cwd()
work = Path('artifacts/legal-mission-control/2026-10-19/failure-recovery')
base = Path('artifacts/legal-mission-control/2026-10-13/master')
paths = [Path(p) for p in (
    'docs/plans/legal-integration-master-2026-10-13.md',
    'docs/implementation/legal-mission-control/integration-master.json',
    'docs/implementation/legal-mission-control/mission.json',
    'scripts/legal_integration_master.py', 'scripts/legal_mission_execution.py',
    'scripts/legal_mission_control.py', 'scripts/legal_integration_phased_live.py',
    'src/legalmath/interpretation/assurance/phased/account_recovery.py',
    'src/legalmath/interpretation/assurance/phased/phase.py',
    'src/legalmath/interpretation/assurance/bounded_checkpoint.py')]
paths += [base / n for n in ('execution-state.json','current-binding.json','live-grant.json','live-calls.json')]
assert not (work/'baseline.json').exists(), 'Already frozen'
state = json.loads((base/'execution-state.json').read_text())
assert not any(r['status']=='RUNNING' for r in state['tasks'].values())
def pointer(p): return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
rows = []
for p in paths:
    dest = work/'before'/p
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f: f.write(p.read_bytes())
    rows.append(dict(previous=pointer(p),archive=pointer(dest)))
result = dict(profile='failure-recovery-baseline.v1',archived=rows,
    calls=len(json.loads((base/'live-calls.json').read_text())['calls']),prior_detours=54,
    separate_hook_packages=1,running_owners=0,
    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    at_utc=datetime.now(timezone.utc).isoformat())
(work/'baseline.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='archived'}))
