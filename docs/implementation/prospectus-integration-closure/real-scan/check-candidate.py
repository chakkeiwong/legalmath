"""Bounded tests of copied baseline/candidate source; active worktree stays fixed."""
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
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parent
PLAN = ROOT / 'docs/plans/prospectus-real-scan-2026-10-11.md'
TEST = 'tests/prospectus_successor/test_closure_correction_images.py'
SOURCE = 'src/legalmath/prospectus/successor/corrections.py'
DATA = ['docs/implementation/prospectus-integration-closure/worker-recovery/ocr-baseline/attempt-001/raw-worker.json',
        'docs/implementation/prospectus-integration-closure/packages/scan/attempt-001/new-scan.pdf']
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {'baseline', 'candidate'}:
        raise ValueError('Specify the reviewed baseline or candidate copy')
    label = sys.argv[1]
    baseline = read(PACKAGE / 'candidate/baseline.json')
    candidate = PACKAGE / 'candidate/corrections.py'
    tests = PACKAGE / 'candidate/test_closure_correction_images.py'
    if sha(ROOT / SOURCE) != baseline['sha256'] or sha(candidate) != baseline['candidate_sha256']:
        raise ValueError('Reviewed baseline/candidate changed')
    active = ROOT / 'docs/implementation/prospectus-integration-closure/worker-recovery/validation-001/started.json'
    frozen = read(active)['method']
    if any(sha(ROOT / name) != value for name, value in frozen.items()):
        raise ValueError('Active R6 method changed')
    source_files = sorted((ROOT / 'src/legalmath').rglob('*.py'))
    bindings = [*source_files, Path(__file__), PLAN, candidate, tests,
                PACKAGE / 'candidate/baseline.json', *[ROOT / name for name in DATA]]
    method = {str(p.relative_to(ROOT)): sha(p) for p in bindings}
    previous = sorted((PACKAGE / 'candidate-check').glob(label + '-*'))
    if previous and read(previous[-1] / 'started.json')['method'] == method:
        raise ValueError('Retain the prior attempt; no unchanged repeat')
    folder = PACKAGE / f'candidate-check/{label}-{len(previous) + 1:03d}'
    folder.mkdir(parents=True)
    started = {'version': 'bes-correction-candidate-check.v1', 'label': label,
               'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'command': ['timeout', '60', '.venv/bin/python', str(Path(__file__).relative_to(ROOT)), label],
               'method': method, 'started_at': datetime.now(timezone.utc).isoformat(),
               'environment': {'python': sys.executable, 'CUDA_VISIBLE_DEVICES': '-1',
                               'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'},
               'cpu_gpu': 'CPU; GPU intentionally hidden; no native worker launched',
               'random_seeds': 'N/A deterministic engineering controls',
               'data_version': {name: sha(ROOT / name) for name in DATA},
               'timeout_seconds': 60, 'evidence_limit_bytes': 5_000_000,
               'plan_file': str(PLAN.relative_to(ROOT)), 'result_file': str((folder / 'result.json').relative_to(ROOT))}
    save(folder / 'started.json', started)
    tick = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix='prospectus-correction-' + label + '-', dir='/tmp') as location:
            isolated = Path(location)
            for source in source_files:
                target = isolated / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            for name in DATA:
                target = isolated / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, target)
            if label == 'candidate':
                shutil.copy2(candidate, isolated / SOURCE)
            (isolated / TEST).parent.mkdir(parents=True)
            shutil.copy2(tests, isolated / TEST)
            script = ("import sys; from pathlib import Path; "
                      "root=Path(sys.argv[1]); sys.path.insert(0,str(root/'src')); "
                      "from legalmath.prospectus.successor import corrections; "
                      "assert Path(corrections.__file__).resolve()==root/'src/legalmath/prospectus/successor/corrections.py'; "
                      "import pytest; raise SystemExit(pytest.main(sys.argv[2:]))")
            argv = [str(ROOT / '.venv/bin/python'), '-c', script, str(isolated), '-q', TEST,
                    '--junitxml=' + str(folder / 'tests.xml')]
            save(folder / 'test-command.json', {'argv': argv, 'cwd': str(isolated),
                 'copied_source_sha256': sha(isolated / SOURCE), 'copied_tests_sha256': sha(isolated / TEST)})
            env = {k: v for k, v in os.environ.items() if k not in {'PYTEST_ADDOPTS', 'PYTHONPATH'}}
            env.update(CUDA_VISIBLE_DEVICES='-1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
            run = subprocess.run(argv, cwd=isolated, env=env, capture_output=True, timeout=45)
            (folder / 'tests.log').write_bytes(run.stdout + run.stderr)
        tree = ET.parse(folder / 'tests.xml').getroot()
        cases = list(tree.iter('testcase'))
        failures = {c.get('name'): c.find('failure').get('message') for c in cases if c.find('failure') is not None}
        invalid = [c.get('name') for c in cases if c.find('error') is not None or c.find('skipped') is not None]
        negative = ['missing', 'wrong', 'missing-source', 'empty-source', 'malformed-source',
                    'nonstring-source', 'unfamiliar-image-method']
        expected_failures = {f'test_correction_binds_actual_ocr_page_identity[{case}-{mode}]'
                             for case in negative for mode in ('words', 'text-fallback')}
        expected_failures |= {'test_corrected_real_ocr_service_keeps_required_image_binding[missing]',
                              'test_corrected_real_ocr_service_keeps_required_image_binding[wrong]'}
        if len(cases) != 20 or len({c.get('name') for c in cases}) != 20 or invalid:
            raise ValueError('Unexpected test inventory, error or skip')
        if label == 'baseline':
            if run.returncode != 1 or set(failures) != expected_failures or any('DID NOT RAISE' not in m for m in failures.values()):
                raise ValueError('Baseline failure is not the exact reviewed adverse admission')
        elif run.returncode != 0 or failures:
            raise ValueError('Candidate failed the image/consumer controls')
        if method != {name: sha(ROOT / name) for name in method} or any(
                sha(ROOT / name) != value for name, value in frozen.items()):
            raise ValueError('Method changed during isolated check')
        payload = sum(p.stat().st_size for p in folder.iterdir() if p.is_file())
        if payload + 65536 > 5_000_000:
            raise ValueError('Evidence cap exceeded')
        result = {'status': 'PASS', 'label': label, 'tests': 20, 'pytest_returncode': run.returncode,
                  'expected_failures': sorted(failures), 'frozen_r6_method_unchanged': True,
                  'scope': 'Expected baseline rejection reproduced' if label == 'baseline' else
                           'Isolated candidate satisfies actual producer and service controls; not integrated',
                  'wall_seconds': time.monotonic() - tick, 'evidence_payload_bytes': payload}
    except Exception as exc:
        result = {'status': 'FAIL', 'label': label, 'error': type(exc).__name__ + ': ' + str(exc),
                  'wall_seconds': time.monotonic() - tick}
    save(folder / 'result.json', result)
    save(folder / 'manifest.json', {'files': {p.name: sha(p) for p in folder.iterdir()
                                         if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps(result), flush=True)
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
