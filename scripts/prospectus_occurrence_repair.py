"""Once-only staged continuation of the sealed BASF015/016 failures."""
from datetime import datetime, timezone
import fcntl
import gzip
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import sys
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from scripts import prospectus_initial_agent_runner as checks
from scripts import prospectus_basf_equity as installer
from legalmath.prospectus import basf_default_f, basf_agent_introduction
from legalmath.prospectus.execution_authority import read, file_hash
from legalmath.prospectus.successor import service, process_ledger, basf_notices
from legalmath.prospectus.successor import basf_initial_agents as core
from legalmath.prospectus.successor.contracts import digest

BASE = ROOT / 'docs/implementation/prospectus-execution-authority'
GROUP = BASE / 'attempts/basf-meanings'
HERE, PRIOR, FAILED = GROUP / 'attempt-017', GROUP / 'attempt-014', GROUP / 'attempt-016'
SUPPORT = BASE / 'reviews/occurrence-lookup-105'
PLAN = 'docs/plans/prospectus-occurrence-lookup-repair-2026-10-15.md'
RUNNER = ROOT / 'scripts/prospectus_occurrence_installed.py'
HELPER = ROOT / 'scripts/prospectus_initial_agent_runner.py'
ALIASES = {'baseline-products.json.gz': PRIOR / 'products.json.gz',
    'baseline-consumer.json.gz': FAILED / 'baseline-consumer.json.gz',
    'construction-products.json.gz': FAILED / 'construction-products.json.gz',
    'prior-profiles.json': GROUP / 'attempt-013/prior-profiles.json'}
STAGES = ('prepare', 'equivalence', 'baseline-interpret', 'baseline-consumer',
    'interpret', 'candidate', 'omission', 'financial', 'controls', 'tests',
    'install-prepare', 'build', 'install', 'replay-construct', 'replay-interpret',
    'replay-answer', 'replay-omission', 'replay-financial', 'replay-controls', 'verify')
REPAIRED = ['prospectus/successor/' + n + '.py'
    for n in ('admissions', 'occurrences', 'reviewed_references', 'service')]
TESTS = ['tests/prospectus_successor/' + n + '.py' for n in (
    'test_occurrence_lookup', 'test_disposition_lookup', 'test_closure_references',
    'test_closure_reference_replacement', 'test_unavailable_references',
    'test_governing_interpretation', 'test_basf_initial_agents', 'test_basf_agent_report')]
installer.HERE = HERE


def artifact(name):
    return HERE / name if (HERE / name).exists() else ALIASES.get(name, HERE / name)


def load(name): return checks.read(artifact(name))


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()
    with path.open('xb') as out:
        out.write(gzip.compress(raw, compresslevel=1, mtime=0) if name.endswith('.gz') else raw)


def methods():
    names = [Path(__file__), RUNNER, HELPER, Path(installer.__file__), ROOT / PLAN,
             ROOT / 'pyproject.toml'] + [ROOT / n for n in TESTS]
    names += sorted((ROOT / 'src/legalmath').rglob('*.py'))
    return {str(p.relative_to(ROOT)): file_hash(p) for p in names}


def bindings():
    assert not (HERE / 'outputs.json').exists(), 'Attempt already sealed'
    admission = read(HERE / 'admission.json')
    assert all(file_hash(ROOT / p) == h for p, h in admission['binding'].items())
    if (HERE / 'methods.json').exists(): assert methods() == read(HERE / 'methods.json')
    if (HERE / 'protected-inputs.json').exists():
        assert all(file_hash(ROOT / p) == h for p, h in read(HERE / 'protected-inputs.json').items())
    return admission


def prior_seconds():
    return sum(read(p)['wall_seconds'] for n in (15, 16)
        for p in (GROUP / ('attempt-%03d' % n) / 'invocations').glob('*/result.json'))


def elapsed_seconds():
    return prior_seconds() + sum(read(p)['wall_seconds']
        for p in (HERE / 'invocations').glob('*/result.json'))


def tree_bytes(folder):
    return sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())


def workspace(): return Path(read(HERE / 'workspace.json')['directory'])


def storage_bytes():
    size = sum(tree_bytes(GROUP / ('attempt-%03d' % n)) for n in (15, 16, 17)) + tree_bytes(SUPPORT)
    if (HERE / 'workspace.json').exists(): size += tree_bytes(workspace())
    return size


def prepare():
    protected = {}
    for n in (13, 14, 15, 16):
        folder = GROUP / ('attempt-%03d' % n)
        for name, sha in read(folder / 'outputs.json').items():
            path = folder / name
            assert file_hash(path) == sha
            protected[str(path.relative_to(ROOT))] = sha
        protected[str((folder / 'outputs.json').relative_to(ROOT))] = file_hash(folder / 'outputs.json')
    for document in read(PRIOR / 'original-sources.json'):
        for row in [document] + document['images']:
            assert file_hash(ROOT / row['path']) == row['sha256']
            protected[row['path']] = row['sha256']
    for n in (15, 16):
        assert not process_ledger.checked(GROUP / ('attempt-%03d' % n) / 'command-ledger.json')['reservations']
    old_environment = Path(read(PRIOR / 'workspace.json')['directory']) / 'environment'
    assert installer.package_files(old_environment / 'lib/python3.11/site-packages/legalmath') == read(PRIOR / 'source-package.json')
    prechange = read(SUPPORT / 'package-before.json')
    current = installer.package_files(ROOT / 'src/legalmath')
    assert prechange.keys() == current.keys()
    assert sorted(p for p, sha in prechange.items() if current[p] != sha) == REPAIRED
    reserve = 6 * (PRIOR / 'products.json.gz').stat().st_size + tree_bytes(old_environment) + 20_000_000
    assert storage_bytes() + reserve < 500 * 1024 * 1024, 'Conservative storage preflight failed'
    save('protected-inputs.json', protected)
    save('input-aliases.json', {n: {'path': str(p.relative_to(ROOT)), 'sha256': file_hash(p)} for n, p in ALIASES.items()})
    save('methods.json', methods())
    for name in methods():
        target = HERE / 'methods' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    process_ledger.create(HERE / 'command-ledger.json', 8, 0,
        'Cumulative015–017: prior child starts0;build,install,six separated replays;no spare/retry')
    return {'status': 'PASS', 'prior_stage_seconds': prior_seconds(), 'reused_complete_artifacts': list(ALIASES),
        'storage_reserve_bytes': reserve, 'repair_files': REPAIRED, 'native_calls': 0, 'http_calls': 0}


def equivalence():
    import pytest
    code = pytest.main(['-q', TESTS[0], '--junitxml=' + str(HERE / 'equivalence.xml')])
    assert code == 0
    return {'status': 'PASS', 'frozen016_equivalence': True}


def baseline_interpret():
    before = load('baseline-products.json.gz')
    p3 = service.interpretation_product(before['P1'], before['P2'], before['P3']['payload']['interpretation_input'])
    assert p3 == before['P3'], 'Complete baseline interpretation changed'
    save('baseline-interpretation.json', {'status': 'PASS', 'full_P3_exact': True, 'sha256': p3['sha256']})
    return {'status': 'PASS', 'full_P3_exact': True}


def baseline_consumer():
    products = load('baseline-products.json.gz')
    earlier = GROUP / 'attempt-013'
    profiles, profile = read(earlier / 'prior-profiles.json'), read(earlier / 'profile.json')
    fresh = basf_default_f.consume(products, profiles, profile, ROOT,
        expected_prior_profiles_sha256=digest(profiles), expected_profile_sha256=digest(profile))
    assert fresh == checks.read(earlier / 'default-consumer.json.gz')
    profile = read(PRIOR / 'profile.json')
    value = basf_agent_introduction.consume(products, fresh, profile, ROOT,
        expected_prior_sha256=digest(fresh), expected_profile_sha256=digest(profile))
    assert value == checks.read(PRIOR / 'agent-introduction-consumer.json.gz') == load('baseline-consumer.json.gz')
    return {'status': 'PASS', 'fresh_complete_baseline_equal': True}


def interpret():
    before, built = load('baseline-products.json.gz'), load('construction-products.json.gz')
    products = checks.finish(built['P1'], built['P2'], before)
    transition = core.validate_transition(before, products)
    save('products.json.gz', products)
    save('transition.json', transition)
    return transition


def candidate():
    products = load('products.json.gz')
    answer = service.consume(products, ROOT, mode='frozen')
    comparison = checks.compare_answers(load('baseline-consumer.json.gz')['answer'], answer, products)
    save('ordinary-answer.json.gz', answer)
    save('comparison.json', comparison)
    return comparison


def omission():
    products, before = load('products.json.gz'), load('baseline-products.json.gz')
    omitted = checks.omission(products, before)
    assert omitted['P1'] == products['P1'] and omitted['P2'] == products['P2']
    unknown = next(n for n in before['P3']['payload']['clauses']['nodes'] if n['id'] == core.UNKNOWN_ID)
    effect = basf_notices.matched_omission(products['P2']['payload']['assembly'],
        products['P3']['payload']['clauses'], omitted['P3']['payload']['clauses'], [unknown])
    answer = service.consume(omitted, ROOT, mode='frozen')
    original = load('ordinary-answer.json.gz')
    row = next(r for r in answer['basf_agents']['readings'] if r['id'] == core.IDENTITY)
    legacy = next(r for r in load('baseline-consumer.json.gz')['answer']['basf_agents']['readings'] if r['id'] == core.IDENTITY)
    assert row == legacy and 'appointment_wording' not in row['reading']
    assert answer['basf_agents']['calculation_agent_office'] == 'UNRESOLVED'
    unchanged = set(original) - {'consumed_products', 'questions', 'basf_agents', 'meaning_coverage', 'report_sha256'}
    assert all(original[k] == answer[k] for k in unchanged)
    save('omitted-products.json.gz', omitted)
    save('omitted-answer.json.gz', answer)
    save('matched-omission.json', {'status': 'PASS', 'same_P1_P2': True, 'legacy_initial_reading_restored': True, **effect})
    return {'status': 'PASS', **effect}


def financial():
    value, profiles = checks.financial(load('products.json.gz'), load('prior-profiles.json'), load('baseline-consumer.json.gz'), ROOT)
    assert value['answer'] == load('ordinary-answer.json.gz')
    save('current-financial-consumer.json.gz', value)
    save('financial-profiles.json', profiles)
    return {'status': 'PASS', 'statement_equity_exact': True, 'oci_hedge_equal_except_explicit_profile_binding_hashes': True,
        'historical_only': ['body', 'default_f', 'agent_introduction'], 'financial_values_validated': False}


def controls():
    values = checks.controls(load('products.json.gz'), load('baseline-products.json.gz'),
        load('current-financial-consumer.json.gz'), load('financial-profiles.json'), ROOT)
    save('actual-controls.json', values)
    return {'status': 'PASS', 'refused': len(values)}


def tests():
    import pytest
    code = pytest.main(['-q', *TESTS[1:], '--junitxml=' + str(HERE / 'tests.xml')])
    assert code == 0
    return {'status': 'PASS', 'pytest_exit': int(code)}


def install_prepare():
    previous = Path(read(PRIOR / 'workspace.json')['directory'])
    old = read(PRIOR / 'source-package.json')
    assert installer.package_files(previous / 'environment/lib/python3.11/site-packages/legalmath') == old
    temp = Path(tempfile.mkdtemp(prefix='installed-basf-occurrence-', dir=ROOT / '.localresources/prospectus'))
    save('workspace.json', {'directory': str(temp), 'environment_cloned_from': str(previous)})
    shutil.copytree(previous / 'environment', temp / 'environment', symlinks=True)
    (temp / 'source').mkdir()
    shutil.copyfile(ROOT / 'pyproject.toml', temp / 'source/pyproject.toml')
    shutil.copytree(ROOT / 'src', temp / 'source/src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
    for path, name in ((RUNNER, 'runner.py'), (HELPER, 'helpers.py')): shutil.copyfile(path, temp / name)
    package = installer.package_files(temp / 'source/src/legalmath')
    prechange = read(SUPPORT / 'package-before.json')
    assert package.keys() == prechange.keys()
    assert sorted(p for p, sha in prechange.items() if package[p] != sha) == REPAIRED
    save('source-package.json', package)
    save('package-transition.json', {'status': 'PASS', 'this_repair_changed': REPAIRED,
        'inherited_changes_since014': sorted(p for p, sha in old.items() if prechange.get(p) != sha),
        'inherited_added_since014': sorted(set(prechange) - set(old)), 'baseline_before_repair': str(SUPPORT.relative_to(ROOT))})
    save('environment-metadata.json', {str(p.relative_to(temp / 'environment')): file_hash(p)
        for p in (temp / 'environment/lib/python3.11/site-packages').glob('*.dist-info/METADATA')})
    return {'status': 'PASS', 'exact_package_files': len(package), 'this_repair_files': REPAIRED}


def build(): return installer.build()
def install(): return installer.install()


def replay(mode):
    for path, name in ((RUNNER, 'runner.py'), (HELPER, 'helpers.py')):
        assert file_hash(workspace() / name) == file_hash(path)
    installer.run('replay-' + mode, [str(workspace() / 'environment/bin/python'), '-I',
        str(workspace() / 'runner.py'), str(HERE), str(ROOT), mode])
    return read(HERE / ('installed-' + mode) / 'result.json')


def verify():
    package = workspace() / 'environment/lib/python3.11/site-packages/legalmath'
    expected = read(HERE / 'source-package.json')
    assert installer.package_files(package) == expected
    metadata = {str(p.relative_to(workspace() / 'environment')): file_hash(p)
        for p in (workspace() / 'environment/lib/python3.11/site-packages').glob('*.dist-info/METADATA')
        if not p.parent.name.startswith('legalmath-')}
    assert metadata == {p: h for p, h in read(HERE / 'environment-metadata.json').items()
        if not Path(p).parent.name.startswith('legalmath-')}
    for mode in ('construct', 'interpret', 'answer', 'omission', 'financial', 'controls'):
        folder = HERE / ('installed-' + mode)
        assert read(folder / 'result.json')['status'] == 'PASS'
        assert read(folder / 'package-files.json') == expected
        proof = read(folder / 'import-proof.json')
        assert proof['isolated'] == 1
        for row in proof['modules'].values():
            path = Path(row['path']).resolve()
            assert path.is_relative_to(package) and file_hash(path) == row['sha256'] == expected[str(path.relative_to(package))]
        assert proof['runner']['sha256'] == file_hash(RUNNER)
        assert proof['helpers']['sha256'] == file_hash(HELPER)
    commands = len(process_ledger.checked(HERE / 'command-ledger.json')['reservations'])
    assert commands == 8
    result = {'status': 'PASS', 'task_complete': False, 'baseline_P3_exact': True,
        'fresh_complete_baseline_equal': True, 'exact_initial_agent_transition': True,
        'ordinary_answer_delta': True, 'matched_omission': True, 'fresh_financial_equality': True,
        'installed_full_reconstruction_and_output_equality': True, 'outer_commands': commands,
        'native_calls': 0, 'http_calls': 0, 'independent_legal_acceptance': False,
        'same_host_only': True, 'further_repairs_allowed': 0}
    save('verified-result.json', result)
    return result


def seal():
    bindings()
    results = {p.parent.name: read(p) for p in (HERE / 'invocations').glob('*/result.json')}
    seconds, size = elapsed_seconds(), storage_bytes()
    limits_passed = seconds < 1800 and size < 500 * 1024 * 1024
    passed = (set(results) == set(STAGES) and
        all(r['status'] == 'PASS' for r in results.values()) and limits_passed)
    for name in ('RESULT.md', 'NEXT-WORK.md'): assert (HERE / name).is_file()
    save('run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'plan': PLAN, 'result': str((HERE / 'RESULT.md').relative_to(ROOT)),
        'environment': sys.executable, 'cpu_gpu': 'CPU only; no framework/device imports; children CUDA_VISIBLE_DEVICES=-1',
        'data': read(HERE / 'input-aliases.json') if (HERE / 'input-aliases.json').exists() else None,
        'random_seeds': 'N/A deterministic',
        'actual_commands': [read(HERE / 'invocations' / s / 'started.json') for s in STAGES if s in results],
        'prior015016_seconds': prior_seconds(), 'cumulative015017_seconds': elapsed_seconds(),
        'cumulative_evidence_workspace_bytes': size, 'limits_passed': limits_passed, 'stages': results})
    save('result.json', {'status': 'PASS' if passed else 'FAIL', 'task': 'basf-meanings', 'task_complete': False,
        'completed_stages': [s for s in STAGES if s in results and results[s]['status'] == 'PASS'],
        'failed_stages': [s for s, r in results.items() if r['status'] != 'PASS'],
        'independent_legal_acceptance': False, 'result_note': 'RESULT.md',
        'limits_passed': limits_passed, 'further_repairs_allowed': 0})
    outputs = {str(p.relative_to(HERE)): file_hash(p) for p in HERE.rglob('*')
        if p.is_file() and p.name not in {'execution.lock', 'outputs.json'} and '__pycache__' not in p.parts}
    save('outputs.json', outputs)
    print(json.dumps({'status': 'PASS' if passed else 'FAIL', 'sealed_files': len(outputs),
        'cumulative_seconds': elapsed_seconds(), 'cumulative_bytes': storage_bytes()}))


def main():
    stage = sys.argv[1]
    assert stage in (*STAGES, 'seal')
    if stage == 'seal': return seal()
    admission = bindings()
    position = STAGES.index(stage)
    for previous in STAGES[:position]: assert read(HERE / 'invocations' / previous / 'result.json')['status'] == 'PASS'
    assert elapsed_seconds() < 1800 and storage_bytes() < 500 * 1024 * 1024
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    command = ['.venv/bin/python', '-m', 'scripts.prospectus_occurrence_repair', stage]
    save('invocations/' + stage + '/started.json', {'command': command,
        'git_commit': admission['git_commit'], 'plan': PLAN, 'environment': sys.executable,
        'started_at': datetime.now(timezone.utc).isoformat(), 'random_seeds': 'N/A deterministic',
        'cpu_gpu': 'CPU only; no framework/device imports; children CUDA_VISIBLE_DEVICES=-1'})
    tick = time.monotonic()
    def expire(signum, frame): raise TimeoutError('120-second occurrence repair stage bound; no retry')
    def no_native(*args, **kwargs): raise AssertionError('Native extraction forbidden in occurrence repair')
    service.source_product = no_native
    signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, min(120, 1800 - elapsed_seconds()))
    try:
        details = replay(stage.removeprefix('replay-')) if stage.startswith('replay-') else globals()[stage.replace('-', '_')]()
        bindings()
        wall = time.monotonic() - tick
        assert elapsed_seconds() + wall < 1800
        size = storage_bytes()
        assert size < 500 * 1024 * 1024
        result = {'status': 'PASS', 'stage': stage, 'details': details, 'wall_seconds': wall,
            'cumulative_evidence_workspace_bytes': size, 'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    except BaseException as error:
        (folder / 'traceback.txt').write_text(traceback.format_exc())
        save('invocations/' + stage + '/result.json', {'status': 'FAIL', 'error': repr(error), 'wall_seconds': time.monotonic() - tick})
        raise
    finally: signal.setitimer(signal.ITIMER_REAL, 0)
    save('invocations/' + stage + '/result.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    with (HERE / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
