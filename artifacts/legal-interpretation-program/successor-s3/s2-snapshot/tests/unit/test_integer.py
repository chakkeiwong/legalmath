from legalmath.integer import parse, decimal
from legalmath.conformance import evaluate_case


def test_arbitrary_precision_without_global_policy_change(case):
    import sys
    before = sys.get_int_max_str_digits()
    huge = "9" * 6000
    assert decimal(parse(huge) + 1) == "1" + "0" * 6000
    case["snapshot"]["facts"]["portfolio"]["value"] = huge
    assert evaluate_case(case)["status"] == "TRUE"
    assert sys.get_int_max_str_digits() == before
