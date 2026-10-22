"""Bounded source-to-answer election integration under the original task."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, digest, adigest, Authority
from scripts import prospectus_office_composition as harness

PREP = AUTH / 'reviews/election-consumer-370'
HERE = AUTH / 'attempts/basf-references/attempt-103'
BASE = AUTH / 'attempts/basf-office/attempt-006'
SOURCE = AUTH / 'attempts/basf-references/attempt-102'
PLAN = 'docs/plans/prospectus-election-consumer-2026-10-20.md'
FILES = [PLAN, 'scripts/prospectus_election_consumer.py', 'scripts/prospectus_election_consumer_worker.py',
    'scripts/prospectus_office_composition.py', 'scripts/prospectus_default_holder.py',
    'src/legalmath/prospectus/successor/election.py', 'src/legalmath/prospectus/successor/election_verify.py',
    'src/legalmath/prospectus/successor/service.py', 'src/legalmath/prospectus/successor/conditional_profiles.py',
    'tests/prospectus_successor/test_election.py', 'tests/prospectus_successor/test_office_change.py']
TESTS = ['tests/prospectus_successor/' + n for n in
    ('test_election.py', 'test_issuer_qualification.py', 'test_office_change.py',
     'test_publication_routes.py', 'test_conditional_profiles_cli.py', 'test_acquisition_receipt_integrity.py')]
DEPS = {'tests': (), 'ordinary': (), 'package': (), 'installed': ('ordinary', 'package'),
        'reconcile': (), 'seal': ('reconcile',)}
CHECKS = ('tests', 'ordinary', 'package', 'installed')
# Reuse only the existing local command, test and byte-checked package helpers.
# This process-local configuration never edits their sealed historical sources.
harness.PREP, harness.HERE, harness.TESTS = PREP, HERE, TESTS


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    records = [PREP / n for n in ('reproduction.json', 'development.json', 'preparation-result.json', 'preflight-result.json')]
    records += list(HERE.glob('stages/*/result.json')) + list(HERE.glob('stages/*/failure.json'))
    measured = extra + sum(read(p).get('wall_seconds', 0) for p in records if p.exists())
    files = {p for d in (PREP, HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update(ROOT / n for n in FILES); files.add(AUTH / 'revisions/0370.json')
    files.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in files if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    total, combined = start['prior_seconds'] + measured + 120, start['prior_bytes'] + size
    assert measured < 1100 and size < 156 * 1024**2, 'Election increment exhausted'
    assert total < 29000 and combined < 4348 * 1024**2, 'Retained reference cumulative bounds exhausted'
    return {'combined_accounted_seconds': total, 'combined_bytes': combined,
        'new_measured_seconds': measured, 'new_conservative_other_seconds': 120, 'new_bytes': size,
        'historical_manual_seconds': 'UNKNOWN', 'old_costs_reset': False, 'seal_reserve_bytes': 4 * 1024**2}


def development():
    began = time.monotonic(); assert not (PREP / 'development.json').exists()
    command = [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', 'tests/prospectus_successor/test_election.py']
    env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1'}
    with (PREP / 'development.log').open('x') as output:
        run = subprocess.run(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=120)
    save(PREP / 'development.json', {'command': command, 'exit_code': run.returncode,
        'wall_seconds': time.monotonic() - began, 'role': 'DEVELOPMENT_ONLY'})
    assert run.returncode == 0, 'Inspect retained development.log'
    return {'status': 'PASS', 'resources': costs()}


def cases():
    from legalmath.prospectus.successor import election as model
    rows = []
    def add(name, route, base='german-domestic', changes=None, opened=False):
        facts = dict.fromkeys(model.domains(route)) if opened else {k: False for k in model.domains(route)}
        if not opened:
            facts.update(category_satisfied=True, germany_choice_made=True,
                         publication_under_section5=True, reading_applies=True,
                         prior_election_at_choice='NO_PRIOR_OTHER', admission_at_evaluation='GERMANY_ONLY')
        facts.update(changes or {})
        rows.append({'id': name, 'kind': 'HYPOTHETICAL_DEVELOPMENT', 'base_case': base,
                     'route': route, 'facts': facts})
    add('all-open', model.ROUTES[0], 'all-open', opened=True)
    for route in model.ROUTES:
        label = 'route1b' if route == model.ROUTES[0] else 'route2'
        add(label + '-complete', route)
        for history in model.PRIOR:
            add(label + '-' + history, route, changes={'prior_election_at_choice': history})
        for field in ('category_satisfied', 'germany_choice_made', 'publication_under_section5', 'reading_applies'):
            for value in (False, None, 'conflict'):
                add(label + '-' + field + '-' + str(value), route, changes={field: value})
        add(label + '-foreign-only-no-new', route, changes={'admission_at_evaluation': 'OTHER_EU_EEA_ONLY'})
        add(label + '-foreign-only-new', route, changes={'admission_at_evaluation': 'OTHER_EU_EEA_ONLY', 'new_home_choice_made': True})
        add(label + '-no-market', route, changes={'admission_at_evaluation': 'NONE'})
    for value in (False, True, None, 'conflict'):
        add('route2-mixed-new-years-' + str(value), model.ROUTES[1], changes={
            'admission_at_evaluation': 'GERMANY_AND_OTHER_EU_EEA', 'new_home_choice_made': True,
            'germany_choice_at_least_three_years': value})
    add('route2-three-years-without-new-choice', model.ROUTES[1], changes={
        'admission_at_evaluation': 'GERMANY_AND_OTHER_EU_EEA', 'germany_choice_at_least_three_years': True})
    add('route2-category1-issuance', model.ROUTES[1], changes={'category1_admitted_issuance': True})
    for base in ('german-excluded', 'german-no-foreign-duty', 'home-open', 'interpretations-diverge-included'):
        add('downstream-' + base, model.ROUTES[0], base)
    return rows


def prepare():
    began = time.monotonic()
    from legalmath.prospectus.successor import election as model
    from legalmath.prospectus.successor.election_verify import expected
    assert read(PREP / 'development.json')['exit_code'] == 0
    assert read(PREP / 'reproduction.json')['status'] == 'CAPABILITY_GAP_CONFIRMED'
    for folder in (BASE, SOURCE):
        for name, checksum in read(folder / 'outputs.json').items(): assert sha(folder / name) == checksum, name
    config = read(AUTH / 'reviews/office-composition-367/config.json')
    config.update(baseline=rel(BASE / 'ordinary-answer.json.gz'),
                  profiles=rel(AUTH / 'reviews/office-composition-367/profiles.json'))
    products = {k: read(ROOT / r['path']) for k, r in read(ROOT / config['products'])['products'].items()}
    ordinary = read(BASE / 'ordinary-answer.json.gz'); scenarios = cases()
    expected_rows = {r['id']: expected(r['route'], r['facts']) for r in scenarios}
    assert all(model.analyze(r['route'], r['facts']) == expected_rows[r['id']] for r in scenarios)
    assert expected_rows['route1b-complete']['statuses']['continuing_german_route'] == 'YES'
    assert expected_rows['route2-mixed-new-years-True']['statuses']['continuing_german_route'] == 'NO'
    profile = {'version': model.VERSION, 'products_sha256': digest(products),
        'ordinary_answer_sha256': digest(ordinary), 'context': model.context(ordinary, ROOT), 'scenarios': scenarios}
    save(PREP / 'profile.json', profile); save(PREP / 'expected.json', expected_rows)
    options = read(ROOT / config['profiles'])
    options['profiles'].append({'name': 'election', 'path': rel(PREP / 'profile.json'),
        'file_sha256': sha(PREP / 'profile.json'), 'profile_sha256': digest(profile)})
    save(PREP / 'profiles.json', options)
    sources = read(AUTH / 'reviews/office-composition-367/source-bindings.json')
    sources.update({rel(BASE / n): sha(BASE / n) for n in ('ordinary-answer.json.gz', 'outputs.json', 'package.json')})
    sources.update({rel(SOURCE / n): sha(SOURCE / n) for n in read(SOURCE / 'outputs.json')})
    sources.update({rel(SOURCE / 'outputs.json'): sha(SOURCE / 'outputs.json')})
    sources.update({rel(PREP / n): sha(PREP / n) for n in ('profile.json', 'profiles.json')})
    for name, checksum in sources.items(): assert sha(ROOT / name) == checksum, name
    save(PREP / 'source-bindings.json', sources)
    save(PREP / 'config.json', {**config, 'profiles': rel(PREP / 'profiles.json'), 'old_profiles': config['profiles']})
    save(PREP / 'preparation-result.json', {'status': 'PASS', 'scenarios': len(scenarios),
        'wall_seconds': time.monotonic() - began, 'prior_answer': rel(BASE / 'ordinary-answer.json.gz')})
    return {'status': 'PASS', 'scenarios': len(scenarios), 'resources': costs()}


def proposal():
    began = time.monotonic()
    from legalmath.prospectus.successor.election import evaluate
    from legalmath.prospectus.successor.election_verify import verify
    config = read(PREP / 'config.json'); profile = read(PREP / 'profile.json')
    products = {k: read(ROOT / r['path']) for k, r in read(ROOT / config['products'])['products'].items()}
    ordinary = read(BASE / 'ordinary-answer.json.gz')
    body = {k: v for k, v in ordinary.items() if k != 'report_sha256'}
    body.update(evaluate(products, ordinary, profile, ROOT, expected_profile_sha256=digest(profile)))
    checked = verify({**body, 'report_sha256': digest(body)}, ordinary, profile, products, ROOT)
    assert checked['changed_scenarios'] > 0
    save(PREP / 'preflight-result.json', {**checked, 'role': 'LOCAL_PREPARATION_NOT_CLI',
        'wall_seconds': time.monotonic() - began})
    program = read(AUTH / 'program.json'); assert program['revision'] == 369 and not HERE.exists()
    attempts = [e['attempt'] for e in Authority(ROOT).events()
                if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 102
    production = {rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
    bindings = {n: sha(ROOT / n) for n in FILES + TESTS}
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    bindings.update(production); bindings.update(read(PREP / 'source-bindings.json'))
    save(PREP / 'freeze.json', {'bindings': bindings, 'production': production})
    new = deepcopy(program); new['revision'] = 370
    task = next(t for t in new['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN, timeout_seconds=380,
        reason='Integrate recovered election provisions into the actual conditional issuer/publication answer',
        election_consumer={'review': rel(PREP), 'original_task_complete': False,
            'new_measured_seconds': 1100, 'new_other_seconds': 120, 'new_bytes': 160 * 1024**2,
            'previous_cumulative_seconds': 28000, 'cumulative_seconds': 29000,
            'cumulative_bytes': 4352 * 1024**2}, build_criteria_scope=[])
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    new['budgets']['basf-references']['maximum_new_attempts'] = 103
    routes = read(ROOT / program['continuation_review']['routes']); routes['baseline_revision'] = 370
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Validate conditional election-to-issuer/publication consequences in complete ordinary and installed consumers; retain historical/regulation gaps',
                stop_condition='103admissions;1100measured+120other seconds/160MiB increment;29000s/4352MiB cumulative;380s consumers;no unchanged retry')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n)
        for n in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Source-bound conditional election capability with no negative home-state inference',
                    'Explicit retained-cumulative time extension for two real complete consumer checks'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN, 'reproduction': rel(PREP / 'reproduction.json')},
        'evidence_contract': {'primary': 'Independent source-bound decisions, actual downstream effects, complete prior preservation and installed equality',
            'promotion_veto': ['Wrong election or implication', 'Source/temporal drift', 'Changed prior answer', 'Wrong imports', 'Permissive corruption control'],
            'continuation_veto': ['Invalid authority', 'Corrupt common evidence', 'Exhausted cumulative limits'],
            'explanatory_only': ['Counts', 'Runtime'],
            'not_concluded': ['Actual home state', 'Historical law', 'Complete legal test', 'Whole task/build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 102, 'new_maximum': 103,
            'retained_attempts': attempts,
            'reason': 'Recovered operative text supports a distinct missing consumer capability; prior611seconds cannot reserve two380second consumers and checks',
            'next_discriminating_check': 'Election permission/publication/expiry changes the real issuer/publication answer without classifying failed routes negatively',
            'stop_condition': '1100+120seconds/160MiB increment;29000s/4352MiB cumulative;no unchanged retry',
            'same_scope_authorization': 'User requested continued internally checked general build; no external calls, opinions or branch actions',
            'previous_cumulative_seconds': 28000, 'new_cumulative_seconds': 29000,
            'all_prior_costs_retained': True, 'storage_limit_unchanged': True}}
    save(PREP / 'proposal.json', new); save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 370, 'resources': costs()}


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
        str(ROOT / 'scripts/prospectus_election_consumer_worker.py'), str(ROOT), str(PREP), str(HERE), mode]
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
        'remaining': ['Historical applicability/commencement', 'Detailed implementing regulations',
            'Actual issuer facts after build', 'Automatic/default/foreign home-state routes',
            'All original source/reference requirements and final build acceptance'],
        'outcomes': {s: outcome[s] for s in CHECKS}, 'external_opinion_required': False})
    return {'status': 'PASS', 'candidate_passed': all(outcome[s] == 'PASS' for s in CHECKS)}


def seal():
    outcome = states()['stages']; assert (HERE / 'RESULT.md').is_file()
    result = {'status': 'PASS' if all(outcome[s] == 'PASS' for s in CHECKS) else 'FAIL',
        'task': 'basf-references', 'original_task_complete': False, 'resources': costs(),
        'result_kind': 'CONDITIONAL_ELECTION_CONSUMER', 'checks': {s: outcome[s] for s in CHECKS},
        'next_action': 'Preserve finite conditional integration; continue distinct historical and implementing/source requirements'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p) for p in sorted((HERE / 'commands').glob('*.json'))],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;GPU intentionally hidden',
        'seeds': 'N/A deterministic finite checks', 'data_version': sha(PREP / 'source-bindings.json'),
        'plan': PLAN, 'result': rel(HERE / 'result.json'), 'resources': costs()})
    return result


def main():
    action = sys.argv[1]
    if action in ('development', 'prepare', 'proposal', 'status'):
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
