"""Reviewed finite reasoning acceptance; the authority remains the selector."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
from legalmath.prospectus.execution_authority import Authority, REL, read, write, digest, file_hash
from legalmath.prospectus.build_contract import BUILD_FIRST_DEFERRED
from scripts.prospectus_component_revalidation import package_files, runtime, runtime_files
from scripts.prospectus_reasoning_acceptance_evidence import evaluate, verify, same, same_records, require

PLAN = 'docs/plans/prospectus-build-acceptance-2026-10-18.md'
SCRIPT = 'scripts/prospectus_reasoning_acceptance.py'
WORKER = 'scripts/prospectus_reasoning_acceptance_worker.py'
EVIDENCE = 'scripts/prospectus_reasoning_acceptance_evidence.py'
TEST = 'tests/prospectus/test_reasoning_acceptance.py'
REVIEW = REL + '/reviews/build-acceptance-261'
PROPOSAL = REL + '/proposals/build-acceptance-261.json'
ROUTES = REL + '/closure-routes-2026-10-18-build-acceptance-261.json'
RECONCILIATION = REVIEW + '/requirements.json'
ATTEMPT = REL + '/attempts/reasoning-corpus/attempt-010'
STAGES = ('build', 'install', 'source', 'installed', 'verify', 'seal')
BOUNDS = {'stage_seconds': 110, 'incremental_seconds': 720, 'new_bytes': 128 * 1024**2,
          'reserve_bytes': 2 * 1024**2, 'preparation_seconds': 90}
SUPPORT = (PLAN, SCRIPT, WORKER, EVIDENCE, TEST)


def now():
    return datetime.now(timezone.utc).isoformat()


def methods(task):
    names = {n for n in task['inputs'] if n.endswith('.py') and (ROOT / n).is_file()}
    names |= {str(p.relative_to(ROOT)) for p in (ROOT / 'src/legalmath').rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    names.update(SUPPORT)
    names.add('pyproject.toml')
    return {n: file_hash(ROOT / n) for n in sorted(names)}


def history(auth):
    retained = []
    for number in (7, 8, 9):
        name = REL + '/attempts/reasoning-corpus/attempt-' + f'{number:03d}'
        event = next(e for e in reversed(auth.events()) if e.get('attempt') == name and e['kind'] in {'RECORD', 'ACCEPT'})
        require(auth.retained_evidence_valid(event), 'Corrupt original reasoning evidence')
        retained.append({'attempt': name, 'event_sha256': event['sha256'], 'outputs_sha256': event['outputs_sha256']})
    return retained


def reconciliation(program, state, routes):
    mapping = {r['task']: r for r in routes['tasks']}
    states = {r['id']: r for r in state['tasks']}
    rows = []
    for obligation in program['obligations']:
        current = [t for t in obligation['tasks'] if t not in BUILD_FIRST_DEFERRED]
        deferred = {t: BUILD_FIRST_DEFERRED[t] for t in obligation['tasks'] if t in BUILD_FIRST_DEFERRED}
        origin = obligation['origin']
        record = None
        if origin['path'].endswith('.json'):
            record = read(ROOT / origin['path'])
            for part in origin['locator'].strip('/').split('/'):
                record = record[int(part)] if isinstance(record, list) else record[part]
            require(digest(record) == origin['record_sha256'], 'Original requirement record changed')
        rows.append({'id': obligation['id'], 'origin': origin, 'original_record': record,
            'original_scope': obligation['scope'], 'current_tasks': current, 'deferred_tasks': deferred,
            'disposition': 'BUILD_AND_DEFERRED' if current and deferred else 'BUILD' if current else 'DEFERRED',
            'accepted_by_reconciliation': False})
    task_rows = []
    for task in program['tasks']:
        route = mapping[task['id']]
        task_rows.append({'id': task['id'], 'original_obligations': task['obligations'],
            'dossier': task['dossier'], 'state': states[task['id']]['state'],
            'last_attempt': states[task['id']].get('attempt'), 'acceptance': task['acceptance'],
            'acceptance_implementation': task.get('validator') or
                (task['handler'] if task['handler'] in {'native-cohort', 'native-interfaces'} else None),
            'proposed_acceptance_implementation': 'conditional-reasoning-current.v1' if task['id'] == 'reasoning-corpus' else None,
            'build_disposition': BUILD_FIRST_DEFERRED.get(task['id'], 'REQUIRED'),
            'remaining': route['remaining'], 'next_action': route['next_action'],
            'acceptance_check': route['acceptance'], 'external_inputs': route['external_inputs'],
            'budget_key': task['budget_key'],
            'admissions_used': state['budget_admissions'][task['budget_key']],
            'admission_limit': program['budgets'][task['budget_key']]['maximum_new_attempts']})
    return {'version': 'prospectus-requirements-reconciliation.v1', 'baseline_revision': program['revision'],
            'baseline_sha256': digest(program), 'event_head': state['event_head'],
            'user_direction': program['build_contract']['authorization'], 'obligations': rows, 'tasks': task_rows,
            'acceptance_granted': False, 'original_inventory_preserved': True}


def prepare():
    tick = time.monotonic()
    folder = ROOT / REVIEW
    folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'started.json', {'at': now(), 'command': ['.venv/bin/python', '-m',
        'scripts.prospectus_reasoning_acceptance', 'prepare']}, exclusive=True)
    try:
        auth = Authority(ROOT); old, tasks, _ = auth.spec(); state = auth.status()
        require(old['revision'] == 260 and not state['running'], 'Wrong active build baseline')
        task = tasks['reasoning-corpus']
        retained = history(auth)
        argv = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                TEST, 'tests/prospectus/test_build_contract.py', 'tests/prospectus/test_execution_authority.py',
                '--junitxml=' + str(folder / 'tests.xml')]
        with (folder / 'tests.log').open('xb') as out:
            completed = subprocess.run(argv, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT,
                env={**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'PYTHONDONTWRITEBYTECODE': '1'}, timeout=60)
        require(completed.returncode == 0, 'Preparation tests failed; retain tests.log')
        from legalmath.prospectus.execution_acceptance import checked_tests
        tests = checked_tests(folder / 'tests.xml', 10)
        routes = read(ROOT / old['continuation_review']['routes'])
        for row in routes['tasks']:
            key = row['task']
            row['before_build_acceptance_261'] = {k: row[k] for k in
                ('mode', 'phase', 'remaining', 'next_action', 'acceptance', 'external_inputs', 'stop_condition')}
            if key in BUILD_FIRST_DEFERRED:
                row.update(mode='external', phase=6,
                    next_action='Deferred under retained user direction: ' + BUILD_FIRST_DEFERRED[key],
                    external_inputs=['User-directed later scope: ' + BUILD_FIRST_DEFERRED[key]])
            elif key in {'actus-prerequisites', 'actus-comparison'}:
                row.update(mode='mixed' if key == 'actus-prerequisites' else 'evidence', phase=5,
                    next_action='Retain local plain-PAM preparation; require authorized pinned core/source/tests/terms before the actual trial.',
                    external_inputs=['Authorized ACTUS core 1.1.0, source/tests and applicable terms; no package-defect inference from absence.'])
            else:
                phase = (4 if tasks[key]['stream'] == 'engineering' else
                         3 if key in {'finance-conventions', 'entitlement'} else 2 if tasks[key]['stream'] == 'automatic' else 1)
                row.update(mode='local', external_inputs=[], phase=phase,
                    next_action='Reconcile original source requirements and actual consumer evidence in ' + tasks[key]['dossier'] +
                    '; implement/review a named acceptance check before another partial campaign. Preserve unknown facts and source gaps.',
                    acceptance='Original task requirements, source/consumer evidence and adverse controls within the declared domain; '
                    'independent derivations verify conditional consequences, and disputed meanings remain explicit. No external-opinion prerequisite.')
        next(r for r in routes['tasks'] if r['task'] == 'reasoning-corpus').update(phase=0,
            next_action='Execute frozen current-source and installed reasoning acceptance, record actual verdict, refresh, then source-coverage work.',
            acceptance='Current 404-case solver corpus, complete source-bound minimal explanations,118 full answers, original controls, independent checks and exact installed provenance.',
            stop_condition=json.dumps(BOUNDS, sort_keys=True))
        write(ROOT / RECONCILIATION, reconciliation(old, state, routes), exclusive=True)
        inputs = set(task['inputs'])
        for item in retained:
            inputs.update(item['attempt'] + '/' + n for n in read(ROOT / item['attempt'] / 'outputs.json'))
            inputs.add(item['attempt'] + '/outputs.json')
        bound = methods(task)
        frozen = {'methods': bound, 'inputs': {n: file_hash(ROOT / n) for n in sorted(inputs)},
                  'package': package_files(ROOT / 'src/legalmath'), 'runtime': runtime_files(), 'history': retained}
        write(folder / 'frozen.json', frozen, exclusive=True)
        admissions = [e['attempt'] for e in auth.events() if e['kind'] == 'ADMIT' and e['budget_key'] == task['budget_key']]
        require(len(admissions) == old['budgets'][task['budget_key']]['maximum_new_attempts'] == 9,
                'Original cumulative reasoning allowance differs')
        new = deepcopy(old); new['revision'] = 261; new['plan'] = PLAN
        new['build_contract'].update(version='general-build.v3', deferred_tasks=BUILD_FIRST_DEFERRED,
            required_tasks=[t for t in old['build_contract']['required_tasks'] if t != 'independent-packet'])
        current = next(t for t in new['tasks'] if t['id'] == 'reasoning-corpus')
        current.update(dossier=PLAN, validator='conditional-reasoning-current.v1', priority=-20,
            reason='Close original finite engineering requirements by current complete consumer evidence and independent reasoning checks',
            reasoning_acceptance={'version': 'conditional-reasoning-current.v1', 'review': REVIEW, 'bounds': BOUNDS},
            timeout_seconds=110)
        current['inputs'] = sorted(inputs | set(bound) | {RECONCILIATION, REVIEW + '/frozen.json',
            REVIEW + '/tests.xml', REVIEW + '/tests.log', REVIEW + '/preparation.json'})
        new['budgets'][task['budget_key']]['maximum_new_attempts'] = 10
        routes['baseline_revision'] = 261
        new_tasks = {t['id']: t for t in new['tasks']}
        for row in routes['tasks']:
            row['task_sha256'] = digest(new_tasks[row['task']])
            if row['task'] == 'reasoning-corpus': row['dossier'] = PLAN
        write(ROOT / ROUTES, routes, exclusive=True)
        new['continuation_review'].update(plan=PLAN, routes=ROUTES)
        for name in (PLAN, ROUTES, RECONCILIATION, SCRIPT, WORKER, EVIDENCE):
            new['continuation_review']['bindings'][name] = file_hash(ROOT / name)
        write(folder / 'preparation.json', {'seconds': time.monotonic() - tick,
            'tests': tests, 'test_argv': argv, 'history': retained, 'retained_admissions': admissions,
            'historical_unmeasured_seconds': 'UNKNOWN', 'new_attempt': ATTEMPT}, exclusive=True)
        review = {'baseline': digest(old), 'changes': current['reason'], 'scope_unchanged': True,
            'budget_unchanged': False, 'delivery_scope_changed': True,
            'delivery_authorization': new['build_contract']['authorization'], 'original_obligations_preserved': True,
            'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN,
                'scope': 'Original task identities, streams, obligations and historical evidence preserved; current reader-cohort prerequisite deferred',
                'default_audit': 'Independent original expectations and current isolated complete consumers required'},
            'evidence_contract': {'question': 'Current conditional reasoning acceptance within the declared domain',
                'baseline': retained, 'primary': 'Complete current consumers, independent verification, source bindings and actual refusals',
                'veto': 'Wrong source/method/import, missing case, false refusal, changed unrelated answer or exhausted bound',
                'explanatory': ['counts', 'timing'], 'not_concluded': ['legal truth', 'complete build', 'automatic interpretation', 'real holding']},
            'budget_revision': {'budget_key': task['budget_key'], 'previous_maximum': 9, 'new_maximum': 10,
                'retained_attempts': admissions, 'reason': current['reason'],
                'next_discriminating_check': 'Named validator independently checks actual current package and complete original reasoning cases',
                'stop_condition': BOUNDS, 'same_scope_authorization': 'User-directed general build; no external-adviser prerequisite'}}
        auth.validate_program(new)
        write(ROOT / PROPOSAL, new, exclusive=True)
        write(folder / 'review.json', review, exclusive=True)
        require(time.monotonic() - tick < 90, 'Preparation ceiling')
        print(json.dumps({'prepared_revision': 261, 'tests': tests, 'tasks': len(new['tasks']),
                          'obligations': len(new['obligations']), 'seconds': time.monotonic() - tick}))
    except BaseException as error:
        write(folder / 'failure.json', {'error': str(error), 'traceback': traceback.format_exc(),
              'seconds': time.monotonic() - tick}, exclusive=True)
        raise


def frozen(task):
    selector = task.get('reasoning_acceptance', {})
    require(task.get('validator') == 'conditional-reasoning-current.v1' and
            set(selector) == {'version', 'review', 'bounds'} and
            selector['version'] == 'conditional-reasoning-current.v1' and selector['bounds'] == BOUNDS and
            selector['review'] in {REVIEW, REL + '/reviews/reasoning-type-repair-262',
                                  REL + '/reviews/reasoning-witness-repair-263'},
            'Wrong named reasoning acceptance')
    value = read(ROOT / selector['review'] / 'frozen.json')
    for name, expected in {**value['methods'], **value['inputs']}.items():
        require(name in task['inputs'] and file_hash(ROOT / name) == expected, 'Frozen reasoning method/input changed: ' + name)
    same(package_files(ROOT / 'src/legalmath'), value['package'], 'current production package')
    same(runtime_files(), value['runtime'], 'CPU runtime')
    return value


def proof_check(attempt, mode, value):
    proof = read(attempt / (mode + '-proof.json'))
    target = ROOT / 'src' if mode == 'source' else attempt / 'installed'
    package = target / 'legalmath'
    same(package_files(package), value['package'], 'worker production package')
    require(proof['mode'] == mode and proof['isolated'] == 1 and proof['guard'] == {'blocked': 0}
        and proof['package_files'] == len(value['package']) and proof['modules']
        and Path(proof['prefix']).resolve() == runtime().resolve(), 'Wrong reasoning worker proof')
    if mode == 'installed':
        require(str(ROOT / 'src') not in proof['sys_path'], 'Checkout path leaked into installed run')
    require(Path(proof['python']).resolve() == (runtime() / 'bin/python').resolve(), 'Wrong worker executable')
    for row in proof['modules'].values():
        path = Path(row['path']).resolve()
        require(path.is_relative_to(package) and row['sha256'] == file_hash(path)
                == value['package'][str(path.relative_to(package))], 'Wrong production import origin')
    command = read(attempt / 'stages' / mode / 'command.json')
    same(command['argv'], [str(runtime() / 'bin/python'), '-I', '-B', str(ROOT / WORKER),
        str(ROOT), str(attempt), str(target), mode], 'actual worker command')
    same(command['environment']['CUDA_VISIBLE_DEVICES'], '-1', 'deliberately CPU-only worker')
    same(command['returncode'], 0, 'worker completion')
    return proof


def verification(attempt, task, replay=False):
    value = frozen(task)
    same(history(Authority(ROOT)), value['history'], 'sealed original reasoning evidence')
    same_records(attempt / 'source', attempt / 'installed-results')
    details = verify(ROOT, attempt / 'source')
    for mode in ('source', 'installed'):
        same(proof_check(attempt, mode, value)['details'], details, mode + ' complete checks')
    if replay:
        with tempfile.TemporaryDirectory(prefix='prospectus-reasoning-acceptance-') as folder:
            actual = Path(folder) / 'replay'
            same(evaluate(ROOT, actual), details, 'fresh current complete reasoning replay')
            same_records(actual, attempt / 'source')
    return details


def checked_stages(attempt, expected):
    stages = Path(attempt) / 'stages'
    require({p.parent.name for p in stages.glob('*/started.json')} == set(expected)
        == {p.parent.name for p in stages.glob('*/result.json')}, 'Incomplete or extra reasoning stages')
    for stage in expected:
        result = read(stages / stage / 'result.json')
        require(result.get('status') == 'PASS' and result.get('error') is None, 'Failed reasoning stage: ' + stage)


def validate_submission(root, attempt, task):
    require(Path(root).resolve() == ROOT and task['id'] == 'reasoning-corpus', 'Wrong reasoning acceptance root/task')
    result = read(Path(attempt) / 'result.json')
    require(result.get('task') == 'reasoning-corpus' and result.get('status') == 'PASS'
        and result.get('scope') == 'FINITE_ENGINEERING_ONLY' and result.get('source_meaning_proved') is False
        and result.get('whole_program_complete') is False, 'Invalid conditional reasoning scope/result')
    checked_stages(attempt, ('validate',) if task.get('evidence_attempt') else STAGES)
    target = Path(attempt)
    if task.get('evidence_attempt'):
        from legalmath.prospectus.execution_acceptance import retained_attempt
        target = retained_attempt(ROOT, task)
        auth = Authority(ROOT)
        event = next(e for e in reversed(auth.events()) if e.get('attempt') == task['evidence_attempt']
                     and e['kind'] in {'ACCEPT', 'RECORD'})
        require(auth.retained_evidence_valid(event), 'Original accepted reasoning evidence changed')
    actual = verification(target, task, replay=True)
    same(actual, read(Path(attempt) / 'verification.json'), 'recorded acceptance verification')
    return True


def execute(attempt, stage, argv, limit=90):
    folder = attempt / 'stages' / stage
    env = {**os.environ, 'PYTHONPATH': '', 'PYTHONDONTWRITEBYTECODE': '1',
           'PIP_NO_INDEX': '1', 'PYTHONNOUSERSITE': '1', 'CUDA_VISIBLE_DEVICES': '-1'}
    command = {'argv': argv, 'cwd': str(attempt), 'timeout_seconds': limit,
        'environment': {k: env[k] for k in ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'PIP_NO_INDEX', 'CUDA_VISIBLE_DEVICES')}}
    write(folder / 'command-started.json', command, exclusive=True)
    with (folder / 'stdout').open('xb') as out, (folder / 'stderr').open('xb') as err:
        result = subprocess.run(argv, cwd=attempt, env=env, stdout=out, stderr=err, timeout=limit)
    write(folder / 'command.json', {**command, 'returncode': result.returncode}, exclusive=True)
    require(result.returncode == 0, 'Worker failed; inspect retained stage stderr')


def storage(attempt):
    paths = {ROOT / n for n in (*SUPPORT, PROPOSAL, ROUTES, REL + '/revisions/0261.json')}
    for folder in (attempt, ROOT / REVIEW):
        paths.update(p for p in folder.rglob('*') if p.is_file())
    total = sum(p.stat().st_size for p in paths if p.is_file())
    require(total + BOUNDS['reserve_bytes'] < BOUNDS['new_bytes'], 'Reasoning storage ceiling')
    return total


def run(stage):
    tick = time.monotonic(); auth = Authority(ROOT); program, tasks, _ = auth.spec()
    task = tasks['reasoning-corpus']; attempt = ROOT / ATTEMPT
    admission = read(attempt / 'admission.json')
    latest = next(e for e in reversed(auth.events()) if e.get('task') == task['id'])
    require(latest['kind'] == 'ADMIT' and latest['attempt'] == ATTEMPT
        and admission['program_sha256'] == digest(program) and admission['binding'] == auth.binding(task)
        and admission['task_spec'] == task, 'Unchanged active reasoning admission required')
    require(stage in STAGES and not (attempt / 'outputs.json').exists(), 'Unknown or sealed reasoning stage')
    preceding = STAGES[:STAGES.index(stage)]
    require({p.parent.name for p in (attempt / 'stages').glob('*/started.json')} == set(preceding), 'Repeated/skipped stage')
    previous = [read(attempt / 'stages' / s / 'result.json') for s in preceding]
    require(all(r['status'] == 'PASS' for r in previous), 'Failed earlier stage')
    folder = attempt / 'stages' / stage; folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'started.json', {'at': now(), 'command': ['.venv/bin/python', '-m',
        'scripts.prospectus_reasoning_acceptance', 'run', '--stage', stage]}, exclusive=True)
    status, error, details = 'PASS', None, {}
    def expired(*args): raise TimeoutError('Reasoning stage ceiling')
    signal.signal(signal.SIGALRM, expired); signal.alarm(max(1, int(110 - (time.monotonic() - tick))))
    try:
        value = frozen(task)
        if stage == 'build':
            write(attempt / 'source-package.json', value['package'], exclusive=True)
            source = attempt / 'build-source'; source.mkdir()
            shutil.copyfile(ROOT / 'pyproject.toml', source / 'pyproject.toml')
            shutil.copytree(ROOT / 'src', source / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
            same(package_files(source / 'src/legalmath'), value['package'], 'copied package')
            execute(attempt, stage, [str(runtime() / 'bin/python'), '-I', '-B', '-m', 'pip', 'wheel',
                '--no-deps', '--no-build-isolation', '--no-index', '--wheel-dir', str(attempt / 'wheel'), str(source)], 60)
            wheels = list((attempt / 'wheel').glob('*.whl')); require(len(wheels) == 1, 'Exactly one wheel required')
            write(attempt / 'wheel.json', {'file': str(wheels[0].relative_to(attempt)), 'sha256': file_hash(wheels[0])}, exclusive=True)
        elif stage == 'install':
            wheel = read(attempt / 'wheel.json'); require(file_hash(attempt / wheel['file']) == wheel['sha256'], 'Wheel drift')
            execute(attempt, stage, [str(runtime() / 'bin/python'), '-I', '-B', '-m', 'pip', 'install', '--no-index', '--no-deps',
                '--no-compile', '--target', str(attempt / 'installed'), str(attempt / wheel['file'])], 60)
            same(package_files(attempt / 'installed/legalmath'), value['package'], 'installed package')
        elif stage in {'source', 'installed'}:
            target = ROOT / 'src' if stage == 'source' else attempt / 'installed'
            execute(attempt, stage, [str(runtime() / 'bin/python'), '-I', '-B', str(ROOT / WORKER),
                str(ROOT), str(attempt), str(target), stage])
            details = read(attempt / (stage + '-proof.json'))['details']
        elif stage == 'verify':
            details = verification(attempt, task, replay=True)
            write(attempt / 'verification.json', details, exclusive=True)
        else:
            details = verification(attempt, task)
            write(attempt / 'result.json', {'task': task['id'], 'status': 'PASS', 'scope': 'FINITE_ENGINEERING_ONLY',
                'source_meaning_proved': False, 'whole_program_complete': False, 'verification': details}, exclusive=True)
            # The authority calls the validator after all stages are final.
            verification(attempt, task, replay=True)
        frozen(task)
        total = read(ROOT / REVIEW / 'preparation.json')['seconds'] + sum(r['seconds'] for r in previous) + time.monotonic() - tick
        require(total < BOUNDS['incremental_seconds'], 'Cumulative reasoning time ceiling')
        details = {**details, 'new_bytes': storage(attempt), 'known_new_seconds': total}
        if stage == 'seal':
            (attempt / 'RESULT.md').write_text(
                '# Current conditional reasoning acceptance\n\n'
                'Current source and a freshly built isolated installation satisfy the original finite engineering checks. '
                'Complete original source-bound answers, independent Boolean/calendar checks and adverse controls agree. '
                'The registered validator replays the complete current evidence. The authority record determines acceptance.\n\n'
                '| Decision | Primary criterion | Veto status | Uncertainty | Next action | Not concluded |\n'
                '| --- | --- | --- | --- | --- | --- |\n'
                '| Submit reasoning engineering acceptance | Complete independent/current/installed checks pass | No declared veto | Source interpretation and unenumerated domains | Record, refresh, source-coverage reconciliation | Legal truth, original whole-program or build completion |\n\n'
                'Alternative explanation: a supplied legal formula can be wrong while correctly evaluated. '
                'Original sources, alternative readings and separate substantive tasks preserve that distinction. '
                'A counterexample within the declared grammar or altered source-to-answer binding overturns this engineering result.\n')
            write(attempt / 'run-manifest.json', {'git_commit': admission['git_commit'], 'plan': PLAN,
                'result': ATTEMPT + '/RESULT.md', 'command': ['.venv/bin/python', '-m', 'scripts.prospectus_reasoning_acceptance'],
                'stages': list(STAGES), 'python': sys.executable, 'runtime': str(runtime()),
                'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'random_seeds': 'Z3 random_seed=0; deterministic corpus',
                'data_version': file_hash(ROOT / REVIEW / 'frozen.json'), 'known_new_seconds': total,
                'historical_unmeasured_seconds': 'UNKNOWN', 'output_path': ATTEMPT}, exclusive=True)
    except BaseException as exc:
        status, error = 'FAIL', type(exc).__name__ + ': ' + str(exc)
        write(folder / 'failure.json', {'error': error, 'traceback': traceback.format_exc()}, exclusive=True)
    finally:
        signal.alarm(0)
        write(folder / 'result.json', {'stage': stage, 'status': status, 'error': error,
            'details': details, 'seconds': time.monotonic() - tick}, exclusive=True)
    if stage == 'seal' or status == 'FAIL':
        if status == 'FAIL':
            write(attempt / 'result.json', {'task': task['id'], 'status': 'FAIL', 'error': error,
                'whole_program_complete': False})
        write(attempt / 'outputs.json', {str(p.relative_to(attempt)): file_hash(p) for p in sorted(attempt.rglob('*'))
            if p.is_file() and p.name != 'admission.json' and '__pycache__' not in p.parts}, exclusive=True)
    print(json.dumps({'stage': stage, 'status': status, 'error': error, 'seconds': time.monotonic() - tick}))
    return 0 if status == 'PASS' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run'))
    parser.add_argument('--stage', choices=STAGES)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(); return 0
    return run(args.stage)


if __name__ == '__main__':
    raise SystemExit(main())
