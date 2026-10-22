"""Pre-candidate whole-answer expectation from the separately reviewed069 matrix."""
from copy import deepcopy
from legalmath.prospectus.successor.contracts import digest

KEY = 'definition_use_bindings'
VERSION = 'definition-use-bindings.v1'
CLASSES = {'GOVERNING_USE_NOT_RECONCILED': 'UNRECONCILED',
           'EXISTING_CONDITIONAL_APPLICATION': 'BOUND_CONDITIONALLY',
           'EXPLICIT_UNRESOLVED_OR_EXCLUDED_USE': 'EXPLICIT_REMAINDER',
           'OTHER_PURPOSE_DEFINITION': 'OTHER_DEFINITION'}


def expected_content(ordinary, coverage):
    report = ordinary['definition_sources']
    supplement = report['application_supplement']
    rules = {r['id']: r for r in supplement['rules']}
    applications = {r['id']: r for r in supplement['applications']}
    originals = {r['id']: r for r in report['records']}
    records, uses = [], []
    for row in coverage['records']:
        record = originals[row['id']]
        first = len(uses)
        expected = [(u, 'ORIGINAL', u['disposition']) for u in row['uses']]
        for extra in coverage['discovery_differences']:
            if extra['record'] == row['id'] and extra['kind'] == 'ADDITIONAL':
                expected.append(({**extra, 'interval': None}, 'SUPPLEMENTAL', extra['record_use_disposition']))
        for item, origin, label in expected:
            disposition = CLASSES[label]
            app = applications.get(item.get('application_id'))
            rule = rules[app['rule']] if app and app['rule'] else None
            binding = None
            if disposition == 'BOUND_CONDITIONALLY':
                assert rule is not None and rule['record'] == row['id']
                binding = {'record': rule['record'], 'rule': rule['id'], 'group': rule['group'],
                           'meaning': deepcopy(rule['meaning']), 'condition': rule['condition'],
                           'rule_sha256': digest(rule)}
            remainder = (['GOVERNING_USE_NOT_RECONCILED'] if app is None else
                         ['OTHER_PURPOSE_DEFINITION:' + rule['record']] if disposition == 'OTHER_DEFINITION'
                         else deepcopy(app['remaining']))
            uses.append({'record': row['id'], 'origin': origin, 'interval': item['interval'],
                'start': item['start'], 'end': item['end'], 'quote': item['quote'],
                'disposition': disposition, 'application_id': app['id'] if app else None,
                'application_sha256': digest(app) if app else None, 'binding': binding, 'remaining': remainder})
        records.append({'id': row['id'], 'original_record_sha256': digest(record),
            'rule_ids': [r['id'] for r in supplement['rules'] if r['record'] == row['id']],
            'use_indices': list(range(first, len(uses))), 'original_uses': len(row['uses']),
            'supplemental_uses': len(uses) - first - len(row['uses']), 'original_status': record['status']})
    return {'records': records, 'uses': uses, 'rules': deepcopy(supplement['rules']),
            'original_associations': 610, 'supplemental_associations': 2}


def question_links(ordinary, content):
    expected_ids = ['definition-source:' + r['id'] for r in content['records']]
    bound = [i for i, u in enumerate(content['uses']) if u['disposition'] == 'BOUND_CONDITIONALLY']
    output = []
    for question in ('Q1', 'Q2'):
        parent = ordinary['questions'][question]
        entries = [(['questions', question], parent)]
        entries.extend((['questions', question, 'subquestions', k], v) for k, v in parent.get('subquestions', {}).items())
        for path, answer in entries:
            actual = [x for x in answer['unresolved'] if x.startswith('definition-source:')]
            assert len(actual) == len(expected_ids) and set(actual) == set(expected_ids)
            output.append({'path': path, 'unresolved_definition_ids': actual, 'bound_use_indices': bound,
                           'retained_status': answer['status'], 'retained_value': answer['value']})
    return output


def expected_report(ordinary, products, profile, content):
    return {'version': VERSION, 'profile_sha256': digest(profile), 'products_sha256': digest(products),
        'ordinary_answer_sha256': digest(ordinary), 'definition_report_sha256': digest(ordinary['definition_sources']),
        'application_supplement_sha256': digest(ordinary['definition_sources']['application_supplement']),
        **deepcopy(content), 'question_links': question_links(ordinary, content),
        'assistance': 'EXACT_SOURCE_REVIEWED_CONDITIONAL_APPLICATIONS',
        'original_report_preserved': True, 'original_question_uncertainties_preserved': True,
        'all_governing_uses_established': False, 'actual_facts_established': False,
        'historical_law_established': False, 'automatic_legal_interpretation': False, 'whole_task_complete': False}


def verify(answer, ordinary, products, profile, content):
    result = {**ordinary, KEY: expected_report(ordinary, products, profile, content)}
    result['report_sha256'] = digest({k: v for k, v in result.items() if k != 'report_sha256'})
    assert answer == result, 'Complete answer differs from independently frozen binding expectation'
    return {'status': 'PASS', 'whole_answer_equal_to_independent_expectation': True,
            'original_associations': 610, 'supplemental_associations': 2,
            'conditional_bindings': sum(u['binding'] is not None for u in content['uses'])}
