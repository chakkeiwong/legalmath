"""The optional annual v2 profile carries the reviewed capital notes."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import statement_cells
from legalmath.prospectus.successor.contracts import digest


FIXTURE = Path(__file__).parent / "fixtures/bes_annual2010_statement_cells_v2.json.gz"


def fixture():
    retained = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    graph = retained["graph"]
    supplied = {
        "version": "source-statement-cells.v1",
        "profile": "bes-annual2010-statements-capital-notes.v2",
        "document": "bes-2010-en",
        "graph_sha256": digest(graph),
        "review": {"kind": "DEVELOPMENT", "reviewer": "retained source reviews",
                   "reason": "Combined annual primary/EPS/cash and capital-note readings"},
        "reading": retained["reading"],
    }
    return graph, supplied


def test_combined_profile_exposes_old_readings_and_capital_notes():
    graph, supplied = fixture()
    output = statement_cells.explain(statement_cells.admit(graph, supplied))
    assert len(graph["units"]) == 1817
    assert {u["page"] for u in graph["units"]} == {
        92, 93, 94, 95, 96, 108, 109, 114, 129, 130, 158, 159, 160, 161
    }
    assert output["primary_statements"] == supplied["reading"]["primary_statements"]
    assert output["eps_cash_notes"] == supplied["reading"]["eps_cash_notes"]
    assert output["capital_notes"] == supplied["reading"]["capital_notes"]
    assert output["capital_notes"]["profile"]["reading"]["context"]["count"] == 646
    assert output["capital_notes"]["analysis"]["call_dates_not_maturities"]
    assert output["consumed"] and not output["independent_financial_acceptance"]
    assert output["source_context"]["source_pages"] == sorted({u["page"] for u in graph["units"]})
    assert output["source_context"]["incorporation_status"] == "UNRESOLVED"
    assert not output["capital_notes"]["profile"]["limits"]["production_integration"]


def test_combined_context_changes_only_scope_and_page_inventory():
    graph, supplied = fixture()
    output = statement_cells.explain(statement_cells.admit(graph, supplied))
    old = output["source_context"]
    assert old["source_authenticity"] == "NOT_ESTABLISHED"
    assert old["independent_financial_review"] is False
    assert old["all_notes_read"] is False
    assert "policies2.8–2.9" in old["scope"] and "Notes35/37" in old["scope"]
    assert "historical_flags" in old


@pytest.mark.parametrize("change", ["capital", "old", "authority", "omission"])
def test_combined_profile_refuses_changed_meaning(change):
    graph, supplied = fixture()
    reading = supplied["reading"]
    if change == "capital":
        reading["capital_notes"]["analysis"]["call_dates_not_maturities"] = False
    elif change == "old":
        reading["eps_cash_notes"]["analysis"]["conflict_finding"] = "No discrepancy"
    elif change == "authority":
        reading["source_context"]["independent_financial_review"] = True
    else:
        del reading["capital_notes"]["profile"]["reading"]["sections"]
    with pytest.raises(ValueError, match="reading differs"):
        statement_cells.admit(graph, supplied)


def test_combined_profile_refuses_changed_source_geometry():
    graph, supplied = fixture()
    graph = deepcopy(graph)
    graph["units"][0]["bbox"][0] += 1
    supplied["graph_sha256"] = digest(graph)
    with pytest.raises(ValueError, match="original pages"):
        statement_cells.admit(graph, supplied)
