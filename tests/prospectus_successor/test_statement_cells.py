"""Original-source statement readings must survive actual product consumption."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import statement_cells
from legalmath.prospectus.successor.contracts import digest

FIXTURE = Path(__file__).parent / "fixtures/bes_statement_cells.json.gz"


def fixture():
    retained = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    graph = retained["graph"]
    supplied = {"version": "source-statement-cells.v1", "profile": "bes-9m10-statement-cells.v1",
                "document": "bes-release-9m10", "graph_sha256": digest(graph),
                "review": {"kind": "DEVELOPMENT", "reviewer": "retained source review",
                           "reason": "Corrected original 9M2010 finite reading"},
                "reading": retained["reading"]}
    return graph, supplied


def test_complete_real_reading_preserves_source_meaning():
    graph, supplied = fixture()
    output = statement_cells.explain(statement_cells.admit(graph, supplied))
    assert len(output["rows"]) == 77
    assert sum(len(r["cells"]) for r in output["rows"]) == 203
    ecb, = [r for r in output["rows"] if r["label"] == "(ow, ECB)"]
    assert [c["magnitude"] for c in ecb["cells"]] == [1071215, 2005438, 4506647]
    assert [c["value"] for c in ecb["cells"]] == [None, None, None]
    assert ecb["non_additive"] and ecb["parent_row"] == "central_bank_deposits"
    assert sum(c["status"] == "PRINTED_DASH_UNKNOWN" for r in output["rows"] for c in r["cells"]) == 23
    assert output["source_context"]["title_difference"] == {"prospectus": "9H10", "release": "9M10", "silently_corrected": False}
    assert output["source_context"]["unaudited_source"]
    assert output["source_context"]["incorporation_status"] == "UNRESOLVED"
    assert output["consumed"] and not output["independent_financial_acceptance"]
    output["rows"].clear()
    assert len(supplied["reading"]["rows"]) == 77


@pytest.mark.parametrize("change", ["cell", "ecb", "dash", "period", "parent", "qualification", "omission"])
def test_altered_meaning_cannot_be_promoted_as_reviewed(change):
    graph, supplied = fixture()
    rows = supplied["reading"]["rows"]
    ecb = next(r for r in rows if r["label"] == "(ow, ECB)")
    if change == "cell": rows[0]["cells"][0]["value"] += 1
    elif change == "ecb": ecb["cells"][0]["value"] = -1071215
    elif change == "dash": next(c for r in rows for c in r["cells"] if c["value"] is None and c["status"] == "PRINTED_DASH_UNKNOWN")["value"] = 0
    elif change == "period": rows[0]["cells"][0]["period"] = "2010-01-01"
    elif change == "parent": ecb["parent_row"] = "cash"
    elif change == "qualification": supplied["reading"]["source_context"]["unaudited_source"] = False
    else: rows.pop()
    with pytest.raises(ValueError, match="reading differs"):
        statement_cells.admit(graph, supplied)


@pytest.mark.parametrize("change", ["raw", "word", "geometry", "missing", "hidden", "edition", "duplicate"])
def test_rehashed_graph_does_not_hide_changed_original_source(change):
    graph, supplied = fixture()
    unit = graph["units"][0]
    if change == "raw": unit["raw"] += " altered"
    elif change == "word": unit["words"][0]["start"] += 1
    elif change == "geometry": unit["bbox"][0] += 1
    elif change == "missing": graph["units"].pop()
    elif change == "hidden": unit["visible"] = False
    elif change == "edition": unit["source_sha256"] = "0" * 64
    else: graph["units"].append(deepcopy(unit))
    supplied["graph_sha256"] = digest(graph)
    with pytest.raises(ValueError, match="original pages|Duplicate"):
        statement_cells.admit(graph, supplied)


def test_unsupported_profile_and_stale_graph_refuse():
    graph, supplied = fixture()
    supplied["profile"] = "arbitrary-table"
    with pytest.raises(ValueError, match="Unsupported"):
        statement_cells.admit(graph, supplied)
    graph, supplied = fixture()
    supplied["graph_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="graph changed"):
        statement_cells.admit(graph, supplied)


def q1_fixture():
    retained = json.loads(gzip.decompress((FIXTURE.parent / "bes_q1_statement_cells.json.gz").read_bytes()))
    graph = retained["graph"]
    supplied = {"version": "source-statement-cells.v1", "profile": "bes-q111-statement-cells.v1",
                "document": "bes-release-q111", "graph_sha256": digest(graph),
                "review": {"kind": "DEVELOPMENT", "reviewer": "retained source review",
                           "reason": "Original Q1 2011 finite reading"}, "reading": retained["reading"]}
    return graph, supplied


def test_q1_preserves_its_own_table_form_and_memoranda():
    graph, supplied = q1_fixture()
    output = statement_cells.explain(statement_cells.admit(graph, supplied))
    assert len(output["rows"]) == 78 and sum(len(r["cells"]) for r in output["rows"]) == 206
    assert output["tables"] == supplied["reading"]["tables"] and "headers" not in output
    assert output["tables"]["36"]["measure"] == "STOCK_AT_DATE"
    assert output["tables"]["37"]["measure"] == "QUARTER_FLOW"
    memo = [r for r in output["rows"] if r["role"] == "MEMORANDUM_QUANTITY"]
    assert len(memo) == 2 and len({r["parent_row"] for r in memo}) == 2
    assert all(c["value"] is None and c["magnitude"] > 0 for r in memo for c in r["cells"])
    assert sum(c["status"] == "PRINTED_DASH_UNKNOWN" for r in output["rows"] for c in r["cells"]) == 22
    assert output["source_context"]["source_authenticity"] == "NOT_ESTABLISHED"
    assert not output["source_context"]["independent_financial_review"]


@pytest.mark.parametrize("change", ["negative_ecb", "lost_cell", "other_table", "wrong_profile", "changed_geometry"])
def test_q1_source_and_semantics_cannot_cross_profiles(change):
    graph, supplied = q1_fixture()
    if change == "negative_ecb":
        c = next(r for r in supplied["reading"]["rows"] if r["role"] == "MEMORANDUM_QUANTITY")["cells"][0]
        c["value"] = -c["magnitude"]
    elif change == "lost_cell": supplied["reading"]["rows"][0]["cells"].pop()
    elif change == "other_table": supplied["reading"] = fixture()[1]["reading"]
    elif change == "wrong_profile": supplied["profile"] = "bes-9m10-statement-cells.v1"
    else:
        graph["units"][0]["bbox"][0] += 1
        supplied["graph_sha256"] = digest(graph)
    with pytest.raises(ValueError, match="reading differs|Unsupported|original pages"):
        statement_cells.admit(graph, supplied)


def fy_fixture():
    retained = json.loads(gzip.decompress((FIXTURE.parent / "bes_fy2010_statement_cells.json.gz").read_bytes()))
    graph = retained["graph"]
    supplied = {"version": "source-statement-cells.v1", "profile": "bes-fy2010-statement-cells.v1",
                "document": "bes-release-fy10", "graph_sha256": digest(graph),
                "review": {"kind": "DEVELOPMENT", "reviewer": "retained source review",
                           "reason": "Original FY2010 finite reading"}, "reading": retained["reading"]}
    return graph, supplied


def test_fy2010_preserves_annual_periods_signed_memorandum_and_unknowns():
    graph, supplied = fy_fixture()
    output = statement_cells.explain(statement_cells.admit(graph, supplied))
    assert len(output["rows"]) == 76 and sum(len(r["cells"]) for r in output["rows"]) == 200
    assert output["tables"] == supplied["reading"]["tables"]
    assert output["tables"]["41"]["periods"] == ["2009-12-31", "2010-06-30", "2010-12-31"]
    assert output["tables"]["42"]["measure"] == "ANNUAL_FLOW"
    assert output["tables"]["42"]["periods"] == ["year_ended_2009-12-31", "year_ended_2010-12-31"]
    memo, = [r for r in output["rows"] if r["non_additive"]]
    assert memo["role"] == "MEMORANDUM_SIGNED" and memo["parent_row"] == "p42-r25"
    assert [c["value"] for c in memo["cells"]] == [-10326, -9036]
    assert sum(c["status"] == "PRINTED_DASH_UNKNOWN" for r in output["rows"] for c in r["cells"]) == 23
    tax, = [r for r in output["rows"] if r["label"] == "Current income tax liabilities"]
    assert tax["cells"][2]["value"] == 25324
    assert all(c["unit"] == "EUR_thousands" for r in output["rows"] for c in r["cells"])
    assert output["source_context"]["unaudited_source"]
    assert output["source_context"]["context_pages_do_not_expand_incorporation"]
    assert output["source_context"]["incorporation_status"] == "UNRESOLVED"
    assert output["consumed"] and not output["independent_financial_acceptance"]


@pytest.mark.parametrize("change", ["quarter", "tax", "dash", "additive", "negated_expense", "qualification", "q1_profile", "geometry"])
def test_fy2010_refuses_financial_meaning_and_edition_changes(change):
    graph, supplied = fy_fixture()
    reading = supplied["reading"]
    if change == "quarter": reading["tables"]["42"]["measure"] = "QUARTER_FLOW"
    elif change == "tax": next(r for r in reading["rows"] if r["label"] == "Current income tax liabilities")["cells"][2]["value"] = 225324
    elif change == "dash": next(c for r in reading["rows"] for c in r["cells"] if c["value"] is None)["value"] = 0
    elif change == "additive": next(r for r in reading["rows"] if r["non_additive"])["non_additive"] = False
    elif change == "negated_expense": next(r for r in reading["rows"] if r["role"] == "EXPENSE")["cells"][0]["value"] *= -1
    elif change == "qualification": reading["source_context"]["unaudited_source"] = False
    elif change == "q1_profile": supplied["profile"] = "bes-q111-statement-cells.v1"
    else:
        graph["units"][0]["bbox"][0] += 1
        supplied["graph_sha256"] = digest(graph)
    with pytest.raises(ValueError, match="reading differs|Unsupported|original pages"):
        statement_cells.admit(graph, supplied)
