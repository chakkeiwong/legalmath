from copy import deepcopy

import pytest

from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.relation_discovery import discover, SCOPED_PROFILE
from test_relation_discovery import example


def graph(rows):
    return {'units': [{'id': f'u{i}', 'document': 'synthetic', 'source_sha256': 'a' * 64,
                       'page': 1, 'order': i, 'raw': text, 'text_sha256': digest(text.encode()),
                       'bbox': box, 'words': []} for i, (text, box) in enumerate(rows)]}


def ratings():
    return graph([
        ('Ratings:', [10, 10, 65, 20]),
        ('These securities have been rated:', [180, 10, 370, 20]),
        ('Agency One: AA-', [180, 25, 290, 35]),
        ('Agency Two: Baa3', [180, 39, 295, 49]),
        ('Intervening agency registration discussion.', [180, 65, 420, 75]),
        ('Its historical position remains uncertain.', [180, 78, 420, 88]),
        ('In general, investors', [180, 110, 280, 120]),
        ('are restricted', [287, 110, 365, 120]),
        ('from using ratings for regulatory purposes unless', [180, 124, 430, 134]),
        ('the stated exception applies.', [180, 138, 365, 148]),
        ('An unrelated later paragraph.', [180, 164, 355, 174]),
        ('3.', [10, 200, 25, 210]),
    ])


def margin():
    return graph([
        ('Folgendes gilt für', [10, 10, 100, 20]),
        ('alle Optionen von', [10, 24, 100, 34]),
        ('Actual/365', [10, 38, 80, 48]),
        ('The reference period begins on the first date', [170, 10, 465, 20]),
        ('and ends immediately before the second date.', [170, 24, 465, 34]),
        ('A separate later paragraph.', [170, 60, 350, 70]),
    ])


def scoped(g):
    return [c for c in discover(g, SCOPED_PROFILE)['candidates'] if c.get('rule')]


def replace(unit, text):
    unit.update(raw=text, text_sha256=digest(text.encode()))


def test_regulatory_qualification_spans_full_exception_and_only_grade_targets():
    g = ratings()
    before = deepcopy(g)
    edge, = scoped(g)
    assert g == before
    assert edge['kind'] == 'qualifies'
    assert [s['unit'] for s in edge['from']] == ['u6', 'u7', 'u8', 'u9']
    assert [s['quote'] for s in edge['to']] == ['Agency One: AA-', 'Agency Two: Baa3']
    assert edge['scope_marker']['quote'] == 'Ratings:'
    assert edge['status'] == 'REQUIRES_REVIEW' and not edge['legal_scope_established']


def test_german_option_name_comes_from_margin_and_body_stops_at_paragraph():
    edge, = scoped(margin())
    assert edge['scope'] == 'all Actual/365 options'
    assert [s['unit'] for s in edge['from']] == ['u0', 'u1', 'u2']
    assert [s['unit'] for s in edge['to']] == ['u3', 'u4']


@pytest.mark.parametrize('factory', [ratings, margin])
def test_scope_candidates_never_admit_relations_or_change_the_graph(factory):
    g = factory()
    before = deepcopy(g)
    result = discover(g, SCOPED_PROFILE)
    assert g == before and not result['accepted_relations'] and not result['legal_scope_inferred']


def test_v1_row_candidates_are_preserved_exactly():
    g = example()
    assert discover(g)['candidates'] == discover(g, SCOPED_PROFILE)['candidates']


@pytest.mark.parametrize('factory', [ratings, margin])
def test_scaling_permutation_and_unseen_document_names_preserve_endpoints(factory):
    g = factory()
    expected = scoped(g)
    g['units'].reverse()
    for u in g['units']:
        u['bbox'] = [2.5 * v + 37 for v in u['bbox']]
    assert scoped(g) == expected
    for u in g['units']:
        u['document'] = 'previously-unseen-synthetic-name'
    actual = scoped(g)
    assert len(actual) == len(expected)
    assert all(s['document'] == 'previously-unseen-synthetic-name'
               for e in actual for key in ('from', 'to') for s in e[key])


@pytest.mark.parametrize('change', ['missing_tail', 'negation', 'competing_label', 'no_grades', 'section_boundary'])
def test_ratings_ambiguity_and_incomplete_exception_refuse_new_edge(change):
    g = ratings()
    if change == 'missing_tail':
        g['units'].pop(9)
    elif change == 'negation':
        replace(g['units'][7], 'are not restricted')
    elif change == 'competing_label':
        replace(g['units'][10], 'Credit Ratings:')
    elif change == 'no_grades':
        replace(g['units'][2], 'not a printed credit grade')
    else:
        g['units'][-1]['bbox'] = [10, 95, 25, 105]
    assert not scoped(g)


@pytest.mark.parametrize('change', ['negation', 'limited_scope', 'competing_body', 'missing_tail'])
def test_margin_does_not_invent_all_option_scope_or_choose_competing_body(change):
    g = margin()
    if change == 'negation':
        replace(g['units'][0], 'Folgendes gilt nicht für')
    elif change == 'limited_scope':
        replace(g['units'][1], 'einzelne Optionen von')
    elif change == 'competing_body':
        extra = deepcopy(g['units'][3])
        extra.update(id='other', order=20, bbox=[600, 10, 800, 20])
        g['units'].append(extra)
    else:
        g['units'].pop(4)
    assert not scoped(g)


@pytest.mark.parametrize('key,value', [('page', 2), ('document', 'other'), ('source_sha256', 'b' * 64)])
def test_ratings_qualification_cannot_cross_source_boundaries(key, value):
    g = ratings()
    for u in g['units'][6:10]:
        u[key] = value
    assert not scoped(g)


@pytest.mark.parametrize('factory', [ratings, margin])
@pytest.mark.parametrize('failure', ['box', 'word_box', 'text', 'duplicate'])
def test_scope_respects_shared_geometry_and_integrity_refusals(factory, failure):
    g = factory()
    if failure == 'box':
        g['units'][0]['bbox'] = None
    elif failure == 'word_box':
        g['units'][0]['words'] = [{'bbox': None}]
    elif failure == 'text':
        g['units'][0]['raw'] += ' changed'
    else:
        g['units'].append(deepcopy(g['units'][0]))
    if failure in {'text', 'duplicate'}:
        with pytest.raises(ValueError):
            scoped(g)
    else:
        assert not scoped(g)


@pytest.mark.parametrize('profile', ['unknown', [], {}])
def test_unknown_profile_is_rejected(profile):
    with pytest.raises(ValueError, match='Unsupported relation discovery'):
        discover(ratings(), profile)
