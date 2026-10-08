from copy import deepcopy
import pytest
from legalmath.ir.typecheck import validate_bundle


@pytest.mark.parametrize("mutation,code", [("span", "E_DUPLICATE_ID"), ("meaning", "E_DUPLICATE_ID"), ("citation", "E_REFERENCE"), ("type", "E_TYPE")])
def test_complete_reference_validation(case, mutation, code):
    b = case["bundle"]
    if mutation == "span": b["source_spans"].append(deepcopy(b["source_spans"][0]))
    if mutation == "meaning": b["interpretations"].append(deepcopy(b["interpretations"][0]))
    if mutation == "citation": b["interpretations"][0]["source_span_ids"] = ["missing"]
    if mutation == "type": b["rules"][0]["body"]["args"][0]["right"]["type"] = "integer"
    assert code in {x["code"] for x in validate_bundle(b)}
