"""Pension quantities and prohibited financial inferences remain distinct."""
import pytest
from legalmath.prospectus.basf_pension_note import quantity, comparison, original_span


def test_funding_total_uses_ceiling_and_preserves_gross_assets():
    gross=quantity("20,083","million_eur")
    ceiling=quantity("–431","million_eur")
    total=quantity("19,652","million_eur")
    actual=comparison("funding",[(1,total)],[(1,gross),(1,ceiling)],scope="2022 reported assets after ceiling")
    assert actual["left_minus_right"]==0
    assert gross["value"]==20083 and total["value"]==19652


def test_unknown_ceiling_prevents_prior_year_arithmetic():
    actual=comparison("prior-year",[(1,quantity("23,130","million_eur"))],
        [(1,quantity("23,130","million_eur")),(1,quantity("–","million_eur"))],scope="No imputation")
    assert actual["status"]=="UNKNOWN_COMPONENT" and actual["left_minus_right"] is None


def test_printed_zero_and_dash_are_different():
    assert quantity("0","million_eur")["value"]==0
    assert quantity("–","million_eur")["value"] is None


def test_signed_net_liability_requires_assets_minus_provisions():
    actual=comparison("signed-liability",[(1,quantity("–2,018","million_eur"))],
        [(1,quantity("792","million_eur")),(-1,quantity("2,810","million_eur"))],scope="Source sign convention")
    assert actual["left_minus_right"]==0


def test_rate_unit_is_disclosed_as_supplied():
    actual=quantity("3.70","supplied_rate_percent")
    assert actual["value"]=="3.70" and actual["unit_basis"]=="SUPPLIED_CONVENTIONAL_RATE_UNIT_NOT_PRINTED"


@pytest.mark.parametrize("literal,kind",[("3.70","million_eur"),("1,20","million_eur"),("101","percent"),("–1","percent"),("3.7","supplied_rate_percent"),("3.70%","supplied_rate_percent")])
def test_wrong_units_or_unprinted_number_formats_refused(literal,kind):
    with pytest.raises(ValueError):quantity(literal,kind)


def test_percent_cannot_be_added_to_monetary_amount():
    with pytest.raises(ValueError,match="different pension quantity types"):
        comparison("invalid",[(1,quantity("42","percent"))],[(1,quantity("42","million_eur"))],scope="Invalid units")


def test_rates_and_mortality_references_cannot_be_added():
    for kind,literal in (("supplied_rate_percent","3.70"),("text","BVG 2020")):
        with pytest.raises(ValueError,match="not additive"):
            comparison("invalid",[(1,quantity(literal,kind))],[(1,quantity(literal,kind))],scope="Not a sum")


def test_merged_columns_preserve_separator_and_all_original_characters():
    raw="Obligations are discounted on high- The strategy of the BASF Group"
    u={"raw":raw}
    intervals=[original_span(u,"51:"+part) for part in ("left","separator","right")]
    assert [raw[a:b] for a,b in intervals]==["Obligations are discounted on high-"," ","The strategy of the BASF Group"]
    assert "".join(raw[a:b] for a,b in intervals)==raw


def test_unexpected_cross_column_join_refused():
    with pytest.raises(ValueError):original_span({"raw":"Obligation.The strategy continues"},"51:left")


def test_printed_difference_is_retained_without_tolerance():
    actual=comparison("unexplained",[(1,quantity("3,759","million_eur"))],
        [(1,quantity("6,800","million_eur")),(1,quantity("–2,641","million_eur")),(1,quantity("–431","million_eur"))],
        scope="Candidate gross bridge; complete scope not established")
    assert actual["status"]=="PRINTED_DIFFERENCE" and actual["left_minus_right"]==31
    assert actual["role"]=="EXPLANATORY_ONLY"
