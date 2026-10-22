"""Bounded registration-source validation through genuine retained P1 and P5/P6."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from math import gcd, lcm
from pathlib import Path
import gzip
import json
import os
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash
from legalmath.prospectus.successor import cases, service, source_graph
from scripts import prospectus_conversion_source_primary as common

PLAN = 'docs/plans/prospectus-registration-groups-2026-10-18.md'
REVIEW = ROOT / REL / 'reviews/registration-groups-253'
HERE = ROOT / REL / 'attempts/entitlement/attempt-009'
PRIOR = ROOT / REL / 'attempts/entitlement/attempt-008'
STAGES = ('tests', 'bbva', 'seb', 'seal')
TESTS = common.TESTS + ['tests/prospectus_successor/test_registration_groups.py']


def require(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def compressed(path, value):
    with path.open('xb') as stream:
        stream.write(gzip.compress(json.dumps(value, sort_keys=True, allow_nan=False).encode(), mtime=0))


def retain_controls(path, records, original):
    """Losslessly share unchanged questions rather than duplicating source text."""
    shared = {k: v for k, v in original['questions'].items() if k != 'Q5'}
    encoded = deepcopy(records)
    for saved, actual in zip(encoded, records):
        questions = saved['answer']['questions']
        for key, value in shared.items():
            if questions.get(key) == value:
                questions[key] = {'$question_ref': key}
        restored = deepcopy(saved)
        for key, value in shared.items():
            if restored['answer']['questions'].get(key) == {'$question_ref': key}:
                restored['answer']['questions'][key] = deepcopy(value)
        require(restored == actual, 'Full retained answer reconstruction differs')
    compressed(path, {'format': 'shared-answer-questions.v1', 'shared_questions': shared,
                      'records': encoded, 'full_answer_reconstruction_checked': True})


def methods_unchanged():
    frozen = read(REVIEW / 'freeze.json')
    current = {str(p.relative_to(ROOT)) for p in (ROOT / 'src/legalmath').rglob('*')
               if p.is_file() and '__pycache__' not in p.parts}
    require(current == set(frozen['production']), 'Production file inventory changed')
    for name, expected in {**frozen['methods'], **frozen['retained']}.items():
        require(file_hash(ROOT / name) == expected, 'Frozen input/method changed: ' + name)


def measured_seconds():
    return (read(PRIOR / 'run-manifest.json')['measured_seconds_including_preparation']
            + read(REVIEW / 'preparation-result.json')['seconds']
            + read(REVIEW / 'freeze.json')['seconds']
            + sum(read(p)['seconds'] for p in (HERE / 'stages').glob('*/result.json')))


def storage():
    paths = [ROOT / REL / 'reviews' / x for x in
             ('conversion-source-primary-251', 'conversion-source-followup-252', 'registration-groups-253')]
    paths += [ROOT / REL / 'attempts/entitlement' / x for x in ('attempt-007', 'attempt-008', 'attempt-009')]
    for revision, name in ((251, 'conversion-source-primary'), (252, 'conversion-source-followup'),
                           (253, 'registration-groups')):
        paths += [ROOT / REL / f'proposals/{name}-{revision}.json',
                  ROOT / REL / f'proposals/{name}-{revision}-review.json',
                  ROOT / REL / f'revisions/{revision:04d}.json',
                  ROOT / REL / f'closure-routes-2026-10-18-{name}-{revision}.json']
    paths += [ROOT / 'docs/plans' / x for x in
              ('prospectus-conversion-source-primary-2026-10-18.md',
               'prospectus-conversion-source-followup-2026-10-18.md',
               'prospectus-registration-groups-2026-10-18.md')]
    paths += [ROOT / 'scripts' / x for x in
              ('prospectus_conversion_source_primary.py', 'prospectus_conversion_source_followup.py',
               'prospectus_registration_prepare.py', 'prospectus_registration_groups.py')]
    paths += [ROOT / name for name in TESTS if 'registration_groups' in name or
              name.endswith('test_conversion_source_primary.py') or name.endswith('test_closure_mechanisms.py')]
    files = set()
    for path in paths:
        if path.is_dir():
            files.update(p for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
        elif path.is_file():
            files.add(path)
    return sum(p.stat().st_size for p in files)


def authenticate():
    auth = Authority(ROOT)
    program, tasks, _ = auth.spec()
    admission = read(HERE / 'admission.json')
    require(program['revision'] == 253 and admission['task'] == 'entitlement', 'Wrong admission')
    require(admission['binding'] == auth.binding(tasks['entitlement']), 'Admission binding changed')
    event = next(e for e in reversed(auth.events()) if e.get('task') == 'entitlement')
    require(event['kind'] == 'ADMIT' and event['attempt'] == str(HERE.relative_to(ROOT)), 'No active admission009')
    methods_unchanged()
    require(measured_seconds() < 480 and storage() + 1024**2 < 80 * 1024**2, 'Original cumulative ceiling')
    source_graph.pdf_units = lambda *_: (_ for _ in ()).throw(ValueError('Six native calls already used'))
    return admission


def tests():
    common.HERE, common.TESTS = HERE, TESTS
    return common.tests()


def canonical(n, d):
    factor = gcd(n, d)
    n, d = n // factor, d // factor
    return str(n) if d == 1 else f'{n}/{d}'


def oracle(s, q):
    """Independent integer quotient/remainder at the reviewed unlisted price3."""
    require(q['status'] == 'CONDITIONAL', 'Explicit valid partition refused')
    c = q['value']['calculation']
    pricekey = 'conversion_price_usd' if s['issue_id'].startswith('seb') else 'conversion_price'
    require(c[pricekey] == '3' and c['conversion'] is True, 'Wrong source price or conversion')
    require('holder_entitlements' not in c and c['beneficial_holder_allocation'] == 'NOT_ESTABLISHED'
            and c['registration_grouping'] == 'SUPPLIED_SAME_REGISTRATION_PARTITION', 'False holder allocation')
    field = 'principal' if s['issue_id'].startswith('seb') else 'liquidation_preference'
    # Group IDs are explicit conditional premises; names are never normalised.
    rows = []
    for key in sorted({h['registration_group_id'] for h in s['holdings']}):
        parts = [h for h in s['holdings'] if h['registration_group_id'] == key]
        ratios = [Decimal(h[field]).as_integer_ratio() for h in parts]
        denominator = lcm(*(d for _, d in ratios))
        numerator = sum(n * (denominator // d) for n, d in ratios)
        shares, remainder = divmod(numerator, 3 * denominator)
        rows.append(dict(registration_group_id=key, registration_name=parts[0]['registration_name'],
                         legal_holder_ids=sorted({h['legal_holder_id'] for h in parts}),
                         amount=canonical(numerator, denominator), shares=shares,
                         fraction_without_cash_compensation=canonical(remainder, 3 * denominator)))
    require(c['registration_entitlements'] == rows, 'Independent registration arithmetic mismatch')
    require(q['value']['actual_event'] == 'NOT_ESTABLISHED'
            and q['value']['full_settlement_supported'] is False, 'Conditional limit lost')
    return {'method': 'Scaled integers, quotient/remainder; no production grouping or Fraction arithmetic',
            'registration_entitlements': rows, 'supplied_price': 3, 'actual_partition': 'NOT_ESTABLISHED'}


def variants(before, prefix):
    rows = []
    for b in before:
        s = deepcopy(b['scenario'])
        for h in s['holdings']:
            h['registration_group_id'] = 'group-' + h['registration_name']
        rows.append((b['kind'], s))
    combined = deepcopy(rows[1][1])
    s = deepcopy(combined); s['holdings'].reverse(); rows.append(('reordered', s))
    field = 'principal' if prefix == 'seb' else 'liquidation_preference'
    s = deepcopy(combined)
    first = s['holdings'][0]; second = deepcopy(first)
    first[field], second[field], second['account_id'] = '2', '3', 'another-account'
    s['holdings'].append(second); rows.append(('within-group-split', s))
    for label, amounts in [('exact-integer', ['1.5', '1.5']),
                           ('fraction-boundary', ['2.9999', '0.0001']),
                           ('huge-exact', ['3000000000000', '0.3'])]:
        s = deepcopy(combined)
        for h, amount in zip(s['holdings'], amounts):
            h[field] = amount
        rows.append((label, s))
    s = deepcopy(combined); s['holdings'] = s['holdings'][:1]; s['holdings'][0][field] = '2.9999'
    rows.append(('below-integer', s))
    s = deepcopy(rows[0][1])
    third = deepcopy(s['holdings'][0]); third['legal_holder_id'] = 'holder-b'
    fourth = deepcopy(s['holdings'][1]); fourth.update(legal_holder_id='holder-c',
        registration_name='Registration C', registration_group_id='group-Registration C'); fourth[field] = '2'
    s['holdings'] += [third, fourth]; rows.append(('multiple-registration-groups', s))
    return rows


def primary(prefix):
    baseline = read(REVIEW / 'baseline.json')
    require(cases.financial_cases(ROOT) == baseline, 'Complete original records changed')
    prior_path = PRIOR / (prefix + '-visible-products.json.gz')
    prior = load(prior_path)
    prods = common.products(prior['P1'])
    require(prods == prior, 'Complete original products changed')
    original = service.consume(prods, ROOT)
    frozen_answer = load(PRIOR / (prefix + '-visible-answer.json.gz'))
    require(original['questions'] == frozen_answer['questions'], 'Original question set changed')
    compressed(HERE / (prefix + '-original-answer.json.gz'), original)
    write(HERE / (prefix + '-product-references.json'), {'path': str(prior_path.relative_to(ROOT)),
          'sha256': file_hash(prior_path), 'products': {k: p['sha256'] for k, p in prods.items()},
          'downstream_reconstructed_equal': True, 'mode': 'GENUINE_RETAINED_P1; FROZEN_CONSUMER'}, exclusive=True)
    before = [r for r in load(REVIEW / 'before-primary.json.gz') if r['issue'] == prefix]
    valid, adverse, known_bad = [], [], []

    def consume(s):
        p5 = service.financial_product(prods['P1'], prods['P2'], prods['P3'], scenario=s)
        answer = service.consume({**prods, 'P5': p5}, ROOT)
        require(answer['may_execute_transaction'] is False, 'Financial answer granted execution')
        for key in original['questions']:
            if key != 'Q5':
                require(answer['questions'][key] == original['questions'][key], 'Other question changed')
        return p5, answer

    candidates = variants(before, prefix)
    for label, s in candidates:
        p5, answer = consume(s)
        proof = oracle(s, answer['questions']['Q5'])
        valid.append({'case': label, 'scenario': s, 'P5': p5, 'answer': answer, 'oracle': proof})
    for label in ('reordered', 'within-group-split'):
        expected = valid[1]['oracle']['registration_entitlements']
        require(next(r for r in valid if r['case'] == label)['oracle']['registration_entitlements'] == expected,
                'Metamorphic registration total changed')
    # The retained pre-edit function must fail both substantive source cases.
    path = REVIEW / 'before' / 'src/legalmath/prospectus/closure_mechanisms.py'
    namespace = {'__name__': 'legalmath.prospectus._retained_registration', '__package__': 'legalmath.prospectus'}
    exec(compile(path.read_text(), str(path), 'exec'), namespace)
    for b in before:
        wrong = namespace['seb' if prefix == 'seb' else 'bbva'](b['scenario'])
        actual = sum(r['shares'] for r in wrong['holder_entitlements'])
        require(actual == b['wrong_total_shares'] and actual != b['source_required_total_shares'],
                'Known-bad function no longer distinguishes the defect')
        known_bad.append({'kind': b['kind'], 'retained_wrong': wrong,
                          'source_required_total_shares': b['source_required_total_shares']})
        for active in (True, False):
            s = deepcopy(b['scenario'])
            if not active:
                common.inactive(s)
            p5, answer = consume(s)
            require(answer['questions']['Q5']['status'] == 'UNSUPPORTED', 'Unsafe implicit partition accepted')
            adverse.append({'kind': b['kind'], 'active': active, 'P5': p5, 'answer': answer})
    for active in (True, False):
        for kind in ('mixed', 'blank-id', 'invalid-id', 'conflicting-name', 'split-name',
                     'blank-holder', 'blank-name', 'missing-holder', 'unknown-field'):
            s = deepcopy(candidates[0][1]); h = s['holdings'][1]
            if not active:
                common.inactive(s)
            if kind == 'mixed': h.pop('registration_group_id')
            elif kind == 'blank-id': h['registration_group_id'] = ' '
            elif kind == 'invalid-id': h['registration_group_id'] = 0
            elif kind == 'conflicting-name': h['registration_group_id'] = s['holdings'][0]['registration_group_id']
            elif kind == 'split-name': h['registration_name'] = s['holdings'][0]['registration_name']
            elif kind == 'blank-holder': h['legal_holder_id'] = ' '
            elif kind == 'blank-name': h['registration_name'] = ''
            elif kind == 'missing-holder': h.pop('legal_holder_id')
            else: h['invented_allocation'] = 'all-shares'
            p5, answer = consume(s)
            require(answer['questions']['Q5']['status'] == 'UNSUPPORTED', 'Malformed registration mapping accepted')
            adverse.append({'kind': kind, 'active': active, 'P5': p5, 'answer': answer})
    excluded = load(PRIOR / (prefix + '-excluded-products.json.gz'))
    p5 = service.financial_product(excluded['P1'], excluded['P2'], excluded['P3'], scenario=candidates[0][1])
    answer = service.consume({**excluded, 'P5': p5}, ROOT)
    require(answer['questions']['Q5']['status'] == 'UNSUPPORTED', 'Explicit groups bypassed source visibility')
    adverse.append({'kind': 'GENUINE_EXCLUDED_P1', 'P5': p5, 'answer': answer})
    p5 = valid[0]['P5']
    for kind in ('CONTENT_TAMPER', 'PARENT_TAMPER'):
        broken = deepcopy(p5)
        if kind == 'CONTENT_TAMPER': broken['payload']['question']['status'] = 'COMPLETE'
        else:
            broken = service.seal('P5', prods['P1']['payload']['request']['bundle'],
                                  {**p5['inputs'], 'P2': '0' * 64}, p5['payload'])
        try:
            service.consume({**prods, 'P5': broken}, ROOT)
        except ValueError as exc:
            require(('content changed' if kind == 'CONTENT_TAMPER' else 'parent bindings changed') in str(exc),
                    'Unexpected tamper refusal')
            adverse.append({'kind': kind, 'refusal': str(exc)})
        else:
            raise ValueError('Tamper admitted')
    retain_controls(HERE / (prefix + '-valid.json.gz'), valid, original)
    retain_controls(HERE / (prefix + '-adverse.json.gz'),
                    [r for r in adverse if 'answer' in r], original)
    write(HERE / (prefix + '-tamper-refusals.json'),
          [r for r in adverse if 'answer' not in r], exclusive=True)
    write(HERE / (prefix + '-known-bad.json'), known_bad, exclusive=True)
    return {'complete_original_secondary_equal': 3, 'complete_original_primary_equal': 1,
            'reconstructed_original_products_equal': 5, 'valid_registration_controls': len(valid),
            'primary_adverse_controls': len(adverse), 'retained_wrong_controls_detected': len(known_bad),
            'native_calls_this_stage': 0, 'whole_task_complete': False}


def seal():
    require((HERE / 'RESULT.md').is_file(), 'Retain substantive interpretation before sealing')
    return {stage: read(HERE / 'stages' / stage / 'result.json')['detail'] for stage in STAGES[:-1]}


def main():
    stage = sys.argv[1]
    require(stage in STAGES, 'Unknown stage')
    for prerequisite in STAGES[:STAGES.index(stage)]:
        require(read(HERE / 'stages' / prerequisite / 'result.json')['status'] == 'PASS', 'Prerequisite failed')
    folder = HERE / 'stages' / stage
    write(folder / 'started.json', {'command': ['.venv/bin/python', str(Path(__file__).relative_to(ROOT)), stage],
          'at': datetime.now(timezone.utc).isoformat(), 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'}, exclusive=True)
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('120s stage bound')))
    signal.alarm(120)
    try:
        admission = authenticate()
        detail = tests() if stage == 'tests' else seal() if stage == 'seal' else primary(stage)
        methods_unchanged()
        require(measured_seconds() + time.monotonic() - start < 480
                and storage() + 1024**2 < 80 * 1024**2, 'Original cumulative ceiling')
        result = {'status': 'PASS', 'seconds': time.monotonic() - start, 'detail': detail}
    except Exception as exc:
        write(folder / 'result.json', {'status': 'FAIL', 'seconds': time.monotonic() - start,
              'error': type(exc).__name__ + ': ' + str(exc)}, exclusive=True)
        raise
    write(folder / 'result.json', result, exclusive=True)
    if stage == 'seal':
        write(HERE / 'run-manifest.json', {'git_commit': admission['git_commit'], 'plan': PLAN,
              'result': str((HERE / 'RESULT.md').relative_to(ROOT)), 'python': sys.version,
              'interpreter': sys.executable, 'environment': 'Existing .venv; current worktree imports pinned',
              'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1', 'random_seeds': 'N/A; deterministic',
              'commands': [read(p) for p in sorted((HERE / 'stages').glob('*/started.json'))],
              'preparation_command': read(REVIEW / 'started.json'),
              'freeze_seconds': read(REVIEW / 'freeze.json')['seconds'],
              'sources': read(REVIEW / 'source-bindings.json'), 'freeze': str((REVIEW / 'freeze.json').relative_to(ROOT)),
              'stages': {p.parent.name: read(p) for p in (HERE / 'stages').glob('*/result.json')},
              'measured_seconds_including_all_source_campaign': measured_seconds(),
              'historical_unmeasured_seconds': 'UNKNOWN', 'native_pdf_calls_this_admission': 0,
              'source_campaign_native_pdf_calls': 6, 'source_campaign_storage_before_manifest': storage()}, exclusive=True)
        write(HERE / 'result.json', {'task': 'entitlement', 'status': 'PASS', 'scope': 'REGISTRATION_GROUP_PRIMARY_Q5',
              'whole_task_complete': False, 'whole_program_complete': False, 'summary': detail}, exclusive=True)
        write(HERE / 'outputs.json', {str(p.relative_to(HERE)): file_hash(p) for p in sorted(HERE.rglob('*'))
              if p.is_file() and p.name not in {'admission.json', 'outputs.json'} and '__pycache__' not in p.parts}, exclusive=True)
        require(storage() < 80 * 1024**2, 'Final original storage ceiling')
    signal.alarm(0)
    print(json.dumps({'stage': stage, **result}), flush=True)


if __name__ == '__main__':
    main()
