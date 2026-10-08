from legalmath.drafting.provider import StubProvider
from legalmath.drafting.validate import propose


def test_bounded_repair_and_candidate_only(case):
    inventory = {"source_spans": case["bundle"]["source_spans"]}
    good = propose(inventory, StubProvider(["not JSON", case["bundle"]]))
    assert good["status"] == "CANDIDATE" and len(good["attempts"]) == 2
    assert good["authority"] == "NONE" and good["review_state"] == "UNREVIEWED"
    bad = propose(inventory, StubProvider(["not JSON"]))
    assert bad["status"] == "MANUAL_REVIEW" and len(bad["attempts"]) == 3
    missing = propose({"source_spans": []}, StubProvider([case["bundle"]]))
    assert missing["status"] == "MANUAL_REVIEW"
