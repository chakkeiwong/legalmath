"""Exact conditional coupon slice; contractual conventions are admitted inputs."""
from calendar import isleap, monthrange
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
from .anchors import bind, fields
from .contracts import timestamp
from ..semantics import exact
from .coupon_dates import anchored_date, english_date, iso_date, lattice_index


def year_fraction(start, end, convention, *, references, frequency, eom, coupon_anchor=None):
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    if not a < b or (b-a).days > 3660 or type(eom) is not bool:
        raise ValueError("Bounded positive accrual interval and explicit EOM rule required")
    if type(frequency) is not int or frequency not in {1, 2, 3, 4, 6, 12}:
        raise ValueError("Explicit supported coupon frequency required")
    if coupon_anchor is not None:
        iso_date(coupon_anchor)
        if convention != 'ACT_ACT_ICMA':
            raise ValueError('Explicit coupon anchors are supported only for ACT/ACT ICMA')
    if convention == "ACT_ACT_ICMA":
        if not isinstance(references, list) or not references:
            raise ValueError("ICMA reference periods required; guessing is forbidden")
        total, cursor, previous = Fraction(), a, None
        for row in references:
            fields(row, {"start", "end"}, {"start", "end"})
            left, right = date.fromisoformat(row["start"]), date.fromisoformat(row["end"])
            months = 12 // frequency
            if coupon_anchor is None:
                n = left.year * 12 + left.month - 1 + months
                year, month = n // 12, n % 12 + 1
                last = monthrange(year, month)[1]
                day = last if eom and left.day == monthrange(left.year, left.month)[1] else min(left.day, last)
                expected = date(year, month, day)
            else:
                index = lattice_index(row['start'], coupon_anchor, frequency, eom)
                expected = anchored_date(coupon_anchor, (index+1)*months, eom)
                iso_date(row['end'])
            if right != expected or previous is not None and left != previous:
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
    if convention == "THIRTY_360_BOND_BASIS":
        # Named endpoint rule only: no February-end adjustment and no generic
        # 30/360 alias. A positive calendar interval may have zero counted days.
        d1 = min(a.day, 30)
        d2 = 30 if b.day == 31 and d1 == 30 else b.day
        return Fraction(360 * (b.year-a.year) + 30 * (b.month-a.month) + d2-d1, 360)
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
    try:
        value, quantum = exact(value), exact(quantum)
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise ValueError("Exact amount and quantum required for rounding") from exc
    if value < 0 or quantum <= 0 or not isinstance(rule, str) or rule not in {"HALF_UP", "DOWN"}:
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
    initial = s.get('profile') == 'fixed-coupon.v3'
    anchored = s.get('profile') in {'fixed-coupon.v2', 'fixed-coupon.v3'}
    if anchored:
        required.add('coupon_anchor')
    if initial:
        required |= {'note_form', 'calculation_amount', 'fixed_coupon_amount', 'broken_coupon_amount'}
    extra={'calculation_amount','fixed_coupon_amount'}
    fields(s, required | extra, required)
    if s["profile"] not in {'fixed-coupon.v1','fixed-coupon.v2','fixed-coupon.v3'} or s["premise_kind"] != "HYPOTHETICAL":
        raise ValueError("Only explicitly hypothetical fixed-coupon premises supported")
    if anchored and s['day_count'] != 'ACT_ACT_ICMA':
        raise ValueError('Fixed coupon v2/v3 requires anchored ACT/ACT ICMA')
    if not isinstance(s["currency"], str) or len(s["currency"]) != 3 or not s["currency"].isupper():
        raise ValueError("Explicit currency required")
    if s["stub"] not in {"REGULAR", "SHORT_FIRST", "LONG_FIRST", "SHORT_FINAL", "LONG_FINAL"}:
        raise ValueError("Explicit stub classification required")
    if initial and (s['stub'] not in {'SHORT_FIRST', 'LONG_FIRST'} or s['due_date'] != s['accrual_end']):
        raise ValueError('Initial broken coupon requires a first stub ending on its due date')
    # Each value is a source-backed interpretation, not a fact inferred by the kernel.
    evidence_fields = (required | (set(s) & extra)) - {"profile", "issue_id", "source_sha256", "premise_kind", "evidence"}
    fields(s["evidence"], evidence_fields, evidence_fields)
    for key, row in s["evidence"].items():
        fields(row, {"source", "reason"}, {"source", "reason"})
        if not row["reason"]:
            raise ValueError("Missing convention interpretation: " + key)
        bind(graph, row["source"])
    if anchored and english_date(s['evidence']['coupon_anchor']['source']['quote']) != s['coupon_anchor']:
        raise ValueError('Coupon anchor differs from its quoted English date')
    if s["issue_id"] != graph["instrument_id"] or not any(d["sha256"] == s["source_sha256"] for d in graph["documents"]):
        raise ValueError("Coupon source/instrument mismatch")
    rate = exact(s["annual_rate"])
    if not 0 <= rate <= 1:
        raise ValueError("Rate outside supported slice")
    fraction = year_fraction(s["accrual_start"], s["accrual_end"], s["day_count"],
                             references=s["references"], frequency=s["frequency"], eom=s["eom"],
                             coupon_anchor=s['coupon_anchor'] if anchored else None)
    if anchored:
        def index(value):
            try:
                return lattice_index(value, s['coupon_anchor'], s['frequency'], s['eom'])
            except ValueError:
                return None
        left, right = index(s['accrual_start']), index(s['accrual_end'])
        if (s['stub'] == 'REGULAR' and (left is None or right is None or right != left+1) or
                s['stub'].endswith('FIRST') and right is None or
                s['stub'].endswith('FINAL') and left is None):
            raise ValueError('Accrual endpoints contradict the declared coupon classification')
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
    aggregation=s['rounding']['aggregation']
    if aggregation not in {'PER_LEGAL_HOLDER','PER_CALCULATION_AMOUNT'}:
        raise ValueError("Explicit supported aggregation required")
    # Declared rounding must be valid even when no holder receives a payment.
    rounded(0, s['rounding']['quantum'], s['rounding']['rule'])
    if initial:
        expected_aggregation = {'GLOBAL': 'PER_LEGAL_HOLDER', 'DEFINITIVE': 'PER_CALCULATION_AMOUNT'}
        if s['note_form'] not in expected_aggregation or aggregation != expected_aggregation[s['note_form']]:
            raise ValueError('Declared note form disagrees with coupon rounding basis')
    if aggregation=='PER_CALCULATION_AMOUNT':
        if 'calculation_amount' not in s or exact(s['calculation_amount']) <= 0:
            raise ValueError('Positive calculation amount required')
    elif not initial and set(s) & extra:
        raise ValueError('Calculation-amount terms require that explicit aggregation')
    per_amount = None
    if initial:
        from .coupon_amounts import initial_amounts
        per_amount = initial_amounts(s, rate, fraction, rounded)
    elif aggregation == 'PER_CALCULATION_AMOUNT':
        per_amount = rounded(exact(s['calculation_amount'])*rate*fraction,
                             s['rounding']['quantum'], s['rounding']['rule'])
        if 'fixed_coupon_amount' in s:
            if s['stub'] != 'REGULAR' or exact(s['fixed_coupon_amount']) != per_amount:
                raise ValueError('Published fixed coupon disagrees with admitted rate/reference fraction')
            per_amount = exact(s['fixed_coupon_amount'])
    if not isinstance(s["holdings"], list) or not s["holdings"]:
        raise ValueError("Entitled legal holdings required")
    if initial and s['note_form'] == 'GLOBAL' and len(s['holdings']) != 1:
        raise ValueError('Initial global coupon requires one explicitly declared aggregate holding')
    holders, accounts = {}, set()
    for row in s["holdings"]:
        fields(row, {"legal_holder_id", "account_id", "principal", "entitled"}, {"legal_holder_id", "account_id", "principal", "entitled"})
        if any(not isinstance(row[key], str) or not row[key].strip() for key in ("legal_holder_id", "account_id")):
            raise ValueError("Nonblank string holder and account identifiers required")
        if not row["legal_holder_id"] or not row["account_id"] or row["account_id"] in accounts or type(row["entitled"]) is not bool:
            raise ValueError("Distinct accounts, legal holder and explicit entitlement required")
        accounts.add(row["account_id"])
        principal = exact(row["principal"])
        if principal < 0:
            raise ValueError("Negative principal")
        if aggregation=='PER_CALCULATION_AMOUNT' and (principal/exact(s['calculation_amount'])).denominator!=1:
            raise ValueError('Holdings require integral admitted calculation amounts')
        if row["entitled"]:
            holders[row["legal_holder_id"]] = holders.get(row["legal_holder_id"], Fraction()) + principal
    kinds = {"accrual_start", "accrual_end", "notice", "observation", "determination", "record", "ex_coupon", "payment"}
    fields(s["event_scope"], kinds, kinds)
    for value in s["event_scope"].values():
        if value not in {"REQUIRED", "NOT_APPLICABLE"}:
            raise ValueError("Every event kind needs an explicit scope disposition")
    if any(s["event_scope"][k] != "REQUIRED" for k in ("accrual_start", "accrual_end", "determination", "payment")):
        raise ValueError("Core coupon events required")
    events, ids, instants = [], set(), set()
    for row in s["events"]:
        fields(row, {"id", "kind", "at", "order"}, {"id", "kind", "at", "order"})
        if not isinstance(row["id"], str) or not row["id"].strip():
            raise ValueError("Nonblank string event identifier required")
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
    if not positions["accrual_start"] < positions["accrual_end"] <= positions["determination"] < positions["payment"] or ('record' in positions and positions["record"] >= positions["payment"]):
        raise ValueError("Coupon event order contradicts accrual/determination/entitlement")
    def payment(principal):
        if aggregation=='PER_LEGAL_HOLDER':
            return rounded(principal*rate*fraction,s['rounding']['quantum'],s['rounding']['rule'])
        amount=exact(s['calculation_amount'])
        return principal/amount*per_amount
    transfers = [{"legal_holder_id": holder, "currency": s["currency"], "unrounded": str(principal*rate*fraction),
                  "amount": str(payment(principal)),
                  "payment_event": events[positions["payment"]][2]["id"]} for holder, principal in sorted(holders.items())]
    return {**({'profile':s['profile'], 'coupon_anchor':s['coupon_anchor']} if anchored else {}),
            **({'published_coupon': {'note_form': s['note_form'],
                'calculation_amount': s['calculation_amount'], 'regular_amount': s['fixed_coupon_amount'],
                'initial_broken_amount': s['broken_coupon_amount'],
                'initial_amount_used_for_payment': s['note_form'] == 'DEFINITIVE',
                'payment_basis': 'ONE_HYPOTHETICAL_GLOBAL_AGGREGATE' if s['note_form'] == 'GLOBAL' else 'PUBLISHED_INITIAL_PER_CALCULATION_AMOUNT',
                'actual_note_form_established': False}} if initial else {}),
            "day_fraction": str(fraction), "payment_date": payment_date, "transfers": transfers,
            "entitlement_basis": {"kind": "HYPOTHETICAL_DECLARED_FLAGS",
                "holdings": [dict(row) for row in s["holdings"]],
                "excluded_accounts": [row["account_id"] for row in s["holdings"] if not row["entitled"]],
                "event_scope": dict(s["event_scope"]), "rounding_aggregation": aggregation,
                "legal_entitlement_established": False, "transfer_effects_inferred": False,
                "note_form_inferred": False},
            "events": deepcopy([e[2] for e in events]), "scope": "FIXED_COUPON_ONLY", "actual_event": "NOT_ESTABLISHED",
            "full_settlement_supported": False, "source_evidence": deepcopy(s["evidence"]),
            "calculation_inputs": deepcopy(s)}
