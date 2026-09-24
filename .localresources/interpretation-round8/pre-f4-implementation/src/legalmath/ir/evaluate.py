"""Pure RuleIR 0.1 reference evaluator. No I/O, host clock or authority writes."""
from dataclasses import dataclass, field

from ..canonical import digest
from ..domain import eligible, timestamp
from ..errors import BoundaryError, diagnostic
from ..integer import parse as integer, decimal
from .graph import children, dependency_closure, walk
from .typecheck import validate_bundle, validate_snapshot
from .load import schema_errors

ENGINE = "legalmath-python/0.1.0"
SEMANTIC_FIELDS = ("status", "type", "mode", "diagnostics", "value", "reason_codes", "missing_inputs", "blocking_inputs", "trace")


@dataclass
class Value:
    type: str | None
    status: str
    value: object = None
    reasons: set = field(default_factory=set)
    missing: set = field(default_factory=set)
    evidence: set = field(default_factory=set)
    diagnostics: list = field(default_factory=list)


def known(typ, value):
    return Value(typ, ("TRUE" if value else "FALSE") if typ == "bool" else "VALUE", value)


def merge(typ, values, status=None, value=None):
    error = next((v for v in values if v.status == "ERROR"), None)
    conflict = next((v for v in values if v.status == "CONFLICT"), None)
    bad = error or conflict
    if bad:
        result = Value(typ, bad.status, diagnostics=bad.diagnostics.copy())
    elif status is not None:
        result = Value(typ, status, value)
    else:
        result = Value(typ, "UNKNOWN")
    for v in values:
        result.reasons.update(v.reasons)
        result.missing.update(v.missing)
        result.evidence.update(v.evidence)
    if bad:
        result.reasons = bad.reasons.copy()
    return result


def result_hash(result, rule_id):
    request = {k: result[k] for k in ("bundle_hash", "snapshot_hash", "mode", "valid_at", "known_at", "engine_version")}
    request["rule_id"] = rule_id
    semantic = {k: result[k] for k in SEMANTIC_FIELDS if k in result}
    return digest({"request": request, "result": semantic})


def evaluate(bundle, snapshot, rule_id, valid_at, known_at, mode="draft"):
    # Identity validation precedes any attempt to return an identified response.
    bh, sh = digest(bundle), digest(snapshot)
    timestamp(valid_at)
    timestamp(known_at)
    if mode not in ("draft", "production", "replay") or not isinstance(rule_id, str):
        raise BoundaryError("E_SCHEMA")
    trace = []
    blocking = None
    errors = schema_errors("rule-bundle", bundle, "/bundle") + schema_errors("fact-snapshot", snapshot, "/snapshot")
    rules = {r["id"]: r for r in bundle["rules"]} if not errors else {}
    if not errors:
        errors = validate_bundle(bundle) + validate_snapshot(bundle, snapshot)
        if rule_id not in rules:
            errors.append(diagnostic("E_REFERENCE", "/rule_id"))
        stages = {"E_SCHEMA": 0, "E_REFERENCE": 1, "E_DUPLICATE_ID": 1, "E_TYPE": 2, "E_CYCLE": 3, "E_TIME": 4, "E_RESOURCE_LIMIT": 0}
        if errors:
            stage = min(stages[e["code"]] for e in errors)
            errors = [e for e in errors if stages[e["code"]] == stage]
    errors.sort(key=lambda e: (e["pointer"], e["code"]))
    typ = rules.get(rule_id, {}).get("type")
    if errors:
        value = Value(None, "ERROR", reasons={e["code"] for e in errors}, diagnostics=errors)
    elif not eligible(bundle["valid_from"], bundle["valid_until"], valid_at):
        value = Value(typ, "ERROR", reasons={"E_VERSION_TIME"}, diagnostics=[diagnostic("E_VERSION_TIME", "/valid_at")])
    else:
        _, fact_names = dependency_closure(bundle, rule_id)
        conflicts = {f for f in fact_names if snapshot["facts"][f]["status"] == "conflict"}
        if conflicts:
            value = Value(typ, "CONFLICT", reasons={"INPUT_CONFLICT"})
            blocking = sorted(conflicts)
        else:
            context = Context(bundle, snapshot, valid_at, known_at)
            value = context.rule(rule_id)
            trace = context.trace
    result = {"status": value.status, "type": value.type, "mode": mode,
        "diagnostics": value.diagnostics, "reason_codes": sorted(value.reasons),
        "missing_inputs": sorted(value.missing),
        "blocking_inputs": blocking if blocking is not None else ([] if value.status in ("TRUE", "FALSE", "VALUE", "OUT_OF_SCOPE") else sorted(value.missing)),
        "trace": trace, "bundle_hash": bh, "snapshot_hash": sh, "engine_version": ENGINE,
        "valid_at": valid_at, "known_at": known_at}
    if value.status in ("TRUE", "FALSE", "VALUE"):
        result["value"] = value.value
    result["result_hash"] = result_hash(result, rule_id)
    return result


class Context:
    def __init__(self, bundle, snapshot, valid_at, known_at):
        self.rules = {r["id"]: r for r in bundle["rules"]}
        self.facts = snapshot["facts"]
        self.valid_at, self.known_at = valid_at, known_at
        self.trace, self.memo, self.rule_memo = [], {}, {}
        self.types, self.pointers = {}, {}

        def infer(node, pointer):
            op = node["op"]
            ts = [infer(n, pointer + "/" + part) for part, n in children(node)]
            typ = (node["type"] if op == "literal" else self.facts[node["name"]]["type"] if op == "fact" else
                self.rules[node["name"]]["type"] if op == "rule" else "bool" if op in ("all", "any", "not", "compare") else
                ts[1] if op == "if" else ts[0])
            self.types[node["node_id"]], self.pointers[node["node_id"]] = typ, pointer
            return typ
        for i, r in enumerate(bundle["rules"]):
            for field in ("scope", "body"):
                infer(r[field], f"/bundle/rules/{i}/{field}")

    def append(self, node, rule, value, kids):
        entry = {"node_id": node["node_id"], "op": node["op"], "children": kids,
            "type": value.type, "status": value.status, "evidence_ids": sorted(value.evidence),
            "source_span_ids": sorted(set(rule["source_span_ids"]))}
        if value.status in ("TRUE", "FALSE", "VALUE"):
            entry["value"] = value.value
        self.trace.append(entry)
        self.memo[node["node_id"]] = value
        return value

    def skip(self, node, rule):
        if node["node_id"] not in self.memo:
            self.append(node, rule, Value(self.types[node["node_id"]], "SKIPPED"), [])

    def rule(self, name):
        if name in self.rule_memo:
            return self.rule_memo[name]
        r = self.rules[name]
        scope = self.node(r["scope"], r)
        if scope.status == "TRUE":
            body = self.node(r["body"], r)
            result = merge(r["type"], [scope, body], body.status, body.value)
        else:
            self.skip(r["body"], r)
            result = merge(r["type"], [scope], "OUT_OF_SCOPE" if scope.status == "FALSE" else "UNKNOWN")
            if scope.status == "UNKNOWN":
                result.reasons.add("SCOPE_UNKNOWN")
        self.rule_memo[name] = result
        return result

    def node(self, node, rule):
        ident, op = node["node_id"], node["op"]
        if ident in self.memo:
            return self.memo[ident]
        typ = self.types[ident]
        kids = [child["node_id"] for _, child in children(node)]
        if op == "literal":
            v = known(typ, node["value"])
        elif op == "fact":
            f = self.facts[node["name"]]
            if f["status"] == "known" and eligible(f["valid_from"], f["valid_until"], self.valid_at) and f["recorded_at"] <= self.known_at:
                v = known(typ, f["value"])
                v.evidence.update(f["evidence_ids"])
            else:
                reason = f.get("reason", "STALE" if f.get("recorded_at", "") <= self.known_at else "MISSING")
                v = Value(typ, "UNKNOWN", reasons={reason}, missing={node["name"]})
        elif op == "rule":
            v = self.rule(node["name"])
            target = self.rules[node["name"]]
            kids = [target[f]["node_id"] for f in ("scope", "body")]
        elif op == "if":
            c = self.node(node["condition"], rule)
            chosen = "then" if c.status == "TRUE" else "else" if c.status == "FALSE" else None
            values = [c]
            for branch in ("then", "else"):
                if branch == chosen:
                    values.append(self.node(node[branch], rule))
                else:
                    self.skip(node[branch], rule)
            v = merge(typ, values, values[-1].status if chosen else "UNKNOWN", values[-1].value if chosen else None)
        elif op == "default":
            guards = [self.node(e["guard"], rule) for e in node["exceptions"]]
            selected, state = None, None
            if any(g.status in ("ERROR", "CONFLICT") for g in guards):
                state = "UNKNOWN"  # merge retains error/conflict precedence
            elif sum(g.status == "TRUE" for g in guards) > 1:
                state = "CONFLICT"
            elif any(g.status == "UNKNOWN" for g in guards):
                state = "UNKNOWN"
            else:
                selected = next((e["value"] for e, g in zip(node["exceptions"], guards) if g.status == "TRUE"), node["base"])
            values = list(guards)
            for candidate in [node["base"]] + [e["value"] for e in node["exceptions"]]:
                if candidate is selected:
                    values.append(self.node(candidate, rule))
                else:
                    self.skip(candidate, rule)
            v = merge(typ, values, state or values[-1].status, values[-1].value if selected else None)
            if state == "CONFLICT":
                v.reasons.add("MULTIPLE_EXCEPTIONS")
        else:
            values = [self.node(c, rule) for _, c in children(node)]
            v = merge(typ, values)
            if v.status not in ("ERROR", "CONFLICT"):
                if op in ("all", "any"):
                    states = [x.status for x in values]
                    target = "FALSE" if op == "all" else "TRUE"
                    other = "TRUE" if op == "all" else "FALSE"
                    state = target if target in states else other if "UNKNOWN" not in states else "UNKNOWN"
                    v = merge(typ, values, state, state == "TRUE" if state != "UNKNOWN" else None)
                elif all(x.status != "UNKNOWN" for x in values):
                    if op == "not":
                        answer = not values[0].value
                    elif op == "compare":
                        a, b = (x.value if x.type == "date" else integer(x.value) for x in values)
                        answer = {"eq": a == b, "ge": a >= b, "gt": a > b}[node["cmp"]]
                    elif op in ("add", "sub"):
                        a, b = (integer(x.value) for x in values)
                        answer = decimal(a + b if op == "add" else a - b)
                    else:
                        num, den = integer(values[0].value) * integer(node["numerator"]), integer(node["denominator"])
                        if num % den:
                            v = merge(typ, values, "ERROR")
                            v.reasons = {"E_INEXACT_SCALE"}
                            v.diagnostics = [diagnostic("E_INEXACT_SCALE", self.pointers[ident])]
                            return self.append(node, rule, v, kids)
                        answer = decimal(num // den)
                    status = ("TRUE" if answer else "FALSE") if typ == "bool" else "VALUE"
                    v = merge(typ, values, status, answer)
        return self.append(node, rule, v, kids)
