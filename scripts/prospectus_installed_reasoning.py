"""Reviewed, bounded installed reasoning continuation under the sole authority."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
from legalmath.prospectus.execution_authority import Authority, REL, read, write, digest, file_hash
from scripts.prospectus_installed_reasoning_evidence import EXPLANATIONS, NOTICE, STAGES, require, verify_retained
from scripts.prospectus_component_revalidation import package_files, runtime, runtime_files

PLAN = 'docs/plans/prospectus-installed-explanations-2026-10-17.md'
NEXT_PLAN = 'docs/plans/prospectus-post-repair-runtime-2026-10-17.md'
SCRIPT = 'scripts/prospectus_installed_reasoning.py'
WORKER = 'scripts/prospectus_installed_reasoning_worker.py'
TEST = 'tests/prospectus/test_installed_reasoning.py'
DONOR = REL + '/attempts/source-bes-dep-06/attempt-013'
ALL_STAGES = (*STAGES, 'verify', 'seal')
BOUNDS = {'stage_seconds': 110, 'preparation_seconds': 60, 'incremental_seconds': 600,
          'new_bytes': 64 * 1024**2, 'reserve_bytes': 2 * 1024**2, 'native_calls': 0, 'gpu_calls': 0}
SUPPORT = [PLAN, NEXT_PLAN, SCRIPT, WORKER, TEST, 'scripts/prospectus_installed_reasoning_evidence.py',
           'scripts/prospectus_component_installed_worker.py', 'scripts/prospectus_component_revalidation.py',
           'scripts/prospectus_component_evidence.py', 'scripts/prospectus_explanation_evidence.py',
           'scripts/prospectus_explanation_oracle.py', 'scripts/prospectus_calendar_evidence.py',
           'scripts/prospectus_calendar_oracle.py', 'scripts/prospectus_agent_window_evidence.py',
           'scripts/prospectus_agent_window_prepare.py']


def methods():
    paths = {str(p.relative_to(ROOT)) for p in (ROOT / 'src/legalmath').rglob('*')
             if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    return {n: file_hash(ROOT / n) for n in sorted(paths | set(SUPPORT))}


def history(auth):
    rows = []
    for name in (EXPLANATIONS, NOTICE, DONOR):
        event = next(e for e in reversed(auth.events()) if e.get('attempt') == name and e['kind'] in {'RECORD', 'ACCEPT'})
        require(auth.retained_evidence_valid(event), 'Original evidence changed: ' + name)
        rows.append({'attempt': name, 'event_sha256': event['sha256'], 'outputs_sha256': event['outputs_sha256']})
    return rows


def preparation():
    tick = time.monotonic()
    auth = Authority(ROOT); old, tasks, _ = auth.spec()
    revision = old['revision'] + 1
    review_name = REL + '/reviews/installed-reasoning-' + str(revision)
    folder = ROOT / review_name; folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_installed_reasoning', 'prepare'],
        'at': datetime.now(timezone.utc).isoformat()}, exclusive=True)
    def expired(*args): raise TimeoutError('Installed reasoning preparation ceiling')
    signal.signal(signal.SIGALRM, expired); signal.alarm(max(1, int(60 - (time.monotonic() - tick))))
    try:
        task = tasks['reasoning-corpus']
        retained = history(auth)
        package = package_files(ROOT / 'src/legalmath')
        require(len(package) == 452 and package == read(ROOT / DONOR / 'source-package.json')
                == package_files(ROOT / DONOR / 'installed/legalmath'), 'Shared package changed')
        inputs = set(task['inputs'])
        for name in (EXPLANATIONS, NOTICE, DONOR):
            inputs.update(name + '/' + n for n in read(ROOT / name / 'outputs.json'))
            inputs.add(name + '/outputs.json')
        bound = methods()
        # Original source/support inputs are checked through the current
        # admission plus the unchanged original event/output manifests.
        command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', TEST,
                   '--junitxml=' + str(folder / 'tests.xml')]
        with (folder / 'tests.log').open('xb') as out:
            result = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src'),
                'PYTHONDONTWRITEBYTECODE': '1'}, stdout=out, stderr=subprocess.STDOUT,
                timeout=max(1, 55 - (time.monotonic() - tick)))
        require(result.returncode == 0, 'Installed reasoning harness tests failed')
        from legalmath.prospectus.execution_acceptance import checked_tests
        tests = checked_tests(folder / 'tests.xml', 2)
        frozen = {'methods': bound, 'inputs': {n: file_hash(ROOT / n) for n in sorted(inputs)},
                  'package': package, 'runtime_files': runtime_files(), 'history': retained}
        write(folder / 'frozen.json', frozen, exclusive=True)
        admissions = [e['attempt'] for e in auth.events() if e['kind'] == 'ADMIT' and e['budget_key'] == task['budget_key']]
        before = old['budgets'][task['budget_key']]['maximum_new_attempts']
        require(len(admissions) == before == 8, 'Unexpected cumulative reasoning history')
        expected = REL + '/attempts/reasoning-corpus/attempt-009'
        preparation_result = {'tests': tests,
            'test_command': command, 'expected_attempt': expected, 'revision': revision,
            'retained_admissions': admissions, 'historical_unmeasured_seconds': 'UNKNOWN'}
        new = deepcopy(old); new['revision'] = revision
        current = next(t for t in new['tasks'] if t['id'] == task['id'])
        current.update(dossier=PLAN, reason='Execute118 complete source-bound installed answers and4096 independent explanation checks from the frozen452-file package',
            installed_reasoning={'version': 'installed-reasoning.v1', 'review': review_name, 'donor': DONOR, 'bounds': BOUNDS},
            timeout_seconds=120)
        current['inputs'] = sorted(inputs | set(bound) | {review_name + '/preparation.json'} |
                                  {str(p.relative_to(ROOT)) for p in folder.iterdir() if p.is_file()})
        new['budgets'][task['budget_key']]['maximum_new_attempts'] = before + 1
        routes = read(ROOT / old['continuation_review']['routes']); routes['baseline_revision'] = revision
        for row in routes['tasks']:
            if row['task'] == task['id']:
                row.update(task_sha256=digest(current), dossier=PLAN, phase=0, mode='local',
                    remaining=current['reason'], next_action='Execute bounded installed stages, independently verify full evidence, record/refresh; follow ' + NEXT_PLAN,
                    stop_condition=BOUNDS)
        route_name = REL + '/closure-routes-2026-10-17-installed-reasoning-' + str(revision) + '.json'
        write(ROOT / route_name, routes, exclusive=True)
        new['continuation_review'].update(plan=PLAN, routes=route_name)
        for name in (PLAN, NEXT_PLAN, SCRIPT, route_name):
            new['continuation_review']['bindings'][name] = file_hash(ROOT / name)
        review = {'baseline': digest(old), 'changes': current['reason'], 'scope_unchanged': True, 'budget_unchanged': False,
            'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'source_identity': 'Replay original paths; do not regenerate notice sources',
                'package_freeze': 'No production or shared-method changes', 'partial': 'No original task or build completion'},
            'evidence_contract': {'question': 'Do new paths execute correctly from the actual installed package?',
                'baseline': retained, 'primary': '118 complete original answers and4096 complete cases plus independent proof/arithmetic and all original refusals',
                'veto': 'Changed inputs/methods/imports, output inequality, permissive controls, missing cases or exhausted bound',
                'explanatory': ['counts', 'runtime'], 'not_concluded': ['legal truth', 'whole task', 'unseen coverage', 'portability']},
            'budget_revision': {'budget_key': task['budget_key'], 'previous_maximum': before, 'new_maximum': before + 1,
                'retained_attempts': admissions, 'reason': current['reason'],
                'next_discriminating_check': 'Actual installed consumers and independent verification of complete retained inputs',
                'stop_condition': BOUNDS, 'same_scope_authorization': 'User-directed general build and continuation without external-adviser prerequisite'}}
        write(folder / 'preparation.json', {**preparation_result, 'seconds': time.monotonic() - tick}, exclusive=True)
        auth.validate_program(new)
        write(ROOT / REL / 'proposals' / ('installed-reasoning-' + str(revision) + '.json'), new, exclusive=True)
        write(ROOT / REL / 'proposals' / ('installed-reasoning-' + str(revision) + '-review.json'), review, exclusive=True)
        require(time.monotonic() - tick < 60, 'Preparation time ceiling')
        # Finalize timing before submission/admission freezes these new bytes.
        write(folder / 'preparation.json', {**preparation_result, 'seconds': time.monotonic() - tick})
        print(json.dumps({'prepared_revision': revision, 'attempt': expected, 'tests': tests,
                          'seconds': time.monotonic() - tick}))
    except BaseException as error:
        write(folder / 'failure.json', {'error': str(error), 'seconds': time.monotonic() - tick,
              'traceback': traceback.format_exc()}, exclusive=True)
        raise
    finally:
        signal.alarm(0)


def unchanged(task):
    selector = task['installed_reasoning']
    require(selector['version'] == 'installed-reasoning.v1' and selector['bounds'] == BOUNDS
            and selector['donor'] == DONOR, 'Wrong installed reasoning selector')
    frozen = read(ROOT / selector['review'] / 'frozen.json')
    require(frozen['methods'] == methods() and frozen['inputs'] == {n: file_hash(ROOT / n) for n in frozen['inputs']}
            and frozen['runtime_files'] == runtime_files(), 'Installed reasoning evidence drift')
    target = ROOT / DONOR / 'installed'
    require(frozen['package'] == package_files(ROOT / 'src/legalmath') == package_files(target / 'legalmath'), 'Package changed')
    wheel = read(ROOT / DONOR / 'wheel.json'); path = ROOT / DONOR / wheel['file']
    require(file_hash(path) == wheel['sha256'], 'Wheel changed')
    with zipfile.ZipFile(path) as archive:
        content = {n.removeprefix('legalmath/'): hashlib.sha256(archive.read(n)).hexdigest()
                   for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    require(content == frozen['package'], 'Wheel/source package disagreement')
    return frozen


def verify_proofs(attempt, frozen):
    target = ROOT / DONOR / 'installed'
    for stage in STAGES:
        proof = read(attempt / 'stages' / stage / 'installed-proof.json')
        command = read(attempt / 'stages' / stage / 'command.json')
        argv = [str(runtime() / 'bin/python'), '-I', '-B', str(ROOT / WORKER), str(ROOT), str(attempt), str(target), stage]
        require(command['argv'] == argv and command['timeout_seconds'] == 100 and command['cwd'] == str(attempt)
                and command['environment'] == {'PYTHONPATH': '', 'PYTHONDONTWRITEBYTECODE': '1',
                                                'CUDA_VISIBLE_DEVICES': '-1'}, 'Actual worker command differs')
        require(proof['isolated'] == 1 and proof['guard'] == {'blocked': 0}
                and Path(proof['prefix']).resolve() == runtime().resolve()
                and Path(proof['python']).resolve() == (runtime() / 'bin/python').resolve()
                and proof['package_files'] == len(frozen['package']) and proof['modules']
                and str(ROOT / 'src') not in proof['sys_path'], 'Wrong installed environment or origin')
        for name, row in proof['modules'].items():
            path = Path(row['path']).resolve()
            require(path.is_relative_to(target / 'legalmath') and row['sha256'] == file_hash(path)
                    == frozen['package'][str(path.relative_to(target / 'legalmath'))], 'Wrong installed module: ' + name)
    return {'actual_isolated_workers': len(STAGES), 'all_production_origins_verified': True}


def storage(task, attempt):
    revision = read(ROOT / task['installed_reasoning']['review'] / 'preparation.json')['revision']
    paths = [attempt, ROOT / task['installed_reasoning']['review'], *[ROOT / n for n in SUPPORT],
             ROOT / REL / 'revisions' / f'{revision:04d}.json',
             ROOT / REL / ('closure-routes-2026-10-17-installed-reasoning-' + str(revision) + '.json')]
    paths.extend((ROOT / REL / 'proposals').glob('installed-reasoning-' + str(revision) + '*.json'))
    files = set()
    for p in paths:
        files.update(q for q in p.rglob('*') if q.is_file()) if p.is_dir() else files.add(p)
    value = sum(p.stat().st_size for p in files if p.is_file())
    require(value + BOUNDS['reserve_bytes'] < BOUNDS['new_bytes'], 'Installed reasoning storage ceiling')
    return value


def run(attempt_name, stage):
    tick = time.monotonic()
    auth = Authority(ROOT); program, tasks, _ = auth.spec(); task = tasks['reasoning-corpus']
    attempt = auth.path(attempt_name); admission = read(attempt / 'admission.json')
    event = next(e for e in reversed(auth.events()) if e.get('task') == task['id'])
    require(event['kind'] == 'ADMIT' and event['attempt'] == attempt_name
            and admission['program_sha256'] == digest(program) and admission['task_spec'] == task
            and admission['binding'] == auth.binding(task), 'Unchanged installed reasoning admission required')
    require(stage in ALL_STAGES and not (attempt / 'outputs.json').exists(), 'Unknown or sealed stage')
    index = ALL_STAGES.index(stage)
    require({p.parent.name for p in (attempt / 'stages').glob('*/started.json')} ==
            {p.parent.name for p in (attempt / 'stages').glob('*/result.json')} == set(ALL_STAGES[:index]),
            'Skipped, repeated or interrupted stage')
    previous = [read(attempt / 'stages' / s / 'result.json') for s in ALL_STAGES[:index]]
    require(all(r['status'] == 'PASS' for r in previous), 'Failed predecessor')
    folder = attempt / 'stages' / stage; folder.mkdir(parents=True, exist_ok=False)
    write(folder / 'started.json', {'at': datetime.now(timezone.utc).isoformat(), 'command':
        ['.venv/bin/python', '-m', 'scripts.prospectus_installed_reasoning', 'run', '--attempt', attempt_name, '--stage', stage]}, exclusive=True)
    status = 'PASS'; error = None; details = {}
    def expired(*args): raise TimeoutError('Installed reasoning stage ceiling')
    signal.signal(signal.SIGALRM, expired); signal.alarm(max(1, int(110 - (time.monotonic() - tick))))
    try:
        frozen = unchanged(task)
        if stage == STAGES[0]:
            write(attempt / 'source-package.json', frozen['package'], exclusive=True)
        if stage in STAGES:
            argv = [str(runtime() / 'bin/python'), '-I', '-B', str(ROOT / WORKER), str(ROOT), str(attempt),
                    str(ROOT / DONOR / 'installed'), stage]
            environment = {**os.environ, 'PYTHONPATH': '', 'PYTHONDONTWRITEBYTECODE': '1',
                           'PYTHONNOUSERSITE': '1', 'PIP_NO_INDEX': '1', 'CUDA_VISIBLE_DEVICES': '-1'}
            write(folder / 'command.json', {'argv': argv, 'cwd': str(attempt), 'timeout_seconds': 100,
                  'environment': {k: environment[k] for k in ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'CUDA_VISIBLE_DEVICES')}}, exclusive=True)
            with (folder / 'stdout').open('xb') as out, (folder / 'stderr').open('xb') as err:
                result = subprocess.run(argv, cwd=attempt, env=environment, stdout=out, stderr=err, timeout=100)
            require(result.returncode == 0, 'Installed worker failed; inspect retained stderr')
            details = read(folder / 'installed-proof.json')['details']
        elif stage == 'verify':
            guard = {'blocked': 0}
            def audit(event, args):
                if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty',
                        'os.exec', 'os.posix_spawn', 'os.spawn', 'pty.spawn'}:
                    guard['blocked'] += 1
                    raise RuntimeError('Independent reasoning verification forbids process/network')
            sys.addaudithook(audit)
            require(history(auth) == frozen['history'], 'Original retained history differs')
            details = {**verify_retained(ROOT, attempt / 'installed-results'), **verify_proofs(attempt, frozen)}
            # Independently replay the controls in the checkout and require
            # complete equality with actual installed control records.
            from scripts.prospectus_installed_reasoning_evidence import controls, load
            details['controls'] = controls(ROOT, attempt / 'independent-controls')
            require(load(attempt / 'independent-controls/controls.json') == load(attempt / 'installed-results/controls.json'),
                    'Installed controls differ from independent replay')
            require(guard['blocked'] == 0, 'Forbidden verification action attempted')
            details['guard'] = guard
            write(attempt / 'verification.json', details, exclusive=True)
        else:
            details = read(attempt / 'verification.json')
            require(details['complete_answers'] == 118 and details['independent_corpus_cases'] == 4096, 'Incomplete final verification')
            verify_proofs(attempt, frozen)
        unchanged(task)
        prep = read(ROOT / task['installed_reasoning']['review'] / 'preparation.json')
        total = prep['seconds'] + sum(r['seconds'] for r in previous) + time.monotonic() - tick
        used = storage(task, attempt)
        require(total < 600, 'Installed reasoning cumulative time ceiling')
        require(time.monotonic() - tick < 110, 'Installed reasoning stage time ceiling')
        if stage == 'seal':
            (attempt / 'RESULT.md').write_text(
                '# Installed conditional explanations and notice windows\n\n'
                'The frozen452-file installation produced118 complete original answers and4096 complete explanation records. '
                'Independent Boolean and integer checks passed. Five notice attacks,18 malformed explanation inputs, '
                'eight proof forgeries and the repinned source forgery were refused. Two original refusals remain unchanged.\n\n'
                '| Decision | Primary criterion | Veto status | Uncertainty | Next action | Limit |\n'
                '| --- | --- | --- | --- | --- | --- |\n'
                '| Retain finite installed evidence | Full original equality and independent verification passed | No source/import/refusal drift | Supplied readings and unseen source coverage | Record, refresh; current native/runtime/recovery validation | Original reasoning task and whole build remain incomplete |\n\n'
                'Post-run red team: source and installed agreement can preserve an incorrect legal reading. '
                'The separate finite checkers establish conditional consequences, not legal truth or complete interpretation discovery.\n')
            write(attempt / 'run-manifest.json', {'git_commit': admission['git_commit'], 'plan': PLAN,
                'result': attempt_name + '/RESULT.md', 'python': sys.executable, 'installed_runtime': str(runtime()),
                'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'seeds': 'N/A deterministic',
                'data_version': frozen['inputs'], 'methods': frozen['methods'], 'wheel_donor': DONOR,
                'commands': [read(attempt / 'stages' / s / 'started.json') for s in ALL_STAGES],
                'cumulative_seconds': total, 'cumulative_bytes': used, 'historical_unmeasured_seconds': 'UNKNOWN'}, exclusive=True)
            write(attempt / 'result.json', {'status': 'PASS', 'task': task['id'], 'whole_task_complete': False,
                'whole_program_complete': False, 'scope': 'INSTALLED_FINITE_CONDITIONAL_REASONING', 'verification': details}, exclusive=True)
    except BaseException as exc:
        status, error = 'FAIL', type(exc).__name__ + ': ' + str(exc)
        write(folder / 'failure.json', {'error': error, 'traceback': traceback.format_exc()}, exclusive=True)
    finally:
        signal.alarm(0)
    write(folder / 'result.json', {'status': status, 'error': error, 'seconds': time.monotonic() - tick, 'details': details}, exclusive=True)
    if stage == 'seal' or status == 'FAIL':
        if status == 'FAIL' and not (attempt / 'result.json').exists():
            write(attempt / 'result.json', {'status': 'FAIL', 'task': task['id'], 'error': error}, exclusive=True)
        write(attempt / 'outputs.json', {str(p.relative_to(attempt)): file_hash(p) for p in sorted(attempt.rglob('*'))
              if p.is_file() and p.name not in {'outputs.json', 'admission.json'}}, exclusive=True)
    print(json.dumps({'stage': stage, 'status': status, 'seconds': time.monotonic() - tick, 'error': error}))
    return int(status != 'PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run'])
    parser.add_argument('--attempt'); parser.add_argument('--stage', choices=ALL_STAGES)
    args = parser.parse_args()
    if args.action == 'prepare': return preparation()
    if not args.attempt or not args.stage: parser.error('--attempt and --stage required')
    return run(args.attempt, args.stage)


if __name__ == '__main__':
    raise SystemExit(main())
