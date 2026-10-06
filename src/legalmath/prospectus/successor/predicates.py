"""Finite open-world predicates shared by clause and authority evaluation."""
import re
from ..semantics import possible_decision

def names(expr, depth=0):
    if depth > 24:
        raise ValueError("Predicate nesting limit exceeded")
    if type(expr) is bool:
        return set()
    if isinstance(expr, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}", expr):
        return {expr}
    if not isinstance(expr, dict) or len(expr) != 1:
        raise ValueError("Use a fact name, Boolean, all/any list, or not expression")
    op, args = next(iter(expr.items()))
    if op == "not":
        return names(args, depth + 1)
    if op not in {"all", "any"} or not isinstance(args, list) or not 1 <= len(args) <= 128:
        raise ValueError("Unknown or empty predicate operator")
    return set().union(*(names(arg, depth + 1) for arg in args))

def evaluate(expr, world):
    if type(expr) is bool:
        return expr
    if isinstance(expr, str):
        return world[expr]
    op, args = next(iter(expr.items()))
    if op == "not":
        return not evaluate(args, world)
    values = (evaluate(arg, world) for arg in args)
    return all(values) if op == "all" else any(values)

def decide(expr, observations):
    required = sorted(names(expr))
    if len(required) > 12:
        raise ValueError("Predicate exceeds the supported twelve-fact domain")
    answer = possible_decision(required, {k:v for k,v in observations.items() if k in required}, lambda w: evaluate(expr, w))
    return {**answer, "status": {"TRUE": "YES", "FALSE": "NO",
            "UNDETERMINED": "UNKNOWN", "CONFLICT": "CONFLICT"}[answer["decision"]]}
