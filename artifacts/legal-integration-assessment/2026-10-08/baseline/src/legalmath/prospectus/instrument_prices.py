"""Exact, bounded Condition 8 arithmetic; unresolved source choices stay visible."""
from fractions import Fraction
from datetime import timedelta

from ..transaction.evidence import fields
from .instrument_terms import amount, day, _result


def factor(kind, data):
    """Calculate a declared adjustment, independently of its legal occurrence.

    Ratios are dimensionless; A, B, C must already have the source-specified
    meaning and currency. Missing FX/market valuation is not assumed to be one.
    """
    if kind in {"split", "bonus"}:
        fields(data, {"old_shares", "new_shares"})
        return amount(data["old_shares"], positive=True)/amount(data["new_shares"], positive=True)
    if kind == "rights":
        fields(data, {"shares_before", "consideration", "market_price", "new_shares", "subscription_price"})
        a, consideration, market, c, subscription = (amount(data[k], positive=k in {"shares_before", "market_price", "new_shares"})
            for k in ("shares_before", "consideration", "market_price", "new_shares", "subscription_price"))
        if subscription >= market * Fraction(95, 100):
            return Fraction(1)
        return (a + consideration/market)/(a+c)
    if kind == "extraordinary_distribution":
        fields(data, {"market_price", "distribution_per_share"})
        a, b = amount(data["market_price"], positive=True), amount(data["distribution_per_share"], positive=True)
        # This is what the rendered retained source prints, including denominator B.
        return (a-b)/b
    raise ValueError("Unsupported adjustment kind")


def price_at_notice(terms, notice_date, history):
    """Chronological action coverage through the notice, not conversion date.

    Complete history is a stated factual premise, not established by an empty
    list. This bounded profile handles exact-cent deterministic adjustments;
    unsupported determinations and ambiguous rounding qualify the price.
    """
    day(notice_date)
    fields(history, {"from", "through", "complete", "actions", "par_value_sgd", "issuer_substituted", "terms_amended"})
    issues = []
    if history["complete"] is not True or day(history["from"]) > day("2024-06-18") or day(history["through"]) < day(notice_date):
        issues.append("Complete corporate-action history through notice not established")
    if history["issuer_substituted"] is not False or history["terms_amended"] is not False:
        issues.append("Issuer substitution or amended terms require a new profile")
    if history["par_value_sgd"] is None:
        issues.append("Dated SGD par-value floor missing")
    if issues:
        return _result({"price": None, "trace": []}, issues)
    floor = amount(history["par_value_sgd"], positive=True)
    current = shadow = amount(terms["initial_conversion_price"], positive=True)
    trace, previous, ids = [], None, set()
    if not isinstance(history["actions"], list) or len(history["actions"]) > 10000:
        raise ValueError("Bounded corporate-action list required")
    for action in history["actions"]:
        fields(action, {"id", "date", "kind", "data", "employee_plan", "overlapping_adjustment"})
        at = day(action["date"])
        if (not isinstance(action["id"], str) or not action["id"] or action["id"] in ids
                or (previous is not None and at < previous) or not day(history["from"]) <= at <= day(history["through"])):
            raise ValueError("Actions must be uniquely identified, chronological and covered")
        ids.add(action["id"]); previous = at
        if at <= day("2024-06-18") or at > day(notice_date):
            trace.append({"id": action["id"], "disposition": "OUTSIDE_PRICE_WINDOW"})
            continue
        if action["employee_plan"] is True:
            trace.append({"id": action["id"], "disposition": "EMPLOYEE_PLAN_EXCLUSION"})
            continue
        if action["employee_plan"] is not False or action["overlapping_adjustment"] is not False:
            issues.append("Employee-plan or overlapping-adjustment determination unresolved")
            break
        if action["kind"] not in {"split", "bonus", "rights", "extraordinary_distribution"}:
            issues.append("Contractual determination or successor terms required: " + action["kind"])
            break
        ratio = factor(action["kind"], action["data"])
        if action["kind"] == "extraordinary_distribution":
            trace.append({"id": action["id"], "printed_formula": "(A-B)/B", "literal_factor": str(ratio),
                          "literal_candidate": str(shadow*ratio)})
            issues.append("Printed distribution denominator B: intended operational adjustment unresolved")
            break
        candidate = max(floor, shadow*ratio)
        # No rounding convention is smuggled into the text's imprecise rule.
        if (candidate*100).denominator != 1:
            trace.append({"id": action["id"], "exact_candidate": str(candidate)})
            issues.append("Conversion-price rounding needs an authoritative convention/determination")
            break
        shadow = candidate
        if abs(candidate-current) < current/100:
            trace.append({"id": action["id"], "disposition": "CARRIED_FORWARD", "unapplied_price": str(shadow)})
        else:
            current = candidate
            trace.append({"id": action["id"], "disposition": "APPLIED", "price": str(current)})
    return _result({"price": str(current) if not issues else None, "trace": trace,
                    "unapplied_shadow_price": str(shadow), "price_date": notice_date}, issues)


def successor_price(existing_price, ordinary_window, relevant_window, *, relevant_event,
                    effective_date, conversion_date, approved_entity, arrangements_entered,
                    terms_amended, dealing_days):
    """8(e) arithmetic with five explicitly covered common dealing days.

    More general dual-exchange windows are qualified until separate calendars
    and market conventions are supplied; no issuer geography is inferred.
    """
    issues = []
    event, effective, conversion = map(day, (relevant_event, effective_date, conversion_date))
    if approved_entity is not True or arrangements_entered is not True or terms_amended is not True:
        issues.append("Approved entity/arrangements/amended terms not established")
    if not event <= effective <= event + timedelta(days=7) or conversion < effective:
        issues.append("Seven-calendar-day/new-conversion-effective-date conditions fail")
    days = [day(v) for v in dealing_days]
    if len(days) != len(set(days)) or days != sorted(days):
        raise ValueError("Ordered distinct dealing-day inventory required")
    expected = [v.isoformat() for v in days if v < event][-5:]
    if len(expected) != 5:
        issues.append("Five preceding dealing days not covered")
    means = []
    for window in (ordinary_window, relevant_window):
        if not isinstance(window, list) or len(window) != 5:
            issues.append("Five VWAP observations required")
            continue
        for row in window:
            fields(row, {"date", "vwap", "sgd_fx"})
        if [row["date"] for row in window] != expected:
            issues.append("VWAP window does not match evidenced preceding dealing days")
        means.append(sum(amount(row["vwap"], positive=True)*amount(row["sgd_fx"], positive=True) for row in window)/5)
    return _result({"new_conversion_price": str(amount(existing_price, positive=True)*means[1]/means[0]) if not issues else None,
                    "source_formula": "ECP * VWAPRS / VWAPOS"}, issues)


def offer_allocation(*, event_kind, holder_weight, proceeds_sgd_net, remaining_shares,
                     offer_end, calendar):
    """Conditional 8(h) distribution of evidenced net SGD proceeds/remainder."""
    if event_kind != "trigger":
        raise ValueError("Settlement Shares Offer is restricted to Trigger Events")
    weight = amount(holder_weight)
    if weight > 1 or type(remaining_shares) is not int or remaining_shares < 0:
        raise ValueError("Invalid holder proportion or remaining share count")
    exact_cash = weight*amount(proceeds_sgd_net)*100
    rounded_cents = (exact_cash + Fraction(1, 2)).numerator // (exact_cash + Fraction(1, 2)).denominator
    shares = weight*remaining_shares
    return {"cash_sgd": str(Fraction(rounded_cents, 100)), "remaining_shares": shares.numerator//shares.denominator,
        "cash_due": calendar.after(offer_end, 5), "shares_due_by": calendar.after(offer_end, 5),
        "proceeds_fx_and_costs": "EXPLICIT_INPUT_PREMISES", "actual_payment": "NOT_ESTABLISHED"}
