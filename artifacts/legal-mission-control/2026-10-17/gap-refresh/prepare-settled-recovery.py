"""Freeze settled work and prepare recovery; never dispatch or alter authority."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from pathlib import Path
import sys, json, time, subprocess
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, save, ref, require, process_alive
from scripts.legal_integration_master import BASE, DOC, PROGRAM, STATE, PLAN
from legalmath.interpretation.assurance.phased import account_recovery
WORK = Path('artifacts/legal-mission-control/2026-10-17/gap-refresh/settled-recovery')
began = time.monotonic()
require(not (ROOT / WORK / 'baseline.json').exists(), 'Already frozen; inspect retained result')
p, s = read(ROOT / PROGRAM), read(ROOT / STATE)
require(not any(t['status'] == 'RUNNING' for t in s['tasks'].values()), 'Owner still running')
for name in ('worker-start.json', 'worker-live-process.json'):
    require(not process_alive(read(ROOT / WORK.parent / 'evidence-continuation' / name)['process']), 'Worker survives')
worker = read(ROOT / WORK.parent / 'evidence-continuation/worker-result.json')
require(worker['live_exit_code'] == 0 and all(x.get('exit_code') == 0 for x in worker['checks']), 'Worker unsettled')
binding = read(ROOT / BASE / 'current-binding.json')
scope = Path(binding['phase_service_scope']['path']).parent
mutated = [str(PLAN), 'scripts/legal_integration_master.py', 'scripts/legal_integration_phased_live.py',
    'scripts/legal_mission_execution.py', 'scripts/legal_mission_control.py']
paths = [PROGRAM, STATE, DOC / 'mission.json', BASE / 'current-binding.json', BASE / 'live-calls.json',
    BASE / 'live-grant.json', scope / 'service-circuit.json', scope / 'service-recovery.json'] + list(map(Path, mutated))
census = []
for q, directory in p['repair_execution']['common_directories'].items():
    for path in (Path(directory) / 'calls/dispatch.json', Path(directory) / 'requirement-details.json'):
        if (ROOT / path).exists(): paths.append(path)
    dispatch = Path(directory) / 'calls/dispatch.json'
    rows = read(ROOT / dispatch)['calls']
    require(all(x['status'] in ('VALIDATED', 'FAILED') for x in rows.values()), 'Unsettled dispatch ' + q)
    census.append(str(dispatch))
archived = []
for path in dict.fromkeys(paths):
    target = WORK / 'before' / path
    (ROOT / target).parent.mkdir(parents=True, exist_ok=True)
    with (ROOT / target).open('xb') as f: f.write((ROOT / path).read_bytes())
    archived.append({'previous': ref(ROOT, path), 'archive': ref(ROOT, target)})
save(ROOT / WORK / 'baseline.json', dict(profile='settled-gap-baseline.v1', archived=archived,
    calls=len(read(ROOT / BASE / 'live-calls.json')['calls']), prior_detours=53,
    running_owners=0, reserved_dispatches=0, dispatch_census=census, mutated=mutated,
    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    at_utc=datetime.now(timezone.utc).isoformat()))
for q in ('evidence', 'p10'):
    directory = ROOT / p['repair_execution']['common_directories'][q]
    checkpoint = account_recovery.build(ROOT, directory / 'calls', read(directory / 'requirement-details.json'),
        predecessor=p['repair_execution']['recoveries'][q], complete_details_path=ROOT / WORK / (q + '-complete-details.json'))
    path = WORK / ('recovery-' + q + '.json')
    save(ROOT / path, checkpoint)
    account_recovery.load(ROOT, ref(ROOT, path), checkpoint['input_hash'])
    print(json.dumps({'question': q, 'successful_calls': len(checkpoint['calls']),
        'roots_to_recover': len(checkpoint['account_recovery']['roots']),
        'corrections': list(checkpoint['account_recovery'].get('corrections', {})),
        'checkpoint': ref(ROOT, path)}), flush=True)
require(ref(ROOT, BASE / 'live-calls.json')['sha256'] == next(r['previous']['sha256'] for r in archived
    if r['previous']['path'] == str(BASE / 'live-calls.json')), 'Calls changed')
save(ROOT / WORK / 'checkpoint-result.json', dict(verdict='PASS', provider_calls=0,
    recoveries={q:ref(ROOT,WORK / ('recovery-' + q + '.json')) for q in ('evidence','p10')},
    wall_seconds=time.monotonic()-began, legal_acceptance=False))
