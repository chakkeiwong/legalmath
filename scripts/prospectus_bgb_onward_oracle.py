"""Check the retained source-to-answer addition without importing its implementation."""
import json

from legalmath.prospectus.successor.contracts import digest

KEY = 'bgb802_onward_review'


def verify(actual, old, products, expected, profile, root):
    assert type(actual) is dict and KEY in actual, 'Missing onward answer'
    assert {k: v for k, v in actual.items() if k not in (KEY, 'report_sha256')} == {
        k: v for k, v in old.items() if k != 'report_sha256'}, 'Complete prior answer changed'
    assert actual['report_sha256'] == digest({k: v for k, v in actual.items() if k != 'report_sha256'}), 'Invalid report digest'
    report = actual[KEY]
    assert type(report) is dict and report == expected, 'Reading differs from frozen source expectations'
    assert report['profile_sha256'] == digest(profile)
    assert report['products_sha256'] == digest(products)
    assert report['ordinary_answer_sha256'] == digest(old)
    assert report['scope']['antecedent'] == 'BGB802_PRE_INITIATION_SIX_MONTH_PERIOD'
    assert report['scope']['status'] == 'LOCAL_GRAMMATICAL_CONSTRUCTION'
    assert report['scope']['application_to_all_clocks_proved'] is False
    assert report['scope']['source']['excerpts'][0]['end'] < report['scope']['source']['excerpts'][1]['start']
    h28 = next(r for r in old['statutory_references']['records'] if r['id'] == 'H28')
    assert report['h28_record_sha256'] == digest(h28)
    assert h28['availability'] == 'RETAINED_PRIMARY_READING' and h28['application'] == 'UNKNOWN'
    scope = report['scope']['source']
    assert scope['text_path'] == h28['legal_sources'][1]['text_path']
    assert scope['text_sha256'] == digest((root/scope['text_path']).read_bytes())
    scope_text = (root/scope['text_path']).read_text()
    for excerpt in scope['excerpts']:
        assert scope_text[excerpt['start']:excerpt['end']] == excerpt['quote']
    assert [r['section'] for r in report['readings']] == ['206', '210', '211']
    for row in report['readings']:
        source = row['source']
        text = (root/source['text_path']).read_text()
        assert digest((root/source['text_path']).read_bytes()) == source['text_sha256']
        for excerpt in source['excerpts']:
            assert text[excerpt['start']:excerpt['end']] == excerpt['quote']
        assert digest((root/source['raw_path']).read_bytes()) == source['raw_sha256']
        receipt_bytes = (root/source['receipt_path']).read_bytes()
        assert digest(receipt_bytes) == source['receipt_sha256']
        receipt = json.loads(receipt_bytes)
        assert receipt['http_code'] == 200 and receipt['exit_code'] == 0
        assert receipt['files']['body'] == source['raw_sha256']
        assert receipt['url'] == 'https://www.gesetze-im-internet.de/bgb/__' + row['section'] + '.html'
        assert row['historical_application_proved'] is False
        assert row['local_corresponding_application']['application_proved'] is False
        assert row['local_corresponding_application']['target_period'] == report['scope']['antecedent']
    rules = {r['section']: r['literal_rule'] for r in report['readings']}
    assert rules['206']['effect'] == 'SUSPENSION_WHILE_PREVENTED'
    assert rules['206']['conditions'] == ['CREDITOR_PREVENTED_FROM_PURSUING_RIGHT', 'FORCE_MAJEURE', 'WITHIN_LAST_SIX_MONTHS_OF_LIMITATION']
    assert rules['210']['effect'] == rules['211']['effect'] == 'PREVENTION_OF_EXPIRY'
    assert rules['210']['exceptions'] == ['SHORTER_LIMITATION_PERIOD_REPLACES_SIX_MONTHS', 'PARAGRAPH1_EXCLUDED_INSOFAR_LIMITED_CAPACITY_PERSON_HAS_PROCEDURAL_CAPACITY']
    assert rules['211']['exceptions'] == ['SHORTER_LIMITATION_PERIOD_REPLACES_SIX_MONTHS']
    assert rules['211']['alternative_events'] == ['INHERITANCE_ACCEPTED_BY_HEIR', 'ESTATE_INSOLVENCY_OPENED', 'CLAIM_CAN_BE_ASSERTED_BY_OR_AGAINST_REPRESENTATIVE']
    for name in ('historical_application_proved', 'actual_deadline_computed', 'automatic_legal_interpretation', 'whole_task_complete', 'whole_build_complete'):
        assert report[name] is False, name
    return {'status': 'PASS', 'complete_prior_answer_equal': True, 'literal_rules_retained': ['206', '210', '211'],
            'scope': report['scope']['antecedent'], 'historical_application_proved': False,
            'actual_deadline_computed': False, 'whole_build_complete': False}
