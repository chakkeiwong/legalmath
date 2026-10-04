"""Fixed obligation inventory and conditional specifications with source anchors.

These are inspectable interpretation proposals, not certified English meaning.
The request cannot supply a smaller inventory or a precomputed finding.
"""
from copy import deepcopy

from ..compliance import Layer
from ..prospectus.models import definitions as product_definitions, make_model

PROFILE = "us-bank-hk-private-client.v1"


def spec(facts, outputs, meaning, anchors):
    return {"facts": [(x, "bool") if isinstance(x, str) else x for x in facts],
            "outputs": [(name, "bool", expression) for name, expression in outputs],
            "meaning": meaning, "anchors": anchors}


def specifications():
    bsa = ["written_program", "board_authorization_recorded", "board_minutes",
           "customer_identification_program", "internal_controls", "independent_testing",
           "responsible_officer", "personnel_training"]
    dd = ["owner_identity", "political_figure_screen", "funds_and_purpose",
          "activity_review_and_reporting", "failure_procedures"]
    private_scope = "(and covered_institution (>= required_minimum_usd_cents (integer 100000000)) non_us_owner liaison (or established_us maintained_us administered_us managed_us))"
    cmic_trigger = "(and transaction_purchase_or_sale designated_issuer covered_security restriction_in_force (or ultimate_party_us_person (and principal_capacity actor_us_person)))"
    result = {
        "entity": spec(["organized_under_us_law", "present_in_us"],
            [("us_entity", "(or organized_under_us_law present_in_us)")],
            "Conditional entity/presence limb only; branch identity, individuals and territory remain factual premises.",
            [("eo14032", "organized under the laws of the United States")]),
        "cmic": spec(["transaction_purchase_or_sale", "principal_capacity", "designated_issuer",
            "covered_security", "restriction_in_force", "actor_us_person", "ultimate_party_us_person",
            "solely_divestment", "divestment_window_open", "applicable_ofac_authorization", "otherwise_permissible"],
            [("satisfied", "(and otherwise_permissible (or (not " + cmic_trigger + ") applicable_ofac_authorization (and solely_divestment divestment_window_open)))")],
            "Selected CMIC consequences. Capacity, exposure, timing, every license condition and otherwise-permissible activity must be established separately. An affirmative result covers only these formal premises.",
            [("ofac-cmic-services", "provided that the underlying purchase or sale would not otherwise violate"),
             ("ofac-cmic-holding", "365-day")]),
        "bsa_program": spec(["national_bank", "covered_savings_association", *bsa],
            [("applies", "(or national_bank covered_savings_association)"),
             ("satisfied", "(and " + " ".join(bsa) + ")")],
            "Selected 12 CFR 21.21 program requirements from the retained 2025 edition. Existence and adequacy of the listed controls are separate factual/interpretive premises. Board authorization is a business fact, never a quality label.",
            [("us-bank-bsa-program-2025", "controls to assure ongoing compliance;")]),
        "private_account": spec(["covered_institution", ("required_minimum_usd_cents", "integer"),
            "non_us_owner", "liaison", "established_us", "maintained_us", "administered_us", "managed_us",
            *dd, "senior_foreign_political_figure", "enhanced_scrutiny"],
            [("applies", private_scope),
             ("satisfied", "(and " + " ".join(dd) + " (or (not senior_foreign_political_figure) enhanced_scrutiny))")],
            "Selected 31 CFR 1010.605(m), 1010.620(a)-(d), retained 2025 edition. The threshold is the required minimum in exact USD cents, not today's balance. Territorial scope is tested for this provision only; false does not waive other AML requirements.",
            [("us-private-banking-definitions-2025", "less than $1,000,000;"),
             ("us-private-banking-due-diligence-2025", "(d) Special procedures when due dili-")]),
        "cmic_reporting": spec(["us_financial_institution", "attempted_cmic_prohibited_transaction",
            "transaction_rejected", "rejection_reported_in_time"],
            [("applies", "(and us_financial_institution attempted_cmic_prohibited_transaction)"),
             ("satisfied", "(and transaction_rejected rejection_reported_in_time)")],
            "Selected FAQ 1048 rejection/reporting duties. Trigger classification and reporting deadline require independent evidence; this does not imply an asset-blocking duty.",
            [("ofac-cmic-intermediation", "must be rejected and reported to OFAC within 10 business days")]),
    }
    for name in ("complex", "financial", "client", "threshold", "eligibility", "duties"):
        d = deepcopy(product_definitions()[name])
        if name == "threshold":
            d["facts"].append(("threshold_controls_established", "bool"))
            amount = d["outputs"][0][2]
            d["outputs"].append(("threshold_compliant", "bool", "(and threshold_controls_established " + amount + ")"))
            d["meaning"] += " The combined result additionally requires source-supported threshold controls; the amount condition alone cannot establish them."
        d["anchors"] = [(d["source"], None)]
        result["product_" + name] = d
    return result


# Every row must remain visible, including rule families without an executable
# interpretation. This closes omissions within this catalog, not outside it.
ROWS = (
    ("scope.parties", Layer.SCOPE, None, "Complete legal entity, branch, capacity and jurisdiction evidence"),
    ("scope.coverage", Layer.SCOPE, None, "Complete applicable-law inventory and conflict resolution remain unproved"),
    ("sanctions.cmic", Layer.SANCTIONS, "cmic", "Selected conditional CMIC rules"),
    ("sanctions.blocking", Layer.SANCTIONS, None, "Designation identity, ownership completeness and applicable blocking authority"),
    ("sanctions.other", Layer.SANCTIONS, None, "Other applicable programs, exposure and license conditions"),
    ("bank.bsa_program", Layer.BANK, "bsa_program", "Selected program controls only"),
    ("bank.licensing", Layer.BANK, None, "Entity/activity-specific authority, licensing and prudential restrictions"),
    ("client.private_account", Layer.CLIENT, "private_account", "Selected US private-account obligations only"),
    ("client.other", Layer.CLIENT, None, "Other jurisdiction-specific client/account and AML controls"),
    ("product.spi", Layer.PRODUCT, "product_eligibility", "Existing conditional SPI premises; not product or transaction permission"),
    ("product.other", Layer.PRODUCT, None, "Other conduct, distribution, prospectus dependencies, issuer law and regulatory events"),
    ("policy.internal", Layer.POLICY, None, "Actual versioned bank policies and account mandate have not been supplied"),
    ("operations.route", Layer.OPERATIONS, None, "Custodian, intermediary, currency and settlement obligations"),
    ("operations.cmic_reporting", Layer.OPERATIONS, "cmic_reporting", "Selected rejection/reporting duties only"),
)


def inventory(profile):
    if profile != PROFILE:
        raise ValueError("Unsupported jurisdiction/activity profile: retain qualification")
    return [{"rule_id": key, "version": "1", "layer": layer.value,
             "specification": name, "scope": scope} for key, layer, name, scope in ROWS]


def declarations():
    result = {}
    for d in specifications().values():
        for name, typ in d["facts"]:
            if name in result and result[name] != typ:
                raise ValueError("Inconsistent fact types")
            result[name] = typ
    return result


def models():
    return {name: make_model("bank_" + name, d) for name, d in specifications().items()}
