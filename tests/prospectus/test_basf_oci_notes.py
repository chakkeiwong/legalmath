"""Distinguish literal sign, prose decrease, missing amount and accounting scope."""
import pytest
from legalmath.prospectus.basf_oci_notes import monetary, scoped_comparison
from legalmath.prospectus.basf_equity import amount


@pytest.mark.parametrize('literal,direction,expected', [('€33',-1,-33),('€329',-1,-329),
    ('€37',1,37),('–€381',1,-381),('–€1,256',1,-1256)])
def test_direction_comes_from_a_printed_sign_or_the_bound_prose(literal,direction,expected):
    result = monetary(literal,direction)
    assert result['integer_millions'] == expected
    assert result['literal'] == literal


@pytest.mark.parametrize('literal,direction', [('–€33',-1),('€–',1),('33',1),('€1,20',1),('€33',True)])
def test_do_not_invent_or_reverse_an_amount(literal,direction):
    with pytest.raises(ValueError):
        monetary(literal,direction)


def test_equal_numbers_with_different_scope_do_not_establish_equality():
    result = scoped_comparison('components',[amount('7')],[amount('7')],
                               matched_scope=False,explanation='Different aggregates.')
    assert result['status'] == 'SCOPE_EQUIVALENCE_NOT_ESTABLISHED'
    assert result['left_minus_right'] is None


def test_actual_hedge_difference_is_not_corrected_or_tolerated_away():
    result = scoped_comparison('hedge',[monetary('€33',-1)],[amount('84'),amount('–116')],
                               matched_scope=True,explanation='Supplied net movement comparison.')
    assert result['status'] == 'PRINTED_DIFFERENCE'
    assert result['left_minus_right'] == -1
    assert result['role'] == 'EXPLANATORY_ONLY'


def test_a_printed_dash_remains_unknown_even_when_scope_is_supplied():
    result = scoped_comparison('unknown',[amount('868')],[amount('–')],
                               matched_scope=True,explanation='Illustration of unavailable amount.')
    assert result['status'] == 'UNKNOWN_COMPONENT'
    assert result['left_minus_right'] is None
