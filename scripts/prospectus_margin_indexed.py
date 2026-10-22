"""Measured layout-index repair followed by the original printed-scope checks."""
from copy import deepcopy
from datetime import datetime, timezone
import contextlib
import cProfile
import json
import os
from pathlib import Path
import pstats
import signal
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from scripts.prospectus_margin_preparation import AUTH, read, save, sha, relative
from scripts import prospectus_relative_notices as refs
from scripts import prospectus_margin_oracle as oracle
from scripts import prospectus_margin_execution as original
from scripts.prospectus_typed_delta import changes, apply, equal
from legalmath.prospectus.successor import service, basf_printed_scope as core
from legalmath.prospectus.successor.contracts import digest

PREP = AUTH / 'reviews/occurrence-scan-profile-272'
HERE = AUTH / 'attempts/basf-margins/attempt-006'
PLAN = 'docs/plans/prospectus-occurrence-scan-repair-2026-10-18.md'
STAGES = ('tests', 'baseline', 'omit-listed', 'omit-redemption', 'omit-remaining', 'omit-all',
          'upstream-controls', 'consumer-scope-truncated', 'consumer-dependency-promoted',
          'consumer-dependency-dropped', 'consumer-question-hidden', 'default-f', 'validate', 'seal')


def baseline_inputs():
    return refs.retained('candidate-answer')


def profile():
    p, ordinary = baseline_inputs()
    semantic = p['P3']['payload']
    request = {**p['P1']['payload']['request'], **semantic['interpretation_input']}
    profiler = cProfile.Profile()
    began = time.monotonic()
    profiler.enable()
    actual = core.verify_consumed(p['P1']['payload']['graph'], p['P2']['payload']['assembly'], request, semantic)
    profiler.disable()
    seconds = time.monotonic() - began
    profiler.dump_stats(str(PREP / 'candidate.prof'))
    equal(actual, read(PREP / 'original-result.json.gz'), 'Indexed scope result changed')
    rows = []
    for (filename, line, name), (cc, nc, tt, ct, callers) in pstats.Stats(profiler).stats.items():
        if 'prospectus/successor' in filename:
            rows.append({'file': filename, 'line': line, 'function': name,
                'calls': nc, 'self_seconds': tt, 'cumulative_seconds': ct})
    rows.sort(key=lambda r: r['cumulative_seconds'], reverse=True)
    save(PREP / 'candidate-function-costs.json', rows)
    return {'status': 'PASS', 'profiled_seconds': seconds,
        'full_result_equal_original': True, 'top_functions': rows[:8],
        'timing_interpretation': 'Single profile; descriptive only; exact result equivalence is primary'}


def costs():
    prior = read(AUTH / 'attempts/basf-margins/attempt-005/result.json')['resources']['accounted_seconds_including_failure']
    seconds = prior + read(PREP / 'result.json')['wall_seconds']
    if (PREP / 'profile-result.json').exists(): seconds += read(PREP / 'profile-result.json')['wall_seconds']
    seconds += sum(read(p)['wall_seconds'] for p in HERE.glob('stages/*/result.json'))
    seconds += sum(read(p)['wall_seconds'] for p in HERE.glob('stages/*/failure.json'))
    # Count the retained earlier package conservatively, then every new272 file.
    size = read(AUTH / 'attempts/basf-margins/attempt-005/result.json')['resources']['new_counted_bytes']
    size += sum(p.stat().st_size for folder in (PREP, HERE) if folder.exists()
                for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    extras = [ROOT / PLAN, Path(__file__), AUTH / 'program.json', AUTH / 'revisions/0272.json',
              ROOT / 'tests/prospectus_successor/test_layout_anchor_index.py',
              ROOT / 'src/legalmath/prospectus/successor/admissions.py',
              ROOT / 'src/legalmath/prospectus/execution_acceptance.py']
    size += sum(p.stat().st_size for p in extras if p.exists())
    if seconds >= 2200 or size >= 252 * 1024**2:
        raise ValueError('Cumulative original margin repair bound exhausted')
    return {'measured_seconds': seconds, 'prior005_measured_seconds': prior, 'bound_seconds': 2200,
            'counted_bytes': size, 'bound_bytes': 256 * 1024**2, 'reserve_bytes': 4 * 1024**2,
            'unknown_time': 'Additional authoring/controller and historical unmeasured time UNKNOWN'}


def propose():
    from legalmath.prospectus.execution_authority import Authority, CODE, digest as authority_digest
    program = read(AUTH / 'program.json')
    assert program['revision'] == 271
    assert read(PREP / 'profile-result.json')['full_result_equal_original']
    inputs = {}
    for folder in (refs.HERE, AUTH / 'attempts/basf-margins/attempt-005'):
        manifest = read(folder / 'outputs.json')
        for name, expected in manifest.items():
            assert sha(folder / name) == expected
            inputs[relative(folder / name)] = expected
        inputs[relative(folder / 'outputs.json')] = sha(folder / 'outputs.json')
    inputs.update(read(AUTH / 'reviews/basf-margin-production-268/source-inputs.json'))
    for name in ('inputs.json', 'original.prof', 'function-costs.json', 'result.json',
                 'original-result.json.gz', 'profile-started.json', 'profile-result.json',
                 'candidate.prof', 'candidate-function-costs.json', 'preparation-tests.xml'):
        inputs[relative(PREP / name)] = sha(PREP / name)
    for path in (AUTH / 'reviews/current-default-alternatives-257/profile.json',
                 AUTH / 'attempts/basf-meanings/attempt-020/current-answer.json.gz'):
        inputs[relative(path)] = sha(path)
    methods = {relative(p): sha(p) for p in sorted((ROOT / 'src/legalmath/prospectus').rglob('*.py'))}
    for path in sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.json')):
        methods[relative(path)] = sha(path)
    for name in (*CODE, PLAN, relative(Path(__file__)),
                 'scripts/prospectus_margin_execution.py', 'scripts/prospectus_margin_oracle.py',
                 'scripts/prospectus_margin_preparation.py', 'scripts/prospectus_relative_notices.py',
                 'scripts/prospectus_relative_notice_oracle.py', 'scripts/prospectus_typed_delta.py',
                 'tests/prospectus_successor/test_layout_anchor_index.py',
                 'tests/prospectus_successor/test_occurrence_lookup.py',
                 'tests/prospectus_successor/test_governing_interpretation.py',
                 'tests/prospectus_successor/test_basf_call_references.py',
                 'tests/prospectus/test_basf_printed_scope.py',
                 'tests/prospectus/test_execution_acceptance.py',
                 'tests/prospectus/test_execution_authority.py'):
        methods[name] = sha(ROOT / name)
    save(PREP / 'freeze.json', {'methods': methods, 'inputs': inputs})
    proposal = deepcopy(program)
    proposal['revision'] = 272
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-margins')
    task.update(dossier=PLAN, reason='Measured layout anchor scans dominate actual margin consumer; indexed production repair preserves validation and resumes complete original source criteria',
        printed_scope_acceptance={'version': 'basf-printed-scope.v1', 'review': relative(PREP),
            'bounds': {'stage_seconds': 180, 'cumulative_seconds': 2200, 'cumulative_bytes': 256 * 1024**2},
            'indexed_repair': True, 'further_harness_retry_allowed': False, 'prior_failures': ['attempt-004','attempt-005'],
            'original_body_meaning_obligations_remain': True})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(methods) + list(inputs) + [relative(PREP / 'freeze.json')]))
    proposal['budgets']['basf-margins']['maximum_new_attempts'] = 6
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 272
    for row in routes['tasks']:
        if row['task'] == 'basf-margins':
            row['before272'] = {k: deepcopy(row[k]) for k in ('remaining', 'next_action', 'stop_condition')}
            row.update(task_sha256=authority_digest(task), dossier=PLAN,
                remaining='005timeout preserved. Actual profile shows layout source scans dominate; measured indexed repair and frozen-equivalence checks pass.',
                next_action='Execute one changed original-task trial against current013baseline; complete all54groups/522occurrences, omissions, refusals, default(f) and named acceptance.',
                stop_condition='Six total original margin admissions;2200cumulative measured seconds;256MiB;180s stages;no further harness retry; all005costs preserved.')
        if row['task'] == 'basf-references':
            row['remaining'] = '013recorded two exact local(b) links, two whole answers and nine actual refusals; original47+13source reference remainder still open.'
            row['next_action'] = 'Retain013; review heterogeneous scalar-source ledger before any whole-reference reconciliation; no repeat of its failed optional inspection without review.'
        if row['task'] == 'reasoning-corpus':
            row['phase'] = 5
            row['next_action'] = 'Revalidate once substantive service/acceptance methods stabilize; historical012 remains retained, current acceptance stale.'
    save(PREP / 'routes.json', routes)
    proposal['continuation_review']['plan'] = PLAN
    proposal['continuation_review']['routes'] = relative(PREP / 'routes.json')
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        relative(PREP / 'routes.json'): sha(PREP / 'routes.json'), relative(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-margins']
    assert len(attempts) == 5
    review = {'baseline': authority_digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'original_obligations_preserved': True,
        'changes': ['Measured production layout-index repair; original005failure and all costs retained',
            'Current013complete comparator and original scope oracle; no semantic relaxation',
            'Individual actual control receipts and named original-task acceptance'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN,
            'original_profile': relative(PREP / 'result.json'), 'candidate_profile': relative(PREP / 'profile-result.json'),
            'initial_hypothesis_revised': 'Structure dominates, not dependency lookup',
            'not_an_unchanged_batch_retry': True},
        'evidence_contract': {'primary': 'Exact complete original scope, actual whole-answer equality/omission effects and all adverse consumers',
            'veto': ['Meaning/source drift', 'Permissive forgery', 'Missing case', 'Resource bound', 'Harness failure'],
            'not_concluded': ['Whole build', 'Complete body meanings', 'Actual facts', 'Source authenticity', 'Statistical speed ranking']},
        'budget_revision': {'budget_key': 'basf-margins', 'previous_maximum': 5, 'new_maximum': 6,
            'retained_attempts': attempts, 'reason': 'Actual profiling establishes a changed production repair; explicitly supersedes269 no-retry only for this trial',
            'next_discriminating_check': 'Exact current consumers and original scope acceptance after indexed anchor validation',
            'stop_condition': '180s stages;2200cumulative seconds from268;256MiB including history;no further harness retry',
            'same_scope_authorization': 'User requested refreshed program and continued general build'}}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 272, 'methods': len(methods), 'prior_admissions': len(attempts), 'resources': costs()}


def frozen():
    freeze = read(PREP / 'freeze-final.json')
    for name, expected in {**freeze['methods'], **freeze['inputs']}.items():
        if sha(ROOT / name) != expected:
            raise ValueError('Indexed margin method/source changed: ' + name)
    for name, expected in read(HERE / 'admission.json')['binding'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Indexed margin admission changed: ' + name)


def retain(label, p, a):
    before, answer = baseline_inputs()
    dp, da = changes(before, p), changes(answer, a)
    equal(apply(before, dp), p, 'Lossy product delta')
    equal(apply(answer, da), a, 'Lossy answer delta')
    save(HERE / (label + '.json.gz'), {'products_delta': dp, 'answer_delta': da,
        'products_sha256': digest(p), 'answer_sha256': digest(a)})


def retained(label):
    p, a = baseline_inputs()
    row = read(HERE / (label + '.json.gz'))
    p, a = apply(p, row['products_delta']), apply(a, row['answer_delta'])
    assert digest(p) == row['products_sha256'] and digest(a) == row['answer_sha256']
    return p, a


def baseline():
    p, before = baseline_inputs()
    actual = original.complete(p, deepcopy(p['P3']['payload']['interpretation_input']))
    equal(actual, p, 'Indexed repair changed any complete current product')
    answer = service.consume(actual, ROOT, mode='frozen')
    equal(answer, before, 'Indexed repair changed complete current answer')
    summary = oracle.verify(actual, answer)
    retain('baseline', actual, answer)
    return {**summary, 'scope_status': summary['status'], 'status': 'PASS', 'whole_answer_equal': True}


def omission(label):
    p, before = retained('baseline')
    missing = list(core.PREFIXES) if label == 'omit-all' else [label.removeprefix('omit-')]
    interpretation = deepcopy(p['P3']['payload']['interpretation_input'])
    interpretation['governing_admission']['governing'] = [e for e in interpretation['governing_admission']['governing']
                                                        if core.family(e['id']) not in missing]
    candidate = original.complete(p, interpretation)
    answer = service.consume(candidate, ROOT, mode='frozen')
    original.compare_omission(p, candidate, before, answer, missing)
    summary = oracle.verify(candidate, answer, missing=missing)
    retain(label, candidate, answer)
    return {**summary, 'scope_status': summary['status'], 'status': 'PASS'}


def upstream_controls():
    p, _ = retained('baseline')
    observed = []
    for name in original.CONTROL_NAMES:
        start = time.monotonic()
        source, construction, interpretation = original.mutated(p, name)
        try:
            service.interpretation_product(source, construction, interpretation)
        except ValueError as exc:
            row = {'name': name, 'outcome': 'REJECTED_UPSTREAM', 'reason': str(exc),
                   'final_answer_exists': False, 'wall_seconds': time.monotonic() - start}
            save(HERE / 'controls' / (name + '.json'), row)
            observed.append(row)
        else:
            raise ValueError('Actual P3 accepted invalid margin: ' + name)
    save(HERE / 'upstream-controls.json', observed)
    return {'status': 'PASS', 'actual_interpretation_refusals': len(observed)}


def consumer_control(label):
    name = label.removeprefix('consumer-')
    p, _ = retained('baseline')
    payload = deepcopy(p['P3']['payload'])
    if name == 'scope-truncated': payload['interpretation_input']['governing_admission']['governing'][0]['to'].pop()
    elif name == 'dependency-promoted':
        next(d for d in payload['dependencies'] if d['id'].startswith('governing:basf-remaining-margin:') and d['status'] == 'UNRESOLVED')['status'] = 'RESOLVED'
    elif name == 'dependency-dropped':
        payload['dependencies'] = [d for d in payload['dependencies'] if not d['id'].startswith('governing:basf-listed-notices-margin-3:')]
    elif name == 'question-hidden':
        payload['questions']['Q1']['unresolved'] = [x for x in payload['questions']['Q1']['unresolved'] if not x.startswith('governing:basf-remaining-margin:')]
    else:
        raise ValueError('Unknown consumer control')
    altered = dict(p)
    bundle = p['P1']['payload']['request']['bundle']
    altered['P3'] = service.seal('P3', bundle, p['P3']['inputs'], payload)
    for stage in ('P4', 'P5'):
        altered[stage] = service.seal(stage, bundle, {**p[stage]['inputs'], 'P3': altered['P3']['sha256']}, p[stage]['payload'])
    try:
        service.consume(altered, ROOT, mode='frozen')
    except ValueError as exc:
        if not any(word in str(exc) for word in ('printed scope', 'BASF question')):
            raise
        return {'status': 'PASS', 'name': name, 'outcome': 'REJECTED_BY_FINAL_CONSUMER', 'reason': str(exc)}
    raise ValueError('Invalid final margin consumer accepted: ' + name)


def default_f():
    from legalmath.prospectus import basf_default_f_current as extension
    p, ordinary = retained('baseline')
    profile = read(AUTH / 'reviews/current-default-alternatives-257/profile.json')
    profile['products_sha256'] = digest(p)
    profile['ordinary_answer_sha256'] = digest(ordinary)
    answer = service.consume(p, ROOT, mode='frozen', default_f_profile=profile,
                             expected_default_f_profile_sha256=digest(profile))
    extension.verify_answer(answer, ordinary, profile, expected_profile_sha256=digest(profile))
    old = read(AUTH / 'attempts/basf-meanings/attempt-020/current-answer.json.gz')
    bound = {'profile_sha256', 'ordinary_answer_sha256', 'products_sha256'}
    oracle.same({k: v for k, v in old['default_f_review'].items() if k not in bound},
                {k: v for k, v in answer['default_f_review'].items() if k not in bound},
                'Original default(f) meaning/decision changed')
    save(HERE / 'default-profile.json', profile)
    save(HERE / 'default-answer-delta.json.gz', {'delta': changes(old, answer), 'sha256': digest(answer)})
    return {'status': 'PASS', 'original_decisions_preserved': True,
            'checked_answers': answer['default_f_reasoning_verification']['checked_answers']}


def tests():
    import pytest
    with (HERE / 'tests.log').open('x') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        result = pytest.main(['-q', 'tests/prospectus_successor/test_layout_anchor_index.py',
            'tests/prospectus_successor/test_occurrence_lookup.py',
            'tests/prospectus_successor/test_governing_interpretation.py',
            'tests/prospectus_successor/test_basf_call_references.py',
            'tests/prospectus/test_basf_printed_scope.py', 'tests/prospectus/test_execution_acceptance.py',
            'tests/prospectus/test_execution_authority.py', '--junitxml=' + str(HERE / 'tests.xml')])
    if result:
        raise ValueError('Indexed layout and source acceptance tests failed')
    return {'status': 'PASS'}


def evidence():
    frozen()
    baseline_p, baseline_a = retained('baseline')
    before, before_answer = baseline_inputs()
    equal(baseline_p, before, 'Current source baseline products changed')
    equal(baseline_a, before_answer, 'Current source baseline answer changed')
    results = {'baseline': oracle.verify(baseline_p, baseline_a)}
    for label in ('omit-listed', 'omit-redemption', 'omit-remaining', 'omit-all'):
        p, a = retained(label)
        missing = list(core.PREFIXES) if label == 'omit-all' else [label.removeprefix('omit-')]
        original.compare_omission(baseline_p, p, baseline_a, a, missing)
        results[label] = oracle.verify(p, a, missing=missing)
    actual = service.consume(baseline_p, ROOT, mode='frozen')
    equal(actual, baseline_a, 'Actual current full consumer differs')
    upstream = read(HERE / 'upstream-controls.json')
    assert [r['name'] for r in upstream] == list(original.CONTROL_NAMES)
    assert all(r['outcome'] == 'REJECTED_UPSTREAM' and r['final_answer_exists'] is False and r['reason'] for r in upstream)
    for label in STAGES[:STAGES.index('validate')]:
        receipt = read(HERE / 'stages' / label / 'result.json')
        assert receipt['status'] == 'PASS' and receipt['wall_seconds'] < 180
        if label.startswith('consumer-'):
            assert receipt['outcome'] == 'REJECTED_BY_FINAL_CONSUMER' and receipt['reason']
    from legalmath.prospectus import basf_default_f_current as extension
    old = read(AUTH / 'attempts/basf-meanings/attempt-020/current-answer.json.gz')
    row = read(HERE / 'default-answer-delta.json.gz')
    extended = apply(old, row['delta'])
    assert digest(extended) == row['sha256']
    profile = read(HERE / 'default-profile.json')
    extension.verify_answer(extended, baseline_a, profile, expected_profile_sha256=digest(profile))
    from legalmath.prospectus.execution_acceptance import checked_tests
    ntests = checked_tests(HERE / 'tests.xml', 240)
    return {'scope': 'BASF_ORIGINAL_PRINTED_SCOPE_ONLY', 'cases': results,
        'upstream_refusals': 12, 'final_consumer_refusals': 4, 'focused_tests': ntests,
        'whole_program_complete': False, 'body_meanings_complete': False,
        'source_scope_task_requirements_met': True}


def validate():
    result = evidence()
    save(HERE / 'verification.json', result)
    return {'status': 'PASS', 'original_scope_requirements_checked': True}


def validate_submission(root, attempt, task):
    if (Path(root).resolve() != ROOT or Path(attempt).resolve() != HERE
            or task.get('id') != 'basf-margins' or task.get('stream') != 'assisted'
            or task.get('validator') != 'basf-printed-scope.v1'):
        raise ValueError('Indexed scope validator outside its exact named original task')
    result = read(HERE / 'result.json')
    if (result.get('task') != 'basf-margins' or result.get('status') != 'PASS'
            or result.get('scope') != 'BASF_ORIGINAL_PRINTED_SCOPE_ONLY'
            or result.get('whole_program_complete') is not False
            or result.get('body_meanings_complete') is not False
            or list(HERE.glob('stages/*/failure.json'))):
        raise ValueError('Failed or overclaimed indexed scope submission')
    expected = evidence()
    equal(expected, read(HERE / 'verification.json'), 'Named source verification differs')
    costs()
    return True


def seal():
    result = {'task': 'basf-margins', 'status': 'PASS', **read(HERE / 'verification.json'),
        'task_complete': True, 'acceptance_requires_named_validator': True, 'resources': costs(),
        'next_action': 'Refresh authority and continue original BASF meanings/reference/law work; installed revalidation after methods stabilize'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': ['.venv/bin/python -m scripts.prospectus_margin_indexed ' + s for s in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;CUDA_VISIBLE_DEVICES=-1;GPU hidden',
        'seeds': 'N/A deterministic', 'wall_time': result['resources'], 'plan': PLAN,
        'result': relative(HERE / 'result.json'), 'data_version': sha(PREP / 'inputs.json'),
        'method_freeze': sha(PREP / 'freeze-final.json'), 'output_artifacts': relative(HERE),
        'prior_failures_retained': ['basf-margins004','basf-margins005']})
    (HERE / 'RESULT.md').write_text('''# Original BASF printed-scope verification

The measured layout-index repair preserves complete current source products and
answers. All54printed groups and522original occurrences are checked through the
actual consumer. Four whole-family omissions produce the required uncertainty;
twelve malformed interpretations and four individually retained resealed
consumer controls refuse. Default(f) alternative decisions remain unchanged.

The previous timeout was in our source-validation path. A single profile found
57.6seconds in full-graph anchor scans out of59.1profiled seconds; layout
structure admission dominated that cost. The repair retains every candidate
for a source identity and calls the unchanged binder on those candidates.
Frozen-method equivalence checks retain original refusals. Timing observations
are descriptive and make no statistical package-performance ranking.

| Decision | Primary criterion | Veto status | Uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Submit original printed-scope task for named acceptance | Exact current whole answers, all54groups/522occurrences and omission effects verified | Malformed upstream and final consumers refused; source/method bounds checked | Body meanings, incorporation, office/law authority and actual facts remain | Continue those original obligations, then installed revalidation | Complete contract, discovery recall, source authenticity or whole build |

Attempts004and005remain sealed failures. No final-consumer result from005is
claimed. This is the measured production repair authorized by272, with all prior
costs and admissions retained. The named validator must independently replay
the source/result checks before the authority can accept this finite task.

The weakest evidence is still the supplied development reading of printed
scope. Original page images and independently enumerated character maps allow
the precise boundaries to be checked. A different source edition, selection or
printed extent invalidates the affected result and requires a new source review.
''')
    return {'status': 'PASS', 'task_complete_requires_record': True, 'resources': result['resources']}


def main():
    label = sys.argv[1]
    if label == 'propose':
        print(json.dumps(propose()))
        return
    if label != 'profile' and label not in STAGES:
        raise ValueError('Unknown indexed scope stage')
    if label != 'profile':
        frozen()
        index = STAGES.index(label)
        if index:
            assert read(HERE / 'stages' / STAGES[index - 1] / 'result.json')['status'] == 'PASS'
        costs()
    folder = PREP if label == 'profile' else HERE / 'stages' / label
    prefix = 'profile-' if label == 'profile' else ''
    started = time.monotonic()
    save(folder / (prefix + 'started.json'), {'command': sys.argv,
        'started_at': datetime.now(timezone.utc).isoformat(), 'stage_seconds': 180})
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Indexed scope180s stage bound')))
    signal.alarm(180)
    try:
        if label.startswith('omit-'): result = omission(label)
        elif label.startswith('consumer-'): result = consumer_control(label)
        else: result = globals()[label.replace('-', '_')]()
        assert result['status'] == 'PASS'
        if label != 'profile': frozen()
        result['wall_seconds'] = time.monotonic() - started
        save(folder / (prefix + 'result.json'), result)
        if label == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*'))
                if p.is_file() and '__pycache__' not in p.parts})
        print(json.dumps(result))
    except BaseException as exc:
        save(folder / (prefix + 'failure.json'), {'status': 'FAIL', 'type': type(exc).__name__,
            'message': str(exc), 'wall_seconds': time.monotonic() - started})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
