"""Financial distinctions that must survive source reading and comparison."""
import pytest
from legalmath.prospectus.basf_equity import amount, comparison


@pytest.mark.parametrize('raw,marker,value', [('–176 c', 'c', -176), ('9 d', 'd', 9),
                                           ('–281 c', 'c', -281), ('–10 d', 'd', -10)])
def test_superscript_is_a_qualification_not_a_digit(raw, marker, value):
    result = amount(raw, marker)
    assert result['literal'] == raw
    assert result['footnote_marker'] == marker
    assert result['integer_millions'] == value


@pytest.mark.parametrize('raw,marker', [('176', 'c'), ('176 c', None), ('176 d', 'c'),
                                      ('– c', 'c'), ('176c', 'c'), ('176 c d', 'd'), ('176 e', None)])
def test_missing_unknown_or_misassigned_qualification_is_refused(raw, marker):
    with pytest.raises(ValueError):
        amount(raw, marker)


def test_unknown_cannot_be_used_as_zero_to_force_identity():
    unknown = comparison('example', [amount('10'), amount('–')], [amount('10')])
    assert unknown['status'] == 'UNKNOWN_COMPONENT'
    assert unknown['left_minus_right'] is None
    zero = comparison('example', [amount('10'), amount('0')], [amount('10')])
    assert zero['status'] == 'EQUAL_PRINTED_VALUES'


def test_difference_is_reported_without_rounding_tolerance_or_repair():
    result = comparison('example', [amount('3,161')], [amount('–627'), amount('3,787')])
    assert result['status'] == 'PRINTED_DIFFERENCE'
    assert result['left_minus_right'] == 1
    assert result['role'] == 'EXPLANATORY_ONLY'
