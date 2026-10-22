"""Retained actual-answer reproduction for strict JSON reasoning acceptance."""
import argparse
from copy import deepcopy
import gzip
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
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.dont_write_bytecode = True
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash, digest
from scripts import prospectus_reasoning_acceptance as prior
from scripts.prospectus_reasoning_acceptance_evidence import verify, load, same, require

REVIEW = REL + '/reviews/reasoning-type-repair-262'
PLAN = 'docs/plans/prospectus-reasoning-type-repair-2026-10-18.md'
SCRIPT = 'scripts/prospectus_reasoning_type_repair.py'
TARGET = REL + '/attempts/reasoning-corpus/attempt-010'
ATTEMPT = REL + '/attempts/reasoning-corpus/attempt-011'
PROPOSAL = REL + '/proposals/reasoning-type-repair-262.json'
ROUTES = REL + '/closure-routes-2026-10-18-reasoning-type-repair-262.json'


def attack(root, source):
    baseline = verify(root, source)
    with tempfile.TemporaryDirectory(prefix='prospectus-json-type-') as folder:
        target = Path(folder) / 'evidence'
        shutil.copytree(source, target)
        size = sum(p.stat().st_size for p in target.rglob('*') if p.is_file())
        require(size < 8 * 1024**2, 'Diagnostic temporary storage ceiling')
        record_path = target / 'explanations/original/notice-other-proof.json.gz'
        record = load(record_path)
        before = file_hash(record_path)
        field = record['answers']['current']['questions']['Q3']['value']['Q1']
        require(field['complete'] is False, 'Wrong original complete-answer attack baseline')
        field['complete'] = 0
        record_path.write_bytes(gzip.compress(json.dumps(record, sort_keys=True, ensure_ascii=False,
            allow_nan=False).encode(), mtime=0))
        refused, reason = False, None
        try:
            changed = verify(root, target)
            same(changed, baseline, 'diagnostic unchanged summary')
        except ValueError as error:
            refused, reason = True, str(error)
        return {'field': 'answers/current/questions/Q3/value/Q1/complete', 'original_type': 'bool',
                'mutated_type': 'int', 'original_sha256': before, 'mutated_sha256': file_hash(record_path),
                'temporary_bytes': size, 'refused': refused, 'reason': reason,
                'baseline': baseline, 'scope': 'ACCEPTANCE_HELPER; no production output changed'}


def reproduce():
    tick = time.monotonic()
    folder = ROOT / REVIEW; folder.mkdir(parents=True, exist_ok=False)
    before = folder / 'before'; before.mkdir()
    for name in (prior.SCRIPT, prior.EVIDENCE, prior.TEST):
        shutil.copyfile(ROOT / name, before / Path(name).name)
    diagnostic = attack(ROOT, ROOT / TARGET / 'source')
    write(folder / 'reproduction.json', {**diagnostic, 'seconds': time.monotonic() - tick,
        'command': ['.venv/bin/python', '-m', 'scripts.prospectus_reasoning_type_repair', 'reproduce']}, exclusive=True)
    require(time.monotonic() - tick < 30, 'Diagnostic time ceiling')
    print(json.dumps({k: diagnostic[k] for k in ('field', 'refused', 'reason', 'scope')}))


def cumulative(attempt=None):
    base = ROOT / TARGET
    seconds = read(ROOT / prior.REVIEW / 'preparation.json')['seconds']
    seconds += sum(read(p)['seconds'] for p in (base / 'stages').glob('*/result.json'))
    seconds += read(ROOT / REVIEW / 'reproduction.json')['seconds']
    preparation = ROOT / REVIEW / 'preparation.json'
    if preparation.exists(): seconds += read(preparation)['seconds']
    if attempt is not None:
        seconds += sum(read(p)['seconds'] for p in (attempt / 'stages').glob('*/result.json'))
    paths = {ROOT / n for n in (PLAN, SCRIPT, PROPOSAL, ROUTES, REL + '/revisions/0262.json')}
    paths |= {p for p in (ROOT / REVIEW).rglob('*') if p.is_file()}
    if attempt is not None: paths |= {p for p in attempt.rglob('*') if p.is_file()}
    size = prior.storage(base) + sum(p.stat().st_size for p in paths if p.is_file())
    require(size + prior.BOUNDS['reserve_bytes'] < prior.BOUNDS['new_bytes'], 'Cumulative261/262 storage ceiling')
    require(seconds < prior.BOUNDS['incremental_seconds'], 'Cumulative261/262 time ceiling')
    return {'known_seconds_261plus': seconds, 'retained_bytes_261plus': size,
            'pre261_unmeasured_seconds': 'UNKNOWN'}


def prepare():
    tick = time.monotonic(); folder = ROOT / REVIEW
    write(folder / 'prepare-started.json', {'command': ['.venv/bin/python', '-m',
        'scripts.prospectus_reasoning_type_repair', 'prepare']}, exclusive=True)
    try:
        auth = Authority(ROOT); old, tasks, _ = auth.spec()
        require(old['revision'] == 261, 'Wrong repair baseline')
        require(read(folder / 'reproduction.json')['refused'] is False, 'No reproduced acceptance defect')
        task = tasks['reasoning-corpus']
        accepted = next(e for e in reversed(auth.events()) if e.get('attempt') == TARGET and e['kind'] == 'ACCEPT')
        require(auth.retained_evidence_valid(accepted), 'Historical010 evidence changed')
        argv = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', prior.TEST,
                '--junitxml=' + str(folder / 'tests.xml')]
        with (folder / 'tests.log').open('xb') as out:
            result = subprocess.run(argv, cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src'),
                'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTHONDONTWRITEBYTECODE': '1'},
                stdout=out, stderr=subprocess.STDOUT, timeout=60)
        require(result.returncode == 0, 'Typed-equality tests failed')
        repaired = attack(ROOT, ROOT / TARGET / 'source')
        require(repaired['refused'] and 'mismatch' in repaired['reason'], 'Actual complete-answer attack still accepted')
        write(folder / 'repaired-control.json', repaired, exclusive=True)
        diff = subprocess.run(['git', 'diff', '--no-index', '--',
            str(folder / 'before' / Path(prior.EVIDENCE).name), str(ROOT / prior.EVIDENCE)],
            cwd=ROOT, capture_output=True, timeout=10)
        require(diff.returncode in (0, 1), 'Cannot retain actual comparison-helper diff')
        (folder / 'helper.diff').write_bytes(diff.stdout)
        inputs = set(task['inputs']) | {TARGET + '/outputs.json'}
        inputs.update(TARGET + '/' + n for n in read(ROOT / TARGET / 'outputs.json'))
        inputs.update(str(p.relative_to(ROOT)) for p in folder.rglob('*') if p.is_file())
        bound = {**prior.methods(task), PLAN: file_hash(ROOT / PLAN), SCRIPT: file_hash(ROOT / SCRIPT)}
        frozen = {'methods': bound, 'inputs': {n: file_hash(ROOT / n) for n in sorted(inputs)},
            'package': prior.package_files(ROOT / 'src/legalmath'), 'runtime': prior.runtime_files(),
            'history': prior.history(auth)}
        same(frozen['package'], read(ROOT / TARGET / 'source-package.json'), 'production unchanged')
        write(folder / 'frozen.json', frozen, exclusive=True)
        new = deepcopy(old); new['revision'] = 262
        current = next(t for t in new['tasks'] if t['id'] == 'reasoning-corpus')
        current.update(dossier=PLAN, reason='Repair reproduced Boolean/integer confusion in complete-answer acceptance; preserve actual010 outputs',
            evidence_attempt=TARGET, reasoning_acceptance={'version': 'conditional-reasoning-current.v1',
                'review': REVIEW, 'bounds': prior.BOUNDS})
        current['inputs'] = sorted(inputs | set(bound) | {REVIEW + '/frozen.json', REVIEW + '/preparation.json'})
        admissions = [e['attempt'] for e in auth.events() if e['kind'] == 'ADMIT' and e['budget_key'] == current['budget_key']]
        require(len(admissions) == old['budgets'][current['budget_key']]['maximum_new_attempts'] == 10, 'Wrong original allowance')
        new['budgets'][current['budget_key']]['maximum_new_attempts'] = 11
        routes = read(ROOT / old['continuation_review']['routes']); routes['baseline_revision'] = 262
        row = next(r for r in routes['tasks'] if r['task'] == 'reasoning-corpus')
        row.update(task_sha256=digest(current), dossier=PLAN,
            remaining='Exact JSON-type evidence repair after actual False-to0 mutation was accepted',
            next_action='Revalidate immutable010 with repaired typed comparison and fresh current replay; record then continue source-authority.')
        write(ROOT / ROUTES, routes, exclusive=True)
        new['continuation_review'].update(plan=PLAN, routes=ROUTES)
        for name in (PLAN, SCRIPT, prior.SCRIPT, prior.EVIDENCE, ROUTES):
            new['continuation_review']['bindings'][name] = file_hash(ROOT / name)
        write(folder / 'preparation.json', {'seconds': time.monotonic() - tick, 'test_argv': argv,
            'retained_accept_event': accepted['sha256'], 'retained_admissions': admissions,
            'production_package_unchanged': True, 'repaired_attack_refused': True}, exclusive=True)
        review = {'baseline': digest(old), 'changes': current['reason'], 'scope_unchanged': True, 'budget_unchanged': False,
            'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'actual_defect': REVIEW + '/reproduction.json',
                'repair_evidence': REVIEW + '/repaired-control.json', 'production': 'Unchanged; reuse exact installed package'},
            'evidence_contract': {'question': 'Does actual complete-answer acceptance preserve JSON types?',
                'baseline': TARGET, 'primary': 'Typed original equality, actual complete-answer forgery refusal and current complete replay',
                'veto': 'Wrong source, missing case, unchecked method, installed drift, permissive forgery or cumulative resource limit',
                'explanatory': ['counts', 'time'], 'not_concluded': ['legal meaning', 'whole build', 'package defect']},
            'budget_revision': {'budget_key': current['budget_key'], 'previous_maximum': 10, 'new_maximum': 11,
                'retained_attempts': admissions, 'reason': current['reason'],
                'next_discriminating_check': 'Actual repaired validator on sealed010 plus current complete replay and numeric-type mutation',
                'stop_condition': 'Original261/262 cumulative720seconds/128MiB; no reset or unchanged retry',
                'same_scope_authorization': 'User-authorized general build and repair of reproduced validation defects'}}
        auth.validate_program(new)
        write(ROOT / PROPOSAL, new, exclusive=True); write(folder / 'review.json', review, exclusive=True)
        require(time.monotonic() - tick < 90, 'Repair preparation ceiling')
        print(json.dumps({'prepared_revision': 262, 'actual_attack_refused': True, **cumulative()}))
    except BaseException as error:
        write(folder / 'preparation-failure.json', {'error': str(error), 'traceback': traceback.format_exc(),
            'seconds': time.monotonic() - tick}, exclusive=True)
        raise


def run():
    tick = time.monotonic(); auth = Authority(ROOT); program, tasks, _ = auth.spec()
    task = tasks['reasoning-corpus']; attempt = ROOT / ATTEMPT
    admission = read(attempt / 'admission.json')
    require(admission['program_sha256'] == digest(program) and admission['binding'] == auth.binding(task)
        and admission['task_spec'] == task, 'Repair admission changed')
    latest = next(e for e in reversed(auth.events()) if e.get('task') == 'reasoning-corpus')
    require(latest['kind'] == 'ADMIT' and latest['attempt'] == ATTEMPT, 'Repair admission inactive')
    stage = attempt / 'stages/validate'; stage.mkdir(parents=True, exist_ok=False)
    write(stage / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_reasoning_type_repair', 'run'],
        'plan': PLAN, 'at': prior.now()}, exclusive=True)
    status, error, details = 'PASS', None, {}
    def expired(*args): raise TimeoutError('Typed acceptance stage ceiling')
    signal.signal(signal.SIGALRM, expired); signal.alarm(110)
    try:
        details = prior.verification(ROOT / TARGET, task, replay=True)
        control = attack(ROOT, ROOT / TARGET / 'source')
        require(control['refused'], 'Actual complete-answer type forgery accepted')
        same(control, read(ROOT / REVIEW / 'repaired-control.json'), 'repaired control repeat')
        write(attempt / 'type-control.json', control, exclusive=True)
        write(attempt / 'verification.json', details, exclusive=True)
        write(attempt / 'result.json', {'task': 'reasoning-corpus', 'status': 'PASS', 'scope': 'FINITE_ENGINEERING_ONLY',
            'source_meaning_proved': False, 'whole_program_complete': False, 'retained_evidence': TARGET}, exclusive=True)
        require(prior.validate_submission(ROOT, attempt, task), 'Actual repaired acceptance boundary failed')
        total = cumulative(attempt)
        require(total['known_seconds_261plus'] + time.monotonic() - tick < 720, 'Repair cumulative ceiling')
        (attempt / 'RESULT.md').write_text('# Exact typed reasoning evidence accepted for review\n\n'
            'The actual complete-answer checker previously accepted False changed to0 in Q3 coverage. '
            'Canonical JSON comparison now rejects that mutation. The unchanged original complete evidence and '
            'fresh current replay pass; the original installed package matches current production. '
            'The defect was in our new acceptance helper, not the reasoning package or a source interpretation.\n\n'
            '| Decision | Primary criterion | Veto | Uncertainty | Next action | Not concluded |\n'
            '| --- | --- | --- | --- | --- | --- |\n'
            '| Submit corrected finite acceptance | Exact typed equality, actual attack refusal and current replay pass | None observed | Supplied source interpretations and wider domain | Record, refresh, source-authority | Whole build or legal truth |\n\n'
            'Historical010 remains sealed. A different untested acceptance attack remains the strongest alternative risk; '
            'an accepted malformed complete record would overturn this boundary result.\n')
        write(attempt / 'run-manifest.json', {'git_commit': admission['git_commit'], 'plan': PLAN,
            'result': ATTEMPT + '/RESULT.md', 'command': ['.venv/bin/python', '-m', 'scripts.prospectus_reasoning_type_repair', 'run'],
            'python': sys.executable, 'runtime': str(prior.runtime()), 'random_seeds': 'Z3 random_seed=0; deterministic corpus',
            'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'data_version': file_hash(ROOT / REVIEW / 'frozen.json'),
            'prior_accepted_evidence': TARGET, 'new_wall_seconds': time.monotonic() - tick, **total}, exclusive=True)
    except BaseException as exc:
        status, error = 'FAIL', type(exc).__name__ + ': ' + str(exc)
        write(stage / 'failure.json', {'error': error, 'traceback': traceback.format_exc()}, exclusive=True)
        if not (attempt / 'result.json').exists():
            write(attempt / 'result.json', {'task': 'reasoning-corpus', 'status': 'FAIL', 'error': error}, exclusive=True)
    finally:
        signal.alarm(0)
        write(stage / 'result.json', {'status': status, 'error': error, 'seconds': time.monotonic() - tick}, exclusive=True)
    write(attempt / 'outputs.json', {str(p.relative_to(attempt)): file_hash(p) for p in sorted(attempt.rglob('*'))
        if p.is_file() and p.name != 'admission.json'}, exclusive=True)
    print(json.dumps({'status': status, 'error': error, **cumulative(attempt)}))
    return 0 if status == 'PASS' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('reproduce', 'prepare', 'run'))
    args = parser.parse_args()
    if args.action == 'reproduce': reproduce(); return 0
    if args.action == 'prepare': prepare(); return 0
    return run()


if __name__ == '__main__':
    raise SystemExit(main())
