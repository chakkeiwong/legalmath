"""Bounded original-task office-condition composition and retained verification."""
from copy import deepcopy
import ast
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, digest, adigest, Authority

PREP = AUTH / 'reviews/office-composition-367'
HERE = AUTH / 'attempts/basf-office/attempt-006'
BASE = AUTH / 'attempts/source-authority/attempt-009'
PRIOR = AUTH / 'attempts/basf-office/attempt-005'
PLAN = 'docs/plans/prospectus-office-replacement-composition-2026-10-20.md'
FILES = [PLAN, 'scripts/prospectus_office_composition.py', 'scripts/prospectus_office_composition_worker.py',
    'src/legalmath/prospectus/successor/office_change.py',
    'src/legalmath/prospectus/successor/office_change_verify.py',
    'src/legalmath/prospectus/successor/service.py',
    'src/legalmath/prospectus/successor/conditional_profiles.py',
    'tests/prospectus_successor/test_office_change.py',
    'tests/prospectus_successor/test_issuer_qualification.py']
TESTS = ['tests/prospectus_successor/' + n for n in ('test_office_change.py',
    'test_agent_notice_application.py', 'test_notice_delivery.py', 'test_conditional_profiles_cli.py',
    'test_acquisition_receipt_integrity.py', 'test_issuer_qualification.py')]
DEPS = {'tests': (), 'ordinary': (), 'package': (), 'installed': ('ordinary', 'package'),
        'reconcile': (), 'seal': ('reconcile',)}
CHECKS = ('tests', 'ordinary', 'package', 'installed')


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    timed = [PREP / n for n in ('reproduction.json', 'development.json', 'preparation-result.json')]
    timed += list(HERE.glob('stages/*/result.json')) + list(HERE.glob('stages/*/failure.json'))
    measured = extra + sum(read(p).get('wall_seconds', 0) for p in timed if p.exists())
    files = {p for d in (PREP, HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update(ROOT / n for n in FILES); files.add(AUTH / 'revisions/0367.json')
    files.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in files if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    total, combined = start['prior_seconds'] + measured + 120, start['prior_bytes'] + size
    assert measured < 900 and size < 156 * 1024**2, 'Incremental office bounds'
    assert total < 12600 and combined < 2044 * 1024**2, 'Original cumulative office bounds'
    return {'combined_accounted_seconds': total, 'combined_bytes': combined,
        'new_measured_seconds': measured, 'new_conservative_other_seconds': 120, 'new_bytes': size,
        'historical_manual_time': 'UNKNOWN', 'old_costs_reset': False, 'seal_reserve_bytes': 4 * 1024**2}


def reproduce():
    started = time.monotonic()
    from legalmath.prospectus.successor import service, conditional_profiles
    assert read(AUTH / 'program.json')['revision'] == 366
    for folder in (BASE, PRIOR):
        for name, checksum in read(folder / 'outputs.json').items(): assert sha(folder / name) == checksum, name
    assert 'office_change_profile' not in inspect.signature(service.consume).parameters
    assert 'office_change' not in conditional_profiles.ORDER
    answer = read(BASE / 'ordinary-answer.json.gz'); assert 'office_change_review' not in answer
    rows = {r['id']: r for r in answer['basf_agents']['readings']}
    office = rows['basf-agents:office-replacement']; effective = rows['basf-agents:effectiveness-reference']
    assert 'in demselben Land' in office['quote'] and office['reading']['same_country'] is True
    assert 'außer im Insolvenzfall' in effective['quote'] and 'gemäß § 13' in effective['quote']
    prior = read(PRIOR / 'result.json')['resources']
    seal_tail = sum((PRIOR / n).stat().st_size for n in ('outputs.json', 'stages/seal/result.json'))
    save(PREP / 'accounting-start.json', {'prior_seconds': prior['combined_measured_seconds'],
        'prior_bytes': prior['combined_bytes'] + seal_tail, 'seal_tail_conservative_bytes': seal_tail,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'program_bytes': (AUTH / 'program.json').stat().st_size, 'old_costs_reset': False})
    for name in ('service.py', 'conditional_profiles.py'):
        target = PREP / 'baseline' / name; target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream: stream.write((ROOT / 'src/legalmath/prospectus/successor' / name).read_bytes())
    save(PREP / 'reproduction.json', {'status': 'CAPABILITY_GAP_CONFIRMED',
        'baseline': rel(BASE / 'ordinary-answer.json.gz'), 'baseline_sha256': sha(BASE / 'ordinary-answer.json.gz'),
        'optional_argument_exists': False, 'office_clause': office, 'effectiveness_clause': effective,
        'notice_cases': len(answer['notice_delivery_review']['scenarios']),
        'not_a_notice_bug': True, 'wall_seconds': time.monotonic() - started})
    return {'status': 'PASS', 'gap': 'Office condition is reported but not composed', 'resources': costs()}


def cases(answer):
    notices = {r['scenario']['id']: r for r in answer['notice_delivery_review']['scenarios']}
    rows = []
    def add(name, notice, original=None, replacement=None, old=None, new=None, applies=None):
        identity = deepcopy(notices[notice]['scenario']['identity'])
        rows.append({'id': name, 'kind': 'HYPOTHETICAL_DEVELOPMENT', 'change_kind': 'OFFICE_REPLACEMENT',
            'identity': identity, 'notice_case': notice, 'country_namespace': 'SCENARIO_LOCAL_COUNTRY_IDENTITY',
            'original_country': original, 'replacement_country': replacement,
            'original_office_designated': old, 'replacement_office_designated': new, 'reading_applies': applies})
    add('all-open', 'all-open')
    for notice in ('PUBLICATION-30', 'PUBLICATION-29', 'CLEARING_SUBSTITUTION-45',
                   'listed_in_lux-None', 'listed_in_lux-conflict', 'insolvency-no-route-or-dates'):
        for suffix, country in (('same', 'COUNTRY_A'), ('different', 'COUNTRY_B'), ('unknown', None), ('conflict', 'conflict')):
            add(notice + '-' + suffix, notice, 'COUNTRY_A', country, True, True, True)
    for field in ('original_office_designated', 'replacement_office_designated', 'reading_applies'):
        for suffix, value in (('false', False), ('unknown', None), ('conflict', 'conflict')):
            add(field + '-' + suffix, 'PUBLICATION-30', 'COUNTRY_A', 'COUNTRY_A', True, True, True)
            rows[-1][field] = value
    return rows


def prepare():
    started = time.monotonic()
    from legalmath.prospectus.successor import office_change as model
    from legalmath.prospectus.successor.office_change_verify import expected
    assert read(PREP / 'reproduction.json')['status'] == 'CAPABILITY_GAP_CONFIRMED'
    assert read(PREP / 'development.json')['exit_code'] == 0
    config = read(AUTH / 'reviews/acquisition-receipt-366/config.json')
    manifest = read(ROOT / config['products'])['products']
    for row in manifest.values(): assert sha(ROOT / row['path']) == row['sha256']
    products = {k: read(ROOT / r['path']) for k, r in manifest.items()}
    answer = read(BASE / 'ordinary-answer.json.gz'); context = model.context(products, answer)
    scenarios = cases(answer); by_id = {r['scenario']['id']: r for r in answer['notice_delivery_review']['scenarios']}
    expected_rows = {}
    for row in scenarios:
        status = by_id[row['notice_case']]['notice']['conditional_notice_precondition']['status']
        result = model.analyze(row, by_id[row['notice_case']], answer['instrument_id'])
        expected_rows[row['id']] = expected(row, status)
        assert result['conditional_office_preconditions']['status'] == expected_rows[row['id']]
    assert expected_rows['PUBLICATION-30-same'] == 'YES'
    assert expected_rows['PUBLICATION-30-different'] == expected_rows['insolvency-no-route-or-dates-different'] == 'NO'
    profile = {'version': model.VERSION, 'products_sha256': digest(products),
        'ordinary_answer_sha256': digest(answer), 'context': context, 'scenarios': scenarios}
    save(PREP / 'profile.json', profile); save(PREP / 'expected.json', expected_rows)
    options = read(ROOT / config['profiles'])
    options['profiles'].append({'name': 'office_change', 'path': rel(PREP / 'profile.json'),
        'file_sha256': sha(PREP / 'profile.json'), 'profile_sha256': digest(profile)})
    save(PREP / 'profiles.json', options)
    sources = read(AUTH / 'reviews/acquisition-receipt-366/source-bindings.json')
    sources.update({rel(BASE / n): sha(BASE / n) for n in ('ordinary-answer.json.gz', 'outputs.json', 'package.json')})
    sources.update({rel(PREP / 'profile.json'): sha(PREP / 'profile.json'), rel(PREP / 'profiles.json'): sha(PREP / 'profiles.json')})
    for path, checksum in sources.items(): assert sha(ROOT / path) == checksum, path
    save(PREP / 'source-bindings.json', sources)
    save(PREP / 'config.json', {**config, 'baseline': rel(BASE / 'ordinary-answer.json.gz'),
        'profiles': rel(PREP / 'profiles.json'), 'old_profiles': config['profiles']})
    save(PREP / 'preparation-result.json', {'status': 'PASS', 'scenarios': len(scenarios),
        'source_and_identity_checked': True, 'wall_seconds': time.monotonic() - started})
    assert time.monotonic() - started < 120
    return {'status': 'PASS', 'scenarios': len(scenarios), 'resources': costs()}


def proposal():
    program = read(AUTH / 'program.json'); assert program['revision'] == 366 and not HERE.exists()
    attempts = [e['attempt'] for e in Authority(ROOT).events() if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-office']
    assert len(attempts) == 5
    production = {rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
    bindings = {n: sha(ROOT / n) for n in FILES + TESTS}
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    bindings.update(production); bindings.update(read(PREP / 'source-bindings.json'))
    save(PREP / 'freeze.json', {'bindings': bindings, 'production': production})
    new = deepcopy(program); new['revision'] = 367
    task = next(t for t in new['tasks'] if t['id'] == 'basf-office')
    task.update(dossier=PLAN, pre_admission_review=PLAN, timeout_seconds=380,
        reason='Compose source-bound same-country/designated-office premises with actual conditional notice results',
        office_composition={'review': rel(PREP), 'original_task_complete': False,
            'new_seconds': 900, 'other_seconds': 120, 'new_bytes': 160 * 1024**2,
            'cumulative_seconds': 12600, 'cumulative_bytes': 2048 * 1024**2})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    new['budgets']['basf-office']['maximum_new_attempts'] = 6
    routes = read(ROOT / program['continuation_review']['routes']); routes['baseline_revision'] = 367
    for row in routes['tasks']:
        if row['task'] == 'basf-office':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Verify source-bound office/notice composition; retain unknown actual office designation and original source requirements',
                stop_condition='6 admissions;900+120s/160MiB new;12600s/2048MiB cumulative;no unchanged retry')
        if row['task'] == 'source-authority':
            row['next_action'] = 'Preserve sealed009 receipt repair; remaining original publication, authenticity and historical availability need distinct evidence'
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Finite office/notice composition; exact complete prior-answer preservation', 'Retain original office and source gaps and five attempts'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN, 'reproduction': rel(PREP / 'reproduction.json')},
        'evidence_contract': {'primary': 'Independent composition decisions, complete ordinary/installed equality and retained source conditions',
            'promotion_veto': ['Wrong composition', 'Changed prior answer', 'Invented office/effectiveness', 'Wrong imports'],
            'continuation_veto': ['Invalid authority', 'Corrupt shared evidence', 'Exhausted bounds'],
            'explanatory_only': ['Counts', 'Time'], 'not_concluded': ['Actual designation', 'Historical law', 'Whole task/build']},
        'budget_revision': {'budget_key': 'basf-office', 'previous_maximum': 5, 'new_maximum': 6,
            'retained_attempts': attempts, 'reason': 'Distinct missing composition confirmed in current source/consumer',
            'next_discriminating_check': 'Same qualifying notice gives YES/NO/UNKNOWN across same/different/missing countries',
            'stop_condition': '900+120s/160MiB new;12600s/2048MiB cumulative;380s consumers;no unchanged retry',
            'same_scope_authorization': 'User requested continued general build; hypothetical facts only; no external or branch actions'}}
    save(PREP / 'proposal.json', new); save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 367, 'resources': costs()}


def frozen():
    admission = read(HERE / 'admission.json')
    assert adigest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items(): assert sha(ROOT / name) == checksum, name


def execute(name, argv, timeout=120, cwd=ROOT):
    folder = HERE / 'commands'; folder.mkdir(exist_ok=True); started = time.monotonic()
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': str(ROOT / 'src'),
        'PYTHONDONTWRITEBYTECODE': '1', 'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    result = None; failure = None
    try:
        with (folder / (name + '.log')).open('x') as output:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
        assert result.returncode == 0, 'Inspect retained ' + name + '.log'
    except Exception as exc:
        failure = {'kind': type(exc).__name__, 'error': str(exc)}; raise
    finally:
        save(folder / (name + '.json'), {'command': argv, 'cwd': str(cwd), 'timeout_seconds': timeout,
            'wall_seconds': time.monotonic() - started, 'exit_code': result.returncode if result else None, 'failure': failure})


def tests():
    execute('tests', [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', *TESTS, '--junitxml=' + str(HERE / 'tests.xml')])
    import xml.etree.ElementTree as ET
    suites = list(ET.parse(HERE / 'tests.xml').getroot().iter('testsuite'))
    assert not any(int(s.get('failures', 0)) or int(s.get('errors', 0)) or int(s.get('skipped', 0)) for s in suites)
    return {'status': 'PASS', 'tests': sum(int(s.get('tests', 0)) for s in suites)}


def ordinary():
    execute('ordinary', [str(ROOT / '.venv/bin/python'), '-B', str(ROOT / 'scripts/prospectus_office_composition_worker.py'),
        str(ROOT), str(PREP), str(HERE), 'ordinary'], 380)
    return {'status': 'PASS', **read(HERE / 'ordinary-verification.json')}


def package():
    folder = HERE / 'package-source'; folder.mkdir()
    shutil.copyfile(ROOT / 'pyproject.toml', folder / 'pyproject.toml')
    shutil.copytree(ROOT / 'src', folder / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
    python = read(PREP / 'config.json')['package_python']
    execute('wheel', [python, '-I', '-B', '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
        '--no-index', '--wheel-dir', str(HERE / 'wheel'), str(folder)])
    wheels = list((HERE / 'wheel').glob('*.whl')); assert len(wheels) == 1
    expected = {str(Path(n).relative_to('src/legalmath')): h for n, h in read(PREP / 'freeze.json')['production'].items()}
    with zipfile.ZipFile(wheels[0]) as archive:
        actual = {n.removeprefix('legalmath/'): digest(archive.read(n)) for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual == expected
    execute('install', [python, '-I', '-B', '-m', 'pip', 'install', '--no-index', '--no-deps', '--no-compile',
        '--target', str(HERE / 'installed'), str(wheels[0])])
    assert {str(p.relative_to(HERE / 'installed/legalmath')): sha(p) for p in (HERE / 'installed/legalmath').rglob('*') if p.is_file()} == expected
    save(HERE / 'package.json', {'python': python, 'files': expected, 'wheel_sha256': sha(wheels[0])})
    return {'status': 'PASS', 'source_matched_files': len(expected)}


def installed():
    execute('installed', [read(HERE / 'package.json')['python'], '-I', '-B', str(ROOT / 'scripts/prospectus_office_composition_worker.py'),
        str(ROOT), str(PREP), str(HERE), 'installed'], 380, HERE)
    return {'status': 'PASS', **read(HERE / 'installed-verification.json')}


def states():
    result = {}
    for stage in DEPS:
        folder = HERE / 'stages' / stage
        if (folder / 'result.json').exists(): result[stage] = read(folder / 'result.json')['status']
        elif (folder / 'failure.json').exists(): result[stage] = 'FAIL'
        elif (folder / 'started.json').exists(): result[stage] = 'INTERRUPTED_OR_RUNNING'
        elif any(result.get(d) in ('FAIL', 'BLOCKED') for d in DEPS[stage]): result[stage] = 'BLOCKED'
        else: result[stage] = 'PENDING'
    ready = [s for s in DEPS if result[s] == 'PENDING' and all(result[d] == 'PASS' for d in DEPS[s])]
    if not all(result[s] in ('PASS', 'FAIL', 'BLOCKED') for s in CHECKS): ready = [s for s in ready if s not in ('reconcile', 'seal')]
    return {'stages': result, 'ready': ready, 'whole_build_complete': False}


def reconcile():
    outcome = states()['stages']
    save(HERE / 'original-requirements.json', {'original_task_complete': False,
        'remaining': ['Actual issue-specific designated office', 'Historical applicability',
            'Full original source/meaning acceptance', 'Final current native/recovery acceptance'],
        'outcomes': {s: outcome[s] for s in CHECKS}, 'external_adviser_opinion_required': False})
    return {'status': 'PASS', 'candidate_passed': all(outcome[s] == 'PASS' for s in CHECKS)}


def seal():
    outcome = states()['stages']; assert (HERE / 'RESULT.md').is_file()
    result = {'status': 'PASS' if all(outcome[s] == 'PASS' for s in CHECKS) else 'FAIL',
        'task': 'basf-office', 'original_task_complete': False, 'resources': costs(),
        'result_kind': 'CONDITIONAL_OFFICE_NOTICE_COMPOSITION', 'checks': {s: outcome[s] for s in CHECKS},
        'next_action': 'Retain missing actual designation; reconcile remaining original source and build requirements'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p) for p in sorted((HERE / 'commands').glob('*.json'))],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;GPU intentionally hidden',
        'seeds': 'N/A deterministic finite checks', 'data_version': sha(PREP / 'source-bindings.json'),
        'plan': PLAN, 'result': rel(HERE / 'result.json'), 'resources': costs()})
    return result


def main():
    action = sys.argv[1]
    if action in ('reproduce', 'prepare', 'proposal', 'status'): return states() if action == 'status' else globals()[action]()
    assert action in states()['ready'], 'Stage not ready; inspect retained worker/result'
    frozen(); costs(); started = time.monotonic(); folder = HERE / 'stages' / action
    save(folder / 'started.json', {'command': sys.argv, 'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat()})
    try:
        result = globals()[action](); frozen(); costs(time.monotonic() - started)
        save(folder / 'result.json', {**result, 'wall_seconds': time.monotonic() - started})
    except Exception as error:
        save(folder / 'failure.json', {'status': 'FAIL', 'kind': type(error).__name__, 'error': str(error), 'wall_seconds': time.monotonic() - started}); raise
    if action == 'seal':
        save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
            if p.is_file() and p.name not in ('admission.json', 'outputs.json') and '__pycache__' not in p.parts
            and not any(n in p.parts for n in ('installed', 'package-source'))})
    return {'status': result['status'], 'stage': action, 'frontier': states(), 'resources': costs()}


if __name__ == '__main__': print(json.dumps(main()))
