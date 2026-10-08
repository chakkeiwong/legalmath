"""Explicit local toolchain and grouped corpora for real Catala builds."""
from pathlib import Path
from legalmath.canonical import digest, loads
from tests.conformance.test_java import spi_cases

ROOT = Path(__file__).resolve().parents[2]
JDK = ROOT / ".localresources/java-toolchain/jdk-17.0.20.1+1"
TOOLCHAIN = {
    "compiler": ROOT / ".localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala",
    "upstream": ROOT / ".localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa",
    "lock": ROOT / "docs/implementation/catala/toolchain-lock.json",
}


def corpus_groups():
    cases = loads((ROOT / "docs/specs/v0.1/fixtures/decision-cases.json").read_bytes())["cases"] + spi_cases()
    groups = {}
    for c in cases:
        groups.setdefault(digest(c["bundle"]), []).append(c)
    return list(groups.values())


def interaction_cases():
    """Deterministic status truth tables, lazy errors, reference reuse and exact types."""
    from copy import deepcopy
    from itertools import product
    seed = loads((ROOT / "docs/specs/v0.1/fixtures/decision-cases.json").read_bytes())["cases"][0]
    b = deepcopy(seed["bundle"])
    b["bundle_id"] = "catala.interactions"
    b["facts"] = [{"name": name, "type": "bool", "description": "Synthetic guard"} for name in ("guard.alpha", "guard.beta", "guard.gamma")]
    b["rules"] = []
    serial = 0
    def node(op, **fields):
        nonlocal serial
        serial += 1
        return {"node_id": f"node.{serial}", "op": op, **fields}
    def literal(typ, value): return node("literal", type=typ, value=value)
    def fact(name): return node("fact", name="guard." + name)
    def error(): return node("scale", arg=literal("integer", "1"), numerator="1", denominator="2")
    def error_guard(): return node("compare", cmp="eq", left=error(), right=literal("integer", "0"))
    def default(guards, typ="integer", values=None):
        return node("default", base=literal(typ, "0" if typ=="integer" else False), exceptions=[
            {"exception_id": f"exception.{i}", "guard": guard,
             "value": values[i] if values else literal(typ, "10" if typ=="integer" else True),
             "interpretation_id": b["interpretations"][0]["id"], "source_span_ids": [b["source_spans"][0]["id"]]}
            for i, guard in enumerate(guards)])
    def rule(name, typ, body):
        b["rules"].append({"id": name, "type": typ, "scope": literal("bool", True), "body": body,
                           "interpretation_id": b["interpretations"][0]["id"], "source_span_ids": [b["source_spans"][0]["id"]]})
    # Three true guards expose multiplicity, including true/true/unknown precedence.
    rule("multiple", "integer", default([fact("alpha"), fact("beta"), fact("gamma")]))
    rule("if.lazy", "integer", node("if", condition=fact("alpha"), then=literal("integer", "7"), **{"else": error()}))
    rule("default.lazy", "integer", default([fact("alpha")], values=[error()]))
    rule("default.guard.error", "integer", default([literal("bool", True), literal("bool", True), error_guard()]))
    rule("default.guard.conflict", "integer", default([default([literal("bool", True), literal("bool", True)], typ="bool"), fact("alpha")]))
    rule("all.unknown", "bool", node("all", args=[fact("alpha"), fact("beta"), fact("gamma")]))
    rule("any.unknown", "bool", node("any", args=[fact("alpha"), fact("beta"), fact("gamma")]))
    rule("all.error", "bool", node("all", args=[literal("bool", False), error_guard()]))
    rule("any.conflict", "bool", node("any", args=[literal("bool", True), default([literal("bool", True), literal("bool", True)], typ="bool")]))
    rule("sum.reference", "integer", node("add", left=node("rule", name="multiple"), right=node("rule", name="multiple")))
    varied = [r["id"] for r in b["rules"]]
    fixed = [
        ("negative.scale", "integer", node("scale", arg=literal("integer", "-123456789012345678901234567890"), numerator="12", denominator="3"), "-493827156049382715604938271560"),
        ("huge.integer", "integer", node("sub", left=literal("integer", "9"*6000), right=literal("integer", "8"*6000)), "1"*6000),
        ("date.first", "date", literal("date", "0001-01-01"), "0001-01-01"),
        ("date.last", "date", literal("date", "9999-12-31"), "9999-12-31"),
        ("date.compare", "bool", node("compare", cmp="gt", left=literal("date", "2024-02-29"), right=literal("date", "2024-02-28")), True),
        ("empty.default", "integer", default([]), "0"),
        ("many.guards", "integer", default([literal("bool", False) for _ in range(130)]), "0"),
    ]
    for name, typ, expression, _ in fixed:
        rule(name, typ, expression)
    requests = []
    def known(value):
        return {"status": "known", "type": "bool", "value": value, "evidence_ids": ["synthetic.observation"],
                "valid_from": seed["valid_at"], "valid_until": None, "recorded_at": seed["known_at"]}
    def make(name, snapshot, ident):
        return {"id": ident, "bundle": b, "snapshot": snapshot, "rule_id": name,
                "valid_at": seed["valid_at"], "known_at": seed["known_at"], "expected": {}}
    for index, states in enumerate(product((True, False, None), repeat=3)):
        snap = {"subject_id": "synthetic", "facts": {f["name"]: known(v) if v is not None else {"status": "unknown", "type": "bool", "reason": "MISSING"} for f, v in zip(b["facts"], states)}}
        for name in varied:
            requests.append(make(name, snap, name + f".{index}"))
    snap = {"subject_id": "synthetic", "facts": {f["name"]: known(False) for f in b["facts"]}}
    for name, typ, _, expected in fixed:
        c = make(name, snap, name)
        c["expected"] = {"status": ("TRUE" if expected else "FALSE") if typ=="bool" else "VALUE", "value": expected}
        requests.append(c)
    return requests
