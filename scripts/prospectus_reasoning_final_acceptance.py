"""Complete the reviewed typed-evidence and nonunique-witness repair."""
from copy import deepcopy
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
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash, digest
from scripts import prospectus_reasoning_acceptance as base
from scripts.prospectus_reasoning_type_repair import attack
from scripts.prospectus_reasoning_acceptance_evidence import same, require

REVIEW = REL + '/reviews/reasoning-witness-repair-263'
PREVIOUS = REL + '/reviews/reasoning-type-repair-262'
PLAN = 'docs/plans/prospectus-reasoning-witness-repair-2026-10-18.md'
SCRIPT = 'scripts/prospectus_reasoning_final_acceptance.py'
DIAGNOSTIC = 'scripts/prospectus_reasoning_witness_diagnostic.py'
TARGET = REL + '/attempts/reasoning-corpus/attempt-010'
FAILED = REL + '/attempts/reasoning-corpus/attempt-011'
ATTEMPT = REL + '/attempts/reasoning-corpus/attempt-012'
PROPOSAL = REL + '/proposals/reasoning-witness-repair-263.json'
ROUTES = REL + '/closure-routes-2026-10-18-reasoning-witness-repair-263.json'


def resources():
    seconds = read(ROOT / base.REVIEW / 'preparation.json')['seconds']
    seconds += sum(read(p)['seconds'] for p in (ROOT / TARGET / 'stages').glob('*/result.json'))
    seconds += read(ROOT / PREVIOUS / 'reproduction.json')['seconds']
    seconds += read(ROOT / PREVIOUS / 'preparation.json')['seconds']
    seconds += sum(read(p)['seconds'] for p in (ROOT / FAILED / 'stages').glob('*/result.json'))
    seconds += read(ROOT / REVIEW / 'diagnostic.json')['seconds']
    if (ROOT / REVIEW / 'preparation.json').exists():
        seconds += read(ROOT / REVIEW / 'preparation.json')['seconds']
    seconds += sum(read(p)['seconds'] for p in (ROOT / ATTEMPT / 'stages').glob('*/result.json'))
    paths = {ROOT / n for n in (PLAN, SCRIPT, DIAGNOSTIC, PROPOSAL, ROUTES,
        'docs/plans/prospectus-reasoning-type-repair-2026-10-18.md',
        'scripts/prospectus_reasoning_type_repair.py', REL + '/proposals/reasoning-type-repair-262.json',
        REL + '/closure-routes-2026-10-18-reasoning-type-repair-262.json',
        REL + '/revisions/0262.json', REL + '/revisions/0263.json')}
    for name in (PREVIOUS, REVIEW, FAILED, ATTEMPT):
        paths |= {p for p in (ROOT / name).rglob('*') if p.is_file()}
    size = base.storage(ROOT / TARGET) + sum(p.stat().st_size for p in paths if p.is_file())
    require(size + base.BOUNDS['reserve_bytes'] < base.BOUNDS['new_bytes'], 'Original261plus storage ceiling')
    require(seconds < base.BOUNDS['incremental_seconds'], 'Original261plus time ceiling')
    return {'measured261plus_seconds': seconds, 'retained261plus_bytes': size,
            'pre261_unmeasured_time': 'UNKNOWN'}


def prepare():
    tick = time.monotonic(); auth = Authority(ROOT); old, tasks, _ = auth.spec()
    require(old['revision'] == 262, 'Wrong active repair baseline')
    folder = ROOT / REVIEW
    write(folder / 'prepare-started.json', {'at': base.now()}, exclusive=True)
    try:
        diagnostic = read(folder / 'diagnostic.json')
        changes = [c for row in diagnostic['runs'] for c in row['changes']]
        require(changes and all(len(c['path']) >= 4 and c['path'][0] == 'cases'
            and c['path'][2] == 'result' and c['path'][3] in {'witnesses', 'unsat_core'} for c in changes),
            'Observed mismatch exceeds reviewed witness/core repair')
        failed_event = next(e for e in reversed(auth.events()) if e.get('attempt') == FAILED and e['kind'] == 'REJECT')
        require(auth.retained_evidence_valid(failed_event), 'Failed011 evidence must remain sealed')
        argv = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', base.TEST,
                '--junitxml=' + str(folder / 'tests.xml')]
        with (folder / 'tests.log').open('xb') as out:
            status = subprocess.run(argv, cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src'),
                'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'},
                stdout=out, stderr=subprocess.STDOUT, timeout=60)
        require(status.returncode == 0, 'Actual witness/stage/type controls failed')
        task = tasks['reasoning-corpus']
        inputs = set(task['inputs']) | {FAILED + '/outputs.json'}
        inputs.update(FAILED + '/' + n for n in read(ROOT / FAILED / 'outputs.json'))
        inputs.update(str(p.relative_to(ROOT)) for p in folder.rglob('*') if p.is_file())
        methods = {**base.methods(task), PLAN: file_hash(ROOT / PLAN), SCRIPT: file_hash(ROOT / SCRIPT),
                   DIAGNOSTIC: file_hash(ROOT / DIAGNOSTIC)}
        frozen = {'methods': methods, 'inputs': {n: file_hash(ROOT / n) for n in sorted(inputs)},
            'package': base.package_files(ROOT / 'src/legalmath'), 'runtime': base.runtime_files(),
            'history': base.history(auth)}
        same(frozen['package'], read(ROOT / TARGET / 'source-package.json'), 'unchanged production package')
        write(folder / 'frozen.json', frozen, exclusive=True)
        new = deepcopy(old); new['revision'] = 263
        current = next(t for t in new['tasks'] if t['id'] == 'reasoning-corpus')
        current.update(dossier=PLAN,
            reason='Accept only independently valid nonunique witnesses; preserve exact JSON types and reject failed-stage PASS results',
            evidence_attempt=TARGET, reasoning_acceptance={'version': 'conditional-reasoning-current.v1',
                'review': REVIEW, 'bounds': base.BOUNDS})
        current['inputs'] = sorted(inputs | set(methods) | {REVIEW + '/frozen.json', REVIEW + '/preparation.json'})
        admissions = [e['attempt'] for e in auth.events() if e['kind'] == 'ADMIT' and e['budget_key'] == 'reasoning-corpus']
        require(len(admissions) == old['budgets']['reasoning-corpus']['maximum_new_attempts'] == 11, 'Wrong retained allowance')
        new['budgets']['reasoning-corpus']['maximum_new_attempts'] = 12
        routes = read(ROOT / old['continuation_review']['routes']); routes['baseline_revision'] = 263
        next(r for r in routes['tasks'] if r['task'] == 'reasoning-corpus').update(task_sha256=digest(current),
            dossier=PLAN, remaining=current['reason'], next_action='Execute repaired acceptance on sealed010, record, refresh, continue source-authority.')
        write(ROOT / ROUTES, routes, exclusive=True)
        new['continuation_review'].update(plan=PLAN, routes=ROUTES)
        for name in (PLAN, SCRIPT, DIAGNOSTIC, base.SCRIPT, base.EVIDENCE, ROUTES):
            new['continuation_review']['bindings'][name] = file_hash(ROOT / name)
        write(folder / 'preparation.json', {'seconds': time.monotonic() - tick, 'test_argv': argv,
            'retained_rejection': failed_event['sha256'], 'diagnostic_changes': len(changes),
            'production_unchanged': True}, exclusive=True)
        review = {'baseline': digest(old), 'changes': current['reason'], 'scope_unchanged': True, 'budget_unchanged': False,
            'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'actual_differences': REVIEW + '/diagnostic.json',
                'bounded_equivalence': 'Only already independently verified case-level witnesses/cores; exact sources/inputs/answers retained',
                'failed_stage': '011 contradictory provisional PASS remains sealed and rejected'},
            'evidence_contract': {'question': 'Exact typed evidence with independently valid nonunique solver choices',
                'baseline': TARGET, 'primary': 'Current complete replay, independent checks, typed forgery refusal and all stages actually passed',
                'veto': 'Changed source/input/answer, false witness, failed stage, missing evidence, wrong package or cumulative ceiling',
                'explanatory': ['counts', 'time'], 'not_concluded': ['legal truth', 'whole build', 'package defect']},
            'budget_revision': {'budget_key': 'reasoning-corpus', 'previous_maximum': 11, 'new_maximum': 12,
                'retained_attempts': admissions, 'reason': current['reason'],
                'next_discriminating_check': 'Actual repaired validator and complete-answer attack with repeated within-process solver use',
                'stop_condition': 'Original261plus720seconds/128MiB,110second stages, no reset or unchanged retry',
                'same_scope_authorization': 'User-authorized continued general build and repair of actual integration failures'}}
        auth.validate_program(new); write(ROOT / PROPOSAL, new, exclusive=True)
        write(folder / 'review.json', review, exclusive=True)
        require(time.monotonic() - tick < 90, 'Preparation ceiling')
        print(json.dumps({'prepared_revision': 263, **resources()}))
    except BaseException as error:
        write(folder / 'preparation-failure.json', {'error': str(error), 'traceback': traceback.format_exc(),
              'seconds': time.monotonic() - tick}, exclusive=True)
        raise


def run():
    tick = time.monotonic(); auth = Authority(ROOT); program, tasks, _ = auth.spec()
    task = tasks['reasoning-corpus']; attempt = ROOT / ATTEMPT
    admission = read(attempt / 'admission.json')
    require(admission['program_sha256'] == digest(program) and admission['binding'] == auth.binding(task)
        and admission['task_spec'] == task, 'Unchanged actual admission required')
    latest = next(e for e in reversed(auth.events()) if e.get('task') == 'reasoning-corpus')
    require(latest['kind'] == 'ADMIT' and latest['attempt'] == ATTEMPT, 'Inactive admission')
    stage = attempt / 'stages/validate'; stage.mkdir(parents=True, exist_ok=False)
    command = ['.venv/bin/python', '-m', 'scripts.prospectus_reasoning_final_acceptance', 'run']
    write(stage / 'started.json', {'command': command, 'at': base.now()}, exclusive=True)
    status, error = 'PASS', None
    def expired(*args): raise TimeoutError('Acceptance110second ceiling')
    signal.signal(signal.SIGALRM, expired); signal.alarm(110)
    try:
        details = base.verification(ROOT / TARGET, task, replay=True)
        control = attack(ROOT, ROOT / TARGET / 'source'); require(control['refused'], 'Typed actual-answer forgery accepted')
        write(attempt / 'verification.json', details, exclusive=True)
        write(attempt / 'type-control.json', control, exclusive=True)
        write(stage / 'result.json', {'status': 'PASS', 'error': None, 'seconds': time.monotonic() - tick}, exclusive=True)
        write(attempt / 'result.json', {'task': 'reasoning-corpus', 'status': 'PASS', 'scope': 'FINITE_ENGINEERING_ONLY',
            'source_meaning_proved': False, 'whole_program_complete': False, 'retained_evidence': TARGET}, exclusive=True)
        # A second within-process replay exercises the formerly wrong comparator.
        require(base.validate_submission(ROOT, attempt, task), 'Actual acceptance failed')
        (attempt / 'RESULT.md').write_text('# Repaired conditional reasoning acceptance\n\n'
            'Current source and exact installed010 records pass independent checks. The complete-answer False-to0 '
            'attack is refused. Different valid solver witnesses are checked against their expressions and premises; '
            'all other source/input/product/answer values retain exact JSON identity. A failed or incomplete stage '
            'cannot be hidden by a provisional PASS. The failed011 and original010 evidence remain sealed.\n\n'
            '| Decision | Primary criterion | Veto status | Uncertainty | Next action | Not concluded |\n'
            '| --- | --- | --- | --- | --- | --- |\n'
            '| Submit corrected engineering acceptance | Current repeated replay and independent/typed checks pass | None observed | Supplied legal meanings and wider domain | Record, refresh, source-authority | Whole build, legal truth or unique solver witness |\n\n'
            'The failures were in our acceptance comparison and producer finalization. No package defect is established. '
            'An accepted invalid witness, changed complete answer or failed-stage result would overturn the conclusion.\n')
        write(attempt / 'run-manifest.json', {'git_commit': admission['git_commit'], 'command': command,
            'plan': PLAN, 'result': ATTEMPT + '/RESULT.md', 'python': sys.executable, 'runtime': str(base.runtime()),
            'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'random_seeds': 'Z3 random_seed=0; nonunique witnesses verified',
            'data_version': file_hash(ROOT / REVIEW / 'frozen.json'), 'retained_evidence': TARGET,
            'wall_seconds': time.monotonic() - tick}, exclusive=True)
    except BaseException as exc:
        status, error = 'FAIL', type(exc).__name__ + ': ' + str(exc)
        write(stage / 'failure.json', {'error': error, 'traceback': traceback.format_exc()}, exclusive=True)
        write(attempt / 'result.json', {'task': 'reasoning-corpus', 'status': 'FAIL', 'error': error,
            'whole_program_complete': False})
    finally:
        signal.alarm(0)
        write(stage / 'result.json', {'status': status, 'error': error, 'seconds': time.monotonic() - tick})
    totals = resources()
    write(attempt / 'resources.json', totals, exclusive=True)
    write(attempt / 'outputs.json', {str(p.relative_to(attempt)): file_hash(p) for p in sorted(attempt.rglob('*'))
        if p.is_file() and p.name != 'admission.json'}, exclusive=True)
    print(json.dumps({'status': status, 'error': error, **totals}))
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']: prepare()
    elif sys.argv[1:] == ['run']: raise SystemExit(run())
    else: raise SystemExit('Use prepare or run')
