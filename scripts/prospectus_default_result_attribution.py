"""Retain rejected BASF proofs and validate a correctly attributed new result."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.execution_authority import Authority, digest, read
from legalmath.prospectus.execution_workers import validate as worker_validate
from legalmath.prospectus.successor.contracts import digest as semantic_digest

AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/default-result-attribution-260'
HERE = AUTH / 'attempts/basf-meanings/attempt-022'
PRIOR = AUTH / 'attempts/basf-meanings/attempt-021'
BASE = AUTH / 'attempts/basf-meanings/attempt-020'
OLD_FREEZE = AUTH / 'reviews/current-default-verifier-258/freeze.json'
OLD_INPUTS = AUTH / 'reviews/current-default-verifier-258/original-inputs.json'
INPUTS = AUTH / 'reviews/current-default-alternatives-257'
PLAN = 'docs/plans/prospectus-default-result-attribution-2026-10-18.md'
ROUTES = 'docs/implementation/prospectus-execution-authority/closure-routes-2026-10-18-result-attribution-260.json'
PROPOSAL = AUTH / 'proposals/default-result-attribution-260.json'
REVIEW = AUTH / 'proposals/default-result-attribution-260-review.json'
OLD_SECONDS = 1469.5192886516452
OLD_BYTES = 487726628
BOUNDS = {'new_seconds': 120, 'stage_seconds': 70, 'new_bytes': 32 * 1024**2,
          'cumulative_seconds': 1800, 'cumulative_bytes': 500 * 1024**2,
          'reserve_bytes': 1024**2, 'network_native_OCR_model_GPU_subagents_messages': 0}
STAGES = {'prepare': (), 'freeze': ('prepare',), 'propose': ('freeze',),
          'validate': ('propose',), 'seal': ('validate',)}
PREPARATION = {'prepare', 'freeze', 'propose'}


def rel(path):
    return str(Path(path).relative_to(ROOT))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encoded(value):
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False).encode()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(encoded(value))


def load(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def resources():
    seconds = sum(load(p)['wall_seconds'] for base in (PREP, HERE)
                  for p in base.glob('stages/*/result.json'))
    paths = {p for base in (PREP, HERE) for p in base.rglob('*') if p.is_file()}
    paths.update(p for p in (Path(__file__), ROOT / PLAN, ROOT / ROUTES,
                            PROPOSAL, REVIEW, AUTH / 'revisions/0260.json') if p.exists())
    if read(AUTH / 'program.json')['revision'] >= 260:
        paths.add(AUTH / 'program.json')
    size = sum(p.stat().st_size for p in paths)
    assert seconds < BOUNDS['new_seconds'] and OLD_SECONDS + seconds < BOUNDS['cumulative_seconds']
    assert size < BOUNDS['new_bytes'] - BOUNDS['reserve_bytes']
    assert OLD_BYTES + size < BOUNDS['cumulative_bytes'] - BOUNDS['reserve_bytes']
    return {'new_measured_stage_seconds': seconds, 'known015plus_seconds': OLD_SECONDS + seconds,
            'new_bytes': size, 'known015plus_bytes': OLD_BYTES + size, 'earlier_timing': 'UNKNOWN'}


def retained():
    authority = Authority(ROOT)
    events = authority.events()
    rows = []
    for folder in (BASE, PRIOR):
        event = next(e for e in reversed(events) if e.get('attempt') == rel(folder)
                     and e['kind'] in {'REJECT', 'RECORD', 'ACCEPT'})
        assert event['kind'] == 'REJECT' and event['reason'] == 'Worker result failed or belongs to another task'
        assert authority.retained_evidence_valid(event), 'Corrupt retained proof'
        result = read(folder / 'result.json')
        assert result['status'] == 'PASS' and 'task' not in result
        assert read(folder / 'admission.json')['task'] == 'basf-meanings'
        rows.append({k: event[k] for k in ('kind', 'reason', 'attempt', 'sha256', 'outputs_sha256')})
    for name, expected in read(OLD_FREEZE)['methods'].items():
        assert sha(ROOT / name) == expected, 'Changed021 method: ' + name
    for name, expected in read(OLD_INPUTS).items():
        assert sha(ROOT / name) == expected, 'Changed original input: ' + name
    return rows


def prepare():
    assert read(AUTH / 'program.json')['revision'] == 259
    events = retained()
    latest = {}
    for event in Authority(ROOT).events():
        if event.get('task') and event.get('outputs_sha256'):
            latest[event['task']] = event
    audit = []
    for task, event in sorted(latest.items()):
        result = read(ROOT / event['attempt'] / 'result.json')
        audit.append({'task': task, 'event': event['kind'], 'status': result.get('status'),
                      'result_task': result.get('task'), 'attribution_matches': result.get('task') == task})
    save(PREP / 'diagnosis.json', {'status': 'PASS', 'reproduced_rejections': events,
        'unchanged021_methods': len(read(OLD_FREEZE)['methods']), 'latest_result_attribution_audit': audit,
        'root_cause': 'Our020/021 top-level result producers omitted the required task ID',
        'historical_evidence_and_rejections_preserved': True})
    return {'reproduced_rejections': len(events), 'unchanged_methods': len(read(OLD_FREEZE)['methods'])}


def freeze():
    retained()
    methods = {**read(OLD_FREEZE)['methods'], rel(Path(__file__)): sha(Path(__file__)),
               PLAN: sha(ROOT / PLAN)}
    names = {rel(OLD_FREEZE), rel(OLD_INPUTS), rel(PREP / 'diagnosis.json')}
    for folder in (BASE, PRIOR):
        names.update(rel(folder / n) for n in read(folder / 'outputs.json'))
        names.update((rel(folder / 'outputs.json'), rel(folder / 'admission.json')))
    names.update((rel(INPUTS / 'products.json.gz'), rel(INPUTS / 'profile.json')))
    save(PREP / 'freeze.json', {'methods': methods, 'inputs': {n: sha(ROOT / n) for n in sorted(names)},
        'skeptical_audit': {'verdict': 'PASS', 'baseline': 'Actual retained authority REJECT events',
            'resolved': ['Unchanged177 substantive methods', 'Actual worker boundary before sealing',
                         'Current full consumers and independent adverse checks',
                         'No sealed proof rewrite or whole-task acceptance']}})
    return {'methods': len(methods), 'inputs': len(names), 'audit': 'PASS'}


def frozen():
    data = read(PREP / 'freeze.json')
    for name, expected in {**data['methods'], **data['inputs']}.items():
        assert sha(ROOT / name) == expected, 'Frozen artifact drift: ' + name
    return data


def propose():
    candidate = frozen()
    authority = Authority(ROOT)
    program = read(AUTH / 'program.json')
    assert program['revision'] == 259
    attempts = [e['attempt'] for e in authority.events()
                if e['kind'] == 'ADMIT' and e['budget_key'] == 'basf-meanings']
    assert len(attempts) == program['budgets']['basf-meanings']['maximum_new_attempts'] == 21
    proposal = deepcopy(program)
    proposal['revision'] = 260
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-meanings')
    task['dossier'] = PLAN
    task['reason'] = 'Retained020/021 actual recording rejects missing task attribution; unchanged source/methods, current full proof and real worker boundary required before new partial recording.'
    task['build_criteria_scope'] = []
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(candidate['methods']) +
        list(candidate['inputs']) + [rel(PREP / 'freeze.json'), ROUTES]))
    proposal['budgets']['basf-meanings']['maximum_new_attempts'] = 22
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 260
    for row in routes['tasks']:
        if row['task'] == 'basf-meanings':
            row.update(task_sha256=digest(task), dossier=PLAN,
                remaining='020/021 substantive PASS proofs retained; actual events REJECT missing task attribution. Original source-meaning and legal-exhaustiveness requirements remain open.',
                next_action='Run frozen022 current full verification and consumers, validate its attributed result at actual worker boundary, seal, record, inspect actual event, refresh, return to original source-to-answer gap.')
        if row['task'] == 'finance-conventions':
            row.update(remaining='009 recorded: actual QuantLib1.38 six-period schedule/leg matches independent integer oracle on two declared calendars; complete consumers equal008. Legal entitlement, aggregation, events, rounding and original scope remain separate.',
                next_action='Preserve009 matched package result. Trace original G15 entitlement, aggregation, event-order and rounding requirements to current source-bound consumers; repair an evidenced remaining gap, not a repeated comparison.')
    save(ROOT / ROUTES, routes)
    proposal['continuation_review'].update(plan=PLAN, routes=ROUTES)
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN), ROUTES: sha(ROOT / ROUTES),
        rel(PREP / 'freeze.json'): sha(PREP / 'freeze.json'), rel(PREP / 'diagnosis.json'): sha(PREP / 'diagnosis.json')})
    review = {'baseline': digest(program), 'changes': ['Repair reproduced result-attribution blocker without rewriting020/021',
        'Revalidate complete current BASF proof and real worker boundary', 'Refresh finance009 and actual BASF rejection routes'],
        'skeptical_audit': candidate['skeptical_audit'],
        'evidence_contract': {'question': 'Preserve current complete proof and obtain correct partial RECORD attribution',
            'primary': 'Full020 equality,192 verified decisions,17 refused forgeries, actual worker False then authority RECORD',
            'veto': ['Artifact/method drift', 'Accepted forgery', 'Changed whole answer', 'Wrong recording event'],
            'not_concluded': ['Original task acceptance', 'Exhaustive legal interpretation', 'Actual default', 'Build completion']},
        'scope_unchanged': True, 'budget_unchanged': False, 'original_obligations_preserved': True,
        'budget_revision': {'budget_key': 'basf-meanings', 'previous_maximum': 21, 'new_maximum': 22,
            'retained_attempts': attempts, 'reason': 'Distinct reproduced result-emission defect, not unchanged retry',
            'next_discriminating_check': 'Actual worker envelope validation and independently rechecked full current answer',
            'stop_condition': BOUNDS,
            'same_scope_authorization': 'User refresh master program and continue; local integration repair within existing build'}}
    forecast = resources()['new_bytes'] + 3 * len(encoded(proposal)) + len(encoded(review))
    assert forecast < BOUNDS['new_bytes'] - BOUNDS['reserve_bytes']
    assert OLD_BYTES + forecast < BOUNDS['cumulative_bytes'] - BOUNDS['reserve_bytes']
    save(PROPOSAL, proposal)
    save(REVIEW, review)
    save(PREP / 'storage-forecast.json', {'forecast_bytes': forecast, 'new_program_copies': 3,
        'known_previous_bytes': OLD_BYTES, 'bounds': BOUNDS})
    return {'revision': 260, 'retained_admissions': len(attempts), 'forecast_bytes': forecast}


def admitted():
    frozen()
    authority = Authority(ROOT)
    program, tasks, _ = authority.spec()
    admission = read(HERE / 'admission.json')
    assert program['revision'] == 260 and admission['task'] == 'basf-meanings'
    assert admission['program_sha256'] == digest(program)
    assert admission['task_sha256'] == digest(tasks['basf-meanings'])
    assert admission['binding'] == authority.binding(tasks['basf-meanings'])
    event = next(e for e in authority.events() if e['kind'] == 'ADMIT' and e['attempt'] == rel(HERE))
    assert event['admission_sha256'] == sha(HERE / 'admission.json')
    return tasks['basf-meanings']


def validate():
    from scripts import prospectus_default_verifier as old
    from legalmath.prospectus.successor import service
    retained()
    answer, ordinary, profile = old.baseline()
    valid = old.current.verify_answer(answer, ordinary, profile, expected_profile_sha256=semantic_digest(profile))
    assert valid['checked_answers'] == 192
    adverse = []
    for name, path, value in old.cases():
        try:
            changed = old.recertified(answer, ordinary, profile, name, path, value)
        except ValueError as error:
            assert name == 'numeric-scenario-flag', 'Unexpected certificate-stage refusal'
            adverse.append({'name': name, 'status': 'REFUSED', 'boundary': 'CERTIFICATE', 'error': str(error)})
            continue
        assert name != 'numeric-scenario-flag', 'Expected typed certificate control was accepted'
        try:
            old.current.verify_answer(changed, ordinary, profile, expected_profile_sha256=semantic_digest(profile))
        except ValueError as error:
            adverse.append({'name': name, 'status': 'REFUSED', 'boundary': 'COMPLETE_ANSWER_VERIFIER', 'error': str(error)})
        else:
            raise AssertionError('Accepted recertified forgery: ' + name)
    assert len(adverse) == 17
    assert sum(row['boundary'] == 'COMPLETE_ANSWER_VERIFIER' for row in adverse) == 16
    products = load(INPUTS / 'products.json.gz')
    observed = service.consume(products, ROOT, mode='frozen', default_f_profile=profile,
        expected_default_f_profile_sha256=semantic_digest(profile))
    omitted = service.consume(products, ROOT, mode='frozen')
    assert observed == answer and omitted == ordinary, 'Complete current consumer changed'
    save(HERE / 'verification.json', {'status': 'PASS', 'valid': valid, 'adverse': adverse,
        'full_current_consumer_equal020': True, 'full_omitted_equal020': True,
        'answer_reference': {'path': rel(BASE / 'current-answer.json.gz'),
            'sha256': sha(BASE / 'current-answer.json.gz'), 'semantic_sha256': semantic_digest(observed)},
        'ordinary_reference': {'path': rel(BASE / 'ordinary-answer.json.gz'),
            'sha256': sha(BASE / 'ordinary-answer.json.gz'), 'semantic_sha256': semantic_digest(omitted)},
        'source_meaning_proved': False, 'candidate_set_exhaustive': False})
    return {'independent_decisions': 192, 'recertified_verifier_refusals': 16,
            'certificate_refusals': 1, 'complete_current_equal020': True}


def seal():
    from legalmath.prospectus.successor import service
    assert Path(service.__file__).resolve().is_relative_to(ROOT / 'src')
    task = admitted()
    result = {'status': 'PASS', 'task': task['id'], 'whole_task_complete': False,
        'build_criteria_claimed': [], 'classification': 'CURRENT_PROOF_AND_RESULT_ATTRIBUTION_REPAIR',
        'verification': read(HERE / 'verification.json'), 'historical_rejections': read(PREP / 'diagnosis.json')['reproduced_rejections'],
        'resources_before_seal': resources()}
    save(HERE / 'result.json', result)
    assert worker_validate(ROOT, HERE, task) is False, 'A partial result must not become whole-task acceptance'
    controls = []
    for name, change in (('missing-task', {'task': None}), ('wrong-task', {'task': 'finance-conventions'}),
                         ('failed-status', {'status': 'FAIL'})):
        value = {**result, **change}
        if name == 'missing-task':
            del value['task']
        folder = HERE / 'envelope-controls' / name
        save(folder / 'result.json', value)
        try:
            worker_validate(ROOT, folder, task)
        except ValueError as error:
            controls.append({'name': name, 'verdict': 'REFUSED', 'error': str(error)})
        else:
            raise AssertionError('Wrong result envelope accepted: ' + name)
    save(HERE / 'envelope-controls.json', {'valid_disposition': 'PARTIAL_FALSE', 'adverse': controls})
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'command': 'stages/*/started.json', 'environment': sys.executable, 'python': sys.version,
        'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1 before imports', 'seeds': 'N/A deterministic',
        'plan': PLAN, 'result': rel(HERE / 'RESULT.md'), 'data': rel(PREP / 'freeze.json'),
        'module_origins': {'worker_validate': str(sys.modules[worker_validate.__module__].__file__),
                           'service': str(service.__file__)},
        'resources_before_seal': resources(), 'historical_known_seconds': OLD_SECONDS,
        'historical_known_bytes': OLD_BYTES, 'earlier_history': 'UNKNOWN', 'bounds': BOUNDS})
    note = '''# BASF result attribution repaired with current substantive evidence

The actual020/021 authority REJECT events arose because our top-level result
files omitted the admitted task ID. Both sealed proofs and rejection events
remain unchanged. This new result includes the correct task ID and passes the
actual worker boundary as partial evidence; three malformed envelopes are
refused. No package defect is implicated.

The unchanged current verifier checks all192 decisions and refuses16
recertified explanatory forgeries. The typed certificate boundary refuses the
remaining numeric-flag forgery before verifier entry. Both complete consumers equal
the sealed020 answers, including omitted-option behavior. Large identical
answers are retained by authenticated immutable references. The177 prior
substantive methods and original inputs remain identical.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Limit |
| --- | --- | --- | --- | --- | --- |
| Submit correctly attributed partial evidence | Current whole-answer equality, independent decisions and adverse checks pass; actual worker returns False | No observed source/method drift or accepted forgery | Source interpretations remain conditional and nonexhaustive | Record, inspect actual RECORD event, refresh and return to original source-to-answer requirements | No whole-task or build completion |
| Attribute prior rejection to our producer | Exact missing-task field reproduces actual boundary failure | Old proofs and events preserved | Other producers need their own boundary check | Use actual validator before sealing future results | No weakening of acceptance |

A shared source-reading error remains the strongest alternative explanation
for substantive agreement. An accepted forgery, changed complete answer,
artifact drift or new recording rejection would overturn the corresponding
engineering conclusion. External adviser opinion is not a prerequisite.
'''
    with (HERE / 'RESULT.md').open('x') as stream:
        stream.write(note)
    return {'status': 'SEALED_PARTIAL', 'worker_disposition': False, 'bad_envelopes_refused': len(controls)}


def main():
    assert len(sys.argv) == 2 and sys.argv[1] in STAGES
    stage = sys.argv[1]
    base = PREP if stage in PREPARATION else HERE
    before = resources()
    limit = min(BOUNDS['stage_seconds'], int(BOUNDS['new_seconds'] - before['new_measured_stage_seconds']))
    assert limit > 5
    save(base / 'stages' / stage / 'started.json', {'argv': ['.venv/bin/python', '-B', '-m',
        'scripts.prospectus_default_result_attribution', stage], 'utc': datetime.now(timezone.utc).isoformat(),
        'timeout_seconds': limit, 'resources_before': before})
    def alarm(*args):
        raise TimeoutError('Reviewed result-attribution stage bound')
    signal.signal(signal.SIGALRM, alarm)
    signal.alarm(limit)
    started = time.monotonic()
    try:
        for predecessor in STAGES[stage]:
            folder = PREP if predecessor in PREPARATION else HERE
            assert read(folder / 'stages' / predecessor / 'result.json')['status'] == 'PASS'
        if stage not in PREPARATION:
            admitted()
        detail = globals()[stage]()
        receipt = {'status': 'PASS', 'detail': detail, 'wall_seconds': time.monotonic() - started}
    except Exception as error:
        receipt = {'status': 'FAIL', 'error': repr(error), 'wall_seconds': time.monotonic() - started}
        save(base / 'stages' / stage / 'result.json', receipt)
        if base == HERE:
            if not (HERE / 'result.json').exists():
                save(HERE / 'result.json', {'status': 'FAIL', 'task': 'basf-meanings',
                    'whole_task_complete': False, 'failed_stage': stage, 'error': repr(error)})
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
                if p.is_file() and p.name not in {'admission.json', 'outputs.json'}})
        raise
    finally:
        signal.alarm(0)
    save(base / 'stages' / stage / 'result.json', receipt)
    if stage == 'seal':
        save(HERE / 'final-resources.json', resources())
        save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
            if p.is_file() and p.name not in {'admission.json', 'outputs.json'}})
    print(json.dumps({'stage': stage, **receipt, 'resources': resources()}), flush=True)


if __name__ == '__main__':
    main()
