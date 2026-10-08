from copy import deepcopy
import json
from pathlib import Path
import pytest
from legalmath.conformance import evaluate_case
from legalmath.ir.trace import verify_result

CASES = json.loads((Path(__file__).resolve().parents[2] / "docs/specs/v0.1/fixtures/decision-cases.json").read_text())["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_hand_specified_decisions(case):
    result = evaluate_case(case)
    for k, v in case["expected"].items():
        if k == "reason_codes_include": assert set(v) <= set(result["reason_codes"])
        else: assert result[k] == v
    assert verify_result(case["bundle"], case["snapshot"], case["rule_id"], result)


def test_missing_is_not_always_blocking():
    yes, unknown = [evaluate_case(next(c for c in CASES if c["id"] == name)) for name in ("f06", "f07")]
    assert yes["missing_inputs"] == ["portfolio"] and yes["blocking_inputs"] == []
    assert unknown["missing_inputs"] == unknown["blocking_inputs"] == ["portfolio"]


def test_static_conflict_in_skipped_branch(case):
    original = case["bundle"]["rules"][0]["body"]
    case["bundle"]["rules"][0]["body"] = {"node_id": "choice", "op": "if", "condition": {"node_id": "yes", "op": "literal", "type": "bool", "value": True}, "then": {"node_id": "ok", "op": "literal", "type": "bool", "value": True}, "else": original}
    case["snapshot"]["facts"]["portfolio"] = {"status": "conflict", "type": "money_hkd", "evidence_ids": ["a", "b"]}
    r = evaluate_case(case)
    assert r["status"] == "CONFLICT" and r["trace"] == []
    case["bundle"]["rules"][0]["body"] = {"node_id": "unrelated", "op": "literal", "type": "bool", "value": True}
    assert evaluate_case(case)["status"] == "TRUE"


def test_eager_error_beats_known_true(case):
    bad = {"node_id": "scale", "op": "scale", "arg": {"node_id": "one", "op": "literal", "type": "integer", "value": "1"}, "numerator": "1", "denominator": "2"}
    comparison = {"node_id": "cmp", "op": "compare", "cmp": "ge", "left": bad, "right": {"node_id": "zero", "op": "literal", "type": "integer", "value": "0"}}
    case["bundle"]["rules"][0]["body"] = {"node_id": "any", "op": "any", "args": [{"node_id": "true", "op": "literal", "type": "bool", "value": True}, comparison]}
    r = evaluate_case(case)
    assert r["status"] == "ERROR" and r["reason_codes"] == ["E_INEXACT_SCALE"]


def test_empty_default_negative_exact_scale(case):
    rule = case["bundle"]["rules"][0]
    rule["type"] = "integer"
    rule["body"] = {"node_id": "default", "op": "default", "exceptions": [], "base": {"node_id": "scale", "op": "scale", "numerator": "1", "denominator": "2", "arg": {"node_id": "negative", "op": "literal", "type": "integer", "value": "-10"}}}
    r = evaluate_case(case)
    assert r["value"] == "-5" and verify_result(case["bundle"], case["snapshot"], case["rule_id"], r)
