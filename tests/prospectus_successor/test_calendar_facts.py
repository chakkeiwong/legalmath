"""Calendar observations must change actual legal answers without inventing facts."""
from copy import deepcopy

import pytest

from legalmath.prospectus.successor import calendar_facts, law_facts, service
from legalmath.prospectus.successor.contracts import VERSION, digest, validate_request
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_calendar_oracle import expected, verify

NOW = "2026-10-13T00:00:00Z"
LATER = "2026-10-14T00:00:00Z"
RULE = "Supplied conditional timing rule; legal applicability and counting convention are not established."


def world(tmp_path, start="2024-03-01", end="2024-03-15", days=14, convention="CIVIL_DATE_GAP"):
    path = tmp_path / "dates.txt"
    path.write_text("\f".join([RULE, "start=" + start, "end=" + end, "late=2024-03-02", "one=1"]))
    request = {"version": VERSION, "bundle": {
        "instrument_id": "bond", "purpose": "review", "issue_date": NOW,
        "effective_at": NOW, "known_at": NOW, "dependencies": [],
        "documents": [{"id": "d", "path": str(path), "sha256": digest(path.read_bytes()),
                       "format": "text", "language": "en", "authority": "Synthetic declared dates",
                       "known_from": NOW, "document_date": NOW}]}}
    p1 = service.source_product(request, tmp_path)
    graph = p1["payload"]["graph"]

    def source(prefix, value):
        u = next(u for u in graph["units"] if u["raw"] == prefix + value)
        return anchor(u, len(prefix), len(prefix) + len(value))

    identities = {"instrument_id": "bond", "jurisdiction": "Test", "event_id": "meeting"}
    times = {"valid_from": NOW, "known_from": NOW, "observed_at": NOW}
    basis = {"id": "notice", "authority": "Supplied conditional rule", "jurisdiction": "Test",
             "edition": "1", "source": source("", RULE), "instrument_id": "bond",
             "valid_from": NOW, "known_from": NOW, "premises": ["timely"]}
    row = {**identities, **times, "id": "dates", "basis_id": "notice", "name": "timely",
           "source": basis["source"], "rule_reading": RULE, "convention": convention, "days": days,
           "start": {**identities, **times, "value": start, "role": "notice", "source": source("start=", start)},
           "end": {**identities, **times, "value": end, "role": "meeting", "source": source("end=", end)}}
    data = {"law_bases": [basis], "facts": [], "calendar_facts": [row]}
    p2 = service.construction_product(p1, tmp_path)
    p3 = service.interpretation_product(p1, p2)
    return {"P1": p1, "P2": p2, "P3": p3, "P5": service.financial_product(p1, p2, p3)}, data, source


def answer(products, data, root):
    p4 = service.law_product(products["P1"], products["P3"], law_input=data)
    output = service.consume({**products, "P4": p4}, root, mode="current")
    assert output["may_execute_transaction"] is False
    assert output["independent_legal_acceptance"] is False
    return output["questions"]["Q4"]


@pytest.mark.parametrize("start,end,days,convention,status", [
    ("2024-03-01", "2024-03-15", 14, "CIVIL_DATE_GAP", "YES"),
    ("2024-03-02", "2024-03-15", 14, "CIVIL_DATE_GAP", "NO"),
    ("2024-03-01", "2024-03-15", 14, "CLEAR_CIVIL_DAYS", "NO"),
    ("2024-02-29", "2024-03-15", 14, "CLEAR_CIVIL_DAYS", "YES"),
    ("1900-02-28", "1900-03-01", 2, "CIVIL_DATE_GAP", "NO"),
    ("2000-02-28", "2000-03-01", 2, "CIVIL_DATE_GAP", "YES"),
    ("2100-02-28", "2100-03-01", 2, "CIVIL_DATE_GAP", "NO"),
    ("2023-12-31", "2024-01-03", 3, "CIVIL_DATE_GAP", "YES"),
    ("2024-03-25T12:00:00+01:00", "2024-03-31T12:00:00+02:00", 6, "ELAPSED_24_HOUR_DAYS", "NO"),
    ("2024-10-21T12:00:00+02:00", "2024-10-27T12:00:00+01:00", 6, "ELAPSED_24_HOUR_DAYS", "YES"),
    ("2024-03-01T08:00:00+08:00", "2024-03-07T00:00:00Z", 6, "ELAPSED_24_HOUR_DAYS", "YES"),
    ("2024-03-01T00:00:00.000001Z", "2024-03-07T00:00:00Z", 6, "ELAPSED_24_HOUR_DAYS", "NO"),
])
def test_complete_current_consumer_matches_independent_calendar(tmp_path, start, end, days, convention, status):
    products, data, _ = world(tmp_path, start, end, days, convention)
    q = answer(products, data, tmp_path)
    assert q["status"] == status
    row = q["value"][0]["calendar_calculations"][0]
    assert verify(row)["status"] == status
    assert row["actual_event_established"] is False
    assert row["legal_counting_convention_established"] is False


@pytest.mark.parametrize("part", ["start", "end"])
def test_missing_dates_reach_unknown(tmp_path, part):
    products, data, _ = world(tmp_path)
    data["calendar_facts"][0][part] = None
    q = answer(products, data, tmp_path)
    assert q["status"] == "UNKNOWN"
    assert q["value"][0]["calendar_calculations"][0]["exact_comparison"] is None


@pytest.mark.parametrize("part,field", [(p, f) for p in ("basis", "rule", "start", "end")
    for f in ("valid_from", "known_from", "valid_until", "known_until", "observed_at")
    if (p, f) != ("basis", "observed_at")])
def test_temporally_unavailable_dates_do_not_prove_premises(tmp_path, part, field):
    products, data, _ = world(tmp_path)
    row = data["calendar_facts"][0]
    target = data["law_bases"][0] if part == "basis" else row if part == "rule" else row[part]
    target["valid_from"] = target["known_from"] = "2026-10-12T00:00:00Z"
    target[field] = NOW if field.endswith("until") else LATER
    assert answer(products, data, tmp_path)["status"] == "UNKNOWN"


@pytest.mark.parametrize("field,value", [
    ("days", True), ("days", 0), ("days", -1), ("days", "14"), ("days", 14.0),
    ("convention", None), ("convention", "BUSINESS_DAYS"), ("convention", []),
    ("event_id", " "), ("rule_reading", ""), ("valid_until", False), ("observed_at", False),
])
def test_malformed_rules_refuse_even_when_start_missing(tmp_path, field, value):
    products, data, _ = world(tmp_path)
    data["calendar_facts"][0]["start"] = None
    data["calendar_facts"][0][field] = value
    with pytest.raises(ValueError):
        answer(products, data, tmp_path)


@pytest.mark.parametrize("field,value", [
    ("value", False), ("value", "2024-02-30"), ("value", "20240315"), ("value", "2024-03-14"),
    ("value", "2024-03-15T00:00:00Z"), ("role", ""), ("event_id", "another-meeting"),
    ("instrument_id", "other"), ("jurisdiction", "other"), ("known_until", 0), ("observed_at", []),
])
def test_missing_start_does_not_mask_invalid_end(tmp_path, field, value):
    products, data, _ = world(tmp_path)
    data["calendar_facts"][0]["start"] = None
    data["calendar_facts"][0]["end"][field] = value
    with pytest.raises(ValueError):
        answer(products, data, tmp_path)


@pytest.mark.parametrize("value", ["2024-03-01T00:00:00", "2024-03-01",
                                   "2024-03-01T00:00:00.0000001Z",
                                   "2024-03-01T00:00:00+25:00", "2024-03-01T00:00:00+01:60",
                                   "2024-03-01T00:00:60Z"])
def test_elapsed_dates_cannot_hide_precision_or_timezone(tmp_path, value):
    products, data, _ = world(tmp_path, value, "2024-03-07T00:00:00Z", 6, "ELAPSED_24_HOUR_DAYS")
    with pytest.raises(ValueError):
        answer(products, data, tmp_path)


def test_duplicate_rule_boolean_and_ratio_overrides_refuse(tmp_path):
    products, original, source = world(tmp_path)
    for mutation in ("id", "rule", "boolean", "ratio"):
        data = deepcopy(original)
        row = data["calendar_facts"][0]
        if mutation in {"id", "rule"}:
            extra = deepcopy(row)
            if mutation == "rule":
                extra["id"], extra["days"] = "other", 13
            data["calendar_facts"].append(extra)
        elif mutation == "boolean":
            data["facts"] = [{"name": "timely", "basis_id": "notice"}]
        else:
            identity = {k: row[k] for k in (*calendar_facts.IDENTITY, "valid_from", "known_from", "observed_at")}
            operand = {**identity, "value": "1", "unit": "vote", "source": source("one=", "1")}
            data["ratio_facts"] = [{**identity, "id": "ratio", "basis_id": "notice", "name": "timely",
                                    "source": row["source"], "operator": "GE", "threshold": "1",
                                    "numerator": operand, "denominator": operand}]
        with pytest.raises(ValueError):
            answer(products, data, tmp_path)


def test_conflicting_dates_and_alternative_conventions_remain_distinct(tmp_path):
    products, original, source = world(tmp_path)
    data = deepcopy(original)
    extra = deepcopy(data["calendar_facts"][0])
    extra["id"] = "other-observation"
    extra["start"].update(value="2024-03-02", source=source("late=", "2024-03-02"))
    data["calendar_facts"].append(extra)
    assert answer(products, data, tmp_path)["status"] == "CONFLICT"
    data = deepcopy(original)
    basis = deepcopy(data["law_bases"][0])
    basis["id"] = "alternative"
    data["law_bases"].append(basis)
    extra = deepcopy(data["calendar_facts"][0])
    extra.update(id="other-reading", basis_id="alternative", convention="CLEAR_CIVIL_DAYS")
    data["calendar_facts"].append(extra)
    data["law_relation"] = "ALTERNATIVE_READINGS"
    q = answer(products, data, tmp_path)
    assert q["status"] == "UNKNOWN"
    assert [r["status"] for r in q["value"]] == ["YES", "NO"]


def test_current_mode_recomputes_resealed_temporal_conclusion(tmp_path):
    products, data, _ = world(tmp_path)
    p4 = service.law_product(products["P1"], products["P3"], law_input=data)
    p4["payload"]["question"]["status"] = "NO"
    forged = service.seal("P4", products["P1"]["payload"]["request"]["bundle"],
                          {"P1": products["P1"]["sha256"], "P3": products["P3"]["sha256"]}, p4["payload"])
    with pytest.raises(ValueError, match="Current interpretation/calculation differs"):
        service.consume({**products, "P4": forged}, tmp_path, mode="current")


def test_independent_oracle_detects_permissive_calculator(tmp_path, monkeypatch):
    products, data, _ = world(tmp_path, start="2024-03-02")
    original = calendar_facts.compare
    monkeypatch.setattr(calendar_facts, "compare", lambda *args: (True, original(*args)[1]))
    row = answer(products, data, tmp_path)["value"][0]["calendar_calculations"][0]
    with pytest.raises(ValueError, match="independent integer oracle"):
        verify(row)


@pytest.mark.parametrize("value", [None, False, 0, {}, ""])
def test_nonlist_input_refused_at_both_request_boundaries(tmp_path, value):
    products, data, _ = world(tmp_path)
    data["calendar_facts"] = value
    with pytest.raises(ValueError, match="Calendar facts must be a list"):
        answer(products, data, tmp_path)
    request = deepcopy(products["P1"]["payload"]["request"])
    request["calendar_facts"] = value
    with pytest.raises(ValueError, match="Calendar facts must be a list"):
        validate_request(request)


def test_reversed_dates_and_missing_authority_refuse(tmp_path):
    products, data, _ = world(tmp_path, "2024-03-15", "2024-03-01")
    with pytest.raises(ValueError, match="ends before"):
        answer(products, data, tmp_path)
    data["law_bases"] = []
    with pytest.raises(ValueError, match="declared legal basis"):
        answer(products, data, tmp_path)


def test_source_request_calendar_input_reaches_ordinary_law_stage(tmp_path):
    products, data, _ = world(tmp_path)
    request = {**deepcopy(products["P1"]["payload"]["request"]), **data}
    p1 = service.source_product(request, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    p3 = service.interpretation_product(p1, p2)
    p4 = service.law_product(p1, p3)
    result = service.consume({"P1": p1, "P2": p2, "P3": p3, "P4": p4,
                              "P5": service.financial_product(p1, p2, p3)}, tmp_path, mode="current")
    assert result["questions"]["Q4"]["status"] == "YES"


def test_small_complete_gregorian_ladder_agrees_with_independent_formula():
    dates = ["0001-01-01", "1600-02-28", "1600-03-01", "1900-02-28", "1900-03-01",
             "1999-12-31", "2000-02-28", "2000-02-29", "2000-03-01", "2024-02-28",
             "2024-02-29", "2024-03-01", "2100-02-28", "2100-03-01", "9999-12-31"]
    for i, start in enumerate(dates):
        for end in dates[i:]:
            for convention in ("CIVIL_DATE_GAP", "CLEAR_CIVIL_DAYS"):
                for days in (1, 3, 6, 14):
                    target = expected(start, end, convention, days)
                    yes, exact = calendar_facts.compare(calendar_facts.operand_value(start, convention),
                        calendar_facts.operand_value(end, convention), convention, days)
                    assert ("YES" if yes else "NO") == target["status"]
                    assert exact == target["exact_comparison"]
