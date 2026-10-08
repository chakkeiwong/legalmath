"""Bank adapter preserves the actual inventory; feature answers grant no clearance."""
from copy import deepcopy
from .contracts import QueryResult, digest
from .anchors import bind, fields
from .. import eligibility
from ...transaction.catalog import inventory


def context_identity(bundle):
    return {k: bundle[k] for k in ("instrument_id", "purpose", "issue_date", "effective_at", "known_at")}


def investigate(bundle, bank, graph=None):
    request = deepcopy(bank["request"])
    context = request["bank_request"]["context"]
    if context["instrument_id"] != bundle["instrument_id"]:
        raise ValueError("Bank request identifies a different instrument")
    admission = bank.get("context_admission")
    fields(admission, {"bundle_context_sha256", "bank_context_sha256", "instrument_kind", "reason", "sources"},
           {"bundle_context_sha256", "bank_context_sha256", "instrument_kind", "reason", "sources"})
    if admission["bundle_context_sha256"] != digest(context_identity(bundle)) or admission["bank_context_sha256"] != digest(context):
        raise ValueError("Bank question context mapping is stale")
    if admission["instrument_kind"] != context["instrument_kind"] or not admission["reason"] or not admission["sources"]:
        raise ValueError("Explicit source-bound instrument kind and date/purpose mapping required")
    sources = [bind(graph, source) for source in admission["sources"]]
    result = eligibility.investigate(request, bank["store"])
    eligibility.revalidate(result, request, bank["store"])
    expected = inventory(request["bank_request"]["profile"])
    if result["inventory"] != expected or result["may_execute_transaction"]:
        raise ValueError("Bank obligation loss or unintended clearance")
    return QueryResult("Q6", "CONDITIONAL", value={"inventory": result["inventory"],
        "context_mapping": admission, "context_sources": sources, "inventory_sha256": digest(expected),
        "bank_receipt": result, "feature_to_regulatory_scope": "NO_AUTOMATIC_IMPLICATION",
        "may_execute_transaction": False}).json()
