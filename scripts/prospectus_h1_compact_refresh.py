"""Preserve historical package copies once while replaying the unchanged H1 check."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts import prospectus_component_revalidation as component
from legalmath.prospectus.execution_authority import Authority, REL, digest, file_hash, read, write

TASK = 'source-bes-dep-05'
REVISION = 438
PREP = ROOT / REL / 'reviews/component-438'
HERE = ROOT / REL / 'attempts/source-bes-dep-05/attempt-072'
PRIOR = ROOT / REL / 'attempts/source-bes-dep-05/attempt-071'
DONOR = ROOT / REL / 'attempts/source-bes-dep-11/attempt-005'
PROPOSAL = ROOT / REL / 'proposals/component-438.json'
REVIEW = ROOT / REL / 'proposals/component-438-review.json'
SELF = 'scripts/prospectus_h1_compact_refresh.py'
PLAN = 'docs/plans/prospectus-h1-evidence-closure-2026-10-22.md'
require = component.require


def rel(path):
    return str(Path(path).relative_to(ROOT))


def historical_package_copy(name):
    """Only package trees; never source documents or scientific evidence."""
    prefix = REL + '/attempts/'
    if name.startswith(prefix):
        parts = name[len(prefix):].split('/')
        if len(parts) < 4 or not parts[1].startswith('attempt-'):
            return False
        rest = '/'.join(parts[2:])
        return rest.startswith((
            'installed/legalmath/', 'installed-package/legalmath/',
            'package-source/src/legalmath/', 'package-source/build/lib/legalmath/',
            'source/src/legalmath/', 'source/build/lib/legalmath/',
            'methods/src/legalmath/', 'before-method/src/legalmath/',
            'final-method/src/legalmath/'))
    prefix = '.localresources/prospectus-preparation/'
    return name.startswith(prefix) and '/candidate/src/legalmath/' in name


def verify_partition(task):
    manifest = read(PREP / 'historical-package-copies.json')
    old = read(PRIOR / 'admission.json')['binding']
    for name, expected in manifest['files'].items():
        require(historical_package_copy(name), 'Non-package input compacted: ' + name)
        require(old.get(name) == expected == file_hash(ROOT / name), 'Historical package copy changed: ' + name)
    require(not set(manifest['files']) & set(task['inputs']), 'Historical copies expanded again')
    require(set(manifest['retained_original_inputs']) <= set(task['inputs']), 'Original non-copy evidence dropped')
    require(set(manifest['files']) | set(manifest['retained_original_inputs']) ==
            set(read(PRIOR / 'admission.json')['task_spec']['inputs']), 'Input partition changed')
    return {'historical_package_files': len(manifest['files']),
            'retained_original_inputs': len(manifest['retained_original_inputs'])}


def donor():
    auth = Authority(ROOT)
    event = next(e for e in reversed(auth.events())
                 if e.get('attempt') == rel(DONOR) and e['kind'] == 'RECORD')
    require(auth.retained_evidence_valid(event), 'Recorded Q1 package evidence changed')
    package = read(DONOR / 'package.json')
    require(package['status'] == 'PASS' and package['files'] == component.package_files(ROOT / 'src/legalmath'),
            'Donor is not the current package')
    wheel = ROOT / package['wheel']['path']
    require(file_hash(wheel) == package['wheel']['sha256'], 'Donor wheel changed')
    with zipfile.ZipFile(wheel) as archive:
        contents = {n.removeprefix('legalmath/'): hashlib.sha256(archive.read(n)).hexdigest()
                    for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    require(contents == package['files'], 'Donor wheel omits or changes production')
    return event, package, wheel


def forecast(task):
    """Conservative final bound; include every repeated generic stage manifest."""
    frozen = read(PREP / 'frozen.json')
    data_size = len(json.dumps({'data_version': frozen['inputs'], 'methods': frozen['methods']}).encode())
    task_size = len(json.dumps(task).encode())
    binding_size = len(json.dumps({n: '0' * 64 for n in task['inputs']}).encode())
    package_size = sum((ROOT / 'src/legalmath' / n).stat().st_size for n in frozen['package'])
    wheel_size = (ROOT / read(DONOR / 'package.json')['wheel']['path']).stat().st_size
    current = component.usage(task, HERE)['new_bytes']
    # The current proposal exists; its accepted revision and admission do not.
    allowances = {
        'accepted_revision': PROPOSAL.stat().st_size,
        'admission': task_size + binding_size + 1024**2,
        'stage_manifests': 5 * (data_size + 256 * 1024),
        'copied_wheel': wheel_size,
        'fresh_install': package_size + 2 * 1024**2,
        'controls_and_results': 4 * 1024**2,
        'final_manifest_record_and_reserve': 4 * 1024**2,
    }
    value = {'current_bytes': current, 'allowances': allowances,
             'forecast_bytes': current + sum(allowances.values()),
             'ceiling': component.BOUNDS['new_bytes'], 'reserve': component.BOUNDS['reserve_bytes']}
    require(value['forecast_bytes'] + value['reserve'] < value['ceiling'], 'Conservative final forecast exceeds bound')
    return value


def prepare():
    started = time.monotonic()
    auth = Authority(ROOT)
    program, tasks, _ = auth.spec()
    require(program['revision'] == 437 and not PREP.exists() and not HERE.exists(), 'Fresh revision437 required')
    require(not auth.status()['running'], 'A worker is running')
    oldtask = tasks[TASK]
    prior_admission = read(PRIOR / 'admission.json')
    require(oldtask == prior_admission['task_spec'], 'Original source05 specification changed')
    rejection = next(e for e in reversed(auth.events()) if e.get('attempt') == rel(PRIOR))
    require(rejection['kind'] == 'REJECT', 'Retain071rejection')
    donor_event, package, wheel = donor()
    require(component.prepare('h1-unit', None) == 0, 'Inspect retained component preparation failure')
    proposal, review = read(PROPOSAL), read(REVIEW)
    task = next(t for t in proposal['tasks'] if t['id'] == TASK)
    frozen = read(PREP / 'frozen.json')
    removed = {n: frozen['inputs'][n] for n in oldtask['inputs'] if historical_package_copy(n)}
    require(removed and all(prior_admission['binding'].get(n) == h for n, h in removed.items()),
            'Compacted copies differ from original admission')
    kept = sorted(set(oldtask['inputs']) - set(removed))
    write(PREP / 'historical-package-copies.json', {
        'baseline_program_sha256': digest(program), 'prior_admission': rel(PRIOR / 'admission.json'),
        'prior_admission_sha256': file_hash(PRIOR / 'admission.json'),
        'prior_rejection_event': rejection['sha256'], 'files': removed,
        'retained_original_inputs': kept, 'historical_files_deleted_or_edited': False,
        'prior_rejected_new_bytes': 99673552, 'prior_reserve_shortfall_bytes': 58832,
        'manual_cumulative_time': 'UNKNOWN',
        'pre_compaction_frozen_sha256': file_hash(PREP / 'frozen.json'),
        'pre_compaction_proposal_sha256': file_hash(PROPOSAL),
    }, exclusive=True)
    write(PREP / 'donor.json', {'attempt': rel(DONOR), 'event_sha256': donor_event['sha256'],
        'outputs_sha256': donor_event['outputs_sha256'], 'package': package,
        'reuse': 'AUTHENTICATE_AND_COPY; no new build',
        'prior_q1_costs': read(DONOR / 'result.json')['costs']}, exclusive=True)
    additions = {SELF, PLAN, rel(PREP / 'historical-package-copies.json'), rel(PREP / 'donor.json'),
                 rel(DONOR / 'outputs.json'), rel(DONOR / 'package.json'), rel(wheel),
                 rel(PRIOR / 'admission.json'), rel(PRIOR / 'outputs.json'), rel(PRIOR / 'DECISION.md')}
    frozen['inputs'] = {n: h for n, h in frozen['inputs'].items() if n not in removed}
    frozen['inputs'].update({n: file_hash(ROOT / n) for n in sorted(additions)})
    # These are newly prepared, unaccepted objects. No sealed object is rewritten.
    write(PREP / 'frozen.json', frozen)
    task['inputs'] = sorted((set(task['inputs']) - set(removed)) | additions)
    task.update(dossier=PLAN, pre_admission_review=PLAN,
                reason='Repair071metadata amplification while retaining every source and unchanged H1 unit validator')
    for key in ('h1_current_unit_acceptance', 'h1_statement_context_acceptance', 'h1_interim_applicability_acceptance'):
        task.pop(key, None)
    files = sorted(set(frozen['methods']) | set(frozen['inputs']) |
                   {rel(PREP / 'frozen.json'), rel(PREP / 'preflight.json')})
    task['build_criteria_scope'] = ['individual-unit-conflict']
    task['build_criterion_lineage'] = {'individual-unit-conflict': {
        'version': 'criterion-evidence.v1', 'files': files, 'trees': ['src/legalmath']}}
    partition = verify_partition(task)
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = REVISION
    for row in routes['tasks']:
        if row['task'] == TASK:
            row.update(task_sha256=digest(task), dossier=PLAN, phase=0,
                remaining='071functional pass was rejected for storage; preserve all wider source05 requirements.',
                next_action='Complete bounded compact current/installed unit submission; then reconcile original source09 requirements.',
                stop_condition='One changed recovery072; unchanged96MiB/750seconds; no unchanged retry or automatic next admission.')
        elif row['task'] == 'source-bes-dep-11':
            row.update(phase=2, remaining='005recorded the finite Q1 financial-target scope repair; original authority/general recognition remain open.',
                next_action='Preserve005and its original coverage matrix; continue only on a distinct reproduced gap or new source evidence.')
    write(PREP / 'routes.json', routes, exclusive=True)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({n: file_hash(ROOT / n)
        for n in (SELF, PLAN, rel(PREP / 'routes.json'), rel(PREP / 'historical-package-copies.json'))})
    review['changes'] = ['Compact historical package-copy bindings without deleting history',
                         'Revalidate original H1 criterion on current437package with unchanged substantive validator']
    review['skeptical_audit'].update(plan=PLAN, partition=partition,
        history_preserved=True, limits_and_validator_unchanged=True)
    review['budget_revision'].update(reason='071failed final storage reserve because inherited historical package-copy paths repeated in stage metadata',
        next_discriminating_check='Same full current/installed/replay checks under96MiB after conservative input compaction',
        stop_condition={**component.BOUNDS, 'outer_process_seconds': 120, 'unchanged_retries': 0, 'further_recoveries': 0})
    review['evidence_contract'].update(baseline_later_answer='Historical source08/008 protection of070retained; not newly claimed here',
        representation='Only old package-copy leaf bindings compacted; all source/meaning/comparator inputs stay direct')
    write(PROPOSAL, proposal)
    write(REVIEW, review)
    estimate = forecast(task)
    write(PREP / 'forecast.json', estimate, exclusive=True)
    write(PREP / 'compact-preparation.json', {'seconds': time.monotonic() - started,
        'partition': partition, 'production_changed': False, 'old_evidence_changed': False,
        'actual_command': SELF + ' prepare', 'timing_role': 'OUTER; includes generic preparation, not additive'}, exclusive=True)
    require(time.monotonic() - started <= 120, 'Compact preparation outer ceiling')
    return {'status': 'PREPARED', 'revision': REVISION, **partition, 'forecast_bytes': estimate['forecast_bytes']}


def current_task():
    auth = Authority(ROOT)
    program, tasks, _ = auth.spec()
    task = tasks[TASK]
    require(program['revision'] == REVISION and read(HERE / 'admission.json')['binding'] == auth.binding(task),
            'Current438admission required')
    require(next(e for e in reversed(auth.events()) if e.get('task') == TASK)['kind'] == 'ADMIT',
            'Attempt already terminal')
    return task


def bind_wheel():
    task = current_task()
    require(read(HERE / 'stages/candidate/result.json')['status'] == 'PASS', 'Current candidate required')
    started = time.monotonic()
    verify_partition(task)
    event, package, wheel = donor()
    require(event['sha256'] == read(PREP / 'donor.json')['event_sha256'], 'Donor history changed')
    target = HERE / 'wheel' / wheel.name
    target.parent.mkdir()
    shutil.copyfile(wheel, target)
    write(HERE / 'wheel.json', {'file': str(target.relative_to(HERE)), 'sha256': file_hash(target)}, exclusive=True)
    stage = HERE / 'stages/build'
    stage.mkdir(parents=True)
    write(stage / 'started.json', {'command': [str(ROOT / '.venv/bin/python'), '-B', '-m',
        'scripts.prospectus_h1_compact_refresh', 'bind-wheel'], 'plan': PLAN,
        'git_commit': read(HERE / 'admission.json')['git_commit'], 'source': rel(wheel),
        'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',
        'operation': 'AUTHENTICATE_AND_COPY_RECORDED_WHEEL', 'new_build_executed': False}, exclusive=True)
    write(stage / 'result.json', {'status': 'PASS', 'error': None, 'wall_seconds': time.monotonic() - started,
        'details': {'files': len(package['files']), 'wheel_hash': file_hash(target), 'new_build_executed': False,
                    'storage': component.usage(task, HERE)}}, exclusive=True)
    return {'status': 'BOUND_RECORDED_WHEEL', 'files': len(package['files']), 'new_build_executed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'bind-wheel', 'verify-history'])
    action = parser.parse_args().action
    result = prepare() if action == 'prepare' else bind_wheel() if action == 'bind-wheel' else verify_partition(current_task())
    print(json.dumps(result), flush=True)
