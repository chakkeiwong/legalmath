"""Knownness-aware SMT comparison of tagged decisions in a declared domain."""
from dataclasses import dataclass
import time
import z3

from ..canonical import digest
from ..domain import scalar
from ..errors import LegalMathError
from ..ir.graph import walk
from ..ir.typecheck import validate_bundle
from ..conformance import evaluate_case
from ..java.manifest import run_java


class Unsupported(Exception):
    pass


@dataclass
class Term:
    type: str
    a: object  # Boolean true / numeric known
    b: object  # Boolean false / numeric integer value

    def known(self):
        return z3.Or(self.a, self.b) if self.type == "bool" else self.a


class Encoder:
    def __init__(self, bundle, variables):
        self.rules = {r["id"]: r for r in bundle["rules"]}
        self.variables = variables
        self.memo = {}

    def expression(self, n):
        op = n["op"]
        if op in ("date", "scale", "default") or n.get("type") == "date":
            raise Unsupported(op)
        if op == "fact": return self.variables[n["name"]]
        if op == "rule":
            if n["name"] not in self.memo:
                self.memo[n["name"]] = self.expression(self.rules[n["name"]]["body"])
            return self.memo[n["name"]]
        if op == "literal":
            return Term("bool", z3.BoolVal(n["value"]), z3.BoolVal(not n["value"])) if n["type"] == "bool" else Term(n["type"], z3.BoolVal(True), z3.IntVal(n["value"]))
        if op in ("all", "any"):
            args = [self.expression(a) for a in n["args"]]
            return Term("bool", (z3.And if op == "all" else z3.Or)(*[x.a for x in args]), (z3.Or if op == "all" else z3.And)(*[x.b for x in args]))
        if op == "not":
            a = self.expression(n["arg"])
            return Term("bool", a.b, a.a)
        if op == "if":
            c, t, f = [self.expression(n[k]) for k in ("condition", "then", "else")]
            if t.type == "bool":
                return Term("bool", z3.Or(z3.And(c.a, t.a), z3.And(c.b, f.a)), z3.Or(z3.And(c.a, t.b), z3.And(c.b, f.b)))
            return Term(t.type, z3.Or(z3.And(c.a, t.a), z3.And(c.b, f.a)), z3.If(c.a, t.b, f.b))
        a, b = self.expression(n["left"]), self.expression(n["right"])
        k = z3.And(a.known(), b.known())
        if op == "compare":
            relation = {"eq": a.b == b.b, "ge": a.b >= b.b, "gt": a.b > b.b}[n["cmp"]]
            return Term("bool", z3.And(k, relation), z3.And(k, z3.Not(relation)))
        return Term(a.type, k, a.b + b.b if op == "add" else a.b - b.b)

    def decision(self, rule_id):
        rule = self.rules[rule_id]
        scope, body = self.expression(rule["scope"]), self.expression(rule["body"])
        if body.type == "bool":
            tag = z3.If(scope.b, 4, z3.If(z3.Not(scope.a), 0, z3.If(body.a, 1, z3.If(body.b, 2, 0))))
            value = z3.IntVal(0)
        else:
            tag = z3.If(scope.b, 4, z3.If(z3.And(scope.a, body.a), 3, 0))
            value = body.b
        return tag, value, body.type


def compare(old, new, rule_id, domain, valid_at, known_at, *, budget_ms=10000, java_jar=None, jdk=None):
    deadline = time.monotonic() + min(budget_ms, 10000) / 1000
    base = {"old_hash": digest(old), "new_hash": digest(new), "domain": domain,
        "valid_at": valid_at, "known_at": known_at, "comparison_target": "status/type/value",
        "solver": "z3/" + z3.get_version_string(), "budget_ms": budget_ms,
        "proof_certificate_checked": False}
    if budget_ms <= 0:
        return {**base, "status": "UNKNOWN", "reason": "TIME_BUDGET"}
    if validate_bundle(old) or validate_bundle(new):
        return {**base, "status": "UNSUPPORTED", "reason": "INVALID_BUNDLE"}
    try:
        for bundle in (old, new):
            if rule_id not in {r["id"] for r in bundle["rules"]}:
                raise Unsupported("rule id")
            if not bundle["valid_from"] <= valid_at or (bundle["valid_until"] is not None and valid_at >= bundle["valid_until"]):
                raise Unsupported("version time")
            nodes = [n for r in bundle["rules"] for field in ("scope", "body") for n, _ in walk(r[field], "")]
            if len(nodes) > 10000 or any(n["op"] in ("default", "scale") or n.get("type") == "date" for n in nodes):
                raise Unsupported("expression fragment")
        facts = {f["name"]: f["type"] for f in old["facts"]}
        if facts != {f["name"]: f["type"] for f in new["facts"]} or set(domain) != set(facts) or "date" in facts.values():
            raise Unsupported("declarations/domain")
        solver = z3.Solver()
        solver.set(timeout=min(budget_ms, 10000))
        variables = {}
        for name, typ in facts.items():
            d = domain[name]
            if typ == "bool":
                if set(d) != {"states"} or not set(d["states"]) <= {"T", "F", "U"}:
                    raise Unsupported("boolean domain")
                t, f = z3.Bools(name + ".true " + name + ".false")
                variables[name] = Term(typ, t, f)
                choices = {"T": z3.And(t, z3.Not(f)), "F": z3.And(f, z3.Not(t)), "U": z3.And(z3.Not(t), z3.Not(f))}
                solver.add(z3.Or(*[choices[k] for k in d["states"]]))
            else:
                if set(d) != {"min", "max", "allow_unknown"} or not scalar(typ, d["min"]) or not scalar(typ, d["max"]) or type(d["allow_unknown"]) is not bool:
                    raise Unsupported("numeric domain")
                k, v = z3.Bool(name + ".known"), z3.Int(name + ".value")
                variables[name] = Term(typ, k, v)
                if not d["allow_unknown"]: solver.add(k)
                solver.add(z3.Implies(k, z3.And(v >= z3.IntVal(d["min"]), v <= z3.IntVal(d["max"]))))
        remaining = int((deadline - time.monotonic()) * 1000)
        if remaining <= 0:
            return {**base, "status": "UNKNOWN", "reason": "TIME_BUDGET"}
        solver.set(timeout=remaining)
        domain_result = solver.check()
        if domain_result == z3.unsat: return {**base, "status": "INCONSISTENT_DOMAIN", "formula": solver.sexpr()}
        if domain_result != z3.sat: return {**base, "status": "UNKNOWN", "reason": solver.reason_unknown(), "formula": solver.sexpr()}
        a, b = Encoder(old, variables).decision(rule_id), Encoder(new, variables).decision(rule_id)
        difference = z3.Or(a[0] != b[0], z3.And(a[0] == 3, b[0] == 3, a[1] != b[1])) if a[2] == b[2] else z3.BoolVal(True)
        solver.add(difference)
        remaining = int((deadline - time.monotonic()) * 1000)
        if remaining <= 0:
            return {**base, "status": "UNKNOWN", "reason": "TIME_BUDGET"}
        solver.set(timeout=remaining)
        outcome = solver.check()
        base["formula"] = solver.sexpr()
        if outcome == z3.unsat: return {**base, "status": "NO_COUNTEREXAMPLE_IN_DECLARED_DOMAIN"}
        if outcome != z3.sat: return {**base, "status": "UNKNOWN", "reason": solver.reason_unknown()}
        model = solver.model()
        snapshot = {"subject_id": "synthetic.solver", "facts": {}}
        for name, term in variables.items():
            known = z3.is_true(model.eval(term.known(), model_completion=True))
            entry = {"type": term.type, "status": "unknown", "reason": "MISSING"}
            if known:
                value = z3.is_true(model.eval(term.a, model_completion=True)) if term.type == "bool" else model.eval(term.b, model_completion=True).as_string()
                entry = {"type": term.type, "status": "known", "value": value, "evidence_ids": ["synthetic.solver"],
                    "valid_from": valid_at, "valid_until": None, "recorded_at": known_at}
            snapshot["facts"][name] = entry
        cases = [{"bundle": bundle, "snapshot": snapshot, "rule_id": rule_id, "valid_at": valid_at, "known_at": known_at} for bundle in (old, new)]
        results = [evaluate_case(c) for c in cases]
        projection = lambda r: {k:r[k] for k in ("status", "type", "value") if k in r}
        if projection(results[0]) == projection(results[1]):
            raise LegalMathError("E_INTEGRITY")
        if java_jar is None or jdk is None:
            return {**base, "status": "UNKNOWN", "reason": "JAVA_REPLAY_REQUIRED"}
        java = run_java(java_jar, cases, jdk)
        if [projection(r) for r in java] != [projection(r) for r in results]:
            raise LegalMathError("E_INTEGRITY")
        return {**base, "status": "COUNTEREXAMPLE", "snapshot": snapshot, "python_replays": results, "java_replays": java}
    except Unsupported as exc:
        return {**base, "status": "UNSUPPORTED", "reason": str(exc)}
