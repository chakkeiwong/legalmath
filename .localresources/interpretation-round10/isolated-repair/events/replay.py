"""Finite attributed consent/achievement replay, assessed at explicit times."""
from ..canonical import digest
from ..domain import timestamp
from ..errors import LegalMathError
from ..ir.load import schema_errors
from .records import validate_events

ENGINE = "legalmath-python-events/0.1.0"


def replay(request):
    digest(request)
    header, valid_at, known_at = request["header"], request["valid_at"], request["known_at"]
    timestamp(valid_at)
    timestamp(known_at)
    result = {"profile": header["profile"], "status": "UNKNOWN", "reason_codes": [], "event_ids": [],
        "evidence_ids": [], "valid_at": valid_at, "known_at": known_at, "source_bundle_hash": None}
    try:
        events = validate_events(header, request["events"])
        selected = [e for e in events if e["occurred_at"] <= valid_at and e["recorded_at"] <= known_at]
        times = [e["occurred_at"] for e in selected]
        if not header["ordering_authority"] and len(set(times)) != len(times):
            raise LegalMathError("E_ORDER_UNRESOLVED")
        selected.sort(key=lambda e: (e["occurred_at"], e["sequence"]))
        result["event_ids"] = [e["id"] for e in selected]
        evidence = {e["evidence_id"] for e in selected}
        if header["profile"] == "consent":
            state, generation, start = "NOT_ESTABLISHED", 0, header["inception"]
            initial = header["initial_snapshot"]
            if initial and initial["recorded_at"] <= known_at and initial["as_of"] <= valid_at:
                state, generation, start = initial["state"], initial["generation"], initial["as_of"]
                evidence.add(initial["evidence_id"])
            seal = request.get("completeness")
            complete = False
            if seal is not None:
                if schema_errors("completeness", seal):
                    raise LegalMathError("E_SCHEMA")
                complete = seal["complete_from"] <= start <= valid_at <= seal["complete_through"] <= seal["recorded_at"] <= known_at
                evidence.add(seal["evidence_id"])
            grant_evidence = {initial["evidence_id"]} if initial and start == initial["as_of"] and state == "ACTIVE" else set()
            violations = []
            for event in selected:
                if event["occurred_at"] < start or (initial and start == initial["as_of"] and event["occurred_at"] == start):
                    continue
                kind = event["kind"]
                if kind == "consent.granted":
                    if event["evidence_id"] in grant_evidence:
                        raise LegalMathError("E_EVENT_ID_COLLISION")
                    grant_evidence.add(event["evidence_id"])
                    state, generation = "ACTIVE", generation + 1
                elif kind == "consent.withdrawn":
                    state = "WITHDRAWN"
                elif kind == "transaction.observed" and state != "ACTIVE":
                    violations.append(event["id"])
            result.update(state=state if complete else "UNKNOWN", generation=generation,
                violation_candidates=violations, status="RESOLVED" if complete else "UNKNOWN",
                reason_codes=[] if complete else ["HISTORY_INCOMPLETE"])
        else:
            openings = [e for e in selected if e["kind"] == "obligation.opened"]
            if len(openings) > 1:
                raise LegalMathError("E_EVENT_ID_COLLISION")
            result.update(breached=False, breach_id=None, performance_event_id=None)
            if not openings:
                result["reason_codes"] = ["ACTIVATION_UNKNOWN"]
            else:
                opening = openings[0]
                activation, deadline = opening["activation"], opening["deadline"]
                result["source_bundle_hash"] = opening["source_bundle_hash"]
                performances = [e for e in selected if e["kind"] == "obligation.performed" and e["occurred_at"] >= activation]
                timely = [e for e in performances if deadline is None or e["occurred_at"] < deadline]
                complete = any(e["kind"] == "watermark" and e["complete_from"] <= activation and
                    deadline is not None and deadline <= e["complete_through"] <= min(e["recorded_at"], valid_at)
                    for e in selected)
                if timely:
                    result.update(status="SATISFIED_ON_TIME", performance_event_id=timely[0]["id"])
                elif deadline is not None and deadline <= valid_at and complete:
                    result.update(status="PERFORMED_LATE" if performances else "BREACHED", breached=True,
                        breach_id=digest({"opening_id": opening["id"], "deadline": deadline}),
                        performance_event_id=performances[0]["id"] if performances else None)
                else:
                    result.update(status="OPEN", performance_event_id=performances[0]["id"] if performances else None)
        result["evidence_ids"] = sorted(evidence)
    except LegalMathError as exc:
        result.update(status="ERROR", reason_codes=[exc.code])
    result["engine_version"] = ENGINE
    result["result_hash"] = digest({"request": request, "result": result})
    return result


def consent_fact(result, valid_from, valid_until):
    if result["profile"] != "consent" or result["status"] == "ERROR":
        raise LegalMathError("E_UNSUPPORTED_PROFILE")
    if result["state"] == "UNKNOWN":
        return {"status": "unknown", "type": "bool", "reason": "ORDER_UNRESOLVED"}
    return {"status": "known", "type": "bool", "value": result["state"] == "ACTIVE",
        "evidence_ids": ["replay." + result["result_hash"]], "valid_from": valid_from,
        "valid_until": valid_until, "recorded_at": result["known_at"]}
