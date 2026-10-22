"""Focused numerical/source invariants; the full original consumer is separate."""
import pytest

from legalmath.prospectus import h1_cash_flow as note, h1_cash_flow_spec as spec


@pytest.mark.parametrize("literal,expected", [
    ("1 847 043", 1847043), ("(462 200)", -462200), ("0", 0), ("-", None), ("8", 8),
])
def test_signed_thousands_and_unknown_dash(literal, expected):
    value = note.quantity(literal)
    assert value["integer_thousands"] == expected
    assert value["printed"] == literal and value["unit"] == "thousand EUR"
    assert (value["status"] == "PRINTED_DASH_UNKNOWN") == (expected is None)


@pytest.mark.parametrize("raw", ["(7? 424)", "(624.426)", "~ (2123 313)", "1 00", "1e3", "1.5", "(1 000", True])
def test_no_implicit_ocr_repair_or_unit_conversion(raw):
    with pytest.raises(ValueError):
        note.quantity(raw)


def rows():
    return [{"id": row["id"], "cells": {year: {"quantity": {"integer_thousands": 0}} for year in spec.YEARS}}
            for row in spec.ROWS]


def set_value(data, key, year, value):
    next(r for r in data if r["id"] == key)["cells"][year]["quantity"]["integer_thousands"] = value


def check(data, name, year="2010"):
    return next(r for r in note.arithmetic(data) if r["name"] == name and r["year"] == year)


def test_rollforward_uses_exchange_and_repeated_flow_once():
    data = rows()
    for key, value in {"opening-cash": 1000, "exchange-effect": -20, "net-change": -100,
                       "net-change-repeat": -100, "closing-cash": 880}.items():
        set_value(data, key, "2010", value)
    result = check(data, "cash-rollforward")
    assert result["component_sum"] == 880 and result["left_minus_right"] == 0
    assert "net-change" not in result["components"]


def test_known_printed_target_does_not_impute_missing_component():
    data = rows()
    set_value(data, "subsidiaries-disposed", "2010", None)
    result = check(data, "investing-components")
    assert result["status"] == "UNKNOWN_COMPONENT" and result["component_sum"] is None
    assert result["left_minus_right"] is None and result["unknown_components"] == ["subsidiaries-disposed"]


def test_synthetic_discrepancy_is_preserved_not_rounded_away():
    data = rows()
    set_value(data, "closing-cash", "2010", 1)
    result = check(data, "cash-rollforward")
    assert result["left_minus_right"] == 1 and result["status"] == "PRINTED_DIFFERENCE"
    assert result["diagnostic_role"] == "EXPLANATORY_ONLY"


def test_negative_mandatory_deposits_remain_signed_components():
    data = rows()
    for key, value in {"cash": 100, "central-bank-deposits": 500, "mandatory-central-bank": -200,
                       "bank-deposits": 50, "total-cash-components": 450}.items():
        set_value(data, key, "2010", value)
    assert check(data, "cash-components")["left_minus_right"] == 0


def test_shared_ocr_line_partition_retains_separator():
    unit = {"raw": "(4687 606) 6888 625"}
    intervals = [note.span(unit, "ocr126:" + k) for k in ("left", "separator", "right")]
    assert "".join(unit["raw"][a:b] for a, b in intervals) == unit["raw"]
    assert intervals[0][1] == intervals[1][0] and intervals[1][1] == intervals[2][0]
    with pytest.raises(ValueError):
        note.span({"raw": "(4687 606)6888 625"}, "ocr126:left")
