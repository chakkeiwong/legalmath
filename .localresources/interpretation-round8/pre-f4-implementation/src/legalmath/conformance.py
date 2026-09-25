from .ir.evaluate import evaluate


def evaluate_case(case):
    return evaluate(case["bundle"], case["snapshot"], case["rule_id"], case["valid_at"], case["known_at"], case.get("mode", "draft"))
