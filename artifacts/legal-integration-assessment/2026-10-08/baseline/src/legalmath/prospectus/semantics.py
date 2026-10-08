"""Exact, conditional semantics. These definitions do not certify English meaning."""
from dataclasses import dataclass
from fractions import Fraction
from itertools import product


def exact(value):
    if isinstance(value, (float, bool)):
        raise ValueError("Exact quantities require an integer, decimal string or rational")
    return Fraction(value)


@dataclass(frozen=True)
class Contract:
    mechanism: str
    threshold: Fraction
    comparison: str = "lt"
    viability_trigger: bool = True
    reduction: Fraction = Fraction(1)
    conversion_price: Fraction | None = None

    def __post_init__(self):
        for value in (self.threshold, self.reduction, self.conversion_price):
            if value is not None and not isinstance(value, (int, Fraction)):
                raise ValueError("Contract quantities must be exact rational values")
            if isinstance(value, bool):
                raise ValueError("Boolean is not a contract quantity")
        if type(self.viability_trigger) is not bool:
            raise ValueError("Viability trigger must be Boolean")
        if self.mechanism not in ("permanent_write_down", "temporary_write_down", "equity_conversion", "none"):
            raise ValueError("Unsupported contractual mechanism")
        if self.comparison not in ("lt", "le") or not 0 <= self.threshold <= 1 or not 0 <= self.reduction <= 1:
            raise ValueError("Invalid ratio or comparator")
        if self.mechanism == "equity_conversion" and (self.conversion_price is None or self.conversion_price <= 0):
            raise ValueError("Conversion requires a positive, same-currency price")


def transition(contract, principal, capital_ratio, viability, *, restore=0, restore_authorized=False):
    """One loss event then one explicitly authorized restoration in a fixed currency.

    No market valuation, repeated-trigger schedule, FX conversion, statutory bail-in
    or anti-dilution adjustment is silently supplied by this bounded model.
    """
    principal, capital_ratio, restore = map(exact, (principal, capital_ratio, restore))
    if principal < 0 or not 0 <= capital_ratio <= 1 or restore < 0 or type(viability) is not bool or type(restore_authorized) is not bool:
        raise ValueError("Invalid event/quantity")
    trigger = (capital_ratio < contract.threshold if contract.comparison == "lt" else capital_ratio <= contract.threshold)
    trigger = trigger or (contract.viability_trigger and viability)
    debt, equity, restorable = principal, Fraction(0), Fraction(0)
    if trigger and contract.mechanism == "equity_conversion":
        debt, equity = Fraction(0), principal / contract.conversion_price
    elif trigger and contract.mechanism in ("permanent_write_down", "temporary_write_down"):
        lost = principal * contract.reduction
        debt -= lost
        if contract.mechanism == "temporary_write_down":
            restorable = lost
            restored = min(restore, lost) if restore_authorized else Fraction(0)
            debt += restored
            restorable -= restored
    return {"triggered": trigger, "debt_principal": debt, "equity_units": equity, "restorable": restorable}


def distribution(principal, declared, scheduled, cumulative=False, arrears=0):
    principal, scheduled, arrears = map(exact, (principal, scheduled, arrears))
    if min(principal, scheduled, arrears) < 0 or type(declared) is not bool or type(cumulative) is not bool:
        raise ValueError("Invalid distribution")
    if not cumulative and arrears:
        raise ValueError("This model has no accumulated arrears for non-cumulative distributions")
    return {"principal": principal, "paid": scheduled + arrears if declared else Fraction(0),
            "arrears": Fraction(0) if declared or not cumulative else scheduled + arrears}


def possible_decision(required, observations, predicate):
    """Enumerate all completions of relevant Boolean evidence. No closed-world default.

    None means unknown; the literal 'conflict' means inconsistent observations.
    Conflicts are not repaired by discarding one side. Domain is at most 12 facts.
    """
    if len(required) > 12 or len(set(required)) != len(required):
        raise ValueError("Unsupported evidence domain")
    if any(k not in required for k in observations):
        raise ValueError("Unexpected field, including expected answers or quality labels")
    for value in observations.values():
        if value is not None and value != "conflict" and type(value) is not bool:
            raise ValueError("Evidence is Boolean, unknown or conflict")
    conflicts = [k for k in required if observations.get(k) == "conflict"]
    missing = [k for k in required if observations.get(k) is None]
    if conflicts:
        return {"decision": "CONFLICT", "missing": missing, "conflicts": conflicts, "worlds": 0, "witnesses": {}}
    witnesses = {}
    count = 0
    for values in product((False, True), repeat=len(missing)):
        world = {k: observations[k] for k in required if k not in missing}
        world.update(zip(missing, values))
        result = predicate(world)
        if type(result) is not bool:
            raise ValueError("Predicate must return Boolean")
        witnesses.setdefault(str(result).lower(), world)
        count += 1
    decision = "UNDETERMINED" if len(witnesses) == 2 else "TRUE" if "true" in witnesses else "FALSE"
    return {"decision": decision, "missing": missing, "conflicts": [], "worlds": count, "witnesses": witnesses}


CLASS_FACTS = ("bond", "perpetual", "subordinated", "contingent_conversion", "contractual_write_down")
SPI_FACTS = ("client_qualifies", "category_selected", "category_knowledge", "consent_active",
             "assessment_current", "threshold_compliant", "other_applicable_requirements")


def complex_bond(facts):
    return facts["bond"] and any(facts[k] for k in CLASS_FACTS[1:])


def eligible(facts):
    return all(facts[k] for k in SPI_FACTS)


def financial(portfolio_cents, net_assets_ex_home_cents):
    if any(type(v) is not int or v < 0 for v in (portfolio_cents, net_assets_ex_home_cents)):
        raise ValueError("Amounts require nonnegative integer HKD cents")
    return exact(portfolio_cents) >= 4_000_000_000 or exact(net_assets_ex_home_cents) >= 8_000_000_000


def threshold(gross_cents, maximum_cents, designated, adding_funds):
    """Only the amount condition, under assumed valid monitoring arrangements.

    Annex 8.3/FAQ 6 permit continued designated-account transactions above the
    threshold without top-up. The caller must separately establish proper controls,
    reviews, transferred exposure treatment and leverage-inclusive gross exposure.
    """
    if any(type(v) is not int for v in (gross_cents, maximum_cents)):
        raise ValueError("Exposure amounts require integer HKD cents")
    gross, maximum = exact(gross_cents), exact(maximum_cents)
    if min(gross, maximum) < 0 or type(designated) is not bool or type(adding_funds) is not bool:
        raise ValueError("Invalid threshold inputs")
    return gross <= maximum or (designated and not adding_funds)


def duties(solicited, complex_product, streamlined, offering_documents, bond_summary, explanation_requested):
    """Selected SPI relief only, conditional on all eligibility premises."""
    if any(type(v) is not bool for v in (solicited, complex_product, streamlined, offering_documents, bond_summary, explanation_requested)):
        raise ValueError("Duty premises must be Boolean")
    active = solicited or complex_product
    return {
        "suitability_matching_required": active and not streamlined,
        "pdd_relief": complex_product and not solicited and streamlined and (offering_documents or bond_summary),
        "explanation_required": active and (not streamlined or explanation_requested),
        "annual_complex_warning_relief": complex_product and not solicited and streamlined,
    }
