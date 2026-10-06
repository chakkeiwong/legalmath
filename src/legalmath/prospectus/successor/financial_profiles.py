"""Guarded named subcalculations. No full settlement profile is advertised."""
from calendar import monthrange
from datetime import date
from .contracts import QueryResult
from .. import closure_mechanisms as kernels

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
    if scenario.get("issue_id") != issue or scenario.get("source_sha256") != profile["sha256"]:
        raise ValueError("Financial scenario binding mismatch")
    if scenario.get("premise_kind") not in {"HYPOTHETICAL", "SOURCE_DEPENDENT_PROPOSAL"}:
        raise ValueError("Explicit conditional scenario required")
    fn = {"deutsche-at1-2025": kernels.deutsche, "bbva-at1-series15-2025": kernels.bbva,
          "seb-at1-usd-2024": kernels.seb}[issue]
    try:
        calculated = fn(scenario)
    except (KeyError, ValueError) as exc:
        return QueryResult("Q5", "UNSUPPORTED", unresolved=["Incomplete or invalid premises: " + str(exc)]).json()
    return QueryResult("Q5", "CONDITIONAL", value={"calculation": calculated,
        "unit": scenario.get("currency"), "scope": "NAMED_SUBCALCULATION_ONLY",
        "inputs": scenario, "full_settlement_supported": False,
        "remaining": INVENTORY[issue]["missing"], "actual_event": "NOT_ESTABLISHED"}).json()
