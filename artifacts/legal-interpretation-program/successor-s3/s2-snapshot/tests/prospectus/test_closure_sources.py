from copy import deepcopy

import pytest

from legalmath.prospectus import closure_sources as s, source_obligations
from legalmath.prospectus.common import digest
from legalmath.prospectus.master_control import sha, read
from legalmath.prospectus.loss_absorption_reader import analyze_issue
from legalmath.transaction.evidence import Registry, Store
from legalmath.transaction.intake import record
from tests.prospectus.test_loss_absorption import fixture, ORDINARY

AT = "2026-10-04T00:00:00Z"
BEFORE = "2026-10-03T00:00:00Z"
DATES = s.assessment(AT, AT)


def setup(tmp_path):
    issue, docs, raw = fixture(tmp_path, [ORDINARY + " The Agency Agreement dated 1 May 2025 applies."])
    row = analyze_issue(issue, docs, tmp_path)
    packet = source_obligations.build(row, issue, docs, tmp_path, as_of=AT)
    image = tmp_path / "reviewed.png"
    image.write_bytes(b"synthetic page comparison fixture, not a real PDF review")
    quote = {"document": "document", "source_binding": s.source_binding(docs["document"]), "page": 1,
             "quote": "Agency Agreement dated 1 May 2025"}
    admission = {"document": "document", "issue_id": issue["id"], "issue_binding": digest(issue),
                 "source_binding": s.source_binding(docs["document"]), "assessment": DATES,
                 "reviewer": {"name": "synthetic mechanical fixture", "role": "agent"}, "reviewed_at": BEFORE,
                 "stage": "final", "execution_required": False,
                 "edition": "synthetic 1 May 2025", "option": "synthetic", "controlling_language": "English fixture",
                 "precedence": "synthetic", "amendment_scope": "synthetic", "amendment_cutoff": AT, "scope": "synthetic",
                 "provenance": {"kind": "supplied", "observed_at": BEFORE,
                     "evidence": [{"path": "original.pdf", "sha256": sha(tmp_path / "original.pdf")}]},
                 "reviewed_pages": [1], "omission_check": {"page_hashes": [digest(raw["pages"][0]["text"])],
                     "verdict": "PASS", "reason": "Synthetic complete page"},
                 "page_reviews": [{"page": 1, "text_sha256": digest(raw["pages"][0]["text"]),
                     "render_path": "reviewed.png", "render_sha256": sha(image), "verdict": "PASS", "reason": "Synthetic fixture"}],
                 "findings": {k: {"reason": "Synthetic source binding", "anchors": [quote]} for k in
                              ("edition", "stage", "option", "language", "precedence", "amendments")}}
    ref = packet["references"][0]
    decision = {"issue_id": issue["id"], "reference_id": ref["id"], "reference_binding": digest(ref),
                "packet_binding": s.packet_binding(packet, issue, DATES), "reviewer": admission["reviewer"],
                "reviewed_at": BEFORE, "disposition": "SATISFIED", "reason": "Synthetic test only",
                "admission_bindings": {"document": digest(admission)}, "anchors": [quote], "dependencies": {}}
    return packet, issue, docs, admission, decision


def resolve(tmp_path, items):
    packet, issue, docs, admission, decision = items
    return s.resolve(packet, issue, docs, tmp_path, DATES, [admission], [decision])


def test_bound_decision_revalidates_and_does_not_claim_legal_completeness(tmp_path):
    items = setup(tmp_path)
    result = resolve(tmp_path, items)
    assert result["open_references"] == 0
    assert not result["all_dependencies_found"] and not result["human_acceptance"] and not result["may_execute_transaction"]
    packet, issue, docs, admission, decision = items
    assert s.revalidate(result, packet, issue, docs, tmp_path, DATES, [admission], [decision]) == result


@pytest.mark.parametrize("mutation", ["edition", "issue", "option", "scope", "stage", "quote", "page", "render",
                                     "provenance", "future", "amendment", "decision", "new_reference"])
def test_invalid_or_stale_evidence_reopens_decision(tmp_path, mutation):
    items = setup(tmp_path)
    packet, issue, docs, admission, decision = items
    prior = resolve(tmp_path, items)
    assert prior["open_references"] == 0
    if mutation == "edition": docs["document"]["edition"] = "wrong edition"
    elif mutation == "issue": issue["id"] = "wrong issue"; packet["issue_id"] = issue["id"]
    elif mutation == "option": issue["documents"][0]["option"] = "II"
    elif mutation == "scope": admission["reviewed_pages"] = []
    elif mutation == "stage": admission["stage"] = "preliminary"
    elif mutation == "quote": admission["findings"]["edition"]["anchors"][0]["quote"] = "invented quote"
    elif mutation == "page": admission["page_reviews"][0]["text_sha256"] = "0" * 64
    elif mutation == "render": (tmp_path / "reviewed.png").write_bytes(b"changed")
    elif mutation == "provenance": (tmp_path / "original.pdf").write_bytes(b"changed")
    elif mutation == "future": admission["reviewed_at"] = "2027-01-01T00:00:00Z"
    elif mutation == "amendment": admission["amendment_cutoff"] = BEFORE
    elif mutation == "decision": admission["findings"]["amendments"]["reason"] = "A changed review"
    elif mutation == "new_reference": packet["references"].append({**packet["references"][0], "id": "new"})
    current = resolve(tmp_path, items)
    assert current["open_references"] >= 1
    with pytest.raises(ValueError, match="reopen"):
        s.revalidate(prior, packet, issue, docs, tmp_path, DATES, [admission], [decision])


def test_duplicate_reviews_and_reference_cycles_cannot_discharge(tmp_path):
    packet, issue, docs, admission, decision = setup(tmp_path)
    assert s.resolve(packet, issue, docs, tmp_path, DATES, [admission, admission], [decision])["open_references"] == 1
    assert s.resolve(packet, issue, docs, tmp_path, DATES, [admission], [decision, decision])["open_references"] == 1
    decision["dependencies"] = {decision["reference_id"]: digest(decision)}
    assert s.resolve(packet, issue, docs, tmp_path, DATES, [admission], [decision])["open_references"] == 1


def test_unrelated_issue_reviews_do_not_invalidate_this_issue(tmp_path):
    items = setup(tmp_path)
    packet, issue, docs, admission, decision = items
    unrelated = {**admission, "issue_id": "another issue", "stage": "bad"}
    result = s.resolve(packet, issue, docs, tmp_path, DATES, [admission, unrelated], [decision])
    assert result == resolve(tmp_path, items)


def test_dependency_review_change_reopens_parent(tmp_path):
    packet, issue, docs, admission, first = setup(tmp_path)
    packet["references"].append({**packet["references"][0], "id": "second"})
    first["packet_binding"] = s.packet_binding(packet, issue, DATES)
    second = {**deepcopy(first), "reference_id": "second", "reference_binding": digest(packet["references"][1])}
    first["dependencies"] = {"second": digest(second)}
    result = s.resolve(packet, issue, docs, tmp_path, DATES, [admission], [first, second])
    assert result["open_references"] == 0
    second["reason"] = "Revised judgment"
    changed = s.resolve(packet, issue, docs, tmp_path, DATES, [admission], [first, second])
    assert changed["open_references"] == 1


def test_unknown_observation_is_not_the_requested_known_at(tmp_path):
    from tests.prospectus.test_feature_investigation import setup as bank_setup
    from legalmath.prospectus.feature_investigation import investigate
    issue, docs, row, store, bank = bank_setup(tmp_path)
    result = investigate(row, issue, docs, tmp_path, bank, store)
    registry = store.json(result["joined_request"]["bank_request"]["registry_sha256"])
    assert registry["document"]["recorded_at"] is None
    check = Registry(store, registry).check(["document"], **DATES)
    assert any("observation time not established" in p for p in check["issues"])


def test_dated_registry_detects_expiry_future_and_unknown_amendment(tmp_path):
    store = Store(tmp_path)
    row = s.intake_record(store, b"evidence", kind="law", origin="synthetic", observed_at=BEFORE,
                          provenance="synthetic", effective_from=BEFORE, fresh_until=AT)
    check = Registry(store, {"old": row}).check(["old"], **DATES)
    assert any("freshness" in p for p in check["issues"])
    successor = {**row, "recorded_at": None, "supersedes": ["old"]}
    check = Registry(store, {"old": row, "new": successor}).check(["old"], **DATES)
    assert any("amendment requires reassessment" in p for p in check["issues"])
    row["recorded_at"] = "2027-01-01T00:00:00Z"
    assert any("not known" in p for p in Registry(store, {"future": row}).check(["future"], **DATES)["issues"])
