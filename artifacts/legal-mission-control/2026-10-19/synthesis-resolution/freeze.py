from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, subprocess, sys
root = Path.cwd(); sys.path.insert(0, str(root))
from scripts.legal_mission_execution import process_alive
work = Path('artifacts/legal-mission-control/2026-10-19/synthesis-resolution')
prior = Path('artifacts/legal-mission-control/2026-10-19/synthesis-continuation')
base = Path('artifacts/legal-mission-control/2026-10-13/master')
implementation = {
    'scripts/legal_integration_synthesis_resolution.py',
    'scripts/legal_integration_master.py', 'scripts/legal_mission_control.py',
    'scripts/legal_mission_execution.py', 'scripts/legal_integration_phased_live.py',
    'scripts/legal_product_completion.py',
    'src/legalmath/interpretation/assurance/bounded_product.py',
    'src/legalmath/interpretation/assurance/bounded_provider.py',
    'src/legalmath/interpretation/assurance/phased/downstream_input.py',
    'src/legalmath/interpretation/assurance/phased/grouping.py',
    'src/legalmath/interpretation/assurance/phased/product.py',
    'src/legalmath/interpretation/assurance/phased/synthesis_recovery.py',
    'src/legalmath/interpretation/assurance/phased/synthesis_catalog.py',
    'src/legalmath/interpretation/assurance/phased/synthesis_reassessment.py',
}
assert (prior/'execution/result.json').exists()
assert not process_alive(json.loads((prior/'execution/armed.json').read_text())['process'])
state = json.loads((base/'execution-state.json').read_text())
assert not any(t['status']=='RUNNING' for t in state['tasks'].values())
assert {q:len(state['tasks']['acquire-'+q]['attempts']) for q in ('p10','p14','evidence','gatecoin')} == dict(p10=12,p14=10,evidence=7,gatecoin=13)
paths = {Path(p) for p in implementation if Path(p).exists()} | {
    Path('docs/plans/legal-integration-master-2026-10-13.md'),
    Path('docs/implementation/legal-mission-control/integration-master.json'),
    Path('docs/implementation/legal-mission-control/mission.json'),
    *(base/n for n in ('execution-state.json','current-binding.json','live-grant.json','live-calls.json'))}
def ref(p): return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
assert not (work/'baseline.json').exists()
archived=[]
for p in sorted(paths):
    target=work/'before'/p; target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f: f.write(p.read_bytes())
    archived.append(dict(previous=ref(p),archive=ref(target)))
value=dict(profile='synthesis-resolution-baseline.v1', archived=archived,
    implementation=sorted(implementation), calls=len(json.loads((base/'live-calls.json').read_text())['calls']),
    prior_detours=57,running_owners=0,prior_execution=ref(prior/'execution/result.json'),
    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),at_utc=datetime.now(timezone.utc).isoformat())
(work/'baseline.json').write_text(json.dumps(value,indent=2))
print(json.dumps({k:v for k,v in value.items() if k not in ('implementation','archived')}))
