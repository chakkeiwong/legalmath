"""Bank adapter preserves the actual inventory; feature answers grant no clearance."""
from copy import deepcopy
from .contracts import QueryResult
from .. import eligibility


def investigate(bundle, bank):
    request = deepcopy(bank["request"])
    if request["bank_request"]["context"]["instrument_id"] != bundle["instrument_id"]:
        raise ValueError("Bank request identifies a different instrument")
    result = eligibility.investigate(request, bank["store"])
    eligibility.revalidate(result, request, bank["store"])
    if len(result["inventory"]) != 14 or result["may_execute_transaction"]:
        raise ValueError("Bank obligation loss or unintended clearance")
    return QueryResult("Q6", "CONDITIONAL", value={"inventory": result["inventory"],
        "bank_receipt": result, "feature_to_regulatory_scope": "NO_AUTOMATIC_IMPLICATION",
        "may_execute_transaction": False}).json()
