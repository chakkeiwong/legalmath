from copy import deepcopy
import pytest
from legalmath.events.replay import replay
from legalmath.events.records import create_stream, append_event
from legalmath.errors import LegalMathError
from tests.conformance.event_support import event_cases


@pytest.mark.parametrize("case", event_cases(), ids=lambda c: c["id"])
def test_preserved_event_outcomes(case):
    result = replay(case["request"])
    for k, v in case["expected"].items(): assert result[k] == v


def test_incomplete_and_future_completeness():
    c = event_cases()[1]["request"]
    c["completeness"] = None
    assert replay(c)["state"] == "UNKNOWN"
    c = event_cases()[1]["request"]
    c["completeness"]["complete_through"] = "2026-09-05T00:00:00.000000Z"
    assert replay(c)["state"] == "UNKNOWN"


def test_order_attribution_and_duplicates():
    c = event_cases()[0]["request"]
    c["events"][1]["occurred_at"] = c["events"][0]["occurred_at"]
    c["header"]["ordering_authority"] = None
    assert replay(c)["reason_codes"] == ["E_ORDER_UNRESOLVED"]
    c = event_cases()[0]["request"]
    c["events"].append(deepcopy(c["events"][0]))
    assert replay(c)["generation"] == 1
    c["events"][-1]["evidence_id"] = "wrong"
    assert replay(c)["reason_codes"] == ["E_EVENT_ID_COLLISION"]
    c = event_cases()[0]["request"]
    c["events"][0]["subject"] = "wrong"
    assert replay(c)["reason_codes"] == ["E_EVENT_ATTRIBUTION"]


def test_late_timely_correction_preserves_historical_result():
    c = event_cases()[5]["request"]
    old = replay(c)
    performance = {**c["events"][0], "kind": "obligation.performed", "id": "late.record", "sequence": 4,
        "occurred_at": "2026-09-01T12:00:00.000000Z", "recorded_at": "2026-09-05T00:00:00.000000Z", "evidence_id": "late.evidence"}
    for key in ("activation", "deadline", "source_bundle_hash"): performance.pop(key)
    c["events"].append(performance)
    assert replay(c)["status"] == old["status"] == "BREACHED"
    c["known_at"] = "2026-09-05T00:00:00.000000Z"
    new = replay(c)
    assert new["status"] == "SATISFIED_ON_TIME" and new["result_hash"] != old["result_hash"]


def test_no_deadline_never_overdue_and_late_without_seal_open():
    c = event_cases()[5]["request"]
    c["events"][0]["deadline"] = None
    assert replay(c)["status"] == "OPEN"
    c = event_cases()[-1]["request"]
    c["events"] = [e for e in c["events"] if e["kind"] != "watermark"]
    assert replay(c)["status"] == "OPEN"


def test_persistent_duplicate_and_sequence_collision(db):
    c = event_cases()[0]["request"]
    with db.transaction() as con:
        create_stream(db, con, c["header"])
        r = append_event(db, con, c["header"]["stream_id"], c["events"][0], 1)
        assert append_event(db, con, c["header"]["stream_id"], c["events"][0], 1) == r
        bad = {**c["events"][1], "sequence": 1}
        with pytest.raises(LegalMathError) as e: append_event(db, con, c["header"]["stream_id"], bad, 2)
        assert e.value.code == "E_SEQUENCE_COLLISION"


def test_late_withdrawal_is_unknown_until_known_and_observation_retained():
    c = event_cases()[0]["request"]
    c["events"][1]["recorded_at"] = "2026-09-05T00:00:00.000000Z"
    # At the original knowledge cutoff a completeness claim would be false:
    # retain an incomplete export instead of asserting absence of withdrawal.
    c["completeness"] = None
    assert replay(c)["state"] == "UNKNOWN"
    c["known_at"] = "2026-09-05T00:00:00.000000Z"
    c["completeness"] = {"complete_from": c["header"]["inception"], "complete_through": c["valid_at"], "recorded_at": c["known_at"], "evidence_id": "complete.corrected"}
    observed = {**c["events"][1], "id": "observed", "sequence": 3, "kind": "transaction.observed", "evidence_id": "observed.evidence", "occurred_at": "2026-09-02T00:00:00.000000Z"}
    c["events"].append(observed)
    r = replay(c)
    assert r["state"] == "WITHDRAWN" and r["violation_candidates"] == ["observed"] and "observed" in r["event_ids"]


def test_initial_snapshot_needs_authenticated_reviewer(db):
    from legalmath.review.lifecycle import Lifecycle
    from tests.helpers import IDENTITIES
    Lifecycle(db).register(IDENTITIES)
    header = event_cases()[0]["request"]["header"]
    header["initial_snapshot"] = {"as_of": "2026-09-01T00:00:00.000000Z", "state": "ACTIVE", "generation": 1,
        "reviewer_id": "meaning", "evidence_id": "reviewed.initial", "recorded_at": "2026-09-01T00:00:00.000000Z"}
    with db.transaction() as con:
        with pytest.raises(LegalMathError): create_stream(db, con, header, reviewer="author")
        assert create_stream(db, con, header, reviewer="meaning")["revision"] == 1
