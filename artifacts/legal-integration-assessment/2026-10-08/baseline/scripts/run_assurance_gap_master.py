#!/usr/bin/env python3
"""Bounded gap-closure phases with immutable attempts and executed repair checks."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
OUT = ROOT/'artifacts/assurance-gap-closure/2026-09-30'
PLAN = ROOT/'docs/plans/systematic-challenges-execution.md'
GRANT = ROOT/'artifacts/assurance-new-grant/2026-09-29/grant.json'
PHASES = ('G0','G1','G2','G3','G4','G5','G5r','G6','G7','G7r','G8')
PYTHON = ROOT/'.venv/bin/python'


def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rel(path): return str(Path(path).relative_to(ROOT))
def now(): return datetime.now(timezone.utc).isoformat()
def receipt(path): return {'path': rel(path), 'sha256': sha(path)}
def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(value, indent=2)+'\n'); tmp.replace(path)


def allowance():
    from legalmath.interpretation.assurance.grants import GrantedAllowance
    return GrantedAllowance(GRANT).verify()


def state(): return read(OUT/'state.json') if (OUT/'state.json').exists() else {'phases': {}}


def checked(ref):
    path = ROOT/ref['path']
    if sha(path) != ref['sha256']: raise RuntimeError('Phase receipt changed')
    value = read(path)
    for name, expected in value.get('outputs', {}).items():
        if sha(ROOT/name) != expected: raise RuntimeError('Retained output changed: '+name)
    return value


def phase_status(ref):
    value=checked(ref)
    review_path=OUT/'reviews'/(ref['sha256']+'.json')
    if review_path.exists():
        review=read(review_path)
        if review.get('prior')!=ref or review.get('status') not in ('REJECTED_AFTER_REVIEW','PARTIAL_VERIFIED') or not review.get('reason'):
            raise RuntimeError('Invalid retrospective phase review')
        if review['status']=='PARTIAL_VERIFIED':
            evidence=review['evidence']
            if sha(ROOT/evidence['path'])!=evidence['sha256']:raise RuntimeError('Recovery review evidence changed')
        return review['status']
    return value['status']


def refresh():
    data = state(); phases = {}; pending = None
    for name in PHASES:
        attempts = data['phases'].get(name, [])
        status = phase_status(attempts[-1]) if attempts else 'PENDING'
        phases[name] = {'status': status, 'attempts': len(attempts), 'remaining_attempts': 3-len(attempts)}
        if pending is None and status not in ('PASSED','PARTIAL_VERIFIED'): pending = name
    report = {'at': now(), 'phases': phases, 'next_phase': pending, 'grant': allowance(),
        'action': 'Inspect and deliver the verified documents; retain remaining research qualifications.' if pending is None else
        'Await the running phase; do not launch it again.' if phases[pending]['status'] == 'RUNNING' else
        'Repair the recorded failure and execute a focused check before retry.' if phases[pending]['attempts'] else
        'Execute the next audited phase.', 'legal_correctness': 'NOT_ESTABLISHED',
        'next_plan': 'docs/implementation/assurance-gap-closure/next-phase-plan.md'}
    save(OUT/'next-phase-plan.json', report); return report


def command(argv, work, label, *, cwd=ROOT, timeout=1800):
    work.mkdir(parents=True, exist_ok=True); start = time.monotonic()
    log = work/(label+'.log')
    with log.open('w') as stream:
        try:
            result = subprocess.run(list(map(str, argv)), cwd=cwd,
                env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': str(Path(cwd)/'src')+os.pathsep+str(cwd)},
                stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
            code = result.returncode
        except subprocess.TimeoutExpired: code = 124
    value = {'argv': list(map(str, argv)), 'cwd': str(cwd), 'exit_code': code,
        'cpu_only': True, 'elapsed_seconds': str(time.monotonic()-start), 'log': receipt(log)}
    save(work/(label+'-command.json'), value)
    if code: raise RuntimeError(label+' failed; see '+str(log))
    return value


def phase(name):
    import assurance_gap_checks as checks
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        data = state(); attempts = data['phases'].setdefault(name, [])
        if attempts and phase_status(attempts[-1]) == 'PASSED': return refresh()
        if attempts and checked(attempts[-1])['status'] == 'RUNNING': raise RuntimeError('Running or interrupted phase needs an explicit interruption record')
        if len(attempts) >= 3: raise RuntimeError('Engineering attempts exhausted; no reset')
        for predecessor in PHASES[:PHASES.index(name)]:
            prior = data['phases'].get(predecessor, [])
            if name=='G7r' and predecessor=='G7' and len(prior)==3 and checked(prior[-1])['status']=='FAILED':continue
            if not prior or phase_status(prior[-1]) not in ('PASSED','PARTIAL_VERIFIED'): raise RuntimeError('Incomplete predecessor: '+predecessor)
        repair = None
        if attempts:
            repair = read(OUT/'repairs'/f'{name}-{len(attempts)}.json')
            if repair['prior'] != attempts[-1] or not repair['cause'] or not repair['change']:
                raise RuntimeError('Repair must identify the original failure and causal change')
            ref = repair['focused_check']; proof = ROOT/ref['path']
            if sha(proof) != ref['sha256'] or read(proof)['exit_code'] != 0: raise RuntimeError('Execute the focused repair check')
            log = read(proof)['log']
            if sha(ROOT/log['path']) != log['sha256']: raise RuntimeError('Focused check log changed')
        work = OUT/name/f'attempt-{len(attempts)+1:02d}'; work.mkdir(parents=True, exist_ok=False)
        from run_executable_reference_master import material
        inputs = material(ROOT)
        with ZipFile(work/'executed-inputs.zip', 'w', ZIP_DEFLATED) as archive:
            for path in sorted(inputs): archive.write(ROOT/path, path)
            archive.write(PLAN, rel(PLAN))
        record = {'phase': name, 'status': 'RUNNING', 'started_at': now(), 'inputs': inputs,
            'plan': receipt(PLAN), 'source_archive': receipt(work/'executed-inputs.zip'),
            'before': allowance(), 'repair': repair, 'environment': str(PYTHON), 'cpu_only': True,
            'seed': 'N/A; deterministic checks, remote generation randomness uncontrolled',
            'commit': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()}
        save(work/'manifest.json', record); attempts.append(receipt(work/'manifest.json'))
        save(OUT/'state.json', data); refresh(); start = time.monotonic()
        try:
            record['result'] = getattr(checks, name)(work)
            record['status'] = 'PASSED'
        except BaseException as exc:
            record.update(status='FAILED', error=type(exc).__name__, details=str(exc)[:5000])
        record.update(finished_at=now(), elapsed_seconds=str(time.monotonic()-start), after=allowance())
        record['outputs'] = {rel(p): sha(p) for p in sorted(work.rglob('*')) if p.is_file() and p.name != 'manifest.json'}
        record['workspace_changes_during_phase'] = sorted(set(inputs)^set(material(ROOT)) | {n for n,h in inputs.items() if not (ROOT/n).exists() or sha(ROOT/n) != h})
        save(work/'manifest.json', record); attempts[-1] = receipt(work/'manifest.json')
        save(OUT/'state.json', data); refresh()
        if record['status'] != 'PASSED': raise RuntimeError('Phase failed: '+record['details'])
        return {'phase': name, 'status': record['status'], 'result': record['result'], 'grant': record['after']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['status','phase','regression','deliver'])
    parser.add_argument('name', nargs='?', choices=PHASES); args = parser.parse_args()
    if args.action == 'status': value = refresh()
    elif args.action == 'phase' and args.name: value = phase(args.name)
    elif args.action == 'regression':
        from assurance_gap_delivery import regression
        value = regression()
    elif args.action == 'deliver':
        from assurance_gap_checks import deliver
        value = deliver()
    else: parser.error('A phase name is required')
    print(json.dumps(value, indent=2), flush=True)
