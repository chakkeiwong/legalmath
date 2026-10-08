"""Adversarial intake and phase tests; synthetic fixtures establish mechanics only."""
from copy import deepcopy
import pytest

from legalmath.prospectus import closure_sources as s, closure_reviews as r
from legalmath.prospectus import evidence_closure as ec, closure_phases as p
from legalmath.prospectus import master_control as c
from legalmath.prospectus.common import digest
from tests.prospectus.test_closure_sources import setup as source_setup, DATES, BEFORE
from tests.prospectus.test_closure_control import setup as control_setup
from tests.prospectus.test_feature_investigation import setup as bank_setup


def test_selected_source_change_requires_current_scope_review(tmp_path):
    _, issue, docs, admission, _ = source_setup(tmp_path)
    baseline = {"documents": docs, "issues": [issue]}
    changed = deepcopy(issue)
    changed["source_language_qualification"] = "Synthetic reviewed language"
    admission["issue_binding"] = digest(changed)
    review = {"reviewer": admission["reviewer"], "reviewed_at": BEFORE,
              "before_sha256": digest(issue), "after_sha256": digest(changed),
              "reason": "Synthetic change", "anchors": admission["findings"]["language"]["anchors"]}
    bundle = {"issues": [{"id": issue["id"], "before_sha256": digest(issue), "issue": changed, "review": review}]}
    with pytest.raises(ValueError, match="admission"):
        s.candidate_inventory(baseline, bundle, [], tmp_path, DATES)
    result = s.candidate_inventory(baseline, bundle, [admission], tmp_path, DATES)
    assert result["issues"][0] == changed
    assert "source_language_qualification" not in issue
    bundle["issues"][0]["issue"]["issuer"] = "another issuer"
    with pytest.raises(ValueError, match="identity"):
        s.candidate_inventory(baseline, bundle, [admission], tmp_path, DATES)


def test_new_document_is_loaded_but_cannot_silently_replace_old_edition(tmp_path):
    _, issue, docs, _, _ = source_setup(tmp_path)
    baseline = {"documents": docs, "issues": [issue]}
    with pytest.raises(ValueError, match="new document identity"):
        s.candidate_inventory(baseline, {"documents": docs}, [], tmp_path, DATES)
    added = deepcopy(docs["document"]); added["id"] = "new-document"
    result = s.candidate_inventory(baseline, {"documents": {"new-document": added}}, [], tmp_path, DATES)
    assert result["issues"] == baseline["issues"] and len(result["documents"]) == 2
    added["text_sha256"] = "wrong"
    with pytest.raises(ValueError, match="hash mismatch"):
        s.candidate_inventory(baseline, {"documents": {"new-document": added}}, [], tmp_path, DATES)


def test_acquisition_timestamp_preserved_and_receipt_mismatch_rejected(tmp_path):
    from legalmath.prospectus.feature_investigation import investigate
    issue, docs, row, store, bank = bank_setup(tmp_path)
    doc = docs["document"]
    c.write(tmp_path / "receipt.json", {"original": doc["original"], "sha256": doc["sha256"], "at": BEFORE})
    doc["acquisition_receipt"] = "receipt.json"
    result = investigate(row, issue, docs, tmp_path, bank, store)
    reg = store.json(result["joined_request"]["bank_request"]["registry_sha256"])
    assert reg["document"]["recorded_at"] == BEFORE
    c.write(tmp_path / "receipt.json", {"original": doc["original"], "sha256": "wrong", "at": BEFORE})
    with pytest.raises(ValueError, match="different source bytes"):
        investigate(row, issue, docs, tmp_path, bank, store)


def factual_bundle(tmp_path, issue):
    path = tmp_path / "actual-facts.json"
    values = {"debt_legal_form": True, "qualifying_wrapper": False,
              "qualifying_contingent_loss_absorption": False, "plain_debt_or_deposit": False}
    c.write(path, values)
    source = {"id": "intake-synthetic", "path": path.name, "sha256": c.sha(path), "kind": "facts",
              "origin": "synthetic:test", "observed_at": "2026-01-01T00:00:00Z", "provenance": "synthetic",
              "media_type": "application/json",
              "effective_from": "2026-01-01T00:00:00Z", "effective_until": None,
              "fresh_until": "2027-01-01T00:00:00Z", "dependencies": []}
    return {"sources": [source], "issues": {issue["id"]: {
        "product_assertions": {k: [{"source": source["id"], "pointer": "/" + k}] for k in values}}}}


def test_facts_join_the_real_bank_and_reject_tampering(tmp_path):
    from legalmath.prospectus.feature_investigation import investigate
    issue, docs, row, store, bank = bank_setup(tmp_path)
    bundle = factual_bundle(tmp_path, issue)
    request, assertions = s.apply_fact_intake(bank, store, tmp_path, bundle, issue["id"])
    result = investigate(row, issue, docs, tmp_path, request, store, product_assertions_sha256=assertions)
    scope = result["bank_investigation"]["calculations"]["scope"]["in_scope_product"]
    assert scope["status"] == "KNOWN" and scope["value"] is False
    assert len(result["bank_investigation"]["inventory"]) == 14 and not result["may_execute_transaction"]
    bundle["issues"][issue["id"]]["context"] = {"instrument_id": "forged"}
    with pytest.raises(ValueError, match="overwrite derived"):
        s.apply_fact_intake(bank, store, tmp_path, bundle, issue["id"])
    bundle["issues"][issue["id"]].pop("context")
    (tmp_path / "actual-facts.json").write_text("{}")
    with pytest.raises(ValueError, match="changed"):
        s.apply_fact_intake(bank, store, tmp_path, bundle, issue["id"])


def test_linked_fact_bytes_invalidate_only_consumers(tmp_path, monkeypatch):
    current = control_setup(tmp_path, monkeypatch)
    path = tmp_path / "facts.txt"; path.write_text("one")
    c.write(ec.DATA / "facts.json", {"sources": [{"path": "facts.txt"}]})
    for phase in ec.PHASES:
        ec.run_phase(phase, current)
    path.write_text("two")
    assert ec.current_phase("S1", current) and ec.current_phase("S2", current)
    assert not ec.current_phase("S3", current) and not ec.current_phase("S7", current)


def test_retained_http_bytes_checked_even_outside_phase_folder(tmp_path, monkeypatch):
    current = control_setup(tmp_path, monkeypatch)
    path = tmp_path / "response.bin"; path.write_bytes(b"source")
    monkeypatch.setattr(ec, "execute", lambda *a: {"status": "QUALIFIED", "remaining": ["source review pending"],
                        "external_outputs": {"response.bin": c.sha(path)}})
    ec.run_phase("S0", current)
    path.write_bytes(b"tampered")
    assert not ec.current_phase("S0", current)
    with pytest.raises(ValueError, match="external source"):
        ec.verify(current)


def test_clause_review_cannot_implement_its_own_expected_disposition(tmp_path, monkeypatch):
    _, issue, docs, admission, _ = source_setup(tmp_path)
    from legalmath.prospectus.loss_absorption_reader import analyze_issue
    row = analyze_issue(issue, docs, tmp_path)
    item = row["evidence"][0]
    monkeypatch.setattr(c, "ROOT", tmp_path)
    review = {"issue_id": issue["id"], "evidence_id": item["id"], "issue_binding": digest(issue),
              "evidence_binding": digest(item), "reviewer": admission["reviewer"], "reviewed_at": BEFORE,
              "reason": "Counterexample requires implementation repair", "anchors": admission["findings"]["stage"]["anchors"],
              "expected_disposition": "unimplemented-change"}
    report = r.clause_audit(tmp_path / "audit", {"issues": [issue], "documents": docs}, [row], [row], [review])
    assert report["status"] == "WAITING_EVIDENCE"
    assert c.read(tmp_path / "audit/clause-reviews.json")[0]["status"] == "SEMANTIC_REPAIR_REQUIRED"
    assert row["evidence"][0] == item
    review["evidence_binding"] = "wrong"
    with pytest.raises(ValueError, match="changed"):
        r.clause_audit(tmp_path / "audit2", {"issues": [issue], "documents": docs}, [row], [row], [review])


def protocol(issuer="Unseen Issuer"):
    return {"cohort": "synthetic-only", "cases": [{"id": "unseen", "issuer": issuer, "family": "unseen",
            "url": "https://example.org/final.pdf", "mechanism_stratum": "ordinary"}],
            "selection_rule": "Synthetic unit fixture", "no_substitution": True,
            "exposure_audit": "Synthetic fixture has no external exposure",
            "adjudicator": {"name": "Synthetic reviewer", "role": "independent_adjudicator"},
            "rubric": "Synthetic rubric", "criterion": "ALL_SELECTED_ADJUDICATED_ZERO_CONTRADICTIONS",
            "request_budget": 1, "nonclaims": "No real fresh-case result"}


def test_challenge_rejects_exposed_family_and_unapproved_budget(tmp_path, monkeypatch):
    data = {"issues": [{"id": "old", "issuer": "Danske Bank A/S"}], "documents": {}}
    with pytest.raises(ValueError, match="exposed"):
        r.validate_protocol(protocol("Danske Bank A/S"), data)
    current = control_setup(tmp_path, monkeypatch)
    c.write(ec.DATA / "challenge.json", protocol())
    with pytest.raises(ValueError, match="budget"):
        r.challenge(tmp_path / "report", current, data)


def test_challenge_cannot_freeze_after_exposure_or_reuse_changed_method(tmp_path, monkeypatch):
    current = control_setup(tmp_path, monkeypatch)
    monkeypatch.setattr(ec, "policy", lambda: {"max_challenge_requests": 1})
    (tmp_path / "method").write_text("v1")
    monkeypatch.setattr(ec, "method", lambda: {"method": c.sha(tmp_path / "method")})
    c.write(ec.DATA / "challenge.json", protocol())
    c.write(ec.DATA / "challenge-evidence.json", {"already": "opened"})
    with pytest.raises(ValueError, match="after challenge evidence"):
        r.challenge(tmp_path / "report", current, {"issues": [], "documents": {}})
    (ec.DATA / "challenge-evidence.json").unlink()
    result = r.challenge(tmp_path / "report", current, {"issues": [], "documents": {}})
    assert result["status"] == "WAITING_EVIDENCE"
    (tmp_path / "method").write_text("v2")
    with pytest.raises(ValueError, match="Frozen method"):
        r.challenge(tmp_path / "report2", current, {"issues": [], "documents": {}})


def test_human_intake_rejects_arbitrary_or_obsolete_acceptance(tmp_path, monkeypatch):
    current = control_setup(tmp_path, monkeypatch)
    for phase in ec.PHASES:
        ec.run_phase(phase, current)
    with pytest.raises(ValueError, match="Incomplete human review"):
        r.human_review(tmp_path / "review", current, {"decision": "ACCEPT"})
    report = r.human_review(tmp_path / "review", current, None)
    assert report["status"] == "WAITING_HUMAN" and not report["human_acceptance"]


def test_source_work_review_advances_only_exact_current_issue_set(tmp_path, monkeypatch):
    packet, issue, docs, admission, decision = source_setup(tmp_path)
    closure = s.resolve(packet, issue, docs, tmp_path, DATES, [admission], [decision])
    monkeypatch.setattr(c, "ROOT", tmp_path)
    monkeypatch.setattr(p, "dates", lambda: DATES)
    directory = tmp_path / "s1"
    c.write(directory / "issues" / (issue["id"] + ".json"), closure)
    current = {"phases": {"S1": {"directory": "s1"}}}
    order = {"gap": "G12", "issuer": "Synthetic", "needed": "Synthetic agreement",
             "status": "OPEN", "issue_ids": [issue["id"]]}
    review = {"gap": "G12", "requirement_binding": digest(order), "reviewer": admission["reviewer"],
              "reviewed_at": BEFORE, "reason": "Synthetic source review",
              "issue_bindings": {issue["id"]: digest(issue)}, "closure_bindings": {issue["id"]: digest(closure)},
              "anchors": admission["findings"]["stage"]["anchors"]}
    data = {"issues": [issue], "documents": docs}
    result = r.source_work_review([deepcopy(order)], [review], data, current)
    assert result[0]["status"] == "SATISFIED_UNDER_RECORDED_REVIEW"
    assert not result[0]["human_acceptance"]
    bad = deepcopy(review)
    bad["issue_bindings"]["unrelated"] = "x"
    with pytest.raises(ValueError, match="affected issue"):
        r.source_work_review([deepcopy(order)], [bad], data, current)
    closure["open_references"] = 1
    c.write(directory / "issues" / (issue["id"] + ".json"), closure)
    review["closure_bindings"][issue["id"]] = digest(closure)
    with pytest.raises(ValueError, match="open dependencies"):
        r.source_work_review([deepcopy(order)], [review], data, current)


def test_scoped_human_acceptance_cannot_clear_other_phase_gaps(tmp_path, monkeypatch):
    current = control_setup(tmp_path, monkeypatch)
    monkeypatch.setattr(ec, "execute", lambda *a: {"status": "QUALIFIED", "remaining": ["Actual source absent"],
                        "assessment": DATES})
    for phase in ec.PHASES:
        ec.run_phase(phase, current)
    folder = tmp_path / "review"
    r.human_review(folder, current, None)
    binding = c.read(folder / "human-review-packet.json")["packet_binding"]
    review = {"packet_binding": binding, "reviewer": {"name": "Synthetic human fixture", "role": "human_legal_reviewer"},
              "qualifications": "Test only; no real acceptance", "independence": True,
              "scope": "Synthetic unit-test mechanics", "assessment": DATES, "decision": "ACCEPT",
              "reason": "Synthetic attestation only", "reviewed_at": BEFORE}
    c.write(tmp_path / "attestation.json", review)
    review["attestation"] = {"path": "attestation.json", "sha256": c.sha(tmp_path / "attestation.json")}
    result = r.human_review(folder, current, review)
    assert result["human_acceptance"] and result["status"] == "QUALIFIED"
    assert not ec.refresh(current)["all_gaps_closed"]
    review["packet_binding"] = "stale"
    with pytest.raises(ValueError, match="obsolete"):
        r.human_review(folder, current, review)
