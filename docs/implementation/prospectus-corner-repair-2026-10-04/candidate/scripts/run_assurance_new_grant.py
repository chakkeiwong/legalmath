#!/usr/bin/env python3
"""Bounded, receipted continuation under the separately authorized 500 calls."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import shutil
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(os.environ.get('LEGALMATH_ASSURANCE_SOURCE_ROOT', str(ROOT)))
sys.path[:0] = [str(SOURCE_ROOT/'src'), str(ROOT/'scripts')]
from legalmath.canonical import digest, raw_digest
from legalmath.interpretation.assurance.diversity import save
from legalmath.interpretation.assurance.grants import GrantedAllowance

OUT = ROOT/'artifacts/assurance-new-grant/2026-09-29'
GRANT = OUT/'grant.json'
PLAN = ROOT/'docs/plans/assurance-new-grant-execution.md'
PHASES = ('F0', 'F1-checks', 'F1-pilot', 'F1-breadth', 'F2-tables', 'F2-sources', 'F2-table-repair', 'F2-table-identity', 'F2-source-repair', 'F3', 'F4')


def read(path): return json.loads(Path(path).read_bytes())
def sha(path): return raw_digest(Path(path).read_bytes())
def rel(path): return str(Path(path).resolve().relative_to(ROOT))
def now(): return datetime.now(timezone.utc).isoformat()
def ref(path): return {'path': rel(path), 'sha256': sha(path)}


def command(argv, work, label, *, timeout=1800, cwd=ROOT):
    start = time.monotonic(); log = work/(label+'.log')
    with log.open('w') as stream:
        try:
            code = subprocess.run(argv, cwd=cwd, env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1',
                'PYTHONPATH': str(Path(cwd)/'src')+os.pathsep+str(cwd),
                'LEGALMATH_ASSURANCE_SOURCE_ROOT': str(cwd)},
                stdout=stream, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = 124
    result = {'argv': list(map(str, argv)), 'exit_code': code, 'cwd': str(cwd),
              'cpu_only': True, 'source_import_root': str(cwd),
              'elapsed_seconds': str(time.monotonic()-start), 'log': ref(log)}
    save(work/(label+'-command.json'), result)
    if code: raise RuntimeError(f'{label} failed with {code}; see {log}')
    return result


def state():
    return read(OUT/'state.json') if (OUT/'state.json').exists() else {'phases': {}}


def checked(receipt):
    path = ROOT/receipt['path']
    if sha(path) != receipt['sha256']: raise RuntimeError('Phase receipt changed')
    value = read(path)
    for name, expected in value.get('outputs', {}).items():
        if sha(ROOT/name) != expected: raise RuntimeError('Retained phase output changed: '+name)
    return value


def refresh():
    value = state(); pending = None; phases = {}
    for name in PHASES:
        attempts = value['phases'].get(name, [])
        current = checked(attempts[-1]) if attempts else None
        status = current['status'] if current else 'PENDING'
        phases[name] = {'status': status, 'attempts': len(attempts),
                        'attempts_remaining': max(0, 3-len(attempts))}
        if pending is None and status != 'PASSED': pending = name
    result = {'at': now(), 'phases': phases, 'next_phase': pending,
              'grant': GrantedAllowance(GRANT).verify(),
              'legal_correctness': 'NOT_ESTABLISHED', 'historical_study_complete': False,
              'action': ('Await the active phase; do not redispatch it.' if pending and phases[pending]['status'] == 'RUNNING'
                  else 'Inspect retained failures; execute a focused repair before retry.'
                  if pending and phases[pending]['attempts'] else 'Execute the next reviewed phase.'
                  if pending else 'Inspect rendered documents and finalize the retained delivery.')}
    save(OUT/'next-phase-plan.json', result)
    return result


def phase(name):
    import assurance_new_grant_checks as checks
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        value = state(); attempts = value['phases'].setdefault(name, [])
        if attempts and checked(attempts[-1])['status'] == 'PASSED':
            return refresh()
        if len(attempts) >= 3: raise RuntimeError('Three engineering attempts exhausted; no reset')
        for before in PHASES[:PHASES.index(name)]:
            previous = value['phases'].get(before, [])
            if not previous or checked(previous[-1])['status'] != 'PASSED':
                raise RuntimeError('Predecessor incomplete: '+before)
        repair = None
        if attempts:
            p = OUT/'repairs'/f'{name}-{len(attempts)}.json'; repair = read(p)
            if repair['prior'] != attempts[-1] or not repair['cause'] or not repair['change']:
                raise RuntimeError('Retry lacks causal repair')
            test = ROOT/repair['focused_check']['path']
            if sha(test) != repair['focused_check']['sha256'] or read(test)['exit_code'] != 0:
                raise RuntimeError('Focused repair check has not passed')
        work = OUT/name/f'attempt-{len(attempts)+1:02}'; work.mkdir(parents=True, exist_ok=False)
        from legalmath.interpretation.assurance.integrated import implementation_identity
        inputs = implementation_identity()
        with ZipFile(work/'executed-source.zip', 'w', ZIP_DEFLATED) as archive:
            for path in sorted((SOURCE_ROOT/'src').rglob('*')):
                if path.is_file() and path.suffix in ('.py', '.java', '.lean', '.json'):
                    archive.write(path, str(path.relative_to(SOURCE_ROOT)))
            for path in (Path(__file__), ROOT/'scripts/assurance_new_grant_checks.py', PLAN):
                archive.write(path, rel(path))
        record = {'phase': name, 'status': 'RUNNING', 'started_at': now(), 'plan': ref(PLAN),
                  'grant': ref(GRANT), 'before': GrantedAllowance(GRANT).verify(),
                  'inputs': inputs, 'repair': repair, 'environment': str(ROOT/'.venv/bin/python'),
                  'source_snapshot': str(SOURCE_ROOT),
                  'executed_source': ref(work/'executed-source.zip'),
                  'cpu_only': True, 'seed': 'N/A; configured remote model randomness uncontrolled',
                  'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
        save(work/'manifest.json', record)
        # Reserve the engineering attempt before executing; interruptions retain it.
        attempts.append(ref(work/'manifest.json')); save(OUT/'state.json', value)
        start = time.monotonic()
        try:
            record['result'] = getattr(checks, name.replace('-', '_'))(work)
            if implementation_identity() != inputs:
                raise RuntimeError('Implementation changed during this phase')
            record['status'] = 'PASSED'
        except BaseException as exc:
            record.update(status='FAILED', error=type(exc).__name__, details=str(exc)[:8000])
        record.update(finished_at=now(), elapsed_seconds=str(time.monotonic()-start),
                      after=GrantedAllowance(GRANT).verify())
        record['outputs'] = {rel(p): sha(p) for p in sorted(work.rglob('*'))
                             if p.is_file() and p.name != 'manifest.json'}
        save(work/'manifest.json', record)
        attempts[-1] = ref(work/'manifest.json'); save(OUT/'state.json', value); refresh()
        print(json.dumps({'phase': name, 'status': record['status'], 'manifest': rel(work/'manifest.json'),
                          'used': record['after']['used']}), flush=True)
        if record['status'] != 'PASSED': raise SystemExit(1)
        return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['status', 'phase', 'freeze-future', 'finalize'])
    parser.add_argument('phase', nargs='?', choices=PHASES); args = parser.parse_args()
    if args.action == 'status': print(json.dumps(refresh(), indent=2))
    elif args.action == 'finalize':
        from finalize_assurance_new_grant import run
        print(json.dumps(run(), indent=2))
    elif args.action == 'freeze-future':
        for name in PHASES:
            attempts = state()['phases'].get(name, [])
            if not attempts or checked(attempts[-1])['status'] != 'PASSED':
                raise RuntimeError('Finish reviewed phases before freezing the future method: '+name)
        verified = checked(state()['phases']['F4'][-1])
        snapshot = Path(verified['result']['snapshot'])
        raise SystemExit(subprocess.run([str(ROOT/'.venv/bin/python'),
            str(snapshot/'scripts/freeze_assurance_future.py'), '--workspace', str(ROOT)],
            cwd=snapshot, env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1',
                               'PYTHONPATH': str(snapshot/'src')}).returncode)
    elif args.phase:
        if 'LEGALMATH_ASSURANCE_SOURCE_ROOT' not in os.environ:
            # Long live work and later development use distinct import trees.
            # The archived package is never modified by a subsequent phase.
            snapshot = Path(tempfile.mkdtemp(prefix='legalmath-new-grant-'))
            shutil.copytree(ROOT/'src', snapshot/'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            (snapshot/'.localresources').symlink_to(ROOT/'.localresources', target_is_directory=True)
            (snapshot/'scripts').symlink_to(ROOT/'scripts', target_is_directory=True)
            raise SystemExit(subprocess.run([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
                cwd=ROOT, env={**os.environ, 'LEGALMATH_ASSURANCE_SOURCE_ROOT': str(snapshot),
                               'CUDA_VISIBLE_DEVICES': '-1'}).returncode)
        phase(args.phase)
    else: parser.error('phase name required')
