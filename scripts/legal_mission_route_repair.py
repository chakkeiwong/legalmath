#!/usr/bin/env python3
"""Fixed local qualification program; never dispatches a live model or arbitrary command."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import legal_mission_control as control

BASE = ROOT / 'docs/implementation/legal-mission-control'
OUT = ROOT / 'artifacts/legal-mission-control/2026-10-11/route-repair'
PLAN = ROOT / 'docs/plans/legal-mission-route-repair.md'
RULES = BASE / 'route-repair.rules'
EXECUTION_REVIEW = BASE / 'route-repair-final-review.md'
VERIFICATION = OUT / 'verification-3'
AUTHORIZATION = ('create a plan to do what you suggest.  review the plan thoroughly.  amend the allow list and all other necessary tools as well as structure your work to use the exact form to avoid generating approvals.  Ask any approvals upfront and in group to minimize distraction.  execute the plan')
PYTHON = '.venv/bin/python'
PHASES = (
    ('boundaries', ['tests/assurance/test_evidence_route.py', 'tests/assurance/test_decomposition.py',
        'tests/assurance/test_route_final_boundaries.py', 'tests/assurance/test_fidelity_capacity.py',
        'tests/assurance/test_successor_incremental.py']),
    ('source-review', ['tests/assurance/test_staged_source_review.py']),
    ('admission-attribution', ['tests/assurance/test_route_admission.py', 'tests/assurance/test_investigation_answer.py']),
    ('consumer-regression', ['tests/assurance/test_dossier_answer.py', 'tests/assurance/test_source_context.py',
        'tests/assurance/test_integration_completion.py', 'tests/tooling/test_legal_mission_control.py']),
)


def now():
    return datetime.now(timezone.utc)


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    tmp.replace(path)


def ref(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def mission():
    return read(BASE/'mission.json'), read(BASE/'tools.json')


def prepare():
    m, t = mission()
    control.admit(m, t)
    if 'route_repair_admission' in m or OUT.exists():
        raise RuntimeError('Attempt already registered; use status. No clock or attempt reset.')
    start = now()
    revision = {'id': 'evidence-route-repair', 'prior_detours': 7, 'additional_attempts': 1, 'live_calls': 0}
    admission = {'revision': revision, 'authorization': AUTHORIZATION,
        'started_utc': start.isoformat(), 'expires_utc': (start + timedelta(minutes=120)).isoformat(),
        'plan': ref(PLAN), 'review': ref(BASE/'route-repair-review.md')}
    OUT.mkdir(parents=True)
    snapshots = []
    for path in sorted((ROOT/'src/legalmath/interpretation').rglob('*.py')):
        target = OUT/'before'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        snapshots.append({'original_path': str(path.relative_to(ROOT)), 'retained': ref(target)})
    save(OUT/'source-before.json', snapshots)
    save(OUT/'mission-before.json', m)
    m['route_repair_admission'] = admission
    task = next(x for x in m['tasks'] if x['id'] == 'product-contribution')
    task['resource_bounds'] = {'live_calls': 0, 'minutes': 120, 'repair_attempts': 1}
    reason = 'Execute the reviewed single evidence-route repair locally; preserve seven previous detours and count this eighth at admission. Return to product-contribution with actual results. No live admission or grant reset.'
    m['history'].append({'id': 'evidence-route-repair-admission-2026-10-11', 'task_id': 'product-contribution',
        'kind': 'product_evaluation', 'outcome': 'no_advance', 'recorded_at_utc': start.isoformat(),
        'decision': 'Latest explicit user instruction admits one reviewed local candidate repair. Legal and tool-effect claims remain open.',
        'bounded_method_revision': revision, 'result_evidence': [admission['plan'], admission['review']],
        'next_task': 'product-contribution', 'next_task_reason': reason})
    m['next_task_reason'] = reason
    control.validate(m, t)
    save(BASE/'mission.json', m)
    save(OUT/'admission.json', admission)
    print(json.dumps({'status': 'LOCAL_REPAIR_ADMITTED', **admission}))


def check():
    m, t = mission()
    control.admit(m, t)
    admission = m['route_repair_admission']
    if read(OUT/'admission.json') != admission:
        raise RuntimeError('Admission changed')
    if now() >= datetime.fromisoformat(admission['expires_utc']):
        raise RuntimeError('Original local repair deadline expired; results remain available')
    return admission


def status():
    m, t = mission()
    state = control.status(m, t)
    print(json.dumps({'mission': state, 'admission': m.get('route_repair_admission'),
        'phase_results': [read(p) for p in sorted(OUT.rglob('phase-*.json'))],
        'next': read(OUT/'next-phase.json') if (OUT/'next-phase.json').exists() else None}, indent=2))


def install_rules():
    # The only protected write. No user paths, shell interpolation or permissive fallback.
    expected = [('scripts/legal_mission_route_repair.py', x) for x in ('status', 'run')]
    expected += [('scripts/legal_mission_control.py', x) for x in ('check', 'status', 'admit', 'refresh')]
    for script, action in expected:
        result = subprocess.run(['codex', 'execpolicy', 'check', '--rules', str(RULES),
            '--', PYTHON, script, action], cwd=ROOT, check=True, capture_output=True, text=True)
        if json.loads(result.stdout).get('decision') != 'allow':
            raise RuntimeError('Exact command was not allowed')
    # Rule text must be exactly the declared narrow set, not an arbitrary supplied policy.
    expected_lines = {f'prefix_rule(pattern=["{PYTHON}", "{s}", "{a}"], decision="allow")' for s, a in expected}
    actual = {x for x in RULES.read_text().splitlines() if x and not x.startswith('#')}
    if actual != expected_lines:
        raise RuntimeError('Unexpected approval rule')
    target = Path('/home/chakwong/.codex/rules/legalmath-route-repair.rules')
    if target.is_symlink():
        raise RuntimeError('Refuse symlink rule destination')
    target.write_bytes(RULES.read_bytes())
    print(json.dumps({'installed': str(target), 'sha256': ref(RULES)['sha256'], 'commands_checked': len(expected)}))


def run():
    check()
    with (OUT/'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        verification = {'admission':ref(OUT/'admission.json'), 'review':ref(EXECUTION_REVIEW),
            'sources':[ref(p) for p in sorted((ROOT/'src/legalmath/interpretation').rglob('*.py'))],
            'tests':[ref(ROOT/p) for _, tests in PHASES for p in tests],
            'scripts':[ref(ROOT/'scripts'/p) for p in ('legal_mission_route_repair.py',
                'legal_mission_route_fixture.py', 'legal_mission_route_target.py','legal_mission_route_replay.py')],
            'same_attempt':True, 'live_calls':0}
        VERIFICATION.mkdir(exist_ok=True)
        if (VERIFICATION/'verification.json').exists():
            if read(VERIFICATION/'verification.json') != verification:
                raise RuntimeError('Verification bindings changed; retain and review within the original attempt')
        else:save(VERIFICATION/'verification.json',verification)
        for index, (name, tests) in enumerate(PHASES):
            check()
            path = VERIFICATION/f'phase-{index+1}-{name}.json'
            bindings = [ref(ROOT/p) for p in tests]
            bindings += [ref(p) for p in sorted((ROOT/'src/legalmath/interpretation').rglob('*.py'))]
            if path.exists():
                prior = read(path)
                if prior['status'] != 'PASS' or prior['bindings'] != bindings:
                    raise RuntimeError('Recorded phase failed or code changed; retain and review explicitly')
                continue
            command = [PYTHON, '-m', 'pytest', '-q', *tests]
            start = time.monotonic()
            remaining = int((datetime.fromisoformat(check()['expires_utc']) - now()).total_seconds())
            log = VERIFICATION/f'phase-{index+1}-{name}.log'
            with log.open('w') as output:
                result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                    timeout=min(600, remaining), env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1'})
            record = {'phase': name, 'status': 'PASS' if result.returncode == 0 else 'FAIL',
                'command': command, 'bindings': bindings, 'log': ref(log),
                'wall_seconds': time.monotonic()-start, 'completed_utc': now().isoformat(),
                'evidence_class': 'local_engineering_only', 'live_calls': 0}
            save(path, record)
            save(OUT/'next-phase.json', {'after': name, 'decision': 'CONTINUE' if result.returncode == 0 else 'REVIEW_FAILURE',
                'next': PHASES[index+1][0] if index+1 < len(PHASES) else 'retained-route-qualification',
                'reason': 'No legal promotion; actual retained-route and live eligibility must be reviewed.'})
            print(json.dumps({k:v for k,v in record.items() if k != 'bindings'}), flush=True)
            if result.returncode:
                raise RuntimeError('Phase failed; inspect retained log')
        check()
        if not (VERIFICATION/'scripted-product/result.json').exists():
            from scripts.legal_mission_route_fixture import qualify
            result=qualify(VERIFICATION/'scripted-product')
            print(json.dumps({'qualification':result['status'],'live_calls':0}),flush=True)
        else:
            result=read(VERIFICATION/'scripted-product/result.json')
            from legalmath.interpretation.assurance.complete_investigation import verify
            for arm in ('baseline','candidate'):
                verify(ROOT,read(ROOT/result[arm]['dossier']['path']))
        save(OUT/'next-phase.json', {'after':'scripted-product','decision':'REVIEW_FULL_TARGET_CAPACITY',
            'next':'retained-target-qualification',
            'reason':'Synthetic full route cannot qualify full-target workload or legal inference.'})
        check()
        if not (VERIFICATION/'retained-target/result.json').exists():
            from scripts.legal_mission_route_replay import qualify as qualify_target
            result=qualify_target(VERIFICATION/'retained-target')
        else:result=read(VERIFICATION/'retained-target/result.json')
        save(OUT/'next-phase.json', {'after':'retained-target', 'decision':'RETURN_TO_PRODUCT_CONTRIBUTION',
            'next':'record-results-and-live-eligibility',
            'reason':'Local qualification cannot establish legal benefit or increase the original stage allocation.',
            'result':ref(VERIFICATION/'retained-target/result.json')})
        print(json.dumps({'retained_target':result['status'],'live_calls':0}),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'status', 'run', 'install-rules'))
    args = parser.parse_args()
    {'prepare': prepare, 'status': status, 'run': run, 'install-rules': install_rules}[args.action]()


if __name__ == '__main__':
    main()
