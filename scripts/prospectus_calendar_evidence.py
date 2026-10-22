"""Original BASF conditional meeting routes with explicit hypothetical dates."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_calendar_oracle import verify

OLD = "docs/implementation/prospectus-execution-authority/attempts/law-applicability/attempt-006"
NOW = "2026-10-13T00:00:00Z"
TIMING = {"meeting_notice14", "deadline_notice14", "registration_received_third_day", "six_day_obtaining"}
DATES = [
    "2024-02-26", "2024-02-27", "2024-02-29", "2024-03-01", "2024-03-02",
    "2024-03-12", "2024-03-13", "2024-03-15",
    "2024-03-09T12:00:00+01:00", "2024-03-09T12:00:00.000001+01:00",
    "2024-03-15T12:00:00+01:00", "2024-03-25T12:00:00+01:00",
    "2024-03-31T12:00:00+02:00", "2024-10-21T12:00:00+02:00",
    "2024-10-27T12:00:00+01:00",
]


def require(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    path = Path(path)
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    with path.open("xb") as stream:
        stream.write(gzip.compress(raw, mtime=0) if path.suffix == ".gz" else raw)


def execute(root, products, data, cases=None):
    p4 = service.law_product(products["P1"], products["P3"], cases=cases, law_input=data)
    answer = service.consume({**products, "P4": p4}, root, mode="current")
    require(answer["may_execute_transaction"] is False and answer["independent_legal_acceptance"] is False,
            "Conditional date calculation acquired transaction authority")
    return {"input": data, "P4": p4, "answer": answer}


def setup(root, attempt):
    old_products = load(root / OLD / "common-products.json.gz")
    path = attempt / "hypothetical-dates.txt"
    with path.open("x") as out:
        out.write("Synthetic development dates, not observed meeting/holder events.\f" +
                  "\f".join("date=" + d for d in DATES))
    request = deepcopy(old_products["P1"]["payload"]["request"])
    request["bundle"]["documents"].append({
        "id": "calendar-hypotheses", "path": str(path.relative_to(root)),
        "sha256": service.digest(path.read_bytes()), "format": "text", "language": "en",
        "authority": "Explicit hypothetical temporal evidence", "document_date": NOW, "known_from": NOW})
    p1 = service.source_product(request, root)
    p2 = service.construction_product(p1, root)
    p3 = service.interpretation_product(p1, p2)
    products = {"P1": p1, "P2": p2, "P3": p3, "P5": service.financial_product(p1, p2, p3)}
    graph = p1["payload"]["graph"]
    units = {u["id"]: u for u in graph["units"]}
    data = load(root / OLD / "favorable-deposit-input.json.gz")
    data["facts"] = [f for f in data["facts"] if f["name"] not in TIMING]
    identities = {"instrument_id": request["bundle"]["instrument_id"],
                  "jurisdiction": data["law_bases"][0]["jurisdiction"], "event_id": "hypothetical-meeting"}
    times = {"valid_from": NOW, "known_from": NOW, "observed_at": NOW}

    def operand(value, role):
        unit = next(u for u in graph["units"] if u["document"] == "calendar-hypotheses" and u["raw"] == "date=" + value)
        return {**identities, **times, "value": value, "role": role, "source": anchor(unit, 5, len(unit["raw"]))}

    definitions = [
        ("meeting_notice14", "notice_registration", 1, "2024-03-01", "2024-03-15",
         14, "CIVIL_DATE_GAP", "call_date", "meeting_date"),
        ("deadline_notice14", "notice_registration", 2, "2024-03-01", "2024-03-12",
         14, "CIVIL_DATE_GAP", "call_date", "registration_deadline_date"),
        ("registration_received_third_day", "notice_registration", 2, "2024-03-12", "2024-03-15",
         3, "CIVIL_DATE_GAP", "registration_received_civil_date", "meeting_date"),
        ("six_day_obtaining", "enumerated_ticket_route", 3, "2024-03-09T12:00:00+01:00", "2024-03-15T12:00:00+01:00",
         6, "ELAPSED_24_HOUR_DAYS", "selected_preparatory_acts_completed", "appointed_meeting_instant"),
    ]
    data["calendar_facts"] = []
    for name, basis, page, start, end, days, convention, start_role, end_role in definitions:
        unit = units["contract:p" + str(page) + ":l0"]
        data["calendar_facts"].append({
            **identities, **times, "id": name + "-dates", "basis_id": basis, "name": name,
            "source": anchor(unit, 0, len(unit["raw"])),
            "rule_reading": f"Conditional arithmetic of {name}: {end_role} minus {start_role} under the explicitly selected convention; legal applicability unestablished.",
            "convention": convention, "days": days,
            "start": operand(start, start_role), "end": operand(end, end_role)})
    return products, data, operand


def cases(root, attempt):
    from legalmath.prospectus.successor import calendar_facts
    products, baseline, operand = setup(root, attempt)
    save(attempt / "common-products.json.gz", products)
    rows = []

    def change_date(data, name, part, value):
        row = next(r for r in data["calendar_facts"] if r["name"] == name)
        row[part] = None if value is None else operand(value, row[part]["role"])

    def set_fact(data, name, value):
        fact = next(f for f in data["facts"] if f["name"] == name)
        unit = next(u for u in products["P1"]["payload"]["graph"]["units"] if u["id"] == fact["source"]["unit"])
        quote = name + "=" + str(value) + "; supplied hypothesis only."
        at = unit["raw"].index(quote)
        fact.update(value=value, source=anchor(unit, at, at + len(quote)))

    def call_date(data, value):
        for name in ("meeting_notice14", "deadline_notice14"):
            change_date(data, name, "start", value)

    def add(name, expected, mutate=lambda d: None, *, scope="selected whole conditional route"):
        data = deepcopy(baseline)
        mutate(data)
        record = execute(root, products, data)
        q = record["answer"]["questions"]["Q4"]
        require(q["status"] == expected, name + " has wrong Q4 status: " + q["status"])
        checked = []
        for basis in q["value"]:
            for c in basis.get("calendar_calculations", []):
                if c["status"] != "UNKNOWN":
                    checked.append({"id": c["id"], **verify(c)})
        if rows:
            reference = load(attempt / "cases" / (rows[0]["case"] + ".json.gz"))["answer"]["questions"]
            require(all(record["answer"]["questions"][k] == reference[k] for k in ("Q1", "Q2", "Q5", "Q6")),
                    "Unrelated question changed with calendar input")
        save(attempt / "cases" / (name + ".json.gz"), record)
        rows.append({"case": name, "status": q["status"], "expected": expected,
                     "scope": scope, "independent_comparisons": checked})

    add("boundary-no-registration", "YES")
    add("notice-one-day-late", "NO", lambda d: call_date(d, "2024-03-02"))
    add("notice-one-day-earlier", "YES", lambda d: call_date(d, "2024-02-29"))
    add("clear-day-reading-boundary", "NO", lambda d: d["calendar_facts"][0].update(convention="CLEAR_CIVIL_DAYS"))
    def clear_early(d):
        d["calendar_facts"][0]["convention"] = "CLEAR_CIVIL_DAYS"
        call_date(d, "2024-02-29")
    add("clear-day-reading-earlier", "YES", clear_early)
    add("required-registration-shifts-reference", "NO", lambda d: set_fact(d, "registration_required", True))
    def registration(d):
        set_fact(d, "registration_required", True)
        call_date(d, "2024-02-27")
    add("registration-boundary", "YES", registration)
    def registration_late(d):
        registration(d)
        change_date(d, "registration_received_third_day", "start", "2024-03-13")
    add("registration-one-day-late", "NO", registration_late)
    def missing_deadline(d):
        set_fact(d, "registration_required", True)
        change_date(d, "deadline_notice14", "end", None)
    add("registration-deadline-missing", "UNKNOWN", missing_deadline)
    add("notice-date-missing", "UNKNOWN", lambda d: change_date(d, "meeting_notice14", "start", None))
    add("ticket-one-microsecond-late", "NO", lambda d: change_date(d, "six_day_obtaining", "start", "2024-03-09T12:00:00.000001+01:00"))
    def spring(d):
        d["law_bases"] = [b for b in d["law_bases"] if b["id"] == "enumerated_ticket_route"]
        d["facts"] = [f for f in d["facts"] if f["basis_id"] == "enumerated_ticket_route"]
        d["calendar_facts"] = [c for c in d["calendar_facts"] if c["name"] == "six_day_obtaining"]
        change_date(d, "six_day_obtaining", "start", "2024-03-25T12:00:00+01:00")
        change_date(d, "six_day_obtaining", "end", "2024-03-31T12:00:00+02:00")
    add("spring-offset-elapsed-less-than-six-days", "NO", spring, scope="ticket-procurement branch only")
    def autumn(d):
        spring(d)
        change_date(d, "six_day_obtaining", "start", "2024-10-21T12:00:00+02:00")
        change_date(d, "six_day_obtaining", "end", "2024-10-27T12:00:00+01:00")
    add("autumn-offset-elapsed-more-than-six-days", "YES", autumn, scope="ticket-procurement branch only")
    def other_proof(d):
        set_fact(d, "other_proof_required", True)
        change_date(d, "six_day_obtaining", "start", None)
    add("other-proof-route-keeps-own-conditions", "YES", other_proof)
    add("historical-law-withheld", "UNKNOWN",
        lambda d: d.update(facts=[f for f in d["facts"] if f["name"] != "historical_law_applicable"]))
    add("notice-observation-future", "UNKNOWN",
        lambda d: d["calendar_facts"][0]["start"].update(observed_at="2026-10-14T00:00:00Z"))
    def inactive(d):
        d["calendar_facts"][0]["start"].update(valid_from="2026-10-12T00:00:00Z", valid_until=NOW)
    add("notice-expired-at-boundary", "UNKNOWN", inactive)
    def conflict(d):
        extra = deepcopy(d["calendar_facts"][0])
        extra["id"] = "conflicting-date"
        extra["start"] = operand("2024-03-02", extra["start"]["role"])
        d["calendar_facts"].append(extra)
    add("contradictory-date-observations", "CONFLICT", conflict)
    def alternatives(d):
        basis = next(b for b in d["law_bases"] if b["id"] == "notice_registration")
        d["law_bases"] = [basis, {**deepcopy(basis), "id": "notice-clear"}]
        d["facts"] = [f for f in d["facts"] if f["basis_id"] == basis["id"]]
        d["facts"] += [{**deepcopy(f), "basis_id": "notice-clear"} for f in list(d["facts"])]
        d["calendar_facts"] = [c for c in d["calendar_facts"] if c["basis_id"] == basis["id"]]
        extra = [{**deepcopy(c), "basis_id": "notice-clear", "id": c["id"] + "-clear"}
                 for c in d["calendar_facts"]]
        extra[0]["convention"] = "CLEAR_CIVIL_DAYS"
        d["calendar_facts"] += extra
        d["law_relation"] = "ALTERNATIVE_READINGS"
    add("competing-notice-counting-readings", "UNKNOWN", alternatives, scope="notice-registration subclause alternatives only")
    original_compare = calendar_facts.compare
    try:
        calendar_facts.compare = lambda *args: (True, original_compare(*args)[1])
        wrong = deepcopy(baseline)
        change_date(wrong, "meeting_notice14", "start", "2024-03-02")
        mutated = execute(root, products, wrong)
        calculation = mutated["answer"]["questions"]["Q4"]["value"][1]["calendar_calculations"][0]
        try:
            verify(calculation)
        except ValueError as exc:
            save(attempt / "permissive-mutant.json.gz", {**mutated, "detected": True, "reason": str(exc)})
        else:
            raise ValueError("Permissive date calculator escaped independent oracle")
    finally:
        calendar_facts.compare = original_compare
    adverse = []
    mutations = [
        ("changed-date-literal", lambda d: d["calendar_facts"][0]["start"].update(value="2024-03-02")),
        ("wrong-event", lambda d: d["calendar_facts"][0]["end"].update(event_id="another")),
        ("business-days-without-calendar", lambda d: d["calendar_facts"][0].update(convention="BUSINESS_DAYS")),
        ("Boolean-day-count", lambda d: d["calendar_facts"][0].update(days=True)),
        ("source-quote-changed", lambda d: d["calendar_facts"][0]["source"].update(quote="invented clause")),
        ("same-ID", lambda d: d["calendar_facts"].append(deepcopy(d["calendar_facts"][0]))),
        ("Boolean-override", lambda d: d["facts"].append({"basis_id": "notice_registration", "name": "meeting_notice14"})),
        ("malformed-interval", lambda d: d["calendar_facts"][0]["end"].update(known_until=False)),
    ]
    for name, mutate in mutations:
        data = deepcopy(baseline)
        mutate(data)
        try:
            execute(root, products, data)
        except ValueError as exc:
            require(str(exc) != "Current interpretation/calculation differs; reassessment required",
                    "Refusal occurred only after new-input computation")
            adverse.append({"case": name, "reason": str(exc)})
            save(attempt / "refusals" / (name + ".json.gz"), {"input": data, "reason": str(exc)})
        else:
            raise ValueError("Malformed calendar input accepted: " + name)
    result = {"cases": rows, "refusals": adverse, "permissive_mutant_detected": True,
              "actual_events_established": False, "controlling_counting_convention_established": False}
    save(attempt / "calendar-evidence.json", result)
    return {"cases": len(rows), "refusals": len(adverse),
            "independent_comparisons": sum(len(r["independent_comparisons"]) for r in rows),
            "permissive_mutant_detected": True}


def regressions(root, attempt):
    products = load(root / OLD / "common-products.json.gz")
    cases = load(root / OLD / "favorable-deposit-P4.json.gz")["payload"]["cases"]
    results = []
    for old in load(root / OLD / "cases-result.json")["cases"]:
        name = old["case"]
        data = load(root / OLD / (name + "-input.json.gz"))
        try:
            record = execute(root, products, data, cases)
        except ValueError as exc:
            require(old["status"] == "REJECTED" and str(exc) == old["reason"], "Original refusal changed: " + name)
            results.append({"case": name, "refused": True, "reason": str(exc)})
        else:
            require(old["status"] != "REJECTED", "Original refusal lost")
            for key, suffix in (("P4", "P4"), ("answer", "answer")):
                expected = load(root / OLD / (name + "-" + suffix + ".json.gz"))
                require(service.digest(record[key]) == service.digest(expected), "Complete original regression differs: " + name)
            save(attempt / "regression" / (name + ".json.gz"), record)
            results.append({"case": name, "complete_equal": True})
    valid = sum(r.get("complete_equal", False) for r in results)
    refusals = sum(r.get("refused", False) for r in results)
    require((valid, refusals) == (21, 2), "Original regression denominator differs")
    save(attempt / "regression-evidence.json", results)
    return {"complete_valid": valid, "original_refusals": refusals}
