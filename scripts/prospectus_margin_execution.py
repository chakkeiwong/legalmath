"""Bounded original-task execution and substantive printed-scope acceptance."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import signal
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from scripts.prospectus_margin_preparation import (
    AUTH, PREP, DONOR, MARGINS, PLAN, read, save, sha, relative, products)
from scripts import prospectus_margin_oracle as oracle
from scripts.prospectus_typed_delta import changes, apply, self_check
from legalmath.prospectus.successor import service, basf_printed_scope as core
from legalmath.prospectus.successor.contracts import digest

HERE = MARGINS / 'attempt-004'
ROUTES = AUTH / 'closure-routes-2026-10-18-basf-margin-268.json'
STAGES = ('tests', 'baseline', 'omit-listed', 'omit-redemption', 'omit-remaining',
          'omit-all', 'upstream-controls', 'consumer-controls', 'default-f', 'validate', 'seal')
CONTROL_NAMES = ('missing-governor', 'truncated-body', 'extended-body', 'duplicate-edge',
                 'wrong-governor', 'wrong-selected-use', 'boolean-offset', 'wrong-question',
                 'inapplicable-branch', 'raw-source', 'selected-role', 'final-premise')


def frozen():
    record = read(PREP / 'freeze.json')
    for name, expected in {**record['methods'], **record['inputs']}.items():
        if sha(ROOT / name) != expected:
            raise ValueError('Frozen scope method/input changed: ' + name)
    if (HERE / 'admission.json').exists():
        for name, expected in read(HERE / 'admission.json')['binding'].items():
            if sha(ROOT / name) != expected:
                raise ValueError('Admitted scope binding changed: ' + name)


def costs():
    new = read(PREP / 'preparation-result.json')['wall_seconds']
    if (PREP / 'consumer-preflight.json').exists():
        new += read(PREP / 'consumer-preflight.json')['wall_seconds']
    receipts = list(HERE.glob('stages/*/result.json')) if HERE.exists() else []
    new += sum(read(p)['wall_seconds'] for p in receipts)
    old = {}
    for i in (1, 2, 3):
        manifest = read(MARGINS / f'attempt-{i:03d}/run-manifest.json')
        old[str(i)] = {k: v for k, v in manifest.items() if 'seconds' in k or 'wall' in k}
    size = sum(p.stat().st_size for base in (PREP, HERE) if base.exists()
               for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    extras = [ROOT / PLAN, ROOT / 'src/legalmath/prospectus/successor/basf_printed_scope.py',
              ROOT / 'src/legalmath/prospectus/successor/basf_printed_scope_spec.json',
              ROOT / 'scripts/prospectus_margin_preparation.py', Path(__file__),
              ROOT / 'scripts/prospectus_margin_oracle.py',
              ROOT / 'tests/prospectus/test_basf_printed_scope.py',
              AUTH / 'program.json', AUTH / 'revisions/0268.json', ROUTES,
              AUTH / 'proposals/basf-margin-268.json', AUTH / 'proposals/basf-margin-268-review.json']
    size += sum(p.stat().st_size for p in extras if p.exists())
    if new >= 900 or size >= 126 * 1024**2:
        raise ValueError('Printed-scope cumulative new work/storage bound exhausted')
    return {'new_measured_seconds': new, 'new_counted_bytes': size,
            'historical_measured_fields': old, 'unmeasured_authoring_controller_and_smoke_time': 'UNKNOWN',
            'new_seconds_bound': 900, 'new_bytes_bound': 128 * 1024**2, 'reserved_bytes': 2 * 1024**2}


def propose():
    program = read(AUTH / 'program.json')
    assert program['revision'] == 267
    assert read(PREP / 'preparation-result.json')['reproduced_gap']
    # Preserve source scope exactly, including source images and historical failures.
    assert sha(PREP / 'spec.json') == sha(ROOT / 'src/legalmath/prospectus/successor/basf_printed_scope_spec.json')
    inputs = read(PREP / 'source-inputs.json')
    for name in ('spec.json', 'preparation-started.json', 'preparation-result.json',
                 'pre-repair-omission.json.gz', 'preparation-tests.xml', 'consumer-preflight.json', 'REQUIREMENTS.md'):
        inputs[relative(PREP / name)] = sha(PREP / name)
    for path in (AUTH / 'attempts/basf-meanings/attempt-020/current-answer.json.gz',
                 AUTH / 'reviews/current-default-alternatives-257/profile.json'):
        inputs[relative(path)] = sha(path)
    from legalmath.prospectus.execution_authority import CODE, Authority
    methods = {relative(p): sha(p) for p in sorted((ROOT / 'src/legalmath/prospectus').rglob('*.py'))}
    for name in (*CODE, PLAN, 'src/legalmath/prospectus/successor/basf_printed_scope_spec.json',
                 'scripts/prospectus_margin_preparation.py', 'scripts/prospectus_margin_oracle.py',
                 'scripts/prospectus_margin_execution.py', 'scripts/prospectus_typed_delta.py',
                 'tests/prospectus/test_basf_printed_scope.py',
                 'tests/prospectus/test_execution_acceptance.py', 'tests/prospectus/test_execution_authority.py',
                 'tests/prospectus_successor/test_governing_interpretation.py',
                 'tests/prospectus_successor/test_occurrence_lookup.py'):
        if not (ROOT / name).is_file():
            raise ValueError('Missing proposed verification method: ' + name)
        methods[name] = sha(ROOT / name)
    save(PREP / 'freeze.json', {'methods': methods, 'inputs': inputs,
        'spec_sha256': sha(PREP / 'spec.json'), 'typed_delta_roundtrips': self_check(),
        'original_scope': 'BASF-02;54 printed groups,522 occurrences; source-scope review only',
        'unknown_body_meanings_remain_in': ['basf-meanings', 'basf-office', 'basf-incorporation', 'law-applicability'],
        'external_opinion_required': False})
    proposal = deepcopy(program)
    proposal['revision'] = 268
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-margins')
    task.update(dossier=PLAN, timeout_seconds=180, validator='basf-printed-scope.v1',
        reason='Reproduced full-family omission removes284 dependencies; integrate all54 original scopes into current P3/final consumer and verify complete original source requirement',
        printed_scope_acceptance={'version': 'basf-printed-scope.v1', 'review': relative(PREP),
            'bounds': {'stage_seconds': 180, 'new_seconds': 900, 'new_bytes': 128 * 1024**2},
            'original_body_meaning_obligations_remain': True})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(methods) + list(inputs) + [relative(PREP / 'freeze.json')]))
    proposal['budgets']['basf-margins']['maximum_new_attempts'] = 4
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 268
    for row in routes['tasks']:
        if row['task'] == 'basf-margins':
            row['before268'] = {k: deepcopy(row[k]) for k in ('remaining', 'next_action', 'acceptance', 'dossier')}
            row.update(remaining='Original inventory complete; current ordinary consumer omitted explicit full-scope verification and missing-family reporting.',
                next_action='Execute the frozen production scope repair and independent original-review acceptance; preserve unresolved body meanings in their existing tasks.',
                acceptance='All54 original printed groups/522 occurrences, exact selected uses, missing-family unknowns, actual consumers and adverse source controls; source-scope acceptance only.',
                dossier=PLAN, task_sha256=digest(task))
        if row['task'] == 'source-authority':
            row['remaining'] = 'Attempt008 passed eight archive boundaries and16 adverse controls; original publication/authenticity and pre2011 availability remain unknown.'
            row['next_action'] = 'Preserve sealed006-008; no further archive harness retry. Continue remaining original source-authority requirements.'
    save(ROUTES, routes)
    proposal['continuation_review']['plan'] = PLAN
    proposal['continuation_review']['routes'] = relative(ROUTES)
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN), relative(ROUTES): sha(ROUTES),
        relative(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-margins']
    review = {'baseline': digest(program), 'changes': ['Production printed-scope checks and final answer explanation',
        'Narrow named assisted acceptance of original scope task; preserve all body/office/law/discovery obligations'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN,
            'reproduced': relative(PREP / 'pre-repair-omission.json.gz'),
            'baseline': 'Complete019 ordinary answer; immutable001-003 extents; no fresh extraction',
            'risks': ['Development reading is conditional, not exhaustive interpretation',
                      'Shared acceptance/service edits stale prior engineering receipts; revalidate once methods stabilize']},
        'evidence_contract': {'primary': 'Original source mappings and independently checked complete ordinary answer effects',
            'veto': ['Source/method/baseline drift', 'Unreported missing family', 'Changed unrelated answers',
                     'Permissive scope forgery', 'Exceeded bounds'],
            'not_concluded': ['Complete contract', 'Automatic discovery', 'Actual event', 'Source authenticity', 'Whole build']},
        'scope_unchanged': True, 'budget_unchanged': False, 'original_obligations_preserved': True,
        'budget_revision': {'budget_key': 'basf-margins', 'previous_maximum': 3, 'new_maximum': 4,
            'retained_attempts': attempts, 'reason': 'Distinct reproduced actual-consumer integration gap',
            'next_discriminating_check': 'Scope families and unknown bodies reach ordinary answers; mutations reject',
            'stop_condition': 'One180s per stage;900s new measured;128MiB; no unchanged retry; frozen methods',
            'same_scope_authorization': 'User directs refreshed general build without external adviser prerequisite'}}
    save(AUTH / 'proposals/basf-margin-268.json', proposal)
    save(AUTH / 'proposals/basf-margin-268-review.json', review)
    return {'status': 'PASS', 'frozen_methods': len(methods), 'original_inputs': len(inputs),
            'prior_admissions_preserved': len(attempts), 'stream': task['stream'], 'costs': costs()}


def complete(p, interpretation):
    candidate = dict(p)
    candidate['P3'] = service.interpretation_product(p['P1'], p['P2'], interpretation)
    old4, old5 = p['P4']['payload'], p['P5']['payload']
    candidate['P4'] = service.law_product(p['P1'], candidate['P3'], old4['cases'], old4['law_input'])
    candidate['P5'] = service.financial_product(p['P1'], p['P2'], candidate['P3'], old5['cases'], old5['scenario_input'])
    return candidate


def retained(label):
    original = products()
    original_answer = read(DONOR / 'installed-answer/ordinary-answer.json.gz')
    row = read(HERE / (label + '.json.gz'))
    current = apply(original, row['products_delta'])
    answer = apply(original_answer, row['answer_delta'])
    assert digest(current) == row['products_sha256'] and digest(answer) == row['answer_sha256']
    return current, answer


def save_case(label, original, candidate, answer, missing):
    old = read(DONOR / 'installed-answer/ordinary-answer.json.gz')
    checked = oracle.verify(candidate, answer, missing=missing)
    dp, da = changes(original, candidate), changes(old, answer)
    oracle.same(apply(original, dp), candidate, 'Product delta is lossy')
    oracle.same(apply(old, da), answer, 'Answer delta is lossy')
    save(HERE / (label + '.json.gz'), {'products_delta': dp, 'answer_delta': da,
        'products_sha256': digest(candidate), 'answer_sha256': digest(answer),
        'missing': list(missing), 'independent_check': checked})
    return {'status': 'PASS', **checked}


def compare_ordinary(old, new):
    oracle.same({k: v for k, v in old.items() if k != 'report_sha256'},
                {k: v for k, v in new.items() if k not in ('printed_margin_review', 'report_sha256')},
                'Unrelated original ordinary answer changed')


def compare_omission(original, candidate, before, after, missing):
    removed = {d['id'] for d in original['P3']['payload']['dependencies'] if d['id'].startswith('governing:')
        and core.family(d['id'].removeprefix('governing:')) in missing}
    expected = deepcopy(before['questions'])
    for q in ('Q1', 'Q2'):
        nodes = [expected[q], *expected[q].get('subquestions', {}).values(), expected['Q3']['value'][q]]
        for node in nodes:
            node['unresolved'] = sorted(set(node['unresolved']) - removed | {'margin-scope:' + f for f in missing})
    oracle.same(after['questions'], expected, 'Unexpected question effect from omitted margin family')
    allowed = {'questions', 'consumed_products', 'printed_margin_review', 'report_sha256'}
    oracle.same({k: v for k, v in before.items() if k not in allowed},
                {k: v for k, v in after.items() if k not in allowed}, 'Unrelated omission answer changed')
    for name in ('P1', 'P2'):
        oracle.same(original[name], candidate[name], 'Source/construction changed on scope omission')
    for name in ('P4', 'P5'):
        oracle.same(original[name]['payload'], candidate[name]['payload'], 'Law/finance payload changed on scope omission')
    for key in original['P3']['payload']:
        if key not in ('dependencies', 'questions', 'interpretation_input', 'governing_admission_sha256'):
            oracle.same(original['P3']['payload'][key], candidate['P3']['payload'][key], 'Unrelated semantic field changed')


def baseline():
    original = products()
    candidate = complete(original, deepcopy(original['P3']['payload']['interpretation_input']))
    oracle.same(original, candidate, 'Current complete P3/P4/P5 differs from protected019')
    answer = service.consume(candidate, ROOT, mode='frozen')
    compare_ordinary(read(DONOR / 'installed-answer/ordinary-answer.json.gz'), answer)
    return save_case('baseline', original, candidate, answer, ())


def omission(label):
    original, before = retained('baseline')
    missing = list(core.PREFIXES) if label == 'omit-all' else [label.removeprefix('omit-')]
    interpretation = deepcopy(original['P3']['payload']['interpretation_input'])
    interpretation['governing_admission']['governing'] = [e for e in interpretation['governing_admission']['governing']
                                                        if core.family(e['id']) not in missing]
    candidate = complete(original, interpretation)
    answer = service.consume(candidate, ROOT, mode='frozen')
    compare_omission(original, candidate, before, answer, missing)
    return save_case(label, original, candidate, answer, missing)


def mutated(p, name):
    source, construction = p['P1'], p['P2']
    interpretation = deepcopy(p['P3']['payload']['interpretation_input'])
    edges = interpretation['governing_admission']['governing']
    i = next(i for i, e in enumerate(edges) if core.family(e['id']) == 'remaining')
    e = edges[i]
    if name == 'missing-governor': edges.pop(i)
    elif name == 'truncated-body': e['to'].pop()
    elif name == 'extended-body': e['to'].append(deepcopy(edges[0]['to'][0]))
    elif name == 'duplicate-edge': edges.append(deepcopy(e))
    elif name == 'wrong-governor': e['from']['quote'] = 'Wrong governor'
    elif name == 'wrong-selected-use': e['to'][0]['use']['start'] += 1
    elif name == 'boolean-offset': e['to'][0]['use']['start'] = False
    elif name == 'wrong-question': e['questions'] = ['Q1']
    elif name == 'inapplicable-branch': e['id'] = 'basf-remaining-margin:permanent-global:p108:l15'
    elif name in ('raw-source', 'final-premise'):
        identity = 'basf-base-september-2022-exchange:p112:l18' if name == 'raw-source' else 'basf-2032-final:p5:l15'
        graph = source['payload']['graph']
        graph = {**graph, 'units': [{**u, 'raw': 'Wrong original text'} if u['id'] == identity else u for u in graph['units']]}
        source = service.seal('P1', source['payload']['request']['bundle'], source['inputs'], {**source['payload'], 'graph': graph})
        construction = service.seal('P2', source['payload']['request']['bundle'], {'P1': source['sha256']}, construction['payload'])
    elif name == 'selected-role':
        assembly = construction['payload']['assembly']
        assembly = {**assembly, 'units': [{**u, 'role': 'EXCLUDED'} if u['unit'] == 'basf-base-september-2022-exchange:p112:l18' else u for u in assembly['units']]}
        construction = service.seal('P2', source['payload']['request']['bundle'], construction['inputs'], {**construction['payload'], 'assembly': assembly})
    else:
        raise ValueError('Unknown scope control')
    return source, construction, interpretation


def upstream_controls():
    p, _ = retained('baseline')
    observed = []
    for name in CONTROL_NAMES:
        source, construction, interpretation = mutated(p, name)
        try:
            service.interpretation_product(source, construction, interpretation)
        except ValueError as exc:
            observed.append({'name': name, 'outcome': 'REJECTED_UPSTREAM', 'reason': str(exc), 'final_answer_exists': False})
        else:
            raise AssertionError('Production interpretation accepted malformed scope: ' + name)
    save(HERE / 'upstream-controls.json', observed)
    return {'status': 'PASS', 'actual_interpretation_refusals': len(observed)}


def consumer_controls():
    p, _ = retained('baseline')
    observed = []
    for name in ('scope-truncated', 'dependency-promoted', 'dependency-dropped', 'question-hidden'):
        payload = deepcopy(p['P3']['payload'])
        if name == 'scope-truncated': payload['interpretation_input']['governing_admission']['governing'][0]['to'].pop()
        elif name == 'dependency-promoted':
            next(d for d in payload['dependencies'] if d['id'].startswith('governing:basf-remaining-margin:') and d['status'] == 'UNRESOLVED')['status'] = 'RESOLVED'
        elif name == 'dependency-dropped':
            payload['dependencies'] = [d for d in payload['dependencies'] if not d['id'].startswith('governing:basf-listed-notices-margin-3:')]
        else:
            payload['questions']['Q1']['unresolved'] = [x for x in payload['questions']['Q1']['unresolved'] if not x.startswith('governing:basf-remaining-margin:')]
        altered = dict(p)
        altered['P3'] = service.seal('P3', p['P1']['payload']['request']['bundle'], p['P3']['inputs'], payload)
        for stage in ('P4', 'P5'):
            altered[stage] = service.seal(stage, p['P1']['payload']['request']['bundle'],
                {**p[stage]['inputs'], 'P3': altered['P3']['sha256']}, p[stage]['payload'])
        try:
            service.consume(altered, ROOT, mode='frozen')
        except ValueError as exc:
            observed.append({'name': name, 'outcome': 'REJECTED_BY_FINAL_CONSUMER', 'reason': str(exc)})
        else:
            raise AssertionError('Resealed inconsistent scope was consumed: ' + name)
    save(HERE / 'consumer-controls.json', observed)
    return {'status': 'PASS', 'actual_final_consumer_refusals': len(observed)}


def default_f():
    from legalmath.prospectus import basf_default_f_current as extension
    p, ordinary = retained('baseline')
    profile = read(AUTH / 'reviews/current-default-alternatives-257/profile.json')
    profile['ordinary_answer_sha256'] = digest(ordinary)
    assert profile['products_sha256'] == digest(p)
    answer = service.consume(p, ROOT, mode='frozen', default_f_profile=profile,
                             expected_default_f_profile_sha256=digest(profile))
    extension.verify_answer(answer, ordinary, profile, expected_profile_sha256=digest(profile))
    old = read(AUTH / 'attempts/basf-meanings/attempt-020/current-answer.json.gz')
    bound = {'profile_sha256', 'ordinary_answer_sha256'}
    oracle.same({k: v for k, v in old['default_f_review'].items() if k not in bound},
                {k: v for k, v in answer['default_f_review'].items() if k not in bound},
                'Default(f) meaning or decision changed on margin integration')
    save(HERE / 'default-profile.json', profile)
    save(HERE / 'default-answer-delta.json.gz', {'delta': changes(old, answer), 'sha256': digest(answer)})
    return {'status': 'PASS', 'original_decisions_preserved': True,
            'checked_answers': answer['default_f_reasoning_verification']['checked_answers']}


def evidence(attempt):
    if Path(attempt).resolve() != HERE.resolve():
        raise ValueError('Printed scope evidence belongs to a different attempt')
    frozen()
    original = products()
    p, ordinary = retained('baseline')
    oracle.same(original, p, 'Original full product baseline changed')
    compare_ordinary(read(DONOR / 'installed-answer/ordinary-answer.json.gz'), ordinary)
    summaries = {'baseline': oracle.verify(p, ordinary)}
    for label in ('omit-listed', 'omit-redemption', 'omit-remaining', 'omit-all'):
        candidate, answer = retained(label)
        missing = list(core.PREFIXES) if label == 'omit-all' else [label.removeprefix('omit-')]
        compare_omission(p, candidate, ordinary, answer, missing)
        summaries[label] = oracle.verify(candidate, answer, missing=missing)
    actual = service.consume(p, ROOT, mode='frozen')
    oracle.same(actual, ordinary, 'Retained full answer differs from actual production consumer')
    upstream, downstream = read(HERE / 'upstream-controls.json'), read(HERE / 'consumer-controls.json')
    assert [r['name'] for r in upstream] == list(CONTROL_NAMES)
    assert all(r['outcome'] == 'REJECTED_UPSTREAM' and r['final_answer_exists'] is False and r['reason'] for r in upstream)
    assert [r['name'] for r in downstream] == ['scope-truncated', 'dependency-promoted', 'dependency-dropped', 'question-hidden']
    assert all(r['outcome'] == 'REJECTED_BY_FINAL_CONSUMER' and r['reason'] for r in downstream)
    from legalmath.prospectus import basf_default_f_current as extension
    old = read(AUTH / 'attempts/basf-meanings/attempt-020/current-answer.json.gz')
    stored = read(HERE / 'default-answer-delta.json.gz')
    extended = apply(old, stored['delta'])
    assert digest(extended) == stored['sha256']
    profile = read(HERE / 'default-profile.json')
    extension.verify_answer(extended, ordinary, profile, expected_profile_sha256=digest(profile))
    from legalmath.prospectus.execution_acceptance import checked_tests
    tests = checked_tests(HERE / 'tests.xml', 24)
    for label in STAGES[:STAGES.index('validate')]:
        receipt = read(HERE / 'stages' / label / 'result.json')
        assert receipt['status'] == 'PASS' and receipt['wall_seconds'] < 180
    return {'scope': 'BASF_ORIGINAL_PRINTED_SCOPE_ONLY', 'cases': summaries,
            'upstream_refusals': 12, 'final_consumer_refusals': 4, 'focused_tests': tests,
            'whole_program_complete': False, 'body_meanings_complete': False,
            'source_scope_task_requirements_met': True}


def validate_submission(root, attempt, task):
    if (Path(root).resolve() != ROOT or task.get('id') != 'basf-margins'
            or task.get('stream') != 'assisted' or task.get('validator') != 'basf-printed-scope.v1'):
        raise ValueError('Scope validator outside its named assisted task')
    if Path(attempt).resolve() != HERE.resolve():
        raise ValueError('Scope validator requires the frozen original-task attempt')
    result = read(HERE / 'result.json')
    if (result.get('task') != 'basf-margins' or result.get('status') != 'PASS'
            or result.get('scope') != 'BASF_ORIGINAL_PRINTED_SCOPE_ONLY'
            or result.get('whole_program_complete') is not False
            or result.get('body_meanings_complete') is not False):
        raise ValueError('Unsupported scope completion claim')
    if list(HERE.glob('stages/*/failure.json')):
        raise ValueError('Failed scope stage cannot be accepted')
    expected = evidence(attempt)
    oracle.same(read(HERE / 'verification.json'), expected, 'Scope verification differs from independent source/consumer evidence')
    return True


def tests():
    import pytest
    code = pytest.main(['-q', 'tests/prospectus/test_basf_printed_scope.py',
        'tests/prospectus/test_execution_acceptance.py', 'tests/prospectus/test_execution_authority.py',
        'tests/prospectus_successor/test_governing_interpretation.py',
        'tests/prospectus_successor/test_occurrence_lookup.py', '--junitxml=' + str(HERE / 'tests.xml')])
    if code != 0:
        raise ValueError('Focused scope/authority regression tests failed')
    return {'status': 'PASS'}


def validate():
    result = evidence(HERE)
    save(HERE / 'verification.json', result)
    return {'status': 'PASS', 'original_requirements_checked': True}


def seal():
    verified = read(HERE / 'verification.json')
    result = {'task': 'basf-margins', 'status': 'PASS', **verified,
        'task_complete': True, 'acceptance_requires_named_validator': True,
        'result_note': 'RESULT.md', 'resources': costs(),
        'next_action': 'Refresh authority; continue unresolved original BASF meanings/office/source tasks, then installed revalidation'}
    save(HERE / 'result.json', result)
    stages = {label: read(HERE / 'stages' / label / 'result.json') for label in STAGES[:-1]}
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'plan': PLAN, 'result': 'RESULT.md', 'environment': str(ROOT / '.venv/bin/python'),
        'cpu_gpu': 'CPU only; CUDA_VISIBLE_DEVICES=-1', 'random_seeds': 'N/A deterministic',
        'source_version': relative(PREP / 'source-inputs.json'), 'method_manifest': relative(PREP / 'freeze.json'),
        'actual_stages': stages, 'resources': result['resources'],
        'output_artifacts': ['baseline.json.gz', 'omit-listed.json.gz', 'omit-redemption.json.gz',
            'omit-remaining.json.gz', 'omit-all.json.gz', 'upstream-controls.json', 'consumer-controls.json',
            'default-answer-delta.json.gz', 'verification.json'], 'fresh_extraction_or_installation': False})
    text = """# BASF complete printed-scope production integration

The ordinary P3 and final consumer now check the complete reviewed printed
families against the original source and selected occurrences. The pre-repair
probe removed284 dependencies without reporting missing scope review. Each
missing family now creates an explicit unresolved dependency and is identified
in the ordinary answer. Partial families, altered extents and inconsistent
resealed dependencies refuse.

All54 original groups and522 occurrences were compared with immutable source
reviews using a separate direct character-map enumerator. The current complete
P1–P5 baseline equals meanings019. The ordinary answer adds the printed review
and its report hash; all previous questions and substantive sections remain
equal. Four omission consumers preserve unrelated conclusions and expose their
missing families. Twelve actual interpretation controls and four final-consumer
controls refuse. The default(f) extension retains its original192 checked
answers after rebinding the expanded ordinary answer.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Submit original printed-scope task for named assisted acceptance | Complete source-to-answer mapping, independent direct source/use comparison and actual adverse consumers | No failed frozen stage; exact source/method/baseline identities checked | Body meanings, office, incorporation and legal-source interpretation remain in their original tasks | Record and refresh; continue substantive work | Complete contract, automatic discovery, actual event, source authenticity, current installed package or whole build |

This was an integration omission in our program. No third-party package failure
was implicated. The original development readings remain conditional source
interpretations. Their full scope is enforced mechanically; the checks do not
prove that no other legal interpretation exists. No external adviser opinion
was required and no independent reader acceptance was claimed.

Post-run review: the strongest alternative explanation is an incorrect original
printed-boundary reading. The retained original images and complete raw anchors
make that reading inspectable; any contrary source evidence requires reopening
the relevant scope. Unknown meanings remain explicit even for a fully reviewed
scope. Source/software identities, actual commands, resource limits and all
previous failures remain retained. Shared service and validator changes require
final installed/engineering revalidation after substantive methods stabilize.
"""
    (HERE / 'RESULT.md').write_text(text)
    return {'status': 'PASS', 'submitted_scope': verified['scope'], 'whole_build_complete': False}


def main():
    label = sys.argv[1]
    if label == 'propose':
        print(json.dumps(propose()))
        return
    if label not in STAGES:
        raise ValueError('Unknown scope stage')
    frozen()
    assert (HERE / 'admission.json').is_file()
    index = STAGES.index(label)
    if index:
        assert read(HERE / 'stages' / STAGES[index - 1] / 'result.json')['status'] == 'PASS'
    costs()
    folder = HERE / 'stages' / label
    began = time.monotonic()
    save(folder / 'started.json', {'command': [str(ROOT / '.venv/bin/python'), '-m',
        'scripts.prospectus_margin_execution', label], 'started_at': datetime.now(timezone.utc).isoformat(),
        'stage_seconds_bound': 180, 'freeze_sha256': sha(PREP / 'freeze.json')})
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Scope stage180s bound')))
    signal.alarm(180)
    try:
        if label.startswith('omit-'):
            result = omission(label)
        else:
            result = globals()[label.replace('-', '_')]()
        frozen()
        result['wall_seconds'] = time.monotonic() - began
        save(folder / 'result.json', result)
        if label == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*'))
                if p.is_file() and '__pycache__' not in p.parts})
        print(json.dumps(result))
    except BaseException as exc:
        save(folder / 'failure.json', {'type': type(exc).__name__, 'message': str(exc),
            'wall_seconds': time.monotonic() - began})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
