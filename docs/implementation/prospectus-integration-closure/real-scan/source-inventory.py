"""Bind the original BES pages and manually reviewed regions without running OCR."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parent
PLAN = ROOT / 'docs/plans/prospectus-real-scan-2026-10-11.md'
ORACLE = PACKAGE / 'oracle.json'
INTERPRETER = Path('/home/chakwong/miniconda3/envs/tfgpu/bin/python')
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def render(folder):
    import fitz
    if fitz.VersionBind != '1.27.2.2':
        raise ValueError('Reviewed PyMuPDF runtime changed')
    oracle = read(ORACLE)
    source = ROOT / oracle['source']
    if sha(source) != oracle['source_sha256']:
        raise ValueError('Protected PDF changed')
    document = fitz.open(source)
    if len(document) != oracle['page_count']:
        raise ValueError('Protected page count changed')
    rows = []
    for number, page in enumerate(document, 1):
        image = page.get_pixmap(dpi=300, colorspace=fitz.csRGB)
        data = image.tobytes('png')
        expected = oracle['images']['pages'][number - 1]
        actual = hashlib.sha256(data).hexdigest()
        row = {'page': number, 'image_sha256': actual, 'image_width': image.width,
               'image_height': image.height, 'pdf_width': page.rect.width,
               'pdf_height': page.rect.height, 'historical_render_equal': actual == expected['image_sha256']}
        if not row['historical_render_equal']:
            (folder / f'page-{number:03d}.png').write_bytes(data)
            row['new_image'] = f'page-{number:03d}.png'
        rows.append(row)
        for target in oracle['targets']:
            if target['page'] != number:
                continue
            x0, y0, x1, y1 = target['region']
            clip = fitz.Rect(x0 / oracle['images']['width'] * page.rect.width,
                             y0 / oracle['images']['height'] * page.rect.height,
                             x1 / oracle['images']['width'] * page.rect.width,
                             y1 / oracle['images']['height'] * page.rect.height)
            crop = page.get_pixmap(dpi=300, colorspace=fitz.csRGB, clip=clip)
            crop.save(folder / ('crop-' + target['id'] + '.png'))
    return {'page_count': len(document), 'pages': rows,
            'runtime': {'interpreter': sys.executable, 'fitz_module': fitz.__file__,
                        'pymupdf': fitz.VersionBind, 'mupdf': fitz.VersionFitz,
                        'CUDA_VISIBLE_DEVICES': os.environ['CUDA_VISIBLE_DEVICES']},
            'ocr_executed': False, 'crop_selection': 'MANUALLY_SUPPLIED_IMAGE_REGIONS'}


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--render':
        folder = Path(sys.argv[2]).resolve()
        if not folder.is_relative_to(PACKAGE / 'inventory'):
            raise ValueError('Output must be inside this evidence package')
        print(json.dumps(render(folder), ensure_ascii=False))
        return
    if len(sys.argv) != 1:
        raise ValueError('Use the exact preparation command')
    oracle = read(ORACLE)
    if len({t['id'] for t in oracle['targets']}) != len(oracle['targets']):
        raise ValueError('Distinct fixed target identities required')
    if [r['page'] for r in oracle['images']['pages']] != list(range(1, 7)):
        raise ValueError('Exact six-page inventory required')
    if sha(INTERPRETER) != '6f38473e7e297ce26d0daf41f8c5d7ce5b8b92859ca905a8145a83a881f0b790':
        raise ValueError('Pinned OCR interpreter changed')
    image_dir = ROOT / oracle['images']['directory']
    bindings = [Path(__file__), PLAN, ORACLE, ROOT / oracle['source']]
    for row in oracle['images']['pages']:
        for suffix, key in [('-review', 'review_sha256'), ('', 'image_sha256')]:
            path = image_dir / f"page-{row['page']:03d}{suffix}.png"
            if sha(path) != row[key]:
                raise ValueError('Previously inspected source image changed')
            if suffix and struct.unpack('>II', path.read_bytes()[16:24]) != (1074, 1518):
                raise ValueError('Reviewed coordinate system changed')
            bindings.append(path)
    for target in oracle['targets']:
        x0, y0, x1, y1 = target['region']
        if not (1 <= target['page'] <= 6 and 0 <= x0 < x1 <= 1074 and 0 <= y0 < y1 <= 1518 and target['text']):
            raise ValueError('Invalid predeclared critical region')
    active = ROOT / 'docs/implementation/prospectus-integration-closure/worker-recovery/validation-001/started.json'
    frozen = read(active)['method']
    if any(sha(ROOT / path) != value for path, value in frozen.items()):
        raise ValueError('Active worker-recovery method drift')
    method = {str(p.relative_to(ROOT)): sha(p) for p in bindings}
    folder = PACKAGE / 'inventory/attempt-001'
    if folder.exists():
        raise ValueError('Inspect retained attempt before any changed-method retry')
    folder.mkdir(parents=True)
    argv = [str(INTERPRETER), str(Path(__file__)), '--render', str(folder)]
    started = {'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'command': ['timeout', '60', '.venv/bin/python', str(Path(__file__).relative_to(ROOT))],
               'render_command': argv, 'method': method,
               'frozen_r6_manifest_sha256': sha(active), 'ocr_interpreter_sha256': sha(INTERPRETER),
               'started_at': datetime.now(timezone.utc).isoformat(), 'timeout_seconds': 60,
               'environment': {'orchestrator': sys.executable, 'CUDA_VISIBLE_DEVICES': '-1'},
               'cpu_gpu': 'CPU; GPU deliberately hidden; no GPU probing',
               'data_version': oracle['source_sha256'], 'random_seeds': 'N/A deterministic rendering',
               'plan_file': str(PLAN.relative_to(ROOT)),
               'result_file': str((folder / 'result.json').relative_to(ROOT)),
               'evidence_limit_bytes': 100_000_000, 'metadata_reserve_bytes': 1_048_576}
    save(folder / 'started.json', started)
    tick = time.monotonic()
    try:
        run = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=50,
                             env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1'})
        (folder / 'render.stderr').write_bytes(run.stderr)
        if run.returncode:
            (folder / 'render.stdout').write_bytes(run.stdout)
            raise RuntimeError('Rendering failed: ' + str(run.returncode))
        rendered = json.loads(run.stdout)
        save(folder / 'pages.json', rendered)
        if method != {name: sha(ROOT / name) for name in method}:
            raise RuntimeError('Source preparation method changed')
        if any(sha(ROOT / path) != value for path, value in frozen.items()):
            raise RuntimeError('Active R6 method changed during preparation')
        payload = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
        if payload + 1_048_576 > 100_000_000:
            raise RuntimeError('Evidence cap exceeded')
        result = {'status': 'PASS', 'page_count': rendered['page_count'],
                  'critical_targets': len(oracle['targets']), 'reviewed_relationships': len(oracle['relations']),
                  'historical_render_equal': all(p['historical_render_equal'] for p in rendered['pages']),
                  'frozen_r6_method_unchanged': True, 'evidence_payload_bytes': payload,
                  'scope': 'Original-page rendering and supplied-region preparation; OCR and consumer not run',
                  'wall_seconds': time.monotonic() - tick}
    except Exception as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc),
                  'wall_seconds': time.monotonic() - tick}
    save(folder / 'result.json', result)
    save(folder / 'manifest.json', {'files': {str(p.relative_to(folder)): sha(p)
         for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps(result))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
