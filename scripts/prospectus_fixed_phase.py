"""Bounded retained-source controls for the optional Danske fixed-phase path."""
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
from hashlib import sha256
import difflib
import gzip
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.successor import service, contract_terms, contract_assembly, occurrences
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.execution_authority import Authority, REL, file_hash, read, write
from legalmath.prospectus.execution_authority import digest as authority_digest
from scripts import prospectus_fixed_phase_oracle as oracle

PLAN = 'docs/plans/prospectus-fixed-phase-2026-10-18.md'
REVIEW = ROOT / REL / 'reviews/fixed-phase-256'
OLD = ROOT / REL / 'attempts/finance-conventions/attempt-003'
HERE = ROOT / REL / 'attempts/finance-conventions/attempt-008'
FINAL = 'danske-dkk-at1-2026-final'
BASE = 'danske-at1-2026-base'
DUE = ['2026-11-25', '2027-11-25', '2028-11-25', '2029-11-25', '2030-11-25', '2031-11-25']
PAY = ['2026-11-25', '2027-11-25', '2028-11-27', '2029-11-26', '2030-11-25', '2031-11-25']
TESTS = ['tests/prospectus/test_build_contract.py',
         'tests/prospectus_successor/test_fixed_phase.py',
         'tests/prospectus_successor/test_bond_basis.py',
         'tests/prospectus_successor/test_initial_coupon.py',
         'tests/prospectus_successor/test_closure_coupon_anchor.py',
         'tests/prospectus_successor/test_closure_finance.py',
         'tests/prospectus_successor/test_closure_consumers.py']
BOUNDS = dict(preparation_seconds=180, regressions_seconds=180, consumers_seconds=180,
              validation_seconds=180, incremental_seconds=720, new_bytes=64 * 1024**2,
              reserve_bytes=1024**2, network_install_native_OCR_model_GPU_subagents=0)


def save(path, value):
    raw = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(gzip.compress(raw, mtime=0) if path.name.endswith('.gz') else raw)


def load(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.name.endswith('.gz') else raw)


def products(name, request, folder):
    result = {'P1': service.source_product(request, ROOT)}
    save(folder / (name + '-P1.json.gz'), result['P1'])
    result['P2'] = service.construction_product(result['P1'], ROOT)
    save(folder / (name + '-P2.json.gz'), result['P2'])
    result['P3'] = service.interpretation_product(result['P1'], result['P2'])
    save(folder / (name + '-P3.json.gz'), result['P3'])
    result['P4'] = service.law_product(result['P1'], result['P3'])
    save(folder / (name + '-P4.json.gz'), result['P4'])
    result['P5'] = service.financial_product(result['P1'], result['P2'], result['P3'])
    save(folder / (name + '-P5.json.gz'), result['P5'])
    answer = service.consume(result, ROOT)
    save(folder / (name + '-answer.json.gz'), answer)
    assert answer['consumed_products'] == {k: p['sha256'] for k, p in result.items()}
    assert not answer['may_execute_transaction'] and not answer['independent_legal_acceptance']
    return result, answer


def build_request():
    request = deepcopy(read(OLD / 'source-request.json'))
    document = next(d for d in request['bundle']['documents'] if d['id'] == 'hypotheses')
    document.update(path=str((REVIEW / 'hypotheses.txt').relative_to(ROOT)),
                    sha256=file_hash(REVIEW / 'hypotheses.txt'),
                    authority='Explicit all-phase hypotheses; not actual events, calendar or entitlement')
    p1 = service.source_product(request, ROOT)
    graph = p1['payload']['graph']
    selected = {FINAL: {3, 4, 6}, BASE: {55, 56, 57, 66, 71, 72, 92, 93, 109, 110, 127}, 'hypotheses': {1}}
    request['assembly'] = {'operations': [
        {'unit': u['id'], 'role': 'OPERATIVE', 'source_text_sha256': u['text_sha256'],
         'context': u['parent'], 'reason': 'Conditional fixed-phase source reading; remaining pages unresolved'}
        for u in graph['units'] if u['page'] in selected.get(u['document'], set())]}
    assembly = contract_assembly.assemble(graph, request['assembly'])
    assert assembly['status'] == 'PARTIAL' and assembly['unresolved']

    def cite(document, page, pattern=None):
        unit = next(u for u in graph['units'] if u['document'] == document and u['page'] == page)
        if pattern is None:
            return occurrences.anchor(unit, 0)
        match = re.search(pattern, unit['raw'])
        assert match, (document, page, pattern)
        return occurrences.anchor(unit, match.start(), match.end())

    premise = {'source': cite('hypotheses', 1), 'reason': 'Explicit numerical hypothesis only; actual facts unresolved'}
    values = dict(currency='DKK', annual_rate='0.051', day_count='THIRTY_360_BOND_BASIS',
                  frequency=1, eom=False, adjustment='FOLLOWING',
                  rounding={'quantum': '1', 'rule': 'HALF_UP', 'aggregation': 'PER_LEGAL_HOLDER'},
                  issue_principal='1250000000', accrual_start='2026-08-25', accrual_end=DUE[0],
                  due_date=DUE[0], coupon_anchor=DUE[0], fixed_phase_end=DUE[-1],
                  fixed_phase_boundary='FIRST_RESET_DATE', note_form='VP_SYSTEMS', references=[], stub='SHORT_FIRST')
    sources = {'currency': cite(FINAL, 3, 'DKK'), 'annual_rate': cite(FINAL, 4, r'5\.100 per cent\.'),
               'frequency': cite(FINAL, 4, 'in each year'), 'day_count': cite(BASE, 71),
               'issue_principal': cite(FINAL, 3, r'DKK 1,250,000,000'),
               'accrual_start': cite(FINAL, 4, r'25\s+August\s+2026'),
               'accrual_end': cite(FINAL, 4, r'25\s+November\s+2026'),
               'due_date': cite(FINAL, 4, r'25\s+November\s+2026'),
               'coupon_anchor': cite(FINAL, 4, r'25\s+November\s+2026'),
               'fixed_phase_end': cite(FINAL, 4, r'25\s+November\s+2031'),
               'fixed_phase_boundary': cite(FINAL, 4), 'note_form': cite(FINAL, 6, 'VP Systems Notes'),
               'adjustment': cite(BASE, 127), 'stub': cite(FINAL, 4, 'short first coupon')}
    terms = {k: {'value': v, 'source': deepcopy(sources.get(k, premise['source'])),
                 'use': sources.get(k, premise['source'])['unit'],
                 'reason': ('Conditional source reading; no definitive-form printed amount used' if k in sources else premise['reason']),
                 'rule': {'currency': 'literal', 'annual_rate': 'percent', 'frequency': 'annual',
                          'issue_principal': 'amount', **{d: 'english-date' for d in
                           ('accrual_start', 'accrual_end', 'due_date', 'coupon_anchor', 'fixed_phase_end')}}.get(k, 'reviewed-convention')}
             for k, v in values.items()}
    packet = {'version': 'selected-coupon-terms.v5', 'assembly_sha256': digest(assembly),
              'review': {'reviewer': 'executor', 'kind': 'DEVELOPMENT',
                         'reason': 'Original retained terms plus explicit hypothetical calendar, rounding and events'}, 'terms': terms}
    common = {'profile': 'fixed-phase.v1', 'issue_id': FINAL, 'source_sha256': request['bundle']['documents'][0]['sha256'],
              'premise_kind': 'HYPOTHETICAL',
              'calendar': {'edition': 'HYPOTHETICAL Sat/Sun only; not verified VP/Copenhagen',
                           'valid_from': '2026-08-25', 'valid_until': '2032-01-01',
                           'holidays': [], 'weekend': [5, 6], 'coverage': 'COMPLETE_DECLARED_INTERVAL'},
              'holdings': [{'legal_holder_id': 'hypothetical-recipient', 'account_id': 'hypothetical-account',
                            'principal': '1000000', 'entitled': True}],
              'event_scope': {k: 'REQUIRED' if k in {'accrual_start', 'accrual_end', 'determination', 'payment'} else 'NOT_APPLICABLE'
                              for k in ('accrual_start', 'accrual_end', 'notice', 'observation', 'determination', 'record', 'ex_coupon', 'payment')},
              'phase_assumptions': {k: True for k in ('no_call', 'no_cancellation', 'no_conversion', 'no_principal_reduction', 'no_tax')}}
    common['evidence'] = {k: deepcopy(premise) for k in ('calendar', 'holdings', 'event_scope', 'phase_assumptions')}
    periods = []
    for i, (start, end, pay) in enumerate(zip(['2026-08-25', *DUE[:-1]], DUE, PAY)):
        events = [{'id': f'period-{i}-{kind}', 'kind': kind, 'at': day + 'T00:00:00Z', 'order': order}
                  for kind, day, order in [('accrual_start', start, 0), ('accrual_end', end, 0),
                                            ('determination', end, 1), ('payment', pay, 2)]]
        periods.append({'payment_date': pay, 'events': events,
                        'evidence': {k: deepcopy(premise) for k in ('payment_date', 'events')}})
    phase = {**deepcopy(request), 'term_interpretations': packet,
             'contract_calculation': {'version': 'selected-fixed-phase-calculation.v1', 'terms_sha256': '0' * 64,
                                      'premises': common, 'periods': periods}}
    legacy = deepcopy(request)
    legacy_packet = deepcopy(packet)
    legacy_packet.update(version='selected-coupon-terms.v1', terms={k: terms[k] for k in contract_terms.REQUIRED})
    admitted = contract_terms.admit(graph, assembly, legacy_packet)
    scenario = {k: deepcopy(v) for k, v in common.items() if k not in {'phase_assumptions'}}
    scenario['profile'] = 'fixed-coupon.v1'
    scenario['evidence'].pop('phase_assumptions')
    for k in ('accrual_start', 'accrual_end', 'due_date', 'stub', 'references'):
        scenario[k] = values[k]
        scenario['evidence'][k] = {'source': deepcopy(terms[k]['source']), 'reason': terms[k]['reason']}
    scenario.update(payment_date=periods[0]['payment_date'], events=periods[0]['events'])
    scenario['evidence'].update(deepcopy(periods[0]['evidence']))
    legacy.update(term_interpretations=legacy_packet,
                  contract_calculation={'version': 'selected-coupon-calculation.v1',
                                        'terms_sha256': digest(admitted), 'premises': scenario})
    return phase, legacy, graph, assembly


def prepare():
    REVIEW.mkdir(parents=True, exist_ok=True)
    methods = [*sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.py')),
               ROOT / 'src/legalmath/prospectus/build_contract.py', ROOT / 'src/legalmath/prospectus/semantics.py',
               ROOT / 'src/legalmath/prospectus/execution_authority.py']
    inventory = {}
    for path in methods:
        name = str(path.relative_to(ROOT))
        target = REVIEW / 'pre-edit' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(path.read_bytes())
        inventory[name] = file_hash(path)
    save(REVIEW / 'pre-edit-methods.json', inventory)
    text = ('HYPOTHETICAL FULL FIXED PHASE ONLY. Actual principal, entitlement and payment are unknown.\n'
            'For calculation only, an entitled recipient holds unchanged DKK1,000,000 throughout all six periods.\n'
            'No call, cancellation, conversion, principal reduction or tax affects any period, including the call window before the last fixed coupon.\n'
            'A hypothetical calendar has Saturday/Sunday weekends, no holidays, coverage25 August2026 to1 January2032; FOLLOWING delays payment without extra interest. It is not a verified VP/Copenhagen calendar.\n'
            'The anchor is25 November2026, annually through25 November2031; EOM is explicitly false; references are empty. Accrual ends exclusively at each due date.\n'
            'Each period has separate start, end, determination and payment events in that order; other event kinds are outside this conditional slice.\n'
            'Rounding hypothesis: quantum1 DKK, HALF_UP, PER_LEGAL_HOLDER; actual VP rounding law is unresolved.\n'
            'The first reset is not maturity. This note is perpetual. Floating coupons and redemption are unmodelled.\n')
    with (REVIEW / 'hypotheses.txt').open('x') as stream:
        stream.write(text)
    bindings = read(OLD / 'source-bindings.json')
    for name, expected in bindings.items():
        assert file_hash(ROOT / name) == expected
    save(REVIEW / 'source-bindings.json', {**bindings, str((REVIEW / 'hypotheses.txt').relative_to(ROOT)): file_hash(REVIEW / 'hypotheses.txt')})
    save(REVIEW / 'source-provenance.json', read(OLD / 'source-provenance.json'))
    phase, legacy, graph, assembly = build_request()
    save(REVIEW / 'phase-request-before.json', phase)
    save(REVIEW / 'legacy-request.json', legacy)
    p1 = service.source_product(phase, ROOT)
    p2 = service.construction_product(p1, ROOT)
    save(REVIEW / 'unsupported-P1.json.gz', p1)
    save(REVIEW / 'unsupported-P2.json.gz', p2)
    try:
        service.interpretation_product(p1, p2)
    except ValueError as exc:
        assert str(exc) == 'Contract term assembly changed', str(exc)
        save(REVIEW / 'unsupported.json', {'phase': 'P3', 'error': str(exc), 'classification': 'LOCAL_UNIMPLEMENTED_FIXED_PHASE'})
    else:
        raise AssertionError('Pre-edit method unexpectedly accepts fixed-phase interface')
    _, answer = products('legacy', legacy, REVIEW)
    assert answer['questions']['Q5']['value']['calculation']['transfers'][0]['amount'] == '12750'
    save(REVIEW / 'source-review.json', {'original_sources': read(OLD / 'source-provenance.json'),
        'selected_form': 'VP_SYSTEMS', 'boundary': 'FIRST_RESET_DATE_EXCLUSIVE_ACCRUAL',
        'independent_expected_due_dates': DUE, 'hypothetical_payment_dates': PAY,
        'printed_definitive_amounts_used_as_inputs': False, 'new_extraction': False,
        'old003_hypotheses_changed': False, 'external_opinion_required': False,
        'source_readings': ['Supplement3: issue principal', 'Supplement4: dates, rate and annual short-first coupon',
                            'Supplement6 item21: VP form; optional call window', 'Base71(v): BondBasis numerator',
                            'Base127 Conditions15.3-15.4: next payment day, no additional interest']})
    return {'unsupported_phase': 'P3', 'legacy_first_coupon': '12750', 'units': len(graph['units'])}


def phase_request():
    phase, _, graph, assembly = build_request()
    phase['contract_calculation']['terms_sha256'] = digest(contract_terms.admit(graph, assembly, phase['term_interpretations']))
    before = load(REVIEW / 'phase-request-before.json')
    expected = deepcopy(before)
    expected['contract_calculation']['terms_sha256'] = phase['contract_calculation']['terms_sha256']
    assert phase == expected, 'Preparation source/hypothesis/request identity changed'
    return phase


def method_names():
    return sorted({str(p.relative_to(ROOT)) for p in (ROOT / 'src/legalmath/prospectus/successor').glob('*.py')} |
                  set(TESTS) | {PLAN, 'scripts/prospectus_fixed_phase.py', 'scripts/prospectus_fixed_phase_oracle.py',
                  'src/legalmath/prospectus/build_contract.py', 'src/legalmath/prospectus/semantics.py',
                  'src/legalmath/prospectus/execution_authority.py', 'src/legalmath/prospectus/execution_workers.py',
                  'src/legalmath/prospectus/execution_acceptance.py', 'scripts/prospectus_control.py'})


def frozen():
    inventory = load(REVIEW / 'freeze.json')['methods']
    assert set(inventory) == set(method_names())
    for name, expected in {**inventory, **load(REVIEW / 'source-bindings.json')}.items():
        assert file_hash(ROOT / name) == expected, 'Frozen method/source drift: ' + name
    return inventory


def admitted():
    frozen()
    admission = read(HERE / 'admission.json')
    auth = Authority(ROOT)
    program, tasks, _ = auth.spec()
    task = tasks['finance-conventions']
    assert admission['task'] == task['id'] and admission['program_sha256'] == authority_digest(program)
    assert admission['binding'] == auth.binding(task) and admission['task_sha256'] == authority_digest(task)
    assert task['build_criteria_scope'] == [] and program['revision'] == 256


def run_tests(folder, names):
    command = [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
               '--junitxml=' + str(folder / 'tests.xml'), *names]
    save(folder / 'test-command.json', {'argv': command, 'cwd': str(ROOT), 'tests': names})
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src') + os.pathsep + str(ROOT), PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='-1')
    with (folder / 'tests.stdout').open('xb') as stream:
        completed = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=160)
    suites = ET.parse(folder / 'tests.xml').getroot()
    counts = {k: sum(int(s.get(k, '0')) for s in suites.iter('testsuite'))
              for k in ('tests', 'failures', 'errors', 'skipped')}
    assert completed.returncode == 0 and counts['tests'] > 0 and not any(counts[k] for k in ('failures', 'errors', 'skipped')), counts
    return counts


def preflight():
    oracle.source_check(OLD)
    for name in method_names():
        if name.endswith('.py'):
            compile((ROOT / name).read_text(), name, 'exec')
    return run_tests(REVIEW, TESTS[:2])


def evaluate(request):
    p1 = service.source_product(request, ROOT)
    p2 = service.construction_product(p1, ROOT)
    p3 = service.interpretation_product(p1, p2)
    p4 = service.law_product(p1, p3)
    p5 = service.financial_product(p1, p2, p3)
    return service.consume(dict(P1=p1, P2=p2, P3=p3, P4=p4, P5=p5), ROOT)


def questions_preserved(answer, baseline):
    for question in ('Q1', 'Q2', 'Q3', 'Q4', 'Q6'):
        assert answer['questions'][question] == baseline['questions'][question], question
    assert answer['may_execute_transaction'] is False and answer['independent_legal_acceptance'] is False


def direct_request(phase, index):
    """Hand-listed period dates, never the candidate schedule or candidate result."""
    result = deepcopy(phase)
    result.pop('term_interpretations')
    result.pop('contract_calculation')
    terms = phase['term_interpretations']['terms']
    common = phase['contract_calculation']['premises']
    scenario = {k: deepcopy(common[k]) for k in ('issue_id', 'source_sha256', 'premise_kind', 'calendar', 'holdings', 'event_scope')}
    scenario.update(profile='fixed-coupon.v1', accrual_start=['2026-08-25', *DUE[:-1]][index],
                    accrual_end=DUE[index], due_date=DUE[index], stub='SHORT_FIRST' if index == 0 else 'REGULAR')
    period = phase['contract_calculation']['periods'][index]
    scenario.update(payment_date=period['payment_date'], events=deepcopy(period['events']))
    scenario['evidence'] = {k: deepcopy(common['evidence'][k]) for k in ('calendar', 'holdings', 'event_scope')}
    scenario['evidence'].update(deepcopy(period['evidence']))
    for key in contract_terms.REQUIRED | {'references'}:
        scenario[key] = deepcopy(terms[key]['value'])
        scenario['evidence'][key] = {k: deepcopy(terms[key][k]) for k in ('source', 'reason')}
    for key in ('accrual_start', 'accrual_end', 'due_date', 'stub'):
        source = terms[key] if index == 0 else terms['coupon_anchor']
        scenario['evidence'][key] = {'source': deepcopy(source['source']),
                                   'reason': source['reason'] if index == 0 else
                                   'Derived from selected annual non-EOM lattice through the first reset'}
    result['financial_scenario'] = scenario
    return result


def mutations(request=None):
    c = ['contract_calculation']
    p = c + ['premises']
    t = ['term_interpretations', 'terms']
    rows = [
        ('missing-last-period', c + ['periods', 5], 'delete', None),
        ('extra-period', c + ['periods'], 'append', (request or load(REVIEW / 'phase-request.json'))['contract_calculation']['periods'][-1]),
        ('period-term-override', c + ['periods', 0, 'accrual_end'], 'set', '2026-11-26'),
        ('common-rate-override', p + ['annual_rate'], 'set', '1/2'),
        ('actual-premise', p + ['premise_kind'], 'set', 'ACTUAL'),
        ('stale-terms', c + ['terms_sha256'], 'set', '0' * 64),
        ('wrong-calculation-version', c + ['version'], 'set', 'selected-coupon-calculation.v1'),
        ('wrong-profile', p + ['profile'], 'set', 'fixed-coupon.v1'),
        ('missing-no-call', p + ['phase_assumptions', 'no_call'], 'delete', None),
        ('missing-assumption-evidence', p + ['evidence', 'phase_assumptions'], 'delete', None),
        ('stale-assumption-source', p + ['evidence', 'phase_assumptions', 'source', 'source_sha256'], 'set', '0' * 64),
        ('over-issue-principal', p + ['holdings', 0, 'principal'], 'set', '1250000001'),
        ('malformed-holding', p + ['holdings', 0], 'set', None),
        ('missing-principal', p + ['holdings', 0, 'principal'], 'delete', None),
        ('excluded-principal-over-issue', p + ['holdings'], 'append', {'legal_holder_id': 'excluded', 'account_id': 'excluded', 'principal': '1250000000', 'entitled': False}),
        ('nonboolean-entitlement', p + ['holdings', 0, 'entitled'], 'set', 1),
        ('wrong-period-event', c + ['periods', 2, 'events', 0, 'at'], 'set', '2026-08-25T00:00:00Z'),
        ('ambiguous-event-order', c + ['periods', 0, 'events', 3, 'order'], 'set', 1),
        ('missing-period-evidence', c + ['periods', 2, 'evidence', 'events'], 'delete', None),
        ('stale-period-quote', c + ['periods', 2, 'evidence', 'events', 'source', 'quote'], 'set', 'changed'),
        ('calendar-too-short', p + ['calendar', 'valid_until'], 'set', '2028-11-26'),
        ('payment-unadjusted-weekend', c + ['periods', 2, 'payment_date'], 'set', '2028-11-25'),
        ('wrong-note-form', t + ['note_form', 'value'], 'set', 'DEFINITIVE'),
        ('wrong-day-count', t + ['day_count', 'value'], 'set', 'ACT_ACT_ICMA'),
        ('fake-maturity-boundary', t + ['fixed_phase_boundary', 'value'], 'set', 'MATURITY'),
        ('reset-date-misquote', t + ['fixed_phase_end', 'value'], 'set', '2030-11-25'),
        ('missing-anchor', t + ['coupon_anchor'], 'delete', None),
        ('invalid-rounding', t + ['rounding', 'value', 'quantum'], 'set', '0'),
        ('wrong-aggregation', t + ['rounding', 'value', 'aggregation'], 'set', 'PER_CALCULATION_AMOUNT'),
        ('invented-maturity', t + ['maturity_date'], 'set', {'value': '2031-11-25'}),
        ('stale-source-file', ['bundle', 'documents', 0, 'sha256'], 'set', '0' * 64),
        ('wrong-instrument', p + ['issue_id'], 'set', 'other-issue'),
    ]
    for key in ('no_call', 'no_cancellation', 'no_conversion', 'no_principal_reduction', 'no_tax'):
        for label, value in (('false', False), ('nonboolean', 1)):
            rows.append((key + '-' + label, p + ['phase_assumptions', key], 'set', value))
    rebind = {'wrong-note-form', 'wrong-day-count', 'fake-maturity-boundary', 'invalid-rounding', 'wrong-aggregation'}
    return [{'name': name, 'path': path, 'operation': operation, 'value': value,
             'rebind_terms': name in rebind} for name, path, operation, value in rows]


def mutate(request, row):
    result = deepcopy(request)
    target = result
    for key in row['path'][:-1]:
        target = target[key]
    last = row['path'][-1]
    if row['operation'] == 'delete':
        del target[last]
    elif row['operation'] == 'append':
        target[last].append(deepcopy(row['value']))
    else:
        assert row['operation'] == 'set'
        target[last] = deepcopy(row['value'])
    if row.get('rebind_terms'):
        p1 = service.source_product(result, ROOT)
        p2 = service.construction_product(p1, ROOT)
        terms = contract_terms.admit(p1['payload']['graph'], p2['payload']['assembly'], result['term_interpretations'])
        result['contract_calculation']['terms_sha256'] = digest(terms)
    return result


def valid_variants(request):
    holiday, excluded = deepcopy(request), deepcopy(request)
    holiday['contract_calculation']['premises']['calendar']['holidays'] = ['2026-11-25']
    holiday['contract_calculation']['periods'][0]['payment_date'] = '2026-11-26'
    holiday['contract_calculation']['periods'][0]['events'][-1]['at'] = '2026-11-26T00:00:00Z'
    excluded['contract_calculation']['premises']['holdings'][0]['entitled'] = False
    return {'holiday': holiday, 'excluded': excluded}


def consumers():
    admitted()
    request = load(REVIEW / 'phase-request.json')
    legacy_request = load(REVIEW / 'legacy-request.json')
    _, legacy = products('legacy', legacy_request, HERE)
    assert legacy == load(REVIEW / 'legacy-answer.json.gz'), 'Complete same-input legacy answer changed'
    selected, answer = products('selected', request, HERE)
    questions_preserved(answer, legacy)
    value = answer['questions']['Q5']['value']
    proof = oracle.check_value(value)
    for i in range(6):
        direct = direct_request(request, i)
        save(HERE / f'direct-{i}-request.json.gz', direct)
        _, response = products('direct-' + str(i), direct, HERE)
        questions_preserved(response, legacy)
        assert response['questions']['Q5']['value'] == value['calculations'][i]
    for name, variant in valid_variants(request).items():
        save(HERE / (name + '-request.json.gz'), variant)
        _, response = products(name, variant, HERE)
        questions_preserved(response, legacy)
        oracle.check_value(response['questions']['Q5']['value'], holiday=name == 'holiday', excluded=name == 'excluded')
    refusals = []
    for row in load(REVIEW / 'mutations.json'):
        variant = mutate(request, row)
        save(HERE / 'adverse' / (row['name'] + '-request.json.gz'), variant)
        try:
            evaluate(variant)
        except ValueError as exc:
            refusals.append({'name': row['name'], 'error': str(exc), 'refused': True})
        else:
            raise AssertionError('Permissive ordinary consumer: ' + row['name'])
    # These controls alter real sealed products, rather than an input-side echo.
    for name, product, field in [('parent-P5', 'P5', 'inputs'), ('tampered-P3', 'P3', 'sha256')]:
        altered = deepcopy(selected)
        if field == 'inputs':
            altered[product][field]['P3'] = '0' * 64
            altered[product]['sha256'] = digest({k: v for k, v in altered[product].items() if k != 'sha256'})
        else:
            altered[product][field] = '0' * 64
        save(HERE / 'adverse' / (name + '-products.json.gz'), altered)
        try:
            service.consume(altered, ROOT)
        except ValueError as exc:
            refusals.append({'name': name, 'error': str(exc), 'refused': True})
        else:
            raise AssertionError('Permissive sealed-product binding: ' + name)
    save(HERE / 'refusals.json', refusals)
    save(HERE / 'source-integer-proof.json', {'sources': oracle.source_check(OLD), **proof})
    return {'periods': 6, 'direct_consumers': 6, 'valid_variants': 2, 'refusals': len(refusals), 'total': proof['total'],
            'legacy_complete_answer_equal': True, 'original_questions_preserved': True}


def read_products(name):
    return {p: load(HERE / (name + '-' + p + '.json.gz')) for p in ('P1', 'P2', 'P3', 'P4', 'P5')}


def verification():
    admitted()
    oracle.source_check(OLD)
    phase = load(REVIEW / 'phase-request.json')
    assert phase == phase_request()
    assert load(REVIEW / 'mutations.json') == mutations()
    requests = {'selected': phase, 'legacy': load(REVIEW / 'legacy-request.json'), **valid_variants(phase)}
    requests.update({'direct-' + str(i): direct_request(phase, i) for i in range(6)})
    answers = {}
    for name, request in requests.items():
        answer = load(HERE / (name + '-answer.json.gz'))
        product_set = read_products(name)
        assert product_set['P1']['payload']['request'] == request
        assert service.consume(product_set, ROOT) == answer == evaluate(request), 'Full consumer replay: ' + name
        answers[name] = answer
    assert answers['legacy'] == load(REVIEW / 'legacy-answer.json.gz')
    for answer in answers.values():
        questions_preserved(answer, answers['legacy'])
    proof = oracle.check_value(answers['selected']['questions']['Q5']['value'])
    for name in ('holiday', 'excluded'):
        oracle.check_value(answers[name]['questions']['Q5']['value'], holiday=name == 'holiday', excluded=name == 'excluded')
    for i in range(6):
        assert answers['direct-' + str(i)]['questions']['Q5']['value'] == answers['selected']['questions']['Q5']['value']['calculations'][i]
    refusal_rows = load(HERE / 'refusals.json')
    expected_names = [r['name'] for r in mutations()] + ['parent-P5', 'tampered-P3']
    assert [r['name'] for r in refusal_rows] == expected_names
    for row, expected in zip(mutations(), refusal_rows):
        retained = load(HERE / 'adverse' / (row['name'] + '-request.json.gz'))
        assert retained == mutate(phase, row)
        try:
            evaluate(retained)
        except ValueError as exc:
            assert expected == {'name': row['name'], 'error': str(exc), 'refused': True}
        else:
            raise AssertionError('Adverse replay accepted: ' + row['name'])
    for expected in refusal_rows[-2:]:
        try:
            service.consume(load(HERE / 'adverse' / (expected['name'] + '-products.json.gz')), ROOT)
        except ValueError as exc:
            assert str(exc) == expected['error'] and expected['refused'] is True
        else:
            raise AssertionError('Altered parent/product replay accepted')
    assert 'parent bindings' in refusal_rows[-2]['error']
    discriminated = []
    for defect in ('omit-last-coupon', 'accrue-through-delayed-payment'):
        wrong = deepcopy(answers['holiday' if defect.startswith('accrue') else 'selected']['questions']['Q5']['value'])
        if defect == 'omit-last-coupon':
            wrong['calculations'].pop()
            wrong['coupon_schedule'].pop()
        else:
            # Wrong source interpretation adds one day of interest for payment delay.
            count = oracle.numerator('2026-08-25', '2026-11-26')
            wrong['calculations'][0]['day_fraction'] = str(Fraction(count, 360))
            wrong['calculations'][0]['transfers'][0]['unrounded'] = str(Fraction(1000000 * 51 * count, 1000 * 360))
        save(HERE / 'wrong-functions' / (defect + '.json.gz'), wrong)
        try:
            oracle.check_value(wrong, holiday=defect.startswith('accrue'))
        except AssertionError:
            discriminated.append(defect)
        else:
            raise AssertionError('Independent oracle failed to distinguish ' + defect)
    tampered = deepcopy(answers['selected'])
    tampered['questions']['Q1']['status'] = 'UNKNOWN' if tampered['questions']['Q1']['status'] != 'UNKNOWN' else 'YES'
    try:
        questions_preserved(tampered, answers['legacy'])
    except AssertionError:
        discriminated.append('alter-original-question')
    else:
        raise AssertionError('Checker permits changed original question')
    xml = ET.parse(HERE / 'tests.xml').getroot()
    counts = {k: sum(int(s.get(k, '0')) for s in xml.iter('testsuite')) for k in ('tests', 'failures', 'errors', 'skipped')}
    assert counts == read(HERE / 'stages/regressions/result.json')['detail']
    assert read(HERE / 'test-command.json')['tests'] == TESTS
    assert not any(counts[k] for k in ('failures', 'errors', 'skipped'))
    return {'full_answers_replayed': len(answers), 'refusals_replayed': len(refusal_rows),
            'source_integer_total': proof['total'], 'wrong_functions_distinguished': discriminated,
            'tests': counts, 'independence': 'SEPARATE_SOURCE_INTEGER_ORACLE; PRODUCTION_REPLAY_IS_REGRESSION_ONLY'}


def package_storage():
    paths = {ROOT / n for n in method_names()}
    for folder in (REVIEW, HERE):
        paths.update(p for p in folder.rglob('*') if p.is_file())
    paths.update(ROOT / REL / name for name in ('proposals/fixed-phase-256.json', 'proposals/fixed-phase-256-review.json',
                 'revisions/0256.json', 'closure-routes-2026-10-18-fixed-phase-256.json'))
    # Count the whole active program conservatively, not merely its size increase.
    paths.add(ROOT / REL / 'program.json')
    return sum(p.stat().st_size for p in paths if p.is_file())


def measured_seconds():
    return sum(read(p)['seconds'] for folder in (REVIEW, HERE) for p in folder.glob('stages/*/result.json'))


def propose():
    auth = Authority(ROOT)
    old, _, _ = auth.spec()
    assert old['revision'] == 255
    attempts = [e['attempt'] for e in auth.events() if e['kind'] == 'ADMIT' and e['budget_key'] == 'finance-conventions']
    assert len(attempts) == old['budgets']['finance-conventions']['maximum_new_attempts'] == 7
    assert read(REVIEW / 'stages/preflight/result.json')['status'] == 'PASS'
    phase = phase_request()
    prepared = {}

    def retain(path, value, pretty=False):
        raw = (json.dumps(value, indent=2, ensure_ascii=False) + '\n' if pretty else
               json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)).encode()
        assert not path.exists(), 'Refusing to overwrite preparation: ' + str(path)
        prepared[path] = raw
        return sha256(raw).hexdigest()

    retain(REVIEW / 'phase-request.json', phase)
    retain(REVIEW / 'mutations.json', mutations(phase))
    before = load(REVIEW / 'pre-edit-methods.json')
    patch = []
    for name in sorted(set(before) | {'src/legalmath/prospectus/successor/fixed_phase.py'}):
        previous = REVIEW / 'pre-edit' / name
        original = previous.read_text() if previous.is_file() else ''
        patch.extend(difflib.unified_diff(original.splitlines(True), (ROOT / name).read_text().splitlines(True),
                     fromfile='pre-edit/' + name, tofile=name))
    assert patch
    prepared[REVIEW / 'candidate.patch'] = ''.join(patch).encode()
    methods = {name: file_hash(ROOT / name) for name in method_names()}
    for name in methods:
        target = REVIEW / 'methods' / name
        assert not target.exists(), 'Refusing to overwrite frozen method'
        prepared[target] = (ROOT / name).read_bytes()
    freeze_hash = retain(REVIEW / 'freeze.json', {'methods': methods, 'source_bindings': load(REVIEW / 'source-bindings.json'),
          'rule': 'No bound method/input edits after admission; actual results are new exclusive files'})
    new = deepcopy(old)
    new['revision'] = 256
    task = next(t for t in new['tasks'] if t['id'] == 'finance-conventions')
    task.update(dossier=PLAN, build_criteria_scope=[],
                reason='Validate frozen source-bound Danske six-coupon fixed phase without fictitious maturity; no old quantity or whole-task criterion claimed')
    task['fixed_phase_validation'] = {'version': 'danske-fixed-phase.v1', 'review': str(REVIEW.relative_to(ROOT)),
        'effective_bounds': BOUNDS, 'retained_admissions': attempts, 'automatic_retry': False,
        'whole_task_acceptance': False, 'independent_source_oracle': 'scripts/prospectus_fixed_phase_oracle.py'}
    extra = set(methods) | {str(p.relative_to(ROOT)) for p in REVIEW.rglob('*') if p.is_file()}
    extra |= {str(p.relative_to(ROOT)) for p in prepared}
    extra |= {str((REVIEW / name).relative_to(ROOT)) for name in ('preflight.json', 'stages/propose/result.json')}
    task['inputs'] = sorted(set(task['inputs']) | extra)
    new['budgets']['finance-conventions']['maximum_new_attempts'] = 8
    route = REL + '/closure-routes-2026-10-18-fixed-phase-256.json'
    mapping = read(ROOT / old['continuation_review']['routes'])
    mapping['baseline_revision'] = 256
    row = next(r for r in mapping['tasks'] if r['task'] == task['id'])
    row.update(task_sha256=authority_digest(task), dossier=PLAN,
        remaining='Fixed-phase candidate prepared; six-coupon downstream validation pending; all original finance coverage and old criteria remain open.',
        next_action='Validate frozen256/008 once: focused regressions, selected/direct full answers, independent source-integer oracle, adverse controls, seal/record/refresh; then inspect next substantive route.',
        stop_condition=json.dumps(BOUNDS, sort_keys=True))
    route_hash = retain(ROOT / route, mapping, pretty=True)
    new['continuation_review'].update(plan=PLAN, routes=route)
    for name in (PLAN, route, 'scripts/prospectus_fixed_phase.py', 'scripts/prospectus_fixed_phase_oracle.py',
                 str((REVIEW / 'freeze.json').relative_to(ROOT))):
        new['continuation_review']['bindings'][name] = ({route: route_hash,
            str((REVIEW / 'freeze.json').relative_to(ROOT)): freeze_hash}.get(name) or file_hash(ROOT / name))
    review = {'baseline': authority_digest(old),
        'changes': ['Refine same finance-conventions task for six fixed coupons through first reset',
                    'Freeze prepared methods and source evidence; retained unsupported and same-input legacy baselines',
                    'Explicit empty conditional criterion scope; no old quantity replay or criterion award',
                    'One cumulative admission7-to8; all prior admissions/resources and obligations retained'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN,
            'baseline': 'New same-hypothesis unsupported v5 and supported complete legacy v1; original003 is distinct and unchanged',
            'resolved': ['No fake maturity or definitive-form amount', 'Separate period events and explicit absence assumptions',
                         'Excluded holdings count toward issue principal; malformed holding rows refused',
                         'Independent integer oracle, deliberately wrong results, full questions and hash/parent controls',
                         'Freeze precedes admission; finite tests are not promotion evidence'],
            'limitations': ['Reviewed source translations', 'Hypothetical calendar/holdings/rounding/events',
                            'No actual payment, floating/redemption, whole-task or package-wide conclusion']},
        'evidence_contract': {'question': 'Do ordinary selected/direct consumers deliver all six conditional fixed coupons through reset?',
            'baseline': 'Preserved same-input legacy whole answer, original retained sources and independent integer derivation',
            'primary': 'Six contiguous periods; amounts12750+5*51000=267750; all original questions preserved; separate period premises',
            'veto': ['Wrong arithmetic/schedule', 'Changed originals/methods', 'Permissive source/parent/premise/event controls', 'Misleading actual or maturity claims'],
            'continuation_veto': ['Corrupt source/comparator', 'Exceeded reviewed resource ceiling', 'Unexpected external activity'],
            'explanatory': ['Test counts', 'Runtime', 'Storage below ceiling'],
            'not_concluded': ['Actual VP calendar', 'Legal entitlement', 'No actual redemption', 'Floating coupons',
                              'Automatic legal interpretation', 'Whole-build correctness', 'Fundamental package defect']},
        'scope_unchanged': True, 'budget_unchanged': False,
        'budget_revision': {'budget_key': 'finance-conventions', 'previous_maximum': 7, 'new_maximum': 8,
            'retained_attempts': attempts, 'reason': 'One changed source-bound optional fixed-phase repair; not a quantity retry',
            'next_discriminating_check': 'Actual six-period selected/direct consumer with independent source-integer and wrong-function checks',
            'stop_condition': BOUNDS, 'same_scope_authorization': 'User-directed refresh and continued general build; no new external action or cost'},
        'original_obligations_preserved': True, 'external_opinion_required': False}
    assert old['obligations'] == new['obligations'] and old['build_contract'] == new['build_contract']
    serialized = (json.dumps(new, indent=2, ensure_ascii=False) + '\n').encode()
    review_bytes = len((json.dumps(review, indent=2, ensure_ascii=False) + '\n').encode())
    occupied = package_storage()
    # Replace the old active copy with the new one, plus proposal and revision.
    # All candidate files are still in memory, so a refused forecast writes none.
    old_program_bytes = (ROOT / REL / 'program.json').stat().st_size
    prepared_bytes = sum(len(raw) for raw in prepared.values())
    forecast = occupied - old_program_bytes + prepared_bytes + 3 * len(serialized) + review_bytes + 20 * 1024**2 + 2 * 1024**2 + BOUNDS['reserve_bytes']
    assert forecast < BOUNDS['new_bytes'], 'Complete storage forecast exceeds64MiB'
    historical = []
    for name in attempts:
        folder = ROOT / name
        manifest = read(folder / 'run-manifest.json') if (folder / 'run-manifest.json').is_file() else {}
        historical.append({'attempt': name, 'bytes': sum(p.stat().st_size for p in folder.rglob('*') if p.is_file()),
                           'reported_timing_fields': {k: v for k, v in manifest.items() if 'seconds' in k or 'time' in k}})
    for path, raw in prepared.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    save(REVIEW / 'preflight.json', {'status': 'PASS', 'occupied_bytes_conservative': occupied,
        'replaced_old_program_bytes': old_program_bytes, 'prepared_new_file_bytes': prepared_bytes,
        'exact_new_program_bytes_each': len(serialized), 'new_full_program_copies_forecast': 3,
        'review_bytes': review_bytes, 'validation_output_forecast_bytes': 20 * 1024**2,
        'metadata_forecast_bytes': 2 * 1024**2, 'seal_reserve_bytes': BOUNDS['reserve_bytes'],
        'forecast_total_bytes': forecast, 'incremental_ceiling_bytes': BOUNDS['new_bytes'],
        'preparation_measured_seconds_before_proposal': measured_seconds(), 'historical': historical,
        'historical_unmeasured_seconds': 'UNKNOWN; no complete historical runtime claim'})
    write(ROOT / REL / 'proposals/fixed-phase-256.json', new, exclusive=True)
    write(ROOT / REL / 'proposals/fixed-phase-256-review.json', review, exclusive=True)
    assert (ROOT / REL / 'proposals/fixed-phase-256.json').stat().st_size == len(serialized)
    return {'revision': 256, 'forecast_bytes': forecast, 'ceiling_bytes': BOUNDS['new_bytes'],
            'retained_admissions': len(attempts), 'methods': len(methods), 'criteria_claimed': []}


def seal():
    admitted()
    stages = {name: read(HERE / 'stages' / name / 'result.json') for name in ('regressions', 'consumers', 'verification')}
    assert all(s['status'] == 'PASS' for s in stages.values())
    assert measured_seconds() < BOUNDS['incremental_seconds']
    assert package_storage() + BOUNDS['reserve_bytes'] < BOUNDS['new_bytes']
    manifest = {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': {name: read(HERE / 'stages' / name / 'started.json') for name in stages},
        'test_command': read(HERE / 'test-command.json'), 'environment': 'Existing .venv; current worktree src pinned',
        'interpreter': sys.executable, 'python': sys.version, 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',
        'random_seeds': 'N/A; deterministic', 'source_data': load(REVIEW / 'source-bindings.json'),
        'methods': frozen(), 'plan': PLAN, 'result': str((HERE / 'RESULT.md').relative_to(ROOT)),
        'measured_incremental_seconds_before_seal': measured_seconds(), 'storage_bytes_before_seal': package_storage(),
        'bounds': BOUNDS, 'historical': load(REVIEW / 'preflight.json')['historical'],
        'historical_unmeasured_seconds': 'UNKNOWN', 'network_installs_native_OCR_model_GPU_calls': 0,
        'at': datetime.now(timezone.utc).isoformat()}
    save(HERE / 'run-manifest.json', manifest)
    detail = stages['verification']['detail']
    note = '''# Danske conditional fixed-phase repair

The actual selected consumer now calculates six fixed coupons through the first
reset, using the original retained supplement and base memorandum with explicit
hypothetical holdings, calendar, rounding and absence-of-event premises. The
amounts are DKK12,750 followed by five DKK51,000 coupons, totalDKK267,750.
The reset is an exclusive accrual boundary, not maturity. No floating coupon,
redemption, settlement or actual entitlement is inferred.

All six hand-enumerated direct consumers agree with the selected calculations.
The complete legacy answer is unchanged; Q1–Q4 and Q6 are preserved in every
positive consumer. Holiday delay changes the payment date without adding
interest. Excluded holdings create no transfers. The separate source-integer
oracle agrees and rejects omission of the last coupon and accrual through a
delayed payment. Source, version, term, parent, assumption, principal, calendar
and event controls are refused through the ordinary product path.

| Decision | Primary criterion | Veto diagnostics | Main uncertainty | Next justified action | Limit |
| --- | --- | --- | --- | --- | --- |
| Retain conditional repair | Six source-prescribed dates and exact amounts; full selected/direct consumers agree | No failed regression or permissive control; frozen methods unchanged | Real VP calendar, holdings, redemption/cancellation/conversion and tax remain unknown | Record partial finance evidence, refresh sole authority and inspect next substantive route | No original-task, package-wide or whole-build completion |

The reproduced pre-edit failure is a missing local versioned integration path,
not evidence of a fundamental third-party package problem. The original003
hypotheses and every sealed historical attempt remain unchanged. This package
claims no old quantity criterion. Test totals are regression diagnostics.

The strongest alternative explanation is an incorrect reviewed source
translation or hypothetical premise. The retained source anchors, independent
integer derivation and adverse controls constrain the declared numerical
domain; they cannot prove unseen legal interpretations. A conflicting source
or real intervening event would require a different conditional scenario.
'''
    with (HERE / 'RESULT.md').open('x') as stream:
        stream.write(note)
    save(HERE / 'result.json', {'task': 'finance-conventions', 'status': 'PASS',
        'classification': 'CONDITIONAL_FIXED_PHASE_REPAIR', 'whole_task_complete': False,
        'build_criteria_claimed': [], 'original_questions_preserved': True, **detail})
    return {'status': 'SEALED_PARTIAL', 'periods': 6, 'total': '267750', **detail}


def stage(stage_name, action, folder):
    target = folder / 'stages' / stage_name
    write(target / 'started.json', {'argv': [sys.executable, str(Path(__file__).relative_to(ROOT)), stage_name],
          'at': datetime.now(timezone.utc).isoformat(), 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'}, exclusive=True)
    start = time.monotonic()
    group = 'preparation' if folder == REVIEW else ('validation' if stage_name in {'verification', 'seal'} else stage_name)
    previous = [(p, read(p)) for base in (REVIEW, HERE) for p in base.glob('stages/*/result.json')]
    used = sum(row['seconds'] for _, row in previous)
    group_used = sum(row['seconds'] for p, row in previous if
        ('preparation' if REVIEW in p.parents else ('validation' if p.parent.name in {'verification', 'seal'} else p.parent.name)) == group)
    remaining = min(BOUNDS[group + '_seconds'] - group_used, BOUNDS['incremental_seconds'] - used)
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Reviewed stage ceiling')))
    try:
        assert remaining > 0, 'Reviewed cumulative time ceiling exhausted'
        assert package_storage() + BOUNDS['reserve_bytes'] < BOUNDS['new_bytes'], 'Reviewed storage ceiling'
        signal.alarm(math.ceil(remaining))
        detail = action()
        elapsed = time.monotonic() - start
        assert elapsed <= remaining, 'Reviewed cumulative time ceiling exceeded'
        assert package_storage() + BOUNDS['reserve_bytes'] < BOUNDS['new_bytes'], 'Reviewed storage ceiling'
        result = {'status': 'PASS', 'seconds': elapsed, 'group': group, 'detail': detail}
    except Exception as exc:
        write(target / 'result.json', {'status': 'FAIL', 'seconds': time.monotonic() - start,
              'error': type(exc).__name__ + ': ' + str(exc)}, exclusive=True)
        raise
    finally:
        signal.alarm(0)
    write(target / 'result.json', result, exclusive=True)
    if stage_name == 'seal':
        save(HERE / 'final-resources.json', {'measured_incremental_seconds_including_seal': measured_seconds(),
            'bytes_before_final_manifests': package_storage(), 'final_manifest_reserve_bytes': BOUNDS['reserve_bytes'],
            'bound_seconds': BOUNDS['incremental_seconds'], 'bound_bytes': BOUNDS['new_bytes'],
            'seal_receipt': 'stages/seal/result.json', 'historical_unmeasured_seconds': 'UNKNOWN'})
        save(HERE / 'outputs.json', {str(p.relative_to(HERE)): file_hash(p) for p in sorted(HERE.rglob('*'))
             if p.is_file() and p.name not in {'admission.json', 'outputs.json'}})
        assert package_storage() < BOUNDS['new_bytes'], 'Final output manifest exceeds storage ceiling'
    print(json.dumps({'stage': stage_name, **result}), flush=True)


if __name__ == '__main__':
    actions = {'prepare': (prepare, REVIEW), 'preflight': (preflight, REVIEW), 'propose': (propose, REVIEW),
               'regressions': (lambda: (admitted(), run_tests(HERE, TESTS))[1], HERE),
               'consumers': (consumers, HERE), 'verification': (verification, HERE), 'seal': (seal, HERE)}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        raise SystemExit('Expected exactly one reviewed stage: ' + ', '.join(actions))
    action, folder = actions[sys.argv[1]]
    stage(sys.argv[1], action, folder)
