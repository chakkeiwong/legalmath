"""Independent Boolean consequences; no interpretation-quality answer labels."""
from pathlib import Path

import z3

from ..transaction.evidence import sha
from .checks import symbolic
from .eligibility import models


def reference(name, v):
    def all_of(*names):
        return z3.Sum([z3.If(v[k], 1, 0) for k in names]) == len(names)
    if name == "scope":
        direct = z3.If(v["debt_legal_form"], z3.If(v["plain_debt_or_deposit"], False, v["qualifying_contingent_loss_absorption"]), False)
        return {"in_scope_product": z3.If(v["qualifying_wrapper"], True, direct)}
    if name == "faq9":
        disqualifies = z3.Or(v["direct_customer_request"], v["circumvention"])
        count = z3.Sum([z3.If(value, 1, 0) for key, value in v.items() if key not in {"direct_customer_request", "circumvention"}])
        return {"faq9_exception": z3.If(disqualifies, False, count == 8)}
    if name == "restriction":
        forbidden = all_of("registered_institution", "in_scope_product")
        return {"pi_restriction_satisfied": z3.Not(z3.And(forbidden, z3.Not(v["faq9_exception"]), z3.Not(v["professional_investor"])))}
    if name == "exemption":
        corp = all_of("corporate_pi", "paragraph_15_3a_complied", "paragraph_15_3b_complied")
        return {"bcd_exempt": z3.If(v["institutional_pi"], True, corp)}
    if name == "duties":
        applicable = z3.If(v["registered_institution"], v["in_scope_product"], False)
        applies = z3.If(v["faq9_exception"], False, applicable)
        base = z3.If(v["bcd_exempt"], False, applies)
        enhanced = z3.If(v["loss_absorption_fund"], False, base)
        return {"risk_rating_required": base, "enhanced_suitability_required": enhanced,
                "enhanced_disclosure_required": enhanced,
                "portfolio_mode_available": z3.If(v["discretionary_portfolio_management"], applies, False)}
    if name == "authority":
        return {"authority_preconditions": z3.Sum([z3.If(x, 0, 1) for x in v.values()]) == 0}
    if name == "exercise":
        operative = z3.If(v["order_suspended"], False, all_of("authority_preconditions", "order_issued", "order_applies_to_instrument"))
        return {"operative_order_under_premises": operative,
                "implemented_loss_under_premises": z3.If(v["loss_implemented"], operative, False)}
    raise ValueError(name)


def prove(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    obligations, mutations = [], []
    for name, model in models().items():
        variables = {f["name"]: z3.Bool(f["name"]) for f in model["facts"]}
        expected = reference(name, variables)
        for rule in model["rules"]:
            actual = symbolic(rule["body"], variables)
            solver = z3.Solver()
            solver.set(timeout=10000)
            solver.add(actual != expected[rule["id"]])
            path = directory / (name + "." + rule["id"] + ".smt2")
            path.write_text(solver.to_smt2())
            if solver.check() != z3.unsat:
                raise ValueError("Conditional equation differs: " + name)
            obligations.append({"model": name, "rule": rule["id"], "result": "UNSAT", "sha256": sha(path.read_bytes())})
            # An inverted output is a basic corruption probe for every relation.
            solver = z3.Solver()
            solver.add(z3.Not(actual) != expected[rule["id"]])
            if solver.check() != z3.sat:
                raise ValueError("Mutation escaped: " + name)
            mutations.append({"model": name, "rule": rule["id"], "mutation": "invert_output", "witness": str(solver.model())})
        if name == "faq9":
            for key in variables:
                mutant = z3.substitute(expected["faq9_exception"], (variables[key], z3.BoolVal(key not in {"direct_customer_request", "circumvention"})))
                solver = z3.Solver()
                solver.add(mutant != expected["faq9_exception"])
                if solver.check() != z3.sat:
                    raise ValueError("Omitted FAQ condition escaped: " + key)
                mutations.append({"model": name, "mutation": "omit_" + key, "witness": str(solver.model())})
    return {"domain": "All Boolean valuations of the declared conditional specifications",
            "solver": z3.get_version_string(), "obligations": obligations, "detected_mutations": mutations,
            "legal_entailment": "NOT_ESTABLISHED", "human_quality_evidence": False}
