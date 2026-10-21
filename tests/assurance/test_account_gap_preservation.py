from copy import deepcopy
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.phased.account_gap_preservation import preserve


def gap(locator='FN1', index='document-a', status='NOT_VERIFIED_IN_DELIVERED_RECORDS'):
    return dict(index_hash=index, locator=locator, status=status)


def test_new_gaps_preserve_old_objects_and_allow_order_changes():
    required = [gap(), gap('P10')]
    actual = [gap('FN4'), gap('P10'), gap()]
    before = deepcopy(actual)
    assert preserve(required, actual) == before
    assert actual == before


@pytest.mark.parametrize('actual', [[], [gap('FN2')], [gap(index='document-b')],
    [gap(status='VERIFIED')], [gap(), gap()]])
def test_missing_altered_or_duplicate_gaps_are_rejected(actual):
    with pytest.raises(LegalMathError):
        preserve([gap()], actual)
