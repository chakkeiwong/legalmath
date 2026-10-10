"""Author exact assisted intervals from the frozen BES page review and raw trial."""
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
PLAN = ROOT / 'docs/plans/prospectus-real-scan-2026-10-11.md'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor.anchors import bind  # noqa: E402
from legalmath.prospectus.successor.occurrences import anchor  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    analysis = PACKAGE / 'analysis/attempt-001'
    for folder in (analysis, PACKAGE / 'baseline/attempt-001'):
        manifest = read(folder / 'manifest.json')['files']
        if any(sha(folder / p) != value for p, value in manifest.items()):
            raise ValueError('Retained raw/analysis evidence changed')
    freeze = read(PACKAGE / 'source-review-freeze.json')
    if any(sha(PACKAGE / p) != value for p, value in freeze['files'].items()):
        raise ValueError('Pre-OCR source review changed')
    graph = read(PACKAGE / 'baseline/attempt-001/service-report.json')['source_map']
    units = {u['id']: u for u in graph['units']}
    rows = {r['id']: r for r in read(analysis / 'critical-occurrences.json')}
    oracle = read(PACKAGE / 'oracle.json')
    replacements = {
        'ratings': [('S&P:', 'S & P:')],
        'ratings-qualification': [('usinga', 'using a')],
        'isin': [('PTBEQBOMO0010', 'PTBEQBOM0010')],
        'clearing-label': [('S.A/', 'S.A./')],
        'clearing-value': [('Liquidacdoe', 'Liquidação e'), ('Mobilidrios', 'Mobiliários')],
        'intended-label': [('ina', 'in a')],
    }
    folder = PACKAGE / 'authoring/attempt-001'
    if folder.exists():
        raise ValueError('Preserve prior authoring; no unchanged repeat')
    folder.mkdir(parents=True)
    method = {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), PLAN, PACKAGE / 'oracle.json',
              PACKAGE / 'source-review-freeze.json', analysis / 'manifest.json', PACKAGE / 'baseline/attempt-001/manifest.json']}
    save(folder / 'started.json', {'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
         'command': ['timeout', '60', '.venv/bin/python', str(Path(__file__).relative_to(ROOT))],
         'method': method, 'started_at': datetime.now(timezone.utc).isoformat(),
         'environment': {'python': sys.executable, 'CUDA_VISIBLE_DEVICES': '-1'},
         'cpu_gpu': 'CPU; GPU intentionally hidden; no OCR/native worker run',
         'random_seeds': 'N/A deterministic supplied source review', 'data_version': oracle['source_sha256'],
         'plan_file': str(PLAN.relative_to(ROOT)), 'result_file': str((folder / 'result.json').relative_to(ROOT)),
         'timeout_seconds': 60, 'evidence_limit_bytes': 5_000_000})
    tick = time.monotonic()
    try:
        targets, edits = [], []
        for expected in oracle['targets']:
            row = rows[expected['id']]
            sources = row['raw_sources']
            selection = 'Predeclared supplied image region, original occurrence order'
            if expected['id'] == 'responsibility':
                unit = units['bes-final-terms-2011:p4:ocr10']
                if unit['raw'] != 'The Issuer accepts responsibility forthe information contained inthese FinalC)':
                    raise ValueError('Explicit reviewed responsibility occurrence changed')
                sources = [anchor(unit)]
                selection = 'Explicit image-reviewed line; centre rule failed because signature inflated word boxes'
            segments, seen = [], set()
            for index, source in enumerate(sources):
                bind(graph, source)
                unit = units[source['unit']]
                text = source['quote']
                if expected['id'] == 'responsibility':
                    text = expected['text']
                else:
                    for old, new in replacements.get(expected['id'], []):
                        if old in text:
                            if old in seen or text.count(old) != 1:
                                raise ValueError('Ambiguous reviewed correction')
                            seen.add(old)
                            text = text.replace(old, new)
                segment = {'source': source, 'display': text, 'image_sha256': unit['image_sha256']}
                if text != source['quote']:
                    identity = expected['id'] + '-segment-' + str(index)
                    segment['correction'] = identity
                    edits.append({'id': identity, 'source': source, 'image_sha256': unit['image_sha256'],
                                  'operations': [{'kind': 'replace', 'start': 0, 'end': len(source['quote']),
                                                  'text': text, 'reason': 'Transcribed from independently inspected original page crop; whole-interval correspondence'}]})
                segments.append(segment)
            if seen != {old for old, _ in replacements.get(expected['id'], [])}:
                raise ValueError('Reviewed replacement did not find its exact original occurrence')
            text = ' '.join(s['display'] for s in segments)
            if ' '.join(text.split()) != expected['text']:
                raise ValueError('Assisted display differs from the pre-OCR oracle: ' + expected['id'])
            targets.append({'id': expected['id'], 'page': expected['page'], 'role': expected['role'],
                            'expected_text': expected['text'], 'display': text, 'segments': segments,
                            'selection': selection,
                            'effect': 'unknown' if expected['id'] == 'responsibility' else
                                      'coupon' if expected['id'] in {'coupon-rate', 'payment-dates', 'day-count'} else 'none'})
        if len(edits) != 8 or len(targets) != 23:
            raise ValueError('Reviewed fixed target/correction inventory differs')
        packet = {'version': 'bes-assisted-source-review.v1', 'oracle_sha256': sha(PACKAGE / 'oracle.json'),
                  'raw_worker_sha256': sha(PACKAGE / 'baseline/attempt-001/raw-worker.json'),
                  'source_sha256': oracle['source_sha256'], 'review': {'kind': 'DEVELOPMENT',
                     'reviewer': 'Codex source-image reading',
                     'reason': 'Exact original page cells and complete printed qualifications; no independent legal acceptance'},
                  'targets': targets, 'corrections': edits, 'relations': oracle['relations'],
                  'unresolved': oracle['required_unresolved'],
                  'scope': 'Assisted source preservation; other meanings and incorporated sources remain unknown'}
        save(folder / 'review.json', packet)
        if method != {p: sha(ROOT / p) for p in method}:
            raise ValueError('Authoring method changed')
        result = {'status': 'PASS', 'targets': len(targets), 'replacements': len(edits),
                  'supplied_relations': len(packet['relations']), 'manual_geometry_recovery': ['responsibility'],
                  'all_displays_equal_frozen_oracle': True, 'service_executed': False,
                  'scope': 'Source packet only; consumer and image-guard integration still required',
                  'wall_seconds': time.monotonic() - tick}
    except Exception as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc),
                  'wall_seconds': time.monotonic() - tick}
    save(folder / 'result.json', result)
    save(folder / 'manifest.json', {'files': {p.name: sha(p) for p in folder.iterdir()
                                         if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps(result))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
