from copy import deepcopy
import json
from pathlib import Path
import pytest

from legalmath.conformance import evaluate_case
from legalmath.ir.trace import verify_result
from legalmath.java.manifest import build_candidate, run_java, verify_candidate

ROOT = Path(__file__).resolve().parents[2]
JDK = ROOT / ".localresources/java-toolchain/jdk-17.0.20.1+1"


def spi_cases():
    path = ROOT / "examples/java-dry-run/spec"
    bundle = json.loads((path / "spi-control.bundle.json").read_text())
    rows = json.loads((path / "decision-cases.json").read_text())
    return [{**c, "bundle": bundle, "rule_id": c.get("rule_id", "spi.streamlining"),
             "expected": {"status": c["expected_status"],
                          **({"blocking_inputs": c["expected_blocking_inputs"]} if "expected_blocking_inputs" in c else {})}}
            for c in rows]


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    cases = spi_cases()
    build = build_candidate(cases[0]["bundle"], tmp_path_factory.mktemp("java"), JDK)
    return build, cases


def test_migrated_spi_scenarios_use_generated_class(compiled):
    build, cases = compiled
    report = verify_candidate(build, cases, JDK)
    assert report["passed"] and report["jar_sha256"] == build["manifest"]["jar_sha256"]


def test_full_language_semantics_and_native_hashes(compiled):
    build, _ = compiled
    cases = json.loads((ROOT / "docs/specs/v0.1/fixtures/decision-cases.json").read_text())["cases"]
    for c, java in zip(cases, run_java(build["jar"], cases, JDK)):
        python = evaluate_case(c)
        assert verify_result(c["bundle"], c["snapshot"], c["rule_id"], java)
        assert {k:v for k,v in python.items() if k not in ("engine_version", "result_hash")} == {k:v for k,v in java.items() if k not in ("engine_version", "result_hash")}, c["id"]
        assert java["engine_version"] != python["engine_version"]


@pytest.mark.parametrize("mutation", ["strict", "and", "consent"])
def test_compiled_outcome_mutants(compiled, tmp_path, mutation):
    _, cases = compiled
    bundle = deepcopy(cases[0]["bundle"])
    financial = next(r for r in bundle["rules"] if r["id"] == "spi.financial")
    if mutation == "strict": financial["body"]["args"][0]["cmp"] = "gt"
    elif mutation == "and": financial["body"]["op"] = "all"
    else:
        def replace(node):
            if isinstance(node, dict):
                if node.get("op") == "fact" and node.get("name") == "active_consent":
                    node.clear();node.update(node_id="mutant.consent", op="literal", type="bool", value=True)
                else:
                    for value in node.values(): replace(value)
            elif isinstance(node, list):
                for value in node: replace(value)
        replace(bundle)
    build = build_candidate(bundle, tmp_path, JDK)
    rows = run_java(build["jar"], cases, JDK, build["class_name"])
    changed = [c["id"] for c, r in zip(cases, rows) if r["status"] != c["expected"]["status"]]
    assert changed, mutation


def test_compiler_rejects_unknown_operator(compiled, tmp_path):
    _, cases = compiled
    bundle = deepcopy(cases[0]["bundle"])
    bundle["rules"][0]["body"]["op"] = "execute_python"
    from legalmath.errors import LegalMathError
    with pytest.raises(LegalMathError): build_candidate(bundle, tmp_path, JDK)


def test_malformed_snapshot_diagnostics_match(compiled):
    build, cases = compiled
    requests = []
    for mutation in ("missing", "wrong_type", "evidence_duplicate", "interval", "metadata_float", "extra", "huge", "array", "null", "subject", "facts", "invalid_name"):
        c = deepcopy(cases[0])
        f = c["snapshot"]["facts"]["portfolio"]
        if mutation == "missing": del c["snapshot"]["facts"]["portfolio"]
        if mutation == "wrong_type": f["type"] = "integer"
        if mutation == "evidence_duplicate": f["evidence_ids"] *= 2
        if mutation == "interval": f["valid_until"] = f["valid_from"]
        if mutation == "metadata_float": continue  # rejected at strict JSON boundary, tested separately
        if mutation == "extra": f["extra"] = True
        if mutation == "huge": f["value"] = "9" * 6000
        if mutation == "array": c["snapshot"] = []
        if mutation == "null": c["snapshot"] = None
        if mutation == "subject": c["snapshot"]["subject_id"] = 3
        if mutation == "facts": c["snapshot"]["facts"] = None
        if mutation == "invalid_name": c["snapshot"]["facts"]["WRONG"] = deepcopy(f)
        requests.append(c)
    for c, java in zip(requests, run_java(build["jar"], requests, JDK, build["class_name"])):
        python = evaluate_case(c)
        assert {k:v for k,v in java.items() if k not in ("engine_version", "result_hash")} == {k:v for k,v in python.items() if k not in ("engine_version", "result_hash")}
