"""Retain one reviewed scope result in mission history under its existing lock."""
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import os
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, save, ref, require, verify
from scripts import legal_mission_control as control
from scripts.legal_integration_master import DOC, PROGRAM

WORK = Path(__file__).resolve().parent
report = WORK / 'veto-scope-applied.json'
require(read(report)['verdict'] == 'PASS', 'Scope correction did not pass')
result = DOC / 'results/gap-refresh-execution-2026-10-17.md'
key = 'integration-master-p10-scoped-stop-2026-10-17'
path = ROOT / DOC / 'mission.json'
with path.with_suffix('.execution.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    mission = read(path)
    require(not any(r['id'] == key for r in mission['history']), 'Do not duplicate retained scope history')
    mission['history'].append(dict(id=key, task_id='product-contribution',
        kind='product_evaluation', outcome='no_advance',
        decision='Retain P10 phase failure; correct only its overbroad continuation-veto scope after actual proof.',
        next_task='product-contribution',
        next_task_reason='Execute independent evidence through its existing sixth attempt and eligible consumers. P10 phase resume, P14 parameter diagnosis and Gatecoin refusal retain their own prerequisites; no allowance is renewed.',
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        result_evidence=[ref(ROOT, PROGRAM), ref(ROOT, report), ref(ROOT, result),
            ref(ROOT, WORK / 'reviewed-veto-scope.md'), ref(ROOT, WORK / 'veto-scope-review.json')]))
    mission['next_task_reason'] = mission['history'][-1]['next_task_reason']
    state = control.validate(mission, read(ROOT / DOC / 'tools.json'), ROOT)
    require(state['detours_since_advance'] == 53, 'Scope result changed the detour count')
    save(path, mission)
    save(WORK / 'scope-history-recorded.json', dict(verdict='PASS', mission=ref(ROOT, path),
        history_id=key, detours=53, provider_calls=0, legal_acceptance=False))
print('Scope result retained in mission history; detours=53; no calls or allowances added.', flush=True)
