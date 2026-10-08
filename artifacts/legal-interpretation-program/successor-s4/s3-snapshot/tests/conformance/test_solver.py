from copy import deepcopy
import json
from pathlib import Path
import pytest
import z3

from legalmath.analysis.compare import compare, Encoder, Term
from legalmath.java.manifest import build_candidate


@pytest.fixture(scope="module")
def java(tmp_path_factory):
    root = Path(__file__).resolve().parents[2]
    cases = json.loads((root / "docs/specs/v0.1/fixtures/decision-cases.json").read_text())["cases"]
    jdk = root / ".localresources/java-toolchain/jdk-17.0.20.1+1"
    return build_candidate(cases[0]["bundle"], tmp_path_factory.mktemp("solver-java"), jdk)["jar"], jdk, cases


def domain():
    return {"portfolio": {"min": "0", "max": "4000000001", "allow_unknown": True},
            "net_assets_ex_home": {"min": "0", "max": "8000000001", "allow_unknown": True}}


@pytest.mark.parametrize("mutation", ["strict", "and"])
def test_counterexamples_replay_in_both_engines(java, mutation):
    jar, jdk, cases = java
    c = cases[0]
    new = deepcopy(c["bundle"])
    if mutation == "strict": new["rules"][0]["body"]["args"][0]["cmp"] = "gt"
    else: new["rules"][0]["body"]["op"] = "all"
    r = compare(c["bundle"], new, c["rule_id"], domain(), c["valid_at"], c["known_at"], java_jar=jar, jdk=jdk)
    assert r["status"] == "COUNTEREXAMPLE"
    assert len(r["java_replays"]) == 2 and not r["proof_certificate_checked"]


def test_empty_timeout_unsupported_and_unknown_classical_trap(java):
    jar, jdk, cases = java
    c = cases[0]
    d = domain();d["portfolio"] = {"min": "5", "max": "4", "allow_unknown": False}
    args = (c["bundle"], c["bundle"], c["rule_id"], d, c["valid_at"], c["known_at"])
    assert compare(*args)["status"] == "INCONSISTENT_DOMAIN"
    assert compare(*args, budget_ms=0)["status"] == "UNKNOWN"
    scaled = next(c for c in cases if c["id"] == "scale.100")
    assert compare(scaled["bundle"], scaled["bundle"], scaled["rule_id"], {}, scaled["valid_at"], scaled["known_at"])["status"] == "UNSUPPORTED"
    c = next(c for c in cases if c["id"] == "logic.excluded_middle")
    b = deepcopy(c["bundle"]);b["rules"][0]["body"] = {"node_id": "true", "op": "literal", "type": "bool", "value": True}
    r = compare(c["bundle"], b, c["rule_id"], {"a": {"states": ["T", "F", "U"]}}, c["valid_at"], c["known_at"], java_jar=jar, jdk=jdk)
    assert r["status"] == "COUNTEREXAMPLE" and r["snapshot"]["facts"]["a"]["status"] == "unknown"


@pytest.mark.parametrize("op", ["all", "any"])
def test_exhaustive_three_valued_tables(op):
    states = {"T": (True, False), "F": (False, True), "U": (False, False)}
    for a in states:
        for b in states:
            variables = {n: Term("bool", z3.BoolVal(states[s][0]), z3.BoolVal(states[s][1])) for n, s in (("a", a), ("b", b))}
            encoder = Encoder({"rules": []}, variables)
            term = encoder.expression({"op": op, "args": [{"op": "fact", "name": "a"}, {"op": "fact", "name": "b"}]})
            actual = "T" if z3.is_true(z3.simplify(term.a)) else "F" if z3.is_true(z3.simplify(term.b)) else "U"
            expected = ("F" if "F" in (a, b) else "T" if a == b == "T" else "U") if op == "all" else ("T" if "T" in (a, b) else "F" if a == b == "F" else "U")
            assert actual == expected
