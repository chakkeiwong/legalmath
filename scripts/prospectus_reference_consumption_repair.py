"""One retained repair and return to the complete election consumer."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import time

from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, adigest, Authority
from scripts import prospectus_office_composition as harness

PREP = AUTH / 'reviews/reference-consumption-repair-372'
HERE = AUTH / 'attempts/basf-references/attempt-105'
PRIOR = AUTH / 'attempts/basf-references/attempt-104'
FAILED = AUTH / 'attempts/basf-references/attempt-103'
CONFIG = AUTH / 'reviews/election-consumer-370'
PLAN = 'docs/plans/prospectus-reference-consumption-repair-2026-10-20.md'
FAMILIES = ('call', 'payment', 'legacy', 'governance', 'default', 'substitution', 'financial', 'internal')
MODULES = ['reviewed_references', 'service'] + ['basf_' + n + '_references' for n in FAMILIES]
METHODS = ['src/legalmath/prospectus/successor/' + n + '.py' for n in MODULES]
FILES = [PLAN, 'scripts/prospectus_reference_consumption_repair.py',
         'scripts/prospectus_reference_consumption_compare.py',
         'scripts/prospectus_election_consumer_worker.py',
         'scripts/prospectus_office_composition.py', 'scripts/prospectus_default_holder.py'] + METHODS
TESTS = ['tests/prospectus_successor/' + n for n in (
    'test_reference_consumption.py', 'test_occurrence_lookup.py', 'test_consumed_reference_closure.py',
    'test_reference_consumer_integrity.py', 'test_structural_context.py', 'test_election.py',
    'test_issuer_qualification.py', 'test_office_change.py', 'test_publication_routes.py',
    'test_conditional_profiles_cli.py', 'test_acquisition_receipt_integrity.py')]
TESTS += ['tests/prospectus_successor/test_basf_' + n + '_references.py'
          for n in FAMILIES if n != 'legacy']
DEPS = {'tests': (), 'compare': (), 'package': (), 'ordinary': ('tests', 'compare'),
        'installed': ('ordinary', 'package'), 'reconcile': (), 'seal': ('reconcile',)}
CHECKS = ('tests', 'compare', 'package', 'ordinary', 'installed')
LIMITS = {'tests': 120, 'compare': 90, 'package': 240, 'ordinary': 380,
          'installed': 380, 'reconcile': 5, 'seal': 10}
harness.PREP, harness.HERE, harness.TESTS = PREP, HERE, TESTS


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    receipts = list(PREP.glob('*-execution.json')) + list(HERE.glob('stages/*/result.json'))
    receipts += list(HERE.glob('stages/*/failure.json'))
    measured = extra + sum(read(p).get('wall_seconds', 0) for p in receipts)
    files = {p for d in (PREP, HERE) for p in d.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    files.update(ROOT / n for n in FILES + TESTS)
    files.add(AUTH / 'revisions/0372.json')
    files.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in files if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    total, combined = start['prior_seconds'] + measured + 180, start['prior_bytes'] + size
    assert measured < 1550 and size < 188 * 1024**2, 'Repair increment exhausted'
    assert total < 31000 and combined < 4540 * 1024**2, 'Cumulative reference limit exhausted'
    return {'combined_accounted_seconds': total, 'combined_bytes': combined,
            'new_measured_seconds': measured, 'new_conservative_other_seconds': 180,
            'new_bytes': size, 'historical_manual_seconds': 'UNKNOWN', 'old_costs_reset': False}


def bootstrap():
    began = time.monotonic()
    program = read(AUTH / 'program.json'); assert program['revision'] == 371 and not PREP.exists()
    events = Authority(ROOT).events()
    assert any(e['kind'] in ('RECORD', 'REJECT') and e.get('attempt') == rel(PRIOR) for e in events)
    for folder in (PRIOR, FAILED):
        for name, checksum in read(folder / 'outputs.json').items():
            assert sha(folder / name) == checksum, name
    from scripts.prospectus_election_diagnostic import costs as prior_costs
    previous = prior_costs()
    assert previous['combined_accounted_seconds'] + 1730 < 31000
    assert previous['combined_bytes'] + 192 * 1024**2 < 4544 * 1024**2
    save(PREP / 'accounting-start.json', {'prior_seconds': previous['combined_accounted_seconds'],
        'prior_bytes': previous['combined_bytes'], 'prior_resources': previous,
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')]})
    frozen = read(CONFIG / 'freeze.json')['production']
    for name in METHODS:
        assert sha(ROOT / name) == frozen[name], name
        target = PREP / 'before' / Path(name).name
        target.parent.mkdir(exist_ok=True); shutil.copyfile(ROOT / name, target)
    save(PREP / 'before.json', {name: frozen[name] for name in METHODS})
    save(PREP / 'bootstrap-execution.json', {'status': 'PASS', 'wall_seconds': time.monotonic() - began,
        'review': PLAN, 'baseline': 'Frozen103 reference methods; office006 complete answer'})
    return {'status': 'PASS', 'resources': costs()}


def development():
    existing = list(PREP.glob('development-*-execution.json'))
    maximum = 3 if (PREP / 'DEVELOPMENT-REVIEW.md').is_file() else 2
    assert len(existing) < maximum
    name = 'development-' + str(len(existing) + 1)
    costs(120); began = time.monotonic()
    import subprocess
    command = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'pytest', '-q',
               'tests/prospectus_successor/test_reference_consumption.py']
    env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'CUDA_VISIBLE_DEVICES': '-1',
           'PYTHONDONTWRITEBYTECODE': '1'}
    failure = None; result = None
    try:
        with (PREP / (name + '.log')).open('x') as stream:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=120)
        assert result.returncode == 0, 'Inspect ' + name + '.log'
    except Exception as error:
        failure = {'kind': type(error).__name__, 'error': str(error)}
    save(PREP / (name + '-execution.json'), {'command': command, 'failure': failure,
        'exit_code': result.returncode if result else None, 'wall_seconds': time.monotonic() - began})
    return {'status': 'PASS' if failure is None else 'FAIL', 'resources': costs()}


def repair_fixture():
    """The one allowed development repair: retain adjacent frozen resources."""
    began = time.monotonic()
    assert read(PREP / 'development-1-execution.json')['failure'] is not None
    assert not (PREP / 'before-resources.json').exists()
    frozen = read(CONFIG / 'freeze.json')['production']; bindings = {}
    for name in FAMILIES:
        path = 'src/legalmath/prospectus/successor/basf_' + name + '_references_spec.json'
        assert sha(ROOT / path) == frozen[path], path
        shutil.copyfile(ROOT / path, PREP / 'before' / Path(path).name)
        bindings[path] = frozen[path]
    save(PREP / 'before-resources.json', bindings)
    save(PREP / 'fixture-repair-execution.json', {'status': 'PASS', 'wall_seconds': time.monotonic() - began,
        'cause': 'Frozen family modules load adjacent specifications; bootstrap copied only Python methods',
        'correction': 'Copy unchanged103 specification bytes beside frozen methods and validate hashes; retain complete grouped selections in reduced fixture',
        'production_change_for_fixture_repair': False, 'earlier_failure_retained': True})
    return {'status': 'PASS', 'resources': costs()}


def proposal():
    began = time.monotonic()
    development = sorted(PREP.glob('development-*-execution.json'))
    assert development and read(development[-1])['failure'] is None
    program = read(AUTH / 'program.json'); assert program['revision'] == 371 and not HERE.exists()
    attempts = [e['attempt'] for e in Authority(ROOT).events()
                if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 104
    # Inputs and election semantics are unchanged. Preserve the failed run.
    prior = read(CONFIG / 'freeze.json'); allowed = set(METHODS)
    for name, checksum in prior['bindings'].items():
        if name not in allowed: assert sha(ROOT / name) == checksum, name
    save(PREP / 'config.json', read(CONFIG / 'config.json'))
    for name in ('profile.json', 'expected.json'):
        shutil.copyfile(CONFIG / name, PREP / name)
    production = {rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
    bindings = {n: sha(ROOT / n) for n in FILES + TESTS}
    bindings.update(prior['bindings']); bindings.update(production)
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file()})
    bindings.update({rel(PRIOR / n): sha(PRIOR / n) for n in ('outputs.json', 'RESULT.md', 'result.json', 'profile-summary.json')})
    save(PREP / 'freeze.json', {'bindings': bindings, 'production': production})
    new = deepcopy(program); new['revision'] = 372
    task = next(t for t in new['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN, timeout_seconds=380,
        reason='Repair repeated source admission found in104; return to complete election ordinary/installed validation',
        reference_consumption_repair={'review': rel(PREP), 'prior_failure': rel(FAILED), 'diagnostic': rel(PRIOR),
            'new_measured_seconds': 1550, 'new_other_seconds': 180, 'new_bytes': 192 * 1024**2,
            'cumulative_seconds': 31000, 'cumulative_bytes': 4544 * 1024**2}, build_criteria_scope=[])
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    new['budgets']['basf-references']['maximum_new_attempts'] = 105
    routes = read(ROOT / program['continuation_review']['routes']); routes['baseline_revision'] = 372
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Validate fresh shared reference admission against frozen methods, then complete original election CLI trials',
                stop_condition='105 admissions;1550 measured+180 other seconds/192MiB new;31000s/4544MiB cumulative;one formal attempt per stage')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n)
        for n in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['One fresh complete reference admission shared inside a synchronous consumer call',
                    'Preserve standalone family checks and complete dependency reconstruction',
                    'Retain failure104 and103, explicitly extend cumulative local reservation without reset'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN},
        'evidence_contract': {'primary': 'Frozen report/refusal equivalence and complete ordinary/installed election answer validation',
            'promotion_veto': ['Answer or refusal mismatch', 'Changed baseline', 'Wrong imports', 'Missing or changed evidence'],
            'continuation_veto': ['Invalid authority', 'Corrupt common evidence', 'Exhausted bounds'],
            'explanatory_only': ['Runtime', 'Call counts', 'Test counts'],
            'not_concluded': ['Whole timeout cause', 'Package defect', 'Historical law', 'Actual issuer state', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 104, 'new_maximum': 105,
            'retained_attempts': attempts, 'reason': 'Observed repeated admission is a concrete bounded repair; old remaining908s/125MiB cannot reserve all required trials',
            'next_discriminating_check': 'Exact frozen reference comparison then ordinary and isolated installed election CLI',
            'stop_condition': '1550+180s/192MiB new;31000s/4544MiB cumulative;one formal command per stage',
            'same_scope_authorization': 'Continue authorized local general build; no external calls or branch actions',
            'previous_cumulative_seconds': 29000, 'new_cumulative_seconds': 31000,
            'previous_cumulative_bytes': 4352 * 1024**2, 'new_cumulative_bytes': 4544 * 1024**2,
            'all_prior_costs_retained': True}}
    save(PREP / 'proposal.json', new); save(PREP / 'review.json', review)
    save(PREP / 'proposal-execution.json', {'wall_seconds': time.monotonic() - began, 'status': 'PASS'})
    return {'status': 'PASS', 'revision': 372, 'resources': costs()}


def frozen():
    admission = read(HERE / 'admission.json')
    assert adigest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum, name


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


def tests(): return harness.tests()
def package(): return harness.package()


def compare():
    harness.execute('compare', [str(ROOT / '.venv/bin/python'), '-B',
        str(ROOT / 'scripts/prospectus_reference_consumption_compare.py'), str(ROOT), str(PREP), str(HERE)], 90)
    return {'status': 'PASS', **read(HERE / 'comparison.json')}


def worker(mode):
    python = read(HERE / 'package.json')['python'] if mode == 'installed' else str(ROOT / '.venv/bin/python')
    command = [python, *(['-I'] if mode == 'installed' else []), '-B',
        str(ROOT / 'scripts/prospectus_election_consumer_worker.py'), str(ROOT), str(PREP), str(HERE), mode]
    harness.execute(mode, command, 380, HERE if mode == 'installed' else ROOT)
    return {'status': 'PASS', **read(HERE / (mode + '-verification.json'))}


def reconcile():
    save(HERE / 'original-requirements.json', {'original_task_complete': False,
        'remaining': read(FAILED / 'original-requirements.json')['remaining'],
        'outcomes': {s: states()['stages'][s] for s in CHECKS}, 'external_opinion_required': False})
    return {'status': 'PASS', 'candidate_passed': all(states()['stages'][s] == 'PASS' for s in CHECKS)}


def seal():
    outcome = states()['stages']; assert (HERE / 'RESULT.md').is_file()
    result = {'status': 'PASS' if all(outcome[s] == 'PASS' for s in CHECKS) else 'FAIL',
        'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'REFERENCE_CONSUMPTION_REPAIR_AND_ELECTION',
        'checks': {s: outcome[s] for s in CHECKS}, 'resources': costs(),
        'next_action': 'Continue original substantive requirements from actual results; no automatic retry'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p) for p in sorted((HERE / 'commands').glob('*.json'))],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;GPU intentionally hidden',
        'data_version': sha(PREP / 'freeze.json'), 'seeds': 'N/A deterministic checks',
        'plan': PLAN, 'result': rel(HERE / 'result.json'), 'resources': costs()})
    return result


def main():
    action = sys.argv[1]
    if action in ('bootstrap', 'repair_fixture', 'development', 'proposal', 'status'):
        return states() if action == 'status' else globals()[action]()
    assert action in states()['ready'], 'Stage not ready; inspect retained worker/result'
    frozen(); costs(LIMITS[action]); began = time.monotonic()
    folder = HERE / 'stages' / action
    save(folder / 'started.json', {'command': sys.argv, 'pid': os.getpid(),
        'started_at': datetime.now(timezone.utc).isoformat()})
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
