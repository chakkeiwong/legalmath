from copy import deepcopy
from legalmath.conformance import evaluate_case
from legalmath.java.manifest import build_candidate, verify_candidate


def literal(n, typ, value): return {"node_id": n, "op": "literal", "type": typ, "value": value}


def test_generated_nonboolean_date_arithmetic_and_selected_branches(case, root, tmp_path):
    bundle = deepcopy(case["bundle"])
    bundle["facts"] = []
    bundle["rules"] = []
    templates = [
        ("date.value", "date", literal("date.output", "date", "9999-12-31"), "VALUE", "9999-12-31"),
        ("date.order", "bool", {"node_id": "date.cmp", "op": "compare", "cmp": "gt", "left": literal("date.left", "date", "2024-02-29"), "right": literal("date.right", "date", "2024-02-28")}, "TRUE", True),
        ("integer.sum", "integer", {"node_id": "sum", "op": "add", "left": literal("sum.left", "integer", "-9"), "right": literal("sum.right", "integer", "3")}, "VALUE", "-6"),
        ("selected.if", "money_hkd", {"node_id": "if", "op": "if", "condition": literal("if.guard", "bool", True), "then": literal("if.then", "money_hkd", "100"), "else": {"node_id": "if.bad", "op": "scale", "arg": literal("if.cent", "money_hkd", "1"), "numerator": "1", "denominator": "2"}}, "VALUE", "100"),
        ("empty.default", "integer", {"node_id": "default", "op": "default", "base": literal("default.base", "integer", "8"), "exceptions": []}, "VALUE", "8"),
        ("shared.references", "integer", {"node_id": "shared.sum", "op": "add", "left": {"node_id": "shared.a", "op": "rule", "name": "integer.sum"}, "right": {"node_id": "shared.b", "op": "rule", "name": "integer.sum"}}, "VALUE", "-12"),
    ]
    for name, typ, body, status, value in templates:
        bundle["rules"].append({"id": name, "type": typ, "scope": literal(name + ".scope", "bool", True), "body": body,
            "interpretation_id": bundle["interpretations"][0]["id"], "source_span_ids": [bundle["source_spans"][0]["id"]]})
    cases = [{"id": name, "bundle": bundle, "snapshot": {"subject_id": "synthetic", "facts": {}}, "rule_id": name,
        "valid_at": case["valid_at"], "known_at": case["known_at"], "expected": {"status": status, "value": value}}
        for name, typ, body, status, value in templates]
    jdk = root / ".localresources/java-toolchain/jdk-17.0.20.1+1"
    build = build_candidate(bundle, tmp_path, jdk)
    assert verify_candidate(build, cases, jdk)["passed"]
    result = evaluate_case(cases[-1])
    assert sum(t["node_id"] == "sum" for t in result["trace"]) == 1
    conditional = evaluate_case(cases[3])
    assert any(t["node_id"] == "if.bad" and t["status"] == "SKIPPED" for t in conditional["trace"])
    assert not any(t["node_id"] == "if.cent" for t in conditional["trace"])
