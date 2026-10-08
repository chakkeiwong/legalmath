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


def _z3_expression(value, variables):
    import z3
    if type(value) is bool:
        return z3.BoolVal(value)
    if isinstance(value, str):
        return variables[value]
    op, args = next(iter(value.items()))
    if op == "not":
        return z3.Not(_z3_expression(args, variables))
    return (z3.And if op == "all" else z3.Or)(*[_z3_expression(a, variables) for a in args])


def solve(expr, observations, constraints=(), *, graph=None, timeout_ms=1000, max_facts=256, solver_factory=None):
    """Optional bounded entailment; named constraints require source occurrences.

    An inconsistent premise set is a conflict, never vacuous entailment. Solver
    resource failure is distinguished from open-world missing information.
    """
    from .anchors import bind, fields
    if type(timeout_ms) is not int or not 1 <= timeout_ms <= 30000 or type(max_facts) is not int or not 1 <= max_facts <= 256:
        raise ValueError("Explicit bounded solver limits required")
    required = names(expr)
    identifiers = set()
    for row in constraints:
        fields(row, {"id", "expression", "source", "reason"}, {"id", "expression", "source", "reason"})
        if not isinstance(row["id"], str) or not row["id"] or row["id"] in identifiers or not row["reason"]:
            raise ValueError("Distinct named source constraints required")
        identifiers.add(row["id"])
        required |= names(row["expression"])
        bind(graph, row["source"])
    required = sorted(required)
    if len(required) > max_facts:
        raise ValueError("Predicate exceeds declared solver domain")
    for k in required:
        v = observations.get(k)
        if v is not None and v != "conflict" and type(v) is not bool:
            raise ValueError("Evidence is Boolean, unknown or conflict")
    missing = [k for k in required if observations.get(k) is None]
    conflicts = [k for k in required if observations.get(k) == "conflict"]
    base = {"missing": missing, "conflicts": conflicts, "witnesses": {}, "constraints": list(constraints),
            "limits": {"timeout_ms_per_check": timeout_ms, "max_facts": max_facts}, "worlds": None}
    def result(status, reason, **extra):
        return {**base, "status": status, "reason": reason, "decision":
                {"YES": "TRUE", "NO": "FALSE", "UNKNOWN": "UNDETERMINED", "CONFLICT": "CONFLICT"}[status], **extra}
    # Preserve explicit relevant conflicts even if q simplifies to a tautology.
    if conflicts:
        return result("CONFLICT", "EXPLICIT_CONFLICT")
    try:
        import z3
    except ImportError:
        return result("UNKNOWN", "SOLVER_UNAVAILABLE")
    variables = {k: z3.Bool("fact:" + k) for k in required}
    def translate(value):
        return _z3_expression(value, variables)
    solver = solver_factory() if solver_factory else z3.Solver()
    solver.set(timeout=timeout_ms, random_seed=0)
    for k in required:
        if type(observations.get(k)) is bool:
            solver.assert_and_track(variables[k] == observations[k], z3.Bool("observation:" + k))
    for row in constraints:
        solver.assert_and_track(translate(row["expression"]), z3.Bool("constraint:" + row["id"]))
    base["solver"] = "z3:" + z3.get_version_string()
    consistency = solver.check()
    if consistency == z3.unsat:
        return result("CONFLICT", "INCONSISTENT_PREMISES", unsat_core=sorted(str(v) for v in solver.unsat_core()))
    if consistency == z3.unknown:
        return result("UNKNOWN", "SOLVER_UNKNOWN", solver_reason=solver.reason_unknown())
    witnesses, satisfiable = {}, {}
    q = translate(expr)
    for value in (False, True):
        solver.push()
        solver.add(q if value else z3.Not(q))
        status = solver.check()
        if status == z3.unknown:
            reason = solver.reason_unknown()
            solver.pop()
            return result("UNKNOWN", "SOLVER_UNKNOWN", solver_reason=reason, witnesses=witnesses)
        satisfiable[value] = status == z3.sat
        if status == z3.sat:
            model = solver.model()
            witnesses[str(value).lower()] = {k: z3.is_true(model.eval(v, model_completion=True)) for k, v in variables.items()}
        solver.pop()
    status = "UNKNOWN" if all(satisfiable.values()) else "YES" if satisfiable[True] else "NO"
    return result(status, "OPEN_PREMISES" if status == "UNKNOWN" else "ENTAILED", witnesses=witnesses)
