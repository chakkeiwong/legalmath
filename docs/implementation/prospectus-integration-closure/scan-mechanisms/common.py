"""Immutable inputs and bounded attempt records for the scan mechanism probes."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parent
SCAN = PACKAGE.parent / 'real-scan'
PLAN = ROOT / 'docs/plans/prospectus-scan-mechanisms-2026-10-11.md'
PYTHON = Path('/home/chakwong/miniconda3/envs/tfgpu/bin/python')
MODEL = ROOT / 'docs/prospectus/closure-2026-10-05/tools/eng.traineddata'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['OMP_THREAD_LIMIT'] = '1'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def verify(folder):
    files = read(folder / 'manifest.json')['files']
    actual = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    if actual != set(files) or any(sha(folder / p) != value for p, value in files.items()):
        raise ValueError('Evidence changed: ' + str(folder))


def active():
    folder = SCAN / 'validation-001'
    frozen = read(folder / 'started.json')['method']
    if any(sha(ROOT / p) != value for p, value in frozen.items()):
        raise ValueError('Active real-scan method changed')
    progress = read(folder / 'progress.json')
    if progress['status'] not in {'RUNNING', 'ENGINEERING_VALIDATION_COMPLETE'}:
        raise ValueError('Active real-scan validation requires review')
    return {'started_sha256': sha(folder / 'started.json'), 'progress': progress}


def method():
    paths = [PLAN, *sorted(PACKAGE.glob('*.py')), *sorted((PACKAGE / 'api-source').glob('*')),
             SCAN / 'oracle.json', SCAN / 'source-review-freeze.json']
    paths += [SCAN / name / 'manifest.json' for name in
              ('inventory/attempt-001', 'baseline/attempt-001', 'analysis/attempt-001')]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths if p.is_file()}


def inputs():
    for name_ in ('inventory/attempt-001', 'baseline/attempt-001', 'analysis/attempt-001'):
        verify(SCAN / name_)
    if any(sha(SCAN / p) != value for p, value in read(SCAN / 'source-review-freeze.json')['files'].items()):
        raise ValueError('Pre-OCR source review changed')
    oracle = read(SCAN / 'oracle.json')
    if sha(ROOT / oracle['source']) != oracle['source_sha256']:
        raise ValueError('Protected PDF changed')
    baseline = read(SCAN / 'baseline/attempt-001/raw-worker.json')
    if sha(PYTHON) != baseline['runtime']['interpreter_sha256'] or sha(MODEL) != baseline['runtime']['language_models']['eng']:
        raise ValueError('Pinned interpreter/model changed')
    return oracle, baseline


def start(name, command):
    if sys.flags.optimize:
        raise ValueError('Assertions must be enabled')
    oracle, baseline = inputs()
    state = active()
    folder = PACKAGE / name / 'attempt-001'
    folder.mkdir(parents=True, exist_ok=False)
    frozen = method()
    save(folder / 'started.json', {'command': command, 'method': frozen,
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'started_at': datetime.now(timezone.utc).isoformat(), 'active_validation': state,
        'environment': {'orchestrator': sys.executable, 'ocr_interpreter': str(PYTHON),
                        'CUDA_VISIBLE_DEVICES': '-1', 'OMP_THREAD_LIMIT': '1'},
        'cpu_gpu': 'CPU; GPU intentionally hidden; concurrent wall times are not compared',
        'interpreter_sha256': sha(PYTHON), 'model_sha256': sha(MODEL),
        'data_version': oracle['source_sha256'], 'random_seeds': 'N/A deterministic diagnostic',
        'plan_file': str(PLAN.relative_to(ROOT)), 'result_file': str((folder / 'result.json').relative_to(ROOT)),
        'evidence_limit_bytes': 20_000_000, 'metadata_reserve_bytes': 1_048_576})
    return folder, frozen, time.monotonic(), oracle, baseline


def finish(folder, frozen, tick, result):
    try:
        inputs()
        state = active()
        if frozen != method():
            raise ValueError('Diagnostic method changed')
        payload = sum(p.stat().st_size for p in PACKAGE.rglob('*') if p.is_file())
        if payload + 1_048_576 > 20_000_000:
            raise ValueError('Diagnostic evidence bound exceeded')
        result.update(active_method_unchanged=True, method_unchanged=True, evidence_payload_bytes=payload,
                      active_phase_at_finish=state['progress'].get('active'))
    except Exception as exc:
        result.update(status='FAIL', error=type(exc).__name__ + ': ' + str(exc))
    result['wall_seconds'] = time.monotonic() - tick
    save(folder / 'result.json', result)
    save(folder / 'manifest.json', {'files': {str(p.relative_to(folder)): sha(p)
        for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps(result), flush=True)
    if result['status'] != 'PASS':
        raise SystemExit(1)
