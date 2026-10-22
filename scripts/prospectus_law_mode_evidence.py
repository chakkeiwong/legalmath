"""Exact complete-answer projection for corrected legal assistance attribution."""
from copy import deepcopy
from legalmath.prospectus.successor import service
from scripts.prospectus_calendar_evidence import load, save, require

BASE = 'docs/implementation/prospectus-execution-authority'
ORIGINAL = BASE + '/attempts/law-applicability/attempt-006'
CALENDAR = BASE + '/attempts/law-applicability/attempt-008'
NATIVE = BASE + '/attempts/native-binding/attempt-017'
ROUTES = ('2009-fresh', '2009-default', '2009-retained', '2010-fresh', '2010-retained')


def corrected(expected):
    require(expected['mode'] in {'AUTOMATIC_BOUNDED', 'ASSISTED'}, 'Unexpected old mode')
    require(expected['report_sha256'] == service.digest({k: v for k, v in expected.items() if k != 'report_sha256'}),
            'Invalid original full report digest')
    target = {**deepcopy(expected), 'mode': 'ASSISTED'}
    target['report_sha256'] = service.digest({k: v for k, v in target.items() if k != 'report_sha256'})
    return target


def verify(actual, expected, *, assisted):
    target = corrected(expected) if assisted else expected
    require(service.digest(actual) == service.digest(target), 'Complete answer differs beyond exact reviewed mode correction')
    return {'complete_expected_equal': True, 'old_mode': expected['mode'], 'new_mode': actual['mode'],
            'old_report_sha256': expected['report_sha256'], 'new_report_sha256': actual['report_sha256'],
            'questions_unchanged': service.digest(actual['questions']) == service.digest(expected['questions'])}


def calendar(root, attempt):
    products = load(root / CALENDAR / 'common-products.json.gz')
    results = []
    for row in load(root / CALENDAR / 'calendar-evidence.json')['cases']:
        record = load(root / CALENDAR / 'cases' / (row['case'] + '.json.gz'))
        p4 = service.law_product(products['P1'], products['P3'], law_input=record['input'])
        require(service.digest(p4) == service.digest(record['P4']), 'Calendar P4 changed')
        answer = service.consume({**products, 'P4': p4}, root, mode='current')
        proof = verify(answer, record['answer'], assisted=True)
        save(attempt / 'calendar' / (row['case'] + '.json.gz'), {'P4': p4, 'answer': answer})
        results.append({'case': row['case'], **proof})
    require(len(results) == 19, 'Incomplete temporal report denominator')
    save(attempt / 'calendar-mode-evidence.json', results)
    return {'complete_calendar_answers': 19, 'P4_unchanged': True}


def original(root, attempt):
    products = load(root / ORIGINAL / 'common-products.json.gz')
    cases = load(root / ORIGINAL / 'favorable-deposit-P4.json.gz')['payload']['cases']
    results = []
    for row in load(root / ORIGINAL / 'cases-result.json')['cases']:
        name = row['case']
        data = load(root / ORIGINAL / (name + '-input.json.gz'))
        try:
            p4 = service.law_product(products['P1'], products['P3'], cases=cases, law_input=data)
            answer = service.consume({**products, 'P4': p4}, root, mode='current')
        except ValueError as exc:
            require(row['status'] == 'REJECTED' and str(exc) == row['reason'], 'Original law refusal changed')
            results.append({'case': name, 'refused': True, 'reason': str(exc)})
        else:
            require(row['status'] != 'REJECTED', 'Original adverse case no longer refuses')
            require(service.digest(p4) == service.digest(load(root / ORIGINAL / (name + '-P4.json.gz'))), 'Original P4 changed')
            proof = verify(answer, load(root / ORIGINAL / (name + '-answer.json.gz')), assisted=True)
            save(attempt / 'original' / (name + '.json.gz'), {'P4': p4, 'answer': answer})
            results.append({'case': name, **proof})
    require(sum(r.get('complete_expected_equal', False) for r in results) == 21
        and sum(r.get('refused', False) for r in results) == 2, 'Original law denominator differs')
    save(attempt / 'original-mode-evidence.json', results)
    return {'complete_original_answers': 21, 'original_refusals': 2, 'P4_unchanged': True}


def native(root, attempt, route):
    require(route in ROUTES, 'Unknown original native route')
    folder = root / NATIVE / 'routes' / route
    products = {p: load(folder / (p + '.json.gz')) for p in ('P1', 'P2', 'P3', 'P4', 'P5')}
    expected = load(folder / 'answer.json.gz')
    actual = service.consume(products, root, mode='frozen', include_artifacts=True)
    proof = verify(actual, expected, assisted=False)
    result = {'route': route, **proof, 'new_native_calls': 0, 'current_native_acceptance': False,
              'original_complete_answer_sha256': service.digest(expected)}
    save(attempt / 'native' / (route + '.json'), result)
    return result
