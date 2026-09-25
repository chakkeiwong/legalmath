from legalmath.conformance import evaluate_case
import pytest
from legalmath.ir.trace import verify_result


def test_structural_snapshot_error_precedes_bundle_type(case):
    case["bundle"]["rules"][0]["type"] = "integer"
    case["snapshot"]["extra"] = True
    r = evaluate_case(case)
    assert r["reason_codes"] == ["E_SCHEMA"]


def test_reference_error_precedes_type(case):
    del case["snapshot"]["facts"]["net_assets_ex_home"]
    case["snapshot"]["facts"]["portfolio"]["type"] = "integer"
    r = evaluate_case(case)
    assert r["reason_codes"] == ["E_REFERENCE"]


@pytest.mark.parametrize("malformed", [None, [], [None], [{"id": {}}]])
def test_hashable_invalid_bundle_returns_identified_error(case, malformed):
    case["bundle"]["rules"] = malformed
    result = evaluate_case(case)
    assert result["reason_codes"] == ["E_SCHEMA"] and result["status"] == "ERROR"
    assert verify_result(case["bundle"], case["snapshot"], case["rule_id"], result)
