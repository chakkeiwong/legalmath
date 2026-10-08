from copy import deepcopy

import pytest

from legalmath.prospectus import eligibility as e
from legalmath.prospectus.eligibility_checks import prove
from legalmath.transaction.evidence import Registry, Store
from legalmath.transaction.intake import record


def observations(**values):
    return {k: {"type": "bool", "status": "UNKNOWN" if k not in values else "KNOWN",
                "value": values.get(k), "sources": [], "issues": []}
            for k in e.declarations()}


def test_full_boolean_equations_and_omitted_exception_conditions(tmp_path):
    result = prove(tmp_path)
    assert len(result["obligations"]) == 11
    assert len(result["detected_mutations"]) == 21


def test_preferred_and_bail_in_do_not_imply_direct_debt_scope():
    calc, _ = e.calculate(observations(debt_legal_form=False, qualifying_wrapper=False))
    assert calc["scope"]["in_scope_product"]["value"] is False
    calc, _ = e.calculate(observations(debt_legal_form=True, qualifying_contingent_loss_absorption=False, qualifying_wrapper=False))
    assert calc["scope"]["in_scope_product"]["value"] is False


def test_spi_cannot_override_pi_restriction_and_asserted_exception():
    calc, _ = e.calculate(observations(debt_legal_form=True, qualifying_contingent_loss_absorption=True,
        plain_debt_or_deposit=False, registered_institution=True, professional_investor=False,
        direct_customer_request=True, faq9_exception=True))
    assert calc["restriction"]["pi_restriction_satisfied"]["status"] == "CONFLICT"
    calc, _ = e.calculate(observations(debt_legal_form=True, qualifying_contingent_loss_absorption=True,
        plain_debt_or_deposit=False, registered_institution=True, professional_investor=False, direct_customer_request=True))
    assert calc["restriction"]["pi_restriction_satisfied"]["value"] is False


def test_fund_retains_rating_and_dpm_does_not_remove_duties():
    v = dict(debt_legal_form=False, qualifying_wrapper=True, registered_institution=True,
             direct_customer_request=True, institutional_pi=False, corporate_pi=False,
             loss_absorption_fund=True, discretionary_portfolio_management=True)
    c, _ = e.calculate(observations(**v))
    assert c["duties"]["risk_rating_required"]["value"] is True
    assert c["duties"]["enhanced_disclosure_required"]["value"] is False
    assert c["duties"]["portfolio_mode_available"]["value"] is True
    v["loss_absorption_fund"] = False
    c, _ = e.calculate(observations(**v))
    assert c["duties"]["enhanced_suitability_required"]["value"] is True


def test_wrong_jurisdiction_prevents_exercise_even_with_asserted_order():
    c, _ = e.calculate(observations(jurisdiction_matches=False, order_issued=True, loss_implemented=True))
    assert c["exercise"]["operative_order_under_premises"]["value"] is False
    assert c["exercise"]["implemented_loss_under_premises"]["value"] is False


def test_unknown_faq_condition_cannot_be_replaced_by_asserted_exception():
    values = {k: k not in {"circumvention", "direct_customer_request"} for k, _ in e.specifications()["faq9"]["facts"]}
    values.pop("written_responsibility_agreement")
    values["faq9_exception"] = True
    c, obs = e.calculate(observations(**values))
    assert obs["faq9_exception"]["status"] == "UNKNOWN"


def test_conversion_does_not_mean_total_value_zero_or_actual_notice(tmp_path):
    store = Store(tmp_path / "store")
    data = {"contract": {"mechanism": "equity_conversion", "threshold": "7/100", "comparison": "lt",
        "viability_trigger": True, "reduction": "1", "conversion_price": "3777/100"},
        "event": {"principal": "3777", "capital_ratio": "6/100", "viability": False, "restore": "0", "restore_authorized": False},
        "event_conditions_satisfied": True, "premise_kind": "HYPOTHETICAL"}
    def registry(data):
        return Registry(store, {"event": record(store.put(data), "facts", "synthetic:event", "2026-01-01T00:00:00Z",
            media_type="application/json", provenance="synthetic", effective_from="2026-01-01T00:00:00Z", fresh_until="2027-01-01T00:00:00Z")})
    at = "2026-09-29T00:00:00Z"
    r = e.contractual_loss(registry(data), "event", at, at)
    assert r["outcome"]["debt_principal"] == "0" and r["outcome"]["equity_units"] == "100"
    assert r["market_value"] == "NOT_COMPUTED"
    data["event_conditions_satisfied"] = None
    assert e.contractual_loss(registry(data), "event", at, at)["status"] == "UNKNOWN"


def test_joined_receipt_recomputes_and_retains_all_bank_obligations(tmp_path):
    # Use the existing bank harness only for evidence setup; not an answer oracle.
    import runpy
    from pathlib import Path
    bank_fixture = runpy.run_path(str(Path(__file__).parents[1] / "compliance/test_transaction.py"))["fixture"]
    store, bank_request = bank_fixture(tmp_path)
    records = store.json(bank_request["registry_sha256"])
    for spec in e.specifications().values():
        for source, quote in spec["anchors"]:
            if source is None:
                continue
            old = store.get(records[source]["blob"]).decode() if source in records else ""
            records[source] = record(store.put((old + quote + "\n").encode()), "law", "synthetic:" + source,
                "2026-01-01T00:00:00Z", provenance="synthetic", effective_from="2026-01-01T00:00:00Z", fresh_until="2027-01-01T00:00:00Z")
    bank_request["registry_sha256"] = store.put(records)
    request = {"profile": e.PROFILE, "bank_request": bank_request,
               "product_assertions_sha256": store.put({}), "issuer_basis_source_ids": [e.ANNEX],
               "prospectus_source_ids": [e.FAQ], "contract_event_source_id": None}
    receipt = e.investigate(request, store)
    assert len(receipt["inventory"]) == 14 and not receipt["may_execute_transaction"]
    assert receipt["bank"]["formal_assessment"]["unresolved"]
    assert e.revalidate(receipt, request, store) == receipt
    for field in ("facts_sha256", "policy_sha256", "route_sha256"):
        mutated = deepcopy(request)
        value = store.json(mutated["bank_request"]["context"][field])
        if field == "facts_sha256": value.pop(next(iter(value)))
        elif field == "policy_sha256": value["source_ids"].append(e.ANNEX)
        else: value["currencies"].append("SGD")
        mutated["bank_request"]["context"][field] = store.put(value)
        with pytest.raises(ValueError, match="changed"):
            e.revalidate(receipt, mutated, store)
    corrupted = deepcopy(receipt)
    corrupted["may_execute_transaction"] = True
    with pytest.raises(ValueError, match="changed"):
        e.revalidate(corrupted, request, store)
