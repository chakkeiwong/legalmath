"""Temporal input validity and downstream refusal, not historical legal truth."""
from copy import deepcopy

import pytest

from legalmath.prospectus.successor import anchors, construction_ast, law_facts
from legalmath.prospectus.successor.contracts import timestamp
from test_adoption import graph_anchors
from test_ratio_facts import world, answer
from test_successor import request, legal_inputs, TIME

PAST = '2025-12-31T00:00:00Z'
FUTURE = '2026-01-02T00:00:00Z'
BAD = [False, 0, 0.0, '', [], {}, True, 1, ['2027-01-01'],
       'not-a-date', '2026-01-01', '2026-01-01T00:00:00', '2026-02-30T00:00:00Z']


@pytest.mark.parametrize('field', ['valid_from', 'known_from', 'valid_until', 'known_until'])
@pytest.mark.parametrize('value', BAD)
def test_malformed_endpoints_refused_even_for_inactive_rows(field, value):
    row = {'valid_from': FUTURE, 'known_from': FUTURE, field: value}
    with pytest.raises(ValueError):
        anchors.in_period(row, timestamp(TIME), timestamp(TIME))


@pytest.mark.parametrize('field', ['valid_from', 'known_from'])
def test_required_start_cannot_be_null(field):
    with pytest.raises(ValueError, match='timestamp string'):
        anchors.in_period({'valid_from': TIME, 'known_from': TIME, field: None},
                          timestamp(TIME), timestamp(TIME))


@pytest.mark.parametrize('endings', [{}, {'valid_until': None}, {'known_until': None},
                                    {'valid_until': None, 'known_until': None}])
def test_omitted_and_null_ends_preserve_open_behavior(endings):
    row = {'valid_from': TIME, 'known_from': TIME, **endings}
    before = deepcopy(row)
    assert anchors.in_period(row, timestamp(FUTURE), timestamp(FUTURE))
    assert row == before


@pytest.mark.parametrize('field,at,expected', [
    ('valid_from', TIME, True), ('valid_from', FUTURE, False),
    ('known_from', TIME, True), ('known_from', FUTURE, False),
    ('valid_until', TIME, False), ('valid_until', FUTURE, True),
    ('known_until', TIME, False), ('known_until', FUTURE, True),
    ('valid_until', '2026-01-01T01:00:00+01:00', False),
    ('known_until', '2025-12-31T19:00:00-05:00', False),
    ('valid_from', '2026-01-01T08:00:00+08:00', True),
    ('known_from', '2025-12-31T19:00:00-05:00', True),
])
def test_independently_specified_half_open_boundaries(field, at, expected):
    row = {'valid_from': PAST, 'known_from': PAST, field: at}
    assert anchors.in_period(row, timestamp(TIME), timestamp(TIME)) is expected


@pytest.mark.parametrize('field', ['valid_until', 'known_until'])
@pytest.mark.parametrize('target', ['basis', 'fact'])
@pytest.mark.parametrize('value', BAD)
def test_law_refuses_malformed_ends(tmp_path, field, target, value):
    r = request(tmp_path, ['A hypothetical conditional authority.'])
    graph, basis, facts = legal_inputs(r, tmp_path)
    (basis if target == 'basis' else facts[0])[field] = value
    with pytest.raises(ValueError):
        law_facts.assess(r['bundle'], [basis], facts, graph)


@pytest.mark.parametrize('field', ['valid_until', 'known_until'])
@pytest.mark.parametrize('target', ['basis', 'rule', 'numerator', 'denominator'])
@pytest.mark.parametrize('value', [False, 0, '', [], {}])
def test_ratio_refuses_malformed_ends_through_consumer(tmp_path, field, target, value):
    products, data, _ = world(tmp_path)
    calculation = data['ratio_facts'][0]
    row = data['law_bases'][0] if target == 'basis' else calculation if target == 'rule' else calculation[target]
    row[field] = value
    with pytest.raises(ValueError):
        answer(products, data, tmp_path)


@pytest.mark.parametrize('field', ['valid_until', 'known_until'])
@pytest.mark.parametrize('value', BAD)
def test_amendment_cannot_gain_open_validity_from_malformed_end(tmp_path, field, value):
    graph, a = graph_anchors(tmp_path, ['Old condition', 'Replacement', 'Authority'])
    change = {'id': 'change', 'kind': 'Override', 'target': 'old', 'replacement': 'new',
              'source': a[2], 'authority': a[2], 'reason': 'Supplied hypothetical amendment',
              'valid_from': TIME, 'known_from': TIME, field: value}
    spec = {'version': 'contract-ast.v2', 'root': 'change', 'nodes': [
        {'id': 'old', 'kind': 'Text', 'source': a[0]},
        {'id': 'new', 'kind': 'Text', 'source': a[1]}, change]}
    with pytest.raises(ValueError):
        construction_ast.render(graph, spec)
