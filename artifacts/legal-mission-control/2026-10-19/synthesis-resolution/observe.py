"""Read-only view of the existing worker, branch results and shared ledger."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parent
BASE = ROOT / 'artifacts/legal-mission-control/2026-10-13/master'


def read(path):
    return json.loads(path.read_text()) if path.exists() else None


state = read(BASE / 'execution-state.json')
ledger = read(BASE / 'live-calls.json')
active = read(WORK / 'execution/active-command.json')
binding = read(BASE / 'current-binding.json')
service = ROOT / Path(binding['phase_service_scope']['path']).parent
recovery = read(service / 'service-recovery.json')
circuit = read(service / 'service-circuit.json')
output = {
    'at_utc': datetime.now(timezone.utc).isoformat(),
    'calls': len(ledger['calls']),
    'active_command': active['command'] if active else None,
    'service_circuit_open': circuit['open'],
    'latest_retry': recovery['charges'][-1] if recovery['charges'] else None,
    'worker_result': read(WORK / 'execution/result.json'),
    'running': [key for key, row in state['tasks'].items() if row['status'] == 'RUNNING'],
    'acquisitions': {},
    'product_progress': {},
    'stderr_tail': (WORK / 'execution/0-stderr').read_text()[-1500:],
}
for question in ('p10', 'evidence', 'p14', 'gatecoin'):
    row = state['tasks']['acquire-' + question]
    output['acquisitions'][question] = {
        'status': row['status'], 'attempts': len(row['attempts']),
        'reason': row.get('reason'), 'result': row.get('result'),
    }
    product = WORK / 'live' / question / 'product'
    journal = read(product / 'calls/dispatch.json') or {'calls': {}}
    phases = {}
    for path in sorted((product / 'phases').glob('*/phase.json')):
        phase = read(path)
        phases[path.parent.name] = {
            'status': phase['status'],
            'logical_dispatches': len(phase.get('logical_dispatches', [])),
        }
    output['product_progress'][question] = {
        'recorded_calls': len(journal['calls']),
        'phases': phases,
        'diagnosis': read(WORK / 'live' / question / 'diagnosis.json'),
    }
print(json.dumps(output, indent=2))
