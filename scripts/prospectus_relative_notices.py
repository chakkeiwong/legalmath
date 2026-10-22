"""Bounded source-reviewed continuation of the original BASF reference task."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import sys
import time
import subprocess

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from scripts.prospectus_margin_preparation import AUTH, DONOR, read, save, sha, relative, products
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

PREP = AUTH / 'reviews/basf-relative-notices-270'
HERE = AUTH / 'attempts/basf-references/attempt-013'
PLAN = 'docs/plans/prospectus-basf-relative-notices-2026-10-18.md'
SPEC = ROOT / 'src/legalmath/prospectus/successor/basf_call_references_spec.json'
KEY = 'basf-base-september-2022-exchange'
STAGES = ('tests', 'candidate-p3', 'candidate-answer', 'missing-p3', 'missing-answer',
          'upstream-controls', 'consumer-dependency', 'consumer-uncertainty',
          'consumer-target', 'validate', 'seal')


def prepare():
    p = products()
    graph, assembly = p['P1']['payload']['graph'], p['P2']['payload']['assembly']
    raw = {u['id']: u for u in graph['units']}
    units = {u['unit']: u for u in assembly['units']}
    from legalmath.prospectus.successor.occurrences import anchor, _DependencyLookup
    from legalmath.prospectus.successor.reviewed_references import admit
    rows = []
    for identity, line, target_page, first, last, paragraph in (
            ('par-call-notice', 23, 120, 51, 66, '5(4)(b)'),
            ('early-call-notice', 91, 121, 8, 21, '5(5)(b)')):
        source = raw[f'{KEY}:p120:l{line}']
        start = source['raw'].index('Absatz (b)')
        targets = []
        for n in range(first, last + 1):
            u = raw[f'{KEY}:p{target_page}:l{n}']
            assert units[u['id']]['text'] == u['raw'] and units[u['id']]['role'] == 'OPERATIVE'
            targets.append({'source': anchor(u), 'use': u['id'], 'language': u['language']})
        cited = anchor(source, start, start + len('Absatz (b)'))
        rows.append({'id': identity, 'form': 'relative', 'source': cited,
            'from_use': source['id'], 'language': source['language'], 'targets': targets,
            'authority': cited, 'questions': ['Q1', 'Q2'], 'discovery_ids': [],
            'reason': 'Original German Option I ' + paragraph + ': complete local notice paragraph; (c) is separate. Actual notice compliance remains unknown.'})
        assert not any(r['unit'] == source['id'] and start <= r['start'] < r['end'] <= cited['end']
                       for r in graph['references'])
    packet = {'version': 'reviewed-references.v2', 'assembly_sha256': digest(assembly),
        'review': {'reviewer': 'Codex original pages120-121', 'kind': 'DEVELOPMENT',
                  'reason': 'Exact relative source links under supplied final terms; no actual notice or complete-contract conclusion'},
        'references': rows}
    original_packet = p['P1']['payload']['request']['reference_admission']
    assert len(original_packet['references']) == 20
    assert not any(r['source']['unit'] in {row['source']['unit'] for row in rows}
                   for r in original_packet['references'])
    swapped = deepcopy(packet)
    swapped['references'][0]['targets'] = deepcopy(rows[1]['targets'])
    got, _ = admit(graph, assembly, swapped, _lookup=_DependencyLookup(graph, assembly))
    assert all(d['status'] == 'RESOLVED' for d in got)
    images = read(AUTH / 'attempts/basf-margins/attempt-002/v3/scope-review.json')['images']
    images = {k: v for k, v in images.items() if k.endswith(('base-120.png', 'base-121.png', 'final-6.png'))}
    for name, expected in images.items():
        assert sha(ROOT / name) == expected
    sources = [{k: d[k] for k in ('id', 'path', 'sha256')}
               for d in p['P1']['payload']['request']['bundle']['documents']
               if d['id'] in (KEY, 'basf-2032-final')]
    for source in sources:
        assert sha(ROOT / source['path']) == source['sha256']
    contexts = [anchor(raw[f'{KEY}:p{page}:l{n}']) for page, n in ((120,22),(120,90),(120,67),(121,22))]
    spec = {'version': 'basf-call-references.v1', 'sources': sources, 'references': rows,
            'contexts': contexts, 'images': images, 'automatic_discovery': False}
    save(PREP / 'source-review.json', spec)
    save(SPEC, spec)
    save(PREP / 'packet.json', packet)
    save(PREP / 'pre-repair.json', {'missing_reviewed_links': [r['id'] for r in rows],
        'automatic_discoveries_at_cited_spans': 0, 'generic_wrong_target_statuses': [d['status'] for d in got],
        'wrong_par_call_target': '5(5)(b) onp121 instead of5(4)(b) onp120',
        'corrected_handoff_extent': '5(5)(b) ends atp121:l21;22-34 is(c)',
        'current_reviewed_references': 20, 'whole_clause_meanings_already_present': True})
    save(PREP / 'source-inputs.json', {**images, **{s['path']: s['sha256'] for s in sources},
        **{relative(DONOR / n): sha(DONOR / n) for n in ('outputs.json',
            'installed-construct/products.json.gz', 'installed-interpret/semantic.json.gz',
            'installed-complete/downstream-products.json.gz', 'installed-answer/ordinary-answer.json.gz')}})
    return {'status': 'PASS', 'relative_links': 2, 'target_lines': [16, 14],
            'generic_wrong_target_accepted_before_repair': True}


def costs():
    seconds = read(PREP / 'preparation-result.json')['wall_seconds']
    seconds += sum(read(p)['wall_seconds'] for p in HERE.glob('stages/*/result.json'))
    seconds += sum(read(p)['wall_seconds'] for p in HERE.glob('stages/*/failure.json'))
    size = sum(p.stat().st_size for folder in (PREP, HERE) if folder.exists()
               for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    extra = [ROOT / PLAN, SPEC, Path(__file__), ROOT / 'scripts/prospectus_relative_notice_oracle.py',
             ROOT / 'src/legalmath/prospectus/successor/basf_call_references.py',
             AUTH / 'program.json', AUTH / 'revisions/0270.json']
    size += sum(p.stat().st_size for p in extra if p.exists())
    if seconds >= 900 or size >= 126 * 1024**2:
        raise ValueError('Relative notice cumulative resource bound exhausted')
    return {'new_measured_seconds': seconds, 'new_counted_bytes': size, 'new_seconds_bound': 900,
            'new_bytes_bound': 128 * 1024**2, 'reserve_bytes': 2 * 1024**2,
            'historical_and_authoring_time': 'Retained prior manifests; additional unmeasured time UNKNOWN'}


def propose():
    from legalmath.prospectus.execution_authority import Authority, CODE, digest as authority_digest
    program = read(AUTH / 'program.json')
    assert program['revision'] == 269
    inputs = read(PREP / 'source-inputs.json')
    original_manifest = read(DONOR / 'outputs.json')
    for name, expected in inputs.items():
        assert sha(ROOT / name) == expected
        if name.startswith(relative(DONOR) + '/') and not name.endswith('/outputs.json'):
            assert original_manifest[str((ROOT / name).relative_to(DONOR))] == expected
    for name in ('preparation-started.json', 'preparation-result.json', 'source-review.json',
                 'packet.json', 'pre-repair.json', 'preflight-tests.xml'):
        inputs[relative(PREP / name)] = sha(PREP / name)
    for name in ('attempts/basf-margins/attempt-004/baseline.json.gz',
                 'attempts/basf-margins/attempt-005/RESULT.md',
                 'attempts/basf-references/attempt-001/reference-ledger.json'):
        inputs[relative(AUTH / name)] = sha(AUTH / name)
    methods = {relative(p): sha(p) for p in sorted((ROOT / 'src/legalmath/prospectus').rglob('*.py'))}
    for name in (*CODE, PLAN, relative(SPEC), relative(Path(__file__)),
            'scripts/prospectus_relative_notice_oracle.py', 'scripts/prospectus_margin_preparation.py',
            'scripts/prospectus_typed_delta.py', 'src/legalmath/prospectus/successor/basf_printed_scope_spec.json',
            'tests/prospectus_successor/test_basf_call_references.py',
            'tests/prospectus_successor/test_closure_reference_replacement.py',
            'tests/prospectus_successor/test_closure_references.py'):
        methods[name] = sha(ROOT / name)
    save(PREP / 'freeze.json', {'methods': methods, 'inputs': inputs})
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 12
    proposal = deepcopy(program)
    proposal['revision'] = 270
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, timeout_seconds=180, build_criteria_scope=[],
        reason='Two original relative call-notice links absent; generic checker accepts wrong local(b); bind complete original targets and actual consumer uncertainty',
        relative_notice_review={'version': 'basf-call-references.v1', 'review': relative(PREP),
            'original_task_complete': False, 'bounds': {'stage_seconds': 180, 'new_seconds': 900,
                'new_bytes': 128 * 1024**2}, 'further_harness_retry_allowed': False})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(methods) + list(inputs) + [relative(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 13
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 270
    for row in routes['tasks']:
        if row['task'] == 'source-authority' and isinstance(row['stop_condition'], dict):
            row['numeric_stop_condition_before270'] = deepcopy(row['stop_condition'])
            row['stop_condition'] = ('All retained numeric bounds apply: ' + json.dumps(row['stop_condition'], sort_keys=True)
                + '; no further archive harness retry; original publication/authenticity remain unknown.')
        if row['task'] == 'basf-margins':
            row['remaining'] = '005 preserved baseline, four omissions and12 P3 refusals; final consumer batch timed out and has zero verified controls; scope task unaccepted.'
            row['next_action'] = 'No further harness retry under269. Any performance repair first needs measured profiling and a separate reviewed revision retaining811.577438154seconds and all failures. Continue independent source work now.'
            row['stop_condition'] = 'No further margin harness retry under269; do not rename or repartition its failed batch to evade the bound.'
        if row['task'] == task['id']:
            row.update(dossier=PLAN, task_sha256=authority_digest(task),
                remaining='Two relative(b) links absent; source review corrects early-call target to121:8-21. Other original references remain open.',
                next_action='Execute the frozen two-link source check and actual consumers under original BASF-01, then reconcile further original requirements.',
                acceptance='Separate source oracle, complete unchanged meanings/answers, missing-link effects and exact paragraph refusals; finite partial evidence only.',
                stop_condition='Thirteen cumulative admissions; one new attempt,180s per stage,900s new measured,128MiB,2MiB reserve; no unchanged/harness retry.')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review']['plan'] = PLAN
    proposal['continuation_review']['routes'] = relative(PREP / 'routes.json')
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        relative(PREP / 'routes.json'): sha(PREP / 'routes.json'), relative(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    review = {'baseline': authority_digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'original_obligations_preserved': True,
        'changes': ['Independent source-reference continuation; no margin retry',
            'Correct local(b) targets and retain missing-link uncertainty', 'Repair continuation route schema without relaxing bounds'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN,
            'corrected_flaw': 'Early-call target must stop before(c);8-34 would be wrong',
            'reproduced': relative(PREP / 'pre-repair.json'),
            'separate_task_and_question': True, 'whole_task_acceptance_claimed': False},
        'evidence_contract': {'primary': 'Independent original targets and complete actual answer effects',
            'veto': ['Wrong source/target', 'Unrelated answer change', 'Permissive adversarial consumer', 'Method drift', 'Resource/harness failure'],
            'not_concluded': ['Whole reference graph', 'Actual notice compliance', 'Automatic discovery', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 12, 'new_maximum': 13,
            'retained_attempts': attempts, 'reason': 'New reproduced original relative-reference gap; independent of margin timeout',
            'next_discriminating_check': 'Distinct local(b) targets and source-bound missing-link answer effects',
            'stop_condition': '180s stages;900s new measured;128MiB;no further harness retry',
            'same_scope_authorization': 'User requested refresh and continued general build without external opinions'}}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 270, 'prior_admissions': len(attempts), 'methods': len(methods), 'resources': costs()}


def frozen():
    record = read(PREP / 'freeze-final.json')
    for name, expected in {**record['inputs'], **record['methods']}.items():
        if sha(ROOT / name) != expected:
            raise ValueError('Frozen relative notice input/method changed: ' + name)
    for name, expected in read(HERE / 'admission.json')['binding'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Admitted relative notice binding changed: ' + name)


def overlay(original, missing=()):
    value = deepcopy(original['P3']['payload']['interpretation_input'])
    packet = deepcopy(original['P1']['payload']['request']['reference_admission'])
    packet['references'].extend(r for r in read(PREP / 'packet.json')['references'] if r['id'] not in missing)
    value['reference_admission'] = packet
    return value


def retain(label, candidate, answer=None):
    from scripts.prospectus_typed_delta import changes, apply, equal
    original = products()
    delta = changes(original, candidate)
    equal(apply(original, delta), candidate, 'Product delta is lossy')
    result = {'products_delta': delta, 'products_sha256': digest(candidate)}
    if answer is not None:
        before = read(DONOR / 'installed-answer/ordinary-answer.json.gz')
        delta = changes(before, answer)
        equal(apply(before, delta), answer, 'Answer delta is lossy')
        result.update(answer_delta=delta, answer_sha256=digest(answer))
    save(HERE / (label + '.json.gz'), result)


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


def interpretation(label):
    from scripts import prospectus_relative_notice_oracle as oracle
    missing = oracle.IDS if label.startswith('missing') else ()
    original = products()
    p = dict(original)
    p['P3'] = service.interpretation_product(original['P1'], original['P2'], overlay(original, missing))
    checked = oracle.verify(p, missing=missing)
    retain(label, p)
    return checked


def answer(label):
    from scripts import prospectus_relative_notice_oracle as oracle
    missing = oracle.IDS if label.startswith('missing') else ()
    p, _ = retained(label.replace('-answer', '-p3'))
    old4, old5 = p['P4']['payload'], p['P5']['payload']
    p['P4'] = service.law_product(p['P1'], p['P3'], old4['cases'], old4['law_input'])
    p['P5'] = service.financial_product(p['P1'], p['P2'], p['P3'], old5['cases'], old5['scenario_input'])
    actual = service.consume(p, ROOT, mode='frozen')
    checked = oracle.verify(p, actual, missing=missing)
    retain(label, p, actual)
    return checked


def tests():
    import contextlib
    import pytest
    with (HERE / 'tests.log').open('x') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        result = pytest.main(['-q', 'tests/prospectus_successor/test_basf_call_references.py',
            'tests/prospectus_successor/test_closure_reference_replacement.py',
            'tests/prospectus_successor/test_closure_references.py', '--junitxml=' + str(HERE / 'tests.xml')])
    if result:
        raise ValueError('Relative notice tests failed')
    return {'status': 'PASS'}


def upstream_controls():
    p = products()
    done = []
    for name in ('swapped-local-b', 'truncated-b', 'extended-into-c', 'renamed-link', 'question', 'source-edition'):
        began = time.monotonic()
        value = overlay(p)
        row = value['reference_admission']['references'][-2]
        if name == 'swapped-local-b': row['targets'] = value['reference_admission']['references'][-1]['targets']
        elif name == 'truncated-b': row['targets'].pop()
        elif name == 'extended-into-c':
            from legalmath.prospectus.successor.occurrences import anchor
            raw = next(u for u in p['P1']['payload']['graph']['units'] if u['id'] == KEY + ':p120:l67')
            row['targets'].append({'source': anchor(raw), 'use': raw['id'], 'language': raw['language']})
        elif name == 'renamed-link': row['id'] = 'hidden'
        elif name == 'question': row['questions'] = ['Q1']
        elif name == 'source-edition': row['source']['source_sha256'] = '0' * 64
        try:
            service.interpretation_product(p['P1'], p['P2'], value)
        except ValueError as exc:
            if 'BASF relative notice' not in str(exc):
                raise
            receipt = {'case': name, 'status': 'PASS', 'refusal': str(exc), 'wall_seconds': time.monotonic() - began}
            save(HERE / 'controls' / (name + '.json'), receipt)
            done.append(name)
        else:
            raise ValueError('Invalid actual P3 was accepted: ' + name)
    return {'status': 'PASS', 'actual_refusals': done}


def consumer_control(label):
    p, _ = retained('missing-answer' if label == 'consumer-uncertainty' else 'candidate-answer')
    semantic = deepcopy(p['P3']['payload'])
    if label == 'consumer-dependency':
        next(d for d in semantic['dependencies'] if d['id'] == 'reviewed-reference:par-call-notice')['targets'].pop()
        required = 'dependencies differ'
    elif label == 'consumer-uncertainty':
        semantic['questions']['Q2']['subquestions'][next(iter(semantic['questions']['Q2']['subquestions']))]['unresolved'].remove('relative-notice:early-call-notice')
        required = 'hides or invents'
    else:
        rows = semantic['interpretation_input']['reference_admission']['references']
        rows[-2]['targets'] = deepcopy(rows[-1]['targets'])
        required = 'exact complete local paragraph'
    bundle = p['P1']['payload']['request']['bundle']
    p['P3'] = service.seal('P3', bundle, p['P3']['inputs'], semantic)
    for stage in ('P4', 'P5'):
        p[stage] = service.seal(stage, bundle, {**p[stage]['inputs'], 'P3': p['P3']['sha256']}, p[stage]['payload'])
    try:
        service.consume(p, ROOT, mode='frozen')
    except ValueError as exc:
        if required not in str(exc):
            raise
        return {'status': 'PASS', 'case': label, 'actual_frozen_consumer_refusal': str(exc)}
    raise ValueError('Resealed invalid ordinary answer accepted: ' + label)


def validate():
    from scripts import prospectus_relative_notice_oracle as oracle
    results = []
    for label, missing in (('candidate-answer', ()), ('missing-answer', oracle.IDS)):
        p, a = retained(label)
        results.append(oracle.verify(p, a, missing=missing))
    return {'status': 'PASS', 'independent_cases': results, 'original_task_complete': False}


def seal():
    resources = costs()
    historical = {}
    for i in range(1, 13):
        folder = AUTH / 'attempts/basf-references' / f'attempt-{i:03d}'
        path = folder / 'run-manifest.json'
        historical[str(i)] = ({'path': relative(path), 'sha256': sha(path)} if path.exists() else
                               {'status': 'No standalone run manifest; original evidence retained'})
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False, 'complete_reference_graph': False,
        'actual_ordinary_answers': 2, 'actual_upstream_refusals': 6, 'actual_consumer_refusals': 3,
        'resources': resources, 'historical_manifests': historical,
        'remaining': ['Other original explicit/implicit references', 'Self/cyclic scope',
            'Statutory original editions', 'Unqualified defined-term uses', 'Whole-task acceptance'],
        'next_action': 'Reconcile every original47marker-line and13additional finding against current meanings and exact source targets; retain unknown statutory sources'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'commands': ['.venv/bin/python -m scripts.prospectus_relative_notices ' + s for s in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;CUDA_VISIBLE_DEVICES=-1;GPU intentionally hidden',
        'data_version': sha(PREP / 'source-review.json'), 'seeds': 'N/A deterministic source/consumer checks',
        'wall_time': resources, 'plan': PLAN, 'result': relative(HERE / 'result.json'),
        'artifact_directory': relative(HERE), 'method_freeze': sha(PREP / 'freeze-final.json')})
    note = '''# Relative call-notice result

The two original relative references now bind their separate complete local
notice paragraphs. Section5(4)(b) contains16source lines and includes the
redemption amount;5(5)(b) contains14lines and ends before(c). The pre-repair
generic checker accepted the wrong operative paragraph. The new source-specific
check rejects that substitution and exposes missing links in ordinary answers.

Two complete current ordinary answers, six actual P3 refusals and three
individually retained final-consumer refusals passed. The independent checker
verifies original PDF/image identities, exact source extents, all existing
clause meanings, all other dependencies and complete unchanged answer content.
Matched omission adds only the two declared uncertainties and related provenance.

| Decision | Primary criterion | Veto status | Uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain finite source-reference repair | Actual whole-answer and independent source checks pass | Wrong paragraph, shortened/extended targets and resealed forgeries refused | Other original references and actual notice facts remain open | Reconcile complete original reference remainder | Complete contract, actual compliance, automatic discovery or whole task |

This was our source-integration gap, not a third-party package failure. The
reviewed source boundaries and frozen-input checks establish this conditional
mapping. They do not establish all possible legal interpretations. The strongest
alternative explanation is a wrong development source reading; the retained
original page images and distinct paragraph labels allow that reading to be
checked. A different operative edition or selection requires a new review.

Margin attempt005 remains a failed, sealed package. Its interrupted final
consumer controls are not included in these results. No margin retry occurred.
The continuation route schema was repaired while retaining every numeric bound.
'''
    (HERE / 'RESULT.md').write_text(note)
    return {'status': 'PASS', 'original_task_complete': False, 'resources': resources}


def main():
    label = sys.argv[1]
    if label == 'propose':
        print(json.dumps(propose()))
        return
    if label != 'prepare' and label not in STAGES:
        raise ValueError('Unknown reviewed stage')
    if label != 'prepare':
        frozen()
        index = STAGES.index(label)
        if index:
            assert read(HERE / 'stages' / STAGES[index - 1] / 'result.json')['status'] == 'PASS'
        costs()
    began = time.monotonic()
    folder = PREP if label == 'prepare' else HERE / 'stages' / label
    stem = 'preparation-' if label == 'prepare' else ''
    limit = 60 if label == 'prepare' else 180
    save(folder / (stem + 'started.json'), {'command': sys.argv, 'stage_seconds': limit,
         'started_at': datetime.now(timezone.utc).isoformat()})
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Relative notice stage bound')))
    signal.alarm(limit)
    try:
        if label.endswith('-p3'):
            result = interpretation(label)
        elif label.endswith('-answer'):
            result = answer(label)
        elif label.startswith('consumer-'):
            result = consumer_control(label)
        else:
            result = globals()[label.replace('-', '_')]()
        if label != 'prepare':
            frozen()
        assert result['status'] == 'PASS'
        result['wall_seconds'] = time.monotonic() - began
        save(folder / (stem + 'result.json'), result)
        if label == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*'))
                if p.is_file() and '__pycache__' not in p.parts})
        print(json.dumps(result))
    except BaseException as exc:
        save(folder / (stem + 'failure.json'), {'type': type(exc).__name__, 'message': str(exc),
            'wall_seconds': time.monotonic() - began})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
