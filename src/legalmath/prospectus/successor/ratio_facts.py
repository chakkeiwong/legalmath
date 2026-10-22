"""Exact declared ratio predicates; source binding does not adjudicate a rule."""
from fractions import Fraction
import re

from .anchors import bind, fields, in_period
from .contracts import timestamp
from .predicates import names

IDENTITY = {"instrument_id", "jurisdiction", "event_id"}
TIMES = {"valid_from", "valid_until", "known_from", "known_until", "observed_at"}
REQUIRED_TIMES = TIMES - {"valid_until", "known_until"}
OPERAND = IDENTITY | TIMES | {"value", "unit", "source"}
CALCULATION = IDENTITY | TIMES | {
    "id", "basis_id", "name", "operator", "threshold", "source", "numerator", "denominator"}


def number(value):
    """Bounded finite decimals only, parsed without binary floating point."""
    if (not isinstance(value, str) or len(value) > 128
            or re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value) is None):
        raise ValueError("Expected a nonnegative finite decimal string of at most 128 characters")
    return Fraction(value)


def derive(bundle, bases, facts, calculations, graph):
    if not isinstance(calculations, list):
        raise ValueError("Ratio facts must be a list")
    declared = {b["id"]: b for b in bases}
    effective, known = timestamp(bundle["effective_at"]), timestamp(bundle["known_at"])
    results, identities, rules, events = {}, set(), {}, set()
    for row in calculations:
        fields(row, CALCULATION, CALCULATION - (TIMES - REQUIRED_TIMES))
        if any(not isinstance(row[k], str) or not row[k]
               for k in ("id", "basis_id", "name", *IDENTITY)):
            raise ValueError("Named ratio identity, subject and event required")
        if row["id"] in identities:
            raise ValueError("Duplicate ratio calculation identity")
        identities.add(row["id"])
        events.add(row["event_id"])
        if len(events) > 1:
            raise ValueError("Different events require separate ratio assessments")
        basis = declared.get(row["basis_id"])
        if basis is None:
            raise ValueError("Ratio fact refers to an undeclared legal basis")
        expression = {"all": basis["premises"]} if isinstance(basis["premises"], list) else basis["premises"]
        if row["name"] not in names(expression):
            raise ValueError("Unexpected ratio fact name")
        if row["instrument_id"] != bundle["instrument_id"] or row["jurisdiction"] != basis["jurisdiction"]:
            raise ValueError("Ratio subject/jurisdiction mismatch")
        key = (row["basis_id"], row["name"])
        if any((f.get("basis_id"), f.get("name")) == key for f in facts):
            raise ValueError("Computed ratio fact cannot also be supplied as a Boolean")
        threshold = number(row["threshold"])
        if (not 0 < threshold <= 1 or not isinstance(row["operator"], str)
                or row["operator"] not in {"GT", "GE"}):
            raise ValueError("Ratio threshold must be in (0,1] with operator GT or GE")
        rule = (row["event_id"], row["operator"], threshold)
        if key in rules and rules[key] != rule:
            raise ValueError("Different event or rule for the same ratio fact")
        rules[key] = rule
        source = bind(graph, row["source"])
        reasons = []
        if not in_period(basis, effective, known):
            reasons.append("Authority outside recorded valid/knowledge interval")
        # Validate every interval even if another condition is already unavailable.
        rule_active = in_period(row, effective, known)
        if not rule_active or timestamp(row["observed_at"]) > known:
            reasons.append("Ratio rule outside valid/knowledge/observation interval")
        operands, values = {}, {}
        for label in ("numerator", "denominator"):
            operand = row[label]
            if operand is None:
                operands[label] = None
                reasons.append("Missing " + label)
                continue
            fields(operand, OPERAND, OPERAND - (TIMES - REQUIRED_TIMES))
            if any(operand[k] != row[k] for k in IDENTITY):
                raise ValueError("Ratio operand subject/jurisdiction/event mismatch")
            if not isinstance(operand["unit"], str) or not operand["unit"].strip():
                raise ValueError("Ratio operand unit required")
            value = number(operand["value"])
            bound = bind(graph, operand["source"])
            if bound["quote"] != operand["value"]:
                raise ValueError("Ratio operand value differs from its exact source literal")
            operands[label] = {**operand, "source": bound}
            values[label] = value
            active = in_period(operand, effective, known)
            if not active or timestamp(operand["observed_at"]) > known:
                reasons.append(label + " outside valid/knowledge/observation interval")
        exact, status = None, "UNKNOWN"
        if len(values) == 2:
            if row["numerator"]["unit"] != row["denominator"]["unit"]:
                raise ValueError("Ratio operand units differ")
            numerator, denominator = values["numerator"], values["denominator"]
            if numerator > denominator:
                raise ValueError("Ratio numerator exceeds denominator")
            if denominator == 0:
                reasons.append("Zero denominator; no defined participating ratio")
            if not reasons:
                left = numerator * threshold.denominator
                right = denominator * threshold.numerator
                value = left > right if row["operator"] == "GT" else left >= right
                status = "YES" if value else "NO"
                exact = {"left": str(left), "right": str(right), "operator": row["operator"],
                         "ratio": str(numerator / denominator),
                         "threshold": str(threshold), "method": "exact rational cross multiplication"}
        result = {**row, **operands, "source": source, "status": status,
                  "unresolved": reasons, "exact_comparison": exact,
                  "qualification": "DECLARED_RULE_AND_SUPPLIED_ELIGIBLE_TOTALS_ONLY"}
        results.setdefault(row["basis_id"], []).append(result)
    return results
