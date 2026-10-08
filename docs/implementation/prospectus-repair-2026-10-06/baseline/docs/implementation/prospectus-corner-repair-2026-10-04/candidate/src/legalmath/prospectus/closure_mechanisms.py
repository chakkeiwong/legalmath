"""Edition-specific conditional profiles joined to the bank investigation."""
from collections import defaultdict
from datetime import date, timedelta
from fractions import Fraction

from . import master_mechanisms as m, master_control as c
from .common import digest
from .closure_sources import require
from .loss_absorption_reader import load_document

PROFILES = {
    "deutsche-at1-2025": {"document": "deutsche-at1-2025", "sha256": "896cf911fc68cdf9c2e83cdb78e39b0e8443ef18a0f0527788381b158e544ac4",
                           "pages": [52, 53, 54, 55, 62]},
    "bbva-at1-series15-2025": {"document": "bbva-at1-2025-offering", "sha256": "2f32af70cdee5cfb8a3f5190ea58b51411922de2290568987a297b5931e9fca8",
                          "pages": [96, 104, 108, 116, 117, 129, 131]},
    "seb-at1-usd-2024": {"document": "seb-at1-2024-information", "sha256": "76f510479585e1015d61d35c9cfc5d451a35f47f62c0bfce5d3e8d10de2df364",
                         "pages": [39, 40, 43, 44, 59, 60, 65]},
}
PROFILE = "issue-specific-conditional.v1"


def boolean(value):
    require(type(value) is bool, "Explicit Boolean premise required")
    return value


def business_after(start, count, calendar):
    current = date.fromisoformat(start)
    require(type(count) is int and 0 <= count <= 100, "Bounded business-day offset required")
    for _ in range(366):
        if count == 0:
            return current.isoformat()
        current += timedelta(days=1)
        require(current.isoformat() in calendar, "Calendar coverage missing")
        if boolean(calendar[current.isoformat()]):
            count -= 1
    raise ValueError("Calendar does not reach deadline within bounded coverage")


def whole_shares(holdings, price, amount_field):
    price = m.amount(price, positive=True)
    groups = defaultdict(Fraction)
    require(isinstance(holdings, list) and holdings, "Holdings required")
    for h in holdings:
        require(isinstance(h.get("registration_name"), str) and h["registration_name"], "Registration grouping required")
        groups[h["registration_name"]] += m.amount(h[amount_field], positive=True)
    return [{"registration_name": name, "amount": str(value), "shares": (value / price).__floor__(),
             "fraction_without_cash_compensation": str(value / price - (value / price).__floor__())}
            for name, value in sorted(groups.items())]


def half_up_cent(value):
    return Fraction((m.amount(value) * 100 + Fraction(1, 2)).__floor__(), 100)


def deutsche(s):
    if s["operation"] == "write_down":
        result = m.write_down(**{k: s[k] for k in ("ratio", "required_loss", "principal", "others", "currency", "premise_kind")})
        trigger = date.fromisoformat(s["trigger_date"])
        determined = date.fromisoformat(s["determination_date"]) if s.get("determination_date") else None
        deadline = date.fromisoformat(s["reviewed_outer_deadline"]) if s.get("reviewed_outer_deadline") else None
        require(determined is None or determined >= trigger, "Determination precedes trigger")
        require(deadline is None or deadline >= trigger, "Deadline precedes trigger")
        notices = s.get("notices", {})
        given = []
        for name in ("trigger_publication", "amount_publication"):
            if notices.get(name):
                value = date.fromisoformat(notices[name])
                require(value >= trigger, "Notice precedes trigger")
                given.append(value + timedelta(days=3))
        result.update(outer_deadline_met=(determined <= deadline) if determined and deadline else None,
                      without_undue_delay="REQUIRES_SEPARATE_REVIEW",
                      holder_notices_given_at=max(given).isoformat() if len(given) == 2 else None,
                      missing_notice_invalidates_write_down=False,
                      event_effectiveness="REQUIRES_ALL_APPLICABLE_NOTICE_AND_IMPLEMENTATION_EVIDENCE",
                      operational_rounded_principal=None, rounding="NO_PRINCIPAL_QUANTUM_ESTABLISHED",
                      cash_settlement="NOT_CREATED_BY_WRITE_DOWN")
        return result
    require(s["operation"] == "write_up", "Unsupported Deutsche operation")
    fields = ("annual_profit", "written_down_initial", "tier1", "distributions", "mda_available", "own_initial",
              "pool_initial", "own_prevailing", "issuer_selected_total", "conditions", "premise_kind")
    conditions = dict(s["conditions"])
    publication = date.fromisoformat(s["notice_publication"]) if s.get("notice_publication") else None
    payment = date.fromisoformat(s["payment_date"])
    notice_given = publication + timedelta(days=3) if publication else None
    timely = notice_given <= payment - timedelta(days=10) if notice_given else None
    if timely is not True:
        return {"status": "MISSING_OR_LATE_NOTICE", "write_up": None, "notice_timely": timely,
                "issuer_discretion_retained": True, "actual_write_up": "NOT_ESTABLISHED"}
    require(conditions["notice_and_payment_date_met"] is True, "Separate payment-date conditions must be satisfied")
    result = m.write_up(**{k: s[k] for k in fields})
    result.update(notice_given_at=notice_given.isoformat(), notice_timely=timely, effective_from=payment.isoformat())
    return result


def bbva(s):
    require(s["currency"] == "EUR", "BBVA profile requires EUR quantities")
    triggered = m.amount(s["issuer_determined_cet1_ratio"]) < Fraction(41, 800)
    capital_reduction = boolean(s["capital_reduction"])
    override = boolean(s["condition_7_7_redemption_override"])
    opt_out = s.get("valid_timely_opt_out")
    if opt_out is not None:
        boolean(opt_out)
    if triggered:
        path = "MANDATORY_6_1"
    elif capital_reduction and override:
        path = "REDEMPTION_7_7"
    elif capital_reduction and opt_out is None:
        return {"status": "MISSING_ELECTION_EVIDENCE", "conversion": None}
    elif capital_reduction:
        path = "OPTED_OUT_6_2" if opt_out else "CONVERSION_6_2"
    else:
        path = "NO_CONVERSION_EVENT_UNDER_PREMISES"
    if path not in {"MANDATORY_6_1", "CONVERSION_6_2"}:
        return {"path": path, "conversion": False, "later_6_1_conversion_still_possible": True}
    listed = boolean(s["listed"])
    components = [m.amount(s["adjusted_floor_price"], positive=True), m.amount(s["nominal_share_value"], positive=True)]
    if listed:
        require(len(s["five_eligible_closing_prices"]) == 5, "Five preselected eligible closing prices required")
        reference = sum((m.amount(p, positive=True) for p in s["five_eligible_closing_prices"]), Fraction()) / 5
        components.append(half_up_cent(str(reference)))
    price = max(components)
    return {"path": path, "conversion": True, "conversion_price": str(price),
            "holder_entitlements": whole_shares(s["holdings"], str(price), "liquidation_preference"),
            "distributions": "CANCELLED_UNDER_6_1" if triggered else "SUBJECT_TO_CONDITION_4_AND_6_2",
            "settlement_date": s.get("settlement_date"), "depository_delivery": "NOT_ESTABLISHED",
            "holder_delivery": "NOT_ESTABLISHED", "adjustments": "SUPPLIED_ADJUSTED_FLOOR; RETROACTIVE_ADJUSTMENTS_REQUIRE_SEPARATE_EVIDENCE"}


def seb(s):
    require(s["currency"] == "USD", "SEB profile requires USD principal and floor")
    triggered = min(m.amount(s["bank_cet1_ratio"]), m.amount(s["group_cet1_ratio"])) < Fraction(41, 800)
    if not triggered:
        return {"conversion": False, "principal_after_conversion": None}
    rate = m.amount(s["usd_per_sek"], positive=True)
    components = [m.amount(s["adjusted_floor_usd"], positive=True), m.amount(s["quota_value_sek"], positive=True) * rate]
    if boolean(s["listed"]):
        components.append(m.amount(s["reviewed_current_market_price_sek"], positive=True) * rate)
    price = max(components)
    return {"conversion": True, "conversion_price_usd": str(price), "principal_after_conversion": "0",
            "holder_entitlements": whole_shares(s["holdings"], str(price), "principal"),
            "economic_recovery": None, "economic_recovery_status": "SHARE_RIGHTS_AND_OFFER_PROCEEDS_REQUIRE_VALUATION_AND_DELIVERY_EVIDENCE",
            "interim_delivery": "NOT_ESTABLISHED", "registration": "NOT_ESTABLISHED", "holder_delivery": "NOT_ESTABLISHED",
            "missing_notice_invalidates_conversion": False}


def investigate(issue, documents, root, joined_request, scenario=None):
    require(issue["id"] in PROFILES, "Unsupported issue-specific profile")
    profile = PROFILES[issue["id"]]
    key = profile["document"]
    require(any(s["id"] == key for s in issue["documents"]) and documents[key]["sha256"] == profile["sha256"],
            "Wrong issue or source edition for numerical profile")
    doc = load_document(documents[key], root)
    anchors = [{"page": page, "text_sha256": digest(doc["pages"][page - 1]["text"])} for page in profile["pages"]]
    calculation = None
    if scenario is not None:
        require(scenario.get("premise_kind") in {"HYPOTHETICAL", "SOURCE_DEPENDENT_PROPOSAL"}, "Explicit conditional provenance required")
        require(scenario.get("issue_id") == issue["id"] and scenario.get("source_sha256") == profile["sha256"],
                "Scenario bound to another issue or edition")
        fn = {"deutsche-at1-2025": deutsche, "bbva-at1-series15-2025": bbva, "seb-at1-usd-2024": seb}[issue["id"]]
        calculation = fn(scenario)
    result = {"profile": PROFILE, "issue_id": issue["id"], "source_sha256": profile["sha256"], "anchors": anchors,
              "joined_request_sha256": digest(joined_request), "scenario_sha256": digest(scenario),
              "calculation": calculation, "status": "CONDITIONAL" if scenario else "INPUTS_REQUIRED",
              "scope": "Named conditional calculation only; full timing, price adjustments, settlement and law remain qualified",
              "actual_loss_or_event": "NOT_ESTABLISHED", "may_execute_transaction": False}
    return {**result, "sha256": digest(result)}


def execute_profiles(folder, data, current):
    from . import evidence_closure as ec, closure_phases as phases
    from .feature_investigation import investigate as join
    from ..transaction.evidence import Store
    parent = c.ROOT / current["phases"]["S3"]["directory"]
    store = Store(parent / "bank/store")
    # Work in a new store; never add bytes to a sealed upstream attempt.
    import shutil
    shutil.copytree(store.directory, folder / "bank/store")
    store = Store(folder / "bank/store")
    row_by_id = {r["id"]: r for r in phases.rows(data)}
    results = []
    scenarios = phases.optional("scenarios.json", {})
    require(isinstance(scenarios, dict) and set(scenarios) <= set(PROFILES), "Unknown numerical scenario issue")
    reviews = phases.optional("mechanism-reviews.json", [])
    require(isinstance(reviews, list), "Mechanism reviews must be a list")
    seen = set()
    for review in reviews:
        from .closure_sources import check_quote, reviewer
        key = review["issue_id"]
        require(set(review) == {"issue_id", "profile_binding", "reviewer", "reason", "anchors"} and
                key in PROFILES and key not in seen, "Unknown or duplicate mechanism review")
        seen.add(key)
        require(review["profile_binding"] == digest(PROFILES[key]) and review["reason"] and review["anchors"],
                "Stale or incomplete mechanism review")
        reviewer(review["reviewer"])
        for anchor in review["anchors"]:
            check_quote(anchor, data["documents"], c.ROOT)
    c.write(folder / "mechanism-reviews.json", reviews)
    for issue in data["issues"]:
        if issue["id"] not in PROFILES:
            continue
        prior = c.read(parent / "receipts" / (issue["id"] + ".json"))
        request = {"profile": PROFILE, "scenario": scenarios.get(issue["id"])}
        receipt = join(row_by_id[issue["id"]], issue, data["documents"], c.ROOT,
                       prior["joined_request"]["bank_request"], store, instrument_request=request,
                       product_assertions_sha256=prior["joined_request"]["product_assertions_sha256"],
                       issuer_basis_source_ids=prior["joined_request"]["issuer_basis_source_ids"])
        require(phases.old.obligations(receipt) == phases.old.obligations(prior), "Numerical adapter changed bank duties")
        c.write(folder / "receipts" / (issue["id"] + ".json"), receipt)
        results.append({"id": issue["id"], "profile": PROFILE, "status": receipt["instrument_investigation"]["status"],
                        "may_execute_transaction": receipt["may_execute_transaction"]})
    require({r["id"] for r in results} == set(PROFILES), "One or more declared numerical profiles were not joined")
    require(not any(r["may_execute_transaction"] for r in results), "Numerical profiles cannot grant permission")
    c.write(folder / "integration.json", results)
    return {"status": "QUALIFIED", "joined_profiles": results,
            "repairs": ["Joined separate Deutsche, BBVA and SEB conditional profiles to the real bank investigator"],
            "remaining": ["G21/G23: operative rounding, full price/adjustment and settlement rules, other issuer profiles and actual numerical inputs remain",
                          "G22: adapter implemented; broader operational acceptance still requires source and factual admission"]}
