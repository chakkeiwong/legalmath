"""Financial-unit and missing-value diagnostics separate from source replay."""
from copy import deepcopy
import pytest
from legalmath.prospectus import h1_risk_tables as risk


@pytest.mark.parametrize("literal,unit,key,expected", [
    ("53 355", "million EUR", "integer_units", 53355),
    ("(24 779)", "thousand EUR", "integer_units", -24779),
    ("-", "thousand EUR", "integer_units", None),
    ("0", "million EUR", "integer_units", 0),
    ("2.82%", "percent", "percent_hundredths", 282),
    ("100.00%", "percent", "percent_hundredths", 10000),
    ("-", "percent", "percent_hundredths", None),
])
def test_signed_amounts_percentages_and_unknowns(literal, unit, key, expected):
    value = risk.quantity(literal, unit)
    assert value[key] == expected and value["unit"] == unit and value["printed"] == literal


@pytest.mark.parametrize("literal,unit", [
    ("2.82%", "million EUR"), ("850", "percent"), ("1%", "percent"),
    ("5.AT%", "percent"), ("101.00%", "percent"), ("MS", "million EUR"),
    ("3.994", "thousand EUR"), ("1 00", "thousand EUR"), (True, "percent"),
    ("1", "EUR"),
])
def test_no_implicit_unit_conversion_or_ocr_correction(literal, unit):
    with pytest.raises(ValueError):
        risk.quantity(literal, unit)


def tables():
    result = []
    for year in ("2010", "2009"):
        col = {"id": "loans-gross", "unit": "thousand EUR", "date": year}
        rows = [{"id": k, "cells": {"loans-gross": {"quantity": risk.quantity(v, "thousand EUR")}}}
                for k, v in (("sector-a", "1 200"), ("sector-b", "2 000"), ("total", "3 200"))]
        result.append({"id": "sectors-" + year, "dates": [year], "rows": rows, "header": {"columns": [col]}})
    cols = [{"id": year + ":" + key, "date": year, "unit": unit}
            for year in ("2010", "2009") for key, unit in (("amount", "million EUR"), ("percent", "percent"))]
    rows = [{"id": key, "group": "group" if key != "total" else None,
        "cells": {c["id"]: {"quantity": risk.quantity(amount if c["unit"] == "million EUR" else percent, c["unit"])} for c in cols}}
        for key, amount, percent in (("rating-a", "1", "33.33%"), ("rating-b", "2", "66.67%"), ("total", "3", "100.00%"))]
    result.append({"id": "ratings", "rows": rows, "header": {"columns": cols},
                   "groups": [{"id": "group", "row_ids": ["rating-a", "rating-b"]}]})
    return result


def test_unknown_component_does_not_become_zero_despite_printed_total():
    data = tables()
    data[0]["rows"][0]["cells"]["loans-gross"]["quantity"] = risk.quantity("-", "thousand EUR")
    row = risk.arithmetic(data)["column_sums"][0]
    assert row["sum"] is None and row["known_component_sum"] == 2000
    assert row["unknown_components"] == ["sector-a"] and row["total_minus_components"] is None


def test_cross_page_conversion_does_not_claim_scope_equivalence():
    row = risk.arithmetic(tables())["cross_page_totals"][0]
    assert row["rating_thousand_eur"] == 3000 and row["sector_minus_rating_thousand_eur"] == 200
    assert row["scope_equivalence_established"] is False and row["rounding_cause_established"] is False


def test_percentage_sums_have_percentage_units():
    result = risk.arithmetic(tables())
    row = next(r for r in result["column_sums"] if r["table"] == "ratings" and r["column"] == "2010:percent")
    assert row["sum"] == 10000 and row["total_minus_components"] == 0
    assert row["unit"] == "hundredth of a percentage point"


def test_printed_discrepancy_is_retained_without_changing_inputs():
    data = tables()
    data[2]["rows"][0]["cells"]["2010:amount"]["quantity"] = risk.quantity("2", "million EUR")
    protected = deepcopy(data)
    result = risk.arithmetic(data)
    row = next(r for r in result["column_sums"] if r["table"] == "ratings" and r["column"] == "2010:amount")
    assert row["total_minus_components"] == -1 and row["status"] == "PRINTED_DIFFERENCE"
    assert data == protected and row["diagnostic_role"] == "EXPLANATORY_ONLY"


def test_amount_ratio_is_exactly_identified_but_rounding_cause_unproved():
    row = risk.arithmetic(tables())["rating_ratios"][0]
    assert row["exact_calculated_percentage_fraction"] == [100, 3]
    assert row["calculated_percentage"] == "33.33333333"
    assert row["printed_minus_calculated_percentage_points"] == "-0.00333333"
    assert row["rounding_cause_established"] is False


def test_group_sum_does_not_include_total_or_other_groups():
    result = risk.arithmetic(tables())
    row = result["rating_group_sums"][0]
    assert row["sum"] == 3 and row["printed_group_total"] is None


def test_unknown_total_never_generates_ratio_or_cross_page_amount():
    data = tables()
    data[2]["rows"][-1]["cells"]["2010:amount"]["quantity"] = risk.quantity("-", "million EUR")
    result = risk.arithmetic(data)
    assert result["rating_ratios"][0]["calculated_percentage"] is None
    assert result["cross_page_totals"][0]["rating_thousand_eur"] is None
