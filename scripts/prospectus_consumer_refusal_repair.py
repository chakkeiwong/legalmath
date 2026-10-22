"""Immutable continuation281; retain failed280 and its correct actual refusal."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from scripts import prospectus_internal_consumer_continuation as prior
from scripts.prospectus_margin_preparation import AUTH, read, save, sha, relative
from scripts.prospectus_consumer_refusal_oracle import RULES, mutation, check_exception, order_preflight
from legalmath.prospectus.successor import service

PREP = AUTH / 'reviews/consumer-refusal-281'
HERE = AUTH / 'attempts/basf-references/attempt-022'
PLAN = 'docs/plans/prospectus-consumer-refusal-repair-2026-10-18.md'
METHODS = ('scripts/prospectus_consumer_refusal_oracle.py', 'scripts/prospectus_consumer_refusal_repair.py')
STAGES = ('reuse', 'adjudicate-drop', *('consumer-' + c for c in RULES if c != 'closure-drop'), 'validate', 'seal')


def costs():
    original = prior.costs()
    receipts = [f for folder in (PREP, HERE) if folder.exists() for f in folder.glob('stages/*/*.json')
                if f.name in ('result.json', 'failure.json')]
    seconds = original['new_measured_seconds'] + sum(read(f)['wall_seconds'] for f in receipts)
    counted = {f for folder in (PREP, HERE) if folder.exists() for f in folder.rglob('*')
               if f.is_file() and '__pycache__' not in f.parts}
    counted.update(ROOT / name for name in (*METHODS, PLAN))
    counted.add(AUTH / 'revisions/0281.json')
    size = original['new_counted_bytes'] + sum(f.stat().st_size for f in counted if f.exists())
    if seconds >= 3600 or size >= 188 * 1024**2:
        raise ValueError('Cumulative279/280/281 resource bound exhausted')
    return {**original, 'new_measured_seconds': seconds, 'new_counted_bytes': size,
            'new_seconds_bound': 3600, 'prior_admissions_retained': 21,
            'new_measured_allowance_added': 0}


def protected():
    prior.old.frozen()
    for name, checksum in read(prior.PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum, 'Frozen280 drift: ' + name
    for name, checksum in read(prior.HERE / 'admission.json')['binding'].items():
        assert sha(ROOT / name) == checksum, 'Admission021 drift: ' + name


def frozen():
    from legalmath.prospectus.execution_authority import digest
    protected()
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum, 'Refusal continuation drift: ' + name
    admission = read(HERE / 'admission.json')
    for name, checksum in admission['binding'].items():
        assert sha(ROOT / name) == checksum, 'Admission022 drift: ' + name
    assert digest(read(AUTH / 'program.json')) == admission['program_sha256']


def close_failed():
    prior.frozen()
    failure = read(prior.HERE / 'stages/consumer-closure-drop/failure.json')
    assert failure['type'] == 'ValueError' and failure['message'] == RULES['closure-drop'][0]
    passed = {d.name: read(d / 'result.json') for d in (prior.HERE / 'stages').iterdir()
              if (d / 'result.json').exists()}
    assert len(passed) == 13 and all(r['status'] == 'PASS' for r in passed.values())
    assert not (prior.HERE / 'candidate-answer-reconciliation.json.gz').exists()
    resources = costs()
    save(prior.HERE / 'result.json', {'status': 'PASS', 'task': 'basf-references',
        'result_kind': 'FAILED_TRIAL_RETENTION_AND_DIAGNOSIS', 'trial_status': 'FAIL',
        'original_task_complete': False, 'passed_stages': passed,
        'failed_stage': 'consumer-closure-drop', 'failure': failure,
        'actual_consumer_refused': True, 'wrapper_expected_later_error': True,
        'complete_ordinary_answers_retained_and_verified': 2,
        'actual_upstream_refusals': 11, 'successful_downstream_control_receipts': 3,
        'final_reconciliation_performed': False, 'resources': resources,
        'next_action': 'Reviewed exact-order continuation281; preserve failure and adjudicate retained refusal separately'})
    save(prior.HERE / 'run-manifest.json', {
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'commands': [read(d / 'started.json')['command'] for d in sorted((prior.HERE / 'stages').iterdir())
                     if (d / 'started.json').exists()],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU deliberately hidden',
        'data_version': sha(prior.old.PREP / 'source-review.json'), 'seeds': 'N/A deterministic',
        'wall_time': resources, 'plan': prior.PLAN, 'result': relative(prior.HERE / 'result.json'),
        'artifacts': relative(prior.HERE), 'method_freeze': sha(prior.PREP / 'freeze.json')})
    with (prior.HERE / 'RESULT.md').open('x') as stream:
        stream.write('''# Correct consumer refusal exposed a harness-order defect

Both complete ordinary answers were retained and independently verified.
Eleven upstream controls and the roots, reachability and cycle consumer controls
passed. The missing-closure consumer refused correctly at the earlier reviewed
v3 check. Its wrapper required a later generic message and failed. That failure
remains FAIL; no later controls or final reconciliation ran. This is a local
oracle defect, not consumer acceptance or an external-package limitation.

| Decision | Primary criterion | Veto status | Uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain failed trial | Two whole answers and earlier controls retained | Harness validity failed | Remaining controls and final mapping unchecked | Review exact-order continuation; no unchanged retry | Original task/build complete |

PASS in result.json classifies retention only; trial_status remains FAIL. All
costs, actual input identities, successful evidence and the failed wrapper are
preserved. A new adjudication may account for the retained actual refusal only
after exact frozen-input reconstruction, without relabelling the old receipt.
''')
    prior.frozen()
    save(prior.HERE / 'outputs.json', {str(f.relative_to(prior.HERE)): sha(f)
        for f in sorted(prior.HERE.rglob('*')) if f.is_file() and '__pycache__' not in f.parts})
    return {'status': 'PASS', 'trial_status': 'FAIL', 'passed_stages': len(passed), 'resources': resources}


def manifest():
    assert read(prior.HERE / 'result.json')['trial_status'] == 'FAIL'
    for name, checksum in read(prior.HERE / 'outputs.json').items():
        assert sha(prior.HERE / name) == checksum, 'Retained021 changed: ' + name


def preflight_matrix():
    protected()
    manifest()
    candidate, _ = prior.retained('candidate-answer')
    omitted, _ = prior.retained('missing-answer')
    return order_preflight(candidate, omitted)


def reuse():
    manifest()
    receipts = {}
    for label in ('candidate-verify', 'missing-verify', 'upstream-controls',
                  'consumer-roots', 'consumer-reachable', 'consumer-cycle'):
        row = read(prior.HERE / 'stages' / label / 'result.json')
        assert row['status'] == 'PASS'
        if label.endswith('-verify'):
            assert row['complete_answer_checked'] and row['ordinary_schema_checked']
            p, answer = prior.retained(label.replace('-verify', '-answer'))
            prior.ordinary_schema(answer, prior.baseline('candidate-answer')[1], expected_additions=('internal_references',))
        receipts[label] = {'path': relative(prior.HERE / 'stages' / label / 'result.json'),
                           'sha256': sha(prior.HERE / 'stages' / label / 'result.json')}
    return {'status': 'PASS', 'sealed_manifest_sha256': sha(prior.HERE / 'outputs.json'),
            'reused_receipts': receipts, 'new_actual_consumers_run': 0}


def adjudicate_drop():
    p, _ = prior.retained('candidate-answer')
    _, receipt = mutation(p, 'closure-drop')
    original = read(prior.HERE / 'controls/consumer-closure-drop-input.json')
    for key in ('case', 'original_products_sha256', 'forged_products_sha256', 'mutated_semantic_sha256', 'validly_resealed'):
        assert receipt[key] == original[key], 'Retained actual refusal input differs: ' + key
    failure = read(prior.HERE / 'stages/consumer-closure-drop/failure.json')
    assert failure['type'] == 'ValueError' and failure['message'] == RULES['closure-drop'][0]
    assert original['expected_refusal_fragment'] == 'Consumed reference closure differs'
    save(HERE / 'controls/closure-drop-adjudication.json', {
        'retained_actual_failure': relative(prior.HERE / 'stages/consumer-closure-drop/failure.json'),
        'retained_failure_sha256': sha(prior.HERE / 'stages/consumer-closure-drop/failure.json'),
        'reconstructed_input': receipt, 'original_wrapper_status': 'FAIL',
        'new_adjudication': 'ACTUAL_SUBSTANTIVE_REFUSAL_CONFIRMED',
        'new_actual_call': False, 'original_traceback_retained': False,
        'origin_evidence': 'Frozen verification order, nonempty v3 unresolved targets, missing Q1 closure and exact error literal'})
    return {'status': 'PASS', 'case': 'consumer-closure-drop', 'reused_actual_refusal': failure['message'],
            'old_failure_preserved': True, 'new_actual_call': False, 'exact_input_reconstruction': True}


def consumer(label):
    case = label.removeprefix('consumer-')
    p, _ = prior.retained('missing-answer' if case == 'subquestion-missing' else 'candidate-answer')
    forged, receipt = mutation(p, case)
    save(HERE / 'controls' / (label + '-input.json'), receipt)
    try:
        service.consume(forged, ROOT, mode='frozen')
    except ValueError as exc:
        actual = check_exception(case, exc)
        save(HERE / 'controls' / (label + '-actual.json'), actual)
        return {'status': 'PASS', 'case': label, **actual}
    raise ValueError('Forged internal consumer accepted: ' + label)


def validate():
    # The frozen function writes only its original HERE. Reconstruct the same
    # comparison here so new reconciliation never changes sealed021.
    from scripts.prospectus_typed_delta import equal
    from scripts.prospectus_internal_reference_preparation import IDS, LEDGER
    for label, missing in (('candidate-answer', ()), ('missing-answer', IDS)):
        p, answer = prior.retained(label)
        prior.ordinary_schema(answer, prior.baseline('candidate-answer')[1], expected_additions=('internal_references',))
        ledger = read(AUTH / 'attempts/basf-references/attempt-019/candidate-answer-reconciliation.json.gz')
        originals = deepcopy([r['original'] for r in ledger['records']])
        rows = {r['id']: r for r in p['P3']['payload']['interpretation_input']['reference_admission']['references']}
        for (family, index), key in zip(LEDGER, IDS):
            record = next(r for r in ledger['records'] if r['family'] == family and r['index'] == index)
            if key in rows:
                record.update(current_reference=rows[key], current_status='CURRENT_LINK_WITH_CONSERVATIVE_CLOSURE',
                              complete_legal_interpretation=False)
        equal([r['original'] for r in ledger['records']], originals, 'Original inventory changed')
        expected = read(prior.old.PREP / 'reconciliation-proposed.json.gz') if not missing else read(
            AUTH / 'attempts/basf-references/attempt-019/candidate-answer-reconciliation.json.gz')
        equal(ledger, expected, 'Current internal mapping differs')
        save(HERE / (label + '-reconciliation.json.gz'), ledger)
    return {'status': 'PASS', 'original_inventory_records': 60, 'original_task_complete': False}


def seal():
    resources = costs()
    save(HERE / 'result.json', {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'new_source_links': 10, 'reviewed_source_links': 47, 'covered_original_records': 48,
        'actual_ordinary_answers': 2, 'actual_upstream_refusals': 11, 'actual_consumer_refusals': 15,
        'new_actual_consumer_refusals': 11, 'reused_successful_consumer_receipts': 3,
        'separately_adjudicated_actual_refusals': 1, 'original_inventory_records': 60,
        'retained_answers': relative(prior.HERE), 'retained_failed_trials': [relative(prior.old.HERE), relative(prior.HERE)],
        'resources': resources, 'remaining': ['Statutory originals and editions/application',
            'Unqualified defined terms', 'Original acceptance and general discovery'],
        'next_action': 'Continue reviewed statutory/definition/discovery remainder using combined021/022 evidence'})
    save(HERE / 'run-manifest.json', {
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'commands': [read(HERE / 'stages' / s / 'started.json')['command'] for s in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU deliberately hidden',
        'data_version': sha(prior.old.PREP / 'source-review.json'), 'seeds': 'N/A deterministic',
        'wall_time': resources, 'plan': PLAN, 'result': relative(HERE / 'result.json'),
        'artifacts': relative(HERE), 'method_freeze': sha(PREP / 'freeze.json')})
    with (HERE / 'RESULT.md').open('x') as stream:
        stream.write('''# Internal-reference consumer controls completed

Ten complete internal targets and both ordinary answers passed the retained
independent reconstruction. All original15 actual consumer controls are
accounted for: three successful021 receipts, its separately adjudicated actual
missing-closure refusal, and eleven new exact-message/origin refusals. Eleven
upstream refusals remain bound. All60 original records survive;47 reviewed links
cover48 records. UNKNOWN headings and conservative source cycles remain visible.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain finite internal integration | Whole answers, intervals, closure and15 actual adverse refusals checked | No promotion veto in this trial | Statutory editions/application, definitions and discovery | Continue original remainder | Original task/build complete |

020 and021 remain failed trials.021's consumer refused correctly; its harness
expected the wrong verification order. Separate adjudication retained the old
failure and exactly reconstructed its input without a new actual call. New
controls check exact substantive traceback origin. These were local integration
and verifier defects; no package limitation is established. The weakest evidence
is shared source interpretation; contrary primary-source evidence could overturn
the finite reading. Test totals and timings establish no legal completeness.
''')
    return {'status': 'PASS', 'original_task_complete': False, 'resources': resources}


def propose():
    from legalmath.prospectus.execution_authority import Authority, CODE, digest
    protected()
    program = read(AUTH / 'program.json')
    assert program['revision'] == 280
    manifest()
    assert read(PREP / 'stages/preflight-matrix/result.json')['status'] == 'PASS'
    attempts = [e['attempt'] for e in Authority(ROOT).events() if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 21
    bindings = {relative(f): sha(f) for folder in (prior.HERE, PREP) for f in sorted(folder.rglob('*'))
                if f.is_file() and '__pycache__' not in f.parts}
    for name in (*CODE, PLAN, *METHODS):
        bindings[name] = sha(ROOT / name)
    save(PREP / 'freeze.json', {'bindings': bindings})
    proposal = deepcopy(program)
    proposal['revision'] = 281
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=relative(PREP / 'PRE-ADMISSION-REVIEW.md'),
        reason='Correct exact refusal order after retained correct consumer rejection; finish all original internal controls',
        consumer_refusal_repair={'failed_trial': relative(prior.HERE), 'review': relative(PREP),
            'bounds': {'stage_seconds': 180, 'cumulative_279_280_281_seconds': 3600, 'bytes': 192 * 1024**2},
            'original_task_complete': False, 'further_harness_retry_allowed': False})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [relative(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 22
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 281
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(dossier=PLAN, task_sha256=digest(task),
                remaining='021 whole answers verified; wrong expected refusal order interrupted controls. Statutory/definition/discovery remainder persists.',
                next_action='Preserve021 failure; exact-order controls and60-record reconciliation, then source remainder.',
                acceptance='Independent source/whole-answer checks and all15 actual refusals; partial original-task evidence.',
                stop_condition='22 cumulative admissions;180s stages;3600s cumulative279/280/281;192MiB with4MiB reserve;no unchanged retry.')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=relative(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN), relative(PREP / 'routes.json'): sha(PREP / 'routes.json'),
                                                      relative(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    review = {'baseline': digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'original_obligations_preserved': True,
        'changes': ['Audit complete remaining matrix against verifier order', 'Exact message and traceback origin checks',
                    'Preserve021 failure and separately adjudicate its correct refusal without replay'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'review': relative(PREP / 'PRE-ADMISSION-REVIEW.md'),
                            'production_unchanged': True, 'whole_task_acceptance_claimed': False},
        'evidence_contract': {'primary': 'Independent whole answers, original intervals/closure, all15 actual substantive refusals and60-record reconciliation',
            'veto': ['Accepted forgery', 'Wrong source or unrelated answer', 'Hidden uncertainty', 'Unexpected refusal', 'Frozen/harness/resource invalidity'],
            'not_concluded': ['Statutory application', 'Automatic discovery', 'Universal correctness', 'Whole task/build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 21, 'new_maximum': 22,
            'retained_attempts': attempts, 'reason': 'Reproduced oracle-order defect despite actual correct consumer refusal; distinct comprehensively reviewed repair',
            'next_discriminating_check': 'Exact reconstructed retained refusal plus all eleven remaining actual controls',
            'stop_condition': '180s stages;3600s cumulative279/280/281;192MiB;no unchanged/automatic harness retry',
            'same_scope_authorization': 'User directs refreshing master program and continued general build with internally demonstrated conditional correctness'},
        'resources_before_admission': costs(), 'new_measured_allowance_added': 0}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 281, 'prior_admissions': 21, 'resources': costs()}


def main():
    label = sys.argv[1]
    if label == 'propose':
        print(json.dumps(propose()))
        return
    preparation = label in ('close-failed', 'preflight-matrix')
    if not preparation:
        assert label in STAGES
        frozen()
        index = STAGES.index(label)
        if index:
            assert read(HERE / 'stages' / STAGES[index - 1] / 'result.json')['status'] == 'PASS'
    resources = costs()
    folder = (PREP if preparation else HERE) / 'stages' / label
    assert not (folder / 'started.json').exists(), 'Stage already started; no unchanged retry'
    seconds = min(180, math.floor(3600 - resources['new_measured_seconds']))
    assert seconds > 0
    save(folder / 'started.json', {'command': ['.venv/bin/python', '-m', 'scripts.prospectus_consumer_refusal_repair', label],
         'stage_seconds': seconds, 'started_at': datetime.now(timezone.utc).isoformat()})
    began = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Refusal repair stage bound')))
    signal.alarm(seconds)
    try:
        result = consumer(label) if label.startswith('consumer-') else globals()[label.replace('-', '_')]()
        if not preparation:
            frozen()
        costs()
        assert result['status'] == 'PASS'
        result['wall_seconds'] = time.monotonic() - began
        save(folder / 'result.json', result)
        if label == 'seal':
            save(HERE / 'outputs.json', {str(f.relative_to(HERE)): sha(f) for f in sorted(HERE.rglob('*'))
                if f.is_file() and '__pycache__' not in f.parts})
        print(json.dumps({k: v for k, v in result.items() if k not in ('matrix', 'traceback', 'reused_receipts')}))
    except BaseException as exc:
        save(folder / 'failure.json', {'type': type(exc).__name__, 'message': str(exc), 'wall_seconds': time.monotonic() - began})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
