"""Once-only018: fix the demonstrated checker, preserving the whole017 package."""
from datetime import datetime, timezone
import fcntl
import gzip
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from scripts import prospectus_initial_agent_runner as checks
from scripts import prospectus_basf_equity as installer
from legalmath.prospectus.execution_authority import read, file_hash
from legalmath.prospectus.successor import service, process_ledger, basf_notices
from legalmath.prospectus.successor import basf_initial_agents as core

BASE = ROOT / 'docs/implementation/prospectus-execution-authority'
GROUP = BASE / 'attempts/basf-meanings'
HERE, PRIOR, FROZEN = [GROUP / ('attempt-%03d' % n) for n in (18, 14, 17)]
SUPPORT = BASE / 'reviews/initial-answer-106'
OLD_SUPPORT = BASE / 'reviews/occurrence-lookup-105'
PLAN = 'docs/plans/prospectus-initial-answer-comparator-repair-2026-10-16.md'
RUNNER = ROOT / 'scripts/prospectus_initial_answer_installed.py'
HELPER = ROOT / 'scripts/prospectus_initial_agent_runner.py'
ALIASES = {'baseline-products.json.gz': PRIOR / 'products.json.gz',
    'baseline-consumer.json.gz': GROUP / 'attempt-016/baseline-consumer.json.gz',
    'construction-products.json.gz': GROUP / 'attempt-016/construction-products.json.gz',
    'prior-profiles.json': GROUP / 'attempt-013/prior-profiles.json',
    'products.json.gz': FROZEN / 'products.json.gz'}
MODES = ('construct', 'interpret', 'complete', 'answer', 'omission-interpret',
         'omission', 'financial', 'controls')
STAGES = ('prepare', 'comparator-tests', 'candidate', 'omission-interpret', 'omission',
    'financial', 'controls', 'tests', 'install-prepare', 'build', 'install',
    *('replay-' + m for m in MODES), 'verify')
TESTS = ['tests/prospectus_successor/' + n + '.py' for n in (
    'test_initial_answer_comparator', 'test_occurrence_lookup', 'test_disposition_lookup',
    'test_closure_references', 'test_closure_reference_replacement', 'test_unavailable_references',
    'test_governing_interpretation', 'test_basf_initial_agents', 'test_basf_agent_report')]
FIXTURE = 'tests/prospectus_successor/fixtures/basf-agent-source.json'
# Logical bytes, not allocated blocks. Existing evidence is never deduplicated
# away. These caps cover the whole new attempt and its private offline clone.
EVIDENCE_LIMIT = 80_000_000
WORKSPACE_GROWTH_LIMIT = 40_000_000
installer.HERE = HERE


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()
    with path.open('xb') as out:
        out.write(gzip.compress(raw, compresslevel=1, mtime=0) if name.endswith('.gz') else raw)


def load(name):
    path = HERE / name
    if not path.exists():
        path = ALIASES[name]
        if (HERE / 'input-aliases.json').exists():
            row = read(HERE / 'input-aliases.json')[name]
            assert str(path.relative_to(ROOT)) == row['path'] and file_hash(path) == row['sha256']
    return checks.read(path)


def methods():
    names = [Path(__file__), RUNNER, HELPER, Path(installer.__file__), ROOT / PLAN,
             ROOT / 'pyproject.toml', ROOT / FIXTURE] + [ROOT / n for n in TESTS]
    names += sorted((ROOT / 'src/legalmath').rglob('*.py'))
    return {str(p.relative_to(ROOT)): file_hash(p) for p in names}


def frozen_package():
    #017 failed before installing. Its frozen Python methods plus the protected
    #pre-repair non-Python files define the entire430-file package exactly.
    package = read(OLD_SUPPORT / 'package-before.json')
    for name, sha in read(FROZEN / 'methods.json').items():
        if name.startswith('src/legalmath/'):
            package[name.removeprefix('src/legalmath/')] = sha
    return package


def bindings():
    assert not (HERE / 'outputs.json').exists(), 'Attempt already sealed'
    admission = read(HERE / 'admission.json')
    assert admission['revision'] == 106 and admission['task'] == 'basf-meanings'
    assert all(file_hash(ROOT / p) == h for p, h in admission['binding'].items())
    if (HERE / 'methods.json').exists(): assert methods() == read(HERE / 'methods.json')
    if (HERE / 'protected-inputs.json').exists():
        assert all(file_hash(ROOT / p) == h for p, h in read(HERE / 'protected-inputs.json').items())
    assert installer.package_files(ROOT / 'src/legalmath') == frozen_package(), 'Production package differs from017'
    return admission


def prior_seconds():
    return sum(read(p)['wall_seconds'] for n in (15, 16, 17)
        for p in (GROUP / ('attempt-%03d' % n) / 'invocations').glob('*/result.json'))


def elapsed_seconds():
    return prior_seconds() + sum(read(p)['wall_seconds'] for p in (HERE / 'invocations').glob('*/result.json'))


def tree_bytes(folder):
    return sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())


def workspace(): return Path(read(HERE / 'workspace.json')['directory'])


def storage_bytes():
    size = sum(tree_bytes(GROUP / ('attempt-%03d' % n)) for n in (15, 16, 17, 18))
    size += tree_bytes(OLD_SUPPORT) + tree_bytes(SUPPORT)
    if (HERE / 'workspace.json').exists(): size += tree_bytes(workspace())
    return size


def check_storage():
    size = storage_bytes()
    assert size < 500 * 1024 * 1024, 'Cumulative logical storage ceiling'
    assert tree_bytes(HERE) <= EVIDENCE_LIMIT, 'New evidence storage cap'
    if (HERE / 'storage-plan.json').exists():
        plan = read(HERE / 'storage-plan.json')
        groups = {
            'installed_construct_P1_P2': ['installed-construct/products.json.gz'],
            'three_actual_P3_files': ['omitted-P3.json.gz', 'installed-interpret/semantic.json.gz',
                                      'installed-omission-interpret/semantic.json.gz'],
            'four_complete_actual_answers': ['ordinary-answer.json.gz', 'omitted-answer.json.gz',
                'installed-answer/ordinary-answer.json.gz', 'installed-omission/omitted-answer.json.gz'],
            'two_complete_financial_consumers': ['current-financial-consumer.json.gz',
                'installed-financial/current-financial-consumer.json.gz'],
            'three_P4_P5_tails': ['omitted-downstream-products.json.gz',
                'installed-complete/downstream-products.json.gz', 'installed-omission/downstream-products.json.gz'],
        }
        used = {k: sum((HERE / n).stat().st_size for n in names if (HERE / n).is_file())
                for k, names in groups.items()}
        used['admission_methods_profiles_wheel_logs_and_manifests'] = tree_bytes(HERE) - sum(used.values())
        assert all(used[k] <= cap for k, cap in plan['evidence_component_caps'].items()), 'Evidence component storage cap'
    if (HERE / 'workspace.json').exists():
        cap = read(HERE / 'storage-plan.json')['workspace_limit_bytes']
        assert tree_bytes(workspace()) <= cap, 'Private workspace storage cap'
    return size


def prepare():
    protected = {}
    for n in (13, 14, 15, 16, 17):
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
    for n in (15, 16, 17):
        assert not process_ledger.checked(GROUP / ('attempt-%03d' % n) / 'command-ledger.json')['reservations']
    assert read(FROZEN / 'result.json')['status'] == 'FAIL'
    for stage in ('prepare', 'equivalence', 'baseline-interpret', 'baseline-consumer', 'interpret'):
        assert read(FROZEN / 'invocations' / stage / 'result.json')['status'] == 'PASS'
    assert read(FROZEN / 'invocations/candidate/result.json')['status'] == 'FAIL'
    old_environment = Path(read(PRIOR / 'workspace.json')['directory']) / 'environment'
    assert installer.package_files(old_environment / 'lib/python3.11/site-packages/legalmath') == read(PRIOR / 'source-package.json')
    environment_bytes = tree_bytes(old_environment)
    # P1/P2 and candidate P1–P5 already exist in sealed016/017. Retain only
    # actual new components; equality still covers the complete recombination.
    evidence_caps = {
        'installed_construct_P1_P2': 30_000_000,
        'three_actual_P3_files': 21_000_000,
        'four_complete_actual_answers': 12_000_000,
        'two_complete_financial_consumers': 8_000_000,
        'three_P4_P5_tails': 300_000,
        'admission_methods_profiles_wheel_logs_and_manifests': 8_700_000,
    }
    assert sum(evidence_caps.values()) == EVIDENCE_LIMIT
    fixed = storage_bytes() - tree_bytes(HERE)
    projected = fixed + EVIDENCE_LIMIT + environment_bytes + WORKSPACE_GROWTH_LIMIT
    assert projected < 500 * 1024 * 1024, 'Conservative storage preflight failed'
    save('storage-plan.json', {'accounting': 'Logical st_size for every file path; no hardlink discount',
        'retained_prior_and_support_bytes': fixed, 'evidence_component_caps': evidence_caps,
        'new_attempt_limit_bytes': EVIDENCE_LIMIT, 'private_clone_baseline_bytes': environment_bytes,
        'workspace_limit_bytes': environment_bytes + WORKSPACE_GROWTH_LIMIT,
        'projected_maximum_bytes': projected, 'cumulative_limit_bytes': 500 * 1024 * 1024,
        'no_prior_evidence_deleted': True, 'complete_value_equality_after_recombination': True})
    save('protected-inputs.json', protected)
    save('input-aliases.json', {n: {'path': str(p.relative_to(ROOT)), 'sha256': file_hash(p)} for n, p in ALIASES.items()})
    save('methods.json', methods())
    save('source-package.json', frozen_package())
    for name in methods():
        target = HERE / 'methods' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    process_ledger.create(HERE / 'command-ledger.json', 10, 0,
        'Cumulative015–018: prior0;build/install/eight separated modes;no spare/retry/native child')
    save('reused-partials.json', {'status': 'PASS', 'sealed017_verdict': 'FAIL',
        'authenticated_passed_stages': ['equivalence', 'baseline-interpret', 'baseline-consumer', 'interpret'],
        'entire_production_package_unchanged': len(frozen_package()),
        'source': str(FROZEN.relative_to(ROOT)), 'no_new_completion_from_reuse': True})
    return {'status': 'PASS', 'prior_stage_seconds': prior_seconds(),
        'source_package_files': len(frozen_package()), 'projected_maximum_storage_bytes': projected,
        'native_calls': 0, 'http_calls': 0}


def comparator_tests():
    import pytest
    code = pytest.main(['-q', TESTS[0], '--junitxml=' + str(HERE / 'comparator-tests.xml')])
    assert code == 0
    return {'status': 'PASS', 'frozen017_rejection_and_strict_regressions': True}


def candidate():
    products = load('products.json.gz')
    answer = service.consume(products, ROOT, mode='frozen')
    save('ordinary-answer.json.gz', answer)
    comparison = checks.compare_answers(load('baseline-consumer.json.gz')['answer'], answer, products)
    save('comparison.json', comparison)
    return comparison


def omission_interpret():
    products, before = load('products.json.gz'), load('baseline-products.json.gz')
    semantic = service.interpretation_product(products['P1'], products['P2'], checks.omission_input(before))
    save('omitted-P3.json.gz', semantic)
    assert semantic['payload']['clauses']['nodes'] == before['P3']['payload']['clauses']['nodes']
    return {'status': 'PASS', 'same_changed_P1_P2': True, 'legacy_clause_nodes_exact': True}


def omission():
    products, before = load('products.json.gz'), load('baseline-products.json.gz')
    omitted = checks.complete(products['P1'], products['P2'], products, load('omitted-P3.json.gz'))
    save('omitted-downstream-products.json.gz', {p: omitted[p] for p in ('P4', 'P5')})
    answer = service.consume(omitted, ROOT, mode='frozen')
    save('omitted-answer.json.gz', answer)
    assert omitted['P1'] == products['P1'] and omitted['P2'] == products['P2']
    unknown = next(n for n in before['P3']['payload']['clauses']['nodes'] if n['id'] == core.UNKNOWN_ID)
    effect = basf_notices.matched_omission(products['P2']['payload']['assembly'],
        products['P3']['payload']['clauses'], omitted['P3']['payload']['clauses'], [unknown])
    row = next(r for r in answer['basf_agents']['readings'] if r['id'] == core.IDENTITY)
    legacy = next(r for r in load('baseline-consumer.json.gz')['answer']['basf_agents']['readings'] if r['id'] == core.IDENTITY)
    assert row == legacy and 'appointment_wording' not in row['reading']
    assert answer['basf_agents']['calculation_agent_office'] == 'UNRESOLVED'
    original = load('ordinary-answer.json.gz')
    unchanged = set(original) - {'consumed_products', 'questions', 'basf_agents', 'meaning_coverage', 'report_sha256'}
    assert all(original[k] == answer[k] for k in unchanged)
    save('matched-omission.json', {'status': 'PASS', 'same_P1_P2': True,
        'legacy_initial_reading_restored': True, **effect})
    return {'status': 'PASS', **effect}


def financial():
    value, profiles = checks.financial(load('products.json.gz'), load('prior-profiles.json'), load('baseline-consumer.json.gz'), ROOT)
    save('current-financial-consumer.json.gz', value)
    save('financial-profiles.json', profiles)
    assert value['answer'] == load('ordinary-answer.json.gz')
    return {'status': 'PASS', 'statement_equity_exact': True,
        'oci_hedge_equal_except_explicit_profile_binding_hashes': True,
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
    assert installer.package_files(previous / 'environment/lib/python3.11/site-packages/legalmath') == read(PRIOR / 'source-package.json')
    temp = Path(tempfile.mkdtemp(prefix='installed-basf-answer-', dir=ROOT / '.localresources/prospectus'))
    save('workspace.json', {'directory': str(temp), 'environment_cloned_from': str(previous)})
    shutil.copytree(previous / 'environment', temp / 'environment', symlinks=True)
    (temp / 'source').mkdir()
    shutil.copyfile(ROOT / 'pyproject.toml', temp / 'source/pyproject.toml')
    shutil.copytree(ROOT / 'src', temp / 'source/src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
    for path, name in ((RUNNER, 'runner.py'), (HELPER, 'helpers.py')): shutil.copyfile(path, temp / name)
    assert installer.package_files(temp / 'source/src/legalmath') == read(HERE / 'source-package.json')
    save('environment-metadata.json', {str(p.relative_to(temp / 'environment')): file_hash(p)
        for p in (temp / 'environment/lib/python3.11/site-packages').glob('*.dist-info/METADATA')})
    return {'status': 'PASS', 'exact017_package_files': len(frozen_package()), 'offline_clone': True}


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
    assert installer.package_files(package) == expected == frozen_package()
    metadata = {str(p.relative_to(workspace() / 'environment')): file_hash(p)
        for p in (workspace() / 'environment/lib/python3.11/site-packages').glob('*.dist-info/METADATA')
        if not p.parent.name.startswith('legalmath-')}
    assert metadata == {p: h for p, h in read(HERE / 'environment-metadata.json').items()
        if not Path(p).parent.name.startswith('legalmath-')}
    for mode in MODES:
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
    ledger = process_ledger.checked(HERE / 'command-ledger.json')
    assert len(ledger['reservations']) == 10 and all(r['state'] == 'STARTED' for r in ledger['reservations'])
    result = {'status': 'PASS', 'task_complete': False,
        'baseline_exact_authenticated_from017': True, 'entire017_package_unchanged': True,
        'ordinary_answer_delta': True, 'matched_omission': True, 'fresh_financial_equality': True,
        'installed_full_reconstruction_and_output_equality': True, 'outer_commands': 10,
        'native_calls': 0, 'http_calls': 0, 'independent_legal_acceptance': False,
        'same_host_only': True, 'further_repairs_allowed': 0}
    save('verified-result.json', result)
    return result


def seal():
    assert not (HERE / 'outputs.json').exists(), 'Attempt already sealed'
    # A corrupted binding or failed preparation must prevent PASS, not sealing.
    binding_error = None
    try: bindings()
    except Exception as error: binding_error = repr(error)
    results = {p.parent.name: read(p) for p in (HERE / 'invocations').glob('*/result.json')}
    seconds, size = elapsed_seconds(), storage_bytes()
    try:
        check_storage()
        storage_passed = True
    except Exception:
        storage_passed = False
    limits_passed = seconds < 1800 and storage_passed
    passed = (not binding_error and set(results) == set(STAGES) and
        all(r['status'] == 'PASS' for r in results.values()) and limits_passed)
    for name in ('RESULT.md', 'NEXT-WORK.md'): assert (HERE / name).is_file()
    save('run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'plan': PLAN, 'result': str((HERE / 'RESULT.md').relative_to(ROOT)),
        'environment': sys.executable, 'cpu_gpu': 'CPU only; no device/framework imports; children CUDA_VISIBLE_DEVICES=-1',
        'data': read(HERE / 'input-aliases.json') if (HERE / 'input-aliases.json').exists() else None,
        'random_seeds': 'N/A deterministic', 'binding_error': binding_error,
        'actual_commands': [read(HERE / 'invocations' / s / 'started.json') for s in STAGES if s in results],
        'prior015017_seconds': prior_seconds(), 'cumulative015018_seconds': seconds,
        'cumulative_evidence_workspace_bytes': size, 'limits_passed': limits_passed, 'stages': results})
    save('result.json', {'status': 'PASS' if passed else 'FAIL', 'task': 'basf-meanings', 'task_complete': False,
        'completed_stages': [s for s in STAGES if s in results and results[s]['status'] == 'PASS'],
        'failed_stages': [s for s, r in results.items() if r['status'] != 'PASS'],
        'independent_legal_acceptance': False, 'result_note': 'RESULT.md',
        'binding_error': binding_error, 'limits_passed': limits_passed, 'further_repairs_allowed': 0})
    outputs = {str(p.relative_to(HERE)): file_hash(p) for p in HERE.rglob('*')
        if p.is_file() and p.name not in {'execution.lock', 'outputs.json'} and '__pycache__' not in p.parts}
    save('outputs.json', outputs)
    print(json.dumps({'status': 'PASS' if passed else 'FAIL', 'sealed_files': len(outputs),
        'cumulative_seconds': seconds, 'cumulative_bytes': storage_bytes()}))


def main():
    stage = sys.argv[1]
    assert stage in (*STAGES, 'seal')
    if stage == 'seal': return seal()
    assert not (HERE / 'outputs.json').exists(), 'Attempt already sealed'
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    tick = time.monotonic()
    command = ['.venv/bin/python', '-m', 'scripts.prospectus_initial_answer_repair', stage]
    save('invocations/' + stage + '/started.json', {'command': command, 'plan': PLAN,
        'environment': sys.executable, 'started_at': datetime.now(timezone.utc).isoformat(),
        'random_seeds': 'N/A deterministic', 'cpu_gpu': 'CPU only; children CUDA_VISIBLE_DEVICES=-1'})
    def expire(signum, frame): raise TimeoutError('120-second initial-answer repair stage bound; no retry')
    def no_native(*args, **kwargs): raise AssertionError('Native extraction forbidden in initial-answer repair')
    service.source_product = no_native
    signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, 120)
    try:
        admission = bindings()
        for previous in STAGES[:STAGES.index(stage)]:
            assert read(HERE / 'invocations' / previous / 'result.json')['status'] == 'PASS'
        spent = elapsed_seconds()
        assert spent < 1800
        check_storage()
        signal.setitimer(signal.ITIMER_REAL, min(120 - (time.monotonic() - tick), 1800 - spent))
        # Only the explicitly budgeted offline build/install/replay may spawn.
        original_popen = subprocess.Popen
        if stage not in ('build', 'install') and not stage.startswith('replay-'):
            subprocess.Popen = no_native
        try:
            details = replay(stage.removeprefix('replay-')) if stage.startswith('replay-') else globals()[stage.replace('-', '_')]()
        finally: subprocess.Popen = original_popen
        bindings()
        wall = time.monotonic() - tick
        assert elapsed_seconds() + wall < 1800
        size = check_storage()
        result = {'status': 'PASS', 'stage': stage, 'git_commit': admission['git_commit'],
            'details': details, 'wall_seconds': wall, 'cumulative_evidence_workspace_bytes': size,
            'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    except BaseException as error:
        (folder / 'traceback.txt').write_text(traceback.format_exc())
        save('invocations/' + stage + '/result.json', {'status': 'FAIL',
            'error': repr(error), 'wall_seconds': time.monotonic() - tick})
        raise
    finally: signal.setitimer(signal.ITIMER_REAL, 0)
    save('invocations/' + stage + '/result.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    with (HERE / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
