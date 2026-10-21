"""Offline build/review workspace for the common capacity interface.

This command never invokes a model, grants live authority, or changes running
product files. Adoption is a separate checked master transaction.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'artifacts/legal-mission-control/2026-10-20/common-capacity-interface'
STAGE = WORK / 'staging'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def stage():
    if (WORK / 'baseline-files.json').exists():
        return {'staging': str(STAGE), 'reused': True}
    hashes = {}
    for name in ('src', 'scripts', 'tests'):
        for source in (ROOT / name).rglob('*'):
            if not source.is_file() or '__pycache__' in source.parts or source.suffix == '.pyc':
                continue
            relative = source.relative_to(ROOT)
            destination = STAGE / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            hashes[str(relative)] = hashlib.sha256(source.read_bytes()).hexdigest()
    for name in ('pyproject.toml',):
        shutil.copy2(ROOT / name, STAGE / name)
    save(WORK / 'baseline-files.json', hashes)
    save(WORK / 'admission.json', {
        'mission_check': 'PASS', 'admission': 'ADMITTED_MASTER_WORK',
        'admitted_task': 'product-contribution', 'provider_calls': 0,
        'predecessor': 'candidate_capacity_retry', 'worker_pid': 229996,
        'scope': 'Isolated implementation; no changes to running bound files',
        'plan': 'docs/plans/legal-common-capacity-interface-2026-10-20.md'})
    return {'staging': str(STAGE), 'files': len(hashes)}


def tests(paths):
    if (WORK / 'test-run.json').exists():
        archive = WORK / 'test-history' / str(len(list((WORK / 'test-history').glob('*'))) + 1)
        archive.mkdir(parents=True)
        for name in ('test-run.json', 'tests.stdout', 'tests.stderr', 'tests.xml'):
            if (WORK / name).exists():
                shutil.copy2(WORK / name, archive / name)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='-1', PYTHONPATH=str(STAGE / 'src') + ':' + str(STAGE))
    command = [str(ROOT / '.venv-context/bin/python'), '-m', 'pytest', '-q', *paths,
               '--junitxml=' + str(WORK / 'tests.xml')]
    started = time.time()
    result = subprocess.run(command, cwd=STAGE, env=env, capture_output=True, text=True)
    (WORK / 'tests.stdout').write_text(result.stdout)
    (WORK / 'tests.stderr').write_text(result.stderr)
    save(WORK / 'test-run.json', {'command': command, 'cwd': str(STAGE),
        'returncode': result.returncode, 'wall_seconds': time.time()-started,
        'cpu_mode': 'CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden', 'provider_calls': 0})
    print(result.stdout[-14000:])
    print(result.stderr[-2000:])
    return {'returncode': result.returncode}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['stage', 'test'])
    parser.add_argument('paths', nargs='*')
    args = parser.parse_args()
    result = stage() if args.action == 'stage' else tests(args.paths or ['tests/assurance/test_common_capacity.py'])
    print(json.dumps(result, indent=2))
    raise SystemExit(result.get('returncode', 0))
