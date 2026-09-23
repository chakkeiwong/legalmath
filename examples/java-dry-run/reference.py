"""Independent reference for the deliberately small SPI-Demo1 decision profile.

This is not the complete RuleIR 0.1 service. No production release authority is
implemented here. The compiler rejects constructs outside the demonstrated subset.
"""
import hashlib
import json


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def evaluate(bundle, snapshot, valid_at, known_at):
    rules = {r["id"]: r for r in bundle["rules"]}
    declarations = {f["name"]: f["type"] for f in bundle["facts"]}
    facts = snapshot["facts"]
    trace, cache = [], {}
    encountered = set()

    def output(status, blockers):
        result = dict(profile="SPI-Demo1", status=status,
                      disposition={"TRUE": "STREAMLINING_CONDITIONS_MET",
                                   "FALSE": "STANDARD_PROCESS_REQUIRED",
                                   "OUT_OF_SCOPE": "OUTSIDE_PROFILE"}.get(status, "REVIEW_REQUIRED"),
                      blocking_inputs=sorted(blockers), missing_inputs=sorted(encountered),
                      trace=trace, bundle_hash=digest(bundle), snapshot_hash=digest(snapshot),
                      valid_at=valid_at, known_at=known_at, authority="DEMONSTRATION_ONLY")
        result["result_hash"] = digest(result)
        return result

    # Every declared fact is in the root's dependency closure in this profile.
    conflicts = {n for n, f in facts.items() if f["status"] == "conflict"}
    if conflicts:
        return output("CONFLICT", conflicts)

    def expr(node):
        op = node["op"]
        if op == "literal":
            return node["value"] if node["type"] == "bool" else int(node["value"]), set()
        if op == "fact":
            name = node["name"]
            f = facts.get(name)
            if (f is None or f["status"] != "known" or f["valid_from"] > valid_at
                    or (f["valid_until"] is not None and valid_at >= f["valid_until"])
                    or f["recorded_at"] > known_at):
                encountered.add(name)
                return None, {name}
            return f["value"] if declarations[name] == "bool" else int(f["value"]), set()
        if op == "rule":
            return rule(node["name"])
        if op in ("all", "any"):
            values = [expr(a) for a in node["args"]]
            decisive = False if op == "all" else True
            if any(v is decisive for v, _ in values):
                return decisive, set()
            if any(v is None for v, _ in values):
                return None, set().union(*(b for _, b in values))
            return not decisive, set()
        if op == "not":
            value, blockers = expr(node["arg"])
            return (None if value is None else not value), blockers
        if op == "compare":
            a, ab = expr(node["left"])
            b, bb = expr(node["right"])
            if a is None or b is None:
                return None, ab | bb
            return {"ge": a >= b, "gt": a > b, "eq": a == b}[node["cmp"]], set()
        raise ValueError("E_UNSUPPORTED: " + op)

    def rule(name):
        if name in cache:
            return cache[name]
        r = rules[name]
        v, b = expr(r["body"])
        cache[name] = v, b
        trace.append(dict(rule_id=name, status="UNKNOWN" if v is None else str(v).upper(),
                          source_span_ids=r["source_span_ids"], blocking_inputs=sorted(b)))
        return v, b

    scope, blockers = expr(rules["spi.streamlining"]["scope"])
    if scope is False:
        return output("OUT_OF_SCOPE", set())
    if scope is None:
        return output("UNKNOWN", blockers)
    value, blockers = rule("spi.streamlining")
    return output("UNKNOWN" if value is None else str(value).upper(), blockers)


def consent(events, valid_at, known_at, complete_through, completeness_recorded_at):
    """One client/category stream. Absence of complete history is not consent."""
    visible = [e for e in events if e["recorded_at"] <= known_at]
    unique = {}
    for e in visible:
        if e["id"] in unique and unique[e["id"]] != e:
            return "CONFLICT"
        unique[e["id"]] = e
    selected = [e for e in unique.values() if e["occurred_at"] <= valid_at]
    if (complete_through < valid_at or completeness_recorded_at > known_at
            or complete_through > completeness_recorded_at):
        return "UNKNOWN"
    keys = [(e["occurred_at"], e["sequence"]) for e in selected]
    if len(keys) != len(set(keys)):
        return "UNKNOWN"
    selected.sort(key=lambda e: (e["occurred_at"], e["sequence"]))
    return "TRUE" if selected and selected[-1]["kind"] == "GRANTED" else "FALSE"
