"""Serial worker-recovery regression and phase refresh with exact test coverage."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/implementation/prospectus-integration-closure'
PACKAGE = BASE / 'worker-recovery'
PLAN = ROOT / 'docs/plans/prospectus-worker-recovery-2026-10-10.md'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor import closure_program as closure  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def method():
    paths = [*sorted((ROOT / 'src/legalmath').rglob('*.py')),
        *sorted((ROOT / 'tests/prospectus_successor').glob('*.py')),
        *sorted((ROOT / 'scripts').glob('prospectus_closure_*.py')),
        ROOT / 'tests/prospectus/test_closure_mechanisms.py', ROOT / 'scripts/prospectus_delivery.py',
        ROOT / 'scripts/prospectus_integration_codec.py', ROOT / 'pyproject.toml', PLAN,
        *sorted(PACKAGE.glob('*.py')), *sorted(BASE.glob('basf-*/review.json'))]
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def counts(path):
    return {key: sum(int(s.get(key, 0)) for s in ET.parse(path).getroot().iter('testsuite'))
            for key in ('tests', 'failures', 'errors', 'skipped')}


def main():
    if sys.flags.optimize:
        raise RuntimeError('Validation requires assertions enabled')
    if len(sys.argv) == 3 and sys.argv[1] == '--collect':
        import pytest
        class Inventory:
            def pytest_collection_finish(self, session):
                rows = []
                for item in session.items:
                    parts = item.nodeid.split('::')
                    classname = parts[0][:-3].replace('/', '.')
                    if len(parts) > 2:
                        classname += '.' + '.'.join(parts[1:-1])
                    rows.append({'nodeid': item.nodeid, 'classname': classname, 'name': parts[-1]})
                save(Path(sys.argv[2]), rows)
        raise SystemExit(pytest.main(['-q', '--collect-only', 'tests/prospectus_successor',
            'tests/prospectus/test_closure_mechanisms.py'], plugins=[Inventory()]))
    if len(sys.argv) != 1 or Path(closure.__file__).resolve() != ROOT / 'src/legalmath/prospectus/successor/closure_program.py':
        raise RuntimeError('Exact validation invocation/worktree required')
    for name in ('recovery-sequence/attempt-004', 'native-boundary/attempt-001', 'ocr-baseline/attempt-001'):
        folder = PACKAGE / name
        manifest = read(folder / 'manifest.json')
        actual = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}
        if actual != set(manifest['files']) or any(sha(folder / p) != h for p, h in manifest['files'].items()):
            raise RuntimeError('Prerequisite evidence changed: ' + name)
        if read(folder / 'result.json')['status'] != 'PASS':
            raise RuntimeError('Prerequisite failed: ' + name)
    for step in (PACKAGE / 'recovery-sequence/attempt-004/steps').iterdir():
        if closure.verified_attempt(ROOT, step / 'phase') is None:
            raise RuntimeError('Retained actual executor receipt invalid: ' + step.name)
    folder = PACKAGE / 'validation-001'
    if folder.exists():
        raise RuntimeError('Inspect existing validation before any changed-method retry')
    folder.mkdir()
    baseline = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    expected = method()
    python = str(ROOT / '.venv/bin/python')
    started = {'version': 'worker-recovery-validation.v1', 'git_commit': baseline,
        'command': ['timeout', '6300', '.venv/bin/python', str(Path(__file__).relative_to(ROOT))],
        'method': expected, 'started_at': datetime.now(timezone.utc).isoformat(),
        'environment': {'python': sys.executable, 'version': sys.version, 'CUDA_VISIBLE_DEVICES': '-1'},
        'cpu_gpu': 'CPU; GPU intentionally hidden; no GPU probe',
        'seeds': 'Deterministic examples; existing Hypothesis settings retained',
        'data_version': 'Protected coupon baseline and retained worker recovery/mount diagnostics',
        'plan_file': str(PLAN.relative_to(ROOT)), 'result_file': str((folder / 'result.json').relative_to(ROOT)),
        'timeout_seconds': 6300, 'evidence_limit_bytes': 100_000_000, 'metadata_reserve_bytes': 1_048_576}
    save(folder / 'started.json', started)
    progress = {'status': 'RUNNING', 'active': None, 'completed': []}

    def run(label, argv, limit, xml=None):
        if method() != expected:
            raise RuntimeError('Method drift before ' + label)
        progress['active'] = label
        save(folder / 'progress.json', progress)
        save(folder / (label + '-started.json'), {'argv': argv, 'timeout_seconds': limit,
            'started_at': datetime.now(timezone.utc).isoformat(), 'method_sha256': sha(folder / 'started.json')})
        print(json.dumps({'starting': label, 'limit': limit}), flush=True)
        tick = time.monotonic()
        try:
            completed = subprocess.run(argv, cwd=ROOT, env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1'},
                                       capture_output=True, timeout=limit)
            (folder / (label + '.log')).write_bytes(completed.stdout + completed.stderr)
            result = {'status': 'PASS' if completed.returncode == 0 else 'FAIL', 'returncode': completed.returncode}
            if xml:
                result['counts'] = counts(xml)
                if not result['counts']['tests'] or any(result['counts'][key] for key in ('failures', 'errors', 'skipped')):
                    result['status'] = 'FAIL'
            if method() != expected:
                result.update(status='FAIL', error='Method changed during run')
        except subprocess.TimeoutExpired as exc:
            (folder / (label + '.log')).write_bytes((exc.stdout or b'') + (exc.stderr or b''))
            result = {'status': 'TIMEOUT', 'error': 'Reviewed bound exceeded; inspect before retry'}
        result['wall_seconds'] = time.monotonic() - tick
        save(folder / (label + '-result.json'), result)
        print(json.dumps({'completed': label, **result}), flush=True)
        if result['status'] != 'PASS':
            raise RuntimeError('Validation failed at ' + label)
        progress['completed'].append({'label': label, **result})
        progress['active'] = None
        save(folder / 'progress.json', progress)

    tick = time.monotonic()
    try:
        inventory = folder / 'inventory.json'
        run('collection', [python, str(Path(__file__)), '--collect', str(inventory)], 60)
        rows = read(inventory)
        universe = {row['nodeid'] for row in rows}
        keys = {(row['classname'], row['name']): row['nodeid'] for row in rows}
        if not rows or len(keys) != len(universe) or len(rows) != len(universe):
            raise RuntimeError('Ambiguous collected test identities')
        covered, evidence = set(), []

        def include(label, xml):
            summary = counts(xml)
            if not summary['tests'] or any(summary[k] for k in ('failures', 'errors', 'skipped')):
                raise RuntimeError('Cannot count failed/skipped tests: ' + label)
            cases = list(ET.parse(xml).getroot().iter('testcase'))
            ids = [keys[(case.get('classname'), case.get('name'))] for case in cases]
            if len(ids) != len(set(ids)) or len(ids) != summary['tests']:
                raise RuntimeError('Duplicate/unaccounted executed cases: ' + label)
            covered.update(ids)
            evidence.append({'label': label, 'xml': str(xml.relative_to(ROOT)), 'sha256': sha(xml),
                             'counts': summary, 'nodes': ids})

        xml = folder / 'focused.xml'
        run('focused', [python, '-m', 'scripts.prospectus_delivery', '--program', 'closure', 'check',
            'tests/prospectus_successor/test_closure_runtime.py', 'tests/prospectus_successor/test_closure_program.py',
            '--junitxml=' + str(xml)], 120, xml)
        include('focused', xml)
        for phase in list(closure.DAG)[:-1]:
            run(phase, [python, '-m', 'scripts.prospectus_delivery', '--program', 'closure', 'phase', '--phase', phase],
                closure.PHASE_TIMEOUTS.get(phase, 600) + 120)
            row = next(r for r in closure.status(ROOT)['phases'] if r['phase'] == phase)
            if not (row['current'] and row['artifact_valid'] and row['engineering_checks'] == 'PASS'):
                raise RuntimeError('Phase failed current evidence check: ' + phase)
            include(phase, ROOT / row['directory'] / 'tests.xml')
        remainder = sorted(universe - covered)
        save(folder / 'remaining-nodeids.json', remainder)
        if remainder:
            xml = folder / 'remaining.xml'
            run('remaining', [python, '-m', 'scripts.prospectus_delivery', '--program', 'closure', 'check',
                *remainder, '--junitxml=' + str(xml)], 600, xml)
            include('remaining', xml)
        if covered != universe or method() != expected:
            raise RuntimeError('Incomplete coverage or changed method')
        save(folder / 'coverage.json', {'version': 'worker-recovery-regression-coverage.v1', 'status': 'PASS',
            'inventory': str(inventory.relative_to(ROOT)), 'inventory_sha256': sha(inventory),
            'unique_tests': len(universe), 'covered': len(covered), 'missing': [], 'unexpected': [],
            'method': expected, 'method_unchanged': True, 'evidence': evidence, 'git_commit': baseline,
            'scope': 'Exact union of current focused/phase/remainder tests, not a single-process aggregate'})
        run('attribution-update', [python, str(PACKAGE / 'update-ledger.py')], 60)
        run('R8', [python, '-m', 'scripts.prospectus_delivery', '--program', 'closure', 'phase', '--phase', 'R8'], 720)
        final = closure.refresh(ROOT)
        if not all(row['current'] and row['artifact_valid'] and row['engineering_checks'] == 'PASS' for row in final['phases']):
            raise RuntimeError('Final phase state is not all current PASS')
        if read(BASE / 'final-attribution.json') != read(ROOT / final['phases'][-1]['directory'] / 'attribution.json'):
            raise RuntimeError('Final attribution differs from phase output')
        save(folder / 'final-status.json', final)
        payload = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
        if payload + 1_048_576 > 100_000_000:
            raise RuntimeError('Validation evidence cap exceeded')
        result = {'status': 'PASS', 'unique_tests': len(universe), 'method_unchanged': method() == expected,
            'phases': final['phases'], 'wall_seconds': time.monotonic() - tick, 'evidence_payload_bytes': payload,
            'program_complete': False, 'external_acceptance': 'NOT_ESTABLISHED'}
        progress.update(status='ENGINEERING_VALIDATION_COMPLETE', active=None)
    except Exception as exc:
        progress.update(status='REVIEW_REQUIRED', error=type(exc).__name__ + ': ' + str(exc))
        result = {'status': 'FAIL', 'error': progress['error'], 'wall_seconds': time.monotonic() - tick}
    save(folder / 'progress.json', progress)
    save(folder / 'result.json', result)
    save(folder / 'manifest.json', {'files': {str(p.relative_to(folder)): sha(p)
        for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps({'validation_directory': str(folder.relative_to(ROOT)), 'status': result['status'],
        'error': result.get('error'), 'wall_seconds': result['wall_seconds']}), flush=True)
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
