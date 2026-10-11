"""Retain all frozen targets when the raw region-selection candidate misses one."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parent
PLAN = ROOT / 'docs/plans/prospectus-real-scan-2026-10-11.md'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor.contracts import digest  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    baseline = PACKAGE / 'baseline/attempt-001'
    manifest = read(baseline / 'manifest.json')['files']
    actual = {str(p.relative_to(baseline)) for p in baseline.rglob('*')
              if p.is_file() and p.name != 'manifest.json'}
    if actual != set(manifest) or any(sha(baseline / p) != value for p, value in manifest.items()):
        raise ValueError('Failed attempt evidence changed')
    failure = read(baseline / 'result.json')
    if failure['status'] != 'FAIL' or failure['error'] != 'ValueError: Critical supplied region has no original word occurrences':
        raise ValueError('Unexpected prior failure; inspect before analysis')
    started = read(baseline / 'started.json')
    for name, value in started['method'].items():
        if name != str(PLAN.relative_to(ROOT)) and sha(ROOT / name) != value:
            raise ValueError('Original worker or analysis method changed: ' + name)
    raw = read(baseline / 'raw-worker.json')
    report = read(baseline / 'service-report.json')
    graph = report['source_map']
    oracle = read(PACKAGE / 'oracle.json')
    if graph['documents'][0]['ocr_sha256'] != digest(raw):
        raise ValueError('Actual raw and service extraction differ')
    if raw['source_sha256'] != oracle['source_sha256'] or raw['page_count'] != 6:
        raise ValueError('Actual source/page inventory differs')
    pages = read(PACKAGE / 'inventory/attempt-001/pages.json')['pages']
    for page, expected in zip(raw['pages'], pages, strict=True):
        if any(page[key] != expected[key] for key in ('page', 'image_sha256', 'image_width', 'image_height')):
            raise ValueError('Actual page identity changed')
    spec = importlib.util.spec_from_file_location('bes_baseline_analysis', PACKAGE / 'run-baseline.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    folder = PACKAGE / 'analysis/attempt-001'
    if folder.exists():
        raise ValueError('Retain prior analysis; no unchanged repeat')
    folder.mkdir(parents=True)
    method = {str(p.relative_to(ROOT)): sha(p) for p in
              [Path(__file__), PLAN, PACKAGE / 'run-baseline.py', PACKAGE / 'oracle.json', baseline / 'manifest.json']}
    save(folder / 'started.json', {'command': ['timeout', '60', '.venv/bin/python', str(Path(__file__).relative_to(ROOT))],
         'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
         'method': method, 'started_at': datetime.now(timezone.utc).isoformat(),
         'environment': {'python': sys.executable, 'CUDA_VISIBLE_DEVICES': '-1'},
         'cpu_gpu': 'CPU; GPU intentionally hidden; no OCR rerun', 'data_version': oracle['source_sha256'],
         'random_seeds': 'N/A deterministic analysis', 'timeout_seconds': 60, 'evidence_limit_bytes': 5_000_000,
         'plan_file': str(PLAN.relative_to(ROOT)), 'result_file': str((folder / 'result.json').relative_to(ROOT))})
    tick = time.monotonic()
    try:
        rows = [module.project(t, graph, raw['pages'][t['page'] - 1], oracle) for t in oracle['targets']]
        save(folder / 'critical-occurrences.json', rows)
        if method != {name: sha(ROOT / name) for name in method}:
            raise ValueError('Analysis method changed')
        result = {'status': 'PASS', 'scope': 'Complete valid analysis; raw extraction/geometry candidate fails promotion',
                  'primary_automatic_criterion': 'FAIL', 'supplied_geometry_criterion': 'FAIL',
                  'page_count': 6, 'target_denominator': len(rows),
                  'worker_page_text_exact_presence': sum(r['worker_page_text_contains_exact'] for r in rows),
                  'service_page_text_exact_presence': sum(r['service_page_text_contains_exact'] for r in rows),
                  'supplied_region_exact': sum(r['supplied_region_exact'] for r in rows),
                  'unmapped_targets': [r['id'] for r in rows if not r['raw_sources']],
                  'supplied_region_misses': [r['id'] for r in rows if not r['supplied_region_exact']],
                  'automatic_relations': {'expected': len(oracle['relations']), 'proposed': 0},
                  'question_statuses': {key: value['status'] for key, value in report['questions'].items()},
                  'fresh_outputs_equal': True, 'method_unchanged_except_reviewed_plan': True,
                  'package_fundamental_limitation_established': False,
                  'next_action': 'Image-supported assisted mapping with the repaired image guard and downstream omission controls',
                  'wall_seconds': time.monotonic() - tick}
    except Exception as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc),
                  'wall_seconds': time.monotonic() - tick}
    save(folder / 'result.json', result)
    if sum(p.stat().st_size for p in folder.iterdir() if p.is_file()) > 5_000_000:
        raise ValueError('Analysis evidence bound exceeded')
    save(folder / 'manifest.json', {'files': {p.name: sha(p) for p in folder.iterdir()
                                         if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps(result), flush=True)
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
