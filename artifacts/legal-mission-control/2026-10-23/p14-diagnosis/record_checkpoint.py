"""Append a diagnosis checkpoint without changing the bound execution graph."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import fcntl
import json
import os

ROOT = Path('/home/chakwong/python/legalmath')
OUT = Path(__file__).resolve().parent
mission_path=ROOT/'docs/implementation/legal-mission-control/mission.json'
def ref(path):
    return dict(path=str(path.relative_to(ROOT)),sha256=sha256(path.read_bytes()).hexdigest())
reason=('Review and bind the isolated P14 request/deferral candidate, preserving all valid results and spent attempts; '
    'service recovery reserve is 88/88, so reviewed finite allocation and exact owner reconciliation precede live work. '
    'Return to P14 context review and warranted corrections; no new live allowance or legal acceptance is implied.')
entry=dict(id='p14-failure-diagnosis-2026-10-23',task_id='product-contribution',kind='product_evaluation',
    outcome='no_advance',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    decision='Diagnosed 17 failed baseline groups and 52 failed repairs. Isolated opt-in repairs pass 203 tests '
        'and 415 context-preserving binding replays. No bound code or grant changed; no provider calls made.',
    next_task='product-contribution',next_task_reason=reason,
    candidate_attempt_accounting=dict(existing_consolidated_review_package=True,
        local_candidate_rounds=1, additional_live_attempts=0, additional_service_replacements=0,
        deployed=False, cumulative_history_reset=False),
    result_evidence=[ref(ROOT/'docs/plans/p14-failure-diagnosis-2026-10-23.md'),
        ref(ROOT/'docs/implementation/legal-mission-control/results/p14-failure-diagnosis-2026-10-23.md'),
        *[ref(OUT/name) for name in ('census.json','contract-replay.json','repair-queue.json',
            'current-state.json','candidate-manifest.json','candidate.patch','local-tests.xml')]])
with mission_path.with_suffix('.execution.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    data=mission_path.read_bytes()
    mission=json.loads(data)
    prior=[r for r in mission['history'] if r['id']==entry['id']]
    if not prior:
        assert mission['current_task']=='product-contribution'
        before=OUT/'mission-before-diagnosis.json'
        if before.exists(): assert before.read_bytes()==data
        else: before.write_bytes(data)
        mission['history'].append(entry)
        mission['next_task_reason']=reason
        tmp=mission_path.with_name('mission.p14-diagnosis.tmp')
        tmp.write_text(json.dumps(mission,indent=2)+'\n')
        os.replace(tmp,mission_path)
print(json.dumps(dict(recorded=True,provider_calls=0,program_changed=False,live_authority_added=False)))
