"""Record the zero-call handover without revising tasks or authority."""
from pathlib import Path
from datetime import datetime, timezone
import fcntl
import json
import shutil
import sys
ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.legal_mission_execution import read, save, ref, require
DOC = Path('docs/implementation/legal-mission-control')
WORK = Path('artifacts/legal-mission-control/2026-10-27/git-handoff')
mission_path = ROOT / DOC / 'mission.json'
with mission_path.with_suffix('.execution.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    mission = read(mission_path)
    event_id = 'git-checkpoint-and-source-reconciliation-2026-10-27'
    require(not any(x['id'] == event_id for x in mission['history']), 'Checkpoint already recorded')
    require(mission['current_task'] == 'product-contribution', 'Unexpected current task')
    archive = ROOT / WORK / 'mission-before-final-record.json'
    require(not archive.exists(), 'Pre-record mission already retained')
    shutil.copyfile(mission_path, archive)
    paths = [
        Path('docs/plans/legal-closure-git-handoff-2026-10-27.md'),
        DOC / 'results/campaign-checkpoint-2026-10-27.md',
        DOC / 'checkpoint-2026-10-27/merge-binding-result.json',
        DOC / 'checkpoint-2026-10-27/postmerge-verification.json',
        DOC / 'checkpoint-2026-10-27/evidence-diagnosis.json',
    ]
    reason = ('Live window expired 2026-10-27 05:15:09 UTC; no dispatch. Retain four owner reservations and 7342 charges. '
              'Renew explicit time authority for independent P10/Gatecoin work; P14 additionally needs attempt/allocation authority and evidence needs branch funding. '
              'Corpus applicability, 24 matched comparisons and six tool-effect decisions remain open. Local handover and diagnosis completed.')
    event = dict(id=event_id, task_id='product-contribution', kind='product_evaluation',
        outcome='no_advance',
        decision='Git handover, merged-source reconciliation and retained evidence diagnosis completed locally; no legal acceptance, new attempt or provider call.',
        next_task='product-contribution', next_task_reason=reason,
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        result_evidence=[ref(ROOT, p) for p in paths])
    mission['history'].append(event)
    mission['next_task_reason'] = reason
    save(mission_path, mission)
    save(ROOT / WORK / 'record-checkpoint-result.json', dict(event=event, mission=ref(ROOT, DOC / 'mission.json'),
        previous_mission=ref(ROOT, archive), new_calls=0, new_attempts=0))
    print(json.dumps({'event': event_id, 'history_entries': len(mission['history']), 'new_calls': 0, 'new_attempts': 0}))
