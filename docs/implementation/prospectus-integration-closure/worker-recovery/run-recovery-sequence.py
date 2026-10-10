"""Finite real OCR/Cassis worker recovery through an isolated closure executor."""
from copy import deepcopy
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
BASE = ROOT / 'docs/implementation/prospectus-integration-closure'
PLAN = ROOT / 'docs/plans/prospectus-worker-recovery-2026-10-10.md'
SCAN_INPUT = BASE / 'packages/scan/attempt-001'
CODEC_INPUT = BASE / 'packages/codec/attempt-003'
MODEL = ROOT / 'docs/prospectus/closure-2026-10-05/tools/eng.traineddata'
OCR_PYTHON = Path('/home/chakwong/miniconda3/envs/tfgpu/bin/python')
CODEC_PYTHON = Path('/tmp/prospectus-adoption-tools/bin/python')
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor import closure_program as closure  # noqa: E402
from legalmath.prospectus.successor.contracts import digest, read, write  # noqa: E402
from scripts.prospectus_closure_fixtures import annotation_fixture  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verified(folder, status='PASS'):
    manifest = read(folder / 'manifest.json')
    files = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    if files != set(manifest['files']) or any(sha(folder / name) != value for name, value in manifest['files'].items()):
        raise RuntimeError('Protected attempt manifest changed: ' + str(folder))
    if read(folder / 'result.json')['status'] != status:
        raise RuntimeError('Protected attempt lacks expected result: ' + str(folder))
    return sha(folder / 'manifest.json')


def main():
    if sys.flags.optimize:
        raise RuntimeError('Assertions must be enabled')
    if Path(closure.__file__).resolve() != ROOT / 'src/legalmath/prospectus/successor/closure_program.py':
        raise RuntimeError('Wrong worktree imported')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if commit != 'dd6724963a2955536093fc1016031ea11803501a':
        raise RuntimeError('Committed coupon comparator changed')
    checks = {'ocr_baseline': verified(PACKAGE / 'ocr-baseline/attempt-001'),
        'model_path': verified(PACKAGE / 'model-path/attempt-002', 'REPAIR_PASS'),
        'scan': verified(SCAN_INPUT), 'codec': verified(CODEC_INPUT)}
    if sha(MODEL) != '7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2':
        raise RuntimeError('Protected OCR model changed')
    if sha(SCAN_INPUT / 'new-scan.pdf') != '3054b4a3af3c6c7d13c0016f6311491423ec7c296c7f6784a643c9bcf1123a68':
        raise RuntimeError('Protected OCR PDF changed')
    interpreter_sha = '6f38473e7e297ce26d0daf41f8c5d7ce5b8b92859ca905a8145a83a881f0b790'
    if sha(OCR_PYTHON) != interpreter_sha or sha(CODEC_PYTHON) != interpreter_sha:
        raise RuntimeError('Pinned worker interpreter changed')
    folder = PACKAGE / 'recovery-sequence/attempt-004'
    if folder.exists():
        raise RuntimeError('Inspect existing sequence before any changed-method retry')
    folder.mkdir(parents=True)
    paths = [*sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.py')),
        ROOT / 'scripts/prospectus_closure_fixtures.py',
        ROOT / 'scripts/prospectus_integration_codec.py',
        *(PACKAGE / name for name in ('run-recovery-sequence.py', 'recovery_probe.py', 'mutate-xmi.py')),
        PLAN, SCAN_INPUT / 'request.json', CODEC_INPUT / 'source.json',
        CODEC_INPUT / 'authored.xmi', CODEC_INPUT / 'TypeSystem.xml']
    method = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    started = {'version': 'worker-recovery-sequence.v1', 'git_commit': commit,
        'command': ['timeout', '180', '.venv/bin/python', str(Path(__file__).relative_to(ROOT))],
        'method': method, 'protected_manifests': checks,
        'started_at': datetime.now(timezone.utc).isoformat(),
        'timeout_seconds': 180, 'evidence_limit_bytes': 100_000_000,
        'metadata_reserve_bytes': 1_048_576,
        'environment': {'orchestrator': sys.executable, 'ocr_python': str(OCR_PYTHON),
            'codec_python': str(CODEC_PYTHON), 'interpreter_sha256': interpreter_sha,
            'CUDA_VISIBLE_DEVICES': '-1'},
        'data_version': {'scan_pdf_sha256': sha(SCAN_INPUT / 'new-scan.pdf'),
            'model_sha256': sha(MODEL), 'xmi_sha256': sha(CODEC_INPUT / 'authored.xmi'),
            'types_sha256': sha(CODEC_INPUT / 'TypeSystem.xml')},
        'seeds': 'N/A deterministic finite mutation sequence',
        'plan_file': str(PLAN.relative_to(ROOT)),
        'result_file': str((folder / 'result.json').relative_to(ROOT))}
    write(folder / 'started.json', started)
    tick = time.monotonic()
    rows = []
    try:
        with tempfile.TemporaryDirectory(prefix='prospectus-worker-sequence-', dir='/tmp') as location:
            isolated = Path(location)
            shutil.copytree(ROOT / 'src/legalmath', isolated / 'src/legalmath',
                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            for p in (ROOT / 'src/legalmath/prospectus/successor').glob('*.py'):
                if sha(p) != sha(isolated / p.relative_to(ROOT)):
                    raise RuntimeError('Copied source differs: ' + p.name)
            scripts = isolated / 'scripts'
            scripts.mkdir()
            shutil.copy2(ROOT / 'scripts/prospectus_integration_codec.py', scripts)
            tests = isolated / 'tests/prospectus_successor'
            tests.mkdir(parents=True)
            probe = tests / 'recovery_probe.py'
            shutil.copy2(PACKAGE / 'recovery_probe.py', probe)
            subprocess.run(['git', 'init', '-q', str(isolated)], check=True, capture_output=True)
            subprocess.run(['git', '-c', 'user.name=Worker recovery fixture',
                '-c', 'user.email=fixture@invalid', 'commit', '--allow-empty', '-qm',
                'Isolated worker recovery comparator'], cwd=isolated, check=True, capture_output=True)
            cases = isolated / closure.REL / 'inputs/R0/cases'
            scan_case, annotation_case = cases / 'scan', cases / 'annotation'
            scan_case.mkdir(parents=True)
            annotation_case.mkdir(parents=True)
            shutil.copy2(SCAN_INPUT / 'new-scan.pdf', scan_case / 'scan.pdf')
            models = scan_case / 'models'
            models.mkdir()
            model = models / 'eng.traineddata'
            shutil.copy2(MODEL, model)
            scan_request = read(SCAN_INPUT / 'request.json')
            scan_request['bundle']['documents'][0]['path'] = 'scan.pdf'
            scan_request['bundle']['documents'][0]['scan_profile']['tessdata'] = 'models'
            write(scan_case / 'request.json', scan_request)
            annotation_request = annotation_fixture(annotation_case)
            for name in ('source.json', 'authored.xmi', 'TypeSystem.xml'):
                shutil.copy2(CODEC_INPUT / name, annotation_case / name)
            source = read(annotation_case / 'source.json')
            packet = annotation_request['annotation_admission']['packets'][0]['packet']
            if packet['source'] != source['source'] or packet['text'] != source['text'] or (
                    [row['id'] for row in packet['relations']] != ['authored-exception']):
                raise RuntimeError('Current annotation fixture differs from retained authored source')
            annotation_request['observations'] = {'exempt': True}
            write(annotation_case / 'request.json', annotation_request)
            interpreter_path = scan_case / 'ocr-python'
            interpreter_path.symlink_to(OCR_PYTHON)
            os.environ['LEGALMATH_OCR_PYTHON'] = str(interpreter_path)
            previous_job = closure.JOBS['R0']
            previous_timeout = closure.PHASE_TIMEOUTS.get('R0')
            closure.JOBS['R0'] = ('tests/prospectus_successor/recovery_probe.py', None)
            closure.PHASE_TIMEOUTS['R0'] = 30
            baseline_scan = baseline_annotation = None
            previous_inputs = None

            def run_step(label, expected_scan_error=None, expected_annotation_error=None,
                         restored=False):
                nonlocal previous_inputs
                index = len(rows)
                before_inputs = closure.bindings(isolated, 'R0')['files']
                changes = sorted(key for key in set(before_inputs) | set(previous_inputs or {})
                    if before_inputs.get(key) != (previous_inputs or {}).get(key))
                if closure.status(isolated)['phases'][0]['current'] or (index and not changes):
                    raise RuntimeError('Resource change did not invalidate before recovery reason: ' + label)
                write(isolated / closure.REL / 'inputs/R0/recovery.json',
                    {'step': index, 'action': label})
                if closure.status(isolated)['phases'][0]['current']:
                    raise RuntimeError('Changed input was incorrectly reusable: ' + label)
                phase = closure.execute(isolated, 'R0')
                if phase.get('reused') or phase['engineering_checks'] != 'PASS':
                    raise RuntimeError('Isolated executor failed or reused stale result: ' + label)
                phase_dir = isolated / phase['directory']
                actual = read(phase_dir / 'assessment.json')
                clean_dir = isolated / 'clean' / label
                clean_dir.mkdir(parents=True)
                clean_path = clean_dir / 'assessment.json'
                env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1',
                    'PYTHONPATH': str(isolated / 'src') + os.pathsep + str(isolated)}
                command = [sys.executable, str(probe), str(clean_path)]
                clean_run = subprocess.run(command, cwd=isolated, env=env,
                    capture_output=True, text=True, timeout=30)
                if clean_run.returncode:
                    raise RuntimeError('Clean recomputation failed: ' + clean_run.stderr[-1200:])
                clean = read(clean_path)
                if actual != clean:
                    raise RuntimeError('Executor differs from clean recomputation: ' + label)
                if not closure.execute(isolated, 'R0')['reused']:
                    raise RuntimeError('Identical current receipt was not reusable: ' + label)
                scan, annotation = actual['scan'], actual['annotation']
                if expected_scan_error:
                    if expected_scan_error not in scan.get('error', ''):
                        raise RuntimeError('Expected scan error absent: ' + label)
                else:
                    report = scan.get('report')
                    if not report:
                        raise RuntimeError('Scan report absent: ' + label)
                    graph = report['source_map']
                    expected_images = read(PACKAGE / 'ocr-baseline/attempt-001/result.json')['page_image_sha256']
                    if (graph['documents'][0]['page_count'] != 2 or
                            [p['image_sha256'] for p in graph['documents'][0]['scan_pages']] != expected_images or
                            not any(u['page'] == 1 and 'unsecured obligations' in u['raw'] for u in graph['units']) or
                            not any(u['page'] == 2 and not u['raw'].strip() for u in graph['units'])):
                        raise RuntimeError('Scan page/image/word oracle failed: ' + label)
                if expected_annotation_error:
                    if expected_annotation_error not in annotation.get('error', ''):
                        raise RuntimeError('Expected annotation error absent: ' + label)
                else:
                    if 'report' not in annotation or 'decoded_packet' not in annotation:
                        raise RuntimeError('Annotation worker or service report absent: ' + label)
                    relations = annotation['decoded_packet']['relations']
                    if [row['id'] for row in relations] != ['authored-exception']:
                        raise RuntimeError('Authored relation lost: ' + label)
                if restored and (scan.get('report') != baseline_scan or
                                 annotation.get('report') != baseline_annotation):
                    raise RuntimeError('Restoration differs from initial full products: ' + label)
                step = folder / 'steps' / f'{index:02d}-{label}'
                step.mkdir(parents=True)
                write(step / 'executor.json', actual)
                write(step / 'clean.json', clean)
                shutil.copy2(phase_dir / 'receipt.json', step / 'receipt.json')
                shutil.copytree(phase_dir, step / 'phase')
                write(step / 'clean-command.json', {'argv': command, 'returncode': clean_run.returncode,
                    'stdout': clean_run.stdout, 'stderr': clean_run.stderr})
                row = {'step': index, 'label': label, 'phase_directory': phase['directory'],
                    'receipt_sha256': sha(phase_dir / 'receipt.json'),
                    'executor_sha256': digest(actual), 'clean_sha256': digest(clean),
                    'scan_status': 'ERROR' if 'error' in scan else scan['report']['questions']['Q1']['status'],
                    'annotation_status': 'ERROR' if 'error' in annotation else annotation['report']['questions']['Q1']['status'],
                    'model_sha256': sha(model) if model.exists() else None,
                    'xmi_sha256': sha(annotation_case / 'authored.xmi'),
                    'ocr_python': os.environ['LEGALMATH_OCR_PYTHON'],
                    'resource_changes_before_recovery_reason': changes,
                    'stale_before_recovery_reason': True,
                    'reused_after_change': False, 'reused_unchanged': True}
                previous_inputs = closure.bindings(isolated, 'R0')['files']
                rows.append(row)
                write(folder / 'progress.json', {'status': 'RUNNING', 'completed': rows})
                print(json.dumps({'completed': label, 'scan': row['scan_status'],
                    'annotation': row['annotation_status']}), flush=True)
                return actual

            try:
                initial = run_step('baseline')
                baseline_scan = initial['scan']['report']
                baseline_annotation = initial['annotation']['report']
                if baseline_annotation['questions']['Q1']['status'] != 'NO':
                    raise RuntimeError('Retained authored exception did not affect Q1')
                model.unlink()
                run_step('model-missing', expected_scan_error='model missing or changed')
                shutil.copy2(MODEL, model)
                run_step('model-restored', restored=True)
                model.write_bytes(model.read_bytes() + b'changed')
                run_step('model-changed', expected_scan_error='model missing or changed')
                shutil.copy2(MODEL, model)
                run_step('model-repaired', restored=True)
                interpreter_path.unlink()
                run_step('interpreter-missing', expected_scan_error='Configure LEGALMATH_OCR_PYTHON')
                interpreter_path.symlink_to(OCR_PYTHON)
                run_step('interpreter-restored', restored=True)
                changed_xmi = isolated / 'relation-removed.xmi'
                mutation = subprocess.run([str(CODEC_PYTHON), str(PACKAGE / 'mutate-xmi.py'),
                    str(annotation_case / 'source.json'), str(annotation_case / 'authored.xmi'),
                    str(annotation_case / 'TypeSystem.xml'), str(changed_xmi)],
                    cwd=ROOT, env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1'},
                    capture_output=True, text=True, timeout=30)
                if mutation.returncode:
                    raise RuntimeError('Isolated XMI mutation failed: ' + mutation.stderr[-1200:])
                mutation_result = json.loads(mutation.stdout)
                if mutation_result != {'status': 'RELATION_REMOVED', 'relations': []}:
                    raise RuntimeError('XMI mutation did not prove relation removal')
                write(folder / 'xmi-mutation.json', {'command': mutation.args,
                    'result': mutation_result, 'changed_xmi_sha256': sha(changed_xmi)})
                shutil.copy2(changed_xmi, annotation_case / 'authored.xmi')
                run_step('relation-removed',
                    expected_annotation_error='Authored relations differ from supplied clause links')
                shutil.copy2(CODEC_INPUT / 'authored.xmi', annotation_case / 'authored.xmi')
                run_step('relation-restored', restored=True)
                (annotation_case / 'authored.xmi').write_bytes(b'<invalid-xmi>')
                run_step('xmi-corrupt', expected_annotation_error='AnnotationCodecError')
                shutil.copy2(CODEC_INPUT / 'authored.xmi', annotation_case / 'authored.xmi')
                run_step('xmi-restored', restored=True)
            finally:
                closure.JOBS['R0'] = previous_job
                if previous_timeout is None:
                    closure.PHASE_TIMEOUTS.pop('R0', None)
                else:
                    closure.PHASE_TIMEOUTS['R0'] = previous_timeout
        if method != {path: sha(ROOT / path) for path in method}:
            raise RuntimeError('Method changed during recovery sequence')
        payload = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
        if payload + 1_048_576 > 100_000_000:
            raise RuntimeError('Recovery evidence exceeds 100-MB cap with metadata reserve')
        result = {'status': 'PASS', 'steps': rows, 'step_count': len(rows),
            'method_unchanged': True, 'evidence_payload_bytes': payload,
            'wall_seconds': time.monotonic() - tick,
            'scope': 'Actual isolated executor OCR/XMI recovery; no native confinement or legal-acceptance claim'}
    except Exception as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc),
            'steps': rows, 'wall_seconds': time.monotonic() - tick}
    write(folder / 'result.json', result)
    write(folder / 'manifest.json', {'files': {str(p.relative_to(folder)): sha(p)
        for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps({'status': result['status'], 'steps': len(rows),
        'error': result.get('error'), 'wall_seconds': result['wall_seconds']}), flush=True)
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
