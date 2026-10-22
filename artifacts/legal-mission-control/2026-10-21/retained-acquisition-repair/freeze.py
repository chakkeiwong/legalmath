"""Preserve the settled baseline before the bounded local correction."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parent
BASE = Path('artifacts/legal-mission-control/2026-10-13/master')
DOC = Path('docs/implementation/legal-mission-control')
paths = [DOC/'integration-master.json', DOC/'mission.json', BASE/'execution-state.json',
    BASE/'live-calls.json', BASE/'live-grant.json', BASE/'current-binding.json',
    Path('docs/plans/legal-integration-master-2026-10-13.md'),
    Path('scripts/legal_integration_master.py'), Path('scripts/legal_mission_execution.py'),
    Path('scripts/legal_mission_control.py'),
    Path('src/legalmath/interpretation/assurance/phased/retained_acquisition.py')]

def ref(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())

state = json.loads((ROOT/BASE/'execution-state.json').read_text())
assert not any(r['status'] == 'RUNNING' for r in state['tasks'].values())
target = WORK/'baseline.json'
assert not target.exists(), 'Existing baseline must not be replaced'
rows = []
for path in paths:
    old, copy = ROOT/path, WORK/'before'/path
    copy.parent.mkdir(parents=True, exist_ok=True)
    with copy.open('xb') as stream:
        stream.write(old.read_bytes())
    rows.append(dict(previous=ref(old), archive=ref(copy)))
value = dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(), prior_detours=60,
    calls=len(json.loads((ROOT/BASE/'live-calls.json').read_text())['calls']), running_owners=0,
    archived=rows, failure=ref(ROOT/BASE/'baseline-gatecoin/attempt-2/evidence.json'),
    worker_result=ref(ROOT/'artifacts/legal-mission-control/2026-10-21/five-minute-retry/finished.json'),
    mission_preflight=dict(check='PASS', status='BLOCKED', admission='REFUSED',
        reason='Task is not ready; refresh its evidence/prerequisites first'),
    diagnostic_revision=ref(ROOT/'docs/plans/legal-retained-acquisition-capacity-repair-2026-10-21.md'))
with target.open('x') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(calls=value['calls'], archived=len(rows), running=0)))
