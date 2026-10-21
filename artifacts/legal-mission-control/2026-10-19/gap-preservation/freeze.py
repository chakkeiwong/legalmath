from pathlib import Path
import json, hashlib, subprocess
from datetime import datetime, timezone
root=Path.cwd();work=Path('artifacts/legal-mission-control/2026-10-19/gap-preservation')
base=Path('artifacts/legal-mission-control/2026-10-13/master')
previous=Path('artifacts/legal-mission-control/2026-10-19/failure-recovery')
assert (previous/'execution/result.json').exists(), 'Previous supervisor still running'
state=json.loads((base/'execution-state.json').read_text())
assert not any(x['status']=='RUNNING' for x in state['tasks'].values())
assert state['tasks']['acquire-p10']['status']=='FAILED'
assert len(state['tasks']['acquire-p10']['attempts'])==10
assert not (work/'baseline.json').exists(), 'Already frozen'
paths=[Path(p) for p in ('docs/plans/legal-integration-master-2026-10-13.md',
    'docs/implementation/legal-mission-control/integration-master.json',
    'docs/implementation/legal-mission-control/mission.json',
    'scripts/legal_integration_master.py','scripts/legal_mission_execution.py',
    'scripts/legal_mission_control.py','scripts/legal_integration_phased_live.py',
    'src/legalmath/interpretation/assurance/bounded_product.py',
    'src/legalmath/interpretation/assurance/phased/account_recovery.py',
    'src/legalmath/interpretation/assurance/phased/account_contract.py',
    'src/legalmath/interpretation/assurance/phased/account_receipt.py',
    'src/legalmath/interpretation/assurance/phased/failure_recovery.py')]
paths += [base/n for n in ('execution-state.json','current-binding.json','live-grant.json','live-calls.json')]
def pointer(path):return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
rows=[]
for path in paths:
    dest=work/'before'/path;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(path.read_bytes())
    rows.append(dict(previous=pointer(path),archive=pointer(dest)))
report=dict(profile='gap-preservation-baseline.v1',archived=rows,
    calls=len(json.loads((base/'live-calls.json').read_text())['calls']),
    prior_detours=55,running_owners=0,prior_execution=pointer(previous/'execution/result.json'),
    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    at_utc=datetime.now(timezone.utc).isoformat())
(work/'baseline.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='archived'}))
