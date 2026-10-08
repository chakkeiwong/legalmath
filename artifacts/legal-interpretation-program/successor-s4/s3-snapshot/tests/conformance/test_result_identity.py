from copy import deepcopy
import pytest
from legalmath.conformance import evaluate_case
from legalmath.ir.evaluate import result_hash
from legalmath.ir.trace import verify_result
from legalmath.errors import LegalMathError, BoundaryError


def test_stable_native_identity(case):
    r = evaluate_case(case)
    assert r == evaluate_case(deepcopy(case))
    modified = {**r, "engine_version": "another/1"}
    assert result_hash(modified, case["rule_id"]) != r["result_hash"]


@pytest.mark.parametrize("mutation", ["evidence", "source", "order", "duplicate", "blocking", "hash", "substituted_evidence", "empty_trace"])
def test_independent_trace_rejects_corruption(case, mutation):
    r = evaluate_case(case)
    if mutation == "evidence": r["trace"][1]["evidence_ids"] += ["e.z", "e.a"]
    if mutation == "source": r["trace"][0]["source_span_ids"] = []
    if mutation == "order": r["trace"] = list(reversed(r["trace"]))
    if mutation == "duplicate": r["trace"].append(r["trace"][0])
    if mutation == "blocking": r["blocking_inputs"] = ["portfolio"]
    if mutation == "substituted_evidence": r["trace"][1]["evidence_ids"] = ["unrelated.evidence"]
    if mutation == "empty_trace": r["trace"] = []
    r["result_hash"] = "0" * 64 if mutation == "hash" else result_hash(r, case["rule_id"])
    with pytest.raises(LegalMathError): verify_result(case["bundle"], case["snapshot"], case["rule_id"], r)


def test_boundary_failure_has_no_fake_identity(case):
    case["snapshot"]["bad"] = 1.5
    with pytest.raises(BoundaryError) as e: evaluate_case(case)
    assert "result_hash" not in e.value.envelope()
