"""Freeze, admit and retain the source09 annual-basis implementation."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts import prospectus_annual_basis_program as work
from legalmath.prospectus.execution_authority import Authority, digest, file_hash

AUTH, SOURCE, WORK, PREP, HERE = work.AUTH, work.SOURCE, work.WORK, work.PREP, work.HERE
TASK = 'source-bes-dep-09'
PARTS = ['answer', 'controls', 'public-a', 'public-b', 'public-c', 'english']
SELF = 'scripts/prospectus_annual_basis_submission.py'
SUPPORT = [SELF, work.SELF, work.READING, work.CHECKS, work.TEST, work.FIXTURE, work.OLD_FIXTURE, work.PLAN,
    'scripts/prospectus_annual_basis_source.py', 'scripts/prospectus_annual_note_index.py',
    'docs/plans/prospectus-annual-notes-roadmap-2026-10-22.md',
    'scripts/prospectus_english_applicability_program.py', 'scripts/prospectus_2010_capital_product_cases.py',
    'scripts/prospectus_2010_annual_cases.py', 'pyproject.toml']
read, save, require, inventory = work.read, work.save, work.require, work.inventory


def rel(path):
    return str(Path(path).relative_to(ROOT))


def usage():
    value = work.costs()
    extras = {ROOT / SELF, AUTH / 'revisions/0440.json'}
    if (PREP / 'start.json').exists():
        start = read(PREP / 'start.json')
        extras.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
        value['new_bytes'] += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    extras.update(p for p in (AUTH / 'reviews/annual-note-roadmap-439').rglob('*') if p.is_file())
    extras.update(ROOT / n for n in ('scripts/prospectus_annual_note_index.py',
                  'docs/plans/prospectus-annual-notes-roadmap-2026-10-22.md'))
    extras.update(p for p in (AUTH / 'reviews/english-applicability-439').glob('*')
                  if p.name in ('RECORD-RECOVERY.md', 'post-record.json', 'resume-projection.json', 'resume-projection.log'))
    value['new_bytes'] += sum(p.stat().st_size for p in extras if p.is_file())
    value['cumulative_bytes'] = read(WORK / 'preparation.json')['prior_bytes'] + value['new_bytes']
    value['allowed'] = value['allowed'] and value['new_bytes'] + 2 * 1024**2 < 128 * 1024**2 and value['cumulative_bytes'] + 2 * 1024**2 < 448 * 1024**2
    return value


def freeze():
    a = Authority(ROOT)
    old, tasks, _ = a.spec()
    require(old['revision'] == 439 and not HERE.exists() and not (PREP / 'freeze.json').exists(), 'Fresh439baseline required')
    latest = {e['task']: e for e in a.events() if e.get('task')}
    require(all(e['kind'] not in ('ADMIT', 'LAUNCH', 'START') for e in latest.values()), 'Active task exists')
    require(read(PREP / 'commands/tests.json')['exit_code'] == 0 and
            all(read(WORK / ('candidate-recovery-' + part) / 'result.json')['status'] == 'PASS' for part in PARTS),
            'Every recovered candidate segment required')
    baseline = read(PREP / 'candidate.json')
    package = inventory(WORK / 'candidate/src/legalmath')
    require(inventory(ROOT / 'src/legalmath') == baseline['baseline'] and package == baseline['candidate'], 'Candidate or baseline changed')
    require({k for k in package if package[k] != baseline['baseline'].get(k)} == {work.CHANGE} and
            package.keys() == baseline['baseline'].keys(), 'Unexpected production changes')
    save(PREP / 'start.json', {'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
                              'program_bytes': (AUTH / 'program.json').stat().st_size})
    runtime = read(AUTH / 'reviews/english-applicability-439/baseline.json')
    from scripts.prospectus_english_applicability_program import check_runtime
    check_runtime(runtime['runtime'], runtime['runtime_files'])
    evidence = {p: file_hash(ROOT / p) for p in SUPPORT}
    for folder in (WORK, PREP, AUTH / 'reviews/annual-note-roadmap-439'):
        evidence.update({rel(p): file_hash(p) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    evidence.update({'src/legalmath/' + n: h for n, h in package.items()})
    evidence.update({rel(SOURCE / 'attempt-015/outputs.json'): file_hash(SOURCE / 'attempt-015/outputs.json'),
                     rel(AUTH / 'reviews/english-applicability-439/post-record.json'): file_hash(AUTH / 'reviews/english-applicability-439/post-record.json')})
    save(PREP / 'freeze.json', {'evidence': evidence, 'package': package, 'baseline': baseline['baseline'],
                               'runtime': runtime['runtime'], 'runtime_files': runtime['runtime_files'], 'parts': PARTS})
    proposal = deepcopy(old)
    proposal['revision'] = 440
    task = next(t for t in proposal['tasks'] if t['id'] == TASK)
    task.update(dossier=work.PLAN, pre_admission_review=work.PLAN, annual_basis_review=rel(PREP / 'freeze.json'),
        reason='Consume missing original Note2.1basis, seven Note3judgment topics and fourteen Note46pronouncements without changing existing annual meanings')
    task['inputs'] = sorted(set(task['inputs']) | set(evidence) | {rel(PREP / 'freeze.json')})
    attempts = [e['attempt'] for e in a.events() if e['kind'] == 'ADMIT' and e['budget_key'] == TASK]
    require(len(attempts) == old['budgets'][TASK]['maximum_new_attempts'] == 15, 'Retain15original admissions')
    proposal['budgets'][TASK]['maximum_new_attempts'] = 16
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 440
    for row in routes['tasks']:
        if row['task'] == TASK:
            row.update(task_sha256=digest(task), dossier=work.PLAN, phase=0,
                remaining='Original annual scope still incomplete; new optional reading covers Note2.1, Note3andNote46only. Note1, remaining policies/numerical notes and Note47remain.',
                next_action='Complete annual-basis016ordinary/installed segments, retain source coverage, then continue next original source notes; preserve439repair and batch finite criteria later.',
                stop_condition='Same source09lineage;16admissions;2560cumulative seconds and448MiB;600new seconds128MiB;one changed segmentation recovery consumed.')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=work.PLAN, routes=rel(PREP / 'routes.json'))
    for name in ('src/legalmath/' + work.CHANGE,):
        if name in proposal['continuation_review']['bindings']:
            proposal['continuation_review']['bindings'][name] = package[work.CHANGE]
    proposal['continuation_review']['bindings'].update({p: file_hash(ROOT / p) for p in
        (SELF, work.SELF, work.PLAN, rel(PREP / 'freeze.json'), rel(PREP / 'routes.json'))})
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', {'baseline': digest(old), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Optional annual-v3source meanings for original missing notes', 'Preserve439report repair and old annual answers'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': work.PLAN, 'source_review': rel(WORK / 'SOURCE-REVIEW.md'),
            'recovery_review': rel(PREP / 'RECOVERY.md'), 'all_candidate_segments': PARTS},
        'evidence_contract': {'baseline': 'Complete012/015annual answer and all439report cases',
            'primary': 'Source-qualified actual optional answer; old complete answer unchanged;18semantic mutations and3public refusals',
            'promotion_veto': ['Source/meaning/import mismatch', 'Unsupported adoption or impact claim'],
            'continuation_veto': ['Invalid authority', 'Corrupt shared evidence', 'Spent cumulative bound'],
            'explanatory': ['Counts', 'Timing'], 'not_concluded': ['Independent IFRS/legal correctness', 'Whole annual completeness']},
        'budget_revision': {'budget_key': TASK, 'previous_maximum': 15, 'new_maximum': 16, 'retained_attempts': attempts,
            'reason': 'Original Note2.1/3/46meanings were absent; cumulative substantive time1960to2560explicitly extended; storage448MiBunchanged',
            'next_discriminating_check': 'Same complete candidate/current/installed answer and every split control segment',
            'stop_condition': {'new_seconds': 600, 'cumulative_seconds': 2560, 'new_bytes': 128 * 1024**2,
                'cumulative_bytes': 448 * 1024**2, 'reserve_bytes': 2 * 1024**2, 'process_seconds': 60,
                'unchanged_retries': 0, 'changed_recovery_consumed': True},
            'same_scope_authorization': 'Recover and continue original build; all prior costs and failures retained'}})
    total_package = sum((ROOT / 'src/legalmath' / p).stat().st_size for p in package)
    forecast = usage()['new_bytes'] + 3 * (PREP / 'proposal.json').stat().st_size + 4 * total_package + 12 * 1024**2
    require(forecast + 2 * 1024**2 < 128 * 1024**2 and
            read(WORK / 'preparation.json')['prior_bytes'] + forecast + 2 * 1024**2 < 448 * 1024**2,
            'Forecast exceeds same-task storage bound')
    save(PREP / 'forecast.json', {'new_bytes': forecast, 'all_final_package_authority_and_output_allowances_included': True})
    return {'status': 'FROZEN', 'forecast_new_bytes': forecast}


def cutover():
    a = Authority(ROOT)
    freeze = read(PREP / 'freeze.json')
    require(digest(a.spec()[0]) == read(PREP / 'review.json')['baseline'] and inventory(ROOT / 'src/legalmath') == freeze['baseline'], 'Baseline changed')
    shutil.copyfile(WORK / 'candidate/src/legalmath' / work.CHANGE, ROOT / 'src/legalmath' / work.CHANGE)
    require(inventory(ROOT / 'src/legalmath') == freeze['package'], 'Cutover differs')
    save(PREP / 'cutover.json', {'changed': [work.CHANGE], 'revision_required': 440})
    return {'status': 'CUTOVER_COMPLETE_REVISION_REQUIRED'}


def admitted():
    a = Authority(ROOT)
    p, tasks, _ = a.spec()
    require(p['revision'] == 440 and read(HERE / 'admission.json')['binding'] == a.binding(tasks[TASK]), 'Current440admission required')
    require(next(e for e in reversed(a.events()) if e.get('task') == TASK)['kind'] == 'ADMIT', 'Attempt already terminal')
    require(not (HERE / 'outputs.json').exists(), 'Attempt already sealed')


def stage(kind, part):
    admitted()
    freeze = read(PREP / 'freeze.json')
    require(usage()['allowed'], 'Before-stage resource ceiling')
    if kind == 'package':
        source = HERE / 'package-source'
        source.mkdir()
        shutil.copyfile(ROOT / 'pyproject.toml', source / 'pyproject.toml')
        shutil.copytree(ROOT / 'src', source / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
        python = freeze['runtime']['package_python']
        work.command('wheel', [python, '-I', '-B', '-m', 'pip', 'wheel', '--no-index', '--no-deps', '--no-build-isolation',
                              '--wheel-dir', str(HERE / 'wheel'), str(source)], HERE / 'commands')
        wheel, = (HERE / 'wheel').glob('*.whl')
        with zipfile.ZipFile(wheel) as archive:
            files = {n.removeprefix('legalmath/'): hashlib.sha256(archive.read(n)).hexdigest()
                     for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
        require(files == freeze['package'], 'Wheel differs')
        work.command('install', [python, '-I', '-B', '-m', 'pip', 'install', '--no-index', '--no-deps', '--no-compile',
                                '--target', str(HERE / 'installed-package'), str(wheel)], HERE / 'commands')
        require(inventory(HERE / 'installed-package/legalmath') == files, 'Installed package differs')
        save(HERE / 'package.json', {'status': 'PASS', 'files': files, 'wheel': {'path': rel(wheel), 'sha256': file_hash(wheel)}})
    else:
        require(part in PARTS, 'Declared segment required')
        if kind == 'installed':
            require(read(HERE / 'package.json')['status'] == 'PASS', 'Installed package required')
        python = freeze['runtime']['package_python' if kind == 'installed' else 'ordinary_python']
        work.command(kind + '-' + part, [python, '-I', '-B', str(ROOT / work.SELF), 'worker', '--kind', kind,
                                        '--part', part], HERE / 'commands')
    require(usage()['allowed'], 'Post-stage resource ceiling')
    return {'status': 'PASS', 'kind': kind, 'part': part, 'costs': usage()}


def seal():
    admitted()
    freeze = read(PREP / 'freeze.json')
    require(all(file_hash(ROOT / p) == h for p, h in freeze['evidence'].items()), 'Frozen evidence changed')
    require(inventory(ROOT / 'src/legalmath') == freeze['package'] == inventory(HERE / 'installed-package/legalmath'), 'Package changed')
    from scripts.prospectus_english_applicability_program import check_runtime
    check_runtime(freeze['runtime'], freeze['runtime_files'])
    for part in PARTS:
        expected = read(WORK / ('candidate-recovery-' + part) / 'result.json')
        require(expected == read(HERE / ('ordinary-' + part) / 'result.json') == read(HERE / ('installed-' + part) / 'result.json'), 'Incomplete/mismatched segment')
    require(read(HERE / 'ordinary-answer/answer-delta.json.gz') == read(HERE / 'installed-answer/answer-delta.json.gz'), 'Complete installed answer delta differs')
    require((HERE / 'RESULT.md').exists() and (HERE / 'COVERAGE.md').exists(), 'Substantive notes required')
    save(HERE / 'result.json', {'status': 'PASS', 'task': TASK, 'task_complete': False, 'whole_program_complete': False,
                              'costs': usage(), 'plan': work.PLAN})
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [rel(p) for p in (HERE / 'commands').glob('*.json')],
        'preparation_commands': [rel(p) for p in (PREP / 'commands').glob('*.json')],
        'environment': freeze['runtime'], 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'random_seeds': 'N/A deterministic',
        'wall_seconds': usage()['new_seconds'], 'data_version': rel(PREP / 'freeze.json'), 'plan': work.PLAN,
        'result': rel(HERE / 'RESULT.md')})
    outputs = {str(p.relative_to(HERE)): file_hash(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    save(HERE / 'outputs.json', outputs)
    require(usage()['allowed'], 'Post-seal storage ceiling')
    return {'status': 'SEALED', 'costs': usage()}


def record():
    started = time.monotonic()
    cmd = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'scripts.prospectus_control', 'record', '--attempt', rel(HERE)]
    with (PREP / 'record-projection.log').open('x') as log:
        result = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=60)
    save(PREP / 'record-projection.json', {'argv': cmd, 'exit_code': result.returncode,
        'seconds': time.monotonic() - started, 'role': 'AUTHORITY_RECORD_AND_VIEW; no registered substantive validator'})
    a = Authority(ROOT)
    event = next(e for e in reversed(a.events()) if e.get('attempt') == rel(HERE))
    require(result.returncode == 0 and event['kind'] == 'RECORD' and a.retained_evidence_valid(event), 'Record not intact')
    save(PREP / 'post-record.json', {'event': event, 'costs': usage(), 'retained_evidence_valid': True})
    return {'status': 'RECORDED', 'event': event['sha256'], 'costs': usage()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['freeze', 'cutover', 'stage', 'seal', 'record', 'usage'])
    parser.add_argument('--kind', choices=['ordinary', 'package', 'installed'])
    parser.add_argument('--part', choices=PARTS)
    args = parser.parse_args()
    started = time.monotonic()
    result = stage(args.kind, args.part) if args.action == 'stage' else globals()[args.action]()
    if args.action in ('freeze', 'cutover', 'seal'):
        save(PREP / 'commands' / (args.action + '.json'), {'argv': sys.argv, 'seconds': time.monotonic() - started})
    print(json.dumps(result), flush=True)
