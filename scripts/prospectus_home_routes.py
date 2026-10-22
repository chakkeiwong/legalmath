"""Retained, bounded automatic/provisional home-state consumer work."""
from copy import deepcopy
from datetime import datetime, timezone
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, digest, adigest, Authority
from scripts import prospectus_office_composition as harness

PREP = AUTH / 'reviews/home-routes-376'
HERE = AUTH / 'attempts/basf-references/attempt-109'
BASE = AUTH / 'attempts/basf-references/attempt-106'
PRIOR = AUTH / 'attempts/basf-references/attempt-108'
PLAN = 'docs/plans/prospectus-home-routes-2026-10-20.md'
FILES = [PLAN, 'scripts/prospectus_home_routes.py', 'scripts/prospectus_home_routes_worker.py',
    'scripts/prospectus_office_composition.py', 'scripts/prospectus_default_holder.py',
    'src/legalmath/prospectus/successor/home_routes.py',
    'src/legalmath/prospectus/successor/home_routes_verify.py',
    'src/legalmath/prospectus/successor/service.py',
    'src/legalmath/prospectus/successor/conditional_profiles.py',
    'tests/prospectus_successor/test_home_routes.py']
TESTS = ['tests/prospectus_successor/' + n for n in
    ('test_home_routes.py', 'test_election.py', 'test_issuer_qualification.py',
     'test_publication_routes.py', 'test_conditional_profiles_cli.py',
     'test_acquisition_receipt_integrity.py', 'test_consumed_reference_closure.py')]
DEPS = {'tests': (), 'ordinary': (), 'package': (), 'installed': ('ordinary', 'package'),
        'reconcile': (), 'seal': ('reconcile',)}
CHECKS = ('tests', 'ordinary', 'package', 'installed')
harness.PREP, harness.HERE, harness.TESTS = PREP, HERE, TESTS


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    records = list(PREP.glob('*-execution.json'))
    records += list(HERE.glob('stages/*/result.json')) + list(HERE.glob('stages/*/failure.json'))
    measured = extra + sum(read(p).get('wall_seconds', 0) for p in records)
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in FILES); paths.add(AUTH / 'revisions/0376.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    total, combined = start['prior_seconds'] + measured + 120, start['prior_bytes'] + size
    assert measured < 1200 and size < 124 * 1024**2, 'Home-route increment exhausted'
    assert total < 31000 and combined < 4540 * 1024**2, 'Retained cumulative bounds exhausted'
    return {'combined_accounted_seconds': total, 'combined_bytes': combined,
        'new_measured_seconds': measured, 'new_conservative_other_seconds': 120, 'new_bytes': size,
        'historical_manual_seconds': 'UNKNOWN', 'old_costs_reset': False}


def reproduce():
    began = time.monotonic()
    from scripts.prospectus_ordinance_navigation import costs as prior_costs
    from legalmath.prospectus.successor import service, conditional_profiles
    program = read(AUTH / 'program.json')
    assert program['revision'] == 375 and not PREP.exists() and not HERE.exists()
    for folder in (BASE, PRIOR, AUTH / 'attempts/basf-references/attempt-098',
                   AUTH / 'attempts/basf-references/attempt-102'):
        for name, checksum in read(folder / 'outputs.json').items(): assert sha(folder / name) == checksum, name
    baseline = read(BASE / 'ordinary-answer.json.gz')
    assert baseline == read(BASE / 'installed-answer.json.gz')
    assert read(BASE / 'installed-verification.json')['complete_installed_equal'] is True
    assert 'home_routes_profile' not in inspect.signature(service.consume).parameters
    assert 'home_routes' not in conditional_profiles.ORDER and 'home_routes_review' not in baseline
    previous = prior_costs()
    assert previous['combined_accounted_seconds'] + 1320 < 31000
    assert previous['combined_bytes'] + 128 * 1024**2 < 4544 * 1024**2
    save(PREP / 'accounting-start.json', {'prior_seconds': previous['combined_accounted_seconds'],
        'prior_bytes': previous['combined_bytes'], 'prior_resources': previous,
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')]})
    for name in ('service.py', 'conditional_profiles.py'):
        p = PREP / 'before' / name; p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('xb') as stream: stream.write((ROOT / 'src/legalmath/prospectus/successor' / name).read_bytes())
    save(PREP / 'reproduction-execution.json', {'status': 'CAPABILITY_GAP_CONFIRMED',
        'baseline': rel(BASE / 'ordinary-answer.json.gz'), 'baseline_sha256': sha(BASE / 'ordinary-answer.json.gz'),
        'complete_installed_equal': True, 'missing_routes': ['SECTION2_13_1A', 'SECTION2_13_3'],
        'original_election_model_wrong': False, 'wall_seconds': time.monotonic() - began})
    return {'status': 'PASS', 'resources': costs()}


def development():
    began = time.monotonic()
    assert read(PREP / 'reproduction-execution.json')['status'] == 'CAPABILITY_GAP_CONFIRMED'
    command = [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', TESTS[0]]
    env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1'}
    with (PREP / 'development.log').open('x') as output:
        run = subprocess.run(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=60)
    save(PREP / 'development-execution.json', {'command': command, 'exit_code': run.returncode,
        'wall_seconds': time.monotonic() - began, 'role': 'DEVELOPMENT_ONLY'})
    assert run.returncode == 0, 'Inspect retained development.log'
    return {'status': 'PASS', 'resources': costs()}


def cases():
    from legalmath.prospectus.successor import home_routes as model
    rows = []
    def add(name, route, changes=None, base='german-domestic', opened=False):
        facts = dict.fromkeys(model.domains(route)) if opened else {
            'instrument_class': model.INSTRUMENT[0], 'seat': 'GERMANY',
            'admission_at_evaluation': 'GERMANY_ONLY', 'reading_applies': True}
        if route == model.ROUTES[1] and not opened:
            facts.update(seat='THIRD_COUNTRY', prior_election_at_evaluation='NO_PRIOR_OTHER',
                         effective_home_choice='NONE_EFFECTIVE')
        facts.update(changes or {})
        rows.append({'id': name, 'kind': 'HYPOTHETICAL_DEVELOPMENT',
                     'route': route, 'base_case': base, 'facts': facts})
    automatic, provisional = model.ROUTES
    add('all-open', automatic, base='all-open', opened=True)
    add('automatic-complete', automatic)
    for key, domain in model.domains(automatic).items():
        for value in (*domain, None, 'conflict'):
            add('automatic-' + key + '-' + str(value), automatic, {key: value})
    add('provisional-complete', provisional)
    for instrument in model.INSTRUMENT:
        for history in model.HISTORY:
            add('provisional-history-' + instrument + '-' + history, provisional,
                {'instrument_class': instrument, 'prior_election_at_evaluation': history})
    for key in ('effective_home_choice', 'admission_at_evaluation', 'reading_applies'):
        for value in (*model.domains(provisional)[key], None, 'conflict'):
            add('provisional-' + key + '-' + str(value), provisional, {key: value})
    for seat in model.SEAT:
        add('provisional-other-instruments-' + seat, provisional,
            {'instrument_class': model.INSTRUMENT[1], 'seat': seat})
    add('provisional-foreign-only-eligible', provisional, {'instrument_class': model.INSTRUMENT[1],
        'seat': 'GERMANY', 'admission_at_evaluation': 'OTHER_EU_EEA_ONLY'})
    for key in ('instrument_class', 'seat', 'prior_election_at_evaluation'):
        for value in (None, 'conflict'):
            add('provisional-' + key + '-' + str(value), provisional, {key: value})
    for base in ('german-excluded', 'german-no-foreign-duty', 'home-open'):
        add('automatic-shared-admission-' + base, automatic, base=base)
        add('automatic-foreign-only-' + base, automatic,
            {'admission_at_evaluation': 'OTHER_EU_EEA_ONLY'}, base=base)
    assert len(rows) <= 64
    return rows


def prepare():
    began = time.monotonic()
    from legalmath.prospectus.successor import home_routes as model
    from legalmath.prospectus.successor.home_routes_verify import expected
    assert read(PREP / 'development-execution.json')['exit_code'] == 0
    config = read(AUTH / 'reviews/reference-validation-373/config.json')
    ordinary = read(BASE / 'ordinary-answer.json.gz')
    manifest = read(ROOT / config['products'])['products']
    for row in manifest.values(): assert sha(ROOT / row['path']) == row['sha256']
    products = {key: read(ROOT / row['path']) for key, row in manifest.items()}
    scenarios = cases(); expected_rows = {r['id']: expected(r['route'], r['facts']) for r in scenarios}
    assert all(model.analyze(r['route'], r['facts']) == expected_rows[r['id']] for r in scenarios)
    for name in ('automatic-complete', 'provisional-complete'):
        assert expected_rows[name]['statuses']['german_route'] == 'YES'
    row = expected_rows['provisional-foreign-only-eligible']['statuses']
    assert row['permission_to_choose'] == 'YES' and row['german_route'] == 'NO'
    profile = {'version': model.VERSION, 'products_sha256': digest(products),
        'ordinary_answer_sha256': digest(ordinary), 'context': model.context(ordinary, ROOT), 'scenarios': scenarios}
    save(PREP / 'profile.json', profile); save(PREP / 'expected.json', expected_rows)
    options = read(ROOT / config['profiles'])
    options['profiles'].append({'name': 'home_routes', 'path': rel(PREP / 'profile.json'),
        'file_sha256': sha(PREP / 'profile.json'), 'profile_sha256': digest(profile)})
    save(PREP / 'profiles.json', options)
    sources = read(AUTH / 'reviews/election-consumer-370/source-bindings.json')
    sources.update({rel(BASE / n): sha(BASE / n) for n in ('ordinary-answer.json.gz', 'outputs.json', 'package.json')})
    sources.update({rel(PREP / n): sha(PREP / n) for n in ('profile.json', 'profiles.json')})
    for name, checksum in sources.items(): assert sha(ROOT / name) == checksum, name
    save(PREP / 'source-bindings.json', sources)
    save(PREP / 'config.json', {**config, 'baseline': rel(BASE / 'ordinary-answer.json.gz'),
        'profiles': rel(PREP / 'profiles.json'), 'old_profiles': config['profiles']})
    save(PREP / 'preparation-execution.json', {'status': 'PASS', 'scenarios': len(scenarios),
        'wall_seconds': time.monotonic() - began})
    return {'status': 'PASS', 'scenarios': len(scenarios), 'resources': costs()}


def proposal():
    began = time.monotonic()
    from legalmath.prospectus.successor.home_routes import evaluate
    from legalmath.prospectus.successor.home_routes_verify import verify
    config = read(PREP / 'config.json'); profile = read(PREP / 'profile.json')
    products = {k: read(ROOT / r['path']) for k, r in read(ROOT / config['products'])['products'].items()}
    ordinary = read(BASE / 'ordinary-answer.json.gz')
    body = {k: v for k, v in ordinary.items() if k != 'report_sha256'}
    body.update(evaluate(products, ordinary, profile, ROOT, expected_profile_sha256=digest(profile)))
    checked = verify({**body, 'report_sha256': digest(body)}, ordinary, profile, products, ROOT)
    assert checked['changed_scenarios'] > 0
    save(PREP / 'preflight-execution.json', {**checked, 'role': 'LOCAL_PREPARATION_NOT_CLI',
        'wall_seconds': time.monotonic() - began})
    program = read(AUTH / 'program.json'); assert program['revision'] == 375 and not HERE.exists()
    attempts = [e['attempt'] for e in Authority(ROOT).events()
                if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 108
    production = {rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
    bindings = {n: sha(ROOT / n) for n in FILES + TESTS}
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file()})
    bindings.update(production); bindings.update(read(PREP / 'source-bindings.json'))
    bindings.update({rel(PRIOR / n): sha(PRIOR / n) for n in ('outputs.json', 'result.json', 'RESULT.md')})
    save(PREP / 'freeze.json', {'bindings': bindings, 'production': production})
    new = deepcopy(program); new['revision'] = 376
    task = next(t for t in new['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN, timeout_seconds=380,
        reason='Integrate retained automatic/provisional home-state provisions into the conditional issuer/publication answer',
        home_route_consumer={'review': rel(PREP), 'original_task_complete': False,
            'new_measured_seconds': 1200, 'new_other_seconds': 120, 'new_bytes': 128 * 1024**2,
            'cumulative_seconds': 31000, 'cumulative_bytes': 4544 * 1024**2}, build_criteria_scope=[])
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    new['budgets']['basf-references']['maximum_new_attempts'] = 109
    routes = read(ROOT / program['continuation_review']['routes']); routes['baseline_revision'] = 376
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Validate automatic/provisional German routes through complete ordinary and installed answers; preserve temporal and source gaps',
                stop_condition='109admissions;1200measured+120other seconds/128MiB;unchanged31000s/4544MiB cumulative;no unchanged retry')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n)
        for n in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Source-bound automatic/provisional routes with shared admission facts and open alternatives'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN, 'reproduction': rel(PREP / 'reproduction-execution.json')},
        'evidence_contract': {'primary': 'Independent source-bound decisions, downstream effects, full prior preservation and installed equality',
            'promotion_veto': ['Wrong route', 'Invented publication condition', 'Contradictory admission facts',
                               'Source/temporal drift', 'Changed prior answer', 'Permissive corruption controls'],
            'continuation_veto': ['Invalid authority', 'Corrupt common evidence', 'Exhausted retained limits'],
            'explanatory_only': ['Counts', 'Runtime'],
            'not_concluded': ['Actual home state', 'Historical law', 'Complete legal test', 'Whole task/build', 'Package defect']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 108, 'new_maximum': 109,
            'retained_attempts': attempts, 'reason': 'Distinct missing source-to-answer routes confirmed in complete106 baseline',
            'next_discriminating_check': 'Automatic/provisional conditions change the real issuer answer while failed routes keep other home states open',
            'stop_condition': '1200+120seconds/128MiB;unchanged31000seconds/4544MiB cumulative;one formal run per stage',
            'same_scope_authorization': 'Continue authorized internally checked general build without external calls or branch actions',
            'all_prior_costs_retained': True, 'cumulative_limits_unchanged': True}}
    save(PREP / 'proposal.json', new); save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 376, 'resources': costs()}


def frozen():
    admission = read(HERE / 'admission.json')
    assert adigest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items(): assert sha(ROOT / name) == checksum, name


def tests(): return harness.tests()
def package(): return harness.package()


def worker(mode):
    python = read(HERE / 'package.json')['python'] if mode == 'installed' else str(ROOT / '.venv/bin/python')
    command = [python, *(['-I'] if mode == 'installed' else []), '-B',
        str(ROOT / 'scripts/prospectus_home_routes_worker.py'), str(ROOT), str(PREP), str(HERE), mode]
    harness.execute(mode, command, 380, HERE if mode == 'installed' else ROOT)
    return {'status': 'PASS', **read(HERE / (mode + '-verification.json'))}


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
    if not all(result[s] in ('PASS', 'FAIL', 'BLOCKED') for s in CHECKS):
        ready = [s for s in ready if s not in ('reconcile', 'seal')]
    return {'stages': result, 'ready': ready, 'whole_build_complete': False}


def reconcile():
    outcome = states()['stages']
    save(HERE / 'original-requirements.json', {'original_task_complete': False,
        'remaining': ['Historical applicability/commencement', 'Implementing rules',
            'Raw issuer/securities category classification', 'Foreign election law and actual facts',
            'Original reference coverage and source-to-answer acceptance', 'Remaining general-build tasks'],
        'outcomes': {s: outcome[s] for s in CHECKS}, 'external_opinion_required': False})
    return {'status': 'PASS', 'candidate_passed': all(outcome[s] == 'PASS' for s in CHECKS)}


def seal():
    outcome = states()['stages']; assert (HERE / 'RESULT.md').is_file()
    result = {'status': 'PASS' if all(outcome[s] == 'PASS' for s in CHECKS) else 'FAIL',
        'task': 'basf-references', 'original_task_complete': False, 'resources': costs(),
        'result_kind': 'CONDITIONAL_AUTOMATIC_PROVISIONAL_HOME_ROUTES',
        'checks': {s: outcome[s] for s in CHECKS},
        'next_action': 'Preserve conditional route integration; inspect cumulative limits and remaining source/semantic frontier'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p) for p in sorted((HERE / 'commands').glob('*.json'))],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;GPU intentionally hidden',
        'seeds': 'N/A deterministic finite checks', 'data_version': sha(PREP / 'source-bindings.json'),
        'plan': PLAN, 'result': rel(HERE / 'result.json'), 'resources': costs()})
    return result


def main():
    action = sys.argv[1]
    if action in ('reproduce', 'development', 'prepare', 'proposal', 'status'):
        return states() if action == 'status' else globals()[action]()
    assert action in states()['ready'], 'Stage not ready; inspect retained result/worker'
    frozen(); costs(); began = time.monotonic(); folder = HERE / 'stages' / action
    save(folder / 'started.json', {'command': sys.argv, 'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat()})
    try:
        result = worker(action) if action in ('ordinary', 'installed') else globals()[action]()
        frozen(); costs(time.monotonic() - began)
        save(folder / 'result.json', {**result, 'wall_seconds': time.monotonic() - began})
    except Exception as error:
        save(folder / 'failure.json', {'status': 'FAIL', 'kind': type(error).__name__,
            'error': str(error), 'wall_seconds': time.monotonic() - began}); raise
    if action == 'seal':
        save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
            if p.is_file() and p.name not in ('admission.json', 'outputs.json') and '__pycache__' not in p.parts
            and not any(n in p.parts for n in ('installed', 'package-source'))})
    return {'status': result['status'], 'stage': action, 'frontier': states(), 'resources': costs()}


if __name__ == '__main__': print(json.dumps(main()))
