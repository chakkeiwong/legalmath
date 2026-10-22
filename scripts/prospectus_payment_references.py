"""Frozen, individually receipted stages for the original payment-reference gap."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from scripts.prospectus_margin_preparation import AUTH, DONOR, read, save, sha, relative, products
from scripts.prospectus_relative_notices import retained as baseline
from scripts.prospectus_payment_reference_preparation import PREP, SPEC, KEY, IDS, reconcile
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

HERE = AUTH / 'attempts/basf-references/attempt-014'
PLAN = 'docs/plans/prospectus-basf-payment-references-2026-10-18.md'
TESTS = ['tests/prospectus_successor/' + n for n in ('test_basf_payment_references.py',
    'test_basf_call_references.py', 'test_closure_reference_replacement.py', 'test_closure_references.py')]
STAGES = ('tests', 'candidate-p3', 'candidate-answer', 'missing-p3', 'missing-answer',
    'upstream-controls', 'consumer-dependency', 'consumer-uncertainty', 'consumer-target', 'validate', 'seal')


def costs():
    seconds = read(PREP / 'preparation-result.json')['wall_seconds']
    seconds += sum(float(s.attrib['time']) for f in PREP.glob('preflight*tests.xml')
                   for s in ET.parse(f).getroot().iter('testsuite'))
    seconds += sum(read(p)['wall_seconds'] for p in HERE.glob('stages/*/result.json'))
    seconds += sum(read(p)['wall_seconds'] for p in HERE.glob('stages/*/failure.json'))
    size = sum(p.stat().st_size for folder in (PREP, HERE) if folder.exists()
               for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    extra = [ROOT / PLAN, SPEC, Path(__file__), ROOT / 'scripts/prospectus_payment_reference_preparation.py',
        ROOT / 'scripts/prospectus_payment_reference_oracle.py',
        ROOT / 'src/legalmath/prospectus/successor/basf_payment_references.py',
        AUTH / 'program.json', AUTH / 'revisions/0273.json', *(ROOT / t for t in TESTS)]
    size += sum(p.stat().st_size for p in extra if p.exists())
    if seconds >= 1000 or size >= 156 * 1024**2:
        raise ValueError('Payment reference cumulative resource bound exhausted')
    return {'new_measured_seconds': seconds, 'new_counted_bytes': size, 'new_seconds_bound': 1000,
        'new_bytes_bound': 160 * 1024**2, 'reserve_bytes': 4 * 1024**2,
        'historical_and_authoring_time': 'Prior evidence preserved; unmeasured authoring/controller time UNKNOWN'}


def propose():
    from legalmath.prospectus.execution_authority import Authority, CODE, digest as authority_digest
    program = read(AUTH / 'program.json')
    assert program['revision'] == 272
    inputs = {relative(p): sha(p) for p in sorted(PREP.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    source = read(PREP / 'source-review.json')
    inputs.update(source['images'])
    inputs.update({s['path']: s['sha256'] for s in source['sources']})
    for folder, names in (
        (DONOR, ('outputs.json', 'installed-construct/products.json.gz', 'installed-interpret/semantic.json.gz',
                 'installed-complete/downstream-products.json.gz', 'installed-answer/ordinary-answer.json.gz')),
        (AUTH / 'attempts/basf-references/attempt-013', ('outputs.json', 'candidate-answer.json.gz', 'RESULT.md')),
        (AUTH / 'attempts/basf-references/attempt-001', ('outputs.json', 'reference-ledger.json')),
        (AUTH / 'attempts/basf-margins/attempt-006', ('outputs.json', 'result.json'))):
        manifest = read(folder / 'outputs.json')
        for name in names:
            path = folder / name
            if name != 'outputs.json':
                assert sha(path) == manifest[name]
            inputs[relative(path)] = sha(path)
    for path, expected in inputs.items():
        assert sha(ROOT / path) == expected
    methods = {relative(p): sha(p) for p in sorted((ROOT / 'src/legalmath/prospectus').rglob('*'))
               if p.suffix in ('.py', '.json')}
    for name in (*CODE, PLAN, relative(Path(__file__)), 'scripts/prospectus_payment_reference_preparation.py',
            'scripts/prospectus_payment_reference_oracle.py', 'scripts/prospectus_margin_preparation.py',
            'scripts/prospectus_relative_notices.py', 'scripts/prospectus_typed_delta.py', *TESTS):
        methods[name] = sha(ROOT / name)
    save(PREP / 'freeze.json', {'methods': methods, 'inputs': inputs})
    attempts = [e['attempt'] for e in Authority(ROOT).events()
                if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 13
    proposal = deepcopy(program)
    proposal['revision'] = 273
    task = next(t for t in proposal['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, timeout_seconds=180, build_criteria_scope=[],
        reason='Original three section4(2) payment links absent; generic checker accepts loss of tax qualifications; complete heterogeneous inventory reconciled',
        payment_reference_review={'version': 'basf-payment-references.v1', 'review': relative(PREP),
            'original_task_complete': False, 'bounds': {'stage_seconds': 180, 'new_seconds': 1000,
                'new_bytes': 160 * 1024**2}, 'further_harness_retry_allowed': False},
        pre_admission_review=relative(PREP / 'PRE-ADMISSION-REVIEW.md'))
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(methods) + list(inputs) + [relative(PREP / 'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 14
    routes = read(ROOT / program['continuation_review']['routes'])
    routes['baseline_revision'] = 273
    for row in routes['tasks']:
        if row['task'] == 'basf-margins':
            row.update(mode='accepted', remaining='006 ACCEPT1817: original54groups/522occurrences, full answer equality, four omissions,12P3 and4individual final-consumer refusals; default(f)192decisions retained.',
                next_action='Preserve accepted006. Revalidate shared methods with the final current build; no new margin task or retry.',
                stop_condition='Original272 cumulative bounds and all failed history retained; no further margin harness retry.')
        if row['task'] == task['id']:
            row.update(dossier=PLAN, task_sha256=authority_digest(task),
                remaining='013 closes two relative call notices. All47historical and13additional records reconciled with two scalar provenance forms preserved; three payment links next.',
                next_action='Execute frozen payment-source and actual-consumer checks; continue original explicit/statutory/self-scope remainder from the lossless reconciliation.',
                acceptance='Independent original selected intervals and complete ordinary answer, matched omission and malformed/resigned consumer refusals; finite partial evidence only.',
                stop_condition='Fourteen cumulative admissions; one new attempt,180s stages,1000s new measured,160MiB/4MiB reserve; no unchanged or harness retry.')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review']['plan'] = PLAN
    proposal['continuation_review']['routes'] = relative(PREP / 'routes.json')
    proposal['continuation_review']['bindings'].update({PLAN: sha(ROOT / PLAN),
        relative(PREP / 'routes.json'): sha(PREP / 'routes.json'), relative(PREP / 'freeze.json'): sha(PREP / 'freeze.json')})
    review = {'baseline': authority_digest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'original_obligations_preserved': True,
        'changes': ['Complete lossless original reference reconciliation', 'Three payment links preserve tax qualifications and exclude RMB option',
            'Actual missing-link consumer effects and resealed adverse controls', 'Retain actual margin ACCEPT1817 and all failures'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN,
            'source_correction': 'Target uses nine selected intervals, not raw whole paragraph; two partial lines exclude RMB',
            'environment_correction': 'Unpinned preflight collected main-worktree package; retained failure; pinned tests pass44',
            'reproduced': relative(PREP / 'pre-repair.json'), 'whole_task_acceptance_claimed': False},
        'evidence_contract': {'primary': 'Independent original intervals, complete actual answers and exact matched omission',
            'veto': ['Lost qualification', 'Excluded option restored', 'Unrelated change', 'Hidden uncertainty', 'Method drift', 'Resource/harness failure'],
            'not_concluded': ['Whole graph', 'External tax-law application', 'Actual payment', 'Automatic discovery', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 13, 'new_maximum': 14,
            'retained_attempts': attempts, 'reason': 'New reproduced original payment-reference gap; no margin retry',
            'next_discriminating_check': 'Nine exact selected intervals preserve qualifications through actual complete consumer',
            'stop_condition': '180s stages;1000s new measured;160MiB;no further harness retry',
            'same_scope_authorization': 'User requested refresh and continued general build; no external-opinion prerequisite'}}
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 273, 'prior_admissions': len(attempts), 'methods': len(methods), 'resources': costs()}


def frozen():
    record = read(PREP / 'freeze.json')
    for name, expected in {**record['inputs'], **record['methods']}.items():
        if sha(ROOT / name) != expected:
            raise ValueError('Frozen payment reference input/method changed: ' + name)
    for name, expected in read(HERE / 'admission.json')['binding'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Admitted payment reference binding changed: ' + name)


def overlay(original, missing=()):
    value = deepcopy(original['P3']['payload']['interpretation_input'])
    value['reference_admission']['references'].extend(
        r for r in read(PREP / 'packet.json')['references'] if r['id'] not in missing)
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
    from scripts import prospectus_payment_reference_oracle as oracle
    missing = IDS if label.startswith('missing') else ()
    original, _ = baseline('candidate-answer')
    p = dict(original)
    p['P3'] = service.interpretation_product(p['P1'], p['P2'], overlay(original, missing))
    checked = oracle.verify(p, missing=missing)
    retain(label, p)
    return checked


def answer(label):
    from scripts import prospectus_payment_reference_oracle as oracle
    missing = IDS if label.startswith('missing') else ()
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
        result = pytest.main(['-q', *TESTS, '--junitxml=' + str(HERE / 'tests.xml')])
    if result:
        raise ValueError('Payment reference tests failed')
    return {'status': 'PASS'}


def upstream_controls():
    p, _ = baseline('candidate-answer')
    done = []
    for name in ('currency-only', 'missing-tax', 'raw-renminbi', 'renamed-link', 'question', 'source-edition'):
        began = time.monotonic()
        value = overlay(p)
        row = value['reference_admission']['references'][-3]
        if name == 'currency-only': row['targets'] = row['targets'][-1:]
        elif name == 'missing-tax': row['targets'].pop(2)
        elif name == 'raw-renminbi':
            from legalmath.prospectus.successor.occurrences import anchor
            raw = next(u for u in p['P1']['payload']['graph']['units'] if u['id'] == KEY + ':p114:l35')
            row['targets'][6]['source'] = anchor(raw)
        elif name == 'renamed-link': row['id'] = 'hidden'
        elif name == 'question': row['questions'] = ['Q1']
        elif name == 'source-edition': row['source']['source_sha256'] = '0' * 64
        try:
            service.interpretation_product(p['P1'], p['P2'], value)
        except ValueError as exc:
            if 'BASF payment reference' not in str(exc):
                raise
            save(HERE / 'controls' / (name + '.json'), {'case': name, 'status': 'PASS',
                'refusal': str(exc), 'wall_seconds': time.monotonic() - began})
            done.append(name)
        else:
            raise ValueError('Invalid actual P3 accepted: ' + name)
    return {'status': 'PASS', 'actual_refusals': done}


def consumer_control(label):
    p, _ = retained('missing-answer' if label == 'consumer-uncertainty' else 'candidate-answer')
    semantic = deepcopy(p['P3']['payload'])
    if label == 'consumer-dependency':
        dep = next(d for d in semantic['dependencies'] if d['id'] == 'reviewed-reference:' + IDS[0])
        dep['targets'] = dep['targets'][-1:]
        required = 'dependencies differ'
    elif label == 'consumer-uncertainty':
        semantic['questions']['Q2']['subquestions'][next(iter(semantic['questions']['Q2']['subquestions']))]['unresolved'].remove('payment-reference:' + IDS[2])
        required = 'hides or invents'
    else:
        row = semantic['interpretation_input']['reference_admission']['references'][-3]
        row['targets'] = row['targets'][-1:]
        required = 'complete selected payment paragraph'
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
    from scripts import prospectus_payment_reference_oracle as oracle
    from scripts.prospectus_typed_delta import equal
    checks = []
    for label, missing in (('candidate-answer', ()), ('missing-answer', IDS)):
        p, a = retained(label)
        checks.append(oracle.verify(p, a, missing=missing))
        actual = reconcile(p)
        equal(actual, read(PREP / ('reconciliation-before.json.gz' if missing else 'reconciliation-proposed.json.gz')),
              'Original reference inventory reconciliation changed')
        save(HERE / (label + '-reconciliation.json.gz'), actual)
    return {'status': 'PASS', 'independent_cases': checks, 'original_records_preserved': 60,
        'scalar_provenance_records_preserved': 2, 'original_task_complete': False}


def seal():
    resources = costs()
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'complete_reference_graph': False, 'actual_ordinary_answers': 2, 'actual_upstream_refusals': 6,
        'actual_consumer_refusals': 3, 'original_inventory_records': 60, 'scalar_provenance_records': 2,
        'resources': resources, 'historical_admissions_retained': 13,
        'remaining': ['Other exact contractual targets', 'Self/cyclic scope', 'Statutory originals and applicable editions',
                      'Unqualified defined-term uses', 'Complete original reference acceptance'],
        'next_action': 'Use candidate-answer-reconciliation.json.gz for original remaining source work; no further payment harness retry'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'commands': ['.venv/bin/python -m scripts.prospectus_payment_references ' + s for s in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;CUDA_VISIBLE_DEVICES=-1;GPU deliberately hidden',
        'data_version': sha(PREP / 'source-review.json'), 'seeds': 'N/A deterministic source checks',
        'wall_time': resources, 'plan': PLAN, 'result': relative(HERE / 'result.json'),
        'artifacts': relative(HERE), 'method_freeze': sha(PREP / 'freeze.json'),
        'prior_admissions': read(PREP / 'review.json')['budget_revision']['retained_attempts']})
    (HERE / 'RESULT.md').write_text('''# Payment reference result

The three original payment references now bind the complete selected section
4(2). Nine intervals preserve its tax qualifications while excluding the
renminbi option. The old generic checker accepted only the last currency
sentence, silently dropping the qualifications. Exact source admission and
final-consumer recomputation now reject that alteration.

Two complete P3–P5 ordinary answers, six actual P3 refusals and three separately
receipted final-consumer refusals passed. The independent oracle verifies the
source images, interval boundaries, every prior meaning/dependency and complete
answer content. Omitting all three links adds precisely the declared unresolved
dependencies. All 47 historical records, 13 additional findings and both scalar
provenance records remain losslessly reconciled with the actual answer inputs.

| Decision | Primary criterion | Veto status | Uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain three source-reference repairs | Independent source and whole-answer checks pass | Truncation, excluded text, changed identity and resealed forgeries refused | Other contractual references and external law remain open | Continue original reconciled remainder | Complete graph, actual payment, external tax-law interpretation or whole build |

This was a local source-integration gap. No third-party package was shown to
fail. The strongest alternative explanation is an incorrect development reading
of the selection; the original images, partial source intervals and excluded
branch checks make that reading reviewable. Another operative edition or final
term selection requires another source review. The finite development inventory
is not a recall denominator. Timing is descriptive only.

The first unpinned preflight resolved the main checkout and failed collection.
That failure is retained; pinned tests and the admitted runner use this checkout.
No passing test count substitutes for the actual consumer evidence. Historical
margin failures and ACCEPT1817 remain intact, with revalidation after shared
methods stabilize. Historical authoring/controller time remains unknown.
''')
    return {'status': 'PASS', 'original_task_complete': False, 'resources': resources}


def main():
    label = sys.argv[1]
    if label == 'propose':
        print(json.dumps(propose()))
        return
    if label not in STAGES:
        raise ValueError('Unknown reviewed payment stage')
    frozen()
    index = STAGES.index(label)
    if index:
        assert read(HERE / 'stages' / STAGES[index - 1] / 'result.json')['status'] == 'PASS'
    costs()
    began = time.monotonic()
    folder = HERE / 'stages' / label
    save(folder / 'started.json', {'command': sys.argv, 'stage_seconds': 180,
        'started_at': datetime.now(timezone.utc).isoformat()})
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Payment reference stage bound')))
    signal.alarm(180)
    try:
        if label.endswith('-p3'):
            result = interpretation(label)
        elif label.endswith('-answer'):
            result = answer(label)
        elif label.startswith('consumer-'):
            result = consumer_control(label)
        else:
            result = globals()[label.replace('-', '_')]()
        frozen()
        assert result['status'] == 'PASS'
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
