"""Bounded current H1 public-consumer trial; preserves all original obligations."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import prospectus_h1_management_consumer as prior
from scripts import prospectus_h1_combined_support as support
from scripts import prospectus_h1_statement_consumer as common

read, save, sha, digest = common.read, common.save, common.sha, common.digest
require, rel = common.require, common.rel
AUTH, BASE = prior.AUTH, prior.BASE
HERE = BASE / 'attempt-063'
PREP = AUTH / 'reviews/h1-combined-consumer-426'
TEMP = ROOT / '.localresources/prospectus-preparation/h1-combined-consumer-063'
SELF = 'scripts/prospectus_h1_combined_consumer.py'
SUPPORT = 'scripts/prospectus_h1_combined_support.py'
PLAN = 'docs/plans/prospectus-h1-combined-consumer-2026-10-22.md'
DEPENDENCIES = {'inputs': [], 'ordinary': ['inputs'], 'compare': ['ordinary'],
    'installed-origin': ['inputs'], 'installed': ['installed-origin', 'compare'],
    'installed-compare': ['installed']}
for case in support.CASES:
    DEPENDENCIES['control-' + case] = ['compare']
    DEPENDENCIES['installed-control-' + case] = ['installed-compare', 'control-' + case]
DEPENDENCIES['coverage'] = []


def costs(reserve=0, seconds_reserve=0):
    start = read(PREP / 'accounting-start.json')
    paths = {p for folder in (PREP, HERE) if folder.exists() for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in (SELF, SUPPORT, PLAN))
    paths.add(AUTH / 'revisions/0426.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists()) + start['temporary_preparation_bytes']
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    seconds = sum(read(p)['wall_seconds'] for folder in (PREP, HERE) for p in folder.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes'] + size,
        'known_cumulative_seconds': start['prior_known_seconds'] + seconds + 60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; history retained',
        'execution_allowed': size + reserve < 252 * 1024**2 and seconds + seconds_reserve < 1200}


def prepare():
    tick = time.monotonic()
    auth = prior.authority()
    old = read(AUTH / 'program.json')
    require(old['revision'] == 425 and not PREP.exists() and not HERE.exists(), 'Fresh revision 425 required')
    events = auth.events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e['budget_key'] == 'source-bes-dep-05']
    require(len(attempts) == old['budgets']['source-bes-dep-05']['maximum_new_attempts'] == 62,
            'Retain all 62 admissions')
    require(read(prior.HERE / 'result.json')['status'] == 'PASS', 'Recorded 062 PASS required')
    manifest = prior.HERE / 'outputs.json'
    recorded = [e for e in events if e.get('attempt') == rel(prior.HERE) and 'outputs_sha256' in e]
    require(recorded and sha(manifest) == recorded[-1]['outputs_sha256'], 'Unauthenticated 062 result')
    for name, value in read(manifest).items():
        require(sha(prior.HERE / name) == value, 'Changed 062 evidence: ' + name)
    production = common.production()
    require(production == read(prior.HERE / 'candidate-production.json'), '062 production changed')
    for kind in ('profiles', 'public-call'):
        receipt = read(TEMP / (kind + '.json'))
        require(receipt['status'] == 'PASS' and receipt['production'] == production
                and receipt['production_changed'] is False, 'Successful unchanged-production preflight required')
        require(all(sha(ROOT / name) == value for name, value in receipt['methods'].items()),
                'Preflight method changed')
    previous = prior.costs()
    save(PREP / 'accounting-start.json', {'prior_known_bytes': previous['known_cumulative_bytes'],
        'prior_known_seconds': previous['known_cumulative_seconds'], 'prior_cost_receipt': previous,
        'temporary_preparation_bytes': sum(p.stat().st_size for p in TEMP.rglob('*') if p.is_file()),
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'program_bytes': (AUTH / 'program.json').stat().st_size})
    shutil.copytree(TEMP, PREP / 'preflight-execution')
    for kind in ('profiles', 'public-call'):
        save(PREP / 'commands' / (kind + '-preflight.json'), {
            'wall_seconds': read(TEMP / (kind + '.json'))['seconds'],
            'command': ['timeout', '120', '.venv/bin/python', '-B', rel(TEMP / 'preflight.py'), kind]})
    config = read(prior.PREP / 'config.json')
    require(sha(config['package_python']) == config['python_sha256'], 'Package interpreter changed')
    config['ordinary_python'] = str(ROOT / '.venv/bin/python')
    config['ordinary_python_sha256'] = sha(config['ordinary_python'])
    save(PREP / 'config.json', config)
    bindings = dict(read(prior.PREP / 'freeze.json')['bindings'])
    bindings.update(production)
    bindings.update({rel(prior.HERE / name): value for name, value in read(manifest).items()})
    names = [SELF, SUPPORT, PLAN, rel(manifest), rel(PREP / 'config.json'),
        'scripts/prospectus_h1_unit_oracle.py', *map(rel, support.PROFILE_FILES.values()),
        rel(BASE / 'attempt-007/scope-consumer.json.gz'), rel(BASE / 'attempt-017/answer-delta.json.gz')]
    names.extend(rel(p) for p in (PREP / 'preflight-execution').rglob('*') if p.is_file())
    bindings.update({name: sha(ROOT / name) for name in names})
    require(all(sha(ROOT / name) == value for name, value in bindings.items()), 'Stale inherited binding')
    save(PREP / 'freeze.json', {'bindings': bindings, 'production': production, 'production_writes': 0})
    new = deepcopy(old)
    new['revision'] = 426
    task = next(t for t in new['tasks'] if t['id'] == 'source-bes-dep-05')
    task.update(dossier=PLAN, pre_admission_review=PLAN, build_criteria_scope=[],
        reason='Deliver current complete 062 and all four H1 reviews through one actual public consumer; preserve conditional scope and original obligations')
    task['inputs'] = sorted(set(task['inputs']) | set(bindings) | {rel(PREP / 'freeze.json')})
    bounds = {'measured_seconds': 1200, 'control_seconds': 60, 'new_bytes': 256 * 1024**2,
        'failure_reserve': 4 * 1024**2, 'worker_seconds': 120, 'large_file_bytes': 32 * 1024**2,
        'previous_known_bytes': previous['known_cumulative_bytes'],
        'previous_known_seconds': previous['known_cumulative_seconds'], 'unchanged_retries': 0}
    task['current_combined_h1_consumer'] = {'version': 'current-h1-combined.v1',
        'freeze': rel(PREP / 'freeze.json'), 'bounds': bounds, 'success_dependencies': DEPENDENCIES,
        'original_task_acceptance': False, 'production_writes': 0}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts'] = 63
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 426
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(task_sha256=common.compact_digest(task), dossier=PLAN, phase=0,
                remaining='062 retained; actual current combined consumer, source associations, references and source authority remain.',
                next_action='Execute 063 public normal/installed consumer and adverse cases; reconcile remaining original source requirements.',
                stop_condition='Retain 62 admissions; attempt 63 only; 1200+60 seconds and 256 MiB new; no unchanged retry; retain failures and costs.')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({name: sha(ROOT / name)
        for name in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    require(new['obligations'] == old['obligations'] and new['build_contract'] == old['build_contract'],
            'Original scope changed')
    raw = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
    # One product copy, two actual answers and authority/history metadata.
    forecast = costs()['new_bytes'] + 2 * len(raw) + 3 * 32 * 1024**2 + 8 * 1024**2
    require(forecast < 252 * 1024**2, 'Storage forecast exceeds reservation')
    preflight_seconds = read(TEMP / 'profiles.json')['seconds'] + read(TEMP / 'public-call.json')['seconds']
    # Each negative call is bounded separately; passing preflight includes the
    # same full public invocation plus more expensive whole-answer comparisons.
    time_forecast = preflight_seconds + 22 * read(TEMP / 'public-call.json')['seconds'] + 90
    require(time_forecast < 1200, 'Measured conservative runtime forecast exceeds reservation')
    with (PREP / 'proposal.json').open('xb') as stream:
        stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as adigest
    save(PREP / 'review.json', {'baseline': adigest(old), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Current public H1 consumer with all four refreshed sequential bindings',
                    'Exact 062 inner and historical substantive component preservation',
                    'Existing installed package verified by bytes; no production changes'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'forecast_new_bytes': forecast,
            'forecast_measured_seconds': time_forecast, 'proxy_metrics_do_not_establish_source_truth': True},
        'evidence_contract': {'question': 'Does one actual public call deliver the complete current H1 answer?',
            'baseline': rel(prior.HERE / 'ordinary-answer.json.gz'),
            'primary': 'Whole inner and substantive component equality, actual public ordinary/installed calls, exact adverse refusals',
            'promotion_veto': ['Lost evidence', 'Changed scope', 'Accepted corruption', 'Wrong import'],
            'continuation_veto': ['Invalid authority', 'Corrupt shared originals', 'Exhausted resources'],
            'not_concluded': ['Source authenticity', 'Financial or legal truth', 'Automatic interpretation', 'Whole build']},
        'budget_revision': {'budget_key': 'source-bes-dep-05', 'previous_maximum': 62, 'new_maximum': 63,
            'retained_attempts': attempts, 'reason': 'Remaining original current combined consumer requirement',
            'next_discriminating_check': 'Actual current public outer invocation and installed equality with re-pinned semantic corruptions',
            'stop_condition': bounds, 'same_scope_authorization': 'Recover and continue original build'}})
    save(PREP / 'commands/preparation.json', {'wall_seconds': time.monotonic() - tick,
        'command': [sys.executable, '-B', '-m', 'scripts.prospectus_h1_combined_consumer', 'prepare']})
    return {'status': 'PREPARED', 'revision': 426, 'forecast_new_bytes': forecast,
            'forecast_measured_seconds': time_forecast, 'resources': costs()}


def frozen():
    auth = prior.authority()
    admission = read(HERE / 'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH / 'program.json')) == admission['program_sha256']
            and auth.binding(admission['task_spec']) == admission['binding'], 'Unchanged admission required')
    freeze = read(PREP / 'freeze.json')
    require(all(sha(ROOT / name) == value for name, value in freeze['bindings'].items()),
            'Frozen input or production changed')
    require(common.production() == freeze['production'], 'Production inventory changed')
    config = read(PREP / 'config.json')
    require(sha(config['package_python']) == config['python_sha256']
            and sha(config['ordinary_python']) == config['ordinary_python_sha256'], 'Bound interpreter changed')


def command(name, argv):
    require(costs(32 * 1024**2, 120)['execution_allowed'], 'Reservation exhausted')
    from legalmath.prospectus.execution_authority import process_identity
    tick = time.monotonic()
    folder = HERE / 'commands'
    folder.mkdir(exist_ok=True)
    process, error = None, None
    try:
        with (folder / (name + '.log')).open('x') as stream:
            process = subprocess.Popen(argv, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1',
                     'PYTHONNOUSERSITE': '1', 'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'})
            save(folder / (name + '-started.json'), {'command': argv, 'identity': process_identity(process.pid),
                'at': datetime.now(timezone.utc).isoformat(), 'timeout_seconds': 120, 'wall_seconds': 0,
                'timing_role': 'Identity only; terminal receipt supplies measured time'})
            process.wait(timeout=120)
        require(process.returncode == 0, 'Inspect ' + name + '.log')
    except Exception as exc:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        error = {'type': type(exc).__name__, 'reason': str(exc)}
    save(folder / (name + '.json'), {'command': argv, 'wall_seconds': time.monotonic() - tick,
        'exit_code': None if process is None else process.returncode, 'error': error})
    require(error is None, 'Command failed: ' + str(error))
    require(costs()['execution_allowed'], 'Post-command resource limit')


def imports(kind):
    location = prior.HERE / 'installed' if kind.startswith('installed') else ROOT / 'src'
    modules = {name: module.__file__ for name, module in sys.modules.items()
               if name.startswith('legalmath') and getattr(module, '__file__', None)}
    require(modules and all(Path(path).resolve().is_relative_to(location) for path in modules.values()),
            'Wrong installed or ordinary import origin')
    return modules


def inputs_worker():
    source = PREP / 'preflight-execution'
    for name in ('products.json.gz', 'profiles.json.gz'):
        shutil.copyfile(source / name, HERE / name)
        require(sha(HERE / name) == sha(source / name), 'Copied input differs')
    save(HERE / 'inputs.json', {'status': 'PASS', 'preflight': read(source / 'profiles.json'),
        'actual_public_preflight': read(source / 'public-call.json'), 'production_changed': False})


def load_inputs():
    prepared = read(PREP / 'preflight-execution/profiles.json')
    for key in ('profiles', 'products'):
        require(sha(HERE / (key + '.json.gz')) == prepared[key]['sha256'], 'Current prepared input changed')
    return read(HERE / 'products.json.gz'), read(HERE / 'profiles.json.gz'), prepared


def large_save(path, value):
    require(path.name in ('ordinary-answer.json.gz', 'installed-answer.json.gz'), 'Unreviewed large answer')
    raw = gzip.compress(common.encoded(value), compresslevel=1, mtime=0)
    require(len(raw) < 32 * 1024**2, 'Answer exceeds reservation')
    with path.open('xb') as stream:
        stream.write(raw)
    return common.ref(path) | {'bytes': len(raw)}


def answer_worker(kind):
    products, profiles, prepared = load_inputs()
    answer = support.consume(products, profiles)
    value = digest(answer)
    require(value == prepared['expected_sha256'], 'Public answer differs from prepared complete components')
    artifact = large_save(HERE / (kind + '-answer.json.gz'), answer)
    save(HERE / (kind + '.json'), {'status': 'PASS', 'answer_sha256': value,
        'answer_file': artifact, 'actual_public_consumer': True, 'imports': imports(kind)})


def checked_answer(kind):
    receipt = read(HERE / (kind + '.json'))
    path = HERE / (kind + '-answer.json.gz')
    require(sha(path) == receipt['answer_file']['sha256'], 'Saved answer bytes changed')
    value = read(path)
    require(digest(value) == receipt['answer_sha256'], 'Saved answer content changed')
    return value


def comparison_worker(kind):
    actual_kind = 'installed' if kind.startswith('installed') else 'ordinary'
    products, profiles, prepared = load_inputs()
    answer, inner = checked_answer(actual_kind), prior.checked_answer('ordinary')
    proof = support.check_answer(answer, inner, products['P1']['payload']['graph'], profiles)
    require(digest(answer) == prepared['expected_sha256'], 'Prepared and actual answers differ')
    if actual_kind == 'installed':
        require(answer == checked_answer('ordinary'), 'Whole installed answer differs')
    # Demonstrate that loss of any outer result or current inner reading is
    # rejected by the comparator, before relying on its positive verdict.
    refusals = []
    for name in ('lost-management', 'lost-equity', 'lost-unit', 'invented-acceptance'):
        bad = dict(answer)
        if name in ('lost-management', 'lost-equity', 'invented-acceptance'):
            bad['answer'] = dict(inner)
            if name == 'invented-acceptance':
                bad['answer']['independent_legal_acceptance'] = True
            else:
                bad['answer']['source_statement_cells'] = dict(inner['source_statement_cells'])
                field = 'management_statement_evidence' if name == 'lost-management' else 'equity_statement_evidence'
                require(field in bad['answer']['source_statement_cells'], 'Missing comparator corruption target')
                del bad['answer']['source_statement_cells'][field]
        else:
            del bad['h1_individual_unit_review']
        try:
            support.check_answer(bad, inner, products['P1']['payload']['graph'], profiles)
        except ValueError as exc:
            require(str(exc) in ('Complete current inner answer changed', 'Complete combined wrapper field inventory required'),
                    'Unexpected comparator refusal')
            refusals.append({'case': name, 'refused': True, 'reason': str(exc)})
        else:
            raise ValueError('Comparator accepted missing or invented evidence: ' + name)
    save(HERE / (kind + '.json'), {'status': 'PASS', 'checks': proof, 'checker_refusals': refusals,
        'inner_sha256': digest(inner), 'answer_sha256': digest(answer), 'imports': imports(kind)})


def installed_origin_worker():
    expected = {name.removeprefix('src/legalmath/'): value
                for name, value in read(prior.HERE / 'candidate-production.json').items()}
    folder = prior.HERE / 'installed/legalmath'
    actual = {str(p.relative_to(folder)): sha(p) for p in folder.rglob('*') if p.is_file()}
    require(actual == expected == read(prior.HERE / 'package.json')['files'], 'Existing installed package bytes differ')
    from legalmath.prospectus import h1_incorporation_scope
    require(Path(h1_incorporation_scope.__file__).is_relative_to(folder), 'Wrong actual outer consumer origin')
    save(HERE / 'installed-origin.json', {'status': 'PASS', 'package': common.ref(prior.HERE / 'package.json'),
        'files': actual, 'imports': imports('installed-origin'), 'new_install': False})


def control_worker(kind):
    installed = kind.startswith('installed-')
    case = kind.removeprefix('installed-').removeprefix('control-')
    require(case in support.CASES, 'Unknown adverse case')
    products, profiles, _ = load_inputs()
    changed, pins = support.adverse_profiles(profiles, case)
    try:
        support.consume(products, changed, pins)
    except ValueError as exc:
        require(str(exc) == support.REFUSALS[case], 'Unexpected adverse refusal: ' + str(exc))
        result = {'status': 'PASS', 'case': case, 'refused': True, 'reason': str(exc),
                  'profile_input_sha256': digest(changed), 'pins': pins}
    else:
        raise ValueError('Actual public consumer accepted corruption: ' + case)
    if installed:
        previous = read(HERE / ('control-' + case + '.json'))
        require(result == {key: value for key, value in previous.items() if key != 'imports'},
                'Installed adverse behavior differs')
    save(HERE / (kind + '.json'), result | {'imports': imports(kind)})


def coverage_worker():
    rows = deepcopy(read(prior.HERE / 'requirements.json')['rows'])
    for row in rows:
        if row.get('status', '').startswith('THIS_ATTEMPT'):
            row.update(status='RETAINED_FINITE_INTEGRATION', evidence=common.ref(prior.HERE / 'result.json'))
    rows.append({'requirement': 'One current public answer with complete 062 and all four outer H1 reviews',
                 'status': 'THIS_ATTEMPT_SUBJECT_TO_ACTUAL_STAGE_RESULTS'})
    save(HERE / 'requirements.json', {'rows': rows, 'original_task_acceptance': False,
        'external_adviser_opinion_required': False,
        'next_discriminating_work': 'Reconcile original page/occurrence associations and referenced-note relationships against the actual complete answer; preserve source-authority and incorporation uncertainty.'})
    inventory = deepcopy(read(prior.HERE / 'note-inventory.json'))
    inventory['management_individual_pages51_54'].update(status='RETAINED_FINITE_INTEGRATION',
        evidence=common.ref(prior.HERE / 'result.json'))
    save(HERE / 'note-inventory.json', inventory)
    save(HERE / 'delivery-scope.json', {
        'current_inner': common.ref(prior.HERE / 'ordinary-answer.json.gz'),
        'expected_outer_fields': ['answer', *support.REVIEW_KEYS.values(), *support.EXPLANATION_KEYS.values()],
        'historical_component_scope': 'Historical component explanations retain their original limited scope; they are not current aggregate coverage verdicts.',
        'current_aggregate_scope': 'Current statement, notes, equity and management evidence plus cash flow, risk, conditional incorporation and individual unit conflict, subject to actual consumer stages.',
        'open_work': ['Explicit residual context associations from delivery-check-060',
            'Original statement-cell and auditor-anchor coverage scanner omissions',
            'Referenced-note relationships including equity notes 12, 37 and 38',
            'Substantive interpretation completeness of Note 2 and other notes',
            'Clipped page-59 totals and unspecified currency',
            'Source authority, Portuguese priority and unresolved incorporation construction',
            'General automatic interpretation and all original-task acceptance criteria'],
        'source_truth_established': False, 'whole_build_complete': False})


def stage(name):
    require(name in DEPENDENCIES and not (HERE / 'stages' / name).exists(), 'Unknown or already-started stage')
    for parent in DEPENDENCIES[name]:
        require(read(HERE / 'stages' / parent / 'result.json')['status'] == 'PASS', 'Failed predecessor: ' + parent)
    frozen()
    require(costs(32 * 1024**2)['execution_allowed'], 'Stage resource reservation exhausted')
    from legalmath.prospectus.execution_authority import process_identity
    save(HERE / 'stages' / name / 'started.json', {'identity': process_identity(os.getpid()),
        'at': datetime.now(timezone.utc).isoformat(), 'stage': name})
    error = None
    try:
        python = read(PREP / 'config.json')['package_python'] if name.startswith('installed') else str(ROOT / '.venv/bin/python')
        command(name, [python, '-I', '-B', str(ROOT / SELF), 'worker-' + name])
        frozen()
    except Exception as exc:
        error = {'type': type(exc).__name__, 'reason': str(exc)}
    save(HERE / 'stages' / name / 'result.json', {'status': 'FAIL' if error else 'PASS', 'error': error})
    return {'stage': name, 'status': 'FAIL' if error else 'PASS', 'error': error, 'resources': costs()}


def finalize():
    require(not (HERE / 'outputs.json').exists(), 'Already sealed')
    for started in (HERE / 'stages').glob('*/started.json'):
        require((started.parent / 'result.json').exists(), 'Unresolved stage; recover recorded process first')
    outcomes = {name: read(HERE / 'stages' / name / 'result.json')['status']
        if (HERE / 'stages' / name / 'result.json').exists() else 'BLOCKED' for name in DEPENDENCIES}
    passed = all(value == 'PASS' for value in outcomes.values())
    if passed:
        frozen()
        save(HERE / 'delivery.json', {'status': 'PASS', 'actual_public_consumer': True,
            'ordinary': read(HERE / 'ordinary.json'), 'installed': read(HERE / 'installed.json'),
            'checks': read(HERE / 'compare.json')['checks'],
            'negative_cases_each_environment': len(support.CASES),
            'all_prior_compositions_retained_in': common.ref(prior.HERE / 'composition.json'),
            'source_truth_established': False, 'original_task_complete': False})
    save(HERE / 'result.json', {'task': 'source-bes-dep-05', 'status': 'PASS' if passed else 'FAIL',
        'stages': outcomes, 'task_complete': False, 'whole_program_complete': False,
        'build_criteria_claimed': [], 'resources': costs()})
    (HERE / 'RESULT.md').write_text(
        '# Current combined H1 delivery\n\n'
        + ('The actual public consumer passed in both ordinary and installed environments. '
           'It preserves the complete 062 inner answer and every substantive field of all four historical H1 reviews. '
           'Only their declared preceding-answer/profile binding hashes change. '
           'Whole installed equality and ten separately bounded adverse cases per environment passed.\n\n'
           if passed else 'The finite trial did not pass. Retained stage results identify failures and blocked dependants.\n\n')
        + 'Historical component explanations retain their original scope. They are not current aggregate coverage decisions. '
          'The current delivery context lists residual associations, note relationships, clipped values, source authority '
          'and incorporation uncertainty explicitly. The package changes no production code or source interpretation.\n\n'
          '|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|\n'
          '|---|---|---|---|---|---|\n'
        + ('|Retain finite delivery|' if passed else '|Retain actual failure|')
        + 'Actual complete public ordinary/installed answer and matched refusals|See actual stages|'
          'Source associations, meaning and authority remain open|Record, refresh and reconcile original source requirements|'
          'Financial/legal truth, general automatic interpretation or whole build|\n\n'
          'Post-run review: preserving a shared erroneous supplied interpretation remains the strongest alternative explanation. '
          'This comparison checks delivery and unchanged scope; it does not independently validate financial or legal truth. '
          'A lost current field, altered substantive component or accepted corrupt profile would overturn the delivery verdict. '
          'Remaining source interpretation is not evidence that a third-party package is fundamentally unsuitable.\n')
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p) for p in sorted((HERE / 'commands').glob('*.json'))],
        'environment': {'ordinary': str(ROOT / '.venv/bin/python'), 'installed': read(PREP / 'config.json')['package_python']},
        'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden',
        'random_seeds': 'N/A deterministic', 'data_version': common.ref(PREP / 'freeze.json'),
        'plan': PLAN, 'result': rel(HERE / 'RESULT.md'), 'resources': costs()})
    save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
         if p.is_file() and '__pycache__' not in p.parts})
    return {'status': 'SEALED', 'candidate_passed': passed, 'resources': costs()}


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    action = sys.argv[1]
    if action.startswith('worker-'):
        kind = action.removeprefix('worker-')
        sys.path.insert(0, str(prior.HERE / 'installed') if kind.startswith('installed') else str(ROOT / 'src'))
        def forbidden(*args, **kwargs):
            raise RuntimeError('No native/network child in current combined worker')
        subprocess.Popen = forbidden
        if kind in ('ordinary', 'installed'):
            answer_worker(kind)
        elif kind in ('compare', 'installed-compare'):
            comparison_worker(kind)
        elif kind.startswith(('control-', 'installed-control-')):
            control_worker(kind)
        else:
            {'inputs': inputs_worker, 'installed-origin': installed_origin_worker, 'coverage': coverage_worker}[kind]()
        result = {'status': 'PASS', 'worker': kind}
    elif action == 'prepare':
        result = prepare()
    elif action == 'finalize':
        result = finalize()
    else:
        result = stage(action)
    print(json.dumps(result), flush=True)
