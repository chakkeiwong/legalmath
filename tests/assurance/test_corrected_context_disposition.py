"""A fresh corrected review must not inherit an old decision's need classification."""
from copy import deepcopy

import pytest

from legalmath.canonical import digest
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.phased import capacity_checkpoint, group_review
from legalmath.interpretation.search.providers import Completion
from tests.assurance.test_bounded_product import envelope
from tests.assurance.test_context_need_disposition import setup


@pytest.mark.parametrize("classification", ["mapping", "retained_source"])
def test_corrected_product_review_keeps_new_fact_without_original_classification(
    tmp_path, monkeypatch, classification
):
    args = setup(tmp_path, ("SOURCE_TEXT" if classification == "mapping" else "EXTERNAL_AUTHORITY",))
    product, item, answer, original = args[:4]
    need = original["value"]["context_needs"][0]
    row = dict(assignment_id=item["id"], decision_hash=digest(original["value"]),
               need_hash=digest(need))
    if classification == "retained_source":
        row.update(record_ids=[item["origin_id"]], reason="Reviewed retained passage.")
    save(tmp_path / "classification.json", dict(needs=[row]))
    key = "mapping_needs" if classification == "mapping" else "retained_source_needs"
    save(tmp_path / "individual.json", {key: evidence_file(tmp_path / "classification.json", tmp_path)})
    save(tmp_path / "checkpoint.json", dict(profile=capacity_checkpoint.PROFILE,
        input_hash=product.route.input_hash, calls={},
        individual_reviews=evidence_file(tmp_path / "individual.json", tmp_path)))
    product.capacity_checkpoint = evidence_file(tmp_path / "checkpoint.json", tmp_path)
    before = (tmp_path / "checkpoint.json").read_bytes()

    fresh = deepcopy(original)
    fresh["value"]["reason"] = "The corrected claim still requires an actual client fact."
    fresh["value"]["context_needs"] = [dict(kind="CLIENT_FACT", record_ids=[],
        locators=[], query="Did the client provide consent?", reason="Actual consent is unknown.")]
    monkeypatch.setattr(group_review, "run", lambda *a, **k: [deepcopy(fresh)])
    seen = []

    def complete(request, schema, settings):
        seen.append(request)
        value = deepcopy(fresh["value"])
        value["need_dispositions"] = [dict(need_id="need-0", disposition="STILL_REQUIRED",
            reason="The client fact is absent.", answer_evidence=dict(path="", quote=""), support=[])]
        return Completion(value, {})

    product.provider.complete = complete
    reviews = product.audit_answer("p14", envelope()["original_questions"][0],
                                   answer, [], prefix="corrected-")
    assert len(seen) == 1
    assert seen[0]["payload"]["prior_needs"][0]["route"] == "CLIENT_FACT"
    assert reviews[0]["status"] == "VALIDATED"
    assert reviews[0]["value"]["verdict"] == "UNRESOLVED"
    assert reviews[0]["value"]["context_needs"] == fresh["value"]["context_needs"]
    assert (tmp_path / "checkpoint.json").read_bytes() == before
