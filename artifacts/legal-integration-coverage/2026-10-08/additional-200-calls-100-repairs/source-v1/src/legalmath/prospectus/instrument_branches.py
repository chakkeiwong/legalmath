"""Additional conditional UBS branches; factual acts never certify legal truth."""
from datetime import timedelta
from fractions import Fraction

from ..transaction.evidence import fields
from .instrument_terms import amount, day, _result
from .instrument_evidence import resolve


def cents(value, mode):
    exact = amount(value) * 100
    if mode == "half_up":
        exact += Fraction(1, 2)
    elif mode != "down":
        raise ValueError("Explicit rounding convention required")
    return Fraction(exact.numerator // exact.denominator, 100)


def rounding_scenarios(value):
    """Two declared engineering scenarios, not an exhaustive legal reading set."""
    variants = {mode: str(cents(value, mode)) for mode in ("down", "half_up")}
    return {"variants": variants, "agree": len(set(variants.values())) == 1,
            "operational_price": None, "selection": "CONTRACTUAL_CONVENTION_UNRESOLVED",
            "exhaustive_interpretations": False}


def determined_price(store, identity, *, scope, at, known_at):
    """A scoped 8(d)/8(m) determination selects a conditional factual price.

    Scope must bind the complete input history and notice, preventing reuse of
    an adviser price for a different action sequence or a subsequent event.
    """
    fields(scope, {"instrument_id", "clause", "event_id", "history_sha256"})
    if scope["instrument_id"] != "ubs-sgd-at1-2024-final-published" or scope["clause"] != "8(d)/8(m)":
        raise ValueError("Unsupported determination profile")
    store.get(scope["history_sha256"])
    checked = resolve(store, identity, scope=scope, kind="determination", at=at, known_at=known_at)
    if checked["status"] != "CONDITIONAL":
        return _result({"price": None, "evidence": checked}, checked["issues"])
    data = checked["value"]
    fields(data, {"price", "actor", "signed", "adviser_unavailable", "manifest_error", "bad_faith", "wilful_default", "par_value_sgd"})
    price, floor = amount(data["price"], positive=True), amount(data["par_value_sgd"], positive=True)
    issues = []
    if data["actor"] not in {"independent_adviser", "issuer"} or data["signed"] is not True:
        issues.append("Required contractual determination not established")
    if data["actor"] == "issuer" and data["adviser_unavailable"] is not True:
        issues.append("Issuer fallback requires the specified adviser failure")
    if any(data[k] is not False for k in ("manifest_error", "bad_faith", "wilful_default")):
        issues.append("Condition 8(n) exceptions are not resolved")
    if price < floor or (price*100).denominator != 1:
        issues.append("Determined price violates par floor or two-decimal constraint")
    return _result({"price": str(price) if not issues else None, "evidence": checked,
                    "source_formula_rewritten": False, "legal_validity": "NOT_ESTABLISHED"}, issues)


def successor_separate(*, existing_price, existing_price_date, ordinary_window,
                       relevant_window, ordinary_calendar, relevant_calendar,
                       relevant_event, effective_date, conversion_date,
                       approved_entity, arrangements_entered, terms_amended):
    event, effective, conversion = map(day, (relevant_event, effective_date, conversion_date))
    issues = []
    if not event <= effective <= event+timedelta(days=7) or conversion < effective:
        issues.append("Successor dates violate the seven-day/effective-date conditions")
    if any(v is not True for v in (approved_entity, arrangements_entered, terms_amended)):
        issues.append("Successor contractual conditions not established")
    if any(c.record["purpose"] != "exchange_dealing" for c in (ordinary_calendar, relevant_calendar)):
        raise ValueError("Exchange dealing calendars required")
    expected_ecp = ordinary_calendar.preceding(effective_date, 1)[0]
    if existing_price_date != expected_ecp:
        issues.append("ECP must be dated on the last ordinary-share dealing day before effectiveness")
    means, windows = [], []
    for rows, calendar in ((ordinary_window, ordinary_calendar), (relevant_window, relevant_calendar)):
        expected = calendar.preceding(relevant_event, 5)
        windows.append(expected)
        if not isinstance(rows, list) or len(rows) != 5:
            issues.append("Five separate-market VWAP observations required")
            continue
        for row in rows:
            fields(row, {"date", "vwap", "sgd_fx"})
        if [r["date"] for r in rows] != expected:
            issues.append("VWAP dates disagree with the market's own preceding five dealing days")
        means.append(sum(amount(r["vwap"], positive=True)*amount(r["sgd_fx"], positive=True) for r in rows)/5)
    return _result({"new_conversion_price": str(amount(existing_price, positive=True)*means[1]/means[0]) if not issues else None,
                    "ordinary_window": windows[0], "relevant_window": windows[1],
                    "calendars": [ordinary_calendar.identity, relevant_calendar.identity],
                    "source_formula": "ECP * VWAPRS / VWAPOS", "actual_event": "NOT_ESTABLISHED"}, issues)


def alternative_notice(store, identity, *, scope, at, known_at):
    fields(scope, {"instrument_id", "clause", "event_id"})
    if scope["instrument_id"] != "ubs-sgd-at1-2024-final-published" or scope["clause"] != "14":
        raise ValueError("Unsupported notice profile")
    checked = resolve(store, identity, scope=scope, kind="notice", at=at, known_at=known_at)
    if checked["status"] != "CONDITIONAL":
        return _result({"notice_date": None}, checked["issues"])
    record = checked["value"]
    fields(record, {"method", "listed_on_six", "permitted_by_applicable_exchange_rules", "rule_source_sha256", "first_effective_date", "notice_source_sha256"})
    store.get(record["rule_source_sha256"]); store.get(record["notice_source_sha256"])
    day(record["first_effective_date"])
    issues = []
    if record["method"] != "alternative_exchange_method" or record["listed_on_six"] is not True or record["permitted_by_applicable_exchange_rules"] is not True:
        issues.append("Alternative listed notice method not established by the applicable rules")
    if day(record["first_effective_date"]) > day(at[:10]):
        issues.append("Notice has not yet become effective")
    return _result({"notice_date": None if issues else record["first_effective_date"], "evidence": checked}, issues)


def holder_delivery(store, identity, *, scope, at, known_at):
    fields(scope, {"instrument_id", "event_id", "holder_id"})
    if scope["instrument_id"] != "ubs-sgd-at1-2024-final-published":
        raise ValueError("Unsupported delivery profile")
    checked = resolve(store, identity, scope=scope, kind="settlement", at=at, known_at=known_at)
    if checked["status"] != "CONDITIONAL":
        return _result({"delivered": None, "voting_registered": None}, checked["issues"])
    v = checked["value"]
    fields(v, {"taxes_due", "taxes_paid", "delivery_receipt_sha256", "delivered_shares", "entitled_shares",
               "registration_receipt_sha256", "voting_registered"})
    if any(type(v[k]) is not int or v[k] < 0 for k in ("delivered_shares", "entitled_shares")):
        raise ValueError("Nonnegative integer share quantities required")
    issues = []
    for k in ("delivery_receipt_sha256", "registration_receipt_sha256"):
        if v[k] is not None: store.get(v[k])
    if v["taxes_due"] is None or v["taxes_paid"] is None:
        issues.append("Tax/payment evidence missing")
    elif amount(v["taxes_paid"]) < amount(v["taxes_due"]):
        issues.append("Required holder taxes not paid")
    delivered = v["delivery_receipt_sha256"] is not None and v["delivered_shares"] == v["entitled_shares"]
    if not delivered: issues.append("Full holder delivery not established")
    registered = v["voting_registered"] if type(v["voting_registered"]) is bool and v["registration_receipt_sha256"] else None
    if registered is None: issues.append("Voting registration not established")
    return _result({"delivered": delivered, "voting_registered": registered, "evidence": checked,
                    "market_value": "NOT_COMPUTED"}, issues)
