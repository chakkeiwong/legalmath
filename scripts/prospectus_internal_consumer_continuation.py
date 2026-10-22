"""Receipt-preserving continuation280 of the failed frozen279 verification."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import os
import signal
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from scripts import prospectus_internal_references as old
from scripts.prospectus_margin_preparation import AUTH, DONOR, read, save, sha, relative, products
from scripts.prospectus_internal_reference_preparation import IDS, LEDGER, reseal
from scripts.prospectus_financial_references import retained as baseline
from scripts.prospectus_internal_consumer_oracle import ordinary_schema, verify
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

PREP = AUTH / 'reviews/internal-consumer-280'
HERE = AUTH / 'attempts/basf-references/attempt-021'
PLAN = 'docs/plans/prospectus-internal-consumer-continuation-2026-10-18.md'
CONSUMERS = old.CONSUMERS
STAGES = ('reuse', 'candidate-downstream', 'candidate-consume', 'candidate-verify',
          'missing-p3', 'missing-p3-verify', 'missing-downstream', 'missing-consume',
          'missing-verify', 'upstream-controls', *('consumer-' + c for c in CONSUMERS), 'validate', 'seal')
LIMIT = 3600


def costs():
    files = [f for pattern in ('preparation*result.json', 'preparation*failure.json',
                              'preflight*result.json', 'preflight*failure.json') for f in old.PREP.glob(pattern)]
    files += [f for pattern in ('stages/*/result.json', 'stages/*/failure.json') for f in old.HERE.glob(pattern)]
    files += [f for pattern in ('preflight*result.json', 'preflight*failure.json') for f in PREP.glob(pattern)]
    files += [f for pattern in ('stages/*/result.json', 'stages/*/failure.json') for f in HERE.glob(pattern)]
    seconds = sum(read(f)['wall_seconds'] for f in files)
    counted = {f for folder in (old.PREP, old.HERE, PREP, HERE) if folder.exists()
               for f in folder.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
    counted.update(ROOT / f for f in (old.PLAN, PLAN,
        'scripts/prospectus_internal_reference_preparation.py', 'scripts/prospectus_internal_reference_oracle.py',
        'scripts/prospectus_internal_revision.py', 'scripts/prospectus_internal_references.py',
        'scripts/prospectus_internal_consumer_oracle.py', 'scripts/prospectus_internal_consumer_continuation.py',
        'src/legalmath/prospectus/successor/basf_internal_references.py', *old.TESTS))
    counted.update((old.SPEC, AUTH / 'program.json', AUTH / 'revisions/0279.json', AUTH / 'revisions/0280.json'))
    size = sum(f.stat().st_size for f in counted if f.exists())
    if seconds >= LIMIT or size >= 188 * 1024**2:
        raise ValueError('Cumulative279/280 internal reference resource bound exhausted')
    return {'new_measured_seconds': seconds, 'new_counted_bytes': size,
        'new_seconds_bound': LIMIT, 'previous_seconds_bound': 1800,
        'new_bytes_bound': 192 * 1024**2, 'reserve_bytes': 4 * 1024**2,
        'prior_admissions_retained': 20, 'unmeasured_authoring_controller_time': 'UNKNOWN'}


def close_failed():
    old.frozen()
    failure = read(old.HERE / 'stages/candidate-answer/failure.json')
    assert failure['type'] == 'KeyError' and failure['message'] == "'dependencies'"
    assert not (old.HERE / 'candidate-answer.json.gz').exists()
    stage_results = {s: read(old.HERE / 'stages' / s / 'result.json') for s in ('tests', 'candidate-p3')}
    assert all(r['status'] == 'PASS' for r in stage_results.values())
    resources = old.costs()
    save(old.HERE / 'result.json', {'status': 'PASS', 'task': 'basf-references',
        'result_kind': 'FAILED_TRIAL_RETENTION_AND_DIAGNOSIS', 'trial_status': 'FAIL',
        'original_task_complete': False, 'retained_stage_results': stage_results,
        'failed_stage': 'candidate-answer', 'failure': failure,
        'ordinary_consume_returned_before_verifier': True, 'ordinary_answer_retained': False,
        'ordinary_answer_verified': False, 'resources': resources,
        'next_action': 'Review distinct continuation280; correct ordinary schema, retain before verify, preserve frozen methods and all costs'})
    save(old.HERE / 'run-manifest.json', {
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'commands': [read(old.HERE / 'stages' / s / 'started.json')['command']
                     for s in ('tests', 'candidate-p3', 'candidate-answer')],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU deliberately hidden',
        'data_version': sha(old.PREP / 'source-review.json'), 'seeds': 'N/A deterministic',
        'wall_time': resources, 'plan': old.PLAN, 'result': relative(old.HERE / 'result.json'),
        'artifacts': relative(old.HERE), 'method_freeze': sha(old.PREP / 'freeze.json')})
    note = '''# Failed verification trial retained

The201 focused tests and ten-target independent P3 reconstruction passed.
The candidate-answer stage failed with KeyError('dependencies') after ordinary
consume returned. Its full answer was never retained and is not verified.
Dependencies are exposed only by artifact export; the ordinary API does not
promise that field. This is a local verifier defect, not a production or package
limitation. No later stage ran, and no unchanged retry is authorized.

| Decision | Primary criterion | Veto status | Uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain and diagnose failed trial | Tests/P3 evidence retained; full-answer criterion unfulfilled | Harness validity failed | Returned ordinary answer unavailable | Separately reviewed corrected continuation | Complete internal integration or whole build |

PASS in result.json classifies retention/diagnosis only; trial_status is FAIL.
All preparation, preflight and stage costs remain cumulative. Original methods
and source evidence are unchanged. Continuation requires a reviewed revision of
the same task, not a retry or a new task with reset counters.
'''
    target = old.HERE / 'RESULT.md'
    with target.open('x') as stream:
        stream.write(note)
    old.frozen()
    save(old.HERE / 'outputs.json', {str(f.relative_to(old.HERE)): sha(f) for f in sorted(old.HERE.rglob('*'))
        if f.is_file() and '__pycache__' not in f.parts})
    return {'status': 'PASS', 'trial_status': 'FAIL', 'resources': resources}


def frozen():
    old.frozen()
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum, 'Continuation binding drift: ' + name
    admission = read(HERE / 'admission.json')
    for name, checksum in admission['binding'].items():
        assert sha(ROOT / name) == checksum, 'Admission binding drift: ' + name
    from legalmath.prospectus.execution_authority import digest as authority_digest
    assert authority_digest(read(AUTH / 'program.json')) == admission['program_sha256']


def retain(label, p, answer=None):
    from scripts.prospectus_typed_delta import changes, apply, equal
    original = products()
    delta = changes(original, p)
    equal(apply(original, delta), p, 'Lossy continuation products')
    row = {'products_delta': delta, 'products_sha256': digest(p)}
    if answer is not None:
        donor = read(DONOR / 'installed-answer/ordinary-answer.json.gz')
        delta = changes(donor, answer)
        equal(apply(donor, delta), answer, 'Lossy continuation answer')
        row.update(answer_delta=delta, answer_sha256=digest(answer))
    save(HERE / (label + '.json.gz'), row)


def retained(label):
    from scripts.prospectus_typed_delta import apply
    row = read(HERE / (label + '.json.gz'))
    p = apply(products(), row['products_delta'])
    assert digest(p) == row['products_sha256']
    answer = None
    if 'answer_delta' in row:
        answer = apply(read(DONOR / 'installed-answer/ordinary-answer.json.gz'), row['answer_delta'])
        assert digest(answer) == row['answer_sha256']
    return p, answer


def schema_preflight():
    _, actual = baseline('candidate-answer')
    ordinary_schema(actual, actual)
    refusals = []
    for case in ('dependencies', 'source_map', 'report-hash'):
        altered = deepcopy(actual)
        if case == 'report-hash':
            altered['report_sha256'] = '0' * 64
        else:
            altered[case] = []
        try:
            ordinary_schema(altered, actual)
        except (ValueError, AssertionError):
            refusals.append(case)
        else:
            raise ValueError('Ordinary schema accepted altered field/hash: ' + case)
    extended = {**actual, 'internal_references': {}}
    extended['report_sha256'] = digest({k: v for k, v in extended.items() if k != 'report_sha256'})
    ordinary_schema(extended, actual, expected_additions=('internal_references',))
    return {'status': 'PASS', 'real_comparator_schema_keys': sorted(actual),
        'actual_ordinary_schema_checked': True, 'adverse_schema_refusals': refusals,
        'explicit_reviewed_report_addition_checked': 'internal_references',
        'production_unchanged': True}


def reuse():
    manifest = read(old.HERE / 'outputs.json')
    assert read(old.HERE / 'result.json')['trial_status'] == 'FAIL'
    for name, checksum in manifest.items():
        assert sha(old.HERE / name) == checksum
    p, _ = old.retained('candidate-p3')
    assert read(old.HERE / 'stages/tests/result.json')['status'] == 'PASS'
    assert read(old.HERE / 'stages/candidate-p3/result.json')['status'] == 'PASS'
    return {'status': 'PASS', 'reused_manifest_sha256': sha(old.HERE / 'outputs.json'),
        'candidate_products_sha256': digest(p), 'reused_test_cases': 201,
        'reused_independent_candidate_p3': True, 'failed_answer_reused': False}


def downstream(label):
    prefix = label.split('-')[0]
    p, _ = old.retained('candidate-p3') if prefix == 'candidate' else retained('missing-p3')
    a, b = p['P4']['payload'], p['P5']['payload']
    p['P4'] = service.law_product(p['P1'], p['P3'], a['cases'], a['law_input'])
    p['P5'] = service.financial_product(p['P1'], p['P2'], p['P3'], b['cases'], b['scenario_input'])
    retain(label, p)
    return {'status': 'PASS', 'products_sha256': digest(p), 'retained_before_verification': True}


def consume(label):
    prefix = label.split('-')[0]
    p, _ = retained(prefix + '-downstream')
    answer = service.consume(p, ROOT, mode='frozen')
    retain(prefix + '-answer', p, answer)
    return {'status': 'PASS', 'products_sha256': digest(p), 'answer_sha256': digest(answer),
        'retained_before_verification': True, 'ordinary_include_artifacts': False}


def missing_p3():
    p, _ = baseline('candidate-answer')
    value = deepcopy(p['P3']['payload']['interpretation_input'])
    p['P3'] = service.interpretation_product(p['P1'], p['P2'], value)
    retain('missing-p3', p)
    return {'status': 'PASS', 'products_sha256': digest(p), 'retained_before_verification': True}


def upstream_controls():
    p, _ = baseline('candidate-answer')
    cases = ('truncate', 'tax-exception', 'holder-ending', 'substitution-ending',
             'proof-ending', 'rename', 'question', 'edition', 'duplicate', 'language', 'discovery')
    for case in cases:
        began = time.monotonic()
        value = deepcopy(p['P3']['payload']['interpretation_input'])
        rows = deepcopy(read(old.PREP / 'packet.json')['references'])
        if case == 'truncate':
            rows[0]['targets'] = rows[0]['targets'][-1:]
        elif case == 'tax-exception':
            rows[1]['targets'] = rows[1]['targets'][:-4]
        elif case == 'holder-ending':
            rows[4]['targets'] = rows[4]['targets'][:-8]
        elif case == 'substitution-ending':
            rows[6]['targets'].pop()
        elif case == 'proof-ending':
            rows[9]['targets'].pop()
        elif case == 'rename':
            rows[0]['id'] = 'hidden'
        elif case == 'question':
            rows[0]['questions'] = ['Q1']
        elif case == 'edition':
            rows[0]['source']['source_sha256'] = '0' * 64
        elif case == 'duplicate':
            rows.append(deepcopy(rows[0]))
        elif case == 'language':
            rows[0]['targets'][0]['language'] = 'en'
        else:
            rows[0]['discovery_ids'] = rows[1]['discovery_ids']
        value['reference_admission']['references'].extend(rows)
        try:
            service.interpretation_product(p['P1'], p['P2'], value)
        except ValueError as exc:
            if 'BASF internal' not in str(exc):
                raise
            save(HERE / 'controls' / (case + '.json'), {'status': 'PASS', 'case': case,
                'actual_P3_refusal': str(exc), 'wall_seconds': time.monotonic() - began})
        else:
            raise ValueError('Invalid internal P3 accepted: ' + case)
    return {'status': 'PASS', 'actual_P3_refusals': list(cases)}


def consumer(label):
    case = label.removeprefix('consumer-')
    p, _ = retained('missing-answer' if case == 'subquestion-missing' else 'candidate-answer')
    semantic = deepcopy(p['P3']['payload'])
    closure = next(d for d in semantic['dependencies'] if d['id'] == 'reference-closure:Q1')
    required = 'Consumed reference closure differs'
    if case in ('roots', 'reachable'):
        closure[case].pop()
    elif case == 'cycle':
        victim = next(s for s in closure['unresolved'] if s.startswith('Unsupported reference cycle:'))
        closure['unresolved'].remove(victim)
    elif case == 'closure-drop':
        semantic['dependencies'].remove(closure)
    elif case == 'closure-duplicate':
        semantic['dependencies'].append(deepcopy(closure))
    elif case == 'closure-invent':
        semantic['dependencies'].append({**deepcopy(closure), 'id': 'reference-closure:invented'})
    elif case.startswith('dependency-'):
        dep = next(d for d in semantic['dependencies'] if d.get('source_use') and '@' in d['id'])
        if case.endswith('drop'):
            semantic['dependencies'].remove(dep)
        else:
            dep['status'] = 'RESOLVED'
        required = 'Consumed dependencies differ'
    elif case == 'subquestion-missing':
        semantic['questions']['Q2']['subquestions']['possible_common']['unresolved'].remove('internal-reference:' + IDS[9])
        required = 'hides or invents a missing internal link'
    elif case in ('question-closure', 'question-status', 'subquestion-status'):
        q = semantic['questions']['Q2']
        if case == 'question-closure':
            q['unresolved'].remove('reference-closure:Q2')
            required = 'hides unresolved closure in question'
        else:
            if case == 'subquestion-status':
                q = q['subquestions']['possible_common']
            q['status'] = 'YES'
            required = 'Consumed question resolves source dependency uncertainty'
    elif case.startswith('q3-'):
        if case.endswith('status'):
            semantic['questions']['Q3']['status'] = 'COMPLETE'
        else:
            semantic['questions']['Q3']['value']['Q1']['complete'] = True
        required = 'Consumed semantic completeness differs'
    else:
        row = next(r for r in semantic['interpretation_input']['reference_admission']['references'] if r['id'] == IDS[0])
        row['targets'] = row['targets'][-1:]
        required = 'exact complete selected target'
    forged = reseal(p, semantic)
    save(HERE / 'controls' / (label + '-input.json'), {
        'case': case, 'original_products_sha256': digest(p), 'forged_products_sha256': digest(forged),
        'mutated_semantic_sha256': digest(semantic), 'validly_resealed': True,
        'expected_refusal_fragment': required})
    try:
        service.consume(forged, ROOT, mode='frozen')
    except ValueError as exc:
        if required not in str(exc):
            raise
        return {'status': 'PASS', 'case': label, 'actual_consumer_refusal': str(exc)}
    raise ValueError('Forged internal consumer accepted: ' + label)


def validate():
    from scripts.prospectus_typed_delta import equal
    for label, missing in (('candidate-answer', ()), ('missing-answer', IDS)):
        p, answer = retained(label)
        ordinary_schema(answer, baseline('candidate-answer')[1], expected_additions=('internal_references',))
        receipt = read(HERE / 'stages' / label.replace('-answer', '-verify') / 'result.json')
        assert receipt['status'] == 'PASS' and receipt['complete_answer_checked']
        ledger = read(AUTH / 'attempts/basf-references/attempt-019/candidate-answer-reconciliation.json.gz')
        originals = deepcopy([r['original'] for r in ledger['records']])
        rows = {r['id']: r for r in p['P3']['payload']['interpretation_input']['reference_admission']['references']}
        for (family, index), key in zip(LEDGER, IDS):
            record = next(r for r in ledger['records'] if r['family'] == family and r['index'] == index)
            if key in rows:
                record.update(current_reference=rows[key], current_status='CURRENT_LINK_WITH_CONSERVATIVE_CLOSURE',
                              complete_legal_interpretation=False)
        equal([r['original'] for r in ledger['records']], originals, 'Original inventory changed')
        expected = read(old.PREP / 'reconciliation-proposed.json.gz') if not missing else read(
            AUTH / 'attempts/basf-references/attempt-019/candidate-answer-reconciliation.json.gz')
        equal(ledger, expected, 'Current internal mapping differs')
        save(HERE / (label + '-reconciliation.json.gz'), ledger)
    return {'status': 'PASS', 'independent_complete_answer_receipts': ['candidate-verify', 'missing-verify'],
        'original_records_preserved': 60, 'original_task_complete': False}


def seal():
    resources = costs()
    save(HERE / 'result.json', {'status': 'PASS', 'task': 'basf-references',
        'original_task_complete': False, 'new_source_links': 10,
        'actual_ordinary_answers': 2, 'actual_upstream_refusals': 11,
        'actual_consumer_refusals': len(CONSUMERS), 'original_inventory_records': 60,
        'resources': resources, 'failed_trial_retained': relative(old.HERE),
        'remaining': ['Statutory originals and applicability', 'Unqualified defined terms',
                      'Original reference acceptance and general discovery'],
        'next_action': 'Continue original source remainder from candidate-answer-reconciliation.json.gz; all47reviewed links retained'})
    save(HERE / 'run-manifest.json', {
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'commands': ['.venv/bin/python -m scripts.prospectus_internal_consumer_continuation ' + s for s in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU deliberately hidden',
        'data_version': sha(old.PREP / 'source-review.json'), 'seeds': 'N/A deterministic',
        'wall_time': resources, 'plan': PLAN, 'result': relative(HERE / 'result.json'),
        'artifacts': relative(HERE), 'method_freeze': sha(PREP / 'freeze.json'),
        'prior_admissions': read(PREP / 'review.json')['budget_revision']['retained_attempts']})
    with (HERE / 'RESULT.md').open('x') as stream:
        stream.write('''# Complete internal scopes reach ordinary consumers

The ten original findings reach their full selected source scopes. Independent
reconstruction checks all original dependencies, closure, complete candidate and
omitted-link answers, unchanged P4/P5 content and all consumed-product hashes.
Artifact-only fields remain absent; the reviewed internal-source report is the
only schema addition. Eleven upstream target changes and fifteen
validly resealed downstream changes are refused by actual product consumers.
All sixty original inventory records survive, with forty-seven reviewed links
covering forty-eight records. Conservative source cycles and UNKNOWN headings
remain visible; they do not establish a legal inconsistency.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain this internal-source integration | Independent intervals and complete ordinary answers agree; actual controls refused | No candidate promotion veto in this finite trial | Statutory applicability, remaining definitions and automatic discovery | Continue original source remainder | Whole-task or general-build completion |

The source-target and consumer gaps were local implementation defects. The020
answer failure was a verifier assumption about the API; its answer was lost and
is not reused. New evidence is retained before independent verification. All
original costs and failures remain cumulative. No external-package limitation
or universal legal correctness follows. The strongest alternative explanation
is a shared reading of the original pages; source-bound independent intervals,
whole-answer comparison and adverse controls constrain that risk. A contrary
primary-source reading would require review and could overturn this conclusion.
''')
    return {'status': 'PASS', 'original_task_complete': False, 'resources': resources}


def propose():
    from legalmath.prospectus.execution_authority import Authority, CODE, digest as authority_digest
    program = read(AUTH / 'program.json')
    assert program['revision'] == 279
    assert read(old.HERE / 'result.json')['trial_status'] == 'FAIL'
    assert read(PREP / 'preflight-schema-result.json')['status'] == 'PASS'
    assert not (PREP / 'freeze.json').exists()
    old.frozen()
    attempts = [e['attempt'] for e in Authority(ROOT).events()
                if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 20
    assert len(program['obligations']) == 59 and len(program['tasks']) == 44
    bindings = {relative(f): sha(f) for folder in (old.HERE, PREP) for f in sorted(folder.rglob('*'))
                if f.is_file() and '__pycache__' not in f.parts}
    for name in (*CODE, PLAN, 'scripts/prospectus_internal_consumer_oracle.py',
                 'scripts/prospectus_internal_consumer_continuation.py'):
        bindings[name] = sha(ROOT / name)
    save(PREP / 'freeze.json', {'bindings': bindings})
    proposal = deepcopy(program)
    proposal['revision'] = 280
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, timeout_seconds=180,
        reason='Continue ten original internal findings after retained ordinary-schema verifier failure; production and source reading unchanged',
        pre_admission_review=relative(PREP / 'PRE-ADMISSION-REVIEW.md'),
        internal_consumer_continuation={'version': 'internal-consumer-continuation.v1',
            'failed_trial': relative(old.HERE), 'review': relative(PREP), 'original_task_complete': False,
            'bounds': {'stage_seconds': 180, 'cumulative_new_seconds': LIMIT, 'new_bytes': 192 * 1024**2},
            'further_harness_retry_allowed': False})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [relative(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 21
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 280
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(dossier=PLAN, task_sha256=authority_digest(task),
                remaining='020 P3/tests pass but ordinary verification failed; full answers and actual controls remain unverified.',
                next_action='Correct ordinary schema, preserve computed evidence, verify complete/omitted answers and actual resealed controls; then statutory/defined-term remainder.',
                acceptance='Independent source/dependency/closure and full ordinary answers; actual refusals; all60original records retained. Partial evidence only.',
                stop_condition='21 cumulative admissions;180s stages;3600s cumulative including279 failures;192MiB with4MiB reserve;no unchanged/harness retry.')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=relative(PREP / 'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        relative(PREP / 'routes.json'): sha(PREP / 'routes.json'),
        relative(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    review = {'baseline': authority_digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'original_obligations_preserved': True,
        'changes': ['Correct nonexistent ordinary-answer field assumption',
                    'Retain computed products and answers before independent verification',
                    'Separate construction, consume and verify receipts; hash-conditional reuse of020 success'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN,
            'review': relative(PREP / 'PRE-ADMISSION-REVIEW.md'), 'production_unchanged': True,
            'schema_preflight': relative(PREP / 'preflight-schema-result.json'),
            'failed_trial': relative(old.HERE / 'result.json'), 'whole_task_acceptance_claimed': False},
        'evidence_contract': {'primary': 'Independent original intervals/dependencies/closure, full ordinary answers and all60inventory records; actual forged-product refusals',
            'veto': ['Wrong/truncated target', 'Changed source, prior link or unrelated meaning',
                     'Concealed uncertainty', 'Invalid schema/hash', 'Harness/frozen/resource invalidity'],
            'not_concluded': ['Statutory applicability', 'Actual tax/event facts',
                             'Automatic discovery', 'Universal correctness', 'Whole task/build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 20, 'new_maximum': 21,
            'retained_attempts': attempts,
            'reason': 'Concrete verifier API mismatch after170.55s; distinct corrected schema and durable separately receipted stages, unchanged production',
            'next_discriminating_check': 'Whole candidate/omission answers under actual ordinary schema plus all original upstream/resealed controls',
            'stop_condition': '180s stages;3600s cumulative including every279 failure;192MiB;one frozen continuation;no automatic/unchanged retry',
            'same_scope_authorization': 'User directs refreshing master program and completing general build with internally demonstrated conditional correctness'},
        'measured_budget_revision': {'previous_seconds': 1800, 'cumulative_seconds': LIMIT,
            'retained_seconds_before_schema_preflight': 569.9076367472298,
            'reason': 'Current combined answer reached170.55s versus01968-72s; fifteen actual consumers remain; retain all original costs, do not reset'},
        'resources_before_admission': costs()}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 280, 'prior_admissions': 20, 'resources': costs()}


def main():
    label = sys.argv[1]
    if label == 'close-failed':
        print(json.dumps(close_failed()))
        return
    if label == 'propose':
        print(json.dumps(propose()))
        return
    preflight = label == 'preflight-schema'
    if not preflight:
        assert label in STAGES, 'Unknown continuation stage'
        frozen()
        index = STAGES.index(label)
        if index:
            assert read(HERE / 'stages' / STAGES[index - 1] / 'result.json')['status'] == 'PASS'
    resources = costs()
    folder = PREP if preflight else HERE / 'stages' / label
    marker = folder / (label + '-started.json' if preflight else 'started.json')
    assert not marker.exists(), 'Stage already started; no unchanged retry'
    seconds = min(180, math.floor(LIMIT - resources['new_measured_seconds']))
    assert seconds > 0
    save(marker, {'command': sys.argv, 'stage_seconds': seconds,
        'started_at': datetime.now(timezone.utc).isoformat()})
    began = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Internal consumer stage bound')))
    signal.alarm(seconds)
    try:
        if preflight:
            result = schema_preflight()
        elif label.endswith('-downstream'):
            result = downstream(label)
        elif label.endswith('-consume'):
            result = consume(label)
        elif label.endswith('-verify'):
            name = 'missing-p3' if label == 'missing-p3-verify' else label.replace('-verify', '-answer')
            p, answer = retained(name)
            result = verify(p, answer, missing=IDS if label.startswith('missing') else ())
        elif label.startswith('consumer-'):
            result = consumer(label)
        else:
            result = globals()[label.replace('-', '_')]()
        if not preflight:
            frozen()
        costs()
        assert result['status'] == 'PASS'
        result['wall_seconds'] = time.monotonic() - began
        save(folder / (label + '-result.json' if preflight else 'result.json'), result)
        if label == 'seal':
            save(HERE / 'outputs.json', {str(f.relative_to(HERE)): sha(f) for f in sorted(HERE.rglob('*'))
                if f.is_file() and '__pycache__' not in f.parts})
        # Full independent diagnostic details remain in the immutable receipt.
        print(json.dumps({k: v for k, v in result.items() if k != 'closure_diagnostic_delta'}))
    except BaseException as exc:
        save(folder / (label + '-failure.json' if preflight else 'failure.json'),
             {'type': type(exc).__name__, 'message': str(exc), 'wall_seconds': time.monotonic() - began})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
