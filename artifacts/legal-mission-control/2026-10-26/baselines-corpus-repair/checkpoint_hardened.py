"""Checkpoint the final isolated repair, then validate the recorded transition."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import fcntl
import json
import os
import subprocess
import time

ROOT = Path('/home/chakwong/python/legalmath')
OUT = Path(__file__).resolve().parent
EVENT = 'failed-baselines-corpus-attribution-repair-2026-10-26'

def read(p): return json.loads(p.read_text())
def ref(p): return {'path':str(p.relative_to(ROOT)), 'sha256':sha256(p.read_bytes()).hexdigest()}
def verify(reference):
    assert ref(ROOT/reference['path']) == reference, reference['path']
def write_new(path, value):
    if path.exists(): assert read(path) == value, str(path)
    else: path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')

initial = read(OUT/'checkpoint-command-results.json')
assert len(initial) == 2 and all(r['exit_code'] == 0 for r in initial), 'Prior refresh not complete or refused'
latest = read(OUT/'latest-candidate.json')
for name in ('candidate','manifest','result'): verify(latest[name])
candidate = read(ROOT/latest['candidate']['path'])
verify(candidate['patch'])
for row in candidate['files']:
    assert sha256((ROOT/row['artifact']).read_bytes()).hexdigest() == row['candidate_sha256']
    live = ROOT/row['path']
    assert (sha256(live.read_bytes()).hexdigest() if live.exists() else None) == row['live_sha256'], row['path']
references = [ref(OUT/'attribution-review-addendum.md'),latest['result'],latest['manifest'],latest['candidate']]
mission_path = ROOT/'docs/implementation/legal-mission-control/mission.json'
with mission_path.with_suffix('.execution.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
    mission = read(mission_path)
    matches = [e for e in mission['history'] if e['id'] == EVENT]
    if matches:
        assert len(matches) == 1 and matches[0]['result_evidence'] == references
        event = matches[0]
    else:
        reason = ('Continue the existing independent dispatcher. Use latest-candidate.json and the hardened consolidated patch at a verified safe checkpoint, preserving all attempts and charges. The first corpus candidate is superseded because it accepted an unrelated passage. Hardened attribution passes 130 tests and 965 real passage selections. P14 target reassessment, corpus applicability/later-treatment, fixed remaining answers and bounded live qualification remain open.')
        event = {'id':EVENT,'task_id':'product-contribution','kind':'product_evaluation',
            'outcome':'no_advance','decision':'Final adverse review and bounded local repair completed; hardened candidate retained, not deployed or legally accepted.',
            'next_task':'product-contribution','next_task_reason':reason,
            'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'result_evidence':references,
            'local_repair_accounting':{'scope':'One explicit reviewed corrective cycle for reproduced false attribution acceptance',
                'corrective_cycles':1,'live_calls':0,'live_attempts':0,'previous_limits_preserved':True}}
        mission['history'].append(event)
        mission['next_task_reason'] = reason
        temporary = mission_path.with_name('mission.hardened-checkpoint.tmp')
        temporary.write_text(json.dumps(mission,indent=2,ensure_ascii=False)+'\n')
        os.replace(temporary,mission_path)
    checkpoint = OUT/'mission-checkpoint-hardened.json'
    if not checkpoint.exists():
        write_new(checkpoint,{'event':event,'mission_sha256':ref(mission_path)['sha256'],'budget_or_graph_changed':False})
command = ['.venv/bin/python','scripts/legal_mission_control.py','refresh']
receipt_path = OUT/'mission-refresh-hardened-command.json'
if receipt_path.exists():
    receipt = read(receipt_path)
    assert receipt['exit_code'] == 0, 'Previous final refresh did not pass; inspect before retry'
else:
    with (OUT/'refresh-hardened.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        start = time.monotonic()
        stamp = datetime.now(timezone.utc).isoformat()
        with (OUT/'mission-refresh-hardened.json').open('w') as stdout, (OUT/'mission-refresh-hardened.stderr').open('w') as stderr:
            result = subprocess.run(command,cwd=ROOT,stdout=stdout,stderr=stderr,timeout=1800)
        receipt = {'command':command,'started_at_utc':stamp,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
            'wall_seconds':time.monotonic()-start,'exit_code':result.returncode,
            'stdout':ref(OUT/'mission-refresh-hardened.json'),'stderr':ref(OUT/'mission-refresh-hardened.stderr')}
        write_new(receipt_path,receipt)
    assert receipt['exit_code'] == 0, 'Final refresh refused; inspect retained output'
refresh = read(OUT/'mission-refresh-hardened.json')
assert refresh['predecessor']['id'] == EVENT, 'Refresh read a different checkpoint'
print(json.dumps({'checkpoint':ref(OUT/'mission-checkpoint-hardened.json'),
    'refresh':receipt,'mission':refresh['status']['mission'],
    'execution':refresh['status'].get('integration_master',{}).get('execution'),
    'deployment':'NOT_DEPLOYED','legal_acceptance':False}))
