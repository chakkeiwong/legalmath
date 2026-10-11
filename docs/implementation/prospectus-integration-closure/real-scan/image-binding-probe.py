"""Test the real OCR producer's correction image binding without another OCR run."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/implementation/prospectus-integration-closure'
PACKAGE = Path(__file__).resolve().parent
PLAN = ROOT / 'docs/plans/prospectus-real-scan-2026-10-11.md'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor import corrections  # noqa: E402
from legalmath.prospectus.successor.contracts import digest  # noqa: E402
from legalmath.prospectus.successor.occurrences import anchor  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    if len(sys.argv) != 1 or Path(corrections.__file__).resolve() != ROOT / 'src/legalmath/prospectus/successor/corrections.py':
        raise ValueError('Exact command and worktree required')
    baseline = BASE / 'worker-recovery/ocr-baseline/attempt-001'
    manifest = read(baseline / 'manifest.json')['files']
    if any(sha(baseline / name) != value for name, value in manifest.items()):
        raise ValueError('Retained actual-worker baseline changed')
    graph = read(baseline / 'service-report.json')['source_map']
    unit = next(u for u in graph['units'] if u['raw'] and u.get('image_sha256'))
    if unit['method'] != 'retained-pymupdf-tesseract':
        raise ValueError('Probe no longer represents the observed producer method')
    frozen = read(BASE / 'worker-recovery/validation-001/started.json')['method']
    if any(sha(ROOT / name) != value for name, value in frozen.items()):
        raise ValueError('Active R6 method changed')
    folder = PACKAGE / 'image-binding/attempt-001'
    if folder.exists():
        raise ValueError('Retain prior attempts; no unchanged repeat')
    folder.mkdir(parents=True)
    method = {str(p.relative_to(ROOT)): sha(p) for p in
              [Path(__file__), PLAN, Path(corrections.__file__), baseline / 'manifest.json']}
    save(folder / 'started.json', {'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
         'command': ['timeout', '30', '.venv/bin/python', str(Path(__file__).relative_to(ROOT))],
         'method': method, 'started_at': datetime.now(timezone.utc).isoformat(),
         'plan_file': str(PLAN.relative_to(ROOT)), 'result_file': str((folder / 'result.json').relative_to(ROOT)),
         'environment': {'python': sys.executable, 'CUDA_VISIBLE_DEVICES': '-1'},
         'cpu_gpu': 'CPU only; GPU deliberately hidden; no native worker or GPU probe',
         'data_version': unit['source_sha256'], 'random_seeds': 'N/A deterministic admission controls',
         'timeout_seconds': 30, 'evidence_limit_bytes': 1_000_000})
    tick = time.monotonic()
    cases = []
    try:
        for case in ('matching', 'wrong-image', 'missing-image', 'literal-ocr-control', 'plain-text-control'):
            candidate = deepcopy(graph)
            raw = next(u for u in candidate['units'] if u['id'] == unit['id'])
            if case == 'literal-ocr-control':
                raw['method'] = 'ocr'
            elif case == 'plain-text-control':
                raw['method'] = 'plain-text'
                raw.pop('image_sha256')
            entry = {'id': 'complete-line', 'source': anchor(raw), 'operations': [
                {'kind': 'copy', 'start': 0, 'end': len(raw['raw']), 'text': raw['raw'],
                 'reason': 'Complete unchanged actual-worker source interval'}]}
            if case not in {'missing-image', 'plain-text-control'}:
                entry['image_sha256'] = unit['image_sha256'] if case == 'matching' else '0' * 64
            packet = {'version': 'reviewed-corrections.v1', 'graph_sha256': digest(candidate),
                      'review': {'kind': 'DEVELOPMENT', 'reviewer': 'bounded local admission probe',
                                 'reason': 'Discriminate method-name dispatch from image identity'},
                      'entries': [entry]}
            expected = 'ACCEPT' if case in {'matching', 'plain-text-control'} else 'REJECT'
            try:
                admitted = corrections.admit(candidate, packet)
                actual, error = 'ACCEPT', None
            except ValueError as exc:
                admitted, actual, error = None, 'REJECT', str(exc)
                if error != 'OCR correction requires the retained source-page image identity':
                    raise
            row = {'case': case, 'expected': expected, 'actual': actual, 'error': error,
                   'source_method': raw['method'], 'source': anchor(raw),
                   'unit_image_sha256': raw.get('image_sha256'),
                   'supplied_image_sha256': entry.get('image_sha256'), 'admitted': admitted}
            cases.append(row)
        if method != {name: sha(ROOT / name) for name in method} or any(
                sha(ROOT / name) != value for name, value in frozen.items()):
            raise ValueError('Method drift during probe')
        controls = [r for r in cases if r['case'] in {'matching', 'literal-ocr-control', 'plain-text-control'}]
        if any(r['actual'] != r['expected'] for r in controls):
            raise ValueError('Discriminating control failed')
        misses = [r['case'] for r in cases if r['actual'] != r['expected']]
        if misses != ['wrong-image', 'missing-image']:
            raise ValueError('Observed behavior differs from the reviewed defect hypothesis')
        result = {'status': 'REPRODUCED_LOCAL_DEFECT', 'adverse_admissions': misses,
                  'actual_producer_method': unit['method'], 'frozen_r6_method_unchanged': True,
                  'next_action': 'After R6 completion, recognize actual OCR provenance and retain regression controls',
                  'package_failure_established': False, 'wall_seconds': time.monotonic() - tick}
    except Exception as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc),
                  'wall_seconds': time.monotonic() - tick}
    save(folder / 'cases.json', cases)
    save(folder / 'result.json', result)
    save(folder / 'manifest.json', {'files': {p.name: sha(p) for p in folder.iterdir()
                                         if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps(result))
    if result['status'] == 'FAIL':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
