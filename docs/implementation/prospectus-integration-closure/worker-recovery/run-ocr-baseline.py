"""Retain a measured current-worker OCR baseline on copied scan inputs."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parent
PLAN = ROOT / 'docs/plans/prospectus-worker-recovery-2026-10-10.md'
BASE = ROOT / 'docs/implementation/prospectus-integration-closure'
REQUEST = BASE / 'packages/scan/attempt-001/request.json'
ORIGINAL = BASE / 'packages/scan/attempt-001/new-scan.pdf'
MODEL = ROOT / 'docs/prospectus/closure-2026-10-05/tools/eng.traineddata'
INTERPRETER = Path('/home/chakwong/miniconda3/envs/tfgpu/bin/python')
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor import extraction, service  # noqa: E402
from legalmath.prospectus.successor.contracts import digest  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def verified_probe():
    folder = PACKAGE / 'model-path/attempt-002'
    manifest = json.loads((folder / 'manifest.json').read_text())
    if any(sha(folder / name) != value for name, value in manifest['files'].items()):
        raise RuntimeError('Path repair diagnostic manifest changed')
    if json.loads((folder / 'result.json').read_text())['status'] != 'REPAIR_PASS':
        raise RuntimeError('Path repair did not pass')
    return sha(folder / 'manifest.json')


def main():
    if sys.flags.optimize:
        raise RuntimeError('Assertions must be enabled')
    if Path(extraction.__file__).resolve() != ROOT / 'src/legalmath/prospectus/successor/extraction.py':
        raise RuntimeError('Wrong checkout imported')
    baseline = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if baseline != 'dd6724963a2955536093fc1016031ea11803501a':
        raise RuntimeError('Committed coupon baseline changed')
    probe_manifest = verified_probe()
    requested = json.loads(REQUEST.read_text())
    document = requested['bundle']['documents'][0]
    expected_pdf = '3054b4a3af3c6c7d13c0016f6311491423ec7c296c7f6784a643c9bcf1123a68'
    expected_model = '7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2'
    if sha(ORIGINAL) != document['sha256'] or sha(ORIGINAL) != expected_pdf:
        raise RuntimeError('Protected English scan changed')
    if sha(MODEL) != document['scan_profile']['models']['eng'] or sha(MODEL) != expected_model:
        raise RuntimeError('Protected English OCR model changed')
    if sha(INTERPRETER) != '6f38473e7e297ce26d0daf41f8c5d7ce5b8b92859ca905a8145a83a881f0b790':
        raise RuntimeError('Pinned OCR interpreter changed')
    folder = PACKAGE / 'ocr-baseline/attempt-001'
    if folder.exists():
        raise RuntimeError('Inspect retained baseline before any changed-method retry')
    folder.mkdir(parents=True)
    paths = [*sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.py')),
        Path(__file__), PLAN, REQUEST]
    method = {str(path.relative_to(ROOT)): sha(path) for path in paths}
    started = {'version': 'worker-ocr-baseline.v1', 'git_commit': baseline,
        'command': ['timeout', '300', '.venv/bin/python', str(Path(__file__).relative_to(ROOT))],
        'method': method, 'probe_manifest_sha256': probe_manifest,
        'started_at': datetime.now(timezone.utc).isoformat(),
        'timeout_seconds': 300, 'evidence_limit_bytes': 100_000_000,
        'metadata_reserve_bytes': 1_048_576,
        'environment': {'orchestrator': sys.executable, 'ocr_interpreter': str(INTERPRETER),
            'ocr_interpreter_sha256': sha(INTERPRETER), 'CUDA_VISIBLE_DEVICES': '-1',
            'extraction_module': str(Path(extraction.__file__).resolve())},
        'data_version': {'english_pdf_sha256': expected_pdf, 'english_model_sha256': expected_model},
        'seeds': 'N/A deterministic retained scan', 'plan_file': str(PLAN.relative_to(ROOT)),
        'result_file': str((folder / 'result.json').relative_to(ROOT))}
    save(folder / 'started.json', started)
    tick = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix='prospectus-worker-ocr-', dir='/tmp') as location:
            isolated = Path(location)
            models = isolated / 'models'
            models.mkdir()
            shutil.copy2(ORIGINAL, isolated / 'scan.pdf')
            shutil.copy2(MODEL, models / 'eng.traineddata')
            if sha(isolated / 'scan.pdf') != expected_pdf or sha(models / 'eng.traineddata') != expected_model:
                raise RuntimeError('Isolated copy differs from protected inputs')
            document['path'] = 'scan.pdf'
            document['scan_profile']['tessdata'] = 'models'
            os.environ['LEGALMATH_OCR_PYTHON'] = str(INTERPRETER)
            start_raw = time.monotonic()
            raw = extraction.scan(document, isolated)
            raw_seconds = time.monotonic() - start_raw
            if raw_seconds > 120:
                raise RuntimeError('First worker exceeded 120 seconds; review schedule before second launch')
            if raw['source_sha256'] != expected_pdf or raw['page_count'] != 2:
                raise RuntimeError('OCR source or page count changed')
            pages = raw['pages']
            if [p['page'] for p in pages] != [1, 2]:
                raise RuntimeError('OCR page sequence changed')
            phrases = ('The Notes are unsecured obligations of the Issuer.',
                'The Notes will be redeemed at maturity.')
            if not all(phrase in pages[0]['text'] for phrase in phrases) or not pages[0]['words']:
                raise RuntimeError('First page lost its reviewed words')
            if pages[1]['text'].strip() or pages[1]['words']:
                raise RuntimeError('Blank second page was not retained')
            images = [p.get('image_sha256') for p in pages]
            if not all(isinstance(value, str) and len(value) == 64 for value in images) or len(set(images)) != 2:
                raise RuntimeError('Page image identities missing or duplicated')
            runtime = raw['runtime']
            if (runtime.get('pymupdf') != '1.27.2.2' or
                    runtime.get('interpreter_sha256') != sha(INTERPRETER) or
                    runtime.get('worker_sha256') != sha(ROOT / 'src/legalmath/prospectus/successor/ocr_worker.py') or
                    runtime.get('language_models') != {'eng': expected_model} or
                    not runtime.get('distribution_files')):
                raise RuntimeError('Actual OCR runtime identity differs')
            save(folder / 'raw-worker.json', raw)
            start_service = time.monotonic()
            report = service.assess(requested, isolated)
            service_seconds = time.monotonic() - start_service
            graph = report['source_map']
            records = graph['documents']
            units = graph['units']
            if (len(records) != 1 or records[0]['page_count'] != 2 or
                    [p['image_sha256'] for p in records[0]['scan_pages']] != images or
                    records[0]['runtime']['worker_sha256'] != runtime['worker_sha256'] or
                    sorted(report['questions']) != ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6'] or
                    not any(u['page'] == 1 and phrases[0] in u['raw'] for u in units) or
                    not any(u['page'] == 2 and not u['raw'].strip() for u in units)):
                raise RuntimeError('Service lost page, source, runtime or question identity')
            save(folder / 'request.json', requested)
            save(folder / 'service-report.json', report)
        if method != {path: sha(ROOT / path) for path in method}:
            raise RuntimeError('Method changed during OCR baseline')
        payload = sum(p.stat().st_size for p in folder.iterdir() if p.is_file())
        if payload + 1_048_576 > 100_000_000:
            raise RuntimeError('Baseline evidence exceeds 100-MB cap with metadata reserve')
        result = {'status': 'PASS', 'raw_worker_seconds': raw_seconds,
            'service_seconds': service_seconds, 'wall_seconds': time.monotonic() - tick,
            'page_count': 2, 'page_image_sha256': images,
            'question_statuses': {k: v['status'] for k, v in report['questions'].items()},
            'source_sha256': expected_pdf, 'model_sha256': expected_model,
            'runtime': runtime, 'method_unchanged': True,
            'evidence_payload_bytes': payload, 'gpu': 'intentionally hidden',
            'scope': 'Current two-launch OCR/service baseline; recovery and native confinement not established'}
    except Exception as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc),
            'wall_seconds': time.monotonic() - tick}
    save(folder / 'result.json', result)
    save(folder / 'manifest.json', {'files': {p.name: sha(p) for p in folder.iterdir()
        if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps({k: result.get(k) for k in ('status', 'error', 'raw_worker_seconds',
        'service_seconds', 'wall_seconds', 'evidence_payload_bytes')}), flush=True)
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
