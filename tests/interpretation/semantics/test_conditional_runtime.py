"""Executable mathematics and hostile transport checks, without legal answer labels."""
from copy import deepcopy
from itertools import product
import json
import os
from pathlib import Path
import pytest

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from legalmath.canonical import canonical, loads, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.semantics import conditional_ir as ir, conditional_runtime as runtime

ROOT = Path(__file__).resolve().parents[3]
JDK = ROOT / ".localresources/java-toolchain/jdk-17.0.20.1+1"


def program(codes=(1,), heads=2, rules=None):
    if rules is None:
        rules = [(0, [0], []), (1, [], [0]), (0, [], [1])]
    return ir.decode(canonical({
        "profile": ir.PROFILE, "context_hash": "0" * 64,
        "fact_ids": ["fact." + str(i) for i in range(len(codes))],
        "codes": list(codes), "heads": ["head." + str(i) for i in range(heads)],
        "rules": [{"id": "rule." + str(i), "head": h, "facts": fs, "parents": ps}
                  for i, (h, fs, ps) in enumerate(rules)]}))


@pytest.fixture(scope="module")
def java(tmp_path_factory):
    path = tmp_path_factory.mktemp("conditional-java")
    runtime.compile_java(path, JDK)
    return path


@pytest.mark.parametrize("code", range(4))
def test_four_states_have_only_one_admitted_value(java, tmp_path, code):
    p = program((code,))
    expected = [0, 1] if code == 1 else []
    assert ir.reference(p) == ir.closed_set_oracle(p) == expected
    assert runtime.checked_java([p], java, JDK)[0]["derived"] == expected
    proof = runtime.kernel(p, expected, tmp_path)
    assert proof["status"] == "KERNEL_CHECKED"
    assert set(proof["kernel_axioms"]) <= {"propext", "Quot.sound"}
    assert "Legal discharge" in proof["scope"]["excludes"]


def test_all_small_parent_graphs_and_evidence_states(java):
    # 25 choices of absent rule or one of all four parent subsets, times 16 states.
    programs = []
    for codes in product(range(4), repeat=2):
        for choices in product((None, (), (0,), (1,), (0, 1)), repeat=2):
            rules = [(i, [i], list(ps)) for i, ps in enumerate(choices) if ps is not None]
            programs.append(program(codes, rules=rules))
    replies = runtime.checked_java(programs, java, JDK)
    assert len(replies) == 400
    for p, reply in zip(programs, replies):
        assert reply["derived"] == ir.closed_set_oracle(p)
        reverse = p.model_copy(update={"rules": tuple(reversed(p.rules))})
        assert ir.reference(reverse) == reply["derived"]


@pytest.mark.parametrize("rules,expected", [
    ([(0, [], [1]), (1, [], [0])], []),
    ([(0, [0], []), (1, [], [0]), (0, [], [1])], [0, 1]),
    ([(0, [], [0]), (0, [], []), (1, [], [0])], [0, 1]),
    ([(0, [], []), (1, [], []), (2, [], [0, 1])], [0, 1, 2]),
    ([], []),
])
def test_cycles_alternatives_and_multiple_parents(java, tmp_path, rules, expected):
    p = program(heads=3, rules=rules)
    assert runtime.checked_java([p], java, JDK)[0]["derived"] == ir.closed_set_oracle(p) == expected
    assert runtime.kernel(p, expected, tmp_path)["status"] == "KERNEL_CHECKED"


def test_largest_chain_has_checked_soundness_and_closure(java, tmp_path):
    p = program(codes=(), heads=64,
                rules=[(i, [], [] if i == 0 else [i - 1]) for i in range(64)])
    expected = list(range(64))
    assert runtime.checked_java([p], java, JDK)[0]["derived"] == expected
    assert runtime.kernel(p, expected, tmp_path)["status"] == "KERNEL_CHECKED"
    with pytest.raises(LegalMathError):
        ir.closed_set_oracle(p)


def test_maximum_fact_and_parent_arity(java, tmp_path):
    p = program(codes=(1,) * 1024, heads=33,
                rules=[(i, [], []) for i in range(32)] +
                      [(32, list(range(992, 1024)), list(range(32)))])
    assert runtime.checked_java([p], java, JDK)[0]["derived"] == list(range(33))
    assert runtime.kernel(p, list(range(33)), tmp_path)["status"] == "KERNEL_CHECKED"


def malformed():
    base = program().model_dump(mode="json")
    rows = []
    for field, value in (
        ("profile", "unversioned"), ("extra", True), ("context_hash", "X" * 64),
        ("codes", [True]), ("codes", [1.0]), ("codes", [4]),
        ("codes", [-1]), ("heads", []), ("heads", ["a", "a"]),
        ("fact_ids", ["x", "x"]), ("codes", [1, 1]),
        ("heads", ["h" + str(i) for i in range(65)]),
        ("fact_ids", ["f" + str(i) for i in range(1025)]),
        ("rules", [dict(base["rules"][0], id=str(i)) for i in range(65)]),
        ("heads", ["x" * 20001]),
    ):
        v = deepcopy(base); v[field] = value; rows.append(json.dumps(v))
    for field, value in (
        ("head", True), ("head", 2), ("head", -1), ("head", "0"),
        ("parents", [0, 0]), ("parents", [True]), ("parents", [2]),
        ("facts", [1]), ("facts", [0, 0]), ("facts", [0] * 33),
        ("parents", [0] * 33), ("negative", True), ("id", ""),
    ):
        v = deepcopy(base); v["rules"][0][field] = value; rows.append(json.dumps(v))
    for field in base:
        v = deepcopy(base); del v[field]; rows.append(json.dumps(v))
    v = deepcopy(base); v["rules"].append(v["rules"][0]); rows.append(json.dumps(v))
    encoded = json.dumps(base)
    rows += ['{"profile":"duplicate",' + encoded[1:], encoded + "{}",
             encoded.replace('"head": 0', '"head": 0, "head": 1', 1),
             "null", "[]", "{", encoded.replace('"fact.0"', '"\\ud800"')]
    return rows


def test_both_codecs_reject_malformed_wire(java):
    rows = malformed()
    for text in rows:
        with pytest.raises(LegalMathError):
            ir.decode(text.encode())
    assert all(r == {"status": "REJECTED", "reason": "INVALID_CONDITIONAL_IR"}
               for r in runtime.java_raw(rows, java, JDK))


def test_unicode_roundtrip_and_hash_identity(java):
    v = program().model_dump(mode="json")
    v["fact_ids"] = ["條款😀\nquote\""]; v["heads"] = ["é", "e\u0301"]
    p = ir.decode(canonical(v))
    reply = runtime.checked_java([p], java, JDK)[0]
    assert reply["decoded"] == v and reply["program_hash"] == p.identity()


@pytest.mark.parametrize("heads", [[], [0], [1], [0, 0], [1, 0], [2], [True]])
def test_missing_forged_and_invalid_results_rejected(heads):
    with pytest.raises(LegalMathError):
        runtime.proof_text(program(), heads)


def test_cycle_only_witness_is_rejected():
    p = program(codes=(), rules=[(0, [], [1]), (1, [], [0])])
    with pytest.raises(LegalMathError):
        runtime.proof_text(p, [0, 1])


def test_line_resource_limit(java):
    with pytest.raises(LegalMathError):
        runtime.java_raw(["{}"] * 4097, java, JDK)


def test_fresh_runtime_verification_and_rehashed_forgery(tmp_path):
    p = program()
    folder = tmp_path / "runtime"
    report = runtime.run(p, folder, JDK)
    assert runtime.verify(p, folder, jdk=JDK) == report
    # Even an attacker who updates the receipt hash cannot cause supplied proof execution.
    path = folder / "proof/ConditionalResult.lean"
    path.write_text("axiom fake : False\n")
    report["kernel"]["certificate_sha256"] = raw_digest(path.read_bytes())
    (folder / "result.json").write_bytes(canonical(report))
    with pytest.raises(LegalMathError):
        runtime.verify(p, folder, jdk=JDK)


def test_java_decoded_input_must_match_request(java, monkeypatch):
    p = program()
    reply = runtime.checked_java([p], java, JDK)[0]
    reply["decoded"]["codes"] = [0]
    monkeypatch.setattr(runtime, "java_raw", lambda *args: [reply])
    with pytest.raises(LegalMathError):
        runtime.checked_java([p], java, JDK)


def test_lowering_preserves_all_source_and_premise_identities():
    from scripts.legal_interpretation_s3_data import retained_inputs
    from legalmath.interpretation.semantics.scoped_standards import compute
    packet, value = retained_inputs()
    scoped = compute(value, packet, {}, {}, [])
    p, mapping = ir.lower(scoped)
    assert len(p.rules) == 20
    assert set(p.codes) == {0, 1, 2, 3}
    for row, mapped in zip(scoped["evaluation"]["results"], mapping["heads"]):
        for key in ("rule_id", "rule_hash", "question", "consequence", "modality"):
            assert mapped[key] == row[key]
    assert ir.reference(p) == [i for i, r in enumerate(scoped["evaluation"]["results"])
                               if r["status"] == "CONDITIONALLY_DERIVED"]
    changed = deepcopy(scoped)
    changed["evaluation"]["results"][0]["status"] = (
        "NOT_DERIVED" if 0 in ir.reference(p) else "CONDITIONALLY_DERIVED")
    with pytest.raises(LegalMathError):
        ir.lower(changed)
