"""BASF019: correct the execution boundary, then compare the current installation."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import fcntl
import gzip
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET

START = time.monotonic()
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
from scripts import prospectus_initial_agent_runner as checks
from scripts import prospectus_basf_equity as installer
from legalmath.prospectus.execution_authority import read, file_hash
from legalmath.prospectus.successor import process_ledger

BASE = ROOT / 'docs/implementation/prospectus-execution-authority'
GROUP = BASE / 'attempts/basf-meanings'
HERE = GROUP / 'attempt-019'
PRIOR = GROUP / 'attempt-018'
SUPPORT = BASE / 'reviews/initial-execution-109'
PLAN = 'docs/plans/prospectus-initial-answer-execution-repair-2026-10-16.md'
RUNNER = ROOT / 'scripts/prospectus_initial_answer_installed.py'
HELPER = ROOT / 'scripts/prospectus_initial_agent_runner.py'
MODES = ('construct', 'interpret', 'complete', 'answer', 'omission-interpret', 'omission', 'financial', 'controls')
STAGES = ('prepare', 'tests', 'install-prepare', 'build', 'install', *('replay-' + m for m in MODES), 'verify')
TESTS = ['tests/prospectus_successor/' + n + '.py' for n in (
    'test_initial_answer_comparator', 'test_occurrence_lookup', 'test_disposition_lookup',
    'test_closure_references', 'test_closure_reference_replacement', 'test_unavailable_references',
    'test_governing_interpretation', 'test_basf_initial_agents', 'test_basf_agent_report')]
FIXTURES = ['tests/conftest.py', 'tests/prospectus_successor/test_closure_consumers.py',
            'tests/prospectus_successor/test_successor.py', 'scripts/prospectus_closure_fixtures.py',
            'tests/prospectus_successor/fixtures/basf-agent-source.json']
ALIASES = {'baseline-products.json.gz': GROUP / 'attempt-014/products.json.gz',
    'baseline-consumer.json.gz': GROUP / 'attempt-016/baseline-consumer.json.gz',
    'construction-products.json.gz': GROUP / 'attempt-016/construction-products.json.gz',
    'prior-profiles.json': GROUP / 'attempt-013/prior-profiles.json',
    'products.json.gz': GROUP / 'attempt-017/products.json.gz',
    **{n: PRIOR / n for n in ('omitted-P3.json.gz', 'omitted-downstream-products.json.gz',
        'ordinary-answer.json.gz', 'omitted-answer.json.gz', 'current-financial-consumer.json.gz',
        'financial-profiles.json', 'actual-controls.json')}}
NATIVE = []
installer.HERE = HERE


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode()
    with path.open('xb') as out:
        out.write(gzip.compress(data, compresslevel=1, mtime=0) if path.suffix == '.gz' else data)


def tree_bytes(folder):
    return sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())


def prior_seconds():
    return sum(read(p)['wall_seconds'] for n in (15, 16, 17, 18)
               for p in (GROUP / ('attempt-%03d' % n) / 'invocations').glob('*/result.json'))


def elapsed():
    return prior_seconds() + sum(read(p)['wall_seconds'] for p in (HERE / 'invocations').glob('*/result.json'))


def workspace():
    return Path(read(HERE / 'workspace.json')['directory'])


def storage_bytes():
    folders = [GROUP / ('attempt-%03d' % n) for n in (15, 16, 17, 18, 19)]
    folders += [BASE / 'reviews' / n for n in ('occurrence-lookup-105', 'initial-answer-106', 'initial-execution-109')]
    if (HERE / 'workspace.json').is_file(): folders.append(workspace())
    return sum(tree_bytes(p) for p in folders)


def check_storage():
    total = storage_bytes()
    assert total < 500 * 1024 * 1024, 'Cumulative015019 logical storage bound'
    assert tree_bytes(HERE) < 80_000_000, 'New019 evidence bound'
    if (HERE / 'workspace.json').is_file():
        assert tree_bytes(workspace()) < read(HERE / 'storage-plan.json')['workspace_limit_bytes']
    return total


def methods():
    paths = [Path(__file__), RUNNER, HELPER, Path(installer.__file__), ROOT / PLAN, ROOT / 'pyproject.toml']
    paths += [ROOT / n for n in TESTS + FIXTURES]
    paths += sorted((ROOT / 'src/legalmath').rglob('*.py'))
    return {str(p.relative_to(ROOT)): file_hash(p) for p in paths}


def bindings():
    assert not (HERE / 'outputs.json').exists()
    admission = read(HERE / 'admission.json')
    assert admission['task'] == 'basf-meanings' and admission['revision'] == 109
    assert all(file_hash(ROOT / p) == h for p, h in admission['binding'].items())
    assert installer.package_files(ROOT / 'src/legalmath') == read(SUPPORT / 'package-review.json')['current']
    if (HERE / 'methods.json').is_file(): assert methods() == read(HERE / 'methods.json')
    if (HERE / 'protected-inputs.json').is_file():
        assert all(file_hash(ROOT / p) == h for p, h in read(HERE / 'protected-inputs.json').items())
    return admission


def prepare():
    protected = {}
    for n in (13, 14, 15, 16, 17, 18):
        folder = GROUP / ('attempt-%03d' % n)
        outputs = read(folder / 'outputs.json')
        for name, sha in outputs.items():
            path = folder / name
            assert file_hash(path) == sha, str(path)
            protected[str(path.relative_to(ROOT))] = sha
        protected[str((folder / 'outputs.json').relative_to(ROOT))] = file_hash(folder / 'outputs.json')
    assert read(PRIOR / 'result.json')['status'] == 'FAIL'
    assert read(PRIOR / 'invocations/tests/result.json')['status'] == 'FAIL'
    for stage in ('candidate', 'omission-interpret', 'omission', 'financial', 'controls'):
        assert read(PRIOR / 'invocations' / stage / 'result.json')['status'] == 'PASS'
    for document in read(GROUP / 'attempt-014/original-sources.json'):
        for row in [document] + document['images']:
            assert file_hash(ROOT / row['path']) == row['sha256']
            protected[row['path']] = row['sha256']
    for n in (15, 16, 17, 18):
        assert not process_ledger.checked(GROUP / ('attempt-%03d' % n) / 'command-ledger.json')['reservations']
    assert abs(prior_seconds() - 848.0792085784487) < 1e-8
    environment = Path(read(GROUP / 'attempt-014/workspace.json')['directory']) / 'environment'
    assert installer.package_files(environment / 'lib/python3.11/site-packages/legalmath') == read(GROUP / 'attempt-014/source-package.json')
    env_bytes = tree_bytes(environment)
    assert env_bytes == 209291471
    projected = storage_bytes() + 80_000_000 + env_bytes + 40_000_000
    assert projected < 500 * 1024 * 1024
    save('storage-plan.json', {'accounting': 'Logical file bytes; prior evidence preserved',
        'historical_and_support_bytes': storage_bytes(), 'attempt_limit_bytes': 80_000_000,
        'environment_baseline_bytes': env_bytes, 'workspace_limit_bytes': env_bytes + 40_000_000,
        'projected_maximum_bytes': projected, 'cumulative_limit_bytes': 500 * 1024 * 1024})
    save('protected-inputs.json', protected)
    save('input-aliases.json', {n: {'path': str(p.relative_to(ROOT)), 'sha256': file_hash(p)} for n, p in ALIASES.items()})
    save('source-package.json', installer.package_files(ROOT / 'src/legalmath'))
    save('methods.json', methods())
    for name in methods():
        path = HERE / 'methods' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, path)
    process_ledger.create(HERE / 'command-ledger.json', 10, 0,
        'Cumulative015019 outer starts: prior0; offline build/install/eight modes; tool-internal pip forks not counted')
    save('reuse-review.json', {'status': 'PASS', 'partial_source': str(PRIOR.relative_to(ROOT)),
        'prior_verdict_unchanged': 'FAIL', 'all_complete_comparators_authenticated': True,
        'current_package_delta': read(SUPPORT / 'package-review.json')['changed'],
        'new_claim_requires_actual_installed_equality': True})
    return {'prior_seconds': prior_seconds(), 'protected_files': len(protected), 'current_package_files': 430, 'projected_bytes': projected}


def tests():
    import pytest
    args = ['-q', *TESTS, '--basetemp=' + str(HERE / 'test-tmp'), '--junitxml=' + str(HERE / 'tests.xml')]
    with (HERE / 'tests.log').open('x') as log, redirect_stdout(log), redirect_stderr(log):
        code = pytest.main(args)
    cases = list(ET.parse(HERE / 'tests.xml').getroot().iter('testcase'))
    result = {'pytest_args': args, 'exit_code': int(code), 'tests': len(cases),
        'failed': [r.attrib.get('name') for r in cases if any(r.find(k) is not None for k in ('failure', 'error', 'skipped'))]}
    save('test-summary.json', result)
    assert code == 0 and not result['failed'] and len(cases) == 195
    return result


def install_prepare():
    previous = Path(read(GROUP / 'attempt-014/workspace.json')['directory'])
    assert installer.package_files(previous / 'environment/lib/python3.11/site-packages/legalmath') == read(GROUP / 'attempt-014/source-package.json')
    temp = Path(tempfile.mkdtemp(prefix='installed-basf-execution-', dir=ROOT / '.localresources/prospectus'))
    save('workspace.json', {'directory': str(temp), 'environment_cloned_from': str(previous)})
    shutil.copytree(previous / 'environment', temp / 'environment', symlinks=True)
    (temp / 'source').mkdir()
    shutil.copyfile(ROOT / 'pyproject.toml', temp / 'source/pyproject.toml')
    shutil.copytree(ROOT / 'src', temp / 'source/src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
    for path, name in ((RUNNER, 'runner.py'), (HELPER, 'helpers.py')): shutil.copyfile(path, temp / name)
    assert installer.package_files(temp / 'source/src/legalmath') == read(HERE / 'source-package.json')
    save('environment-metadata.json', {str(p.relative_to(temp / 'environment')): file_hash(p)
        for p in (temp / 'environment/lib/python3.11/site-packages').glob('*.dist-info/METADATA')})
    return {'current_package_files': 430, 'offline_clone': True, 'environment': str(temp / 'environment')}


def build(): return installer.build()
def install(): return installer.install()


def replay(mode):
    for path, name in ((RUNNER, 'runner.py'), (HELPER, 'helpers.py')):
        assert file_hash(workspace() / name) == file_hash(path)
    installer.run('replay-' + mode, [str(workspace() / 'environment/bin/python'), '-I',
        str(workspace() / 'runner.py'), str(HERE), str(ROOT), mode])
    return read(HERE / ('installed-' + mode) / 'result.json')


def verify():
    expected = read(HERE / 'source-package.json')
    package = workspace() / 'environment/lib/python3.11/site-packages/legalmath'
    assert installer.package_files(package) == expected == installer.package_files(ROOT / 'src/legalmath')
    metadata = {str(p.relative_to(workspace() / 'environment')): file_hash(p)
        for p in (workspace() / 'environment/lib/python3.11/site-packages').glob('*.dist-info/METADATA')
        if not p.parent.name.startswith('legalmath-')}
    assert metadata == {p: h for p, h in read(HERE / 'environment-metadata.json').items() if not Path(p).parent.name.startswith('legalmath-')}
    for mode in MODES:
        folder = HERE / ('installed-' + mode)
        assert read(folder / 'result.json')['status'] == 'PASS'
        assert read(folder / 'package-files.json') == expected
        proof = read(folder / 'import-proof.json')
        assert proof['isolated'] == 1
        for row in proof['modules'].values():
            path = Path(row['path']).resolve()
            assert path.is_relative_to(package) and file_hash(path) == row['sha256'] == expected[str(path.relative_to(package))]
        assert proof['runner']['sha256'] == file_hash(RUNNER) and proof['helpers']['sha256'] == file_hash(HELPER)
    ledger = process_ledger.checked(HERE / 'command-ledger.json')
    assert len(ledger['reservations']) == 10 and all(r['state'] == 'STARTED' for r in ledger['reservations'])
    tests = read(HERE / 'test-summary.json')
    assert tests['tests'] == 195 and not tests['failed']
    native = read(HERE / 'invocations/tests/native-starts.json')
    assert 0 < len(native) <= 64
    result = {'status': 'PASS', 'task_complete': False, 'all195_intended_regressions_executed': True,
        'current_package_full_installed_reconstruction': True, 'complete_answers_omission_financial_controls_equal': True,
        'retained018_failure_unchanged': True, 'test_only_native_starts': len(native), 'outer_starts': 10,
        'installed_native_calls': 0, 'same_host_only': True, 'independent_legal_acceptance': False}
    save('verified-result.json', result)
    return result


def boundaries(stage):
    def refuse(*a, **k): raise RuntimeError('Unreviewed native/process/network operation forbidden in BASF019')
    original = subprocess.Popen
    test = stage == 'tests'
    installed = stage in ('build', 'install') or stage.startswith('replay-')
    executable = Path(shutil.which('pdftotext')).resolve() if test else None
    executable_hash = file_hash(executable) if test else None
    def guarded(argv, *a, **k):
        if installed:
            assert isinstance(argv, list) and argv[0] == str(workspace() / 'environment/bin/python')
            assert not k.get('shell') and Path(k.get('cwd', '')).resolve() == workspace().resolve()
            return original(argv, *a, **k)
        if not test or not isinstance(argv, list) or len(argv) != 6: return refuse()
        assert argv[1:4] == ['-bbox-layout', '-enc', 'UTF-8'] and argv[5] == '-'
        resolved, path = Path(shutil.which(argv[0])).resolve(), Path(argv[4]).resolve()
        assert resolved == executable and file_hash(resolved) == executable_hash
        assert path.is_relative_to((HERE / 'test-tmp').resolve()) and path.suffix == '.pdf'
        assert path.stat().st_size < 100_000 and not k.get('shell') and not a
        assert len(NATIVE) < 64
        NATIVE.append({'argv': argv, 'input_sha256': file_hash(path), 'executable_sha256': executable_hash})
        return original(argv, **k)
    subprocess.Popen = guarded
    os.system = refuse
    if hasattr(os, 'posix_spawn'): os.posix_spawn = refuse
    if hasattr(os, 'posix_spawnp'): os.posix_spawnp = refuse
    socket.create_connection = refuse
    socket.socket.connect = refuse
    socket.socket.connect_ex = refuse


def seal():
    assert not (HERE / 'outputs.json').exists()
    binding_error = None
    try: bindings()
    except Exception as error: binding_error = repr(error)
    results = {p.parent.name: read(p) for p in (HERE / 'invocations').glob('*/result.json')}
    seconds = elapsed() + time.monotonic() - START
    limits = seconds < 1800 and check_storage() < 500 * 1024 * 1024
    passed = not binding_error and set(results) == set(STAGES) and all(r['status'] == 'PASS' for r in results.values()) and limits
    assert (HERE / 'RESULT.md').is_file() and (HERE / 'NEXT-WORK.md').is_file()
    save('run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'], 'plan': PLAN,
        'result': 'RESULT.md', 'environment': sys.executable, 'random_seeds': 'N/A deterministic',
        'cpu_gpu': 'CPU only; CUDA_VISIBLE_DEVICES=-1 before imports and in children',
        'data': 'input-aliases.json and protected-inputs.json', 'methods': 'methods.json and source-package.json',
        'prior015018_seconds': prior_seconds(), 'cumulative015019_seconds': seconds,
        'cumulative_evidence_workspace_bytes': storage_bytes(), 'binding_error': binding_error,
        'limits_passed': limits, 'stages': results})
    save('result.json', {'task': 'basf-meanings', 'status': 'PASS' if passed else 'FAIL', 'task_complete': False,
        'completed_stages': [s for s in STAGES if s in results and results[s]['status'] == 'PASS'],
        'failed_stages': [s for s, r in results.items() if r['status'] != 'PASS'],
        'binding_error': binding_error, 'limits_passed': limits, 'result_note': 'RESULT.md',
        'independent_legal_acceptance': False, 'further_repairs_allowed': 0})
    outputs = {str(p.relative_to(HERE)): file_hash(p) for p in HERE.rglob('*') if p.is_file()
        and p.name not in ('outputs.json', 'execution.lock') and '__pycache__' not in p.parts}
    save('outputs.json', outputs)
    print(json.dumps({'status': 'PASS' if passed else 'FAIL', 'files': len(outputs),
        'cumulative_seconds': seconds, 'cumulative_bytes': storage_bytes()}), flush=True)


def main():
    stage = sys.argv[1]
    assert stage in (*STAGES, 'seal')
    if stage == 'seal': return seal()
    assert not (HERE / 'outputs.json').exists()
    starts = list((HERE / 'invocations').glob('*/started.json'))
    ends = list((HERE / 'invocations').glob('*/result.json'))
    assert len(starts) == len(ends), 'An earlier stage is incomplete; do not duplicate'
    for previous in STAGES[:STAGES.index(stage)]:
        assert read(HERE / 'invocations' / previous / 'result.json')['status'] == 'PASS'
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    command = ['timeout', '120', '.venv/bin/python', '-m', 'scripts.prospectus_initial_answer_resume', stage]
    save('invocations/' + stage + '/started.json', {'command': command, 'plan': PLAN,
        'environment': sys.executable, 'cpu_gpu': 'CPU only; GPU intentionally hidden',
        'random_seeds': 'N/A deterministic', 'started_at': datetime.now(timezone.utc).isoformat()})
    def expire(signum, frame): raise TimeoutError('Reviewed BASF019 stage/cumulative deadline; no retry')
    signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, max(1, min(118 - (time.monotonic() - START), 1800 - elapsed())))
    outcome = {'status': 'PASS'}
    try:
        admission = bindings()
        check_storage()
        boundaries(stage)
        outcome['details'] = replay(stage.removeprefix('replay-')) if stage.startswith('replay-') else globals()[stage.replace('-', '_')]()
        bindings()
        assert elapsed() + time.monotonic() - START < 1800
        outcome['cumulative_evidence_workspace_bytes'] = check_storage()
    except BaseException as error:
        outcome.update(status='FAIL', error=repr(error))
        (folder / 'traceback.txt').write_text(traceback.format_exc())
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    save('invocations/' + stage + '/native-starts.json', NATIVE)
    outcome.update(wall_seconds=time.monotonic() - START, stage=stage, command=command,
        git_commit=read(HERE / 'admission.json')['git_commit'], max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    save('invocations/' + stage + '/result.json', outcome)
    print(json.dumps({'stage': stage, 'status': outcome['status'], 'wall_seconds': outcome['wall_seconds'],
        'error': outcome.get('error')}), flush=True)
    if outcome['status'] != 'PASS': raise SystemExit(1)


if __name__ == '__main__':
    with (HERE / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
