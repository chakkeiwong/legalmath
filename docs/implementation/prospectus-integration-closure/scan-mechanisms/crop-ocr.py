"""Actual supported OCR on exact supplied crops; original production stays fixed."""
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

from common import ROOT, SCAN, PACKAGE, PYTHON, MODEL, start, finish, read, save, sha


def worker():
    import fitz
    baseline = read(SCAN / 'baseline/attempt-001/raw-worker.json')
    distribution = importlib.metadata.distribution('PyMuPDF')
    files = {str(p): sha(distribution.locate_file(p)) for p in distribution.files
             if str(p).endswith(('.py', '.so', 'METADATA'))}
    if (fitz.VersionBind != baseline['runtime']['pymupdf'] or
            files != baseline['runtime']['distribution_files'] or
            sha(Path(sys.executable)) != baseline['runtime']['interpreter_sha256'] or
            sha(MODEL) != baseline['runtime']['language_models']['eng']):
        raise ValueError('Pinned actual OCR runtime/model changed')
    inventory = read(SCAN / 'inventory/attempt-001/manifest.json')['files']
    oracle = read(SCAN / 'oracle.json')
    rows = []
    for target in oracle['targets']:
        name = 'crop-' + target['id'] + '.png'
        path = SCAN / 'inventory/attempt-001' / name
        if sha(path) != inventory[name]:
            raise ValueError('Supplied crop changed')
        pix = fitz.Pixmap(path)
        if pix.xres != 300 or pix.yres != 300 or pix.alpha or pix.colorspace.n != 3:
            raise ValueError('Unreviewed crop resolution or color profile')
        doc = fitz.open(stream=pix.pdfocr_tobytes(language='eng', tessdata=str(MODEL.parent), compress=True), filetype='pdf')
        if len(doc) != 1:
            raise ValueError('OCR crop has unexpected page structure')
        rows.append({'id': target['id'], 'page': target['page'], 'supplied_region': target['region'],
            'crop_sha256': sha(path), 'input_width': pix.width, 'input_height': pix.height,
            'xres': pix.xres, 'yres': pix.yres, 'output_page_box': list(doc[0].rect),
            'text': doc[0].get_text(sort=True), 'words': doc[0].get_text('words'),
            'geometry_scope': 'CROP_LOCAL_ONLY; no original-page geometry or semantic mapping asserted'})
    after = {str(p): sha(distribution.locate_file(p)) for p in distribution.files
             if str(p).endswith(('.py', '.so', 'METADATA'))}
    if after != files or sha(MODEL) != baseline['runtime']['language_models']['eng']:
        raise ValueError('Runtime/model changed during OCR')
    return {'rows': rows, 'runtime': {'python': sys.executable, 'pymupdf': fitz.VersionBind,
        'mupdf': fitz.VersionFitz, 'distribution_files': files, 'dpi': 300, 'language': 'eng',
        'CUDA_VISIBLE_DEVICES': os.environ['CUDA_VISIBLE_DEVICES'], 'OMP_THREAD_LIMIT': os.environ['OMP_THREAD_LIMIT']}}


def main():
    if sys.argv[1:] == ['--worker']:
        print(json.dumps(worker(), ensure_ascii=False))
        return
    if len(sys.argv) != 1:
        raise ValueError('Use the exact diagnostic command')
    folder, frozen, tick, oracle, _ = start('crop-ocr',
        ['timeout', '600', '.venv/bin/python', str(Path(__file__).relative_to(ROOT))])
    try:
        command = [str(PYTHON), str(Path(__file__)), '--worker']
        save(folder / 'worker-command.json', {'argv': command, 'timeout_seconds': 300})
        run = subprocess.run(command, cwd=ROOT, env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'OMP_THREAD_LIMIT': '1'},
                             capture_output=True, timeout=300)
        (folder / 'worker.stdout').write_bytes(run.stdout)
        (folder / 'worker.stderr').write_bytes(run.stderr)
        if run.returncode:
            raise ValueError('OCR worker failed; inspect retained stderr')
        actual = json.loads(run.stdout)
        save(folder / 'raw-worker.json', actual)
        if [r['id'] for r in actual['rows']] != [t['id'] for t in oracle['targets']]:
            raise ValueError('Target denominator/order changed')
        original = read(SCAN / 'analysis/attempt-001/critical-occurrences.json')
        rows = []
        for target, current, prior in zip(oracle['targets'], actual['rows'], original):
            rows.append({'id': target['id'], 'expected': target['text'],
                'baseline_region_text': prior['supplied_region_text'], 'baseline_exact': prior['supplied_region_exact'],
                'crop_text': current['text'], 'crop_exact': ' '.join(current['text'].split()) == ' '.join(target['text'].split()),
                'blank': not current['text'].strip(), 'crop_sha256': current['crop_sha256']})
        save(folder / 'comparisons.json', rows)
        lost = [r['id'] for r in rows if r['baseline_exact'] and not r['crop_exact']]
        gained = [r['id'] for r in rows if not r['baseline_exact'] and r['crop_exact']]
        result = {'status': 'PASS', 'target_denominator': len(rows), 'baseline_supplied_region_exact': 16,
            'crop_exact': sum(r['crop_exact'] for r in rows), 'lost_passing_targets': lost,
            'gained_exact_targets': gained, 'blank_targets': [r['id'] for r in rows if r['blank']],
            'candidate_screen': 'PASS' if not lost else 'FAIL',
            'all_critical_text': 'PASS' if all(r['crop_exact'] for r in rows) else 'FAIL',
            'automatic_relation_proposals': 0, 'production_method_changed': False,
            'scope': 'Actual English OCR with supplied crop boundaries; no package ranking or semantic admission'}
    except subprocess.TimeoutExpired as exc:
        (folder / 'worker.stdout').write_bytes(exc.stdout or b'')
        (folder / 'worker.stderr').write_bytes(exc.stderr or b'')
        result = {'status': 'FAIL', 'error': 'Native worker exceeded reviewed 300-second bound'}
    except Exception as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc)}
    finish(folder, frozen, tick, result)


if __name__ == '__main__':
    main()
