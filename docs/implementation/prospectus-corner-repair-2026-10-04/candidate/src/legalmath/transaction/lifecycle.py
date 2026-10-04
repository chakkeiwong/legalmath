"""Pure event replay: no trades, asset freezes or reports are executed."""
from datetime import date, timedelta

from ..canonical import digest
from .evidence import fields, instant


def business_deadline(start, count, *, calendar, store):
    """Explicit holiday calendar, jurisdiction and covered range; no hidden US calendar."""
    fields(calendar, {"id", "source_sha256", "start", "end", "holidays", "weekend"})
    if store.json(calendar["source_sha256"]) != {k: v for k, v in calendar.items() if k != "source_sha256"}:
        raise ValueError("Calendar differs from its retained factual content")
    if type(count) is not int or not 0 <= count <= 366:
        raise ValueError("Bounded nonnegative business-day count required")
    current = date.fromisoformat(start)
    first, last = date.fromisoformat(calendar["start"]), date.fromisoformat(calendar["end"])
    if not first <= current <= last:
        raise ValueError("Start outside sourced calendar range")
    weekend = calendar["weekend"]
    if not isinstance(weekend, list) or any(type(x) is not int or x not in range(7) for x in weekend) or len(set(weekend)) >= 7:
        raise ValueError("Invalid business week")
    holidays = {date.fromisoformat(day) for day in calendar["holidays"]}
    while count:
        current += timedelta(days=1)
        if current > last:
            raise ValueError("Deadline outside sourced calendar range")
        if current.weekday() not in weekend and current not in holidays:
            count -= 1
    return current.isoformat()


def replay(events, *, store):
    """Append-only ordered events; any decision receipt is reconstructed upstream.

    A recorded assessment never grants execution here. A subsequent fact/source/
    policy/route/action change explicitly invalidates its binding. Business-duty
    completion requires retained evidence, not a tick in a mutable task record.
    """
    if not isinstance(events, list) or len(events) > 10000:
        raise ValueError("Bounded event list required")
    previous, decision, decision_at, seen, duties, changes = None, None, None, {}, {}, []
    for event in events:
        fields(event, {"id", "at", "kind", "payload"})
        if not isinstance(event["id"], str) or not event["id"]:
            raise ValueError("Event identity required")
        if event["id"] in seen:
            if seen[event["id"]] != event:
                raise ValueError("Reused event id has different content")
            continue
        at = instant(event["at"])
        if previous is not None and at < previous:
            raise ValueError("Events are not chronological")
        previous, seen[event["id"]] = at, event
        payload, kind = event["payload"], event["kind"]
        if kind == "assessment":
            fields(payload, {"request", "receipt"})
            from .engine import revalidate
            receipt = revalidate(payload["receipt"], payload["request"], store)
            if instant(payload["request"]["context"]["known_at"]) > at:
                raise ValueError("Assessment contains future knowledge")
            decision = receipt["receipt_hash"]
            decision_at = instant(payload["request"]["context"]["effective_at"])
        elif kind in {"facts_changed", "source_changed", "policy_changed", "route_changed", "corporate_action"}:
            fields(payload, {"evidence_sha256", "description"})
            store.get(payload["evidence_sha256"])
            if not isinstance(payload["description"], str) or not payload["description"]:
                raise ValueError("Explicit change required")
            decision = None
            changes.append(event["id"])
        elif kind == "duty_created":
            fields(payload, {"duty_id", "kind", "actor", "trigger", "due_at", "source_sha256", "basis_receipt"})
            if payload["kind"] not in {"reject", "block", "report", "rescreen", "disclose"}:
                raise ValueError("Unknown duty type")
            if payload["duty_id"] in duties or not all(isinstance(payload[k], str) and payload[k] for k in payload):
                raise ValueError("Duplicate or incomplete duty")
            store.get(payload["source_sha256"])
            if instant(payload["due_at"]) < at or payload["basis_receipt"] != decision:
                raise ValueError("Duty must have a current basis and nonpast deadline")
            duties[payload["duty_id"]] = {**payload, "state": "PENDING", "creation_event": event["id"],
                                          "legal_entailment": "NOT_ESTABLISHED"}
        elif kind == "duty_completed":
            fields(payload, {"duty_id", "evidence_sha256"})
            if payload["duty_id"] not in duties:
                raise ValueError("Cannot complete an uncreated duty")
            store.get(payload["evidence_sha256"])
            duty = duties[payload["duty_id"]]
            if duty["state"] != "PENDING":
                raise ValueError("Duty already completed")
            duty.update(state="EVIDENCE_RECORDED", completed_at=event["at"],
                        completion_evidence=payload["evidence_sha256"],
                        late=at > instant(duty["due_at"]), actual_performance="NOT_ESTABLISHED")
        elif kind == "settlement_requested":
            fields(payload, {"receipt_hash"})
            if decision is None or payload["receipt_hash"] != decision or at != decision_at:
                raise ValueError("Stale or absent assessment at settlement")
            # Qualified investigations cannot be converted to execution permission.
            changes.append(event["id"] + ": settlement remains qualified")
        else:
            raise ValueError("Unsupported lifecycle event")
    for duty in duties.values():
        if duty["state"] == "PENDING" and previous is not None and previous > instant(duty["due_at"]):
            duty["state"] = "OVERDUE"
    result = {"events_hash": digest(events), "current_assessment": decision, "duties": duties,
              "invalidations": changes, "may_execute_transaction": False,
              "legal_entailment": "NOT_ESTABLISHED", "human_quality_evidence": False}
    return {**result, "replay_hash": digest(result)}
