from copy import deepcopy
from pathlib import Path
import shutil

import pytest

from legalmath.prospectus import purchaser_cases as p
from legalmath.prospectus.common import read


@pytest.fixture
def dossier():
    return read(p.DOSSIER / "cases.json"), read(p.DOSSIER / "sources.json")


def changed(case, **values):
    c = deepcopy(case)
    for name, value in values.items():
        c["snapshot"]["facts"][name]["value"] = value
    return c


def test_real_pair_and_controlled_qib_reversal(dossier):
    d, s = dossier
    public, private = p.paired_cases(d, s)
    assert p.evaluate(public)["status"] == "PASS"
    assert p.evaluate(private)["status"] == "FAIL"
    assert p.evaluate(changed(private, purchaser_is_qib=True))["status"] == "PASS"
    # Same institution acting for an ineligible beneficial account fails.
    intermediary = changed(private, purchaser_is_qib=True, own_account=False)
    assert p.evaluate(intermediary)["status"] == "FAIL"
    assert p.evaluate(changed(intermediary, account_is_qib=True))["status"] == "PASS"


@pytest.mark.parametrize("disqualifier", ["purchaser_is_us_person_reg_s", "us_beneficial_account", "issuer_affiliate"])
def test_offshore_route_cannot_hide_us_benefit_or_affiliation(dossier, disqualifier):
    d, s = dossier
    private = p.paired_cases(d, s)[1]
    offshore = changed(private, purchaser_is_us_person_reg_s=False, us_beneficial_account=False,
                       offshore_transaction=True, issuer_affiliate=False)
    assert p.evaluate(offshore)["status"] == "PASS"
    assert p.evaluate(changed(offshore, **{disqualifier: True}))["status"] == "FAIL"
    assert p.evaluate(changed(offshore, offshore_transaction=False))["status"] == "FAIL"


def test_issuer_name_is_not_a_decision_label(dossier):
    d, s = dossier
    c = p.paired_cases(d, s)[1]
    c["id"] = "future-unknown-issuer"
    c["snapshot"]["subject_id"] = "future-unknown-issuer"
    assert p.evaluate(c)["status"] == "FAIL"
    assert p.evaluate(changed(c, public_us_distribution=True, restricted_144a_reg_s_distribution=False))["status"] == "PASS"


def test_unknown_conflict_stale_and_scope_abstain(dossier):
    d, s = dossier
    cases = p.challenge_cases(d, s)
    partial = [c for c in cases if c["id"].endswith((".unknown", ".conflict")) or c["id"] == "stale-investor"]
    assert len(partial) == 19
    assert all(p.evaluate(c)["status"] in {"UNKNOWN", "CONFLICT"} for c in partial)
    assert p.evaluate(cases[0], stage="secondary_resale")["status"] == "UNSUPPORTED_SCOPE"
    assert p.evaluate(cases[0], action="conversion")["status"] == "UNSUPPORTED_SCOPE"


def test_inconsistent_conflict_evidence_is_rejected(dossier):
    from legalmath.errors import LegalMathError
    d, s = dossier
    c = next(c for c in p.challenge_cases(d, s) if c["id"].endswith(".conflict"))
    c["snapshot"]["evidence"]["/public_us_distribution"] = ["unrelated:old-evidence"]
    with pytest.raises(LegalMathError) as error:
        p.evaluate(c)
    assert error.value.code == "E_INTEGRITY"


def test_source_and_derivative_tampering(dossier, tmp_path):
    _, sources = dossier
    source = next(iter(sources.values()))
    for name in ("path", "text_path"):
        target = tmp_path / source[name]; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p.ROOT / source[name], target)
    assert p.verify_sources({"one": source}, root=tmp_path)
    for name in ("path", "text_path"):
        target = tmp_path / source[name]; original = target.read_bytes()
        target.write_bytes(original + b" ")
        with pytest.raises(ValueError, match="Changed retained"):
            p.verify_sources({"one": source}, root=tmp_path)
        target.write_bytes(original)


def test_missing_changed_or_cross_instrument_anchors_rejected(dossier):
    d, s = dossier
    damaged = deepcopy(d); damaged["instruments"][1]["anchors"] = []
    with pytest.raises(ValueError, match="Missing material"):
        p.validate_dossier(damaged, s)
    damaged = deepcopy(d); damaged["instruments"][1]["anchors"][0]["start"] += 1
    with pytest.raises(ValueError, match="Changed source span"):
        p.validate_dossier(damaged, s)
    damaged = deepcopy(d); damaged["instruments"][1]["anchors"][0]["source"] = d["instruments"][0]["source"]
    with pytest.raises(ValueError, match="another prospectus"):
        p.validate_dossier(damaged, s)


def test_quality_labels_and_invalid_denomination_are_not_inputs(dossier):
    d, s = dossier
    altered = deepcopy(d); altered["instruments"][0]["expected_approval"] = True
    with pytest.raises(ValueError, match="quality labels"):
        p.validate_dossier(altered, s)
    altered = deepcopy(d); altered["scenario"]["principal_usd"] = 199999
    with pytest.raises(ValueError, match="denomination"):
        p.validate_dossier(altered, s)
    altered["scenario"]["principal_usd"] = 200001
    with pytest.raises(ValueError, match="denomination"):
        p.validate_dossier(altered, s)


def test_proof_and_discriminating_mutations(tmp_path):
    result = p.prove(tmp_path)
    assert result["equivalence"] == "UNSAT"
    assert len(result["mutations"]) == 6
    assert result["natural_language_entailment"] == "NOT_PROVED"


def test_positive_gate_cannot_erase_bank_qualifications(dossier):
    d, s = dossier
    missing = {"decision": "QUALIFIED", "may_execute_transaction": False,
               "limitations": ["internal policy unavailable", "sanctions identity unresolved"]}
    for case in p.paired_cases(d, s):
        result = p.attach_bank_investigation(p.evaluate(case), missing)
        assert result["bank_investigation"] == missing
        assert result["may_execute_transaction"] is False
        assert result["complete_legal_compliance"] == "NOT_ESTABLISHED"
