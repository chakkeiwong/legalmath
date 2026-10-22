"""Bounded admitted BASF initial-agent P2/P3 repair and offline installed replay."""
from datetime import datetime, timezone
import fcntl
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from scripts import prospectus_initial_agent_runner as checks
from scripts import prospectus_basf_equity as installer
from legalmath.prospectus import basf_default_f, basf_agent_introduction
from legalmath.prospectus.execution_authority import read, file_hash
from legalmath.prospectus.successor import service, process_ledger, basf_notices
from legalmath.prospectus.successor import basf_initial_agents as core
from legalmath.prospectus.successor.contracts import digest

BASE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts/basf-meanings'
HERE, PRIOR, EARLIER = BASE / 'attempt-016', BASE / 'attempt-014', BASE / 'attempt-013'
FAILED = BASE / 'attempt-015'
PLAN = 'docs/plans/prospectus-basf-initial-agent-repair-2026-10-15.md'
RUNNER = ROOT / 'scripts/prospectus_initial_agent_runner.py'
installer.HERE = HERE
PREDECESSORS = {'prepare': (), 'equivalence': ('prepare',), 'dispositions': ('equivalence',),
    'baseline': ('dispositions',), 'construct': ('baseline',), 'interpret': ('construct',),
    'candidate': ('interpret',),
    'omission': ('candidate',), 'financial': ('omission',), 'controls': ('financial',),
    'tests': ('controls',), 'install-prepare': ('tests',), 'build': ('install-prepare',),
    'install': ('build',), 'replay-answer': ('install',), 'replay-financial': ('replay-answer',),
    'replay-controls': ('replay-financial',),
    'verify': ('replay-controls',)}
load = checks.read


def save(name, value): checks.save(HERE / name, value)


def methods():
    names = [Path(__file__), RUNNER, Path(installer.__file__), ROOT / PLAN, ROOT / 'pyproject.toml', HERE / 'EXECUTION-AUDIT.md',
        ROOT / 'tests/prospectus_successor/test_basf_initial_agents.py', ROOT / 'tests/prospectus_successor/test_basf_agent_report.py',
        ROOT / 'tests/prospectus_successor/test_disposition_lookup.py',
        ROOT / 'tests/prospectus_successor/fixtures/basf-agent-source.json']
    names += sorted((ROOT / 'src/legalmath').rglob('*.py'))
    return {str(p.relative_to(ROOT)): file_hash(p) for p in names}


def bindings():
    assert not (HERE / 'outputs.json').exists(), 'Attempt already sealed'
    admission = read(HERE / 'admission.json')
    assert all(file_hash(ROOT / p) == h for p, h in admission['binding'].items())
    for name in ('methods.json', 'protected-inputs.json'):
        if (HERE / name).exists():
            values = read(HERE / name)
            assert (methods() == values) if name == 'methods.json' else all(file_hash(ROOT / p) == h for p, h in values.items())
    return admission


def prepare():
    protected = {}
    for folder in (PRIOR, EARLIER, FAILED):
        for name, sha in read(folder / 'outputs.json').items():
            path = folder / name
            assert file_hash(path) == sha
            protected[str(path.relative_to(ROOT))] = sha
        protected[str((folder / 'outputs.json').relative_to(ROOT))] = file_hash(folder / 'outputs.json')
    sources = read(PRIOR / 'original-sources.json')
    for document in sources:
        for row in [document] + document['images']:
            assert file_hash(ROOT / row['path']) == row['sha256']
            protected[row['path']] = row['sha256']
    save('protected-inputs.json', protected)
    save('methods.json', methods())
    for name in methods():
        target = HERE / 'methods' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    shutil.copyfile(PRIOR / 'products.json.gz', HERE / 'baseline-products.json.gz')
    shutil.copyfile(EARLIER / 'prior-profiles.json', HERE / 'prior-profiles.json')
    save('original-sources.json', sources)
    products = load(HERE / 'baseline-products.json.gz')
    graph, assembly = products['P1']['payload']['graph'], products['P2']['payload']['assembly']
    units = {u['unit']: u for u in assembly['units']}
    spans = core.introduction_spans(units)
    save('initial-source-map.json', {'intro_spans': spans,
        'intro_raw_sources': checks.basf_agent_report._sources(graph, units, spans),
        'caption_node': next(n for n in products['P3']['payload']['clauses']['nodes'] if n['id'] == core.UNKNOWN_ID[:-1] + '6'),
        'intro_unknown_node': next(n for n in products['P3']['payload']['clauses']['nodes'] if n['id'] == core.UNKNOWN_ID),
        'independent_review': False, 'basis': 'Retained original image and selected/raw map review'})
    core.prepare_request(graph, assembly, products['P1']['payload']['request'])
    assert not process_ledger.checked(FAILED / 'command-ledger.json')['reservations']
    process_ledger.create(HERE / 'command-ledger.json', 5, 0,
        'Cumulative015+016: offline build,install,answer,financial,controls;one repair used;no spare')
    return {'status': 'PASS', 'frozen_method_files': len(methods()), 'native_calls': 0, 'http_calls': 0,
        'fresh_baseline_required': True, 'core_source_units': len(spans)}


def baseline():
    products = load(HERE / 'baseline-products.json.gz')
    profiles, profile = read(EARLIER / 'prior-profiles.json'), read(EARLIER / 'profile.json')
    fresh013 = basf_default_f.consume(products, profiles, profile, ROOT,
        expected_prior_profiles_sha256=digest(profiles), expected_profile_sha256=digest(profile))
    assert fresh013 == load(EARLIER / 'default-consumer.json.gz')
    profile014 = read(PRIOR / 'profile.json')
    fresh014 = basf_agent_introduction.consume(products, fresh013, profile014, ROOT,
        expected_prior_sha256=digest(fresh013), expected_profile_sha256=digest(profile014))
    assert fresh014 == load(PRIOR / 'agent-introduction-consumer.json.gz')
    save('baseline-consumer.json.gz', fresh014)
    return {'status': 'PASS', 'fresh_complete_baseline_equal': True,
        'components': ['ordinary', 'statement', 'equity', 'oci', 'hedge', 'body', 'default_f', 'agent_introduction']}


def equivalence():
    import pytest
    code = pytest.main(['-q', 'tests/prospectus_successor/test_disposition_lookup.py',
        '--junitxml=' + str(HERE / 'disposition-equivalence.xml')])
    assert code == 0
    return {'status': 'PASS', 'frozen015_equivalence_and_refusals': True}


def dispositions():
    before = load(HERE / 'baseline-products.json.gz')
    rebuilt = service.construction_product(before['P1'], ROOT)
    assert rebuilt == before['P2'], 'Repaired validator changed the complete real baseline construction'
    report = {'status': 'PASS', 'full_P2_exact': True,
        'reviewed_units': len(rebuilt['payload']['assembly']['reviewed_dispositions']['units'])}
    save('disposition-baseline.json', report)
    return report


def construct():
    built = checks.construct(load(HERE / 'baseline-products.json.gz'), ROOT)
    save('construction-products.json.gz', built)
    return {'status': 'PASS', 'fresh_construction': True}


def interpret():
    before = load(HERE / 'baseline-products.json.gz')
    built = load(HERE / 'construction-products.json.gz')
    products = checks.finish(built['P1'], built['P2'], before)
    transition = core.validate_transition(before, products)
    save('products.json.gz', products)
    save('transition.json', transition)
    return transition


def candidate():
    products = load(HERE / 'products.json.gz')
    answer = service.consume(products, ROOT, mode='frozen')
    comparison = checks.compare_answers(load(HERE / 'baseline-consumer.json.gz')['answer'], answer, products)
    save('ordinary-answer.json.gz', answer)
    save('comparison.json', comparison)
    return comparison


def omission():
    products, before = load(HERE / 'products.json.gz'), load(HERE / 'baseline-products.json.gz')
    omitted = checks.omission(products, before)
    assert omitted['P1'] == products['P1'] and omitted['P2'] == products['P2']
    unknown = next(n for n in before['P3']['payload']['clauses']['nodes'] if n['id'] == core.UNKNOWN_ID)
    effect = basf_notices.matched_omission(products['P2']['payload']['assembly'],
        products['P3']['payload']['clauses'], omitted['P3']['payload']['clauses'], [unknown])
    answer = service.consume(omitted, ROOT, mode='frozen')
    original = load(HERE / 'ordinary-answer.json.gz')
    row = next(r for r in answer['basf_agents']['readings'] if r['id'] == core.IDENTITY)
    legacy = next(r for r in load(HERE / 'baseline-consumer.json.gz')['answer']['basf_agents']['readings'] if r['id'] == core.IDENTITY)
    assert row == legacy and 'appointment_wording' not in row['reading']
    assert answer['basf_agents']['calculation_agent_office'] == 'UNRESOLVED'
    unchanged = set(original) - {'consumed_products', 'questions', 'basf_agents', 'meaning_coverage', 'report_sha256'}
    assert all(original[k] == answer[k] for k in unchanged)
    save('omitted-products.json.gz', omitted)
    save('omitted-answer.json.gz', answer)
    save('matched-omission.json', {'status': 'PASS', 'same_P1_P2': True, 'legacy_initial_reading_restored': True, **effect})
    return {'status': 'PASS', **effect}


def financial():
    result, profiles = checks.financial(load(HERE / 'products.json.gz'), read(HERE / 'prior-profiles.json'),
        load(HERE / 'baseline-consumer.json.gz'), ROOT)
    assert result['answer'] == load(HERE / 'ordinary-answer.json.gz')
    save('current-financial-consumer.json.gz', result)
    save('financial-profiles.json', profiles)
    report = {'status': 'PASS', 'statement_equity_exact': True,
        'oci_hedge_equal_except_explicit_profile_binding_hashes': True,
        'fresh_evaluations': ['statement', 'equity', 'oci', 'hedge'],
        'historical_only': ['body_coverage_review', 'default_f_review', 'agent_introduction_review'],
        'financial_values_validated': False, 'incorporation_resolved': False}
    save('financial-comparison.json', report)
    return report


def controls():
    values = checks.controls(load(HERE / 'products.json.gz'), load(HERE / 'baseline-products.json.gz'),
        load(HERE / 'current-financial-consumer.json.gz'), read(HERE / 'financial-profiles.json'), ROOT)
    save('actual-controls.json', values)
    return {'status': 'PASS', 'refused': len(values)}


def tests():
    import pytest
    code = pytest.main(['-q', 'tests/prospectus_successor/test_basf_initial_agents.py',
        'tests/prospectus_successor/test_basf_agent_report.py', '--junitxml=' + str(HERE / 'tests.xml')])
    assert code == 0
    return {'status': 'PASS', 'pytest_exit': int(code)}


def workspace(): return Path(read(HERE / 'workspace.json')['directory'])


def install_prepare():
    previous = Path(read(PRIOR / 'workspace.json')['directory'])
    old_package = read(PRIOR / 'source-package.json')
    assert installer.package_files(previous / 'environment/lib/python3.11/site-packages/legalmath') == old_package
    temp = Path(tempfile.mkdtemp(prefix='installed-basf-initial-core-', dir=ROOT / '.localresources/prospectus'))
    save('workspace.json', {'directory': str(temp), 'environment_cloned_from': str(previous)})
    shutil.copytree(previous / 'environment', temp / 'environment', symlinks=True)
    (temp / 'source').mkdir()
    shutil.copyfile(ROOT / 'pyproject.toml', temp / 'source/pyproject.toml')
    shutil.copytree(ROOT / 'src', temp / 'source/src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
    shutil.copyfile(RUNNER, temp / 'runner.py')
    package = installer.package_files(temp / 'source/src/legalmath')
    changed = sorted(p for p, h in old_package.items() if package.get(p) != h)
    added = sorted(set(package) - set(old_package))
    assert changed == ['prospectus/successor/admissions.py', 'prospectus/successor/basf_agent_report.py']
    assert added == ['prospectus/successor/basf_initial_agents.py']
    save('source-package.json', package)
    save('package-transition.json', {'status': 'PASS', 'prior_files': len(old_package),
        'unchanged': len(old_package) - len(changed), 'changed': changed, 'added': added})
    return {'status': 'PASS', 'exact_package_files': len(package), 'prior_files_unchanged': len(old_package) - len(changed)}


def build(): return installer.build()
def install(): return installer.install()
def replay_answer():
    assert file_hash(workspace() / 'runner.py') == file_hash(RUNNER)
    installer.run('replay-answer', [str(workspace() / 'environment/bin/python'), '-I', str(workspace() / 'runner.py'), str(HERE), str(ROOT), 'answer'])
    return read(HERE / 'installed-answer/result.json')
def replay_financial():
    assert file_hash(workspace() / 'runner.py') == file_hash(RUNNER)
    installer.run('replay-financial', [str(workspace() / 'environment/bin/python'), '-I', str(workspace() / 'runner.py'), str(HERE), str(ROOT), 'financial'])
    return read(HERE / 'installed-financial/result.json')
def replay_controls():
    assert file_hash(workspace() / 'runner.py') == file_hash(RUNNER)
    installer.run('replay-controls', [str(workspace() / 'environment/bin/python'), '-I', str(workspace() / 'runner.py'), str(HERE), str(ROOT), 'controls'])
    return read(HERE / 'installed-controls/result.json')


def verify():
    answer, control = read(HERE / 'installed-answer/result.json'), read(HERE / 'installed-controls/result.json')
    financial_result = read(HERE / 'installed-financial/result.json')
    assert answer['status'] == control['status'] == financial_result['status'] == 'PASS'
    assert answer['full_output_equal'] and financial_result['financial_outputs_equal']
    assert file_hash(workspace() / 'runner.py') == file_hash(RUNNER)
    expected = read(HERE / 'source-package.json')
    package = workspace() / 'environment/lib/python3.11/site-packages/legalmath'
    assert installer.package_files(package) == expected
    for name in ('answer', 'financial', 'controls'):
        assert read(HERE / ('installed-' + name) / 'package-files.json') == expected
        proof = read(HERE / ('installed-' + name) / 'import-proof.json')
        assert proof['isolated'] == 1
        for row in proof['modules'].values():
            p = Path(row['path']).resolve()
            assert p.is_relative_to(package) and file_hash(p) == row['sha256'] == expected[str(p.relative_to(package))]
    assert load(HERE / 'installed-answer/ordinary-answer.json.gz') == load(HERE / 'ordinary-answer.json.gz')
    assert load(HERE / 'installed-financial/current-financial-consumer.json.gz') == load(HERE / 'current-financial-consumer.json.gz')
    assert read(HERE / 'installed-controls/controls.json') == read(HERE / 'actual-controls.json')
    commands = len(process_ledger.checked(HERE / 'command-ledger.json')['reservations'])
    assert commands == 5 and not process_ledger.checked(FAILED / 'command-ledger.json')['reservations']
    return {'status': 'PASS', 'fresh_complete_baseline_equal': True, 'p3_core_changed': True,
        'ordinary_initial_premise_present': True, 'same_construction_omission_pass': True,
        'fresh_financial_outputs_preserved': True, 'installed_full_output_equal': True,
        'actual_controls_refused': control['controls'], 'exact_package_files': len(expected),
        'outer_commands': commands, 'local_repairs_used': 1, 'further_repairs_allowed': 0, 'native_calls': 0, 'http_calls': 0,
        'independent_legal_acceptance': False, 'different_host_portability': False,
        'historical_visible_native_reservation_lower_bound': 79, 'historical_visible_source_http_lower_bound': 9}


def main():
    stage = sys.argv[1]
    assert stage in PREDECESSORS
    admission = bindings()
    for previous in PREDECESSORS[stage]:
        assert read(HERE / 'invocations' / previous / 'result.json')['status'] == 'PASS'
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    save('invocations/' + stage + '/started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_initial_agent_core', stage],
        'git_commit': admission['git_commit'], 'plan': PLAN, 'environment': sys.executable,
        'started_at': datetime.now(timezone.utc).isoformat(), 'random_seeds': 'N/A deterministic',
        'cpu_gpu': 'CPU only;no framework imports;children CUDA_VISIBLE_DEVICES=-1',
        'required_predecessors': list(PREDECESSORS[stage])})
    tick = time.monotonic()
    def expire(signum, frame): raise TimeoutError('120-second initial-agent core stage bound;no automatic retry')
    def no_native(*args, **kwargs): raise AssertionError('Native extraction forbidden in initial-agent repair')
    service.source_product = no_native
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(120)
    try:
        details = globals()[stage.replace('-', '_')]()
        bindings()
        size = sum(p.stat().st_size for folder in (HERE, FAILED) for p in folder.rglob('*') if p.is_file())
        if (HERE / 'workspace.json').exists():
            size += sum(p.stat().st_size for p in workspace().rglob('*'))
        assert size < 500 * 1024 * 1024, 'Storage bound exceeded'
        result = {'status': 'PASS', 'stage': stage, 'details': details, 'wall_seconds': time.monotonic() - tick,
            'evidence_and_workspace_bytes': size}
    except BaseException as error:
        save('invocations/' + stage + '/result.json', {'status': 'FAIL', 'error': repr(error), 'wall_seconds': time.monotonic() - tick})
        raise
    finally:
        signal.alarm(0)
    save('invocations/' + stage + '/result.json', result)
    print(result)


if __name__ == '__main__':
    with (HERE / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
