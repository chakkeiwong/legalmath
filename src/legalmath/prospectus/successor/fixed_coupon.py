"""Exact conditional coupon slice; contractual conventions are admitted inputs."""
from calendar import isleap, monthrange
from datetime import date, timedelta
from fractions import Fraction
from .anchors import bind, fields
from .contracts import timestamp
from ..semantics import exact


def year_fraction(start, end, convention, *, references, frequency, eom):
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    if not a < b or (b-a).days > 3660 or type(eom) is not bool:
        raise ValueError("Bounded positive accrual interval and explicit EOM rule required")
    if type(frequency) is not int or frequency not in {1, 2, 3, 4, 6, 12}:
        raise ValueError("Explicit supported coupon frequency required")
    if convention == "ACT_ACT_ICMA":
        if not isinstance(references, list) or not references:
            raise ValueError("ICMA reference periods required; guessing is forbidden")
        total, cursor, previous = Fraction(), a, None
        for row in references:
            fields(row, {"start", "end"}, {"start", "end"})
            left, right = date.fromisoformat(row["start"]), date.fromisoformat(row["end"])
            months = 12 // frequency
            n = left.year * 12 + left.month - 1 + months
            year, month = n // 12, n % 12 + 1
            last = monthrange(year, month)[1]
            day = last if eom and left.day == monthrange(left.year, left.month)[1] else min(left.day, last)
            if right != date(year, month, day) or previous is not None and left != previous:
                raise ValueError("Reference periods must be contiguous regular periods under the declared EOM rule")
            previous = right
            x, y = max(a, left), min(b, right)
            if x < y:
                if x != cursor:
                    raise ValueError("Reference periods leave an accrual gap")
                total += Fraction((y-x).days, (right-left).days * frequency)
                cursor = y
        if cursor != b:
            raise ValueError("Reference periods do not cover accrual")
        return total
    if references:
        raise ValueError("Unexpected reference periods for this convention")
    if convention in {"ACT_365_FIXED", "ACT_360"}:
        return Fraction((b-a).days, 365 if convention == "ACT_365_FIXED" else 360)
    if convention == "ACT_ACT_ISDA":
        total = Fraction()
        while a < b:
            stop = min(b, date(a.year+1, 1, 1))
            total += Fraction((stop-a).days, 366 if isleap(a.year) else 365)
            a = stop
        return total
    raise ValueError("Unsupported day-count convention")


def adjusted(day, convention, calendar):
    fields(calendar, {"edition", "valid_from", "valid_until", "holidays", "weekend", "coverage"},
           {"edition", "valid_from", "valid_until", "holidays", "weekend", "coverage"})
    if not calendar["edition"] or calendar["coverage"] != "COMPLETE_DECLARED_INTERVAL":
        raise ValueError("Calendar edition and complete declared interval required")
    start, end = date.fromisoformat(calendar["valid_from"]), date.fromisoformat(calendar["valid_until"])
    if start >= end or not isinstance(calendar["holidays"], list) or not isinstance(calendar["weekend"], list):
        raise ValueError("Invalid calendar")
    holidays = {date.fromisoformat(h) for h in calendar["holidays"]}
    weekend = calendar["weekend"]
    if len(holidays) != len(calendar["holidays"]) or any(not start <= h < end for h in holidays):
        raise ValueError("Holiday outside calendar edition coverage or duplicate")
    if any(type(d) is not int or d not in range(7) for d in weekend) or len(set(weekend)) != len(weekend) or len(weekend) == 7:
        raise ValueError("Explicit valid weekend required")
    original = date.fromisoformat(day)
    def available(d):
        if not start <= d < end:
            raise ValueError("Calendar coverage missing for adjustment")
        return d.weekday() not in weekend and d not in holidays
    available(original)
    if convention == "UNADJUSTED":
        return original.isoformat()
    if convention not in {"FOLLOWING", "MODIFIED_FOLLOWING", "PRECEDING"}:
        raise ValueError("Explicit supported payment adjustment required")
    def move(step):
        value = original
        for _ in range(370):
            if available(value):
                return value
            value += timedelta(days=step)
        raise ValueError("Calendar adjustment bound exceeded")
    answer = move(-1 if convention == "PRECEDING" else 1)
    if convention == "MODIFIED_FOLLOWING" and answer.month != original.month:
        answer = move(-1)
    return answer.isoformat()


def rounded(value, quantum, rule):
    value, quantum = exact(value), exact(quantum)
    if value < 0 or quantum <= 0 or rule not in {"HALF_UP", "DOWN"}:
        raise ValueError("Nonnegative amount and explicit rounding rule/quantum required")
    scaled = value / quantum
    units = scaled.numerator // scaled.denominator
    if rule == "HALF_UP" and (scaled-units) >= Fraction(1, 2):
        units += 1
    return units * quantum


def calculate(s, graph):
    required = {"profile", "issue_id", "source_sha256", "premise_kind", "currency", "annual_rate",
                "accrual_start", "accrual_end", "due_date", "payment_date", "day_count", "references",
                "frequency", "eom", "stub", "adjustment", "calendar", "rounding", "holdings", "events",
                "event_scope", "evidence"}
    fields(s, required, required)
    if s["profile"] != "fixed-coupon.v1" or s["premise_kind"] != "HYPOTHETICAL":
        raise ValueError("Only explicitly hypothetical fixed-coupon premises supported")
    if not isinstance(s["currency"], str) or len(s["currency"]) != 3 or not s["currency"].isupper():
        raise ValueError("Explicit currency required")
    if s["stub"] not in {"REGULAR", "SHORT_FIRST", "LONG_FIRST", "SHORT_FINAL", "LONG_FINAL"}:
        raise ValueError("Explicit stub classification required")
    # Each value is a source-backed interpretation, not a fact inferred by the kernel.
    evidence_fields = required - {"profile", "issue_id", "source_sha256", "premise_kind", "evidence"}
    fields(s["evidence"], evidence_fields, evidence_fields)
    for key, row in s["evidence"].items():
        fields(row, {"source", "reason"}, {"source", "reason"})
        if not row["reason"]:
            raise ValueError("Missing convention interpretation: " + key)
        bind(graph, row["source"])
    if s["issue_id"] != graph["instrument_id"] or not any(d["sha256"] == s["source_sha256"] for d in graph["documents"]):
        raise ValueError("Coupon source/instrument mismatch")
    rate = exact(s["annual_rate"])
    if not 0 <= rate <= 1:
        raise ValueError("Rate outside supported slice")
    fraction = year_fraction(s["accrual_start"], s["accrual_end"], s["day_count"],
                             references=s["references"], frequency=s["frequency"], eom=s["eom"])
    if s["stub"] == "REGULAR" and s["day_count"] == "ACT_ACT_ICMA" and fraction != Fraction(1, s["frequency"]):
        raise ValueError("Regular coupon contradicts reference periods")
    if s["day_count"] == "ACT_ACT_ICMA":
        regular = Fraction(1, s["frequency"])
        if s["stub"].startswith("SHORT") and fraction >= regular or s["stub"].startswith("LONG") and fraction <= regular:
            raise ValueError("Stub classification contradicts reference periods")
    payment_date = adjusted(s["due_date"], s["adjustment"], s["calendar"])
    if payment_date != s["payment_date"]:
        raise ValueError("Payment date contradicts calendar/convention")
    fields(s["rounding"], {"quantum", "rule", "aggregation"}, {"quantum", "rule", "aggregation"})
    if s["rounding"]["aggregation"] != "PER_LEGAL_HOLDER":
        raise ValueError("Explicit per-holder aggregation required")
    if not isinstance(s["holdings"], list) or not s["holdings"]:
        raise ValueError("Entitled legal holdings required")
    holders, accounts = {}, set()
    for row in s["holdings"]:
        fields(row, {"legal_holder_id", "account_id", "principal", "entitled"}, {"legal_holder_id", "account_id", "principal", "entitled"})
        if not row["legal_holder_id"] or not row["account_id"] or row["account_id"] in accounts or type(row["entitled"]) is not bool:
            raise ValueError("Distinct accounts, legal holder and explicit entitlement required")
        accounts.add(row["account_id"])
        principal = exact(row["principal"])
        if principal < 0:
            raise ValueError("Negative principal")
        if row["entitled"]:
            holders[row["legal_holder_id"]] = holders.get(row["legal_holder_id"], Fraction()) + principal
    kinds = {"accrual_start", "accrual_end", "notice", "observation", "determination", "record", "ex_coupon", "payment"}
    fields(s["event_scope"], kinds, kinds)
    for value in s["event_scope"].values():
        if value not in {"REQUIRED", "NOT_APPLICABLE"}:
            raise ValueError("Every event kind needs an explicit scope disposition")
    if any(s["event_scope"][k] != "REQUIRED" for k in ("accrual_start", "accrual_end", "determination", "record", "payment")):
        raise ValueError("Core coupon events required")
    events, ids, instants = [], set(), set()
    for row in s["events"]:
        fields(row, {"id", "kind", "at", "order"}, {"id", "kind", "at", "order"})
        at = timestamp(row["at"])
        if row["kind"] not in kinds or row["id"] in ids or type(row["order"]) is not int or (at, row["order"]) in instants:
            raise ValueError("Unique event identity and explicit equal-time ordering required")
        ids.add(row["id"]); instants.add((at, row["order"]))
        events.append((at, row["order"], row))
    events.sort(key=lambda e: (e[0], e[1]))
    for kind, disposition in s["event_scope"].items():
        found = [e for e in events if e[2]["kind"] == kind]
        if (disposition == "REQUIRED" and len(found) != 1) or (disposition == "NOT_APPLICABLE" and found):
            raise ValueError("Missing, duplicated or out-of-scope event: " + kind)
    positions = {e[2]["kind"]: i for i, e in enumerate(events)}
    for kind, expected in (("accrual_start", s["accrual_start"]), ("accrual_end", s["accrual_end"]), ("payment", payment_date)):
        event = events[positions[kind]]
        if event[0].date().isoformat() != expected:
            raise ValueError("Event date differs from supplied calculation date")
    if not positions["accrual_start"] < positions["accrual_end"] <= positions["determination"] < positions["payment"] or positions["record"] >= positions["payment"]:
        raise ValueError("Coupon event order contradicts accrual/determination/entitlement")
    transfers = [{"legal_holder_id": holder, "currency": s["currency"], "unrounded": str(principal*rate*fraction),
                  "amount": str(rounded(principal*rate*fraction, s["rounding"]["quantum"], s["rounding"]["rule"])),
                  "payment_event": events[positions["payment"]][2]["id"]} for holder, principal in sorted(holders.items())]
    return {"day_fraction": str(fraction), "payment_date": payment_date, "transfers": transfers,
            "events": [e[2] for e in events], "scope": "FIXED_COUPON_ONLY", "actual_event": "NOT_ESTABLISHED",
            "full_settlement_supported": False, "source_evidence": s["evidence"]}
