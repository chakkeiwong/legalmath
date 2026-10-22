"""Explicit current native matrix with cumulative accounting and full validation."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import difflib
import json
import os
from pathlib import Path
import shutil
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
from legalmath.prospectus import native_current_acceptance as checks
from legalmath.prospectus.successor import process_ledger
from scripts import prospectus_native_current as live
from scripts.prospectus_native_campaign import bounded_stage, no_subprocess
from scripts.prospectus_runtime_preflight import package

SCRIPT = 'scripts/prospectus_runtime_matrix.py'
TEST = 'tests/prospectus/test_runtime_matrix.py'
PLAN = 'docs/plans/prospectus-current-runtime-matrix-2026-10-17.md'
REVIEW = REL + '/reviews/runtime-matrix-245-r2'
FAILED_PREPARATION = REL + '/reviews/runtime-matrix-245'
PREFLIGHT = REL + '/attempts/native-binding/attempt-022'
DONOR = REL + '/attempts/source-bes-dep-06/attempt-013'
CHANGED = ('scripts/prospectus_native_current.py', 'scripts/prospectus_current_acceptance.py')
STAGES = ('prepare', 'controls', *('route-' + r for r in checks.ROUTES), 'probe', 'verify', 'seal')
TESTS = (*checks.rehearsal.TESTS, checks.TEST, TEST)
BOUNDS = {'preparation_seconds': 90, 'stage_seconds': 120, 'incremental_seconds': 1200,
          'validation_seconds': 180, 'native_calls': 11, 'historical_native_lower_bound': 61,
          'new_bytes': 512 * 1024**2, 'reserve_bytes': 4 * 1024**2, 'unchanged_retries': 0}
SELECTOR = {'version': 'current-runtime-matrix.v1', 'review': REVIEW, 'preflight': PREFLIGHT,
            'donor': DONOR, 'routes': list(checks.ROUTES), 'bounds': BOUNDS}
require = checks.require


def selector(task):
    require(task.get('id') == 'native-binding' and task.get('handler') == 'agent'
            and task.get('validator') == 'native-retained-current.v3'
            and task.get('current_runtime_matrix') == SELECTOR
            and task.get('preparation_only') is False and task.get('retained_acceptance_only') is False
            and task.get('native_call_allowance') == 11, 'Missing or altered current runtime matrix grant')


def ledger(folder, expected=None):
    value = process_ledger.checked(folder / 'process-ledger.json')
    require(value['limit'] == 11 and value['historical_lower_bound'] == 61, 'Wrong current cumulative native ledger')
    if expected is not None:
        require(len(value['reservations']) == expected and all(r['state'] == 'STARTED' for r in value['reservations']),
                'Missing, failed or unaccounted native reservation')
    return value


def methods():
    names = {str(p.relative_to(ROOT)) for p in (ROOT / 'src/legalmath').rglob('*')
             if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    names |= set(checks.methods(ROOT)) | {SCRIPT, TEST, PLAN, *CHANGED, *TESTS,
        'scripts/prospectus_runtime_preflight.py', 'scripts/prospectus_calendar_evidence.py',
        'scripts/prospectus_calendar_oracle.py'}
    return {n: file_hash(ROOT / n) for n in sorted(names)}


def retained(auth):
    rows = []
    for name in (PREFLIGHT, DONOR, REL + '/attempts/native-binding/attempt-017'):
        event = next(e for e in reversed(auth.events()) if e.get('attempt') == name and e['kind'] in {'RECORD', 'ACCEPT'})
        require(auth.retained_evidence_valid(event), 'Historical matrix evidence changed')
        rows.append({'attempt': name, 'event_sha256': event['sha256'], 'outputs_sha256': event['outputs_sha256']})
    return rows


def prepare():
    tick = time.monotonic(); auth = Authority(ROOT); old, tasks, _ = auth.spec()
    require(old['revision'] == 244, 'Wrong current matrix preparation baseline')
    folder = ROOT / REVIEW
    folder.mkdir(parents=True, exist_ok=False)
    shutil.copytree(ROOT / FAILED_PREPARATION / 'before', folder / 'before')
    shutil.copyfile(ROOT / FAILED_PREPARATION / 'before.json', folder / 'before.json')
    prior_seconds = read(ROOT / FAILED_PREPARATION / 'failure.json')['seconds']
    write(folder / 'repair-review.json', {'failed_preparation': FAILED_PREPARATION,
        'failed_sha256': file_hash(ROOT / FAILED_PREPARATION / 'failure.json'),
        'cause': 'Driver was retained as an input, not in the preflight method set; exact reviewed two-file delta confirmed across both sets',
        'repair': 'Check union of frozen methods and inputs; preserve failure and charge both preparations; no prior test/native start'}, exclusive=True)
    write(folder / 'started.json', {'at': datetime.now(timezone.utc).isoformat(),
          'command': ['.venv/bin/python', '-m', 'scripts.prospectus_runtime_matrix', 'prepare']}, exclusive=True)
    try:
        with bounded_stage(max(1, 90 - prior_seconds - (time.monotonic() - tick))):
            history = retained(auth)
            before = read(folder / 'before.json')
            require(set(before) == set(CHANGED), 'Wrong driver change scope')
            for name, expected in before.items(): require(file_hash(folder / 'before' / name) == expected, 'Pre-edit bytes changed')
            # Confirm these repository-driver edits cannot stale the completed
            # financial package or installed reasoning methods/inputs.
            reviews = [REL + '/reviews/component-' + str(r) for r in (238, 240, 241, 242)]
            reviews += [REL + '/reviews/pension-post-repair-239', REL + '/reviews/installed-reasoning-243']
            for review in reviews:
                frozen = read(ROOT / review / 'frozen.json')
                require(not set(CHANGED) & (set(frozen['methods']) | set(frozen['inputs'])), 'Completed component binds changed driver')
            old_frozen = read(ROOT / REL / 'reviews/runtime-preflight-244/frozen.json')
            changed = {n for n, h in {**old_frozen['methods'], **old_frozen['inputs']}.items() if file_hash(ROOT / n) != h}
            require(changed == set(CHANGED), 'Unreviewed production/preflight method change')
            diff = []
            for name in CHANGED:
                diff.extend(difflib.unified_diff((folder / 'before' / name).read_text().splitlines(True),
                    (ROOT / name).read_text().splitlines(True), fromfile='before/' + name, tofile='after/' + name))
            (folder / 'driver.patch').write_text(''.join(diff))
            current = methods(); files = package(ROOT / 'src/legalmath')
            require(len(files) == 452 and files == read(ROOT / DONOR / 'source-package.json')
                    == package(ROOT / DONOR / 'installed/legalmath'), 'Production/package freeze violated')
            argv = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *TESTS,
                    '--junitxml=' + str(folder / 'tests.xml')]
            with (folder / 'tests.log').open('xb') as out:
                result = subprocess.run(argv, cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src'),
                    'PYTHONDONTWRITEBYTECODE': '1'}, stdout=out, stderr=subprocess.STDOUT,
                    timeout=max(1, 80 - (time.monotonic() - tick)))
            require(result.returncode == 0, 'Current runtime driver/selector tests failed')
            from legalmath.prospectus.execution_acceptance import checked_tests
            count = checked_tests(folder / 'tests.xml', 1)
            require(current == methods(), 'Methods changed during preparation')
            task = tasks['native-binding']; inputs = set(task['inputs'])
            for row in history:
                name = row['attempt']; inputs |= {name + '/' + n for n in read(ROOT / name / 'outputs.json')} | {name + '/outputs.json'}
            write(folder / 'frozen.json', {'methods': current, 'inputs': {n: file_hash(ROOT / n) for n in sorted(inputs)},
                'history': history, 'package': files, 'native_methods': checks.methods(ROOT)}, exclusive=True)
            admissions = [e['attempt'] for e in auth.events() if e['kind'] == 'ADMIT' and e['budget_key'] == task['budget_key']]
            require(len(admissions) == old['budgets']['native-binding']['maximum_new_attempts'] == 22, 'Cumulative admissions differ')
            preparation = {'seconds': prior_seconds + time.monotonic() - tick, 'tests': count, 'test_command': argv,
                'retained_admissions': admissions, 'historical_unmeasured_seconds': 'UNKNOWN',
                'failed_preparation_seconds': prior_seconds,
                'forecast_unique_bytes': 440 * 1024**2, 'forecast_route_seconds': 50,
                'forecast_basis': 'Original native017 storage forecast and current022 stages33-34seconds;512MiB/120seconds limits unchanged'}
            write(folder / 'preparation.json', preparation, exclusive=True)
            new = deepcopy(old); new['revision'] = 245
            t = next(t for t in new['tasks'] if t['id'] == task['id'])
            t.update(dossier=PLAN, reason='Fresh current five-route native matrix and namespace probe under11 additional reservations,preceding floor61; preserve all22 admissions',
                validator='native-retained-current.v3', preparation_only=False, retained_acceptance_only=False,
                native_call_allowance=11, current_runtime_matrix=SELECTOR, timeout_seconds=200)
            t['inputs'] = sorted(inputs | set(current) | {str(p.relative_to(ROOT)) for p in folder.rglob('*') if p.is_file()})
            new['budgets'][t['budget_key']]['maximum_new_attempts'] = 23
            routes = read(ROOT / old['continuation_review']['routes']); routes['baseline_revision'] = 245
            for row in routes['tasks']:
                if row['task'] == t['id']:
                    row.update(task_sha256=digest(t), dossier=PLAN, phase=0, mode='local', remaining=t['reason'],
                        next_action='Prepare owned snapshots,run original controls,canary and remaining actual routes,probe,verify/seal,record/refresh; then installed lifecycles.', stop_condition=BOUNDS)
            route_name = REL + '/closure-routes-2026-10-17-runtime-matrix-245.json'
            write(ROOT / route_name, routes, exclusive=True); new['continuation_review'].update(plan=PLAN, routes=route_name)
            for name in (PLAN, SCRIPT, route_name): new['continuation_review']['bindings'][name] = file_hash(ROOT / name)
            review = {'baseline': digest(old), 'changes': t['reason'], 'scope_unchanged': True, 'budget_unchanged': False,
                'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'driver_delta': REVIEW + '/driver.patch',
                    'old_behavior': 'Exact historical defaults retained;new selector explicit;completed package bindings exclude changes'},
                'evidence_contract': PLAN, 'budget_revision': {'budget_key': t['budget_key'], 'previous_maximum': 22,
                    'new_maximum': 23, 'retained_attempts': admissions, 'reason': t['reason'],
                    'next_discriminating_check': 'Actual current native streams and complete answers,original refusals and boundary probe',
                    'stop_condition': BOUNDS, 'same_scope_authorization': 'User-directed continuing general build;actual host permission is separate'}}
            auth.validate_program(new)
            write(ROOT / REL / 'proposals/runtime-matrix-245.json', new, exclusive=True)
            write(ROOT / REL / 'proposals/runtime-matrix-245-review.json', review, exclusive=True)
            preparation['seconds'] = prior_seconds + time.monotonic() - tick; write(folder / 'preparation.json', preparation)
            print(json.dumps({'prepared_revision': 245, 'tests': count, 'seconds': preparation['seconds'],
                'attempt': REL + '/attempts/native-binding/attempt-023'}))
    except BaseException as exc:
        write(folder / 'failure.json', {'error': str(exc), 'seconds': time.monotonic() - tick, 'traceback': traceback.format_exc()}, exclusive=True)
        raise


def frozen(task):
    selector(task); value = read(ROOT / REVIEW / 'frozen.json')
    require(value['methods'] == methods() and value['inputs'] == {n: file_hash(ROOT / n) for n in value['inputs']}, 'Matrix method/source drift')
    require(value['package'] == package(ROOT / 'src/legalmath') == package(ROOT / DONOR / 'installed/legalmath'), 'Package drift')
    return value


def charged(attempt):
    paths = [attempt, ROOT / REVIEW, ROOT / FAILED_PREPARATION, ROOT / SCRIPT, ROOT / TEST, ROOT / PLAN, ROOT / REL / 'revisions/0245.json',
             ROOT / REL / 'proposals/runtime-matrix-245.json', ROOT / REL / 'proposals/runtime-matrix-245-review.json',
             ROOT / REL / 'closure-routes-2026-10-17-runtime-matrix-245.json']
    files = {}
    for parent in paths:
        for path in parent.rglob('*') if parent.is_dir() else [parent]:
            require(not path.is_symlink(), 'Matrix evidence symlink refused')
            if path.is_file():
                stat = path.stat(); files[stat.st_dev, stat.st_ino] = stat.st_size
    count = sum(files.values())
    require(count + BOUNDS['reserve_bytes'] < BOUNDS['new_bytes'], 'Matrix storage bound')
    return count


def evidence(attempt, task):
    selector(task); f = frozen(task)
    checks.check_methods(ROOT, attempt); tested = checks.tests(attempt, f['native_methods'])
    require(retained(Authority(ROOT)) == f['history'], 'Original matrix evidence changed')
    for stage in STAGES[:STAGES.index('verify')]:
        r = read(attempt / 'stages' / stage / 'result.json')
        require(r['status'] == 'PASS' and 0 <= r['seconds'] < 120, 'Missing/failed matrix stage')
    snapshots = {year: checks.prep.historical.snapshot(attempt / 'snapshots' / year) for year in ('2009', '2010')}
    for year, previous in (('2009', 'attempt-008'), ('2010', 'attempt-006')):
        require(snapshots[year] == read(ROOT / REL / 'attempts/native-binding' / previous / 'snapshot/manifest.json'), 'Original snapshot changed')
    routes = [checks.check_route(ROOT, attempt, name, consume=True) for name in checks.ROUTES]
    controls = checks.prep.historical.check_controls(attempt)
    probe = checks.prep.historical.check_probe(attempt, snapshots['2009'])
    rows = ledger(attempt, 11)['reservations']
    require([r['argv'][0] == '/usr/bin/bwrap' for r in rows] ==
            [True, True, False, False, True, True, True, True, True, True, True], 'Wrong actual native sequence')
    ranges = [read(attempt / 'stages' / ('route-' + r) / 'result.json')['details']['reservations'] for r in checks.ROUTES]
    require(ranges == [[i, i+2] for i in range(0, 10, 2)], 'Route reservation accounting differs')
    require(read(attempt / 'stages/probe/result.json')['details']['reservations'] == [10, 11], 'Probe accounting differs')
    charged(attempt)
    return {'routes': routes, 'prelaunch_refusals': controls, 'probe_receipt_sha256': probe, 'tests': tested,
        'native_reservations': 11, 'historical_native_lower_bound': 61, 'cumulative_native_lower_bound': 72,
        'package_files': len(f['package']), 'methods_sha256': digest(f['methods']),
        'scope': 'FINITE_CURRENT_NATIVE_EXECUTION', 'whole_program_complete': False}


def validate_submission(root, attempt, task):
    require(Path(root).resolve() == ROOT, 'Wrong current runtime root')
    start = time.monotonic()
    with bounded_stage(180), no_subprocess({'attempts': 0}):
        actual = evidence(Path(attempt), task)
        require(read(Path(attempt) / 'verification.json') == actual, 'Current matrix verification mismatch')
        result = read(Path(attempt) / 'result.json')
        require(result.get('status') == 'PASS' and result.get('task') == 'native-binding'
                and result.get('scope') == 'FINITE_CURRENT_NATIVE_EXECUTION'
                and result.get('whole_program_complete') is False, 'Wrong current native disposition')
        spent = read(ROOT / REVIEW / 'preparation.json')['seconds']
        for stage in STAGES:
            row = read(Path(attempt) / 'stages' / stage / 'result.json')
            require(row['status'] == 'PASS' and 0 <= row['seconds'] < 120, 'Failed matrix stage')
            spent += row['seconds']
        require(spent + time.monotonic() - start < 1200, 'Cumulative matrix bound')
    print(json.dumps({'current_native_validation_seconds': time.monotonic() - start}), flush=True)
    return True


def run(name, stage):
    start = time.monotonic(); auth = Authority(ROOT); program, tasks, _ = auth.spec(); task = tasks['native-binding']
    selector(task); attempt = auth.path(name); admission = read(attempt / 'admission.json')
    event = next(e for e in reversed(auth.events()) if e.get('task') == task['id'])
    require(event['kind'] == 'ADMIT' and event['attempt'] == name and admission['program_sha256'] == digest(program)
            and admission['task_spec'] == task and admission['binding'] == auth.binding(task), 'Current unchanged matrix admission required')
    require(stage in STAGES and not (attempt / 'outputs.json').exists(), 'Unknown or sealed matrix stage')
    index = STAGES.index(stage)
    require({p.parent.name for p in (attempt / 'stages').glob('*/started.json')} ==
            {p.parent.name for p in (attempt / 'stages').glob('*/result.json')} == set(STAGES[:index]), 'Repeated/skipped/interrupted matrix stage')
    earlier = [read(attempt / 'stages' / s / 'result.json') for s in STAGES[:index]]
    require(all(r['status'] == 'PASS' for r in earlier), 'Failed matrix predecessor')
    folder = attempt / 'stages' / stage; folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'started.json', {'at': datetime.now(timezone.utc).isoformat(),
        'command': ['.venv/bin/python', '-m', 'scripts.prospectus_runtime_matrix', 'run', '--attempt', name, '--stage', stage],
        'git_commit': admission['git_commit'], 'plan': PLAN, 'grant': SELECTOR, 'python': sys.executable,
        'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'seeds': 'N/A deterministic'}, exclusive=True)
    status, error, details = 'PASS', None, {}
    try:
        with bounded_stage(max(1, 120 - (time.monotonic() - start))):
            f = frozen(task)
            if stage == 'prepare':
                target = attempt / 'validation'; target.mkdir()
                shutil.copyfile(ROOT / REVIEW / 'tests.xml', target / 'tests.xml')
                write(target / 'methods.json', f['native_methods'], exclusive=True)
                write(target / 'result.json', {'status': 'PASS', 'exit_code': 0,
                    'wall_seconds': read(ROOT / REVIEW / 'preparation.json')['seconds'],
                    'tests_sha256': file_hash(target / 'tests.xml'), 'original_tests': REVIEW + '/tests.xml'}, exclusive=True)
                with no_subprocess({'attempts': 0}): details = live.prepare(ROOT, attempt, historical_floor=61)
                ledger(attempt, 0)
            elif stage == 'controls':
                with no_subprocess({'attempts': 0}): details = live.controls(ROOT, attempt, ledger=ledger)
                ledger(attempt, 0)
            elif stage.startswith('route-'):
                route = stage.removeprefix('route-'); ledger(attempt, 2 * checks.ROUTES.index(route))
                details = live.route(ROOT, attempt, route, ledger=ledger)
            elif stage == 'probe':
                ledger(attempt, 10); details = live.probe(ROOT, attempt, ledger=ledger)
                ledger(attempt, 11)
            elif stage == 'verify':
                with no_subprocess({'attempts': 0}): details = evidence(attempt, task)
                write(attempt / 'verification.json', details, exclusive=True)
            else:
                details = read(attempt / 'verification.json'); ledger(attempt, 11)
                require(details['native_reservations'] == 11 and len(details['routes']) == 5, 'Incomplete matrix')
            frozen(task); size = charged(attempt)
            elapsed = read(ROOT / REVIEW / 'preparation.json')['seconds'] + sum(r['seconds'] for r in earlier) + time.monotonic() - start
            require(elapsed + 180 < 1200 and time.monotonic() - start < 120, 'Matrix time/acceptance reserve exhausted')
            if stage == 'seal':
                (attempt / 'RESULT.md').write_text('# Current native runtime matrix\n\n'
                    'All five actual current source routes reproduce original complete streams,receipts,P1-P5 and answers. '
                    'Eight prelaunch controls and the actual namespace probe passed. Eleven supervised starts were charged '
                    'after the retained native-binding lower bound61. The current452-file package stayed unchanged.\n\n'
                    '| Decision | Primary criterion | Veto | Uncertainty | Next action | Limit |\n| --- | --- | --- | --- | --- | --- |\n'
                    '| Submit current finite native evidence | Full original outputs,controls and probe passed | No drift or budget veto | Same-host finite source cohort | Independent authority record,refresh,installed lifecycles | No general legal or whole-build completion |\n\n'
                    'Post-run red team: exact source outputs can preserve interpretation errors; installed lifecycle and recovery are separate obligations.\n')
                write(attempt / 'run-manifest.json', {'git_commit': admission['git_commit'], 'plan': PLAN, 'result': name + '/RESULT.md',
                    'commands': [read(attempt / 'stages' / s / 'started.json') for s in STAGES], 'environment': sys.executable,
                    'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'seeds': 'N/A deterministic', 'methods': f['methods'],
                    'data_version': f['inputs'], 'cumulative_seconds': elapsed, 'cumulative_unique_bytes': size,
                    'historical_unmeasured_seconds': 'UNKNOWN'}, exclusive=True)
                write(attempt / 'result.json', {'task': task['id'], 'status': 'PASS', 'scope': 'FINITE_CURRENT_NATIVE_EXECUTION',
                    'whole_program_complete': False}, exclusive=True)
    except BaseException as exc:
        status, error = 'FAIL', type(exc).__name__ + ': ' + str(exc)
        write(folder / 'failure.json', {'error': error, 'traceback': traceback.format_exc()}, exclusive=True)
    write(folder / 'result.json', {'status': status, 'error': error, 'seconds': time.monotonic() - start, 'details': details}, exclusive=True)
    if stage == 'seal' or status == 'FAIL':
        if not (attempt / 'result.json').exists(): write(attempt / 'result.json', {'task': task['id'], 'status': 'FAIL', 'error': error}, exclusive=True)
        write(attempt / 'outputs.json', {str(p.relative_to(attempt)): file_hash(p) for p in sorted(attempt.rglob('*'))
              if p.is_file() and p.name not in {'outputs.json', 'admission.json'}}, exclusive=True)
    print(json.dumps({'stage': stage, 'status': status, 'error': error, 'seconds': time.monotonic() - start}))
    return int(status != 'PASS')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('action', choices=['prepare', 'run'])
    parser.add_argument('--attempt'); parser.add_argument('--stage', choices=STAGES); args = parser.parse_args()
    if args.action == 'prepare': prepare()
    else:
        if not args.attempt or not args.stage: parser.error('--attempt and --stage required')
        raise SystemExit(run(args.attempt, args.stage))
