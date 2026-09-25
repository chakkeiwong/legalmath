from copy import deepcopy
import subprocess
import zipfile
import pytest

from legalmath.canonical import canonical, digest, loads
from legalmath.catala.generator import ENGINE, generate
from legalmath.errors import LegalMathError
from legalmath.java.manifest import build_candidate, run_java, verify_candidate
from tests.catala.backend_support import JDK, TOOLCHAIN, corpus_groups
from tests.conformance import test_java
from tests.conformance.event_support import event_cases


def build(bundle, output):
    return build_candidate(bundle, output, JDK, backend="catala", catala_toolchain=TOOLCHAIN)


@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    cases = test_java.spi_cases()
    return build(cases[0]["bundle"], tmp_path_factory.mktemp("catala-spi")), cases


@pytest.mark.parametrize("cases", corpus_groups(), ids=lambda cs: cs[0]["id"])
def test_complete_results_for_each_compiled_bundle(cases, tmp_path):
    candidate = build(cases[0]["bundle"], tmp_path)
    assert candidate["manifest"]["decision_engine"] == ENGINE
    assert verify_candidate(candidate, cases, JDK)["passed"]
    source_map = loads((tmp_path / "source-map.json").read_bytes())
    assert all(n["layer"] == "catala" for n in source_map["nodes"] if n["op"] not in ("fact", "rule"))
    for row in loads((tmp_path / "verification-results.json").read_bytes()):
        assert row["java"]["engine_version"] == ENGINE


def test_raw_snapshot_boundary(compiled):
    test_java.test_malformed_snapshot_diagnostics_match(compiled)


@pytest.mark.parametrize("mutation", ["strict", "and", "consent"])
def test_semantic_bundle_mutations_execute_in_catala(compiled, tmp_path, mutation, monkeypatch):
    calls = []
    def builder(bundle, output, jdk):
        candidate = build(bundle, output)
        calls.append(candidate)
        return candidate
    monkeypatch.setattr(test_java, "build_candidate", builder)
    test_java.test_compiled_outcome_mutants(compiled, tmp_path, mutation)
    original = generate(compiled[1][0]["bundle"])["source"]
    assert (tmp_path / "Lowered.catala_en").read_text() != original
    assert len(calls) == 1 and calls[0]["manifest"]["decision_engine"] == ENGINE


def test_modes_events_and_no_plain_java_fallback(compiled):
    candidate, cases = compiled
    rows = [{**deepcopy(cases[0]), "id": mode, "mode": mode} for mode in ("draft", "production", "replay")]
    assert verify_candidate(candidate, rows, JDK, event_cases())["passed"]
    with pytest.raises(subprocess.CalledProcessError) as e:
        run_java(candidate["jar"], rows, JDK)  # cannot silently run the original evaluator
    assert b"Catala generated policy class required" in e.value.stderr


def test_reproducible_self_contained_jar(case, tmp_path):
    a, b = build(case["bundle"], tmp_path / "a"), build(case["bundle"], tmp_path / "b")
    assert a["manifest"] == b["manifest"]
    with zipfile.ZipFile(a["jar"]) as archive:
        assert "catala/runtime/CatalaInteger.class" in archive.namelist()
        meta = loads(archive.read("META-INF/legalmath/catala-build.json"))
        assert meta["generated_sha256"] == a["manifest"]["generated_sha256"]
        assert meta["runtime_sha256"] == a["manifest"]["runtime_sha256"]
        source = archive.read("META-INF/legalmath/sources/Lowered.java")
        assert b"legalmath-catala-" not in source


def test_tampered_compiler_and_unknown_operator_rejected(case, tmp_path):
    fake = tmp_path / "compiler"
    fake.write_text("wrong executable")
    with pytest.raises(LegalMathError) as error:
        build_candidate(case["bundle"], tmp_path / "out", JDK, backend="catala", catala_toolchain={**TOOLCHAIN, "compiler": fake})
    assert error.value.code == "E_HASH_MISMATCH"
    invalid = deepcopy(case["bundle"])
    invalid["rules"][0]["body"]["op"] = "execute_python"
    with pytest.raises(LegalMathError):
        build(invalid, tmp_path / "invalid")
    with pytest.raises(LegalMathError):
        build_candidate(case["bundle"], tmp_path / "implicit", JDK, backend="catala")


def test_engine_substitution_rejected(compiled):
    candidate, cases = compiled
    counterfeit = deepcopy(candidate)
    counterfeit["manifest"]["decision_engine"] = "legalmath-java/0.1.0"
    with pytest.raises(LegalMathError):
        verify_candidate(counterfeit, cases, JDK)


def test_trace_records_a_faulty_catala_calculation(case, tmp_path, monkeypatch):
    """A deliberately wrong compiled literal must appear in both result and trace."""
    from legalmath.catala import backend
    from legalmath.ir.trace import verify_result
    original = backend.generate
    case = deepcopy(case)
    b = case["bundle"]
    b["facts"] = []
    b["rules"] = [deepcopy(b["rules"][0])]
    b["rules"][0]["type"] = "integer"
    b["rules"][0]["body"] = {"node_id": "fault.literal", "op": "literal", "type": "integer", "value": "7"}
    case["snapshot"] = {"subject_id": "synthetic", "facts": {}}
    case["expected"] = {"status": "VALUE", "value": "7"}
    def faulty(bundle):
        generated = original(bundle)
        generated["source"] = generated["source"].replace("definition resultValue equals 7\n", "definition resultValue equals 9\n")
        return generated
    monkeypatch.setattr(backend, "generate", faulty)
    candidate = build(b, tmp_path)
    actual = run_java(candidate["jar"], [case], JDK, candidate["class_name"])[0]
    assert actual["value"] == "9"
    assert next(t for t in actual["trace"] if t["node_id"] == "fault.literal")["value"] == "9"
    assert verify_result(b, case["snapshot"], case["rule_id"], actual)  # honest hash/provenance, wrong calculation
    with pytest.raises(LegalMathError):
        verify_candidate(candidate, [case], JDK)


def test_tampered_jar_rejected(compiled, tmp_path):
    candidate, cases = compiled
    altered = deepcopy(candidate)
    path = tmp_path / "altered.jar"
    from pathlib import Path
    path.write_bytes(Path(candidate["jar"]).read_bytes() + b"altered")
    altered["jar"] = str(path)
    with pytest.raises(LegalMathError) as e:
        verify_candidate(altered, cases, JDK)
    assert e.value.code == "E_HASH_MISMATCH"


def test_operator_status_interactions_and_exact_types(tmp_path):
    from tests.catala.backend_support import interaction_cases
    cases = interaction_cases()
    candidate = build(cases[0]["bundle"], tmp_path)
    assert verify_candidate(candidate, cases, JDK)["passed"]
    rows = {r["id"]: r["java"] for r in loads((tmp_path / "verification-results.json").read_bytes())}
    assert rows["multiple.0"]["status"] == rows["multiple.2"]["status"] == "CONFLICT"
    assert rows["default.guard.error.0"]["reason_codes"] == ["E_INEXACT_SCALE"]
    assert rows["if.lazy.0"]["value"] == "7"
    assert sum(t["node_id"] == cases[0]["bundle"]["rules"][0]["body"]["node_id"] for t in rows["sum.reference.0"]["trace"]) == 1
