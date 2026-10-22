"""Bounded original-source and primary-Q5 validation, with immutable preparation."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path
import gzip
import json
import os
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash
from legalmath.prospectus.successor import cases, service, source_graph
from legalmath.prospectus.successor.contracts import digest

PLAN = 'docs/plans/prospectus-conversion-source-primary-2026-10-18.md'
REVIEW = ROOT / REL / 'reviews/conversion-source-primary-251'
HERE = ROOT / REL / 'attempts/entitlement/attempt-007'
TESTS = ['tests/prospectus_successor/test_conversion_admission.py',
         'tests/prospectus/test_closure_mechanisms.py',
         'tests/prospectus_successor/test_repairs.py',
         'tests/prospectus_successor/test_closure_finance.py',
         'tests/prospectus_successor/test_conversion_source_primary.py']
CHANGED = ['src/legalmath/prospectus/closure_mechanisms.py',
           'src/legalmath/prospectus/successor/financial_profiles.py']
STAGES = ('tests', 'primary', 'current', 'seal')


def require(value, reason):
    if not value:
        raise ValueError(reason)


def load(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def compressed(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(gzip.compress(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                             allow_nan=False).encode(), mtime=0))


def methods_unchanged():
    frozen = read(REVIEW / 'freeze.json')
    current = {str(p.relative_to(ROOT)) for p in (ROOT / 'src/legalmath').rglob('*')
               if p.is_file() and '__pycache__' not in p.parts}
    require(current == set(read(REVIEW / 'before-methods.json')), 'Production file set changed')
    for name, expected in frozen['methods'].items():
        require(file_hash(ROOT / name) == expected, 'Frozen method changed: ' + name)
    for name, expected in frozen['preparation'].items():
        require(file_hash(ROOT / name) == expected, 'Frozen preparation changed: ' + name)


def measured_seconds():
    return (read(REVIEW / 'preparation-result.json')['seconds']
            + sum(read(p)['seconds'] for p in (HERE / 'stages').glob('*/result.json')))


def storage():
    paths = [REVIEW, HERE, ROOT / PLAN, Path(__file__), ROOT / TESTS[-1],
             ROOT / REL / 'proposals/conversion-source-primary-251.json',
             ROOT / REL / 'proposals/conversion-source-primary-251-review.json',
             ROOT / REL / 'revisions/0251.json',
             ROOT / REL / 'closure-routes-2026-10-18-conversion-source-primary-251.json']
    files = set()
    for path in paths:
        if path.is_dir():
            files.update(p for p in path.rglob('*') if p.is_file())
        elif path.exists():
            files.add(path)
    return sum(p.stat().st_size for p in files)


def authenticate():
    auth = Authority(ROOT)
    program, tasks, _ = auth.spec()
    admission = read(HERE / 'admission.json')
    require(program['revision'] == 251 and admission['task'] == 'entitlement', 'Wrong admission')
    require(admission['binding'] == auth.binding(tasks['entitlement']), 'Admission binding changed')
    event = next(e for e in reversed(auth.events()) if e.get('task') == 'entitlement')
    require(event['kind'] == 'ADMIT' and event['attempt'] == str(HERE.relative_to(ROOT)),
            'No active source-primary admission')
    methods_unchanged()
    for name, expected in read(REVIEW / 'source-bindings.json').items():
        require(file_hash(ROOT / name) == expected, 'Original source changed: ' + name)
    require(measured_seconds() < 480 and storage() + 1024**2 < 80 * 1024**2,
            'Incremental resource ceiling')
    return admission


def tests():
    argv = [sys.executable, '-c',
            'import sys; sys.path[:0]=[sys.argv[1],sys.argv[2]]; import pytest; '
            'raise SystemExit(pytest.main(sys.argv[3:]))',
            str(ROOT / 'src'), str(ROOT), '-q', *TESTS, '--junitxml=' + str(HERE / 'tests.xml')]
    write(HERE / 'test-command.json', {'argv': argv}, exclusive=True)
    with (HERE / 'tests.stdout').open('xb') as out, (HERE / 'tests.stderr').open('xb') as err:
        completed = subprocess.run(argv, cwd=ROOT, stdout=out, stderr=err, timeout=100,
                                   env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    require(completed.returncode == 0, 'Regression failure; inspect retained test logs')
    xml = ET.parse(HERE / 'tests.xml').getroot()
    counts = {k: sum(int(s.get(k, '0')) for s in xml.iter('testsuite'))
              for k in ('tests', 'failures', 'errors', 'skipped')}
    require(counts['tests'] >= 353 and not any(counts[k] for k in ('failures', 'errors', 'skipped')),
            'Missing or failed regression controls')
    return counts


def products(p1):
    p2 = service.construction_product(p1, ROOT)
    p3 = service.interpretation_product(p1, p2)
    return {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3),
            'P5': service.financial_product(p1, p2, p3)}


def independent(s, question):
    """Source proposition in Decimal; allocation by exact integer division."""
    require(question['status'] == 'CONDITIONAL', 'Valid source control refused')
    q = question['value']['calculation']
    if s['issue_id'].startswith('seb'):
        trigger = Decimal(s['bank_cet1_ratio']) < Decimal('0.05125') or Decimal(s['group_cet1_ratio']) < Decimal('0.08')
        require(q.get('conversion') is trigger, 'Source-specific SEB predicate mismatch')
        pricekey, amount = 'conversion_price_usd', 'principal'
        rate = Decimal(s['usd_per_sek'])
        candidates = [Decimal(s['adjusted_floor_usd']), Decimal(s['quota_value_sek']) * rate]
        if s['listed']:
            candidates.append(Decimal(s['reviewed_current_market_price_sek']) * rate)
        if not trigger:
            require(q['principal_after_conversion'] is None, 'No-trigger principal falsely settled')
            return {'conversion': False, 'allocation': 'NOT_APPLICABLE'}
        require(q['principal_after_conversion'] == '0' and q['economic_recovery'] is None,
                'Converted principal confused with economic recovery')
    else:
        trigger = Decimal(s['issuer_determined_cet1_ratio']) < Decimal('0.05125')
        if trigger:
            path = 'MANDATORY_6_1'
        elif s['capital_reduction'] and s['condition_7_7_redemption_override']:
            path = 'REDEMPTION_7_7'
        elif s['capital_reduction'] and s.get('valid_timely_opt_out') is None:
            require(q == {'status': 'MISSING_ELECTION_EVIDENCE', 'conversion': None},
                    'Unknown election incorrectly selected a branch')
            return {'conversion': None, 'reason': 'UNKNOWN_ELECTION'}
        elif s['capital_reduction']:
            path = 'OPTED_OUT_6_2' if s['valid_timely_opt_out'] else 'CONVERSION_6_2'
        else:
            path = 'NO_CONVERSION_EVENT_UNDER_PREMISES'
        converts = path in {'MANDATORY_6_1', 'CONVERSION_6_2'}
        require(q['path'] == path and q['conversion'] is converts, 'BBVA source branch mismatch')
        if not converts:
            return {'conversion': False, 'path': path, 'allocation': 'NOT_APPLICABLE'}
        pricekey, amount = 'conversion_price', 'liquidation_preference'
        candidates = [Decimal(s['adjusted_floor_price']), Decimal(s['nominal_share_value'])]
        if s['listed']:
            mean = sum(Decimal(v) for v in s['five_eligible_closing_prices']) / Decimal(5)
            candidates.append(mean.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    price = Fraction(max(candidates))
    require(Fraction(q[pricekey]) == price, 'Independent source price mismatch')
    # This campaign is limited to identical holder/name partitions. It does not
    # bless arbitrary legal-holder grouping across different registered names.
    holders, names, groups = {}, {}, {}
    for row in s['holdings']:
        holder, name = row['legal_holder_id'], row['registration_name']
        require(holders.setdefault(holder, name) == name and names.setdefault(name, holder) == holder,
                'Control exceeds reviewed matched holder/name scope')
        groups[holder] = groups.get(holder, Fraction()) + Fraction(row[amount])
    expected = []
    for holder, total in sorted(groups.items()):
        shares = total.numerator * price.denominator // (total.denominator * price.numerator)
        expected.append({'legal_holder_id': holder, 'registration_names': [holders[holder]],
                         'amount': str(total), 'shares': shares,
                         'fraction_without_cash_compensation': str(total / price - shares)})
    require(q['holder_entitlements'] == expected, 'Independent integer allocation mismatch')
    require(question['value']['full_settlement_supported'] is False
            and question['value']['actual_event'] == 'NOT_ESTABLISHED', 'Conditional limits lost')
    return {'conversion': True, 'price': str(price), 'entitlements': expected,
            'method': 'Independent Decimal source proposition and integer/rational allocation'}


def variants(original):
    rows = [('original', deepcopy(original))]
    if original['issue_id'].startswith('seb'):
        for bank, group in [('0.1', '0.06'), ('0.05125', '0.08'),
                            ('0.05124999', '0.1'), ('0.05125', '0.1'), ('0.05125001', '0.1'),
                            ('0.1', '0.07999999'), ('0.1', '0.08'), ('0.1', '0.08000001'),
                            ('0.05', '0.079'), ('0.1', '0.05'), ('0.1', '0.1')]:
            s = deepcopy(original)
            s.update(bank_cet1_ratio=bank, group_cet1_ratio=group)
            rows.append(('threshold-bank-' + bank + '-group-' + group, s))
        for label, edits in [('floor', {'adjusted_floor_usd': '5'}),
                             ('quota', {'quota_value_sek': '100'}),
                             ('unlisted', {'listed': False})]:
            s = deepcopy(original)
            s.update(edits)
            if not s['listed']:
                del s['reviewed_current_market_price_sek']
            rows.append((label, s))
    else:
        branch_edits = [
            ('exact-trigger', {'issuer_determined_cet1_ratio': '0.05125', 'capital_reduction': False}),
            ('below-trigger-overrides-optout', {'issuer_determined_cet1_ratio': '0.05124999'}),
            ('redemption', {'issuer_determined_cet1_ratio': '0.1', 'condition_7_7_redemption_override': True}),
            ('opted-out', {'issuer_determined_cet1_ratio': '0.1', 'valid_timely_opt_out': True}),
            ('capital-conversion', {'issuer_determined_cet1_ratio': '0.1', 'valid_timely_opt_out': False}),
            ('unknown-election', {'issuer_determined_cet1_ratio': '0.1', 'valid_timely_opt_out': None}),
            ('half-cent-below', {'five_eligible_closing_prices': ['5.004999'] * 5}),
            ('half-cent-exact', {'five_eligible_closing_prices': ['5.005'] * 5}),
            ('floor', {'adjusted_floor_price': '7'}),
            ('nominal', {'nominal_share_value': '8'}),
            ('unlisted', {'listed': False, 'five_eligible_closing_prices': []})]
        for label, edits in branch_edits:
            s = deepcopy(original)
            s.update(edits)
            rows.append((label, s))
    s = deepcopy(original)
    s['holdings'][1].update(legal_holder_id='synthetic-holder-b', registration_name='Synthetic B')
    rows.append(('separate-matched-registration', s))
    return rows


def inactive(s):
    if s['issue_id'].startswith('seb'):
        s.update(bank_cet1_ratio='0.1', group_cet1_ratio='0.1')
    else:
        s.update(issuer_determined_cet1_ratio='0.1', capital_reduction=False)


def old_module(name, package):
    path = REVIEW / 'before' / name
    namespace = {'__name__': package + '._retained_before', '__package__': package}
    exec(compile(path.read_text(), str(path), 'exec'), namespace)
    return namespace


def primary():
    baseline = read(REVIEW / 'baseline.json')
    require(cases.financial_cases(ROOT) == baseline, 'Complete original secondary cases changed')
    write(HERE / 'original-valid.json', baseline, exclusive=True)
    valid, malformed, known_bad, originals = [], [], [], []
    for prefix in ('bbva', 'seb'):
        label = prefix + '-visible'
        p1 = load(REVIEW / (label + '-P1.json.gz'))
        prods = products(p1)
        answer = service.consume(prods, ROOT)
        before = load(REVIEW / (label + '-before-answer.json.gz'))
        expected = next(c['question'] for c in baseline if c['instrument_id'].startswith(prefix))
        require(answer['questions'] == before['questions'] and answer['questions']['Q5'] == expected,
                'Original complete primary questions changed')
        require(answer['may_execute_transaction'] is False, 'Calculation granted transaction permission')
        compressed(HERE / (label + '-products.json.gz'), prods)
        compressed(HERE / (label + '-answer.json.gz'), answer)
        original = expected['value']['inputs']
        for variant, s in variants(original):
            p5 = service.financial_product(p1, prods['P2'], prods['P3'], scenario=s)
            result = service.consume({**prods, 'P5': p5}, ROOT)
            for key in answer['questions']:
                if key != 'Q5':
                    require(result['questions'][key] == answer['questions'][key], 'Variant altered another question')
            oracle = independent(s, result['questions']['Q5'])
            valid.append({'source_reuse': 'GENUINE_FROZEN_P1; explicit P5 scenario override',
                          'P1': p1['sha256'], 'variant': variant, 'scenario': s,
                          'P5': p5, 'answer': result, 'oracle': oracle})
        field = 'adjusted_floor_usd' if prefix == 'seb' else 'adjusted_floor_price'
        for active in (True, False):
            for kind in ('zero-price', 'zero-denominator', 'blank-holder', 'blank-registration'):
                s = deepcopy(original)
                if not active:
                    inactive(s)
                if kind in {'zero-price', 'zero-denominator'}:
                    s[field] = '0' if kind == 'zero-price' else '1/0'
                else:
                    s['holdings'][0]['legal_holder_id' if kind == 'blank-holder' else 'registration_name'] = ' '
                p5 = service.financial_product(p1, prods['P2'], prods['P3'], scenario=s)
                result = service.consume({**prods, 'P5': p5}, ROOT)
                require(result['questions']['Q5']['status'] == 'UNSUPPORTED', 'Malformed primary scenario accepted')
                malformed.append({'P1': p1['sha256'], 'active': active, 'kind': kind,
                                  'P5': p5, 'answer': result})
        excluded = load(REVIEW / (prefix + '-excluded-P1.json.gz'))
        graph = excluded['payload']['graph']
        require(not any(d['visible'] for d in graph['documents'])
                and not any(u['visible'] for u in graph['units']), 'Exclusion not genuine')
        excluded_prods = products(excluded)
        refused = service.consume(excluded_prods, ROOT)
        prior = load(REVIEW / (prefix + '-excluded-before-answer.json.gz'))
        require(prior['questions']['Q5']['status'] == 'CONDITIONAL'
                and refused['questions']['Q5']['status'] == 'UNSUPPORTED', 'Visibility repair did not discriminate')
        for key in prior['questions']:
            if key != 'Q5':
                require(refused['questions'][key] == prior['questions'][key], 'Source refusal changed unrelated questions')
        require(graph['unresolved'] == excluded_prods['P1']['payload']['graph']['unresolved'], 'Date uncertainty lost')
        compressed(HERE / (prefix + '-excluded-products.json.gz'), excluded_prods)
        compressed(HERE / (prefix + '-excluded-answer.json.gz'), refused)
        old_assess = old_module(CHANGED[1], 'legalmath.prospectus.successor')['assess']
        old_question = old_assess(excluded['payload']['request']['bundle'], original, graph)
        require(old_question['status'] == 'CONDITIONAL', 'Pre-edit visibility control no longer reproduces')
        known_bad.append({'issue': original['issue_id'], 'defect': 'SOURCE_VISIBILITY',
                          'old': old_question, 'repaired': refused['questions']['Q5']})
        originals.append({'issue': original['issue_id'], 'visible_q5_equal': True,
                          'excluded_q5': refused['questions']['Q5'],
                          'source_unresolved': graph['unresolved'],
                          'original_before_report_sha256': before['report_sha256']})
        # Actual consumer refusals; original source files are never modified.
        tampered = deepcopy(prods['P5'])
        tampered['payload']['question']['status'] = 'COMPLETE'
        try:
            service.consume({**prods, 'P5': tampered}, ROOT)
        except ValueError as exc:
            require('content changed' in str(exc), 'Unexpected content-tamper error')
            malformed.append({'issue': prefix, 'kind': 'CONTENT_TAMPER', 'refusal': str(exc)})
        else:
            raise ValueError('Unsealed content tamper admitted')
        wrong_parent = service.seal('P5', p1['payload']['request']['bundle'],
                                   {**prods['P5']['inputs'], 'P2': '0' * 64}, prods['P5']['payload'])
        try:
            service.consume({**prods, 'P5': wrong_parent}, ROOT)
        except ValueError as exc:
            require('parent bindings changed' in str(exc), 'Unexpected parent-tamper error')
            malformed.append({'issue': prefix, 'kind': 'PARENT_TAMPER', 'refusal': str(exc)})
        else:
            raise ValueError('Wrong phase parent admitted')
        payload = deepcopy(p1['payload'])
        payload['request']['bundle']['documents'][0]['sha256'] = '0' * 64
        payload['graph']['bundle_sha256'] = digest(payload['request']['bundle'])
        wrong_source = service.seal('P1', payload['request']['bundle'],
                                    {'request': digest(payload['request'])}, payload)
        try:
            service.construction_product(wrong_source, ROOT)
        except ValueError as exc:
            require('Source bytes changed' in str(exc), 'Unexpected source-tamper error')
            malformed.append({'issue': prefix, 'kind': 'SOURCE_HASH_TAMPER', 'refusal': str(exc)})
        else:
            raise ValueError('Source hash tamper admitted')
        print(json.dumps({'primary': prefix, 'visible_q5': 'UNCHANGED', 'excluded_q5': 'UNSUPPORTED'}), flush=True)
    old_seb = old_module(CHANGED[0], 'legalmath.prospectus')['seb']
    s = deepcopy(next(c['question']['value']['inputs'] for c in baseline if c['instrument_id'].startswith('seb')))
    s.update(bank_cet1_ratio='0.1', group_cet1_ratio='0.06')
    observed = old_seb(s)
    require(observed['conversion'] is False
            and (Decimal(s['group_cet1_ratio']) < Decimal('0.08')), 'Known-bad threshold not detected')
    known_bad.append({'defect': 'SEB_GROUP_THRESHOLD', 'scenario': s, 'old': observed,
                      'source_required_conversion': True})
    compressed(HERE / 'valid-controls.json.gz', valid)
    compressed(HERE / 'adverse-controls.json.gz', malformed)
    write(HERE / 'known-bad-controls.json', known_bad, exclusive=True)
    write(HERE / 'original-primary-comparisons.json', originals, exclusive=True)
    return {'original_complete_secondary_equal': len(baseline), 'original_primary_equal': 2,
            'genuine_primary_exclusions_repaired': 2, 'valid_frozen_primary_controls': len(valid),
            'primary_adverse_controls': len(malformed), 'known_bad_controls_detected': len(known_bad),
            'whole_task_complete': False}


def current():
    calls, original_pdf_units = [], source_graph.pdf_units
    preparation_calls = read(REVIEW / 'native-calls.json')
    require(len(preparation_calls) == 4, 'Wrong preparation native-call account')

    def counted(path, document):
        require(len(calls) + len(preparation_calls) < 6, 'Six-call native ceiling')
        row = {'sequence': len(calls) + 5, 'document': document['id'],
               'source_sha256': document['sha256'],
               'argv': ['pdftotext', '-bbox-layout', '-enc', 'UTF-8', str(path), '-'], 'state': 'STARTED'}
        calls.append(row)
        write(HERE / 'native-calls.json', calls)
        start = time.monotonic()
        value = original_pdf_units(path, document)
        row.update(state='COMPLETE', seconds=time.monotonic() - start,
                   page_count=value[1], extraction=value[2])
        write(HERE / 'native-calls.json', calls)
        return value

    source_graph.pdf_units = counted
    try:
        for prefix in ('bbva', 'seb'):
            prods = load(HERE / (prefix + '-visible-products.json.gz'))
            frozen = load(HERE / (prefix + '-visible-answer.json.gz'))
            answer = service.consume(prods, ROOT, mode='current')
            require(answer['questions'] == frozen['questions']
                    and answer['source_graph_sha256'] == frozen['source_graph_sha256']
                    and answer['consumed_products'] == frozen['consumed_products'],
                    'Fresh current consumer differs from frozen primary')
            compressed(HERE / (prefix + '-current-answer.json.gz'), answer)
            print(json.dumps({'current': prefix, 'question_equality': True}), flush=True)
    finally:
        source_graph.pdf_units = original_pdf_units
    require(len(calls) == 2 and all(r['state'] == 'COMPLETE' for r in calls), 'Incomplete current extraction')
    return {'current_consumers': 2, 'native_calls_this_stage': 2, 'native_calls_including_preparation': 6,
            'fresh_graphs_and_primary_questions_equal': True}


def seal():
    for stage in STAGES[:-1]:
        require(read(HERE / 'stages' / stage / 'result.json')['status'] == 'PASS', 'Missing required stage')
    require((HERE / 'RESULT.md').is_file(), 'Detailed interpretation required before sealing')
    return {stage: read(HERE / 'stages' / stage / 'result.json')['detail'] for stage in STAGES[:-1]}


def main():
    stage = sys.argv[1]
    require(stage in STAGES, 'Unknown validation stage')
    for prerequisite in STAGES[:STAGES.index(stage)]:
        require(read(HERE / 'stages' / prerequisite / 'result.json')['status'] == 'PASS', 'Stage dependency failed')
    folder = HERE / 'stages' / stage
    write(folder / 'started.json', {'command': ['.venv/bin/python', str(Path(__file__).relative_to(ROOT)), stage],
          'at': datetime.now(timezone.utc).isoformat(), 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'}, exclusive=True)
    start = time.monotonic()

    def expired(signum, frame):
        raise TimeoutError('Reviewed 120-second stage bound reached')

    signal.signal(signal.SIGALRM, expired)
    signal.alarm(120)
    try:
        admission = authenticate()
        detail = globals()[stage]()
        methods_unchanged()
        require(measured_seconds() + time.monotonic() - start < 480
                and storage() + 1024**2 < 80 * 1024**2, 'Incremental resource ceiling')
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
              'sources': read(REVIEW / 'source-bindings.json'), 'freeze': str((REVIEW / 'freeze.json').relative_to(ROOT)),
              'commands': [read(p) for p in sorted((HERE / 'stages').glob('*/started.json'))],
              'stages': {p.parent.name: read(p) for p in (HERE / 'stages').glob('*/result.json')},
              'measured_seconds_including_preparation': measured_seconds(),
              'historical_unmeasured_seconds': 'UNKNOWN', 'native_pdf_calls': 6,
              'incremental_bytes_before_manifest': storage()}, exclusive=True)
        write(HERE / 'result.json', {'task': 'entitlement', 'status': 'PASS',
              'scope': 'ORIGINAL_CONVERSION_SOURCE_AND_PRIMARY_Q5',
              'whole_task_complete': False, 'whole_program_complete': False, 'summary': detail}, exclusive=True)
        write(HERE / 'outputs.json', {str(p.relative_to(HERE)): file_hash(p) for p in sorted(HERE.rglob('*'))
              if p.is_file() and p.name not in {'admission.json', 'outputs.json'} and '__pycache__' not in p.parts},
              exclusive=True)
        require(storage() < 80 * 1024**2, 'Final storage ceiling')
    signal.alarm(0)
    print(json.dumps({'stage': stage, **result}), flush=True)


if __name__ == '__main__':
    main()
