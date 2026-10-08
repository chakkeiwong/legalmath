"""Versioned actual-route runtime proofs and rejected branch/method substitutions."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from legalmath.canonical import canonical, digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.semantics import integration
from scripts.legal_interpretation_s4_data import execute_product, ROOT


def test_versioned_context_is_required_and_runtime_method_is_bound():
    from scripts.legal_interpretation_s3_data import retained_inputs
    from scripts.legal_interpretation_demo import options
    v3 = {**options(1), "profile": integration.SCOPED_PROFILE}
    v4 = {**v3, "profile": integration.CONDITIONAL_PROFILE}
    _, value = retained_inputs()
    ctx = integration.investigation_context(v4, None, value)
    assert ctx["profile"] == integration.CONDITIONAL_CONTEXT
    with pytest.raises(LegalMathError):
        integration.context_for(v3, ctx)
    with pytest.raises(LegalMathError):
        integration.context_for(v4, integration.investigation_context(v3, None, value))
    method = integration.configuration(v4)["conditional_runtime"]
    assert {"ConditionalHorn.lean", "ConditionalHorn.java"} <= set(method["method"])
    assert method["lean_sha256"]


@pytest.fixture(scope="module")
def product():
    with TemporaryDirectory(prefix="s4-product-", dir=ROOT / "artifacts") as td:
        runner, dossier, provenance = execute_product(td)
        yield runner, dossier, provenance


def test_actual_dossier_has_exact_runtime_proof_and_whole_stage_replay(product):
    from legalmath.interpretation.assurance.investigation_observations import method, check_stages
    runner, dossier, provenance = product
    report = dossier["semantic_stage"]["report"]
    assert report["profile"] == integration.CONDITIONAL_PROFILE
    conditional = report["conditional_runtime"]
    assert conditional["runtime"]["kernel"]["status"] == "KERNEL_CHECKED"
    assert len(conditional["branches"]) == len(report["standards"]["branches"]) == 6
    for branch, original in zip(conditional["branches"], report["standards"]["branches"]):
        assert branch["branch_id"] == original["branch_id"]
        assert len(branch["rule_results"]) == 18
        for row, rule in zip(branch["rule_results"], original["results"]):
            assert row["rule_id"] == rule["rule_id"]
            assert row["derived"] == (rule["status"] == "CONDITIONALLY_DERIVED")
        assert branch["legacy_formula_relationship"] == "NOT_ESTABLISHED"
    assert check_stages(ROOT, dossier, method(runner), runner)["execution_complete"]
    assert all(r["original"]["quote"] == r["projected"]["quote"] for r in provenance)


@pytest.mark.parametrize("fault", ["branch", "rule", "lowering", "proof", "missing"])
def test_runtime_branch_and_proof_forgery_rejected(product, fault):
    runner, dossier, _ = product
    folder = ROOT / dossier["semantic_stage"]["directory"]
    path = folder / "result.json"
    original = path.read_bytes()
    altered = loads(original)
    part = altered["conditional_runtime"]
    if fault == "branch":
        part["branches"][0]["branch_id"] = part["branches"][1]["branch_id"]
    elif fault == "rule":
        part["branches"][0]["rule_results"][0]["derived"] ^= True
    elif fault == "lowering":
        part["lowering"]["heads"][0]["modality"] = "MUST_NOT"
    elif fault == "proof":
        part["runtime"]["kernel"]["derived"] = []
    else:
        del altered["conditional_runtime"]
    inputs = loads((folder / "inputs.json").read_bytes())
    try:
        path.write_bytes(canonical(altered))
        with pytest.raises(LegalMathError):
            integration.verify(folder, inputs["packet"], inputs["candidates"], inputs["questions"],
                inputs["options"], inputs["at"], context=inputs["context"], jdk=runner.jdk)
    finally:
        path.write_bytes(original)
