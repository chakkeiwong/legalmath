"""Retain annual statement contradictions and cash limits through the adapter."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import statement_cells
from legalmath.prospectus.successor.contracts import digest


FIXTURE = Path(__file__).parent / "fixtures/bes_annual2010_statement_cells.json.gz"


def fixture():
    retained = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    graph = retained["graph"]
    supplied = {
        "version": "source-statement-cells.v1",
        "profile": "bes-annual2010-statements-notes.v1",
        "document": "bes-2010-en", "graph_sha256": digest(graph),
        "review": {"kind": "DEVELOPMENT", "reviewer": "retained source review",
                   "reason": "Original annual statements and EPS/cash notes"},
        "reading": retained["reading"],
    }
    return graph, supplied


def consume(supplied, graph):
    return statement_cells.explain(statement_cells.admit(graph, supplied))


def test_complete_nested_reading_preserves_source_and_authority_limits():
    graph, supplied = fixture()
    output = consume(supplied, graph)
    assert len(graph["units"]) == 1171
    assert {u["page"] for u in graph["units"]} == {92, 93, 94, 95, 96, 114, 129, 130}
    for key, value in supplied["reading"].items():
        assert output[key] == value
    assert output["consumed"]
    assert output["origin"] == "SUPPLIED_DEVELOPMENT_READING"
    assert not output["independent_financial_acceptance"]
    assert output["legal_dependency_resolution"] == "UNCHANGED"
    assert output["source_context"]["incorporation_status"] == "UNRESOLVED"
    assert not output["source_context"]["all_notes_read"]
    assert not output["source_context"]["independent_financial_review"]
    for key in ("primary_statements", "eps_cash_notes"):
        assert not output[key]["profile"]["limits"]["production_integration"]
        assert not output[key]["profile"]["limits"]["independent_acceptance"]


def test_eps_contradiction_keeps_both_figures_and_selects_no_correction():
    graph, supplied = fixture()
    output = consume(supplied, graph)
    ratios = output["eps_cash_notes"]["analysis"]["ratios"]
    current, = [r for r in ratios if r["year"] == 2010]
    prior, = [r for r in ratios if r["year"] == 2009]
    assert current["primary_basic"]["value"] == current["note_EPS"]["value"] == "0.41"
    assert prior["primary_basic"]["value"] == "0.45"
    assert prior["primary_diluted"]["value"] == prior["note_EPS"]["value"] == "0.49"
    assert prior["exact_ratio"] == [244317, 499087]
    assert prior["rounded_HALF_UP_2dp"] == "0.49"
    assert prior["source_conflict"] and not prior["primary_basic_matches"]
    assert not prior["official_correction_selected"]
    assert not output["eps_cash_notes"]["analysis"]["limitations"]["IAS33_compliance_checked"]


def test_unknown_cells_are_not_imputed_and_all_primary_tables_survive():
    graph, supplied = fixture()
    primary = consume(supplied, graph)["primary_statements"]
    tables = primary["profile"]["reading"]["tables"]
    assert set(tables) == {"income", "comprehensive", "assets", "liabilities", "equity", "equity_changes", "cash_flow"}
    cells = [c for table in tables.values() for row in table["rows"] for c in row["cells"]]
    assert len(cells) == 613
    unknown = [c for c in cells if c["status"] in {"DASH_UNKNOWN", "BLANK_UNKNOWN"}]
    assert Counter(c["status"] for c in unknown) == {"DASH_UNKNOWN": 212, "BLANK_UNKNOWN": 6}
    assert all(c["value"] is None for c in unknown)


def test_cash_scope_printed_date_and_maintenance_period_remain_distinct():
    graph, supplied = fixture()
    analysis = consume(supplied, graph)["eps_cash_notes"]["analysis"]
    cash = analysis["cash_definition"]
    assert cash["maturity"] == "less than three months"
    assert cash["measured_from"] == "inception date" and not cash["remaining_maturity_used"]
    assert cash["restricted_Central_Bank_balances_excluded"]
    assert not cash["all_bank_deposits_assumed_unrestricted"]
    differences = analysis["restricted_mandatory_comparisons"]
    assert [(r["year"], r["Group_restricted_magnitude_minus_Bank_of_Portugal_mandatory"])
            for r in differences] == [(2010, 30866), (2009, 28092)]
    assert all(not r["equal_scope_assumed"] and not r["difference_cause_identified"] for r in differences)
    reserve = analysis["historical_reserve_description"]
    assert reserve["interest_rate_percent"] == {"2010-12-31": "1.00", "2008-12-31": "1.27"}
    assert reserve["maintenance_period"] == ["2010-12-08", "2011-01-18"]
    assert reserve["average_mandatory_reserve_EUR_million"] == 577
    assert not reserve["average_is_closing_balance"]
    assert not reserve["report_legal_description_independently_checked"]
    assert not reserve["current_law_verified"]


def test_input_admission_and_explanation_do_not_share_nested_mutable_state():
    graph, supplied = fixture()
    original = deepcopy(supplied)
    admitted = statement_cells.admit(graph, supplied)
    supplied["reading"]["primary_statements"]["profile"]["reading"]["tables"].clear()
    supplied["reading"]["eps_cash_notes"]["analysis"]["ratios"].clear()
    assert admitted["reading"] == original["reading"]
    protected = deepcopy(admitted)
    output = statement_cells.explain(admitted)
    output["primary_statements"]["profile"]["reading"]["tables"].clear()
    output["eps_cash_notes"]["analysis"]["ratios"].clear()
    output["source_context"]["source_pages"].clear()
    output["review"]["reviewer"] = "changed"
    assert admitted == protected


@pytest.mark.parametrize("change", ["EPS", "conflict", "unknown", "cash", "omission", "date", "authority"])
def test_altered_financial_meaning_is_not_admitted(change):
    graph, supplied = fixture()
    reading = supplied["reading"]
    analysis = reading["eps_cash_notes"]["analysis"]
    if change == "EPS":
        next(r for r in analysis["ratios"] if r["year"] == 2009)["primary_basic"]["value"] = "0.49"
    elif change == "conflict":
        analysis["conflict_finding"] = "No discrepancy"
    elif change == "unknown":
        tables = reading["primary_statements"]["profile"]["reading"]["tables"]
        next(c for t in tables.values() for r in t["rows"] for c in r["cells"] if c["value"] is None)["value"] = 0
    elif change == "cash":
        analysis["cash_definition"]["restricted_Central_Bank_balances_excluded"] = False
    elif change == "omission":
        del reading["eps_cash_notes"]["profile"]["reading"]["sections"]["Note14"]
    elif change == "date":
        analysis["historical_reserve_description"]["interest_rate_percent"] = {"2010-12-31": "1.00", "2009-12-31": "1.27"}
    else:
        reading["source_context"]["independent_financial_review"] = True
    with pytest.raises(ValueError, match="reading differs"):
        statement_cells.admit(graph, supplied)


@pytest.mark.parametrize("change", ["raw", "word", "geometry", "missing", "hidden", "duplicate", "edition"])
def test_rehashed_graph_cannot_replace_original_source_occurrences(change):
    graph, supplied = fixture()
    unit = graph["units"][0]
    if change == "raw": unit["raw"] += " altered"
    elif change == "word": unit["words"][0]["start"] += 1
    elif change == "geometry": unit["bbox"][0] += 1
    elif change == "missing": graph["units"] = [u for u in graph["units"] if u["page"] != 130]
    elif change == "hidden": unit["visible"] = False
    elif change == "duplicate": graph["units"].append(deepcopy(unit))
    else: unit["source_sha256"] = "0" * 64
    supplied["graph_sha256"] = digest(graph)
    with pytest.raises(ValueError, match="original pages|Duplicate"):
        statement_cells.admit(graph, supplied)


def test_stale_admitted_evidence_is_rejected():
    graph, supplied = fixture()
    admitted = statement_cells.admit(graph, supplied)
    admitted["reading"]["eps_cash_notes"]["analysis"]["ratios"].clear()
    with pytest.raises(ValueError, match="evidence changed"):
        statement_cells.explain(admitted)
