"""Separately receipted internal-target and actual-consumer trial; CPU only."""
from copy import deepcopy
from datetime import datetime, timezone
import contextlib
import json
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
from scripts.prospectus_margin_preparation import AUTH, DONOR, read, save, sha, relative, products
from scripts.prospectus_financial_references import retained as baseline
from scripts.prospectus_internal_reference_preparation import PREP, SPEC, IDS, LEDGER, reseal
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

HERE = AUTH / 'attempts/basf-references/attempt-020'
PLAN = 'docs/plans/prospectus-internal-reference-closure-2026-10-18.md'
TESTS = ['tests/prospectus_successor/' + name for name in (
    'test_basf_internal_references.py', 'test_consumed_reference_closure.py',
    'test_basf_financial_references.py', 'test_basf_substitution_references.py',
    'test_basf_default_references.py', 'test_reference_unknown_targets.py',
    'test_basf_governance_references.py', 'test_reference_consumer_integrity.py',
    'test_basf_call_references.py', 'test_basf_payment_references.py',
    'test_closure_references.py', 'test_closure_reference_replacement.py', 'test_unavailable_references.py')]
CONSUMERS = ('roots', 'reachable', 'cycle', 'closure-drop', 'closure-duplicate', 'closure-invent',
    'dependency-drop', 'dependency-status', 'question-closure', 'question-status',
    'subquestion-status', 'subquestion-missing', 'q3-status', 'q3-value', 'target')
STAGES = ('tests', 'candidate-p3', 'candidate-answer', 'missing-p3', 'missing-answer',
    'upstream-controls', *('consumer-' + c for c in CONSUMERS), 'validate', 'seal')


def costs():
    receipts = [f for pattern in ('preparation*result.json', 'preparation*failure.json',
                                 'preflight*result.json', 'preflight*failure.json') for f in PREP.glob(pattern)]
    receipts += [f for pattern in ('stages/*/result.json', 'stages/*/failure.json') for f in HERE.glob(pattern)]
    seconds = sum(read(f)['wall_seconds'] for f in receipts)
    size = sum(f.stat().st_size for folder in (PREP, HERE) if folder.exists()
               for f in folder.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
    extra = [ROOT / PLAN, SPEC, Path(__file__), AUTH / 'program.json', AUTH / 'revisions/0279.json',
             ROOT / 'scripts/prospectus_internal_reference_preparation.py',
             ROOT / 'scripts/prospectus_internal_reference_oracle.py',
             ROOT / 'scripts/prospectus_internal_revision.py',
             ROOT / 'src/legalmath/prospectus/successor/basf_internal_references.py',
             *(ROOT / t for t in TESTS)]
    size += sum(f.stat().st_size for f in extra if f.exists())
    if seconds >= 1800 or size >= 188 * 1024**2:
        raise ValueError('Internal reference cumulative resource bound exhausted')
    return {'new_measured_seconds': seconds, 'new_counted_bytes': size,
            'new_seconds_bound': 1800, 'new_bytes_bound': 192 * 1024**2,
            'reserve_bytes': 4 * 1024**2, 'prior_admissions_retained': 19,
            'unmeasured_authoring_controller_time': 'UNKNOWN'}


def frozen():
    record = read(PREP / 'freeze.json')
    for name, checksum in {**record['inputs'], **record['methods']}.items():
        if sha(ROOT / name) != checksum:
            raise ValueError('Frozen internal method/input changed: ' + name)
    for name, checksum in read(HERE / 'admission.json')['binding'].items():
        if sha(ROOT / name) != checksum:
            raise ValueError('Admitted internal binding changed: ' + name)


def retain(label, p, a=None):
    from scripts.prospectus_typed_delta import changes, apply, equal
    original = products()
    delta = changes(original, p)
    equal(apply(original, delta), p, 'Lossy products')
    out = {'products_delta': delta, 'products_sha256': digest(p)}
    if a is not None:
        old = read(DONOR / 'installed-answer/ordinary-answer.json.gz')
        delta = changes(old, a)
        equal(apply(old, delta), a, 'Lossy ordinary answer')
        out.update(answer_delta=delta, answer_sha256=digest(a))
    save(HERE / (label + '.json.gz'), out)


def retained(label):
    from scripts.prospectus_typed_delta import apply
    row = read(HERE / (label + '.json.gz'))
    p = apply(products(), row['products_delta'])
    assert digest(p) == row['products_sha256']
    a = None
    if 'answer_delta' in row:
        a = apply(read(DONOR / 'installed-answer/ordinary-answer.json.gz'), row['answer_delta'])
        assert digest(a) == row['answer_sha256']
    return p, a


def interpretation(label):
    from scripts.prospectus_internal_reference_oracle import verify
    p, _ = baseline('candidate-answer')
    value = deepcopy(p['P3']['payload']['interpretation_input'])
    missing = IDS if label.startswith('missing') else ()
    value['reference_admission']['references'].extend(
        r for r in read(PREP / 'packet.json')['references'] if r['id'] not in missing)
    p['P3'] = service.interpretation_product(p['P1'], p['P2'], value)
    result = verify(p, missing=missing)
    retain(label, p)
    return result


def answer(label):
    from scripts.prospectus_internal_reference_oracle import verify
    p, _ = retained(label.replace('-answer', '-p3'))
    missing = IDS if label.startswith('missing') else ()
    old4, old5 = p['P4']['payload'], p['P5']['payload']
    p['P4'] = service.law_product(p['P1'], p['P3'], old4['cases'], old4['law_input'])
    p['P5'] = service.financial_product(p['P1'], p['P2'], p['P3'], old5['cases'], old5['scenario_input'])
    actual = service.consume(p, ROOT, mode='frozen')
    result = verify(p, actual, missing=missing)
    retain(label, p, actual)
    return result


def run_tests(folder, label):
    import pytest
    with (folder / (label + '.log')).open('x') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        code = pytest.main(['-q', *TESTS, '--junitxml=' + str(folder / (label + '.xml'))])
    if code:
        raise ValueError('Internal reference tests failed; see retained log')
    return {'status': 'PASS'}


def tests():
    return run_tests(HERE, 'tests')


def upstream_controls():
    p, _ = baseline('candidate-answer')
    cases = ('truncate', 'tax-exception', 'holder-ending', 'substitution-ending',
             'proof-ending', 'rename', 'question', 'edition', 'duplicate', 'language', 'discovery')
    for case in cases:
        began = time.monotonic()
        value = deepcopy(p['P3']['payload']['interpretation_input'])
        rows = deepcopy(read(PREP / 'packet.json')['references'])
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
    try:
        service.consume(reseal(p, semantic), ROOT, mode='frozen')
    except ValueError as exc:
        if required not in str(exc):
            raise
        return {'status': 'PASS', 'case': label, 'actual_consumer_refusal': str(exc)}
    raise ValueError('Forged internal consumer accepted: ' + label)


def validate():
    from scripts.prospectus_internal_reference_oracle import verify
    from scripts.prospectus_typed_delta import equal
    checks = []
    for label, missing in (('candidate-answer', ()), ('missing-answer', IDS)):
        p, a = retained(label)
        checks.append(verify(p, a, missing=missing))
        ledger = read(AUTH / 'attempts/basf-references/attempt-019/candidate-answer-reconciliation.json.gz')
        originals = deepcopy([r['original'] for r in ledger['records']])
        rows = {r['id']: r for r in p['P3']['payload']['interpretation_input']['reference_admission']['references']}
        for (family, index), key in zip(LEDGER, IDS):
            record = next(r for r in ledger['records'] if r['family'] == family and r['index'] == index)
            if key in rows:
                record.update(current_reference=rows[key], current_status='CURRENT_LINK_WITH_CONSERVATIVE_CLOSURE',
                              complete_legal_interpretation=False)
        equal([r['original'] for r in ledger['records']], originals, 'Original inventory changed')
        expected = read(PREP / 'reconciliation-proposed.json.gz') if not missing else read(
            AUTH / 'attempts/basf-references/attempt-019/candidate-answer-reconciliation.json.gz')
        equal(ledger, expected, 'Current internal mapping differs')
        save(HERE / (label + '-reconciliation.json.gz'), ledger)
    return {'status': 'PASS', 'independent_cases': checks, 'original_records_preserved': 60,
            'original_task_complete': False}


def seal():
    resources = costs()
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'new_source_links': 10, 'actual_ordinary_answers': 2, 'actual_upstream_refusals': 11,
        'actual_consumer_refusals': len(CONSUMERS), 'original_inventory_records': 60, 'resources': resources,
        'remaining': ['Statutory originals and applicability', 'Unqualified defined terms',
            'Original reference acceptance and general discovery'],
        'next_action': 'Continue original source remainder from candidate-answer-reconciliation.json.gz; all47reviewed links retained'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'commands': ['.venv/bin/python -m scripts.prospectus_internal_references ' + s for s in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU deliberately hidden',
        'data_version': sha(PREP / 'source-review.json'), 'seeds': 'N/A deterministic', 'wall_time': resources,
        'plan': PLAN, 'result': relative(HERE / 'result.json'), 'artifacts': relative(HERE),
        'method_freeze': sha(PREP / 'freeze.json'),
        'prior_admissions': read(PREP / 'review.json')['budget_revision']['retained_attempts']})
    (HERE / 'RESULT.md').write_text('''# Complete internal scopes and consumed reference closure

Ten original internal findings bind their full selected scopes, including tax
exceptions, holder-notice periods, cross-page substitution and proof conditions.
The source-specific validator retains issuer exclusions and UNKNOWN tax headings.
The ordinary consumer reconstructs all dependencies and reference closure and
checks propagation into Q1, Q2, every subquestion and stored semantic Q3.
Deterministic traversal retains conservative source cycles; these cycles do not
establish a legal inconsistency in the prospectus. The independent oracle rebuilds
original intervals, raw/reviewed edges, closure and the entire ordinary answer.

| Decision | Primary criterion | Veto diagnostics | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain complete internal links and consumer repair | Original intervals and complete candidate/omission answers match independent reconstruction | Target truncation, source/discovery changes, closure forgery and hidden uncertainty refused | Statutory application, actual events, remaining defined terms | Continue original reference remainder | Universal legal correctness, automatic discovery or whole build completion |

The reproduced gaps were implementation failures in source-specific admission
and ordinary-consumer verification. No external-package limitation follows.
The strongest alternative explanation is a shared interpretation of an original
page; independently transcribed bounds, source hashes and adverse controls limit
that risk. A contrary source reading requires a new reviewed revision. All sixty
original records and all prior costs remain retained. The preparation timeout is
counted and was followed by separately bounded checks, not an unchanged retry.
''')
    return {'status': 'PASS', 'original_task_complete': False, 'resources': resources}


def preflight(label):
    if label in ('preflight-tests', 'preflight-tests-v2', 'preflight-tests-v3'):
        return run_tests(PREP, label)
    if label in ('preflight-source', 'preflight-source-v2', 'preflight-source-v3', 'preflight-source-v4'):
        from scripts.prospectus_internal_reference_oracle import originals, independent_closures
        p, _ = baseline('candidate-answer')
        rows, _, _ = originals(p)
        closures = independent_closures(p, p['P3']['payload']['dependencies'])
        return {'status': 'PASS', 'independent_original_links': len(rows),
            'baseline_reconstructed_roots': {d['id']: len(d['roots']) for d in closures},
            'baseline_reconstructed_cycles': {d['id']: [s for s in d['unresolved']
                if s.startswith('Unsupported reference cycle:')] for d in closures}}
    raise ValueError('Unknown preflight stage')


def main():
    label = sys.argv[1]
    if label == 'propose':
        from scripts.prospectus_internal_revision import propose
        print(json.dumps(propose()))
        return
    preparation = label.startswith('preflight-')
    if not preparation and label not in STAGES:
        raise ValueError('Unknown internal reference stage')
    if not preparation:
        frozen()
        index = STAGES.index(label)
        if index:
            assert read(HERE / 'stages' / STAGES[index - 1] / 'result.json')['status'] == 'PASS'
    costs()
    folder = PREP if preparation else HERE / 'stages' / label
    marker = folder / (label + '-started.json' if preparation else 'started.json')
    if marker.exists():
        raise ValueError('Internal stage already started; no unchanged retry')
    began = time.monotonic()
    save(marker, {'command': sys.argv, 'stage_seconds': 180,
        'started_at': datetime.now(timezone.utc).isoformat()})
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Internal reference stage180s')))
    signal.alarm(180)
    try:
        if preparation:
            result = preflight(label)
        elif label.endswith('-p3'):
            result = interpretation(label)
        elif label.endswith('-answer'):
            result = answer(label)
        elif label.startswith('consumer-'):
            result = consumer(label)
        else:
            result = globals()[label.replace('-', '_')]()
        if not preparation:
            frozen()
        assert result['status'] == 'PASS'
        result['wall_seconds'] = time.monotonic() - began
        save(folder / (label + '-result.json' if preparation else 'result.json'), result)
        if label == 'seal':
            save(HERE / 'outputs.json', {str(f.relative_to(HERE)): sha(f) for f in sorted(HERE.rglob('*'))
                if f.is_file() and '__pycache__' not in f.parts})
        print(json.dumps(result))
    except BaseException as exc:
        save(folder / (label + '-failure.json' if preparation else 'failure.json'),
             {'type': type(exc).__name__, 'message': str(exc), 'wall_seconds': time.monotonic() - began})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
