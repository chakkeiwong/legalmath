from copy import deepcopy
import math

import pytest

from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.relation_discovery import discover


def example():
    rows = [("(i)", [10, 10, 20, 20]), ("Code:", [30, 10, 90, 20]),
            ("AB12", [200, 10, 245, 20]),
            ("(ii)", [10, 40, 20, 50]), ("Arrangement:", [30, 40, 110, 50]),
            ("Yes", [200, 40, 230, 50]),
            ("Note that intended use", [200, 55, 330, 65]),
            ("does not establish eligibility.", [200, 68, 350, 78])]
    return {"units": [{"id": str(i), "document": "fixture", "source_sha256": "a" * 64,
                       "page": 1, "order": i, "raw": text, "text_sha256": digest(text.encode()),
                       "bbox": box, "words": []} for i, (text, box) in enumerate(rows)]}


def test_exact_qualifier_and_source_identity_survive_without_legal_admission():
    graph = example()
    before = deepcopy(graph)
    result = discover(graph)
    assert graph == before
    qualifier = next(e for e in result["candidates"] if e["kind"] == "qualifies")
    assert [s["quote"] for s in qualifier["from"]] == [
        "Note that intended use", "does not establish eligibility."]
    assert [s["quote"] for s in qualifier["to"]] == ["Yes"]
    assert all(s["source_sha256"] == "a" * 64 for s in qualifier["from"])
    assert not result["accepted_relations"] and not result["legal_scope_inferred"]


@pytest.mark.parametrize("box", [None, [1, 1, 1, 2]])
def test_unknown_geometry_refuses_entire_page(box):
    graph = example()
    graph["units"][-1]["bbox"] = box
    result = discover(graph)
    assert not result["candidates"]
    assert result["diagnostics"][0]["reason"] == "UNKNOWN_OR_INVALID_PAGE_GEOMETRY"


@pytest.mark.parametrize("value", [math.nan, math.inf])
def test_non_json_geometry_rejected(value):
    graph = example()
    graph["units"][-1]["bbox"] = [0, 0, value, 1]
    with pytest.raises(ValueError, match="JSON compliant"):
        discover(graph)


def test_unknown_word_geometry_cannot_be_hidden_by_line_box():
    graph = example()
    graph["units"][-1]["words"] = [{"bbox": None}]
    assert not discover(graph)["candidates"]


@pytest.mark.parametrize("change", ["duplicate", "text"])
def test_corrupted_source_rejected(change):
    graph = example()
    if change == "duplicate":
        graph["units"].append(deepcopy(graph["units"][0]))
    else:
        graph["units"][-1]["raw"] = "eligibility guaranteed"
    with pytest.raises(ValueError):
        discover(graph)


def test_candidate_identity_uses_source_order_not_input_order():
    graph = example()
    expected = discover(graph)["candidates"]
    graph["units"].reverse()
    assert discover(graph)["candidates"] == expected


@pytest.mark.parametrize("key,value", [("document", "other"), ("page", 2), ("source_sha256", "b" * 64)])
def test_separate_source_pages_do_not_supply_column_support(key, value):
    graph = example()
    for unit in graph["units"][3:]:
        unit[key] = value
    assert not discover(graph)["candidates"]


def test_uniform_geometry_scaling_does_not_change_source_relations():
    graph = example()
    expected = discover(graph)["candidates"]
    for unit in graph["units"]:
        unit["bbox"] = [3 * v + 70 for v in unit["bbox"]]
    assert discover(graph)["candidates"] == expected


def test_overlapping_column_content_is_ambiguous():
    graph = example()
    graph["units"][-1]["bbox"][0] = 80
    result = discover(graph)
    assert all(e["row_marker"]["quote"] != "(ii)" for e in result["candidates"])
