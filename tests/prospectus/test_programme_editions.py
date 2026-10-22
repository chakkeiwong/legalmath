"""Semantic screens: publication dates are not correction target dates."""
import pytest
from legalmath.prospectus.programme_editions import period, printed_date, screen_editions


def test_distinct_editions_and_issuers():
    rows = [{'document': 'old', 'issuer': 'JICA', 'date': '2025-08-07'},
            {'document': 'new', 'issuer': 'JICA', 'date': '2026-08-06'},
            {'document': 'other', 'issuer': 'OTHER', 'date': '2025-08-07'}]
    result = screen_editions('2025-08-07', 'JICA', rows)
    assert result['target_state'] == 'COMPATIBLE_CANDIDATE'
    assert [r['status'] for r in result['candidates']] == [
        'EDITION_COMPATIBLE_REQUIRES_REVIEW', 'EDITION_MISMATCH', 'ISSUER_MISMATCH']
    assert result['accepted_relations'] == [] and not result['legal_effect_established']


def test_missing_and_ambiguous_remain_unaccepted():
    old = {'document': 'old', 'issuer': 'JICA', 'date': '2025-08-07'}
    assert screen_editions('2025-08-07', 'JICA', [])['target_state'] == 'MISSING_TARGET'
    result = screen_editions('2025-08-07', 'JICA', [old, old.copy()])
    assert result['target_state'] == 'AMBIGUOUS_TARGET' and not result['accepted_relations']


def test_dates_keep_calendar_and_period_distinctions():
    assert printed_date('2025 年 8 月 7 日') == '2025-08-07'
    actual = period('2025年8月8日から2026年8月6日まで')
    assert (actual['start'], actual['end']) == ('2025-08-08', '2026-08-06')


@pytest.mark.parametrize('text', ['2025年2月29日', '2025年13月1日', '2025年8月7日付',
    '2025年8月8日から2027年8月7日まで', '2025-08-07', '2025年8月7日 2026年8月6日'])
def test_non_date_or_invalid_date_refused(text):
    with pytest.raises(ValueError):
        printed_date(text)


def test_reverse_period_refused():
    with pytest.raises(ValueError):
        period('2026年8月8日から2025年8月7日まで')
