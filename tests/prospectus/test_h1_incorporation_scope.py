"""Membership invariants; legal correctness is tested by neither set arithmetic nor installation."""
from copy import deepcopy
import pytest
from legalmath.prospectus.h1_incorporation_scope import membership_delta


def test_difference_retains_source_order_and_unchanged_inputs():
    first, second = ["p59:2", "p55:0", "p60:1"], ["p60:1", "p162:0"]
    before = deepcopy((first, second))
    delta = membership_delta(first, second)
    assert delta == {"common": ["p60:1"], "first_only": ["p59:2", "p55:0"], "second_only": ["p162:0"]}
    assert (first, second) == before


def test_identical_sets_with_different_order_do_not_invent_a_difference():
    delta = membership_delta([3,1,2], [2,3,1])
    assert delta["common"] == [3,1,2] and delta["first_only"] == delta["second_only"] == []


@pytest.mark.parametrize("first,second", [([1,1],[1]), ([1],[1,1]), ([1,1],[1,1]), ((1,2),[1]), ([1],(1,2))])
def test_duplicate_or_unordered_contract_does_not_count_as_complete_membership(first, second):
    with pytest.raises(ValueError, match="Unique ordered"):
        membership_delta(first, second)


def test_different_occurrences_on_same_page_remain_distinct():
    first = ["report:p59:l1", "report:p59:l2"]
    delta = membership_delta(first, ["report:p59:l1"])
    assert delta["first_only"] == ["report:p59:l2"]


def test_same_page_and_line_in_different_documents_are_not_collapsed():
    delta = membership_delta(["bank:p59:l1"], ["finance:p59:l1"])
    assert not delta["common"] and delta["first_only"] == ["bank:p59:l1"] and delta["second_only"] == ["finance:p59:l1"]


def test_empty_membership_propagates_without_inventing_source_content():
    assert membership_delta([], []) == {"common": [], "first_only": [], "second_only": []}
    assert membership_delta([1,2], [])["first_only"] == [1,2]
