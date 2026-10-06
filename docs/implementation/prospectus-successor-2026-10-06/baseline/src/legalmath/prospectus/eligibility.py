"""Source-bound conditional Hong Kong investigation joined to the bank inventory.

These are declared interpretations of retained provisions. Neither a successful
calculation nor a source quotation establishes the interpretation's legal truth.
"""
from copy import deepcopy

from ..canonical import digest
from ..transaction import engine
from ..transaction.evidence import Registry, facts, fields
from .models import make_model
from .semantics import Contract, exact, transition

PROFILE = "joined-loss-absorption.v1"
FAQ = "hkma-loss-absorption-annex2-20221021"
ANNEX = "hkma-loss-absorption-annex1-20221021"


def specifications():
    def spec(names, outputs, meaning, source, quote):
        return {"facts": [(n, "bool") for n in names.split()],
                "outputs": [(n, "bool", expression) for n, expression in outputs],
                "meaning": meaning, "anchors": [(source, quote)]}
    return {
        "scope": spec("debt_legal_form qualifying_contingent_loss_absorption plain_debt_or_deposit qualifying_wrapper",
            [("in_scope_product", "(or qualifying_wrapper (and debt_legal_form qualifying_contingent_loss_absorption (not plain_debt_or_deposit)))")],
            "Direct debt with qualifying contingent conversion/write-down, or a qualifying wrapper. Wrapper scope is a separate document-dependent premise; no numerical fund threshold is invented. Equity-form preferred shares are not direct debt; possible bail-in alone is insufficient.",
            FAQ, "Not all debt instruments which could be bailed in are within the scope."),
        "faq9": spec("specific_ia_am_contracts order_from_ia_am regulated_ia_am execution_custody_only no_direct_client_contact written_responsibility_agreement client_informed_in_writing arrangement_current direct_customer_request circumvention",
            [("faq9_exception", "(and specific_ia_am_contracts order_from_ia_am regulated_ia_am execution_custody_only no_direct_client_contact written_responsibility_agreement client_informed_in_writing arrangement_current (not direct_customer_request) (not circumvention))")],
            "FAQ 9 exception for the described broker arrangements only. Each condition is an explicit factual premise. Arrangement changes require reassessment and written customer updates; an earlier notification does not establish the current arrangement.",
            FAQ, "the customer has been informed in writing of the arrangement"),
        "restriction": spec("registered_institution in_scope_product faq9_exception professional_investor",
            [("pi_restriction_satisfied", "(or (not registered_institution) (not in_scope_product) faq9_exception professional_investor)")],
            "Annex 1 A restricts RI sales to professional investors in scope; FAQ 9 is a specific broker exception. SPI status, loss size and B/C/D exemptions cannot override A.",
            ANNEX, "Products only to professional investors"),
        "exemption": spec("institutional_pi corporate_pi paragraph_15_3a_complied paragraph_15_3b_complied",
            [("bcd_exempt", "(or institutional_pi (and corporate_pi paragraph_15_3a_complied paragraph_15_3b_complied))")],
            "Annex 1 F removes B/C/D for the specified PI categories; corporate PI requires both stated Code provisions. It does not remove the PI restriction or other laws.",
            ANNEX, "15.3A and 15.3B"),
        "duties": spec("registered_institution in_scope_product faq9_exception bcd_exempt loss_absorption_fund discretionary_portfolio_management",
            [("risk_rating_required", "(and registered_institution in_scope_product (not faq9_exception) (not bcd_exempt))"),
             ("enhanced_suitability_required", "(and registered_institution in_scope_product (not faq9_exception) (not bcd_exempt) (not loss_absorption_fund))"),
             ("enhanced_disclosure_required", "(and registered_institution in_scope_product (not faq9_exception) (not bcd_exempt) (not loss_absorption_fund))"),
             ("portfolio_mode_available", "(and registered_institution in_scope_product (not faq9_exception) discretionary_portfolio_management)")],
            "Selected Annex 1 B/C/D duties. Funds are exempt from C/D, with other SFC duties remaining. FAQ 8 disclosure flexibility needs separate authority. FAQ 10 permits holistic DPM handling, not disappearance or assumed performance of duties.",
            ANNEX, "Loss-absorption Funds"),
        "authority": spec("jurisdiction_matches entity_covered instrument_covered basis_in_force event_conditions_met procedure_satisfied legal_authority_established",
            [("authority_preconditions", "(and jurisdiction_matches entity_covered instrument_covered basis_in_force event_conditions_met procedure_satisfied legal_authority_established)")],
            "Necessary issuer-power premises, independently supplied for a particular legal basis and edition. No power or jurisdiction is inferred from the issuer's country or capital label.",
            None, None),
        "exercise": spec("authority_preconditions order_issued order_applies_to_instrument order_suspended loss_implemented",
            [("operative_order_under_premises", "(and authority_preconditions order_issued order_applies_to_instrument (not order_suspended))"),
             ("implemented_loss_under_premises", "(and authority_preconditions order_issued order_applies_to_instrument (not order_suspended) loss_implemented)")],
            "Authority, an applicable operative order and implementation are different propositions. Litigation, suspension, finality and repayment are not inferred from an order. These inputs do not replace contractual conversion conditions.",
            None, None),
    }


LINKS = (("scope", "in_scope_product"), ("faq9", "faq9_exception"),
         ("exemption", "bcd_exempt"), ("authority", "authority_preconditions"))


def declarations():
    return {n: t for spec in specifications().values() for n, t in spec["facts"]}


def models():
    return {name: make_model("joined_" + name, spec) for name, spec in specifications().items()}


def contractual_loss(registry, source_id, at, known):
    """Retrieve a bounded event calculation; never infer notice/date satisfaction.

    Contract/event records must distinguish engineering hypotheticals from a
    source-dependent proposal. An absent or invalid record cannot imply no loss.
    """
    if source_id is None:
        return {"status": "UNKNOWN", "reason": "Missing instrument-specific contract/event evidence"}
    check = registry.check([source_id], at, known)
    if check["issues"]:
        return {"status": "UNKNOWN", "issues": check["issues"]}
    record = registry.records[source_id]
    if record["kind"] != "facts" or record["media_type"] != "application/json":
        raise ValueError("Typed contract/event evidence required")
    data = registry.store.json(record["blob"])
    fields(data, {"contract", "event", "event_conditions_satisfied", "premise_kind"})
    fields(data["contract"], {"mechanism", "threshold", "comparison", "viability_trigger", "reduction", "conversion_price"})
    fields(data["event"], {"principal", "capital_ratio", "viability", "restore", "restore_authorized"})
    if data["premise_kind"] not in {"HYPOTHETICAL", "SOURCE_DEPENDENT_PROPOSAL"}:
        raise ValueError("Explicit premise qualification required")
    if data["event_conditions_satisfied"] is not True:
        return {"status": "UNKNOWN", "reason": "Notice, timing and other instrument-specific event conditions not established"}
    values = dict(data["contract"])
    for key in ("threshold", "reduction", "conversion_price"):
        if values[key] is not None:
            values[key] = exact(values[key])
    event = transition(Contract(**values), **data["event"])
    return {"status": "CONDITIONAL", "source": source_id, "blob": record["blob"],
            "premise_kind": data["premise_kind"], "mechanism": values["mechanism"],
            "outcome": {k: v if type(v) is bool else str(v) for k, v in event.items()},
            "market_value": "NOT_COMPUTED", "legal_event_truth": "NOT_ESTABLISHED"}


def calculate(observations):
    """Derived assertions are checked, never allowed to bypass their premises."""
    observed = deepcopy(observations)
    calculations, mm = {}, models()
    for name, output in LINKS:
        result = engine.conditional(mm[name], observed)
        calculations[name] = result
        row, supplied = result[output], observed[output]
        status, value = row["status"], row["value"]
        if supplied["status"] == "CONFLICT" or (status == "KNOWN" and supplied["status"] == "KNOWN" and value != supplied["value"]):
            status, value = "CONFLICT", None
        observed[output] = {"status": status, "type": "bool", "value": value,
            "sources": sorted(set(supplied["sources"]).union(*(observed[f["name"]]["sources"] for f in mm[name]["facts"]))),
            "issues": ["derived from " + name], "truth_of_assertion": "CONDITIONAL_FORMAL_DERIVATION"}
    for name in ("restriction", "duties", "exercise"):
        calculations[name] = engine.conditional(mm[name], observed)
    return calculations, observed


def investigate(request, store):
    """Compose with a freshly computed bank receipt, not a caller's clearance."""
    fields(request, {"profile", "bank_request", "product_assertions_sha256", "issuer_basis_source_ids", "prospectus_source_ids", "contract_event_source_id"})
    if request["profile"] != PROFILE:
        raise ValueError("Unknown joined profile")
    bank_request = request["bank_request"]
    bank = engine.investigate(bank_request, store)
    registry = Registry(store, store.json(bank_request["registry_sha256"]))
    context = bank_request["context"]
    at, known = context["effective_at"], context["known_at"]
    observed = facts(registry, store.json(request["product_assertions_sha256"]), declarations(), at, known)
    # The same client PI proposition appears in the SFC and HKMA specifications.
    # Preserve a conflict across inputs; absence on either side is not evidence.
    pi = bank["observations"]["professional_investor"]
    supplied = observed["professional_investor"]
    if pi["status"] == "CONFLICT" or (pi["status"] == supplied["status"] == "KNOWN" and pi["value"] != supplied["value"]):
        supplied.update(status="CONFLICT", value=None)
    elif supplied["status"] == "UNKNOWN" and pi["status"] == "KNOWN":
        observed["professional_investor"] = deepcopy(pi)
    calculations, observed = calculate(observed)
    references, issues = {}, []
    for key in ("issuer_basis_source_ids", "prospectus_source_ids"):
        ids = request[key]
        if not isinstance(ids, list) or any(not isinstance(x, str) or not x for x in ids) or (not ids and key == "prospectus_source_ids"):
            raise ValueError("Explicit source identifiers and a nonempty prospectus set required")
        references[key] = registry.check(ids, at, known)
        if not ids:
            references[key]["issues"].append("Issuer legal basis not supplied; authority remains unestablished")
        issues.extend(references[key]["issues"])
    for name, spec in specifications().items():
        anchors = []
        for source, quote in spec["anchors"]:
            if source is None:
                continue
            check = registry.check([source], at, known)
            issues.extend(check["issues"])
            try:
                anchors.append(registry.quote(source, quote))
            except (ValueError, KeyError, OSError, UnicodeDecodeError):
                issues.append("missing or changed anchor: " + source)
        references[name] = anchors
    restricted = calculations["restriction"]["pi_restriction_satisfied"]
    result = {"profile": PROFILE, "request_hash": digest(request), "method_hash": engine.method_identity(),
        "bank": bank, "observations": observed, "calculations": calculations, "source_bindings": references,
        "source_issues": sorted(set(issues)), "inventory": bank["inventory"],
        "supplements_obligation": "product.other", "inventory_coverage": "ALL_14_RETAINED",
        "decision": "QUALIFIED", "may_execute_transaction": False,
        "restriction_signal": "CONDITIONAL_RESTRICTION" if restricted["status"] == "KNOWN" and restricted["value"] is False else "NO_CLEARANCE",
        "duties_performed": "NOT_ESTABLISHED", "legal_meaning_and_completeness": "NOT_ESTABLISHED",
        "source_applicability": "UNRESOLVED" if issues else "CONDITIONAL_ON_REGISTERED_INTERVALS",
        "contractual_loss": contractual_loss(registry, request["contract_event_source_id"], at, known),
        "human_quality_evidence": False}
    return {**result, "receipt_hash": digest(result)}


def revalidate(receipt, request, store):
    current = investigate(request, store)
    if current != receipt:
        raise ValueError("Joined evidence or method changed; reassessment required")
    return current
