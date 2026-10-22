"""The single changed repair of attempt 064's empty comparator import check."""
from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import prospectus_h1_current_relationships as base

common, mapping = base.common, base.mapping
read, save, require, sha, digest, rel = base.read, base.save, base.require, base.sha, base.digest, base.rel
AUTH, BASE = base.AUTH, base.BASE
OLD_HERE, OLD_PREP = base.HERE, base.PREP
HERE = BASE / 'attempt-065'
PREP = AUTH / 'reviews/h1-relationship-runner-repair-428'
SELF = 'scripts/prospectus_h1_relationship_runner_repair.py'
PLAN = 'docs/plans/prospectus-h1-relationship-runner-repair-2026-10-22.md'
DEPENDENCIES = {'compare': [], 'legacy': ['compare'], 'package': ['legacy'],
    'installed': ['package'], 'installed-compare': ['installed'],
    'installed-legacy': ['installed-compare']}
for case in mapping.CASES:
    DEPENDENCIES['control-' + case] = ['compare']
    DEPENDENCIES['installed-control-' + case] = ['installed-compare', 'control-' + case]
DEPENDENCIES['coverage'] = []


def costs(reserve=0, seconds_reserve=0):
    start = read(PREP / 'accounting-start.json')
    paths = {p for folder in (PREP, HERE) if folder.exists() for p in folder.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in (SELF, PLAN))
    paths.add(AUTH / 'revisions/0428.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    seconds = sum(r['wall_seconds'] for folder in (PREP, HERE) for p in folder.glob('commands/*.json')
        if (r := read(p)).get('accounting_role') != 'NESTED_IN_PARENT')
    old = start['prior_cost_receipt']
    aggregate_bytes = old['new_bytes'] + size
    aggregate_seconds = old['new_measured_seconds'] + old['new_control_seconds'] + seconds + 60
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes'] + size,
        'known_cumulative_seconds': start['prior_known_seconds'] + seconds + 60,
        'aggregate_064_065_bytes': aggregate_bytes, 'aggregate_064_065_seconds': aggregate_seconds,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; includes earlier unmeasured empty-import probe',
        'execution_allowed': size + reserve < 156 * 1024**2 and seconds + seconds_reserve < 1000
            and aggregate_bytes + reserve < 252 * 1024**2 and aggregate_seconds + seconds_reserve < 1260}


def prepare():
    tick = time.monotonic()
    auth = common.authority()
    old = read(AUTH / 'program.json')
    require(old['revision'] == 427 and not PREP.exists() and not HERE.exists(), 'Fresh revision 427 required')
    events = auth.events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e['budget_key'] == 'source-bes-dep-05']
    require(len(attempts) == old['budgets']['source-bes-dep-05']['maximum_new_attempts'] == 64, 'Retain 64 admissions')
    manifest = OLD_HERE / 'outputs.json'
    require(any(e.get('attempt') == rel(OLD_HERE) and e.get('outputs_sha256') == sha(manifest)
        for e in events), 'Recorded 064 required')
    require(all(sha(OLD_HERE / n) == v for n, v in read(manifest).items()), 'Changed sealed 064')
    result = read(OLD_HERE / 'result.json')
    require(result['status'] == 'FAIL' and result['stages']['compare'] == 'FAIL'
        and all(result['stages'][n] == 'PASS' for n in ('source', 'implement', 'tests', 'ordinary')),
        'Diagnosed 064 outcome changed')
    require('Wrong imported package origin' in (OLD_HERE / 'commands/compare.log').read_text(), 'Wrong repair target')
    production = common.production()
    require(production == read(OLD_PREP / 'candidate-production.json'), '064 production changed')
    previous = base.costs()
    save(PREP / 'accounting-start.json', {'prior_known_bytes': previous['known_cumulative_bytes'],
        'prior_known_seconds': previous['known_cumulative_seconds'], 'prior_cost_receipt': previous,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'program_bytes': (AUTH / 'program.json').stat().st_size})
    config = read(OLD_PREP / 'config.json')
    require(sha(config['package_python']) == config['python_sha256']
        and sha(config['ordinary_python']) == config['ordinary_python_sha256'], 'Interpreter changed')
    save(PREP / 'config.json', config)
    save(PREP / 'candidate-production.json', production)
    # A changed diagnostic: load the actual module before testing its origin.
    probe = time.monotonic()
    sys.path.insert(0, str(ROOT / 'src'))
    module = importlib.import_module('legalmath.prospectus.h1_source_relationships')
    require(Path(module.__file__).resolve() == (ROOT / mapping.MODULE).resolve(), 'Wrong repair diagnostic origin')
    save(PREP / 'import-diagnostic.json', {'status': 'PASS', 'module': module.__name__,
        'origin': module.__file__, 'sha256': sha(module.__file__), 'production_changed': False})
    save(PREP / 'commands/import-diagnostic.json', {'wall_seconds': time.monotonic() - probe,
        'accounting_role': 'NESTED_IN_PARENT', 'command': 'Explicit package import after worktree path selection'})
    checked_answer('ordinary')
    bindings = dict(read(OLD_PREP / 'freeze.json')['bindings'])
    bindings.update(production)
    bindings.update({rel(OLD_HERE / n): v for n, v in read(manifest).items()})
    names = [SELF, PLAN, rel(manifest), rel(OLD_PREP / 'freeze.json'),
        rel(OLD_PREP / 'candidate-production.json'), rel(OLD_PREP / 'profile.json'),
        rel(PREP / 'config.json'), rel(PREP / 'candidate-production.json'), rel(PREP / 'import-diagnostic.json')]
    bindings.update({n: sha(ROOT / n) for n in names})
    require(all(sha(ROOT / n) == v for n, v in bindings.items()), 'Stale retained binding')
    save(PREP / 'freeze.json', {'bindings': bindings, 'production': production, 'production_writes': 0,
        'retained_ordinary': common.ref(OLD_HERE / 'ordinary.json')})
    new = deepcopy(old)
    new['revision'] = 428
    task = next(t for t in new['tasks'] if t['id'] == 'source-bes-dep-05')
    task.update(dossier=PLAN, pre_admission_review=PLAN, build_criteria_scope=[],
        reason='Repair the diagnosed empty comparator import and finish remaining 064 checks without changing production')
    task['inputs'] = sorted(set(task['inputs']) | set(bindings) | {rel(PREP / 'freeze.json')})
    bounds = {'measured_seconds': 1000, 'control_seconds': 60, 'new_bytes': 160 * 1024**2,
        'failure_reserve': 4 * 1024**2, 'worker_seconds': 120, 'large_file_bytes': 32 * 1024**2,
        'original_aggregate_bytes': 256 * 1024**2, 'original_aggregate_seconds': 1260,
        'previous_known_bytes': previous['known_cumulative_bytes'],
        'previous_known_seconds': previous['known_cumulative_seconds'], 'unchanged_retries': 0,
        'additional_runner_repairs': 0}
    task['current_h1_relationship_runner_repair'] = {'version': 'h1-relationship-runner-repair.v1',
        'freeze': rel(PREP / 'freeze.json'), 'failed_attempt': rel(OLD_HERE), 'bounds': bounds,
        'success_dependencies': DEPENDENCIES, 'original_task_acceptance': False, 'production_writes': 0}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts'] = 65
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 428
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(task_sha256=common.compact_digest(task), dossier=PLAN, phase=0,
                remaining='Retained 064 failure; installed and adverse checks incomplete; wider source/reference meaning remains.',
                next_action='Execute the single changed import-check repair; record, refresh and continue original source review.',
                stop_condition='Attempt65 only; 160MiB and1000+60 seconds within original aggregate; no production writes or unchanged retry.')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n)
        for n in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    require(new['obligations'] == old['obligations'] and new['build_contract'] == old['build_contract'], 'Original scope changed')
    raw = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
    source_bytes = sum((ROOT / n).stat().st_size for n in production)
    forecast = costs()['new_bytes'] + 2 * len(raw) + 4 * source_bytes + 32 * 1024**2 + 8 * 1024**2
    time_forecast = 19 * (read(OLD_HERE / 'commands/ordinary.json')['wall_seconds'] + 8) + 100
    require(costs(forecast - costs()['new_bytes'], time_forecast)['execution_allowed'], 'Residual forecast exceeds original allowance')
    with (PREP / 'proposal.json').open('xb') as stream:
        stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as adigest
    save(PREP / 'review.json', {'baseline': adigest(old), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Explicit package import before comparison-origin receipt',
            'Authenticated 064 successful work reused; remaining actual public checks only',
            'No production changes; original aggregate allowance retained'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'forecast_new_bytes': forecast,
            'forecast_measured_seconds': time_forecast, 'failed_attempt_unchanged': True},
        'evidence_contract': {'question': 'Does unchanged064 satisfy the remaining public ordinary/installed checks?',
            'baseline': rel(OLD_HERE / 'ordinary-answer.json.gz'),
            'primary': 'Whole063 preservation, audited links, ordinary/installed equality, old-call compatibility and exact refusals',
            'promotion_veto': ['Lost prior', 'Wrong association', 'Accepted corruption', 'Wrong import'],
            'continuation_veto': ['Invalid authority', 'Corrupt originals', 'Exhausted residual resources'],
            'not_concluded': ['Financial reconciliation', 'Source truth', 'General automatic capability', 'Whole build']},
        'budget_revision': {'budget_key': 'source-bes-dep-05', 'previous_maximum': 64, 'new_maximum': 65,
            'retained_attempts': attempts, 'reason': 'Single declared changed repair of reproduced 064 runner defect',
            'next_discriminating_check': 'Explicit real-package import and strict origin check before comparator receipt',
            'stop_condition': bounds, 'same_scope_authorization': 'Recover and continue original build'}})
    save(PREP / 'commands/preparation.json', {'wall_seconds': time.monotonic() - tick,
        'command': [sys.executable, '-B', '-m', 'scripts.prospectus_h1_relationship_runner_repair', 'prepare']})
    return {'status': 'PREPARED', 'revision': 428, 'forecast_new_bytes': forecast,
        'forecast_measured_seconds': time_forecast, 'resources': costs()}


def frozen():
    auth = common.authority()
    admission = read(HERE / 'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH / 'program.json')) == admission['program_sha256']
        and auth.binding(admission['task_spec']) == admission['binding'], 'Admission changed')
    freeze = read(PREP / 'freeze.json')
    require(all(sha(ROOT / n) == v for n, v in freeze['bindings'].items()), 'Frozen evidence changed')
    require(common.production() == freeze['production'], 'Production changed during runner repair')
    config = read(PREP / 'config.json')
    require(sha(config['package_python']) == config['python_sha256']
        and sha(config['ordinary_python']) == config['ordinary_python_sha256'], 'Interpreter changed')


def load_inputs():
    return (read(base.prior.HERE / 'products.json.gz'), read(base.prior.HERE / 'profiles.json.gz'),
        read(OLD_PREP / 'profile.json'), read(base.prior.HERE / 'ordinary-answer.json.gz'),
        read(base.AUDIT / 'associations-063.json'))


def checked_answer(kind):
    location = OLD_HERE if kind == 'ordinary' else HERE
    receipt = read(location / (kind + '.json'))
    path = location / (kind + '-answer.json.gz')
    require(receipt['status'] == 'PASS' and sha(path) == receipt['answer_file']['sha256'], 'Saved answer bytes changed')
    answer = read(path)
    require(digest(answer) == receipt['answer_sha256'], 'Saved answer content changed')
    return answer


def configure():
    # These are the complete, reviewed adaptations of frozen worker functions.
    for name, value in {'HERE': HERE, 'PREP': PREP, 'SELF': SELF, 'PLAN': PLAN,
        'DEPENDENCIES': DEPENDENCIES, 'costs': costs, 'frozen': frozen,
        'load_inputs': load_inputs, 'checked_answer': checked_answer}.items():
        setattr(base, name, value)


def finalize():
    save(HERE / 'repair-attribution.json', {
        'failed_attempt': common.ref(OLD_HERE / 'result.json'),
        'retained_successes': {name: common.ref(OLD_HERE / 'stages' / name / 'result.json')
            for name in ('source', 'implement', 'tests', 'ordinary')},
        'ordinary_answer': common.ref(OLD_HERE / 'ordinary-answer.json.gz'),
        'cause': 'Local comparator runner requested nonempty package imports without importing the package',
        'repair': 'Explicit actual module import after environment selection; strict origin assertion unchanged',
        'production_changed': False, 'third_party_package_defect_established': False,
        'prior_failure_remains_failure': True})
    result = base.finalize()
    return result | {'retained_failure': rel(OLD_HERE / 'result.json'),
        'ordinary_reused_from': rel(OLD_HERE / 'ordinary.json'), 'production_changed': False}


def main():
    action = sys.argv[1]
    if action == 'prepare':
        return prepare()
    configure()
    if not action.startswith('worker-'):
        return finalize() if action == 'finalize' else base.stage(action)
    kind = action.removeprefix('worker-')
    require(kind in DEPENDENCIES, 'No unreviewed worker')
    sys.path.insert(0, str(HERE / 'installed') if kind.startswith('installed') else str(ROOT / 'src'))
    if kind != 'package':
        def forbidden(*args, **kwargs):
            raise RuntimeError('No native/network child in relationship repair worker')
        base.subprocess.Popen = forbidden
    if kind in ('compare', 'installed-compare'):
        importlib.import_module('legalmath.prospectus.h1_source_relationships')
        base.compare_worker(kind)
    elif kind == 'installed':
        base.answer_worker(kind)
    elif kind in ('legacy', 'installed-legacy'):
        base.legacy_worker(kind)
    elif kind.startswith(('control-', 'installed-control-')):
        base.control_worker(kind)
    else:
        {'package': base.package_worker, 'coverage': base.coverage_worker}[kind]()
    return {'status': 'PASS', 'worker': kind}


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    print(json.dumps(main()), flush=True)
