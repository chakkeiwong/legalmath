"""Exact enclosure boundary, scaling and unknown-value invariants."""
from fractions import Fraction
from itertools import product

import pytest

from legalmath.prospectus.rounding_enclosure import enclose, rational


@pytest.mark.parametrize('residual,excluded', [(2, False), (-2, False), (3, True), (-3, True), (0, False)])
def test_closed_boundaries_and_sign_symmetry(residual, excluded):
    result = enclose([residual, 0, 0, 0], [1, -1, -1, -1], ['1/2'] * 4)
    assert result['underlying_residual_enclosure'] == [str(residual - 2), str(residual + 2)]
    assert (result['rounding_only_explanation'] == 'EXCLUDED_UNDER_ASSUMPTIONS') is excluded
    assert result['actual_rounding_cause_established'] is False


def test_enclosure_contains_every_endpoint_under_unequal_errors_and_scaling():
    amounts, coefs, errors = [5, -2, 3], [3, -2, 0], [Fraction(1, 3), Fraction(2, 5), Fraction(7)]
    result = enclose(amounts, coefs, [str(e) for e in errors])
    lo, hi = map(Fraction, result['underlying_residual_enclosure'])
    possible = [sum(c * (d + sign * e) for c, d, sign, e in zip(coefs, amounts, signs, errors))
                for signs in product((-1, 1), repeat=3)]
    assert (lo, hi) == (min(possible), max(possible))


def test_unknown_signed_ceiling_is_not_zero_and_zero_coefficient_is_irrelevant():
    result = enclose([3476, 1496, 1935, None], [1, -1, -1, -1], ['1/2'] * 4)
    assert result['known_residual_part'] == 45 and result['unknown_term_indices'] == [3]
    assert result['displayed_residual'] is None and result['underlying_residual_enclosure'] is None
    assert result['rounding_only_explanation'] == 'UNDETERMINED_UNKNOWN_COMPONENT'
    assert enclose([1, None], [1, 0], [0, 100])['displayed_residual'] == 1


@pytest.mark.parametrize('args', [([], [], []), ([1], [1, 2], [1]), ([True], [1], [1]),
    ([1.0], [1], [1]), ([1], [True], [1]), ([1], [1], [-1]), ([1], [1], [0.5]),
    ([1], [1], ['1/0']), ([1], [1], ['1e2']), ([1], [1], [True])])
def test_invalid_inputs_refuse_instead_of_coercing(args):
    with pytest.raises(ValueError):
        enclose(*args)


def test_rational_reduction_is_exact():
    assert rational('2/6') == Fraction(1, 3)
