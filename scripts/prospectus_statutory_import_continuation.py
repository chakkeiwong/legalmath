"""Preserve failed024 and delegate frozen283 trials with child imports pinned."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['PYTHONPATH'] = os.pathsep.join((str(ROOT / 'src'), str(ROOT)))

from scripts import prospectus_statutory_integration as old
from legalmath.prospectus.execution_authority import Authority, CODE, digest

AUTH = old.AUTH
FAILED = old.HERE
ORIGINAL_PLAN = old.PLAN
PREP = AUTH / 'reviews/statutory-import-284'
HERE = AUTH / 'attempts/basf-references/attempt-025'
PLAN = 'docs/plans/prospectus-statutory-import-continuation-2026-10-18.md'
METHOD = 'scripts/prospectus_statutory_import_continuation.py'
read, save, sha, rel = old.read, old.save, old.sha, old.rel
PREPARATION = ('close-failed', 'probe', 'propose')


def costs(extra_seconds=0):
    start = read(old.PREP / 'accounting-start.json')
    folders = (old.PREP, FAILED, PREP, HERE)
    receipts = [p for d in folders for pattern in ('stages/*/result.json', 'stages/*/failure.json')
                for p in d.glob(pattern)]
    seconds = extra_seconds + sum(read(p)['wall_seconds'] for p in receipts)
    paths = {p for d in folders if d.exists() for p in d.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / p for p in (ORIGINAL_PLAN, old.METHOD, old.ORACLE, PLAN, METHOD))
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    paths.update(AUTH / f'revisions/{n:04d}.json' for n in (283, 284))
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    growth = sum(max(0, (ROOT / p).stat().st_size - before) for p, before in start['production_bytes'].items()
                 if (ROOT / p).exists())
    size += growth
    if seconds >= 3600 or size >= 188 * 1024**2:
        raise ValueError('Cumulative283/284 statutory integration resource bound exhausted')
    return {'additional_measured_seconds': seconds, 'additional_bytes': size, 'seconds_bound': 3600,
            'bytes_bound_including_reserve': 192 * 1024**2, 'reserve_bytes': 4 * 1024**2,
            'new_time_or_storage_allowance': 0, 'prior_admissions_retained': 24,
            'installed_production_growth_bytes': growth, 'retained_023_resources': start['prior_resources'],
            'historical_authoring_reading_controller_seconds': 'UNKNOWN'}


def close_failed():
    old.frozen()
    failure = read(FAILED / 'stages/tests/failure.json')
    tests = read(FAILED / 'checks/targeted-tests.json')
    assert failure['type'] == 'AssertionError' and tests['returncode'] == 2
    assert '/home/chakwong/python/legalmath/src/legalmath/prospectus/successor/__init__.py' in tests['stdout']
    installed = read(FAILED / 'stages/install/result.json')
    assert installed['status'] == 'PASS' and installed['exact_reviewed_files_installed'] == 4
    assert not list(FAILED.glob('*-answer.json.gz'))
    save(FAILED / 'result.json', {'status': 'PASS', 'task': 'basf-references',
         'result_kind': 'FAILED_TRIAL_RETENTION_AND_DIAGNOSIS', 'trial_status': 'FAIL',
         'failed_stage': 'tests', 'failure': failure, 'installation': installed,
         'new_ordinary_answers': 0, 'original_task_complete': False, 'resources': costs(),
         'next_action': 'Review explicit child import environment; resume unchanged source-to-answer matrix in a new admission'})
    save(FAILED / 'run-manifest.json', {'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
         'commands': [read(FAILED / 'stages' / s / 'started.json')['command'] for s in ('install', 'tests')],
         'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU intentionally hidden',
         'data_version': sha(old.PRIOR / 'investigation.json'), 'random_seeds': 'N/A deterministic',
         'wall_time': costs(), 'plan': old.PLAN, 'result': rel(FAILED / 'result.json'),
         'artifacts': rel(FAILED), 'method_freeze': sha(old.PREP / 'freeze.json')})
    with (FAILED / 'RESULT.md').open('x') as stream:
        stream.write('''# Failed statutory trial retained

The exact four reviewed files installed successfully. Tests failed during
collection because a fresh child interpreter imported the main worktree's
editable package. The parent sys.path pin was not inherited. No statutory
ordinary-answer stage ran. The production behavior has not yet been evaluated.
This is our test-launcher/environment defect, not a fundamental package problem.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain failed trial | Ordinary-answer matrix unrun | Harness validity failed | Installed behavior untested | Reviewed child-path continuation | Legal correctness or integration completion |

PASS in result.json describes failure retention only; trial_status is FAIL.
All original methods, installed candidates, source evidence and costs remain.
No unchanged retry or additional time/storage allowance is authorized.
''')
    old.frozen()
    save(FAILED / 'outputs.json', {str(p.relative_to(FAILED)): sha(p) for p in FAILED.rglob('*')
         if p.is_file() and '__pycache__' not in p.parts})
    return {'status': 'PASS', 'trial_status': 'FAIL', 'new_ordinary_answers': 0}


def probe():
    command = [sys.executable, '-B', '-c',
        'import importlib,json,sys; '
        'names=("legalmath","legalmath.prospectus.successor.service",'
        '"legalmath.prospectus.successor.basf_legacy_references",'
        '"legalmath.prospectus.successor.calendar_facts",'
        '"legalmath.prospectus.successor.statutory_references"); '
        'print(json.dumps({"modules":{n:importlib.import_module(n).__file__ for n in names},'
        '"python":sys.version,"executable":sys.executable}))']
    result = subprocess.run(command, cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True, timeout=30)
    save(PREP / 'import-probe.json', {'command': command, 'returncode': result.returncode,
         'stdout': result.stdout, 'stderr': result.stderr, 'PYTHONPATH': os.environ['PYTHONPATH'],
         'CUDA_VISIBLE_DEVICES': os.environ['CUDA_VISIBLE_DEVICES']})
    assert result.returncode == 0, result.stderr
    paths = json.loads(result.stdout)['modules']
    assert all(Path(p).is_relative_to(ROOT / 'src') for p in paths.values()), paths
    for row in read(old.PREP / 'installation.json')['files']:
        assert sha(ROOT / row['target']) == row['after_sha256']
    return {'status': 'PASS', 'role': 'IMPORT_PATH_DIAGNOSTIC_ONLY', 'resolved_modules': paths,
            'production_changed': False, 'tests_run': 0, 'ordinary_answers_run': 0}


def propose():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 283
    events = Authority(ROOT).events()
    assert next(e for e in reversed(events) if e.get('attempt') == rel(FAILED))['kind'] == 'RECORD'
    assert read(PREP / 'stages/probe/result.json')['status'] == 'PASS'
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 24
    bindings = {rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    bindings.update({name: sha(ROOT / name) for name in (*CODE, PLAN, METHOD)})
    bindings[rel(FAILED / 'outputs.json')] = sha(FAILED / 'outputs.json')
    save(PREP / 'freeze.json', {'bindings': bindings})
    proposal = deepcopy(program)
    proposal['revision'] = 284
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'PRE-ADMISSION-REVIEW.md'),
        reason='Repair reproduced child import mismatch; continue unchanged statutory ordinary-answer matrix without resetting resources',
        statutory_import_continuation={'review': rel(PREP), 'failed_attempt': rel(FAILED),
            'original_freeze': rel(old.PREP / 'freeze.json'), 'production_changes': False,
            'bounds': {'stage_seconds': 180, 'cumulative283_284_seconds': 3600, 'bytes': 192 * 1024**2}})
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 25
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 284
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(dossier=PLAN, task_sha256=digest(task),
                next_action='Verify installed files and child paths; run unchanged frozen statutory matrix; continue original definition/discovery remainder',
                stop_condition='25 cumulative admissions;180s stages;3600 cumulative283/284 seconds;192MiB including4MiB reserve;no unchanged retries')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        rel(PREP / 'routes.json'): sha(PREP / 'routes.json'), rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    review = {'baseline': digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Preserve failed024 and exact installed production', 'Pass worktree PYTHONPATH into test children',
                    'Delegate unchanged283 source, answer oracle and controls; no new time/storage allowance'],
        'skeptical_audit': {'verdict': 'PASS', 'review': rel(PREP / 'PRE-ADMISSION-REVIEW.md'),
                            'frozen_methods_unchanged': True, 'production_unchanged': True},
        'evidence_contract': {'primary': 'Unchanged283 independent whole-product/answer comparison and actual adverse refusals',
            'veto': ['Accepted forgery', 'Hidden uncertainty', 'Wrong source/edition', 'Unrelated answer drift', 'Frozen/resource invalidity'],
            'not_concluded': ['Historical applicability', 'Entitlement', 'Automatic discovery', 'Original task/build completion']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 24, 'new_maximum': 25,
            'retained_attempts': attempts, 'reason': 'Reproduced test-child import defect;024 installed exact candidate but ran no ordinary-answer matrix',
            'next_discriminating_check': 'Pinned child collection then unchanged ordinary-answer and resealed-refusal matrix',
            'stop_condition': '180s stages;3600 cumulative283/284 measured seconds;192MiB;no unchanged retry',
            'same_scope_authorization': 'User requests refreshed master and continued general build with internal supported-behavior proof'},
        'resources_before_admission': costs(), 'additional_time_or_storage_allowance': 0,
        'original_obligations_preserved': True}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 284, 'resources': costs()}


def frozen():
    old.frozen()
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum, name
    for name, checksum in read(FAILED / 'outputs.json').items():
        assert sha(FAILED / name) == checksum, name


def main():
    label = sys.argv[1]
    preparation = label in PREPARATION
    if not preparation:
        old.HERE, old.PLAN, old.costs = HERE, PLAN, costs
    from scripts import prospectus_statutory_integration_oracle as oracle
    assert label in PREPARATION or label in oracle.STAGES, 'Unknown continuation stage'
    folder = (PREP if preparation else HERE) / 'stages' / label
    assert not (folder / 'started.json').exists(), 'Unchanged stage retry refused'
    costs()
    if label == 'probe':
        assert read(PREP / 'stages/close-failed/result.json')['status'] == 'PASS'
    elif label == 'propose':
        assert read(PREP / 'stages/probe/result.json')['status'] == 'PASS'
    elif not preparation:
        for dependency in oracle.prerequisites(label):
            base = PREP if dependency == 'propose' else HERE
            assert read(base / 'stages' / dependency / 'result.json')['status'] == 'PASS', dependency
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_statutory_import_continuation', label],
        'started_at': datetime.now(timezone.utc).isoformat(), 'stage_seconds': 180})
    began = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Statutory continuation stage bound')))
    signal.alarm(180)
    try:
        if not preparation:
            frozen()
        if preparation:
            result = {'close-failed': close_failed, 'probe': probe, 'propose': propose}[label]()
        elif label == 'install':
            result = {'status': 'PASS', 'exact_existing_installation_verified': 4,
                'production_changed': False, 'prior_installation': rel(FAILED / 'stages/install/result.json'),
                'child_environment': {k: os.environ[k] for k in ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'CUDA_VISIBLE_DEVICES')}}
        elif label.startswith('build-'):
            result = old.build(label.removeprefix('build-'))
        elif label.startswith('consume-'):
            result = old.consume(label.removeprefix('consume-'))
        else:
            result = oracle.dispatch(label)
        if not preparation:
            frozen()
        costs(time.monotonic() - began)
        result['wall_seconds'] = time.monotonic() - began
        save(folder / 'result.json', result)
        if label == 'seal':
            save(HERE / 'continuation-provenance.json', {'failed_trial': rel(FAILED),
                'failed_trial_outputs_sha256': sha(FAILED / 'outputs.json'), 'original_freeze': sha(old.PREP / 'freeze.json'),
                'continuation_freeze': sha(PREP / 'freeze.json'), 'production_changed': False,
                'answer_oracle_or_controls_changed': False, 'resources_reset': False})
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
                if p.is_file() and '__pycache__' not in p.parts})
        print(json.dumps({k: v for k, v in result.items() if k != 'details'}))
    except BaseException as exc:
        save(folder / 'failure.json', {'type': type(exc).__name__, 'message': str(exc),
             'wall_seconds': time.monotonic() - began})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
