"""Independent representation of the declared interpretation; no RuleIR imports.

For the body, enumerate possible Boolean completions of missing classifications.
Every variable occurs once in this formula, with a single polarity, so its T/F/U
outcomes agree with the stated strong-Kleene operations. Scope is explicitly a
separate prerequisite and uses the specified OUT_OF_SCOPE/UNKNOWN convention.
This checks the encoding; a second human reader must still adjudicate meaning.
"""
from itertools import product


def expected_status(values):
    scope_values = [values["is_distributor"], values["promotes_sfc_authorised_fund"]]
    if "F" in scope_values: return "OUT_OF_SCOPE"
    if "U" in scope_values: return "UNKNOWN"
    keys = ("gift_offered", "specific_product_promotion", "particular_product_type_promotion", "fee_discount_only")
    possibilities = {"T": (True,), "F": (False,), "U": (False, True)}
    outcomes = set()
    for gift, specific, kind, discount in product(*(possibilities[values[k]] for k in keys)):
        # The candidate AST and evaluator are deliberately absent from this oracle.
        outcomes.add(gift and (specific or kind) and not discount)
    if outcomes == {True}: return "TRUE"
    if outcomes == {False}: return "FALSE"
    return "UNKNOWN"
