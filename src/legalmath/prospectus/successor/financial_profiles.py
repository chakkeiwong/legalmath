"""Guarded named subcalculations. No full settlement profile is advertised."""
from calendar import monthrange
from datetime import date
from .contracts import QueryResult
from .. import closure_mechanisms as kernels
from .anchors import fields

INVENTORY = {
    "deutsche-at1-2025": {"kernel": "write_down/write_up", "missing": ["principal quantum", "reviewed notice/deadline", "actual facts"]},
    "bbva-at1-series15-2025": {"kernel": "conversion price/whole shares", "missing": ["adjustments", "settlement", "delivery"]},
    "seb-at1-usd-2024": {"kernel": "conversion price/whole shares", "missing": ["FX observation", "settlement", "delivery"]},
    "ubs": {"kernel": "existing source-bound adapter only", "missing": ["successor mapping", "actual facts"]},
}


def add_months(value, months, convention):
    if type(months) is not int or abs(months) > 1200:
        raise ValueError("Bounded integer months required")
    if convention not in {"CLAMP", "ERROR"}:
        raise ValueError("Explicit reviewed rounding convention required")
    day = date.fromisoformat(value)
    n = day.year * 12 + day.month - 1 + months
    year, month = n // 12, n % 12 + 1
    last = monthrange(year, month)[1]
    if day.day > last and convention == "ERROR":
        raise ValueError("Ambiguous month-end requires legal convention")
    return date(year, month, min(day.day, last)).isoformat()


def validate_scenario(issue, s):
    """Validate even inactive branches: bad inputs must not be hidden by a trigger."""
    common = {"issue_id", "source_sha256", "premise_kind", "currency"}
    numbers, booleans, optional = set(), set(), set()
    extra = set()
    if issue == "deutsche-at1-2025":
        if s.get("operation") == "write_down":
            numbers = {"ratio", "required_loss", "principal"}
            extra = {"operation", "others", "trigger_date"}
            optional = {"determination_date", "reviewed_outer_deadline", "notices"}
            if not isinstance(s.get("others"), list):
                raise ValueError("others must be a list")
            for row in s["others"]:
                fields(row, {"currency", "effective", "principal"}, {"currency", "effective", "principal"})
                kernels.boolean(row["effective"])
                kernels.m.amount(row["principal"], positive=True)
                if row["currency"] != s.get("currency"):
                    raise ValueError("Other principal currency mismatch")
            notices = s.get("notices", {})
            fields(notices, {"trigger_publication", "amount_publication"})
            for value in notices.values():
                date.fromisoformat(value)
            date.fromisoformat(s["trigger_date"])
            for key in ("determination_date", "reviewed_outer_deadline"):
                if key in s:
                    date.fromisoformat(s[key])
        elif s.get("operation") == "write_up":
            numbers = {"annual_profit", "written_down_initial", "tier1", "distributions", "mda_available",
                       "own_initial", "pool_initial", "own_prevailing", "issuer_selected_total"}
            extra = {"operation", "conditions", "payment_date"}
            optional = {"notice_publication"}
            conditions = {"subsequent_financial_year", "no_annual_loss_created", "no_continuing_or_recreated_trigger",
                          "regulatory_conditions_met", "pari_passu_conditions_met", "notice_and_payment_date_met",
                          "issuer_elected_write_up"}
            fields(s.get("conditions"), conditions, conditions)
            for v in s["conditions"].values():
                kernels.boolean(v)
            date.fromisoformat(s["payment_date"])
            if "notice_publication" in s:
                date.fromisoformat(s["notice_publication"])
        else:
            raise ValueError("Unsupported Deutsche operation")
    elif issue == "bbva-at1-series15-2025":
        numbers = {"issuer_determined_cet1_ratio", "adjusted_floor_price", "nominal_share_value"}
        booleans = {"capital_reduction", "condition_7_7_redemption_override", "listed"}
        extra = {"holdings", "five_eligible_closing_prices"}
        optional = {"valid_timely_opt_out", "settlement_date"}
        prices = s.get("five_eligible_closing_prices")
        if not isinstance(prices, list) or len(prices) != (5 if s.get("listed") else 0):
            raise ValueError("Price window must be a list of five prices when listed, otherwise empty")
        for price in prices:
            kernels.m.amount(price, positive=True)
        if s.get("valid_timely_opt_out") is not None:
            kernels.boolean(s["valid_timely_opt_out"])
        if "settlement_date" in s:
            date.fromisoformat(s["settlement_date"])
    elif issue == "seb-at1-usd-2024":
        numbers = {"bank_cet1_ratio", "group_cet1_ratio", "usd_per_sek", "adjusted_floor_usd", "quota_value_sek"}
        booleans = {"listed"}
        extra = {"holdings"}
        if s.get("listed"):
            numbers.add("reviewed_current_market_price_sek")
    required = common | numbers | booleans | extra
    fields(s, required | optional, required)
    if s["currency"] != {"deutsche-at1-2025": "EUR", "bbva-at1-series15-2025": "EUR", "seb-at1-usd-2024": "USD"}[issue]:
        raise ValueError("Profile currency mismatch")
    for key in numbers:
        kernels.m.amount(s[key])
    for key in booleans:
        kernels.boolean(s[key])
    if "holdings" in extra:
        amount_field = "principal" if issue == "seb-at1-usd-2024" else "liquidation_preference"
        if not isinstance(s["holdings"], list) or not s["holdings"]:
            raise ValueError("Nonempty holdings list required")
        for h in s["holdings"]:
            fields(h, {"legal_holder_id", "registration_name", "account_id", amount_field},
                   {"legal_holder_id", "registration_name", amount_field})
        kernels.whole_shares(s["holdings"], "1", amount_field)


def assess(bundle, scenario):
    if scenario is None:
        return QueryResult("Q5", "UNSUPPORTED", unresolved=["No complete named financial scenario supplied"],
                           value={"inventory": INVENTORY}).json()
    issue = bundle["instrument_id"]
    profile = kernels.PROFILES.get(issue)
    if not profile:
        return QueryResult("Q5", "UNSUPPORTED", unresolved=["No supported profile for this instrument"]).json()
    if not any(d["sha256"] == profile["sha256"] for d in bundle["documents"]):
        raise ValueError("Financial profile source edition mismatch")
    if not isinstance(scenario, dict):
        return QueryResult("Q5", "UNSUPPORTED", unresolved=["Scenario must be an object"]).json()
    if scenario.get("issue_id") != issue or scenario.get("source_sha256") != profile["sha256"]:
        raise ValueError("Financial scenario binding mismatch")
    if scenario.get("premise_kind") not in {"HYPOTHETICAL", "SOURCE_DEPENDENT_PROPOSAL"}:
        raise ValueError("Explicit conditional scenario required")
    fn = {"deutsche-at1-2025": kernels.deutsche, "bbva-at1-series15-2025": kernels.bbva,
          "seb-at1-usd-2024": kernels.seb}[issue]
    try:
        validate_scenario(issue, scenario)
    except (KeyError, ValueError, TypeError) as exc:
        return QueryResult("Q5", "UNSUPPORTED", unresolved=["Incomplete or invalid premises: " + str(exc)]).json()
    try:
        calculated = fn(scenario)
    except ValueError as exc:
        return QueryResult("Q5", "UNSUPPORTED", unresolved=["Invalid numerical premises: " + str(exc)]).json()
    return QueryResult("Q5", "CONDITIONAL", value={"calculation": calculated,
        "unit": scenario.get("currency"), "scope": "NAMED_SUBCALCULATION_ONLY",
        "inputs": scenario, "full_settlement_supported": False,
        "remaining": INVENTORY[issue]["missing"], "actual_event": "NOT_ESTABLISHED"}).json()
