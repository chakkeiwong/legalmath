"""Read-only compact progress view; never dispatches or changes the master."""
from pathlib import Path
from datetime import datetime,timezone
import json
root=Path(__file__).resolve().parents[4]
work=Path(__file__).resolve().parent
base=root/'artifacts/legal-mission-control/2026-10-13/master'
def read(path):return json.loads(path.read_text()) if path.exists() else None
state=read(base/'execution-state.json')
ledger=read(base/'live-calls.json')
phase=read(work/'live/pass-1/product/phases/reduction-p10-0/phase.json')
details=read(work/'live/pass-1/product/requirement-details.json')
out={
    'observed_at_utc':datetime.now(timezone.utc).isoformat(),
    'calls':len(ledger['calls']),'ceiling':ledger['maximum'],
    'running':[k for k,v in state['tasks'].items() if v['status']=='RUNNING'],
    'p10_status':state['tasks']['acquire-p10']['status'],
    'p10_attempts':len(state['tasks']['acquire-p10']['attempts']),
    'validated_accounts':sum(x['result']['status']=='VALIDATED' for x in details) if details else None,
    'synthesis':dict(status=phase['status'],logical_calls=len(phase.get('logical_dispatches',[])),
        settled=len(phase.get('partial_results',{})),admitted='admission' in phase) if phase else None,
    'active_command':read(work/'execution/active-command.json'),
    'worker_finished':(work/'execution/result.json').exists(),
    'diagnosis':read(work/'next-actions.json')}
print(json.dumps(out,indent=2))
