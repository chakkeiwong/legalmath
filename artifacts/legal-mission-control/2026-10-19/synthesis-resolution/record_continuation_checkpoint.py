"""Record an evidence checkpoint without reopening or modifying live owners."""
from datetime import datetime, timezone
from hashlib import sha256
import collections
import fcntl
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, ref, save, require
from scripts import legal_mission_control as control

BASE = ROOT / 'artifacts/legal-mission-control/2026-10-13/master'
DOC = ROOT / 'docs/implementation/legal-mission-control'
EVENT = 'synthesis-service-and-source-checkpoint-2026-10-19'

def main():
    ledger = read(BASE / 'live-calls.json')
    receipts = []
    for slot in (3335, 3336, 3337):
        charge = ledger['calls'][slot - 1]
        folder = BASE / 'provider-evidence' / (str(slot).zfill(4) + '-' + charge['request_hash'][:16])
        manifest = read(folder / 'manifest.json')
        require(manifest['allowance_slot'] == slot and manifest['request_hash'] == charge['request_hash'], 'Receipt charge mismatch')
        for name, details in manifest['files'].items():
            require(sha256((folder / name).read_bytes()).hexdigest() == details['retained_sha256'], 'Receipt content mismatch')
        events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines() if line.strip()]
        receipts.append(dict(slot=slot, request_hash=charge['request_hash'],
            schema_hash=manifest['files']['schema.json']['retained_sha256'], receipt=ref(ROOT, folder / 'manifest.json'),
            complete_output=manifest['complete_output_present'],
            terminal_events=[e for e in events if e.get('type') in ('error', 'turn.failed', 'turn.completed')]))
    require(len({r['request_hash'] for r in receipts}) == len({r['schema_hash'] for r in receipts}) == 1, 'Retry identity changed')
    require([r['complete_output'] for r in receipts] == [False, False, True], 'Unexpected recovery result')
    journal = read(WORK / 'live/p14/product/calls/dispatch.json')['calls']
    require(journal['reduce-p14-0-43']['status'] == 'VALIDATED', 'Recovered request not validated')
    record = dict(at_utc=datetime.now(timezone.utc).isoformat(), receipts=receipts,
        recovered_key='reduce-p14-0-43', recovered_status='VALIDATED',
        calls_observed=len(ledger['calls']), journal_status_counts=dict(collections.Counter(r['status'] for r in journal.values())),
        integration_complete=False, checkpoint_provider_calls=0, attempts_reopened=0,
        program=ref(ROOT, DOC / 'integration-master.json'),
        source_result=ref(ROOT, WORK / 'source-check-result.json'),
        conclusion='Exact retry recovered; current publication identities retained; continue the existing owner without duplicate dispatch.')
    observation = WORK / 'recovered-service-checkpoint.json'
    if not observation.exists():
        save(observation, record)
    reason = ('Continue the existing synthesis worker and exact missing-work journals; preserve the recovered slot 3337, '
        'all earlier successes and the current provider circuit. Drain each eligible answer/tool branch after its own acquisition. '
        'Publication identity is freshly checked; actual corpus answer/citation use and scheduling repair remain separate open duties. '
        'No duplicate worker, owner reopening or allowance increase is authorized by this checkpoint.')
    path = DOC / 'mission.json'
    with path.with_suffix('.execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        mission = read(path)
        if not any(row['id'] == EVENT for row in mission['history']):
            mission['history'].append(dict(id=EVENT, task_id='product-contribution', kind='product_evaluation',
                outcome='no_advance', recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                decision='Authenticated overload recovery and fresh official publication identity; no legal closure or production repair claimed.',
                next_task='product-contribution', next_task_reason=reason,
                result_evidence=[ref(ROOT, WORK / name) for name in (
                    'service-execution-audit.md', 'service-execution-audit.json', 'service-audit-tests.json',
                    'continuation-source-check.md', 'source-check-result.json',
                    'continuation-source-result.md', 'recovered-service-checkpoint.json')]))
            mission['next_task_reason'] = reason
            control.validate(mission, read(DOC / 'tools.json'), ROOT)
            save(path, mission)
    command = ['.venv/bin/python', 'scripts/legal_mission_control.py', 'refresh']
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=900)
    (WORK / 'checkpoint-refresh.stdout').write_text(result.stdout)
    (WORK / 'checkpoint-refresh.stderr').write_text(result.stderr)
    save(WORK / 'checkpoint-refresh-result.json', dict(command=command, exit_code=result.returncode,
        at_utc=datetime.now(timezone.utc).isoformat(), stdout=ref(ROOT, WORK / 'checkpoint-refresh.stdout'),
        stderr=ref(ROOT, WORK / 'checkpoint-refresh.stderr')))
    require(result.returncode == 0, 'Mission refresh failed; inspect retained output')
    refreshed = json.loads(result.stdout)
    print(json.dumps(dict(checkpoint=EVENT, refresh=refreshed['refresh'],
        execution=refreshed['status']['integration_master']['execution'],
        ready=refreshed['status']['integration_master']['ready'],
        running=refreshed['status']['integration_master']['running'],
        detours=refreshed['status']['detours_since_substantive_advance'],
        integration_complete=False), indent=2))

if __name__ == '__main__':
    main()
