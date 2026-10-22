"""Changed report headings must not turn thin literal facts into support."""
from copy import deepcopy

import pytest

from legalmath.prospectus.successor import english_report_context, report_scope
from test_english_report_context import fixture, direct, UNKNOWN


@pytest.mark.parametrize('title', [
    'STATUTORY AUDITOR REPORT ON CONSOLIDATED FINANCIAL STATEMENTS',
    'STATUTORY AUDITORS’ REPORT ON CONSOLIDATED FINANCIAL STATEMENTS',
    "Statutory auditor's report on the financial statements",
    'AUDIT COMMITTEE REPORT FOR THE YEAR 2010',
    'Audit Committee Report for the Year 2011',
    '  Audit\tCommittee Report  ',
    'REPORT OF THE AUDIT COMMITTEE FOR THE YEAR 2011',
])
@pytest.mark.parametrize('kind', ['STATUTORY_FINANCIAL_AUDIT', 'COMMITTEE_REPORT',
                                 'LIMITED_SUSTAINABILITY_ASSURANCE'])
def test_recognizable_new_heading_withholds_internally_consistent_thin_facts(title, kind):
    text = 'Derivative report for regression testing.\n' + title + '\nUnreviewed body.'
    selected, scope = fixture(text, derivative=True)
    span = {'start': 0, 'end': text.index('\n'), 'quote': text.splitlines()[0]}
    codes = {'identity': kind, **report_scope.PROFILES[kind]}
    facts = {key: deepcopy(UNKNOWN) for key in report_scope.FACTS}
    for key in report_scope.FACTS - report_scope.EXTERNAL:
        facts[key] = {'status': 'SUPPLIED', 'spans': [span],
                      **({'value': codes[key]} if key in codes else {})}
    if kind == 'COMMITTEE_REPORT':
        facts['assurance_level'] = deepcopy(UNKNOWN)
    scope['reports'][0]['facts'] = facts
    answer = direct(selected, scope)
    assert answer['status'] == 'INCOMPLETE_SOURCE_READING'
    assert answer['english_report_context']['status'] == 'UNRECOGNIZED_OR_CHANGED_SOURCE_READING'
    assert 'SUPPLIED_SOURCE_SUPPORT' not in answer['use_assessment'].values()


@pytest.mark.parametrize('text', [
    'We received the statutory auditor report on consolidated financial statements yesterday.',
    'The audit committee report for the year 2011 was discussed.',
    'AUDIT COMMITTEE REPORTING POLICY',
    'Statutory auditor report on consolidated financial statements was requested.',
    'Independent Limited Assurance Report\nSustainability information.',
    'REPORT ON THE AUDIT COMMITTEE',
])
def test_added_heading_guard_does_not_match_ordinary_prose_or_unrelated_titles(text):
    selected, _ = fixture(text, derivative=True)
    assert english_report_context.check(selected['reports'][0], {}) is None


def test_recognizable_heading_with_unknown_category_remains_incomplete():
    selected, scope = fixture('AUDIT COMMITTEE REPORT FOR THE YEAR 2011\nUnreviewed.', derivative=True)
    scope['reports'][0]['facts'] = {k: deepcopy(UNKNOWN) for k in report_scope.FACTS}
    assert direct(selected, scope)['status'] == 'INCOMPLETE_SOURCE_READING'


def test_old_conservative_cue_is_preserved():
    text = 'Historical cue: AUDITORS’ REPORT CONSOLIDATED FINANCIAL STATEMENTS quoted here.'
    selected, _ = fixture(text, derivative=True)
    assert english_report_context.check(selected['reports'][0], {})['status'] == 'UNRECOGNIZED_OR_CHANGED_SOURCE_READING'
