"""Frozen, receipted original financial-reference trial; worktree imports pinned."""
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
import xml.etree.ElementTree as ET

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from scripts.prospectus_margin_preparation import AUTH, DONOR, read, save, sha, relative, products
from scripts.prospectus_substitution_references import retained as baseline
from scripts.prospectus_financial_reference_preparation import PREP, SPEC, IDS, LEDGER
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

HERE = AUTH / 'attempts/basf-references/attempt-019'
PLAN = 'docs/plans/prospectus-financial-references-2026-10-18.md'
TESTS = ['tests/prospectus_successor/' + name for name in (
    'test_basf_financial_references.py', 'test_basf_substitution_references.py',
    'test_basf_default_references.py', 'test_reference_unknown_targets.py',
    'test_basf_governance_references.py', 'test_reference_consumer_integrity.py',
    'test_basf_call_references.py', 'test_basf_payment_references.py',
    'test_closure_references.py', 'test_closure_reference_replacement.py')]
STAGES = ('tests', 'candidate-p3', 'candidate-answer', 'missing-p3', 'missing-answer',
    'upstream-controls', 'consumer-change', 'consumer-drop', 'consumer-invent',
    'consumer-duplicate', 'consumer-uncertainty', 'consumer-target', 'consumer-resolve',
    'consumer-meaning', 'consumer-closure', 'validate', 'seal')


def costs():
    seconds = sum(read(f)['wall_seconds'] for f in PREP.glob('preparation*json')
                  if f.name.endswith(('result.json', 'failure.json')))
    seconds += sum(read(f)['wall_seconds'] for pattern in ('preflight*result.json', 'preflight*failure.json')
                   for f in PREP.glob(pattern))
    seconds += sum(read(f)['wall_seconds'] for pattern in ('stages/*/result.json', 'stages/*/failure.json')
                   for f in HERE.glob(pattern))
    size = sum(f.stat().st_size for folder in (PREP, HERE) if folder.exists()
               for f in folder.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
    extra = [ROOT / PLAN, SPEC, Path(__file__), AUTH / 'program.json', AUTH / 'revisions/0278.json',
             ROOT / 'scripts/prospectus_financial_reference_preparation.py',
             ROOT / 'scripts/prospectus_financial_reference_oracle.py',
             ROOT / 'scripts/prospectus_financial_revision.py',
             ROOT / 'src/legalmath/prospectus/successor/basf_financial_references.py',
             *(ROOT / t for t in TESTS)]
    size += sum(f.stat().st_size for f in extra if f.exists())
    if seconds >= 1200 or size >= 156 * 1024**2:
        raise ValueError('Financial reference cumulative resource bound exhausted')
    return {'new_measured_seconds': seconds, 'new_counted_bytes': size,
            'new_seconds_bound': 1200, 'new_bytes_bound': 160 * 1024**2,
            'reserve_bytes': 4 * 1024**2, 'prior_admissions_retained': 18,
            'unmeasured_authoring_controller_time': 'UNKNOWN'}


def frozen():
    record = read(PREP / 'freeze.json')
    for name, checksum in {**record['inputs'], **record['methods']}.items():
        if sha(ROOT / name) != checksum:
            raise ValueError('Frozen financial method/input changed: ' + name)
    for name, checksum in read(HERE / 'admission.json')['binding'].items():
        if sha(ROOT / name) != checksum:
            raise ValueError('Admitted financial binding changed: ' + name)


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
    from scripts.prospectus_financial_reference_oracle import verify
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
    from scripts.prospectus_financial_reference_oracle import verify
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
        raise ValueError('Financial reference tests failed; see retained log')
    return {'status': 'PASS'}


def tests():
    return run_tests(HERE, 'tests')


def upstream_controls():
    p, _ = baseline('candidate-answer')
    done = []
    for case in ('truncate', 'missing-section', 'missing-paragraph', 'wrong-tax-branch',
                 'missing-formula', 'rename', 'question', 'edition', 'duplicate'):
        began = time.monotonic()
        value = deepcopy(p['P3']['payload']['interpretation_input'])
        rows = deepcopy(read(PREP / 'packet.json')['references'])
        if case == 'truncate':
            rows[0]['targets'] = rows[0]['targets'][-1:]
        elif case == 'missing-section':
            rows.pop(0)
        elif case == 'missing-paragraph':
            rows.pop(1)
        elif case == 'wrong-tax-branch':
            rows[4]['targets'] = deepcopy(rows[0]['targets'])
        elif case == 'missing-formula':
            rows[3]['targets'] = rows[3]['targets'][:3]
        elif case == 'rename':
            rows[0]['id'] = 'hidden'
        elif case == 'question':
            rows[0]['questions'] = ['Q1']
        elif case == 'edition':
            rows[0]['source']['source_sha256'] = '0' * 64
        else:
            rows.append(deepcopy(rows[0]))
        value['reference_admission']['references'].extend(rows)
        try:
            service.interpretation_product(p['P1'], p['P2'], value)
        except ValueError as exc:
            if 'BASF financial' not in str(exc):
                raise
            save(HERE / 'controls' / (case + '.json'), {'status': 'PASS', 'case': case,
                'refusal': str(exc), 'wall_seconds': time.monotonic() - began})
            done.append(case)
        else:
            raise ValueError('Invalid financial P3 accepted: ' + case)
    return {'status': 'PASS', 'actual_P3_refusals': done}


def consumer(label):
    p, _ = retained('missing-answer' if label == 'consumer-uncertainty' else 'candidate-answer')
    semantic = deepcopy(p['P3']['payload'])
    dep = next(d for d in semantic['dependencies'] if d['id'] == 'reviewed-reference:' + IDS[0]) if label != 'consumer-uncertainty' else None
    required = 'dependencies differ'
    if label == 'consumer-change':
        dep['targets'] = dep['targets'][:2]
    elif label == 'consumer-drop':
        semantic['dependencies'].remove(dep)
    elif label == 'consumer-invent':
        semantic['dependencies'].append({**deepcopy(dep), 'id': 'reviewed-reference:invented'})
    elif label == 'consumer-duplicate':
        semantic['dependencies'].append(deepcopy(dep))
    elif label == 'consumer-resolve':
        next(d for d in semantic['dependencies'] if d['id'] == 'reviewed-reference:' + IDS[2])['status'] = 'RESOLVED'
    elif label == 'consumer-meaning':
        semantic['questions']['Q2']['subquestions'][next(iter(semantic['questions']['Q2']['subquestions']))]['unresolved'].remove('reviewed-reference:' + IDS[2])
        required = 'hides or invents'
    elif label == 'consumer-closure':
        next(d for d in semantic['dependencies'] if d['id'] == 'reference-closure:Q1')['unresolved'].remove('Unresolved reference: reviewed-reference:' + IDS[2])
        required = 'closure hides or invents'
    elif label == 'consumer-uncertainty':
        semantic['questions']['Q2']['subquestions'][next(iter(semantic['questions']['Q2']['subquestions']))]['unresolved'].remove('financial-reference:' + IDS[4])
        required = 'hides or invents'
    else:
        row = next(r for r in semantic['interpretation_input']['reference_admission']['references'] if r['id'] == IDS[0])
        row['targets'] = row['targets'][:2]
        required = 'exact complete selected target'
    bundle = p['P1']['payload']['request']['bundle']
    p['P3'] = service.seal('P3', bundle, p['P3']['inputs'], semantic)
    for stage in ('P4', 'P5'):
        p[stage] = service.seal(stage, bundle, {**p[stage]['inputs'], 'P3': p['P3']['sha256']}, p[stage]['payload'])
    try:
        service.consume(p, ROOT, mode='frozen')
    except ValueError as exc:
        if required not in str(exc):
            raise
        return {'status': 'PASS', 'case': label, 'actual_consumer_refusal': str(exc)}
    raise ValueError('Forged financial consumer accepted: ' + label)


def validate():
    from scripts.prospectus_financial_reference_oracle import verify
    from scripts.prospectus_typed_delta import equal
    checks = []
    for label, missing in (('candidate-answer', ()), ('missing-answer', IDS)):
        p, a = retained(label)
        checks.append(verify(p, a, missing=missing))
        ledger = read(AUTH / 'attempts/basf-references/attempt-018/candidate-answer-reconciliation.json.gz')
        originals = deepcopy([r['original'] for r in ledger['records']])
        rows = {r['id']: r for r in p['P3']['payload']['interpretation_input']['reference_admission']['references']}
        for (family, index), key in zip(LEDGER, IDS):
            record = next(r for r in ledger['records'] if r['family'] == family and r['index'] == index)
            if key in rows:
                record['current_reference'] = rows[key]
                record['current_status'] = 'CURRENT_LINK_AND_UNRESOLVED_TARGET_MEANING' if key == IDS[2] else 'CURRENT_REVIEWED_LINK'
        equal([r['original'] for r in ledger['records']], originals, 'Original inventory changed')
        expected = read(PREP / 'reconciliation-proposed.json.gz') if not missing else read(
            AUTH / 'attempts/basf-references/attempt-018/candidate-answer-reconciliation.json.gz')
        equal(ledger, expected, 'Current inventory mapping differs')
        save(HERE / (label + '-reconciliation.json.gz'), ledger)
    return {'status': 'PASS', 'independent_cases': checks, 'original_records_preserved': 60, 'original_task_complete': False}


def seal():
    resources = costs()
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'new_source_links': 5, 'actual_ordinary_answers': 2, 'actual_upstream_refusals': 9,
        'actual_consumer_refusals': 9, 'original_inventory_records': 60, 'resources': resources,
        'remaining': ['Original tax conditions and reverse links', 'Statutory originals and applicability',
            'Self/cyclic scope', 'Unqualified defined terms', 'Complete original reference acceptance'],
        'next_action': 'Continue original source remainder from candidate-answer-reconciliation.json.gz; all37reviewed links retained'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'commands': ['.venv/bin/python -m scripts.prospectus_financial_references ' + s for s in STAGES],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU deliberately hidden',
        'data_version': sha(PREP / 'source-review.json'), 'seeds': 'N/A deterministic', 'wall_time': resources,
        'plan': PLAN, 'result': relative(HERE / 'result.json'), 'artifacts': relative(HERE),
        'method_freeze': sha(PREP / 'freeze.json'),
        'prior_admissions': read(PREP / 'review.json')['budget_revision']['retained_attempts']})
    (HERE / 'RESULT.md').write_text('''# Original financial-reference targets

The split maturity citation binds both adjacent source parts to the complete
selected maturity paragraph, retaining prior redemption and nominal-amount
qualifications and the final-term maturity date. The coupon citation retains
interest start, rate, annual payment date, first payment date and its UNKNOWN
heading. The day-count link binds the selected annual formula, preserving the
complete cross-page exclusion of the reference-period branch. The tax-call
amount links only section5(10)(a), with the paragraph7alternative removed.

The separate oracle reconstructs all source and final-term intervals and
character maps. Complete candidate and omission P3-P5 products and ordinary
answers are retained. Nine upstream and nine actual resealed-consumer controls
refuse truncation, unpaired citations, wrong targets, forgery and concealed
uncertainty. All32previous links, five default UNKNOWN uses,13amendment UNKNOWN
uses and all60original inventory records survive unchanged. The historical
substitution_basis with document/path/text-hash/offset provenance is preserved.

| Decision | Primary criterion | Veto diagnostics | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain five complete original links | Independent original intervals/maps and full answers match | Wrong targets, pair omissions, scalar provenance, false resolution and concealment refused | Tax application, actual payments and remaining original references | Continue original source/tax/cycle work | Automatic interpretation, whole task or whole build completion |

The reproduced failures were incomplete source-specific admission and use of
selected scalar provenance. They are implementation gaps; this trial neither
establishes nor rejects any external package's general capability. Strongest
alternative explanation is a shared original-page interpretation error. Exact
independently transcribed bounds and adverse controls constrain it; a contrary
source reading would require a new reviewed revision. Untested jurisdictions
and generic automatic discovery remain outside this finite evidence.
''')
    return {'status': 'PASS', 'original_task_complete': False, 'resources': resources}


def main():
    label = sys.argv[1]
    if label == 'propose':
        from scripts.prospectus_financial_revision import propose
        print(json.dumps(propose()))
        return
    if label in ('preflight', 'preflight-repaired'):
        signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Financial preflight180s')))
        signal.alarm(180)
        began = time.monotonic()
        try:
            from scripts.prospectus_financial_reference_oracle import originals
            originals(baseline('candidate-answer')[0])
            result = run_tests(PREP, label + '-tests')
            save(PREP / 'preflight-result.json', {**result, 'wall_seconds': time.monotonic() - began})
            print(json.dumps(result))
        except BaseException as exc:
            save(PREP / (label + '-failure.json'), {'type': type(exc).__name__, 'message': str(exc),
                 'wall_seconds': time.monotonic() - began})
            raise
        finally:
            signal.alarm(0)
        return
    if label not in STAGES:
        raise ValueError('Unknown financial reference stage')
    frozen()
    index = STAGES.index(label)
    if index:
        assert read(HERE / 'stages' / STAGES[index - 1] / 'result.json')['status'] == 'PASS'
    costs()
    began = time.monotonic()
    folder = HERE / 'stages' / label
    if folder.exists():
        raise ValueError('Financial stage already started; no unchanged retry')
    save(folder / 'started.json', {'command': sys.argv, 'stage_seconds': 180,
        'started_at': datetime.now(timezone.utc).isoformat()})
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Financial reference stage180s')))
    signal.alarm(180)
    try:
        if label.endswith('-p3'):
            result = interpretation(label)
        elif label.endswith('-answer'):
            result = answer(label)
        elif label.startswith('consumer-'):
            result = consumer(label)
        else:
            result = globals()[label.replace('-', '_')]()
        frozen()
        assert result['status'] == 'PASS'
        result['wall_seconds'] = time.monotonic() - began
        save(folder / 'result.json', result)
        if label == 'seal':
            save(HERE / 'outputs.json', {str(f.relative_to(HERE)): sha(f) for f in sorted(HERE.rglob('*'))
                if f.is_file() and '__pycache__' not in f.parts})
        print(json.dumps(result))
    except BaseException as exc:
        save(folder / 'failure.json', {'type': type(exc).__name__, 'message': str(exc),
            'wall_seconds': time.monotonic() - began})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
