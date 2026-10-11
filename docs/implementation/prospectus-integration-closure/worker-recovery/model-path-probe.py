"""Bounded, non-OCR reproduction of the OCR model symlink boundary."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parent
PLAN = ROOT / 'docs/plans/prospectus-worker-recovery-2026-10-10.md'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor import extraction  # noqa: E402
from legalmath.prospectus.successor.contracts import digest  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def observed(document, root):
    try:
        extraction.scan(document, root)
    except Exception as exc:
        return {'type': type(exc).__name__, 'message': str(exc)}
    return {'type': 'UNEXPECTED_SUCCESS', 'message': 'OCR must not start in this probe'}


def main():
    if sys.flags.optimize:
        raise RuntimeError('Assertions must be enabled')
    expected_module = ROOT / 'src/legalmath/prospectus/successor/extraction.py'
    if Path(extraction.__file__).resolve() != expected_module.resolve():
        raise RuntimeError('Wrong checkout imported')
    baseline = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if baseline != 'dd6724963a2955536093fc1016031ea11803501a':
        raise RuntimeError('Committed coupon baseline changed')
    previous = PACKAGE / 'model-path' / 'attempt-001'
    if not previous.is_dir():
        raise RuntimeError('Reproduced baseline attempt is required before repair validation')
    manifest = json.loads((previous / 'manifest.json').read_text())
    if any(sha(previous / name) != value for name, value in manifest['files'].items()):
        raise RuntimeError('Baseline diagnostic changed')
    if json.loads((previous / 'result.json').read_text())['status'] != 'REPRODUCED_LOCAL_DEFECT':
        raise RuntimeError('Baseline did not reproduce the defect')
    folder = PACKAGE / 'model-path' / 'attempt-002'
    if folder.exists():
        raise RuntimeError('Inspect retained repair attempt before any changed-method retry')
    folder.mkdir(parents=True)
    method = {str(path.relative_to(ROOT)): sha(path) for path in (expected_module,
        ROOT / 'src/legalmath/prospectus/successor/contracts.py', Path(__file__), PLAN)}
    started = {'version': 'model-path-probe.v1', 'git_commit': baseline,
        'command': ['timeout', '30', '.venv/bin/python', str(Path(__file__).relative_to(ROOT))],
        'method': method, 'started_at': datetime.now(timezone.utc).isoformat(),
        'timeout_seconds': 30, 'environment': {'python': sys.executable,
            'CUDA_VISIBLE_DEVICES': os.environ['CUDA_VISIBLE_DEVICES'],
            'extraction_module': str(Path(extraction.__file__).resolve())},
        'seeds': 'N/A deterministic synthetic path cases',
        'data_version': 'Synthetic model bytes created only in isolated temporary directories',
        'plan_file': str(PLAN.relative_to(ROOT)),
        'result_file': str((folder / 'result.json').relative_to(ROOT))}
    save(folder / 'started.json', started)
    tick = time.monotonic()
    try:
        raw = b'synthetic OCR model path fixture; not executable model data\n'
        with tempfile.TemporaryDirectory(prefix='prospectus-worker-root-', dir='/tmp') as inside_name, \
                tempfile.TemporaryDirectory(prefix='prospectus-worker-outside-', dir='/tmp') as outside_name:
            inside, outside = Path(inside_name), Path(outside_name)
            models = inside / 'models'
            models.mkdir()
            model = models / 'eng.traineddata'
            model.write_bytes(raw)
            os.environ['LEGALMATH_OCR_PYTHON'] = str(inside / 'missing-interpreter')
            document = {'scan_profile': {'version': 'pymupdf-scan.v1', 'dpi': 300,
                'language': 'eng', 'max_pages': 2, 'tessdata': 'models',
                'models': {'eng': digest(raw)}}}
            regular = observed(document, inside)
            if regular['type'] != 'ExtractionUnavailable' or 'Configure LEGALMATH_OCR_PYTHON' not in regular['message']:
                raise RuntimeError('In-root model did not reach the non-OCR interpreter check')
            document['scan_profile']['models']['eng'] = '0' * 64
            changed = observed(document, inside)
            if changed['type'] != 'ExtractionUnavailable' or 'model missing or changed' not in changed['message']:
                raise RuntimeError('Changed hash did not reject before interpreter check')
            document['scan_profile']['models']['eng'] = digest(raw)
            model.rename(models / 'saved-model')
            missing = observed(document, inside)
            if missing['type'] != 'ExtractionUnavailable' or 'model missing or changed' not in missing['message']:
                raise RuntimeError('Missing model did not reject before interpreter check')
            external = outside / 'eng.traineddata'
            external.write_bytes(raw)
            model.symlink_to(external)
            escaped = observed(document, inside)
            admitted = escaped == regular
            rejected = escaped['type'] in {'ValueError', 'ExtractionUnavailable'} and (
                'escape' in escaped['message'].lower() or 'outside declared root' in escaped['message'].lower())
            if not (admitted or rejected):
                raise RuntimeError('Symlink outcome neither reproduced admission nor root-bound rejection')
            cases = {'regular': regular, 'changed_hash': changed, 'missing': missing,
                'outside_symlink': escaped}
            paths = {'temporary_root': str(inside), 'outside_directory': str(outside),
                'model_sha256': digest(raw), 'external_model_sha256': sha(external)}
        if method != {path: sha(ROOT / path) for path in method}:
            raise RuntimeError('Method changed during diagnostic')
        elapsed = time.monotonic() - tick
        if elapsed > 30:
            raise RuntimeError('Thirty-second probe bound exceeded')
        result = {'status': 'REPAIR_FAILED' if admitted else 'REPAIR_PASS',
            'cases': cases, 'paths': paths, 'escape_admitted': admitted,
            'method_unchanged': True, 'wall_seconds': elapsed,
            'ocr_launched': False, 'real_model_read': False,
            'interpretation': 'Isolated path admission only; no worker recovery or host-confinement claim'}
    except Exception as exc:
        result = {'status': 'INVALID_PROBE', 'error': type(exc).__name__ + ': ' + str(exc),
            'wall_seconds': time.monotonic() - tick}
    save(folder / 'result.json', result)
    save(folder / 'manifest.json', {'files': {p.name: sha(p) for p in folder.iterdir()
        if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps({'status': result['status'], 'escape_admitted': result.get('escape_admitted'),
        'wall_seconds': result['wall_seconds']}), flush=True)
    if result['status'] != 'REPAIR_PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
