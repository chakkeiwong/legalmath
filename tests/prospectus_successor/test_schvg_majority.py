"""Source-specific majority arithmetic and exposed-premise regression checks."""
from copy import deepcopy
from itertools import product
import pytest

from scripts.prospectus_majority_oracle import classify, projection, scenarios
from legalmath.prospectus import schvg_majority as subject


@pytest.mark.parametrize('row', scenarios('bond'), ids=lambda r: r['id'])
def test_reviewed_boundaries_match_independent_integer_oracle(row):
    actual = subject.analyze(row, 'bond')
    assert projection(actual) == classify(row)
    assert actual['effective_amendment'] == 'NOT_ESTABLISHED'
    assert actual['historical_applicability'] == 'NOT_ESTABLISHED'


def test_all_numbered_classifications_and_open_premises():
    count = 0
    for number, essential, eligibility, applies, votes in product(
            [None, 'NONE', *range(1, 11)], [False, True, None, 'conflict'],
            [False, True, None, 'conflict'], [False, True, None, 'conflict'],
            [None, '0', '50', '60', '75', '100']):
        row = deepcopy(scenarios('bond')[1])
        row.update(subject=number, essential_change=essential, eligible_totals=eligibility, readings_apply=applies)
        row['totals']['in_favor'] = votes
        assert projection(subject.analyze(row, 'bond')) == classify(row)
        count += 1
    assert count == 4608


@pytest.mark.parametrize('field,value', [('subject', True), ('subject', 11), ('subject', '8'),
    ('essential_change', 1), ('eligible_totals', 'yes'), ('readings_apply', [])])
def test_untyped_classifications_are_refused(field, value):
    row = deepcopy(scenarios('bond')[1]); row[field] = value
    with pytest.raises(ValueError):
        subject.analyze(row, 'bond')


@pytest.mark.parametrize('field,value', [('in_favor', '-1'), ('in_favor', 'NaN'), ('in_favor', '1e2'),
    ('in_favor', '101'), ('in_favor', 75), ('participating', '1'*129),
    ('instrument_id', 'other'), ('event_id', 'other'), ('unit', 'outstanding-principal')])
def test_invalid_totals_and_denominators_are_refused(field, value):
    row = deepcopy(scenarios('bond')[1]); row['totals'][field] = value
    with pytest.raises(ValueError):
        subject.analyze(row, 'bond')
