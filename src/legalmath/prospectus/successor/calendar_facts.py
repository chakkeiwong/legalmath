"""Source-bound interval arithmetic under an explicitly supplied convention."""
from datetime import date
import re

from .anchors import bind, fields, in_period
from .contracts import timestamp
from .predicates import names

IDENTITY = {"instrument_id", "jurisdiction", "event_id"}
TIMES = {"valid_from", "valid_until", "known_from", "known_until", "observed_at"}
OPTIONAL = {"valid_until", "known_until", "operator"}
OPERAND = IDENTITY | TIMES | {"value", "source", "role"}
CALCULATION = IDENTITY | TIMES | {
    "id", "basis_id", "name", "source", "rule_reading", "convention", "days", "start", "end", "operator"}
CONVENTIONS = {"CIVIL_DATE_GAP", "CLEAR_CIVIL_DAYS", "ELAPSED_24_HOUR_DAYS"}
DAY_MICROSECONDS = 86_400_000_000


def moment(value):
    if not isinstance(value, str):
        raise ValueError("Calendar observation requires a timezone-aware timestamp string")
    return timestamp(value)


def operand_value(value, convention):
    if not isinstance(value, str):
        raise ValueError("Calendar operand requires an exact ISO string")
    if convention == "ELAPSED_24_HOUR_DAYS":
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value) is None:
            raise ValueError("Elapsed calendar operand requires an offset and at most microsecond precision")
        if not value.endswith("Z") and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
            raise ValueError("Elapsed calendar operand has an invalid UTC offset")
        return timestamp(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise ValueError("Civil calendar operand requires YYYY-MM-DD")
    return date.fromisoformat(value)


def compare(start, end, convention, days, operator="GE"):
    """Compare the declared mathematical intervals; never choose a legal rule."""
    if not isinstance(operator, str) or operator not in {"GE", "LE", "GT"}:
        raise ValueError("Calendar operator must be GE, LE or GT")
    delta = end - start
    if delta.days < 0:
        raise ValueError("Calendar interval ends before it starts")
    if convention == "ELAPSED_24_HOUR_DAYS":
        left = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
        right, unit = days * DAY_MICROSECONDS, "microseconds"
    else:
        left = delta.days if convention == "CIVIL_DATE_GAP" else max(0, delta.days - 1)
        right, unit = days, "civil_days"
    return ({"GE": left >= right, "LE": left <= right, "GT": left > right}[operator]), {"left": str(left), "right": str(right), "operator": operator,
                           "unit": unit, "convention": convention}


def derive(bundle, bases, facts, calculations, graph, *, ratio_facts=None):
    if not isinstance(calculations, list):
        raise ValueError("Calendar facts must be a list")
    declared = {b["id"]: b for b in bases}
    effective, known = timestamp(bundle["effective_at"]), timestamp(bundle["known_at"])
    results, identities, rules, events = {}, set(), {}, set()
    for row in calculations:
        fields(row, CALCULATION, CALCULATION - OPTIONAL)
        if any(not isinstance(row[k], str) or not row[k].strip()
               for k in ("id", "basis_id", "name", "rule_reading", *IDENTITY)):
            raise ValueError("Named calendar identity, subject, event and rule reading required")
        if row["id"] in identities:
            raise ValueError("Duplicate calendar calculation identity")
        identities.add(row["id"])
        events.add(row["event_id"])
        if len(events) > 1:
            raise ValueError("Different events require separate calendar assessments")
        basis = declared.get(row["basis_id"])
        if basis is None:
            raise ValueError("Calendar fact refers to an undeclared legal basis")
        expr = {"all": basis["premises"]} if isinstance(basis["premises"], list) else basis["premises"]
        if row["name"] not in names(expr):
            raise ValueError("Unexpected calendar fact name")
        if row["instrument_id"] != bundle["instrument_id"] or row["jurisdiction"] != basis["jurisdiction"]:
            raise ValueError("Calendar subject/jurisdiction mismatch")
        key = (row["basis_id"], row["name"])
        if any((f.get("basis_id"), f.get("name")) == key for f in facts):
            raise ValueError("Computed calendar fact cannot also be supplied as a Boolean")
        if any((f.get("basis_id"), f.get("name")) == key for f in (ratio_facts or [])):
            raise ValueError("Computed calendar fact cannot also be supplied as a ratio")
        convention, days = row["convention"], row["days"]
        if not isinstance(convention, str) or convention not in CONVENTIONS:
            raise ValueError("Unsupported calendar convention; an explicit supported convention is required")
        if type(days) is not int or days <= 0:
            raise ValueError("Calendar day threshold must be a positive integer")
        operator = row.get("operator", "GE")
        if not isinstance(operator, str) or operator not in {"GE", "LE", "GT"}:
            raise ValueError("Calendar operator must be GE, LE or GT")
        rule = (row["event_id"], convention, days, operator, row["rule_reading"], row["source"])
        if key in rules and rules[key] != rule:
            raise ValueError("Different calendar rules for one premise require separate alternative bases")
        rules[key] = rule
        source = bind(graph, row["source"])
        reasons = []
        if not in_period(basis, effective, known):
            reasons.append("Authority outside recorded valid/knowledge interval")
        active = in_period(row, effective, known)
        observed = moment(row["observed_at"])
        if not active or observed > known:
            reasons.append("Calendar rule outside valid/knowledge/observation interval")
        operands, values = {}, {}
        for label in ("start", "end"):
            operand = row[label]
            if operand is None:
                operands[label] = None
                reasons.append("Missing " + label)
                continue
            fields(operand, OPERAND, OPERAND - OPTIONAL)
            if any(operand[k] != row[k] for k in IDENTITY):
                raise ValueError("Calendar operand subject/jurisdiction/event mismatch")
            if not isinstance(operand["role"], str) or not operand["role"].strip():
                raise ValueError("Calendar operand role required")
            values[label] = operand_value(operand["value"], convention)
            bound = bind(graph, operand["source"])
            if bound["quote"] != operand["value"]:
                raise ValueError("Calendar operand differs from its exact source literal")
            operands[label] = {**operand, "source": bound}
            active = in_period(operand, effective, known)
            observed = moment(operand["observed_at"])
            if not active or observed > known:
                reasons.append(label + " outside valid/knowledge/observation interval")
        status, exact = "UNKNOWN", None
        if len(values) == 2:
            value, compared = compare(values["start"], values["end"], convention, days, operator)
            if not reasons:
                status, exact = ("YES" if value else "NO"), compared
        result = {**row, **operands, "source": source, "status": status,
                  "unresolved": reasons, "exact_comparison": exact,
                  "qualification": "DECLARED_CONVENTION_AND_SUPPLIED_DATES_ONLY",
                  "legal_counting_convention_established": False,
                  "actual_event_established": False}
        results.setdefault(row["basis_id"], []).append(result)
    return results
