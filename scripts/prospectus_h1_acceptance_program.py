"""Bounded revision430 acceptance repair and return to original source work."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from scripts import prospectus_h1_current_acceptance as check

read, sha, require = check.read, check.sha, check.require
AUTH = ROOT / check.AUTH
WORK = ROOT / '.localresources/prospectus-preparation/h1-acceptance-lineage'
PREP = AUTH / 'reviews/h1-acceptance-lineage-430'
HERE = ROOT / check.BASE / 'attempt-067'
SELF = 'scripts/prospectus_h1_acceptance_program.py'
ADAPTER = 'scripts/prospectus_h1_current_acceptance.py'
PLAN = 'docs/plans/prospectus-h1-acceptance-lineage-2026-10-22.md'
CHANGED = ['prospectus/build_contract.py', 'prospectus/criterion_evidence.py', 'prospectus/execution_authority.py']
STAGES = ('ordinary', 'package', 'installed')
LIMITS = {'new_bytes': 192 * 1024**2, 'measured_seconds': 600, 'control_seconds': 60,
          'worker_seconds': 120, 'unchanged_retries': 0}


def rel(path):
    return str(Path(path).relative_to(ROOT))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    if path.suffix == '.gz':
        data = gzip.compress(data, mtime=0)
    limit = 32 * 1024**2 if path.suffix == '.gz' else 24 * 1024**2 if path.name == 'proposal.json' else 4 * 1024**2
    require(len(data) < limit, 'Output file ceiling')
    with path.open('xb') as stream:
        stream.write(data)


def authority():
    sys.path.insert(0, str(ROOT / 'src'))
    from legalmath.prospectus.execution_authority import Authority
    return Authority(ROOT)


def costs():
    start = read(PREP / 'accounting-start.json')
    paths = {p for folder in (WORK, PREP, HERE) if folder.exists() for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in (SELF, ADAPTER, PLAN, 'tests/prospectus/test_criterion_evidence.py'))
    paths.update(ROOT / 'src/legalmath' / n for n in CHANGED)
    paths.add(AUTH / 'revisions/0430.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    seconds = sum(read(WORK / n)['seconds'] for n in (
        'current-unit-066.json', 'candidate-tests.json', 'candidate-tests-recovery.json'))
    seconds += sum(read(p)['seconds'] for folder in (PREP, HERE) for p in folder.glob('commands/*.json')
                   if read(p).get('accounting_role') != 'NESTED')
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
            'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
            'known_cumulative_bytes': start['prior_known_bytes'] + size,
            'known_cumulative_seconds': start['prior_known_seconds'] + seconds + 60,
            'historical_manual_unmeasured_costs': 'UNKNOWN',
            'allowed': size < LIMITS['new_bytes'] - 2 * 1024**2 and seconds < 600}


def prepare():
    tick = time.monotonic()
    a = authority()
    old, tasks, _ = a.spec()
    require(old['revision'] == 429 and not PREP.exists() and not HERE.exists(), 'Fresh429required')
    require(not a.status()['running'], 'Active worker forbids controller cutover')
    require(read(WORK / 'candidate-tests-recovery.json')['status'] == 'PASS', 'Candidate tests must pass')
    from scripts import prospectus_h1_reference_closure as donor_trial
    previous = donor_trial.costs()
    save(PREP / 'accounting-start.json', {
        'prior_known_bytes': previous['known_cumulative_bytes'], 'prior_known_seconds': previous['known_cumulative_seconds'],
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'program_bytes': (AUTH / 'program.json').stat().st_size})
    baseline = check.inventory(ROOT / 'src/legalmath')
    require(baseline == read(ROOT / check.DONOR / 'package.json')['files'], 'Current source differs from066')
    candidate = check.inventory(WORK / 'candidate/src/legalmath')
    require({n for n in set(baseline) | set(candidate) if baseline.get(n) != candidate.get(n)} == set(CHANGED),
            'Unreviewed production change')
    runtime = read(AUTH / 'reviews/h1-reference-closure-429/config.json')
    require(sha(runtime['package_python']) == runtime['python_sha256']
            and sha(runtime['ordinary_python']) == runtime['ordinary_python_sha256'], 'Interpreter changed')
    inherited = read(AUTH / 'reviews/h1-reference-closure-429/freeze.json')['bindings']
    require(all(sha(ROOT / n) == h for n, h in inherited.items()), 'Donor inputs changed')
    donor = ROOT / check.DONOR
    outputs = read(donor / 'outputs.json')
    require(all(sha(donor / n) == h for n, h in outputs.items()), 'Changed sealed066')
    evidence = dict(inherited)
    evidence.update({rel(donor / n): h for n, h in outputs.items()})
    evidence[rel(donor / 'outputs.json')] = sha(donor / 'outputs.json')
    for n in (SELF, ADAPTER, PLAN, 'scripts/prospectus_h1_unit_oracle.py',
              'scripts/prospectus_h1_acceptance_lineage_audit.py', 'tests/prospectus/test_criterion_evidence.py'):
        evidence[n] = sha(ROOT / n)
    for p in WORK.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            evidence[rel(p)] = sha(p)
    evidence.update({'src/legalmath/' + n: h for n, h in candidate.items()})
    save(PREP / 'freeze.json', {'baseline_production': baseline, 'candidate_production': candidate,
        'evidence': evidence, 'runtime': runtime, 'changed_files': CHANGED, 'limits': LIMITS})
    program = deepcopy(old)
    program['revision'] = 430
    task = next(t for t in program['tasks'] if t['id'] == 'source-bes-dep-05')
    names = sorted(set(evidence) | {rel(PREP / 'freeze.json')})
    task.update(dossier=PLAN, pre_admission_review=PLAN, build_criteria_scope=[check.CRITERION],
        reason='Validate current H1 unit evidence and preserve criterion evidence across unrelated task progress',
        h1_current_unit_acceptance={'version': check.VERSION, 'freeze': rel(PREP / 'freeze.json'), 'donor': check.DONOR},
        build_criterion_lineage={check.CRITERION: {'version': 'criterion-evidence.v1', 'files': names, 'trees': ['src/legalmath']}})
    task['inputs'] = sorted(set(task['inputs']) | set(names))
    attempts = [e['attempt'] for e in a.events() if e['kind'] == 'ADMIT' and e['budget_key'] == task['budget_key']]
    require(len(attempts) == old['budgets'][task['budget_key']]['maximum_new_attempts'] == 66, 'Retain66admissions')
    program['budgets'][task['budget_key']]['maximum_new_attempts'] = 67
    from legalmath.prospectus.execution_authority import digest
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 430
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(task_sha256=digest(task), dossier=PLAN, phase=0,
                remaining='Current unit derivation checked; acceptance lifecycle requires repair; wider original source requirements open.',
                next_action='Run current ordinary/installed unit acceptance, record and refresh, then trace remaining original source requirements.',
                stop_condition='Attempt067only;192MiB,600+60seconds; no unchanged retry; original source acceptance remains open.')
    save(PREP / 'routes.json', routes)
    program['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    for n in CHANGED:
        key = 'src/legalmath/' + n
        if key in program['continuation_review']['bindings']:
            program['continuation_review']['bindings'][key] = candidate[n]
    program['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in
        (PLAN, SELF, ADAPTER, rel(PREP / 'freeze.json'), rel(PREP / 'routes.json'))})
    require(program['obligations'] == old['obligations'] and program['build_contract'] == old['build_contract'], 'Original scope changed')
    save(PREP / 'proposal.json', program)
    save(PREP / 'review.json', {'baseline': digest(old), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Criterion-specific current evidence with failed-recheck invalidation', 'Current066schema and063context adapter',
                    'Actual ordinary and isolated installed dimensional proof; original task stays open'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'candidate_tests': rel(WORK / 'candidate-tests-recovery.json'),
            'control_cutover': 'Frozen reviewed candidate only; no running worker; cutover before revision commit and admission'},
        'evidence_contract': {'question': 'Does independently checked current unit evidence survive only unrelated task progress?',
            'baseline': check.DONOR, 'primary': 'Lifecycle controls and exact current ordinary/installed answer with original dimensional oracle',
            'promotion_veto': ['Changed proof or origin', 'False acceptance', 'Older success after failed recheck'],
            'continuation_veto': ['Invalid authority', 'Corrupt shared source', 'Exhausted reservation'],
            'explanatory': ['Test count', 'Runtime'], 'not_concluded': ['Original task completion', 'Source authenticity', 'Intended unit', 'Whole build']},
        'budget_revision': {'budget_key': task['budget_key'], 'previous_maximum': 66, 'new_maximum': 67,
            'retained_attempts': attempts, 'reason': 'Reproduced acceptance schema and latest-event invalidation defects',
            'next_discriminating_check': 'Current delivery plus tested persistent criterion lifecycle', 'stop_condition': LIMITS,
            'same_scope_authorization': 'Recover and continue the prospectus build'}})
    save(PREP / 'commands/preparation.json', {'seconds': time.monotonic() - tick, 'argv': [SELF, 'prepare']})
    forecast = costs()['new_bytes'] + 3 * sum((ROOT / 'src/legalmath' / n).stat().st_size for n in baseline)
    forecast += 3 * (PREP / 'proposal.json').stat().st_size + 4 * (donor / 'ordinary-answer.json.gz').stat().st_size
    require(forecast < 190 * 1024**2 and costs()['allowed'], 'Reservation forecast exceeded')
    return {'status': 'PREPARED', 'revision': 430, 'forecast_bytes': forecast, 'resources': costs()}


def cutover():
    a = authority()
    from legalmath.prospectus.execution_authority import digest
    require(digest(a.spec()[0]) == read(PREP / 'review.json')['baseline'] and not a.status()['running'], 'Cutover baseline changed')
    frozen = read(PREP / 'freeze.json')
    require(check.inventory(ROOT / 'src/legalmath') == frozen['baseline_production'], 'Cutover source changed')
    require(check.inventory(WORK / 'candidate/src/legalmath') == frozen['candidate_production'], 'Candidate changed')
    for name in CHANGED:
        shutil.copyfile(WORK / 'candidate/src/legalmath' / name, ROOT / 'src/legalmath' / name)
    require(check.inventory(ROOT / 'src/legalmath') == frozen['candidate_production'], 'Cutover differs')
    save(PREP / 'cutover.json', {'status': 'PASS', 'changed': CHANGED, 'revision_to_commit': 430})
    return {'status': 'CUTOVER_COMPLETE_REVISION_REQUIRED'}


def environment():
    return {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONNOUSERSITE': '1', 'PYTHONPATH': '', 'PIP_NO_INDEX': '1',
            'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'PIP_NO_CACHE_DIR': '1'}


def command(name, argv, *, nested=False, timeout=120):
    require(costs()['allowed'] and costs()['new_measured_seconds'] + timeout < 600, 'Reservation exhausted')
    folder = HERE / 'commands'
    folder.mkdir(exist_ok=True)
    tick = time.monotonic()
    env = environment()
    from legalmath.prospectus.execution_authority import process_identity
    with (folder / (name + '.log')).open('x') as log:
        process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        save(folder / (name + '-started.json'), {'argv': argv, 'identity': process_identity(process.pid),
             'at': datetime.now(timezone.utc).isoformat(), 'seconds': 0})
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            code = -1
    save(folder / (name + '.json'), {'argv': argv, 'exit_code': code, 'seconds': time.monotonic() - tick,
         'accounting_role': 'NESTED' if nested else 'MEASURED',
         'environment': {k: env[k] for k in ('CUDA_VISIBLE_DEVICES', 'PYTHONPATH', 'PIP_NO_INDEX')}})
    require(code == 0, 'Inspect retained ' + name + '.log')
    require(costs()['allowed'], 'Post-command reservation exceeded')


def stage(name):
    a = authority()
    program, tasks, _ = a.spec()
    task = tasks['source-bes-dep-05']
    admission = read(HERE / 'admission.json')
    require(program['revision'] == 430 and admission['binding'] == a.binding(task), 'Current430admission required')
    require(next(e for e in reversed(a.events()) if e.get('task') == task['id'])['kind'] == 'ADMIT', 'Attempt already terminal')
    for prior in STAGES[:STAGES.index(name)]:
        require(read(HERE / 'commands' / (prior + '.json'))['exit_code'] == 0, 'Predecessor failed')
    frozen = read(PREP / 'freeze.json')
    python = frozen['runtime']['package_python' if name == 'installed' else 'ordinary_python']
    command(name, [python, '-I', '-B', str(ROOT / SELF), 'worker', '--kind', name])
    return {'stage': name, 'status': 'PASS', 'resources': costs()}


def worker(kind):
    frozen = read(PREP / 'freeze.json')
    if kind == 'package':
        authority()  # Local packaging supervisor uses the reviewed controller only.
        source = HERE / 'package-source'
        source.mkdir()
        shutil.copyfile(ROOT / 'pyproject.toml', source / 'pyproject.toml')
        shutil.copytree(ROOT / 'src', source / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
        python = frozen['runtime']['package_python']
        command('wheel', [python, '-I', '-B', '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
            '--no-index', '--wheel-dir', str(HERE / 'wheel'), str(source)], nested=True, timeout=60)
        wheels = list((HERE / 'wheel').glob('*.whl'))
        require(len(wheels) == 1, 'Exactly one wheel required')
        command('install', [python, '-I', '-B', '-m', 'pip', 'install', '--no-index', '--no-deps', '--no-compile',
            '--target', str(HERE / 'installed'), str(wheels[0])], nested=True, timeout=60)
        require(check.inventory(HERE / 'installed/legalmath') == frozen['candidate_production'], 'Installed inventory differs')
        save(HERE / 'package.json', {'status': 'PASS', 'files': frozen['candidate_production'],
            'wheel': {'path': rel(wheels[0]), 'sha256': sha(wheels[0])}})
    else:
        target = ROOT / 'src' if kind == 'ordinary' else HERE / 'installed'
        sys.path.insert(0, str(target))
        products, profiles = check.inputs(ROOT)
        answer = check.consume(ROOT, products, profiles)
        require(answer == read(ROOT / check.DONOR / 'ordinary-answer.json.gz'), 'Complete066answer changed')
        evaluation = check.proof(ROOT, answer, adverse=True)
        path = HERE / (kind + '-answer.json.gz')
        save(path, answer)
        save(HERE / (kind + '.json'), {'status': 'PASS', 'answer_sha256': sha(path), 'evaluation': evaluation,
            'imports': check.imported(target), 'isolated': sys.flags.isolated == 1,
            'executable': str(Path(sys.executable).resolve()), 'prefix': sys.prefix})
    return {'worker': kind, 'status': 'PASS'}


def seal():
    a = authority()
    for name in STAGES:
        require(read(HERE / 'commands' / (name + '.json'))['exit_code'] == 0, 'Required stage missing')
    require(costs()['allowed'], 'Reservation exhausted')
    admission = read(HERE / 'admission.json')
    save(HERE / 'run-manifest.json', {'git_commit': admission['git_commit'], 'plan': PLAN,
        'command': SELF + ' stage --kind ordinary|package|installed; seal; authority record/refresh',
        'commands': {n: read(HERE / 'commands' / (n + '.json')) for n in STAGES},
        'environment': read(PREP / 'freeze.json')['runtime'], 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',
        'data_version': check.DONOR, 'random_seeds': 'N/A; deterministic source proof',
        'wall_seconds': costs()['new_measured_seconds'], 'artifacts': rel(HERE), 'resources': costs()})
    save(HERE / 'result.json', {'status': 'PASS', 'task': 'source-bes-dep-05', 'candidate_passed': True,
        'original_task_complete': False, 'whole_program_complete': False, 'criteria_submitted': [check.CRITERION],
        'scope': 'FINITE_CURRENT_UNIT_EVIDENCE_AND_ACCEPTANCE_LIFECYCLE', 'resources': costs()})
    (HERE / 'RESULT.md').write_text(
        '# Current H1 unit acceptance and evidence persistence\n\n'
        'The current ordinary and isolated installed answers exactly preserve066. '
        'The independent original-source oracle verifies the printed1000scale ratio '
        'and unknown dash; seven altered outputs/bindings are refused in each environment. '
        'The controller candidate passed its lifecycle and legacy tests. The first '
        'test collection failed on a local fixture import and the changed recovery passed.\n\n'
        '|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n'
        '|---|---|---|---|---|---|\n'
        '|Submit named criterion|Current full answers and independent proof pass|No candidate veto remains|'
        'Source authority and intended unit unresolved|Record and refresh; return to original source requirements|'
        'Whole source, whole build, financial equality or legal truth|\n\n'
        'The binding closure includes the complete production inventory and donor source/method evidence. '
        'This conservatively invalidates evidence on any production change; it does not infer semantic independence. '
        'Historical results remain sealed. External adviser opinion is not required.\n')
    save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts and p.name != 'outputs.json'})
    return {'status': 'SEALED', 'attempt': rel(HERE), 'resources': costs()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'cutover', 'stage', 'worker', 'seal', 'costs'])
    parser.add_argument('--kind', choices=STAGES)
    args = parser.parse_args()
    result = stage(args.kind) if args.action == 'stage' else worker(args.kind) if args.action == 'worker' else globals()[args.action]()
    print(json.dumps(result), flush=True)
