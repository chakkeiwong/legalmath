"""Register reviewed progress only; no task, binding, grant, or limit changes."""
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, ref, save, verify, require
from scripts import legal_mission_control as control

WORK = Path(__file__).resolve().parent
DOC = ROOT / 'docs/implementation/legal-mission-control'
MASTER = ROOT / 'artifacts/legal-mission-control/2026-10-13/master'
ID = 'integration-master-progress-checkpoint-2026-10-17'

def main():
    started = time.monotonic()
    path = DOC / 'mission.json'
    stable_paths = [DOC / 'integration-master.json',
        ROOT / 'docs/plans/legal-integration-master-2026-10-13.md',
        MASTER / 'current-binding.json', MASTER / 'live-grant.json']
    stable = [ref(ROOT, p) for p in stable_paths]
    evidence = [ref(ROOT, DOC / 'results/gap-refresh-progress-2026-10-17.md'),
        ref(ROOT, WORK / 'current-progress-diagnostic.json'),
        ref(ROOT, WORK / 'evidence-account-followthrough-7-8-2026-10-17.md'),
        ref(ROOT, WORK / 'evidence-account-followthrough-7-8-2026-10-17.manifest.json')]
    diagnostic = read(WORK / 'current-progress-diagnostic.json')
    require(diagnostic['reviewed_plan'] == evidence[0]
        and diagnostic['new_provider_calls'] == diagnostic['new_owner_attempts'] == diagnostic['new_repairs'] == 0
        and diagnostic['rejection']['retained_correction_annotation_valid']
        and len(diagnostic['delayed_retries']) == 2, 'Incomplete reviewed progress evidence')
    with path.with_suffix('.execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        mission = read(path)
        require(not any(r['id'] == ID for r in mission['history']), 'Checkpoint already recorded')
        before = WORK / 'current-progress-mission-before.json'
        with before.open('x') as stream:
            json.dump(mission, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
        candidate = deepcopy(mission)
        now = datetime.now(timezone.utc).isoformat()
        reason = ('Continue the existing evidence worker through its sixth attempt and eligible consumers. '
            'Retain the diagnosed detail-25-part-1 response rejection; any correction requires a settled '
            'checkpoint, production resume review and authorized continuation allocation. P10 phase '
            'adoption, P14 unknown parameter and Gatecoin refusal remain independent blockers. '
            'Preserve hourly service recovery, all prior charges and original deadlines.')
        candidate['integration_master']['execution_checkpoint'] = {
            'profile': 'integration-progress-checkpoint.v1', 'recorded_at_utc': now,
            'review': evidence[0], 'diagnostic': evidence[1], 'task': 'product-contribution',
            'new_phase': False, 'calls_added': 0, 'owner_attempts_added': 0, 'repairs_added': 0,
            'executable_program_changed': False, 'legal_acceptance': False}
        candidate['next_task_reason'] = reason
        candidate['history'].append({'id': ID, 'task_id': 'product-contribution',
            'kind': 'product_evaluation', 'outcome': 'no_advance',
            'decision': 'Verified exact delayed recovery of two terminal failures and reproduced '
                'three rejected prose fields at slot 2466; retained source-account observations. '
                'Continue the existing worker and keep response correction separately conditional.',
            'next_task': 'product-contribution', 'next_task_reason': reason,
            'recorded_at_utc': now, 'result_evidence': evidence,
            'legal_progress_not_established_by_execution': True})
        validation = control.validate(candidate, read(DOC / 'tools.json'), ROOT)
        require(validation['detours_since_advance'] == 53, 'Progress changed detour accounting')
        for pointer in stable + evidence:
            verify(ROOT, pointer)
        require(read(path) == mission, 'Mission changed outside the execution lock')
        save(path, candidate)
        require(read(path) == candidate, 'Checkpoint write did not persist')
        result = {'profile': 'integration-progress-registration.v1', 'verdict': 'PASS',
            'at_utc': datetime.now(timezone.utc).isoformat(), 'wall_seconds': time.monotonic()-started,
            'command': ['.venv/bin/python', str(Path(__file__).relative_to(ROOT))],
            'source': ref(ROOT, Path(__file__)), 'before': ref(ROOT, before),
            'mission_after': ref(ROOT, path), 'stable_inputs': stable, 'evidence': evidence,
            'detours': validation['detours_since_advance'], 'new_provider_calls': 0,
            'new_owner_attempts': 0, 'new_repairs': 0, 'legal_acceptance': False,
            'frontier_at_validation': {k: validation['integration_master'][k]
                for k in ('execution', 'ready', 'running', 'blocked')},
            'next_step': 'Run exact mission refresh; retain worker and continue independent admitted work.'}
        save(WORK / 'current-progress-registration.json', result)
    print(json.dumps({k: result[k] for k in ('verdict','wall_seconds','detours','new_provider_calls',
        'new_owner_attempts','new_repairs','next_step')}, indent=2))

if __name__ == '__main__':
    main()
