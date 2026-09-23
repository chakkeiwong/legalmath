from copy import deepcopy
from legalmath.review.amendment import changes
from legalmath.conformance import evaluate_case
from legalmath.events.replay import replay
from tests.conformance.event_support import event_cases


def test_changed_definition_invalidates_dependants_but_preserves_history(case):
    old = deepcopy(case["bundle"])
    original_result = evaluate_case(case)
    new = deepcopy(old)
    new["interpretations"][0]["statement"] += " Synthetic amended definition."
    report = changes(old, new)
    assert report["affected_rule_ids"] == [case["rule_id"]]
    assert report["changed_definitions"] and report["required_actions"]
    assert evaluate_case(case) == original_result
    req = event_cases()[2]["request"]
    opening_version = req["events"][0]["source_bundle_hash"]
    assert replay(req)["source_bundle_hash"] == opening_version
    assert report["obligation_migration"] == "REQUIRES_SEPARATE_REVIEW"
