"""Current OCR and complete service output against the frozen BES source review."""
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
INTERPRETER = Path('/home/chakwong/miniconda3/envs/tfgpu/bin/python')
MODEL = ROOT / 'docs/prospectus/closure-2026-10-05/tools/eng.traineddata'
MODEL_SHA = '7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor import closure_program, extraction, service  # noqa: E402
from legalmath.prospectus.successor.contracts import digest  # noqa: E402
from legalmath.prospectus.successor.occurrences import anchor  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def verify(folder):
    manifest = read(folder / 'manifest.json')['files']
    actual = {str(p.relative_to(folder)) for p in folder.rglob('*')
              if p.is_file() and p.name != 'manifest.json'}
    if actual != set(manifest) or any(sha(folder / name) != value for name, value in manifest.items()):
        raise ValueError('Evidence manifest changed: ' + str(folder))
    if read(folder / 'result.json')['status'] != 'PASS':
        raise ValueError('Required evidence failed: ' + str(folder))


def normalize(text):
    return ' '.join(text.split())


def project(target, graph, page, oracle):
    """Project supplied image cells onto original word occurrences, without sorting."""
    x0, y0, x1, y1 = target['region']
    # pdfocr_tobytes preserves the rendered pixmap's 300-DPI physical size.
    width, height = page['image_width'] * 72 / 300, page['image_height'] * 72 / 300
    sources, boxes = [], []
    for unit in graph['units']:
        if unit['page'] != target['page']:
            continue
        runs = []
        for word in unit.get('words', []):
            left, top, right, bottom = word['bbox']
            cx = (left + right) / 2 / width * oracle['images']['width']
            cy = (top + bottom) / 2 / height * oracle['images']['height']
            if not (x0 <= cx < x1 and y0 <= cy < y1):
                continue
            a, b = word['start'], word['end']
            if unit['raw'][a:b] != word['text']:
                raise ValueError('Raw word offsets changed')
            if runs and a == runs[-1][1] + 1 and unit['raw'][runs[-1][1]:a] == ' ':
                runs[-1][1] = b
            else:
                runs.append([a, b])
            boxes.append({'unit': unit['id'], 'start': a, 'end': b, 'raw': word['text'],
                          'bbox': word['bbox'], 'review_image_center': [cx, cy]})
        sources.extend(anchor(unit, a, b) for a, b in runs)
    projected = ' '.join(s['quote'] for s in sources)
    service_text = ' '.join(u['raw'] for u in graph['units'] if u['page'] == target['page'])
    return {'id': target['id'], 'page': target['page'], 'expected': target['text'],
            'region': target['region'], 'image_sha256': page['image_sha256'],
            'worker_page_text_contains_exact': normalize(target['text']) in normalize(page['text']),
            'service_page_text_contains_exact': normalize(target['text']) in normalize(service_text),
            'supplied_region_text': projected,
            'supplied_region_exact': normalize(projected) == normalize(target['text']),
            'raw_sources': sources, 'raw_words': boxes,
            'location_method': 'SUPPLIED_REVIEWED_REGION; raw occurrence order preserved',
            'character_corrections': False}


def main():
    if sys.flags.optimize or len(sys.argv) != 1:
        raise ValueError('Exact invocation with assertions enabled required')
    if Path(extraction.__file__).resolve() != ROOT / 'src/legalmath/prospectus/successor/extraction.py':
        raise ValueError('Wrong checkout imported')
    completed = BASE / 'worker-recovery/validation-001'
    r6_started = read(completed / 'started.json')
    if any(sha(ROOT / name) != value for name, value in r6_started['method'].items()):
        raise ValueError('Completed worker-recovery method changed')
    r6_progress = read(completed / 'progress.json')
    if (completed / 'result.json').exists():
        verify(completed)
        required_phases = set(closure_program.DAG)
    elif r6_progress['status'] == 'RUNNING':
        required_phases = {'R0', 'R1', 'R2', 'R3'}
    else:
        raise ValueError('R6 is neither active under its frozen method nor complete PASS')
    phases = closure_program.status(ROOT)
    if not all(row['current'] and row['artifact_valid'] and row['engineering_checks'] == 'PASS'
               for row in phases['phases'] if row['phase'] in required_phases):
        raise ValueError('Required source-intake phase receipts must be current PASS')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if subprocess.run(['git', 'merge-base', '--is-ancestor', r6_started['git_commit'], commit], cwd=ROOT).returncode:
        raise ValueError('R6 comparator is not descended from the protected baseline')
    verify(PACKAGE / 'inventory/attempt-001')
    freeze = read(PACKAGE / 'source-review-freeze.json')
    if any(sha(PACKAGE / name) != value for name, value in freeze['files'].items()):
        raise ValueError('Pre-OCR source review changed')
    oracle = read(PACKAGE / 'oracle.json')
    if sha(ROOT / oracle['source']) != oracle['source_sha256'] or sha(MODEL) != MODEL_SHA:
        raise ValueError('Protected source/model changed')
    if sha(INTERPRETER) != '6f38473e7e297ce26d0daf41f8c5d7ce5b8b92859ca905a8145a83a881f0b790':
        raise ValueError('Pinned OCR interpreter changed')
    folder = PACKAGE / 'baseline/attempt-001'
    if folder.exists():
        raise ValueError('Inspect the existing attempt; unchanged retries are forbidden')
    folder.mkdir(parents=True)
    bindings = [*sorted((ROOT / 'src/legalmath').rglob('*.py')), Path(__file__), PLAN,
                PACKAGE / 'oracle.json', PACKAGE / 'source-review-freeze.json',
                PACKAGE / 'inventory/attempt-001/manifest.json', completed / 'started.json']
    method = {str(p.relative_to(ROOT)): sha(p) for p in bindings}
    command = ['timeout', '900', '.venv/bin/python', str(Path(__file__).relative_to(ROOT))]
    save(folder / 'started.json', {'version': 'bes-current-ocr-baseline.v1', 'git_commit': commit,
         'command': command, 'method': method, 'started_at': datetime.now(timezone.utc).isoformat(),
         'r6_state_at_admission': r6_progress,
         'source_state': 'Exact recorded snapshot; R6 modifications may be uncommitted; not a clean installed release',
         'plan_file': str(PLAN.relative_to(ROOT)), 'result_file': str((folder / 'result.json').relative_to(ROOT)),
         'data_version': oracle['source_sha256'], 'random_seeds': 'N/A fixed deterministic source',
         'cpu_gpu': 'CPU; GPU deliberately hidden; no GPU probing',
         'environment': {'orchestrator': sys.executable, 'ocr_interpreter': str(INTERPRETER),
                         'ocr_interpreter_sha256': sha(INTERPRETER), 'CUDA_VISIBLE_DEVICES': '-1'},
         'model_sha256': MODEL_SHA, 'timeout_seconds': 900,
         'evidence_limit_bytes': 100_000_000, 'metadata_reserve_bytes': 1_048_576})
    document = {'id': 'bes-final-terms-2011', 'path': oracle['source'], 'sha256': oracle['source_sha256'],
                'page_count': 6, 'language': 'en; Portuguese clearing-system name',
                'authority': 'Retained issuer final terms; authenticity not independently established',
                'document_date': '2011-07-14T00:00:00Z', 'known_from': '2026-10-04T00:00:00Z',
                'scan_profile': {'version': 'pymupdf-scan.v1', 'dpi': 300, 'language': 'eng',
                   'max_pages': 6, 'tessdata': str(MODEL.parent.relative_to(ROOT)), 'models': {'eng': MODEL_SHA}}}
    request = {'version': 'prospectus-successor.v3', 'bundle': {'instrument_id': 'PTBEQBOM0010',
         'purpose': 'review', 'issue_date': '2011-07-15T00:00:00Z',
         'effective_at': '2011-07-15T00:00:00Z', 'known_at': '2026-10-11T00:00:00Z',
         'documents': [document]}}
    save(folder / 'request.json', request)
    tick = time.monotonic()
    try:
        os.environ['LEGALMATH_OCR_PYTHON'] = str(INTERPRETER)
        start_raw = time.monotonic()
        raw = extraction.scan(document, ROOT)
        raw_seconds = time.monotonic() - start_raw
        save(folder / 'raw-worker.json', raw)
        images = read(PACKAGE / 'inventory/attempt-001/pages.json')['pages']
        if raw['source_sha256'] != oracle['source_sha256'] or raw['page_count'] != 6:
            raise ValueError('OCR source/page count changed')
        if [p['page'] for p in raw['pages']] != list(range(1, 7)):
            raise ValueError('OCR lost the exact page sequence')
        for page, image in zip(raw['pages'], images, strict=True):
            for key in ('page', 'image_sha256', 'image_width', 'image_height'):
                if page[key] != image[key]:
                    raise ValueError('OCR page image differs from the independently rendered source')
            if not page['text'].strip() or not page['words']:
                raise ValueError('A known nonblank page was unread by OCR')
        if raw['runtime']['pymupdf'] != '1.27.2.2' or not raw['runtime'].get('distribution_files'):
            raise ValueError('Unknown actual OCR distribution')
        if raw_seconds > 120:
            raise ValueError('Review measured scheduling before a second OCR launch')
        start_service = time.monotonic()
        report = service.assess(request, ROOT)
        service_seconds = time.monotonic() - start_service
        save(folder / 'service-report.json', report)
        graph = report['source_map']
        if graph['documents'][0]['ocr_sha256'] != digest(raw):
            raise ValueError('Fresh worker output differs between raw and service launches')
        if sorted(report['questions']) != ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6']:
            raise ValueError('Service question inventory changed')
        if sorted({u['page'] for u in graph['units']}) != list(range(1, 7)):
            raise ValueError('Service lost a page')
        rows = [project(target, graph, raw['pages'][target['page'] - 1], oracle)
                for target in oracle['targets']]
        if any(not r['raw_sources'] for r in rows):
            raise ValueError('Critical supplied region has no original word occurrences')
        save(folder / 'critical-occurrences.json', rows)
        if method != {name: sha(ROOT / name) for name in method}:
            raise ValueError('Method changed during trial')
        payload = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
        if payload + 1_048_576 > 100_000_000:
            raise ValueError('Evidence cap exceeded')
        result = {'status': 'PASS', 'scope': 'Valid current-method raw and service baseline, not automatic acceptance',
                  'page_count': 6, 'critical_targets': len(rows),
                  'raw_worker_seconds': raw_seconds, 'service_seconds': service_seconds,
                  'worker_page_text_exact_presence': sum(r['worker_page_text_contains_exact'] for r in rows),
                  'service_page_text_exact_presence': sum(r['service_page_text_contains_exact'] for r in rows),
                  'supplied_region_exact': sum(r['supplied_region_exact'] for r in rows),
                  'supplied_region_misses': [r['id'] for r in rows if not r['supplied_region_exact']],
                  'automatic_relationships': {'expected': len(oracle['relations']), 'proposed': 0,
                     'reason': 'Current raw intake emits words; this request supplies no reviewed row/qualification relations'},
                  'automatic_candidate': 'NOT_PROMOTED; exact text alone cannot establish required relationships',
                  'question_statuses': {key: value['status'] for key, value in report['questions'].items()},
                  'fresh_outputs_equal': True, 'method_unchanged': True,
                  'evidence_payload_bytes': payload, 'wall_seconds': time.monotonic() - tick,
                  'next_action': 'Inspect misses, then admit image-supported correction and actual downstream omission controls'}
    except Exception as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc),
                  'wall_seconds': time.monotonic() - tick}
    save(folder / 'result.json', result)
    save(folder / 'manifest.json', {'files': {str(p.relative_to(folder)): sha(p)
         for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps(result), flush=True)
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
