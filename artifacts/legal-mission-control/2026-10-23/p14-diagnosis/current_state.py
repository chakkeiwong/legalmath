"""Compact read-only checkpoint of the retained legal worker and budget."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from hashlib import sha256

ROOT = Path('/home/chakwong/python/legalmath')
OUT = Path(__file__).resolve().parent
BASE = ROOT/'artifacts/legal-mission-control/2026-10-13/master'
WORK = ROOT/'artifacts/legal-mission-control/2026-10-21/review-repair'
def read(path): return json.loads(path.read_text())
def ref(path): return dict(path=str(path.relative_to(ROOT)),sha256=sha256(path.read_bytes()).hexdigest())
state = read(BASE/'execution-state.json')
ledger = read(BASE/'live-calls.json')
service = read(WORK/'service/service-recovery.json')
circuit = read(WORK/'service/service-circuit.json')
worker = read(WORK/'worker.json')
mission = read(ROOT/'docs/implementation/legal-mission-control/mission.json')
program = read(ROOT/'docs/implementation/legal-mission-control/integration-master.json')
result = dict(at_utc=datetime.now(timezone.utc).isoformat(),
    worker=worker, worker_finished=read(WORK/'finished.json'), worker_error=read(WORK/'worker-error.json'),
    calls=len(ledger['calls']), call_ceiling=ledger['maximum'],
    service_charges=len(service['charges']), service_maximum=service['maximum'],
    service_open=circuit['open'], half_open_reserved=circuit.get('half_open_reserved',False),
    tasks={k:dict(status=v['status'],attempts=len(v['attempts']),supervisor=v.get('live_supervisor'),
        reason=v.get('reason','')[:240]) for k,v in state['tasks'].items() if k in ('baseline-p14','baseline-gatecoin')},
    status_counts=dict(Counter(v['status'] for v in state['tasks'].values())),
    mission_current_task=mission['current_task'], deadline_utc=program['deadline_utc'],
    evidence=[ref(BASE/'live-calls.json'),ref(WORK/'finished.json'),ref(WORK/'service/service-recovery.json')],
    provider_calls_made_by_diagnosis=0, legal_acceptance=False)
(OUT/'current-state.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
