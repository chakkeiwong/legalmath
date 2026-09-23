"""Check proposed schemas, provenance and example structure; no rule execution.

Use `--runtime module:function` after W03 to run decision cases against an actual
interpreter. The function receives a complete case dictionary and returns a
complete EvaluationResult dictionary. Without that option no expected outcome is claimed
to have been executed.
"""
import argparse
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import sqlite3

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/v0.1"


def read(name):
    return json.loads((SPEC / name).read_text())


def validator(name):
    data = read(name + ".schema.json")
    Draft202012Validator.check_schema(data)
    return Draft202012Validator(data, format_checker=FormatChecker())


def semantic_structure(bundle):
    """Cross-reference/type/cycle checks needed to validate written examples."""
    facts = {x["name"]: x["type"] for x in bundle["facts"]}
    rules = {x["id"]: x for x in bundle["rules"]}
    if len(facts) != len(bundle["facts"]) or len(rules) != len(bundle["rules"]):
        raise ValueError("E_DUPLICATE_ID")
    spans = {x["id"] for x in bundle["source_spans"]}
    meanings = {x["id"] for x in bundle["interpretations"]}
    nodes, edges = set(), {r: set() for r in rules}

    def same(a, b):
        if a != b:
            raise ValueError("E_TYPE")
        return a

    def walk(node, current):
        nid, op = node["node_id"], node["op"]
        if nid in nodes:
            raise ValueError("E_DUPLICATE_ID")
        nodes.add(nid)
        if op == "literal":
            return node["type"]
        if op == "fact":
            if node["name"] not in facts:
                raise ValueError("E_REFERENCE")
            return facts[node["name"]]
        if op == "rule":
            if node["name"] not in rules:
                raise ValueError("E_REFERENCE")
            target = rules[node["name"]]
            if not (target["scope"]["op"] == "literal" and target["scope"].get("value") is True):
                raise ValueError("E_TYPE")
            edges[current].add(node["name"])
            return target["type"]
        if op in ["all", "any", "not"]:
            for child in node.get("args", [node.get("arg")]):
                same(walk(child, current), "bool")
            return "bool"
        if op in ["add", "sub", "compare"]:
            typ = same(walk(node["left"], current), walk(node["right"], current))
            if typ not in (["integer", "money_hkd", "date"] if op == "compare" else ["integer", "money_hkd"]):
                raise ValueError("E_TYPE")
            return "bool" if op == "compare" else typ
        if op == "scale":
            typ = walk(node["arg"], current)
            if typ not in ["integer", "money_hkd"]:
                raise ValueError("E_TYPE")
            return typ
        if op == "if":
            same(walk(node["condition"], current), "bool")
            return same(walk(node["then"], current), walk(node["else"], current))
        if op == "default":
            typ = walk(node["base"], current)
            ids = set()
            for ex in node["exceptions"]:
                if ex["exception_id"] in ids:
                    raise ValueError("E_DUPLICATE_ID")
                ids.add(ex["exception_id"])
                if ex["interpretation_id"] not in meanings or not set(ex["source_span_ids"]) <= spans:
                    raise ValueError("E_REFERENCE")
                same(walk(ex["guard"], current), "bool")
                same(walk(ex["value"], current), typ)
            return typ
        raise ValueError("E_SCHEMA")

    for ident, rule in rules.items():
        if rule["interpretation_id"] not in meanings or not set(rule["source_span_ids"]) <= spans:
            raise ValueError("E_REFERENCE")
        same(walk(rule["scope"], ident), "bool")
        same(walk(rule["body"], ident), rule["type"])

    def visit(ident, path):
        if ident in path:
            raise ValueError("E_CYCLE")
        for child in edges[ident]:
            visit(child, path | {ident})
    for ident in rules:
        visit(ident, set())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", help="Future evaluator module:function")
    args = parser.parse_args()
    bval, fval = validator("rule-bundle"), validator("fact-snapshot")
    eval_validator = validator("evaluation")
    anchor = read("fixtures/source-anchor.json")
    text = (ROOT / anchor["text_path"]).read_text().removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    span = anchor["span"]
    assert hashlib.sha256((ROOT / anchor["raw_path"]).read_bytes()).hexdigest() == span["raw_sha256"]
    assert hashlib.sha256(text.encode()).hexdigest() == span["text_sha256"]
    assert hashlib.sha256(text[span["start"]:span["end"]].encode()).hexdigest() == span["quote_sha256"]
    assert text[:span["start"]].count("\f") + 1 == span["page"]
    cases = read("fixtures/decision-cases.json")["cases"]
    assert len({c["id"] for c in cases}) == len(cases)
    for c in cases:
        bval.validate(c["bundle"])
        semantic_structure(c["bundle"])
        fval.validate(c["snapshot"])
        declarations = {f["name"]: f["type"] for f in c["bundle"]["facts"]}
        assert declarations == {n: f["type"] for n, f in c["snapshot"]["facts"].items()}, c["id"]
        assert c["rule_id"] in {r["id"] for r in c["bundle"]["rules"]}
    invalid = read("fixtures/invalid-cases.json")
    for c in invalid:
        candidate = deepcopy(read("fixtures/" + c["base"]))
        target = candidate
        for key in c["path"][:-1]:
            target = target[key]
        target[c["path"][-1]] = c["replacement"]
        if c["rejected_at"] == "schema":
            assert list(bval.iter_errors(candidate)), c["id"]
        else:
            bval.validate(candidate)
            try:
                semantic_structure(candidate)
            except ValueError as exc:
                assert str(exc) == c["expected_code"], (c["id"], str(exc))
            else:
                raise AssertionError(c["id"])
    conn = sqlite3.connect(":memory:")
    conn.executescript((SPEC / "storage.sql").read_text())
    assert not conn.execute("PRAGMA foreign_key_check").fetchall()
    event_cases = read("fixtures/event-cases.json")
    for c in event_cases:
        assert len({e["id"] for e in c["events"]}) == len(c["events"])
        assert all(e["stream_id"] == c["stream_id"] for e in c["events"])
        assert all(FormatChecker().conforms(e["occurred_at"], "date-time") for e in c["events"])
        assert c["stream_header"]["ordering_authority"] == c["ordering_authority"]
        if c["profile"] == "consent":
            assert c["completeness"]["complete_from"] <= c["stream_header"]["inception"]
            assert c["completeness"]["complete_through"] >= c["valid_at"]
            assert c["completeness"]["recorded_at"] <= c["known_at"]
    executed = 0
    if args.runtime:
        module, function = args.runtime.split(":", 1)
        evaluate = getattr(importlib.import_module(module), function)
        for c in cases:
            actual = evaluate(deepcopy(c))
            eval_validator.validate(actual)
            for key, expected in c["expected"].items():
                if key == "reason_codes_include":
                    assert set(expected) <= set(actual.get("reason_codes", [])), c["id"]
                else:
                    assert actual.get(key) == expected, (c["id"], expected, actual)
            executed += 1
    print(json.dumps({"schemas_valid": 3, "decision_fixture_contracts_valid": len(cases),
                      "negative_contract_checks": len(invalid), "event_fixture_structure_checks": len(event_cases),
                      "source_anchor_hashes_valid": True, "sqlite_ddl_valid": True,
                      "runtime_decisions_executed": executed,
                      "event_and_release_outcomes_executed": False,
                      "legal_interpretations_approved": False}, indent=2))


if __name__ == "__main__":
    main()
