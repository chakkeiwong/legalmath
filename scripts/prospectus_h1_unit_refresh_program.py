"""Submit current finite H1 unit evidence using the recorded release-repair wheel."""
from copy import deepcopy
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile
import hashlib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts import prospectus_component_revalidation as component
from scripts import prospectus_release_applicability_program as release
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read, write, process_identity

AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/component-435'
HERE = AUTH / 'attempts/source-bes-dep-05/attempt-071'
DONOR = release.HERE
SELF = 'scripts/prospectus_h1_unit_refresh_program.py'
PLAN = 'docs/plans/prospectus-unit-refresh-after-release-2026-10-22.md'
PROPOSAL = AUTH / 'proposals/component-435.json'
REVIEW = AUTH / 'proposals/component-435-review.json'
require = component.require


def rel(path):
    return str(Path(path).relative_to(ROOT))


def prepare():
    start = time.monotonic()
    a = Authority(ROOT)
    old, _, _ = a.spec()
    require(old['revision'] == 434 and not PREP.exists() and not HERE.exists(), 'Fresh434required')
    event = next(e for e in reversed(a.events()) if e.get('attempt') == rel(DONOR) and e['kind'] == 'RECORD')
    require(a.retained_evidence_valid(event), 'Recorded donor changed')
    package = read(DONOR / 'package.json')
    require(package['files'] == component.package_files(ROOT / 'src/legalmath'), 'Current wheel required')
    status = component.prepare('h1-unit', None)
    require(status == 0, 'Component preparation failed; inspect retained failure')
    proposal = read(PROPOSAL)
    review = read(REVIEW)
    task = next(t for t in proposal['tasks'] if t['id'] == 'source-bes-dep-05')
    # Select the existing general component validator. Historical selectors and
    # methods remain unchanged in every prior revision/admission.
    for key in ('h1_current_unit_acceptance', 'h1_statement_context_acceptance', 'h1_interim_applicability_acceptance'):
        task.pop(key, None)
    task.update(dossier=PLAN, pre_admission_review=PLAN,
                reason='Submit fresh original unit proof on unchanged434production using the recorded008wheel')
    input_names = set(task['inputs']) | {SELF, PLAN}
    input_names.update(rel(DONOR / n) for n in read(DONOR / 'outputs.json'))
    input_names.add(rel(DONOR / 'outputs.json'))
    task['inputs'] = sorted(input_names)
    frozen = read(PREP / 'frozen.json')
    files = sorted(set(frozen['methods']) | set(frozen['inputs']) | {
        rel(PREP / 'frozen.json'), rel(PREP / 'preflight.json'), SELF, PLAN,
        rel(DONOR / 'outputs.json'), rel(PREP / 'donor.json')})
    write(PREP / 'donor.json', {'attempt': rel(DONOR), 'event_sha256': event['sha256'],
         'outputs_sha256': event['outputs_sha256'], 'package': package,
         'prior_cumulative_costs': release.costs(), 'manual_time': 'UNKNOWN'}, exclusive=True)
    task['inputs'] = sorted(set(task['inputs']) | set(files))
    task['build_criteria_scope'] = ['individual-unit-conflict']
    task['build_criterion_lineage'] = {'individual-unit-conflict': {
        'version': 'criterion-evidence.v1', 'files': files, 'trees': ['src/legalmath']}}
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 435
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(task_sha256=digest(task), dossier=PLAN, phase=0,
                remaining='Current unit criterion pending after shared release repair; original source interpretation gaps remain open.',
                next_action='Validate unchanged434unit behavior with original controls; then reconcile original source08 coverage.',
                stop_condition='Admission071; unchanged registered96MiB/750seconds; no retry;120second outer processes.')
        elif row['task'] == 'source-bes-dep-08':
            row.update(phase=1, remaining='008sealed and recorded the24false-support repair; original coverage remains open.',
                next_action='Reconcile original release pages and supplied200-cell meaning against all original source08 requirements; avoid repeat installation.')
    write(PREP / 'routes.json', routes, exclusive=True)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({n: file_hash(ROOT / n) for n in (PLAN, SELF, rel(PREP / 'routes.json'), rel(PREP / 'donor.json'))})
    review['changes'] = ['Fresh finite unit acceptance on434production', 'Use recorded current wheel with honest build-binding stage', 'Retain all original scope and source history']
    review['skeptical_audit'].update(plan=PLAN, wheel_binding=rel(PREP / 'donor.json'),
        dispatch='Remove obsolete per-attempt selectors; unchanged registered component validator recomputes original evidence')
    review['evidence_contract']['baseline_later_answer'] = rel(DONOR / 'ordinary-answer.json.gz')
    review['budget_revision']['reason'] = 'Shared production changed in source08/008; criterion must be freshly validated'
    review['budget_revision']['stop_condition']['outer_worker_seconds'] = 120
    # These proposals are still unaccepted preparation products, not sealed evidence.
    write(PROPOSAL, proposal)
    write(REVIEW, review)
    write(PREP / 'refresh-preparation.json', {'seconds': time.monotonic() - start,
          'actual_action': SELF + ' prepare', 'production_edited': False, 'wheel_build_planned': False}, exclusive=True)
    component.usage(task, HERE)
    forecast = component.usage(task, HERE)['new_bytes'] + 2 * PROPOSAL.stat().st_size + 20 * 1024**2
    require(forecast < component.BOUNDS['new_bytes'] - component.BOUNDS['reserve_bytes'], 'Forecast exceeds component bound')
    return {'status': 'PREPARED', 'revision': 435, 'forecast_bytes': forecast}


def task():
    a = Authority(ROOT)
    program, tasks, _ = a.spec()
    current = tasks['source-bes-dep-05']
    require(program['revision'] == 435 and read(HERE / 'admission.json')['binding'] == a.binding(current), 'Current435admission required')
    require(next(e for e in reversed(a.events()) if e.get('task') == current['id'])['kind'] == 'ADMIT', 'Attempt terminal')
    return current


def bind_wheel():
    current = task()
    require(read(HERE / 'stages/candidate/result.json')['status'] == 'PASS', 'Candidate required')
    start = time.monotonic()
    saved = read(PREP / 'donor.json')
    a = Authority(ROOT)
    event = next(e for e in a.events() if e['sha256'] == saved['event_sha256'])
    require(a.retained_evidence_valid(event), 'Donor evidence changed')
    package = read(DONOR / 'package.json')
    require(package == saved['package'] and package['files'] == component.package_files(ROOT / 'src/legalmath'), 'Wrong donor package')
    wheel = ROOT / package['wheel']['path']
    require(file_hash(wheel) == package['wheel']['sha256'], 'Wheel changed')
    with zipfile.ZipFile(wheel) as archive:
        contents = {n.removeprefix('legalmath/'): hashlib.sha256(archive.read(n)).hexdigest()
                    for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    require(contents == package['files'], 'Wheel inventory changed')
    target = HERE / 'wheel' / wheel.name
    target.parent.mkdir()
    shutil.copyfile(wheel, target)
    write(HERE / 'wheel.json', {'file': str(target.relative_to(HERE)), 'sha256': file_hash(target)}, exclusive=True)
    stage = HERE / 'stages/build'
    stage.mkdir(parents=True)
    write(stage / 'started.json', {'command': [str(ROOT / '.venv/bin/python'), '-B', '-m', 'scripts.prospectus_h1_unit_refresh_program', 'bind-wheel'],
         'plan': PLAN, 'git_commit': read(HERE / 'admission.json')['git_commit'], 'source': rel(wheel),
         'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'operation': 'AUTHENTICATE_AND_COPY_RECORDED_WHEEL',
         'new_build_executed': False}, exclusive=True)
    write(stage / 'result.json', {'status': 'PASS', 'error': None, 'wall_seconds': time.monotonic() - start,
         'details': {'wheel_hash': file_hash(target), 'current_inventory_equal': True, 'new_build_executed': False,
                     'storage': component.usage(current, HERE)}}, exclusive=True)
    return {'status': 'BOUND_RECORDED_WHEEL', 'new_build_executed': False}


def run(stage):
    current = task()
    folder = PREP / 'commands'
    folder.mkdir(exist_ok=True)
    argv = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'scripts.prospectus_component_revalidation',
            'run', '--attempt', rel(HERE), '--stage', stage]
    start = time.monotonic()
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(ROOT / 'src'), 'PIP_NO_INDEX': '1'}
    with (folder / (stage + '.log')).open('x') as log:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        write(folder / (stage + '-started.json'), {'argv': argv, 'identity': process_identity(child.pid)}, exclusive=True)
        try:
            code = child.wait(timeout=120)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            code = -1
    write(folder / (stage + '.json'), {'exit_code': code, 'seconds': time.monotonic() - start,
          'actual_argv': argv, 'timing_role': 'OUTER; nested stage duration not added again'}, exclusive=True)
    require(code == 0, 'Inspect retained stage log')
    component.usage(current, HERE)
    return {'status': 'PASS', 'stage': stage}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'bind-wheel', 'run'])
    parser.add_argument('--stage', choices=['candidate', 'install', 'installed', 'seal'])
    args = parser.parse_args()
    result = prepare() if args.action == 'prepare' else bind_wheel() if args.action == 'bind-wheel' else run(args.stage)
    print(json.dumps(result), flush=True)
