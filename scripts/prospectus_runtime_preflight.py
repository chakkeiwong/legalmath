"""Current source rehearsal with original budgets and immutable comparators."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                  LEGALMATH_OCR_PYTHON='/home/chakwong/miniconda3/envs/tfgpu/bin/python')
from legalmath.prospectus.execution_authority import Authority, REL, read, write, digest, file_hash
from legalmath.prospectus import native_source_rehearsal as source
from scripts.prospectus_native_source_rehearsal import rehearse
from scripts import prospectus_native_product_delta as original
from scripts.prospectus_calendar_evidence import load

PLAN = 'docs/plans/prospectus-runtime-preflight-2026-10-17.md'
NEXT = 'docs/plans/prospectus-post-repair-runtime-2026-10-17.md'
SCRIPT = 'scripts/prospectus_runtime_preflight.py'
DONOR = REL + '/attempts/source-bes-dep-06/attempt-013'
HISTORY = (original.NATIVE, REL + '/attempts/native-binding/attempt-021', DONOR)
ROUTES = tuple(source.preparation.ROUTES)
STAGES = (*('route-' + r for r in ROUTES), 'adverse', 'verify', 'seal')
BOUNDS = {'preparation_seconds': 60, 'stage_seconds': 110, 'incremental_seconds': 750,
          'new_bytes': 64 * 1024**2, 'reserve_bytes': 2 * 1024**2,
          'native_calls': 0, 'gpu_calls': 0, 'test_starts': 1, 'unchanged_retries': 0}
require = source.require


def package(folder):
    return {str(p.relative_to(folder)): file_hash(p) for p in folder.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def methods():
    names = {str(p.relative_to(ROOT)) for p in (ROOT / 'src/legalmath').rglob('*')
             if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    names |= set(source.methods(ROOT)) | set(original.methods(ROOT)) | {SCRIPT, PLAN, NEXT,
        'scripts/prospectus_native_source_rehearsal.py', 'scripts/prospectus_calendar_evidence.py',
        'scripts/prospectus_calendar_oracle.py', *source.TESTS}
    return {n: file_hash(ROOT / n) for n in sorted(names)}


def retained(auth):
    rows = []
    for name in HISTORY:
        event = next(e for e in reversed(auth.events()) if e.get('attempt') == name and e['kind'] in {'RECORD', 'ACCEPT'})
        require(auth.retained_evidence_valid(event), 'Retained runtime evidence changed: ' + name)
        rows.append({'attempt': name, 'event_sha256': event['sha256'], 'outputs_sha256': event['outputs_sha256']})
    return rows


def prepare():
    tick = time.monotonic(); auth = Authority(ROOT); old, tasks, _ = auth.spec()
    task = tasks['native-binding']; revision = old['revision'] + 1
    review = REL + '/reviews/runtime-preflight-' + str(revision)
    folder = ROOT / review; folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'started.json', {'at': datetime.now(timezone.utc).isoformat(),
          'command': ['.venv/bin/python', '-m', 'scripts.prospectus_runtime_preflight', 'prepare']}, exclusive=True)
    def expired(*args): raise TimeoutError('Runtime preflight preparation ceiling')
    signal.signal(signal.SIGALRM, expired); signal.alarm(max(1, int(60 - (time.monotonic() - tick))))
    try:
        history = retained(auth); current = methods()
        files = package(ROOT / 'src/legalmath')
        require(len(files) == 452 and files == read(ROOT / DONOR / 'source-package.json')
                == package(ROOT / DONOR / 'installed/legalmath'), 'Frozen452-file package changed')
        inputs = set(task['inputs'])
        for name in HISTORY:
            inputs |= {name + '/' + n for n in read(ROOT / name / 'outputs.json')} | {name + '/outputs.json'}
        ledgers = {}
        for task_name in ('native-binding', 'native-confinement'):
            for path in sorted((ROOT / REL / 'attempts' / task_name).glob('attempt-*/*ledger.json')):
                value = read(path); name = str(path.relative_to(ROOT)); inputs.add(name)
                ledgers[name] = {'sha256': file_hash(path), 'historical_lower_bound': value.get('historical_lower_bound'),
                    'reservations': len(value.get('reservations', [])), 'limit': value.get('limit')}
        binding_ledger = read(ROOT / original.NATIVE / 'process-ledger.json')
        require(binding_ledger['historical_lower_bound'] + len(binding_ledger['reservations']) == 61, 'Native history differs')
        installed = ROOT / REL / 'attempts/native-confinement/attempt-012'
        for filename, expected in (('native-ledger.json', 16), ('outer-ledger.json', 94)):
            ledger = read(installed / filename)
            require(ledger['historical_lower_bound'] + len(ledger['reservations']) == expected,
                    'Installed cumulative ledger differs: ' + filename)
        previous = read(ROOT / HISTORY[1] / 'methods.json')
        delta = {n: {'old': h, 'current': file_hash(ROOT / n)} for n, h in previous.items() if file_hash(ROOT / n) != h}
        write(folder / 'source-review.json', {'history': history, 'native_binding_lower_bound': 61,
            'installed_native_lower_bound': 16, 'installed_outer_lower_bound': 94, 'ledgers': ledgers,
            'changed_historical_methods': delta, 'package_files': len(files),
            'comparison': 'Complete current values versus actual017 and original006/008; no historical profile bridge'}, exclusive=True)
        argv = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *source.TESTS,
                '--junitxml=' + str(folder / 'tests.xml')]
        with (folder / 'tests.log').open('xb') as log:
            result = subprocess.run(argv, cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src'),
                'PYTHONDONTWRITEBYTECODE': '1'}, stdout=log, stderr=subprocess.STDOUT,
                timeout=max(1, 55 - (time.monotonic() - tick)))
        require(result.returncode == 0, 'Current source-rehearsal tests failed')
        from legalmath.prospectus.execution_acceptance import checked_tests
        tests = checked_tests(folder / 'tests.xml', 1)
        require(current == methods(), 'Preparation methods changed')
        write(folder / 'frozen.json', {'methods': current, 'inputs': {n: file_hash(ROOT / n) for n in sorted(inputs)},
              'package': files, 'history': history}, exclusive=True)
        admissions = [e['attempt'] for e in auth.events() if e['kind'] == 'ADMIT' and e['budget_key'] == task['budget_key']]
        before = old['budgets'][task['budget_key']]['maximum_new_attempts']
        require(len(admissions) == before == 21, 'Unexpected native admission history')
        preparation = {'seconds': time.monotonic() - tick, 'tests': tests, 'test_command': argv,
            'retained_admissions': admissions, 'revision': revision, 'historical_unmeasured_seconds': 'UNKNOWN'}
        write(folder / 'preparation.json', preparation, exclusive=True)
        new = deepcopy(old); new['revision'] = revision
        current_task = next(t for t in new['tasks'] if t['id'] == task['id'])
        current_task['previous_native_validator'] = current_task.pop('validator')
        current_task.update(dossier=PLAN, reason='Execute current full source and downstream rehearsal of five original routes with zero new native calls; prepare explicit current runtime validation',
            preparation_only=True, native_call_allowance=0, retained_acceptance_only=False,
            runtime_preflight={'version': 'runtime-preflight.v1', 'review': review, 'bounds': BOUNDS}, timeout_seconds=120)
        current_task['inputs'] = sorted(inputs | set(current) | {str(p.relative_to(ROOT)) for p in folder.iterdir() if p.is_file()})
        new['budgets'][task['budget_key']]['maximum_new_attempts'] = before + 1
        routes = read(ROOT / old['continuation_review']['routes']); routes['baseline_revision'] = revision
        for row in routes['tasks']:
            if row['task'] == task['id']:
                row.update(task_sha256=digest(current_task), dossier=PLAN, phase=0, mode='local', remaining=current_task['reason'],
                    next_action='Run five bounded source rehearsals and original refusals; verify, record and refresh before reviewing fresh native/runtime stages.', stop_condition=BOUNDS)
            elif row['task'] == 'reasoning-corpus':
                row.update(phase=3, remaining='009 recorded118 complete installed answers,4096 corpus checks,99 integer calendar checks and actual refusal/forgery controls; wider task remains open.',
                    next_action='Preserve installed009 and current452-file package; continue current runtime and source/domain work.')
        route = REL + '/closure-routes-2026-10-17-runtime-preflight-' + str(revision) + '.json'
        write(ROOT / route, routes, exclusive=True); new['continuation_review'].update(plan=PLAN, routes=route)
        for name in (PLAN, NEXT, SCRIPT, route): new['continuation_review']['bindings'][name] = file_hash(ROOT / name)
        audit = {'baseline': digest(old), 'changes': current_task['reason'], 'scope_unchanged': True, 'budget_unchanged': False,
            'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'source_review': review + '/source-review.json'},
            'evidence_contract': PLAN,
            'budget_revision': {'budget_key': task['budget_key'], 'previous_maximum': before, 'new_maximum': before + 1,
                'retained_attempts': admissions, 'reason': current_task['reason'],
                'next_discriminating_check': 'Current source dispatch and complete P1-P5/answer equality before fresh source calls',
                'stop_condition': BOUNDS, 'same_scope_authorization': 'User-directed general build and continued execution'}}
        auth.validate_program(new)
        write(ROOT / REL / 'proposals' / ('runtime-preflight-' + str(revision) + '.json'), new, exclusive=True)
        write(ROOT / REL / 'proposals' / ('runtime-preflight-' + str(revision) + '-review.json'), audit, exclusive=True)
        preparation['seconds'] = time.monotonic() - tick
        write(folder / 'preparation.json', preparation)
        print(json.dumps({'prepared_revision': revision, 'tests': tests, 'seconds': preparation['seconds'],
                          'attempt': REL + '/attempts/native-binding/attempt-022'}))
    except BaseException as exc:
        write(folder / 'failure.json', {'error': str(exc), 'seconds': time.monotonic() - tick,
              'traceback': traceback.format_exc()}, exclusive=True)
        raise
    finally:
        signal.alarm(0)


def unchanged(task):
    selector = task['runtime_preflight']
    require(selector['bounds'] == BOUNDS and task.get('validator') is None and task['native_call_allowance'] == 0,
            'Wrong preflight grant')
    frozen = read(ROOT / selector['review'] / 'frozen.json')
    require(frozen['methods'] == methods() and frozen['inputs'] == {n: file_hash(ROOT / n) for n in frozen['inputs']}
            and frozen['package'] == package(ROOT / 'src/legalmath') == package(ROOT / DONOR / 'installed/legalmath'),
            'Current preflight methods/sources/package changed')
    return frozen


def verify(attempt):
    rows = []
    for name in ROUTES:
        folder = attempt / 'routes' / name
        dispatch, comparison = read(folder / 'dispatch.json'), read(folder / 'comparison.json')
        source.check_delivery(ROOT, name, dispatch)
        require(set(comparison['objects']) == {'P1', 'P2', 'P3', 'P4', 'P5', 'answer'}
                and all(comparison['complete_equality'].values()), 'Incomplete source comparison')
        for key, ref in comparison['objects'].items():
            require(file_hash(ROOT / ref['path']) == ref['sha256'], 'Referenced original changed')
            require(load(ROOT / ref['path']) == load(ROOT / original.NATIVE / 'routes' / name / (key + '.json.gz')),
                    'Actual017 and original source comparators differ')
        rows.append({'route': name, 'complete_raw_source_and_P1_P5_answer_equal': True})
    expected = read(ROOT / REL / 'attempts/native-binding/attempt-021/adverse.json')
    require(read(attempt / 'adverse.json') == expected, 'Original provenance refusals changed')
    return {'routes': rows, 'provenance_refusals': len(expected), 'new_native_calls': 0,
            'fresh_native_execution_established': False, 'whole_task_complete': False}


def run(name, stage):
    tick = time.monotonic(); auth = Authority(ROOT); program, tasks, _ = auth.spec(); task = tasks['native-binding']
    attempt = auth.path(name); admission = read(attempt / 'admission.json')
    event = next(e for e in reversed(auth.events()) if e.get('task') == task['id'])
    require(event['kind'] == 'ADMIT' and event['attempt'] == name and admission['program_sha256'] == digest(program)
            and admission['task_spec'] == task and admission['binding'] == auth.binding(task), 'Current unchanged preflight admission required')
    require(stage in STAGES and not (attempt / 'outputs.json').exists(), 'Unknown or sealed preflight stage')
    index = STAGES.index(stage)
    require({p.parent.name for p in (attempt / 'stages').glob('*/started.json')} ==
            {p.parent.name for p in (attempt / 'stages').glob('*/result.json')} == set(STAGES[:index]), 'Repeated, skipped or interrupted preflight')
    earlier = [read(attempt / 'stages' / s / 'result.json') for s in STAGES[:index]]
    require(all(r['status'] == 'PASS' for r in earlier), 'Failed preflight predecessor')
    folder = attempt / 'stages' / stage; folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'started.json', {'at': datetime.now(timezone.utc).isoformat(), 'command':
        ['.venv/bin/python', '-m', 'scripts.prospectus_runtime_preflight', 'run', '--attempt', name, '--stage', stage]}, exclusive=True)
    status, error, details = 'PASS', None, {}
    guard = {'blocked': 0}
    def audit(event, args):
        if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty',
                'os.exec', 'os.posix_spawn', 'os.spawn', 'pty.spawn'}:
            guard['blocked'] += 1; raise RuntimeError('Preflight forbids actual process/network actions')
    sys.addaudithook(audit)
    def expired(*args): raise TimeoutError('Runtime preflight stage ceiling')
    signal.signal(signal.SIGALRM, expired); signal.alarm(max(1, int(110 - (time.monotonic() - tick))))
    try:
        frozen = unchanged(task)
        if stage.startswith('route-'):
            details = rehearse(ROOT, attempt, stage.removeprefix('route-'))
        elif stage == 'adverse':
            details = original.adverse(ROOT); write(attempt / 'adverse.json', details, exclusive=True)
        elif stage == 'verify':
            require(retained(auth) == frozen['history'], 'Historical preflight evidence changed')
            details = verify(attempt); write(attempt / 'verification.json', details, exclusive=True)
        else:
            details = verify(attempt)
            require(details == read(attempt / 'verification.json'), 'Preflight verification changed')
        unchanged(task)
        prep = read(ROOT / task['runtime_preflight']['review'] / 'preparation.json')
        elapsed = prep['seconds'] + sum(r['seconds'] for r in earlier) + time.monotonic() - tick
        used = sum(p.stat().st_size for parent in (attempt, ROOT / task['runtime_preflight']['review'])
                   for p in parent.rglob('*') if p.is_file())
        used += sum((ROOT / n).stat().st_size for n in (SCRIPT, PLAN, NEXT))
        for p in (ROOT / REL / 'proposals').glob('runtime-preflight-' + str(prep['revision']) + '*.json'): used += p.stat().st_size
        used += (ROOT / REL / 'revisions' / f'{prep["revision"]:04d}.json').stat().st_size
        used += (ROOT / REL / ('closure-routes-2026-10-17-runtime-preflight-' + str(prep['revision']) + '.json')).stat().st_size
        require(guard['blocked'] == 0 and elapsed < 750 and time.monotonic() - tick < 110
                and used + BOUNDS['reserve_bytes'] < BOUNDS['new_bytes'], 'Preflight resource/action veto')
        if stage == 'seal':
            (attempt / 'RESULT.md').write_text('# Current source/runtime preflight\n\n'
                'All five current source/downstream rehearsals equal the original complete raw/consumed source, P1-P5 and answers. '
                'Three actual re-sealed provenance attacks retain their original refusals. No native process ran.\n\n'
                '| Decision | Primary criterion | Veto | Uncertainty | Next action | Limit |\n| --- | --- | --- | --- | --- | --- |\n'
                '| Retain current preflight | Whole original equality and refusals pass | No drift, forbidden call or overrun | Actual current native execution pending | Review original-task live/runtime continuation | Not renewed native acceptance or whole-build completion |\n\n'
                'Post-run red team: identical recorded streams can conceal a changed live environment. The separate actual live/runtime phases must check that environment.\n')
            write(attempt / 'run-manifest.json', {'git_commit': admission['git_commit'], 'plan': PLAN, 'result': name + '/RESULT.md',
                'environment': sys.executable, 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'seeds': 'N/A deterministic',
                'methods': frozen['methods'], 'data_version': frozen['inputs'], 'cumulative_seconds': elapsed,
                'cumulative_bytes': used, 'historical_unmeasured_seconds': 'UNKNOWN',
                'commands': [read(attempt / 'stages' / s / 'started.json') for s in STAGES]}, exclusive=True)
            write(attempt / 'result.json', {'task': task['id'], 'status': 'PASS', 'scope': 'CURRENT_RECORDED_SOURCE_REHEARSAL_ONLY',
                'whole_task_complete': False, 'whole_program_complete': False, 'verification': details}, exclusive=True)
    except BaseException as exc:
        status, error = 'FAIL', type(exc).__name__ + ': ' + str(exc)
        write(folder / 'failure.json', {'error': error, 'traceback': traceback.format_exc()}, exclusive=True)
    finally:
        signal.alarm(0)
    write(folder / 'result.json', {'status': status, 'error': error, 'seconds': time.monotonic() - tick,
          'details': details, 'guard': guard}, exclusive=True)
    if stage == 'seal' or status == 'FAIL':
        if not (attempt / 'result.json').exists(): write(attempt / 'result.json', {'task': task['id'], 'status': 'FAIL', 'error': error}, exclusive=True)
        write(attempt / 'outputs.json', {str(p.relative_to(attempt)): file_hash(p) for p in sorted(attempt.rglob('*'))
              if p.is_file() and p.name not in {'outputs.json', 'admission.json'}}, exclusive=True)
    print(json.dumps({'stage': stage, 'status': status, 'error': error, 'seconds': time.monotonic() - tick}))
    return int(status != 'PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('action', choices=['prepare', 'run'])
    parser.add_argument('--attempt'); parser.add_argument('--stage', choices=STAGES); args = parser.parse_args()
    if args.action == 'prepare': prepare()
    else:
        if not args.attempt or not args.stage: parser.error('--attempt and --stage required')
        raise SystemExit(run(args.attempt, args.stage))
