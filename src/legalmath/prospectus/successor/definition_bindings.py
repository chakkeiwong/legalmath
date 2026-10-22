"""Exact, conditional links from registered definition identities to uses.

These additive links preserve the original unresolved definition report. The
registered finite source review supplies the rules; matching words does not.
"""
from copy import deepcopy

from .anchors import fields
from .contracts import digest
from .definition_applications import require

VERSION = 'definition-use-bindings.v1'
KEY = 'definition_use_bindings'
ORDINARY_SHA256 = '6ba48cc3d8c8ea91bde3e9a8edac5aea83f89a09bc5a6b1586f190f1114cad0e'
PRODUCTS_SHA256 = 'b7095aa6f5b68a13b77cfa8adc44168ca2339daf18a24c81b4ced203c66f16b4'
SEMANTIC_MATRIX_SHA256 = 'b85ca63511a21730c6f4f90838fd11395e2219bc7becc2be54abafb4ecb5e289'
RECORD_RULES = {
    'D31-holder-redemption-day': 'holder',
    'D41-affiliate': 'affiliate',
    'D45-custodian': 'custodian',
    'U06-tax-early-amount': 'tax',
    'U07-makewhole-early-amount': 'makewhole',
}


def _checked_report(products, ordinary):
    from . import definition_scopes, definition_roles, structural_roles
    p1, p2, p3 = (products[k]['payload'] for k in ('P1', 'P2', 'P3'))
    graph, request, assembly = p1['graph'], p1['request'], p2['assembly']
    interpretation_input = {**request, **(p3.get('interpretation_input') or {})}
    retained = definition_scopes.verify_consumed(graph, p2, interpretation_input, p3)
    require(retained is not None and 'application_supplement' in retained,
            'Registered definition sources and applications required')
    spec = structural_roles.verify(graph, assembly, request.get('structural_roles'))
    require(spec is not None, 'Registered structural review required')
    approved = {r['unit']: {'before': r['before']['role'], 'after': 'HEADER'}
                for r in spec['decisions']}
    current = definition_roles.project(retained, graph['units'], assembly, approved)
    require(ordinary.get('definition_sources') == current['report'],
            'Definition report differs from registered source and current-role reconstruction')
    history = ordinary.get('definition_role_projection', {})
    require(history.get('current_definition_report_sha256') == digest(current['report'])
            and history.get('prior_definition_report_sha256') == digest(retained)
            and history.get('changes') == current['changes'], 'Definition role history changed')
    return current['report'], assembly['continuous_text']


def _application_index(report, text):
    supplement = report['application_supplement']
    rules = {r['id']: r for r in supplement['rules']}
    require(len(rules) == len(supplement['rules']) == len(RECORD_RULES)
            and {r['record']: r['id'] for r in rules.values()} == RECORD_RULES,
            'Registered rule/record identities changed')
    records = {r['id']: r for r in report['records']}
    for rule in rules.values():
        declarations = [report['intervals'][i] for i in records[rule['record']]['declarations']]
        for premise in rule['premises']:
            require(text[premise['start']:premise['end']] == premise['quote'],
                    'Rule premise differs from source')
        require(all(any(p['start'] <= d['start'] < d['end'] <= p['end']
                        for p in rule['premises']) for d in declarations),
                'Rule premises do not cover this record declaration')
        require(rule['extents'] and all(type(a) is int and type(b) is int
                and 0 <= a < b <= len(text) for a, b in rule['extents']),
                'Invalid express rule extent')
    applications = {}
    ids = set()
    for app in supplement['applications']:
        key = (app['start'], app['end'])
        require(key not in applications and app['id'] not in ids,
                'Duplicate application identity or interval')
        require(text[key[0]:key[1]] == app['quote'], 'Application quotation changed')
        applications[key] = app
        ids.add(app['id'])
    return rules, applications


def _rule_binding(record_id, application, rules, record_rules, start, end):
    if application is None:
        return 'UNRECONCILED', None, ['GOVERNING_USE_NOT_RECONCILED']
    require((application['start'], application['end']) == (start, end),
            'Application belongs to another occurrence')
    rule_id = application['rule']
    if rule_id is None:
        require(application['meaning'] is None and application['condition'] is None
                and application['remaining'], 'Excluded use acquired a meaning')
        return 'EXPLICIT_REMAINDER', None, deepcopy(application['remaining'])
    require(rule_id in rules, 'Application refers to unknown rule')
    rule = rules[rule_id]
    require(record_rules.get(rule['record']) == rule_id
            and any(a <= start < end <= b for a, b in rule['extents'])
            and application['group'] == rule['group']
            and application['meaning'] == rule['meaning']
            and application['condition'] == rule['condition']
            and application['role'] in {'OPERATIVE_USE', 'DECLARATION'}
            and application['remaining'] == [],
            'Application purpose, extent, meaning or qualification differs from source rule')
    if rule['record'] != record_id:
        return 'OTHER_DEFINITION', None, ['OTHER_PURPOSE_DEFINITION:' + rule['record']]
    return 'BOUND_CONDITIONALLY', {
        'record': rule['record'], 'rule': rule['id'], 'group': rule['group'],
        'meaning': deepcopy(rule['meaning']), 'condition': rule['condition'],
        'rule_sha256': digest(rule)}, []


def _question_links(ordinary, records, uses):
    expected_ids = {'definition-source:' + r['id'] for r in records}
    bound = [i for i, row in enumerate(uses) if row['disposition'] == 'BOUND_CONDITIONALLY']
    result = []
    for question in ('Q1', 'Q2'):
        parent = ordinary['questions'][question]
        entries = [(['questions', question], parent)]
        entries.extend((['questions', question, 'subquestions', key], value)
                       for key, value in parent.get('subquestions', {}).items())
        for path, answer in entries:
            actual = [x for x in answer['unresolved'] if x.startswith('definition-source:')]
            require(len(actual) == len(expected_ids) and set(actual) == expected_ids
                    and answer['status'] in {'UNKNOWN', 'CONFLICT'} and answer['value'] is None,
                    'Original question definition uncertainty changed')
            result.append({'path': path, 'unresolved_definition_ids': actual,
                'bound_use_indices': bound, 'retained_status': answer['status'],
                'retained_value': answer['value']})
    return result


def _content(report, text, profile):
    rules, applications = _application_index(report, text)
    extra = report['application_supplement']['source_supplement']['new_occurrence']
    require({k: extra[k] for k in ('start', 'end', 'quote')} == profile['supplemental_occurrence']
            and extra['candidate_record_associations'] == profile['supplemental_records'],
            'Supplemental occurrence or record identities changed')
    records, uses = [], []
    for record in report['records']:
        first = len(uses)
        items = [(report['intervals'][u['interval']], 'ORIGINAL', u['interval']) for u in record['uses']]
        if record['id'] in profile['supplemental_records']:
            items.append((extra, 'SUPPLEMENTAL', None))
        for occurrence, origin, interval in items:
            a, b = occurrence['start'], occurrence['end']
            require(text[a:b] == occurrence['quote'], 'Use quotation changed')
            app = applications.get((a, b))
            disposition, binding, remaining = _rule_binding(record['id'], app, rules, RECORD_RULES, a, b)
            uses.append({'record': record['id'], 'origin': origin, 'interval': interval,
                'start': a, 'end': b, 'quote': occurrence['quote'], 'disposition': disposition,
                'application_id': app['id'] if app else None,
                'application_sha256': digest(app) if app else None, 'binding': binding, 'remaining': remaining})
        records.append({'id': record['id'], 'original_record_sha256': digest(record),
            'rule_ids': [r['id'] for r in rules.values() if r['record'] == record['id']],
            'use_indices': list(range(first, len(uses))), 'original_uses': len(record['uses']),
            'supplemental_uses': len(items) - len(record['uses']), 'original_status': record['status']})
    result = {'records': records, 'uses': uses, 'rules': deepcopy(list(rules.values())),
        'original_associations': sum(r['original_uses'] for r in records),
        'supplemental_associations': sum(r['supplemental_uses'] for r in records)}
    require(len(records) == 62 and result['original_associations'] == 610
            and result['supplemental_associations'] == 2
            and digest(result) == profile['expected_content_sha256'], 'Reviewed binding matrix changed')
    return result


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'semantic_matrix_sha256',
            'expected_content_sha256', 'record_rules', 'supplemental_occurrence',
            'supplemental_records', 'legal_truth_established', 'whole_task_complete'}
    fields(profile, keys, keys)
    require(profile['version'] == VERSION and digest(profile) == expected_profile_sha256
            and profile['products_sha256'] == digest(products) == PRODUCTS_SHA256
            and profile['semantic_matrix_sha256'] == SEMANTIC_MATRIX_SHA256
            and profile['ordinary_answer_sha256'] == digest(ordinary) == ORDINARY_SHA256
            and ordinary.get('report_sha256') == digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})
            and profile['legal_truth_established'] is False and profile['whole_task_complete'] is False
            and KEY not in ordinary, 'Pinned definition profile or verified prior answer changed')
    require(profile['record_rules'] == RECORD_RULES
            and profile['supplemental_records'] == ['U06-tax-early-amount', 'U07-makewhole-early-amount'],
            'Reviewed record identities changed')
    report, text = _checked_report(products, ordinary)
    content = _content(report, text, profile)
    return {KEY: {'version': VERSION, 'profile_sha256': digest(profile),
        'products_sha256': digest(products), 'ordinary_answer_sha256': digest(ordinary),
        'definition_report_sha256': digest(report),
        'application_supplement_sha256': digest(report['application_supplement']),
        **content, 'question_links': _question_links(ordinary, content['records'], content['uses']),
        'assistance': 'EXACT_SOURCE_REVIEWED_CONDITIONAL_APPLICATIONS',
        'original_report_preserved': True, 'original_question_uncertainties_preserved': True,
        'all_governing_uses_established': False, 'actual_facts_established': False,
        'historical_law_established': False, 'automatic_legal_interpretation': False,
        'whole_task_complete': False}}


def verify_answer(answer, ordinary, profile, products, root, *, expected_profile_sha256):
    projection = evaluate(products, ordinary, profile, root, expected_profile_sha256=expected_profile_sha256)
    expected = {**ordinary, **projection}
    expected['report_sha256'] = digest({k: v for k, v in expected.items() if k != 'report_sha256'})
    require(answer == expected, 'Definition binding answer differs from complete reconstruction')
    return {'status': 'PASS', 'whole_answer_equal': True, 'legal_truth_established': False}
