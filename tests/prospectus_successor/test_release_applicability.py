"""Recognizable but incomplete issuer releases cannot acquire assurance."""
from copy import deepcopy

import pytest

from legalmath.prospectus.successor import report_scope, service, unaudited_release
from test_unaudited_release import fixture as fy_fixture, TEXT as FY, UNKNOWN
from test_q1_release import fixture as q1_fixture, TEXT as Q1
from test_report_scope import exact_span, products


@pytest.mark.parametrize('label,fixture,text', [('fy', fy_fixture, FY), ('q1', q1_fixture, Q1)])
@pytest.mark.parametrize('variant', ['eu', 'date', 'commentary', 'assurance'])
@pytest.mark.parametrize('category', list(report_scope.PROFILES))
def test_changed_release_cannot_borrow_report_category(tmp_path, label, fixture, text, variant, category):
    changes = {
        'eu': text.replace(' as implemented by the European Union', '', 1),
        'date': text.replace('Lisbon, 31 January 2011' if label == 'fy' else 'Lisbon, 2 May 2011', 'Lisbon, 3 May 2011', 1),
        'commentary': 'Commentary quotes the following issuer release.\n' + text,
        'assurance': text.replace('Unaudited', 'Audited', 1),
    }
    p1, p2, scope, retained = fixture(tmp_path, changes[variant])
    facts = scope['reports'][0]['facts']
    facts['identity']['value'] = category
    for name, value in report_scope.PROFILES[category].items():
        facts[name] = {'status': 'SUPPLIED', 'value': value,
                      'spans': facts[name].get('spans', [exact_span(retained, 'MATERIAL EVENT')])}
    if category == 'COMMITTEE_REPORT':
        facts['assurance_level'] = deepcopy(UNKNOWN)
    for field in ('addressee', 'purpose', 'reliance_limits'):
        facts[field] = {'status': 'SUPPLIED', 'spans': [exact_span(retained, 'MATERIAL EVENT')]}
    report, = service.consume(products(p1, p2, scope), tmp_path, mode='current')['source_reports']
    assert report['status'] == 'INCOMPLETE_SOURCE_READING'
    assert report['unresolved_unaudited_release_fields'] == ['source_header']
    assert all(value != 'SUPPLIED_SOURCE_SUPPORT' for value in report['use_assessment'].values())


@pytest.mark.parametrize('source', [
    'b28420dced99cbb219a3f447ed43fa603d6ae1bc0086fb7705876e25631a569f',
    '4c7067274ff3eb8f812a8a98d23c4fd2d4b159ed0259f066069b2416ae2e75ec',
])
def test_known_cover_without_title_is_incomplete(source):
    reading = {'text': 'Explicit changed extraction with lost cover title.',
               'source_sha256': source, 'pages': [{'page': 1, 'mode': 'raw'}]}
    result = unaudited_release.check(reading, {'identity': {'status': 'SUPPLIED', 'value': 'STATUTORY_FINANCIAL_AUDIT'}})
    assert result['unresolved_fields'] == ['source_header']
    reading['pages'][0]['page'] = 5
    assert unaudited_release.check(reading, {'identity': {'status': 'SUPPLIED', 'value': 'STATUTORY_FINANCIAL_AUDIT'}}) is None


def test_generic_phrase_alone_does_not_assign_release_context():
    reading = {'text': 'A discussion of unaudited financial information.', 'source_sha256': 'other', 'pages': [{'page': 1}]}
    assert unaudited_release.check(reading, {'identity': {'status': 'SUPPLIED', 'value': 'STATUTORY_FINANCIAL_AUDIT'}}) is None


def test_incomplete_correct_category_still_refuses_invented_conclusion(tmp_path):
    p1, p2, scope, text = fy_fixture(tmp_path, FY.replace(' as implemented by the European Union', '', 1))
    scope['reports'][0]['facts']['conclusion'] = {
        'status': 'SUPPLIED', 'value': 'AFFIRMATIVE_FINANCIAL_OPINION',
        'spans': [exact_span(text, 'MATERIAL EVENT')]}
    with pytest.raises(ValueError, match='requires unknown independent opinion conclusion'):
        service.interpretation_product(p1, p2, {'source_report_scope': scope})
