"""Bounded changed recovery of source-authority010; sealed evidence is read-only."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from scripts import prospectus_shell_source_chain as prior
from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, adigest, Authority

PLAN = 'docs/plans/prospectus-shell-source-chain-repair-2026-10-21.md'
PREP = AUTH / 'reviews/shell-source-chain-repair-381'
HERE = AUTH / 'attempts/source-authority/attempt-011'
OLD_PREP = prior.PREP
OLD_ATTEMPT = prior.HERE
SELF = rel(Path(__file__))
TEST = 'tests/prospectus_successor/test_shell_source_chain_consumer.py'
TESTS = [*prior.TESTS, TEST]
FILES = [*prior.FILES, PLAN, SELF, TEST]


def production():
    return {str(p.relative_to(ROOT / 'src/legalmath')): sha(p)
            for p in (ROOT / 'src/legalmath').rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}


def recover():
    assert read(AUTH / 'program.json')['revision'] == 380 and not PREP.exists()
    resources = prior.costs()
    events = Authority(ROOT).events()
    records = [e for e in events if e.get('attempt') == rel(OLD_ATTEMPT) and 'outputs_sha256' in e]
    assert records and sha(OLD_ATTEMPT / 'outputs.json') == records[-1]['outputs_sha256']
    for name, checksum in read(OLD_ATTEMPT / 'outputs.json').items():
        assert sha(OLD_ATTEMPT / name) == checksum, name
    assert read(OLD_ATTEMPT / 'result.json')['status'] == 'FAIL'
    service = ROOT / 'src/legalmath/prospectus/successor/service.py'
    assert sha(service) == read(OLD_PREP / 'freeze.json')['bindings'][rel(service)]
    save(PREP / 'accounting-start.json', {
        'prior_seconds': resources['known006plus_accounted_seconds'],
        'prior_bytes': resources['known006plus_bytes'], 'prior_resources': resources,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'started_at': datetime.now(timezone.utc).isoformat(), 'earlier_and_manual_costs': 'UNKNOWN'})
    (PREP / 'baseline').mkdir()
    shutil.copyfile(service, PREP / 'baseline/service.py')
    save(PREP / 'baseline/production.json', production())
    for name in ('source-spec.json', 'source-bindings.json', 'input-bindings.json',
                 'cases.json', 'config.json', 'SOURCE-REVIEW.md'):
        shutil.copyfile(OLD_PREP / name, PREP / name)
    bindings = {rel(OLD_PREP / n): sha(OLD_PREP / n) for n in (
        'freeze.json', 'source-spec.json', 'input-bindings.json', 'cases.json', 'SOURCE-REVIEW.md')}
    bindings.update({rel(OLD_ATTEMPT / n): sha(OLD_ATTEMPT / n) for n in (
        'outputs.json', 'result.json', 'commands/tests.log', 'commands/tests.json',
        'commands/ordinary.log', 'commands/ordinary.json', 'RESULT.md')})
    save(PREP / 'failure-bindings.json', bindings)
    save(PREP / 'recovery.json', {'status': 'FAILURE_AUTHENTICATED', 'failed_attempt': rel(OLD_ATTEMPT),
        'mechanism': 'Verification assigned in interpretation_product; undefined in actual consume',
        'classification': 'OUR_CONSUMER_WIRING_AND_PREFLIGHT_COVERAGE',
        'source_reading_changed': False, 'whole_task_complete': False})
    return {'status': 'PASS', 'baseline': rel(PREP / 'baseline/service.py'), 'resources': costs()}


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    records = list(PREP.glob('commands/*.json')) + list(HERE.glob('commands/*.json'))
    measured = extra + sum(read(p)['wall_seconds'] for p in records)
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in FILES + TESTS)
    paths.add(AUTH / 'revisions/0381.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    total, combined = start['prior_seconds'] + measured + 60, start['prior_bytes'] + size
    assert measured < 220 and total < 1900, 'Recovery cumulative time exhausted'
    assert size < 124 * 1024**2 and combined < 380 * 1024**2, 'Recovery cumulative storage exhausted'
    return {'new_measured_seconds': measured, 'new_conservative_other_seconds': 60, 'new_bytes': size,
            'known006plus_accounted_seconds': total, 'known006plus_bytes': combined,
            'earlier_and_manual_costs': 'UNKNOWN', 'old_costs_reset': False, 'seal_reserve_bytes': 4 * 1024**2}


def development():
    prior.command('development-consumer', [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q',
        *TESTS, '--junitxml=' + str(PREP / 'development-consumer.xml')], folder=PREP, timeout=60)
    return {'status': 'PASS', 'resources': costs()}


def prepare():
    old = read(AUTH / 'program.json')
    assert old['revision'] == 380 and not HERE.exists()
    assert read(PREP / 'commands/development-consumer.json')['exit_code'] == 0
    from legalmath.prospectus.execution_acceptance import checked_tests
    checked_tests(PREP / 'development-consumer.xml', 1)
    original = read(PREP / 'baseline/production.json')
    current = production()
    assert original.keys() == current.keys()
    assert {n for n in current if original[n] != current[n]} == {'prospectus/successor/service.py'}
    inputs = {**read(PREP / 'input-bindings.json'), **read(PREP / 'failure-bindings.json')}
    for name, checksum in inputs.items():
        assert sha(ROOT / name) == checksum, name
    bindings = {n: sha(ROOT / n) for n in FILES + TESTS + ['pyproject.toml', 'scripts/prospectus_default_holder.py']}
    bindings.update({'src/legalmath/' + n: checksum for n, checksum in current.items()})
    bindings.update(inputs)
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    save(PREP / 'freeze.json', {'bindings': bindings, 'production': current,
        'skeptical_audit': 'PASS: actual-consumer preflight, complete legacy baseline, preserved failed010 and source review'})
    attempts = [e['attempt'] for e in Authority(ROOT).events()
                if e['kind'] == 'ADMIT' and e['budget_key'] == 'source-authority']
    assert len(attempts) == old['budgets']['source-authority']['maximum_new_attempts'] == 10
    new = deepcopy(old)
    new['revision'] = 381
    task = next(t for t in new['tasks'] if t['id'] == 'source-authority')
    task.update(dossier=PLAN, pre_admission_review=PLAN, build_criteria_scope=[],
        reason='Repair authenticated010 consumer wiring failure with actual-consumer preflight and a new frozen candidate')
    bounds = {'new_measured_seconds': 220, 'conservative_control_seconds': 60,
        'known006plus_seconds': 1900, 'new_bytes': 128 * 1024**2,
        'known006plus_bytes': 384 * 1024**2, 'seal_reserve_bytes': 4 * 1024**2}
    task['shell_source_chain_repair'] = {'failed_attempt': rel(OLD_ATTEMPT),
        'review': rel(PREP), 'freeze': rel(PREP / 'freeze.json'), 'bounds': bounds,
        'retained_admissions': attempts, 'whole_task_complete': False, 'automatic_retry': False,
        'stage_dependencies': prior.DEPS, 'completion_dependencies': {'reconcile': list(prior.CHECKS)}}
    task['inputs'] = sorted(set(task['inputs']) | set(bindings) | {rel(PREP / 'freeze.json')})
    new['budgets']['source-authority']['maximum_new_attempts'] = 11
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 381
    row = next(r for r in routes['tasks'] if r['task'] == 'source-authority')
    row.update(task_sha256=adigest(task), dossier=PLAN,
        remaining='010 failed in actual consume due to our misplaced verifier; original source applicability remains unresolved.',
        next_action='Execute changed011 recovery once, record/refresh and continue original-source frontier; preserve010 and finance013.',
        stop_condition='11 admissions;220+60s/128MiB new;known006+1900s/384MiB;no unchanged retry')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in (
        PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    assert old['obligations'] == new['obligations'] and old['build_contract'] == new['build_contract']
    forecast = costs()['new_bytes'] + 2 * len(json.dumps(new, indent=2, ensure_ascii=False).encode()) + 80 * 1024**2
    assert forecast < 124 * 1024**2
    assert read(PREP / 'accounting-start.json')['prior_bytes'] + forecast < 380 * 1024**2
    save(PREP / 'proposal.json', new)
    save(PREP / 'review.json', {'baseline': adigest(old), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Move source-chain verification to the actual consumer',
                    'Add actual consumer success/forgery/absence regression before freeze',
                    'Preserve source010 failure, source readings, finance013 and all cumulative costs'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN,
            'development_result': rel(PREP / 'commands/development-consumer.json'), 'forecast_new_bytes': forecast},
        'evidence_contract': {'question': 'Does the repaired final consumer preserve legacy answers and reject forged source-chain reports?',
            'baseline': 'Failing010 service/logs and complete finance013 original-case answers/P5',
            'primary': 'Actual full consumer equality/refusals, qualified source report and isolated installed equality',
            'promotion_veto': ['Missing case/qualifier', 'Changed financial answer', 'Accepted forgery', 'Wrong import origin'],
            'continuation_veto': ['Corrupt common originals', 'Invalid authority', '1900s/384MiB known006+ exhausted'],
            'explanatory_only': ['Counts', 'Runtime', 'Storage'],
            'not_concluded': ['Authenticity', 'Actual succession', 'Operative source roles', 'Whole task/build']},
        'budget_revision': {'budget_key': 'source-authority', 'previous_maximum': 10, 'new_maximum': 11,
            'retained_attempts': attempts, 'reason': 'Diagnosed changed repair of our source010 consumer wiring and preflight gap',
            'next_discriminating_check': 'New frozen actual consumer and installed consumer with rehashed adversarial products',
            'stop_condition': bounds, 'same_scope_authorization': 'User recover and continue; authorized bounded repairs'}})
    return {'status': 'PASS', 'revision': 381, 'resources': costs()}


def verify():
    prior.command('verify', [str(ROOT / '.venv/bin/python'), '-B', '-m',
        'scripts.prospectus_shell_source_chain_repair', 'verify-evidence'], folder=HERE, timeout=60)
    return read(HERE / 'verification.json')


def reconcile():
    outcomes = {n: prior.status()['stages'][n] for n in prior.CHECKS}
    passed = all(v == 'PASS' for v in outcomes.values())
    save(HERE / 'original-requirements.json', {'candidate_passed': passed, 'checks': outcomes,
        'original_task_complete': False, 'original_obligations': ['G01', 'G20'],
        'failure_retained': rel(OLD_ATTEMPT), 'attribution': 'OUR_CONSUMER_WIRING_AND_PREFLIGHT_COVERAGE',
        'remaining': ['Original authenticity/publication and historical availability',
            'Executed agreement/amendment/succession evidence', 'Complete source construction'],
        'external_adviser_opinion_required': False})
    text = f'''# Source-chain consumer repair

The changed candidate {'passed' if passed else 'failed'}: {outcomes}.
Source-authority010 remains a failed immutable attempt. Its verifier was assigned
in interpretation_product but consumed from another function. Verification now
runs in the actual final consumer; preflight also exercises this boundary.
This establishes our integration/test-coverage defect, not a package defect.
Source-authority001–010 and finance013 remain unchanged.

The source reading still distinguishes the printed memorandum reference from
authenticity, specific agreement precedence from universal priority, and dated
trustee descriptions from proof of succession. Missing executed agreements,
UNKNOWN assembly roles and hypothetical financial premises remain explicit.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| {'Retain repaired integration' if passed else 'Retain changed candidate failure'} | Complete answers/refusals, source qualifications and installed equality: {passed} | Retained stage records | Source applicability and missing executed agreements | Record/refresh and continue original-source frontier | Whole task/build, authenticity or actual succession |

Post-run red-team: source-byte equality and three scenarios do not establish
general legal completeness. A lost qualifier, accepted forgery, changed legacy
answer or conflicting original would invalidate the corresponding conclusion.
The report is a named source interpretation, with no stochastic ranking or new
automatic default. Whole-task and whole-program completion remain false.
'''
    with (HERE / 'RESULT.md').open('x') as stream:
        stream.write(text)
    return {'status': 'PASS', 'candidate_passed': passed}


def configure():
    prior.HERE, prior.PREP, prior.PLAN = HERE, PREP, PLAN
    prior.FILES, prior.TESTS = FILES, TESTS
    prior.costs, prior.verify, prior.reconcile = costs, verify, reconcile


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'recover':
        output = recover()
    elif action == 'development':
        output = development()
    elif action == 'prepare':
        output = prepare()
    elif action == 'verify-evidence':
        from scripts import prospectus_shell_source_chain_verify as verifier
        verifier.PREP = PREP
        output = verifier.verify(HERE)
        save(HERE / 'verification.json', output)
    else:
        configure()
        if action == 'status':
            output = prior.status()
        elif action in prior.DEPS:
            output = prior.stage(action)
        else:
            raise SystemExit('Unsupported action ' + action)
    print(json.dumps(output))
