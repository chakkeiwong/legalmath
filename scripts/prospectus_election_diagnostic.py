"""One bounded stack/cost diagnostic; no product pass or unchanged retry."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
import time
from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, adigest, Authority

PREP = AUTH / 'reviews/election-diagnostic-371'
HERE = AUTH / 'attempts/basf-references/attempt-104'
PRIOR = AUTH / 'attempts/basf-references/attempt-103'
CONFIG = AUTH / 'reviews/election-consumer-370'
PLAN = 'docs/plans/prospectus-election-timeout-diagnostic-2026-10-20.md'
FILES = (PLAN, 'scripts/prospectus_election_diagnostic.py', 'scripts/prospectus_election_diagnostic_worker.py')


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    paths = [PREP / 'preparation-result.json', HERE / 'diagnostic-execution.json']
    measured = extra + sum(read(p).get('wall_seconds', 0) for p in paths if p.exists())
    files = {p for d in (PREP, HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update(ROOT / n for n in FILES); files.add(AUTH / 'revisions/0371.json')
    files.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in files if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    combined, total = start['prior_bytes'] + size, start['prior_seconds'] + measured + 120
    assert measured < 120 and size < 44 * 1024**2, 'Diagnostic increment exhausted'
    assert total < 29000 and combined < 4348 * 1024**2, 'Reference cumulative limit exhausted'
    return {'combined_accounted_seconds': total, 'combined_bytes': combined,
        'new_measured_seconds': measured, 'new_conservative_other_seconds': 120,
        'new_bytes': size, 'historical_manual_seconds': 'UNKNOWN', 'old_costs_reset': False}


def prepare():
    began = time.monotonic(); program = read(AUTH / 'program.json')
    assert program['revision'] == 370 and not HERE.exists()
    events = Authority(ROOT).events()
    assert any(e['kind'] in ('RECORD', 'REJECT') and e.get('attempt') == rel(PRIOR) for e in events)
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 103
    for name, checksum in read(PRIOR / 'outputs.json').items(): assert sha(PRIOR / name) == checksum, name
    failed = read(PRIOR / 'result.json'); assert failed['checks']['ordinary'] == 'FAIL'
    assert failed['checks']['tests'] == failed['checks']['package'] == 'PASS'
    from scripts.prospectus_election_consumer import costs as prior_costs
    previous = prior_costs()
    assert previous['combined_accounted_seconds'] + 240 < 29000
    assert previous['combined_bytes'] + 48 * 1024**2 < 4352 * 1024**2
    save(PREP / 'accounting-start.json', {'prior_seconds': previous['combined_accounted_seconds'],
        'prior_bytes': previous['combined_bytes'], 'prior_resources': previous,
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')]})
    save(PREP / 'preparation-result.json', {'status': 'PASS', 'wall_seconds': time.monotonic() - began,
        'failure': read(PRIOR / 'commands/ordinary.json')['failure'], 'last_complete_baseline': 'basf-office/attempt-006'})
    bindings = read(CONFIG / 'freeze.json')['bindings']
    for name, checksum in bindings.items(): assert sha(ROOT / name) == checksum, name
    bindings = {**bindings, **{n: sha(ROOT / n) for n in FILES}}
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file()})
    bindings.update({rel(PRIOR / n): sha(PRIOR / n) for n in
        ('outputs.json', 'result.json', 'commands/ordinary.json', 'RESULT.md', 'package.json')})
    save(PREP / 'freeze.json', {'bindings': bindings, 'production_change': False})
    new = deepcopy(program); new['revision'] = 371
    task = next(t for t in new['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN,
        reason='Locate actual prefix work after ordinary election consumer103 timed out; no unchanged acceptance retry',
        election_diagnostic={'review': rel(PREP), 'prior_attempt': rel(PRIOR),
            'maximum_diagnostics': 1, 'internal_seconds': 60, 'outer_seconds': 90,
            'new_measured_seconds': 120, 'new_other_seconds': 120, 'new_bytes': 48 * 1024**2,
            'cumulative_seconds': 29000, 'cumulative_bytes': 4352 * 1024**2}, build_criteria_scope=[])
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    new['budgets']['basf-references']['maximum_new_attempts'] = 104
    routes = read(ROOT / program['continuation_review']['routes']); routes['baseline_revision'] = 371
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                remaining='Election103 is unpromoted: ordinary380second timeout, installed blocked; tests/package passed; office006 remains complete baseline',
                next_action='Inspect one bounded actual stack/cost trace; return to named election integration repair only after supported diagnosis',
                stop_condition='104admissions;one60second diagnostic/90outer;120measured+120other seconds/48MiB new;29000s/4352MiB cumulative')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in
        (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['One instrumented diagnostic of actual failed consumer; no production or acceptance change'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN},
        'evidence_contract': {'primary': 'Real preserved stack and cost trace of frozen candidate with trustworthy identities',
            'promotion_veto': ['Missing trace/profile', 'Wrong imports', 'Untimed/unaccounted child'],
            'continuation_veto': ['Corrupt evidence', 'Invalid authority', 'Exhausted limits'],
            'explanatory_only': ['Runtime', 'Call counts', 'Sample frequency'],
            'not_concluded': ['Product pass', 'Package defect', 'Proved runtime cause', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 103, 'new_maximum': 104,
            'retained_attempts': attempts, 'reason': 'Reproduced380second failure needs bounded discriminating diagnosis',
            'next_discriminating_check': 'Sample actual executing frames and profile cost once under60seconds',
            'stop_condition': 'One60s/90outer diagnostic;120+120s/48MiB increment;unchanged29000s/4352MiB cumulative',
            'same_scope_authorization': 'Continue original integration with bounded failure diagnosis; no external calls or branch actions'}}
    save(PREP / 'proposal.json', new); save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 371, 'resources': costs()}


def frozen():
    admission = read(HERE / 'admission.json')
    assert adigest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items(): assert sha(ROOT / name) == checksum, name
    costs()


def run():
    frozen(); began = time.monotonic()
    save(HERE / 'diagnostic-started.json', {'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat(), 'maximum_children': 1})
    command = [str(ROOT / '.venv/bin/python'), '-B', str(ROOT / 'scripts/prospectus_election_diagnostic_worker.py'),
               str(ROOT), str(CONFIG), str(HERE)]
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(ROOT / 'src')}
    result = None; failure = None
    try:
        with (HERE / 'diagnostic.log').open('x') as output:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=90)
        assert result.returncode == 0, 'Inspect diagnostic.log'
    except Exception as error:
        failure = {'kind': type(error).__name__, 'error': str(error)}
    save(HERE / 'diagnostic-execution.json', {'command': command, 'outer_seconds': 90,
        'wall_seconds': time.monotonic() - began, 'exit_code': result.returncode if result else None,
        'failure': failure})
    frozen()
    return {'status': 'PASS' if failure is None else 'FAIL', 'resources': costs(), 'product_pass': False}


def seal():
    frozen(); assert (HERE / 'RESULT.md').is_file()
    execution = read(HERE / 'diagnostic-execution.json')
    result = {'status': 'PASS' if execution['failure'] is None else 'FAIL', 'task': 'basf-references',
        'result_kind': 'BOUNDED_RUNTIME_DIAGNOSTIC', 'original_task_complete': False,
        'product_pass': False, 'resources': costs(), 'next_action': 'Follow the retained diagnostic finding back to the original integration; no automatic retry'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'command': execution['command'], 'environment': str(ROOT / '.venv/bin/python'),
        'cpu_gpu': 'CPU;GPU intentionally hidden', 'seeds': 'N/A diagnostic', 'plan': PLAN,
        'data_version': sha(PREP / 'freeze.json'), 'result': rel(HERE / 'result.json'), 'resources': costs()})
    save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
        if p.is_file() and p.name not in ('admission.json', 'outputs.json')})
    return result


if __name__ == '__main__':
    action = sys.argv[1]; assert action in ('prepare', 'run', 'seal')
    print(json.dumps(globals()[action]()))
