"""Deterministic comparison corpus. Used only by validation, not the candidate."""
from copy import deepcopy
from itertools import product
import json


def comparison_cases(root):
    original = json.loads((root / "docs/specs/v0.1/fixtures/decision-cases.json").read_text())["cases"]
    cases = [deepcopy(c) for c in original if c["rule_id"] in ("spi.financial", "exception.test")]
    finance = next(c for c in original if c["id"] == "f01")
    defaults = next(c for c in original if c["id"] == "exception.false.false")

    def fact(template, value):
        if value is None:
            return {"status": "unknown", "type": template["type"], "reason": "MISSING"}
        if value == "conflict":
            return {"status": "conflict", "type": template["type"], "evidence_ids": ["a", "b"]}
        result = deepcopy(template)
        result["value"] = value
        return result

    for i, (p, a) in enumerate(product(
            ["-1", "0", "3999999999", "4000000000", "4000000001", "1" + "0" * 40, None, "conflict"],
            ["-1", "0", "7999999999", "8000000000", "8000000001", "1" + "0" * 40, None, "conflict"])):
        case = deepcopy(finance)
        case["id"] = f"grid.financial.{i:02d}"
        case.pop("expected", None)
        for name, value in (("portfolio", p), ("net_assets_ex_home", a)):
            case["snapshot"]["facts"][name] = fact(case["snapshot"]["facts"][name], value)
        cases.append(case)
    for i, (a, b) in enumerate(product([True, False, None, "conflict"], repeat=2)):
        case = deepcopy(defaults)
        case["id"] = f"grid.exceptions.{i:02d}"
        case.pop("expected", None)
        for name, value in (("a", a), ("b", b)):
            case["snapshot"]["facts"][name] = fact(case["snapshot"]["facts"][name], value)
        cases.append(case)
    for field, values in {
        "valid_from": ["2026-09-01T00:00:00.000000Z", "2026-09-01T00:00:00.000001Z"],
        "valid_until": ["2026-09-01T00:00:00.000000Z", "2026-09-01T00:00:00.000001Z"],
        "recorded_at": ["2026-09-01T00:00:00.000000Z", "2026-09-01T00:00:00.000001Z"],
    }.items():
        for i, value in enumerate(values):
            case = deepcopy(finance)
            case["id"] = f"time.{field}.{i}"
            case.pop("expected", None)
            case["snapshot"]["facts"]["portfolio"][field] = value
            cases.append(case)
    scope_case = next(c for c in original if c["id"] == "scope.false")
    for i, value in enumerate((True, False, None, "conflict")):
        case = deepcopy(scope_case)
        case["id"] = f"grid.scope.{i}"
        case.pop("expected", None)
        case["snapshot"]["facts"]["scope"] = fact(case["snapshot"]["facts"]["scope"], value)
        cases.append(case)
    # RuleIR statically sees a conflict even if scope would skip the body.
    case = deepcopy(scope_case)
    case["id"] = "scope.false.body_conflict"
    case.pop("expected", None)
    case["snapshot"]["facts"]["portfolio"] = fact(case["snapshot"]["facts"]["portfolio"], "conflict")
    cases.append(case)
    return original, cases
