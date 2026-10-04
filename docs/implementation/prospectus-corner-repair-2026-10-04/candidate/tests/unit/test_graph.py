from legalmath.ir.typecheck import validate_bundle
from legalmath.ir.graph import dependency_closure


def test_cycle_before_execution(case):
    b = case["bundle"]
    b["rules"][0]["body"] = {"node_id": "cycle", "op": "rule", "name": case["rule_id"]}
    assert validate_bundle(b)[0]["code"] == "E_CYCLE"


def test_static_closure(case):
    assert dependency_closure(case["bundle"], case["rule_id"])[1] == {"portfolio", "net_assets_ex_home"}


def test_long_rule_chain_has_a_resource_error_before_recursion(case):
    from copy import deepcopy
    from legalmath.conformance import evaluate_case
    template = case["bundle"]["rules"][0]
    rules = []
    for i in range(1200):
        rule = deepcopy(template)
        rule.update(id=f"rule.{i}", scope={"node_id": f"scope.{i}", "op": "literal", "type": "bool", "value": True},
            body={"node_id": f"body.{i}", "op": "rule", "name": f"rule.{i+1}"} if i < 1199 else {"node_id": "end", "op": "literal", "type": "bool", "value": True})
        rules.append(rule)
    case["bundle"]["rules"] = rules
    case["rule_id"] = "rule.0"
    assert evaluate_case(case)["reason_codes"] == ["E_RESOURCE_LIMIT"]
    rules[-1]["body"] = {"node_id": "end", "op": "rule", "name": "rule.0"}
    assert validate_bundle(case["bundle"])[0]["code"] == "E_CYCLE"
