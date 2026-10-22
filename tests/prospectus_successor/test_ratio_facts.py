"""Exact conditional legal arithmetic and actual final-consumer controls."""
from copy import deepcopy

import pytest

from legalmath.prospectus.successor import law_facts, service
from legalmath.prospectus.successor.contracts import VERSION, digest
from legalmath.prospectus.successor.occurrences import anchor

TIME = "2026-01-01T00:00:00Z"
FUTURE = "2026-01-02T00:00:00Z"
RULE = "The hypothetical reviewed rule requires at least 75 percent of eligible participating voting weight."


def world(tmp_path, numerator="75", denominator="100", *, operator="GE", threshold="0.75"):
    path = tmp_path / "source.txt"
    path.write_text("\f".join([RULE, "numerator=" + numerator, "denominator=" + denominator,
                              "alternative=74", "Eligibility is an explicit supplied hypothesis."]))
    request = {"version": VERSION, "bundle": {
        "instrument_id": "bond", "purpose": "review", "issue_date": TIME,
        "effective_at": TIME, "known_at": TIME, "dependencies": [],
        "documents": [{"id": "d", "path": str(path), "sha256": digest(path.read_bytes()),
                       "format": "text", "language": "en", "authority": "Hypothetical development source",
                       "document_date": TIME, "known_from": TIME}]},
        "scope": {"Q1": {"complete": False}, "Q2": {"complete": False}, "Q4": {"complete": False}}}
    p1 = service.source_product(request, tmp_path)
    graph = p1["payload"]["graph"]

    def source(prefix, value):
        unit = next(u for u in graph["units"] if u["raw"] == prefix + value)
        return anchor(unit, len(prefix), len(prefix) + len(value))

    times = {"valid_from": TIME, "known_from": TIME, "observed_at": TIME}
    identity = {"instrument_id": "bond", "jurisdiction": "Test jurisdiction", "event_id": "meeting-1"}
    basis = {"id": "majority", "authority": "Supplied hypothetical reading", "edition": "1",
             "instrument_id": "bond", "jurisdiction": identity["jurisdiction"], "source": source("", RULE),
             "valid_from": TIME, "known_from": TIME, "premises": ["threshold"]}
    calculation = {**identity, **times, "id": "tally-1", "name": "threshold", "basis_id": "majority",
                   "source": basis["source"], "operator": operator, "threshold": threshold,
                   "numerator": {**identity, **times, "value": numerator, "unit": "eligible-vote-weight",
                                 "source": source("numerator=", numerator)},
                   "denominator": {**identity, **times, "value": denominator, "unit": "eligible-vote-weight",
                                   "source": source("denominator=", denominator)}}
    law_input = {"law_bases": [basis], "facts": [], "ratio_facts": [calculation]}
    p2 = service.construction_product(p1, tmp_path)
    p3 = service.interpretation_product(p1, p2)
    products = dict(P1=p1, P2=p2, P3=p3, P5=service.financial_product(p1, p2, p3))
    return products, law_input, source


def answer(products, law_input, root):
    p4 = service.law_product(products["P1"], products["P3"], law_input=law_input)
    report = service.consume({**products, "P4": p4}, root, mode="current")
    assert not report["may_execute_transaction"] and not report["independent_legal_acceptance"]
    assert report["questions"]["Q3"]["status"] == "PARTIAL"
    assert report["questions"]["Q4"]["value"][0]["actual_exercise"] == "NOT_ESTABLISHED"
    return report["questions"]["Q4"]


@pytest.mark.parametrize("numerator,denominator,operator,threshold,status", [
    ("75", "100", "GE", "0.75", "YES"),
    ("74.999", "100", "GE", "0.75", "NO"),
    ("50", "100", "GT", "0.5", "NO"),
    ("50.001", "100", "GT", "0.5", "YES"),
    ("50", "100", "GE", "0.5", "YES"),
    ("0", "100", "GE", "0.75", "NO"),
    ("100", "100", "GE", "1", "YES"),
    ("0", "0", "GE", "0.75", "UNKNOWN"),
    ("0.3", "0.4", "GE", "0.75", "YES"),
    ("2999999999999999999999999999999", "4000000000000000000000000000000", "GE", "0.75", "NO"),
])
def test_exact_boundaries_reach_current_consumer(tmp_path, numerator, denominator, operator, threshold, status):
    products, data, _ = world(tmp_path, numerator, denominator, operator=operator, threshold=threshold)
    q = answer(products, data, tmp_path)
    assert q["status"] == status
    calculation = q["value"][0]["calculations"][0]
    assert calculation["numerator"]["source"]["quote"] == numerator
    assert calculation["denominator"]["source"]["quote"] == denominator
    assert calculation["status"] == status
    if status != "UNKNOWN":
        assert calculation["exact_comparison"]["method"] == "exact rational cross multiplication"


@pytest.mark.parametrize("part", ["numerator", "denominator"])
def test_missing_total_is_unknown(tmp_path, part):
    products, data, _ = world(tmp_path)
    data["ratio_facts"][0][part] = None
    q = answer(products, data, tmp_path)
    assert q["status"] == "UNKNOWN"
    assert "Missing " + part in q["value"][0]["calculations"][0]["unresolved"]


@pytest.mark.parametrize("part,field,value", [
    (part, field, value)
    for part in ("numerator", "denominator", "rule", "basis")
    for field, value in (("known_from", FUTURE), ("valid_from", FUTURE),
                         ("known_until", TIME), ("valid_until", TIME), ("observed_at", FUTURE))
    if (part, field) != ("basis", "observed_at")
])
def test_unavailable_numeric_evidence_is_not_counted(tmp_path, part, field, value):
    products, data, _ = world(tmp_path)
    row = data["law_bases"][0] if part == "basis" else data["ratio_facts"][0]
    target = row if part in {"basis", "rule"} else row[part]
    if field.endswith("until"):
        target[field.replace("until", "from")] = "2025-01-01T00:00:00Z"
    target[field] = value
    assert answer(products, data, tmp_path)["status"] == "UNKNOWN"


@pytest.mark.parametrize("part", ["numerator", "denominator", "rule"])
def test_invalid_numeric_period_refused_even_with_missing_other_operand(tmp_path, part):
    products, data, _ = world(tmp_path)
    row = data["ratio_facts"][0]
    target = row if part == "rule" else row[part]
    target["valid_until"] = TIME
    if part != "rule":
        row["denominator" if part == "numerator" else "numerator"] = None
    with pytest.raises(ValueError, match="Invalid validity"):
        answer(products, data, tmp_path)


@pytest.mark.parametrize("field,value,reason", [
    ("event_id", "another-meeting", "event mismatch"),
    ("instrument_id", "another-bond", "subject"),
    ("jurisdiction", "another-country", "jurisdiction"),
    ("unit", "headcount", "units differ"),
])
def test_mixed_totals_refused(tmp_path, field, value, reason):
    products, data, _ = world(tmp_path)
    data["ratio_facts"][0]["numerator"][field] = value
    with pytest.raises(ValueError, match=reason):
        answer(products, data, tmp_path)


@pytest.mark.parametrize("value", [-1, True, 0.75, "-1", "NaN", "Infinity", "1e3", " 75", "", "1" * 129])
def test_untyped_nonfinite_or_unbounded_input_refused(tmp_path, value):
    products, data, _ = world(tmp_path)
    data["ratio_facts"][0]["numerator"]["value"] = value
    with pytest.raises(ValueError, match="finite decimal"):
        answer(products, data, tmp_path)


def test_numerator_larger_than_total_refused(tmp_path):
    products, data, _ = world(tmp_path, "101", "100")
    with pytest.raises(ValueError, match="exceeds"):
        answer(products, data, tmp_path)


def test_changed_value_and_hidden_source_refused(tmp_path):
    products, data, _ = world(tmp_path)
    data["ratio_facts"][0]["numerator"]["value"] = "74"
    with pytest.raises(ValueError, match="source literal"):
        answer(products, data, tmp_path)
    data["ratio_facts"][0]["numerator"]["value"] = "75"
    graph = deepcopy(products["P1"]["payload"]["graph"])
    unit = data["ratio_facts"][0]["numerator"]["source"]["unit"]
    next(u for u in graph["units"] if u["id"] == unit)["visible"] = False
    with pytest.raises(ValueError, match="unavailable"):
        law_facts.assess(products["P1"]["payload"]["request"]["bundle"], data["law_bases"], [], graph,
                         ratio_facts=data["ratio_facts"])


def test_conflicting_tallies_reach_existing_conflict_logic(tmp_path):
    products, data, source = world(tmp_path)
    other = deepcopy(data["ratio_facts"][0])
    other["id"] = "independent-tally"
    other["numerator"].update(value="74", source=source("alternative=", "74"))
    data["ratio_facts"].append(other)
    q = answer(products, data, tmp_path)
    assert q["status"] == "CONFLICT"
    assert {r["status"] for r in q["value"][0]["calculations"]} == {"YES", "NO"}


def test_manual_boolean_cannot_override_computed_or_missing_total(tmp_path):
    products, data, _ = world(tmp_path, "74")
    data["facts"] = [{"name": "threshold", "basis_id": "majority", "instrument_id": "bond",
                     "jurisdiction": "Test jurisdiction", "value": True,
                     "source": data["law_bases"][0]["source"],
                     "valid_from": TIME, "known_from": TIME, "observed_at": TIME}]
    for numerator in (data["ratio_facts"][0]["numerator"], None):
        data["ratio_facts"][0]["numerator"] = numerator
        with pytest.raises(ValueError, match="also be supplied"):
            answer(products, data, tmp_path)


def test_arithmetic_cannot_supply_missing_eligibility(tmp_path):
    products, data, _ = world(tmp_path)
    data["law_bases"][0]["premises"].append("eligible")
    q = answer(products, data, tmp_path)
    assert q["status"] == "UNKNOWN"
    assert q["value"][0]["premises"] == {"threshold": True, "eligible": None}


@pytest.mark.parametrize("change", ["operator", "threshold", "event"])
def test_different_rule_or_event_for_same_name_refused(tmp_path, change):
    products, data, _ = world(tmp_path)
    other = deepcopy(data["ratio_facts"][0])
    other["id"] = "other"
    if change == "event":
        other["event_id"] = "another-meeting"
    elif change == "operator":
        other["operator"] = "GT"
    else:
        other["threshold"] = "0.5"
    data["ratio_facts"].append(other)
    with pytest.raises(ValueError, match="Different event"):
        answer(products, data, tmp_path)


def test_different_predicates_cannot_join_different_meetings(tmp_path):
    products, data, _ = world(tmp_path)
    data["law_bases"][0]["premises"].append("quorum")
    other = deepcopy(data["ratio_facts"][0])
    other.update(id="quorum-tally", name="quorum", event_id="meeting-2")
    for label in ("numerator", "denominator"):
        other[label]["event_id"] = "meeting-2"
    data["ratio_facts"].append(other)
    with pytest.raises(ValueError, match="Different events require separate"):
        answer(products, data, tmp_path)


@pytest.mark.parametrize("field,value", [("operator", []), ("operator", "EQ"),
                                          ("threshold", "0"), ("threshold", "1.1")])
def test_invalid_declared_comparison_refused(tmp_path, field, value):
    products, data, _ = world(tmp_path)
    data["ratio_facts"][0][field] = value
    with pytest.raises(ValueError, match="Ratio threshold"):
        answer(products, data, tmp_path)


def test_request_and_phase_input_paths_match(tmp_path):
    products, data, _ = world(tmp_path)
    expected = answer(products, data, tmp_path)
    request = {**products["P1"]["payload"]["request"], **data}
    report = service.assess(request, tmp_path)
    assert report["questions"]["Q4"] == expected


def test_no_numeric_input_preserves_legacy_explanation(tmp_path):
    products, data, _ = world(tmp_path)
    data.pop("ratio_facts")
    q = answer(products, data, tmp_path)
    assert q["status"] == "UNKNOWN"
    assert "calculations" not in q["value"][0]
    data["ratio_facts"] = []
    assert answer(products, data, tmp_path) == q


@pytest.mark.parametrize("value", [None, {}, "75"])
def test_invalid_optional_input_refused_at_public_boundaries(tmp_path, value):
    products, data, _ = world(tmp_path)
    data["ratio_facts"] = value
    with pytest.raises(ValueError, match="must be a list"):
        answer(products, data, tmp_path)
    with pytest.raises(ValueError, match="must be a list"):
        service.source_product({**products["P1"]["payload"]["request"], **data}, tmp_path)
