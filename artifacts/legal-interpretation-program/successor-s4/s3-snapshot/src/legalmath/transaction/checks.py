"""Independent equations and generated challenges, without legal answer labels."""
from pathlib import Path

import z3

from ..canonical import canonical
from ..prospectus.checks import symbolic, independent as product_reference
from ..prospectus.models import AT
from .catalog import specifications, models
from .evidence import sha


def reference(name, v):
    if name.startswith("product_"):
        answer = product_reference(name.removeprefix("product_"), v)
        if name == "product_threshold":
            answer["threshold_compliant"] = z3.If(v["threshold_controls_established"], answer["amount_condition"], z3.BoolVal(False))
        return answer
    if name == "entity":
        return {"us_entity": z3.Sum([z3.If(x, 1, 0) for x in v.values()]) > 0}
    if name == "cmic":
        nexus = z3.If(v["principal_capacity"], z3.Or(v["actor_us_person"], v["ultimate_party_us_person"]), v["ultimate_party_us_person"])
        restriction = z3.Not(z3.Or(z3.Not(v["transaction_purchase_or_sale"]), z3.Not(v["designated_issuer"]),
                                  z3.Not(v["covered_security"]), z3.Not(v["restriction_in_force"]), z3.Not(nexus)))
        exempt = z3.If(v["applicable_ofac_authorization"], z3.BoolVal(True),
                       z3.If(v["divestment_window_open"], v["solely_divestment"], z3.BoolVal(False)))
        return {"satisfied": z3.If(v["otherwise_permissible"], z3.If(restriction, exempt, z3.BoolVal(True)), z3.BoolVal(False))}
    if name == "bsa_program":
        required = [x for k, x in v.items() if k not in {"national_bank", "covered_savings_association"}]
        return {"applies": z3.Not(z3.And(z3.Not(v["national_bank"]), z3.Not(v["covered_savings_association"]))),
                "satisfied": z3.Sum([z3.If(x, 1, 0) for x in required]) == 8}
    if name == "private_account":
        geographic = [v[k] for k in ("established_us", "maintained_us", "administered_us", "managed_us")]
        outside = z3.Or(z3.Not(v["covered_institution"]), v["required_minimum_usd_cents"] < 100000000,
                        z3.Not(v["non_us_owner"]), z3.Not(v["liaison"]),
                        z3.Sum([z3.If(x, 1, 0) for x in geographic]) == 0)
        failures = [z3.Not(v[k]) for k in ("owner_identity", "political_figure_screen", "funds_and_purpose",
                                          "activity_review_and_reporting", "failure_procedures")]
        failures.append(z3.And(v["senior_foreign_political_figure"], z3.Not(v["enhanced_scrutiny"])))
        return {"applies": z3.Not(outside), "satisfied": z3.Not(z3.Or(*failures))}
    if name == "cmic_reporting":
        return {"applies": z3.If(v["us_financial_institution"], v["attempted_cmic_prohibited_transaction"], z3.BoolVal(False)),
                "satisfied": z3.Sum([z3.If(v[k], 1, 0) for k in ("transaction_rejected", "rejection_reported_in_time")]) == 2}
    raise ValueError("No independent specification for " + name)


def prove_equations(directory):
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    obligations, mutants = [], []
    for name, model in models().items():
        variables = {f["name"]: z3.Bool(f["name"]) if f["type"] == "bool" else z3.Int(f["name"])
                     for f in model["facts"]}
        domain = [variables[f["name"]] >= 0 for f in model["facts"] if f["type"] == "integer"]
        targets = reference(name, variables)
        for rule in model["rules"]:
            actual = symbolic(rule["body"], variables)
            solver = z3.Solver()
            solver.set(timeout=10000)
            solver.add(*domain, z3.Or(z3.Not(symbolic(rule["scope"], variables)), actual != targets[rule["id"]]))
            path = out / (name + "." + rule["id"] + ".smt2")
            path.write_text(solver.to_smt2())
            if solver.check() != z3.unsat:
                raise ValueError("Unproved formal specification: " + name)
            obligations.append({"model": name, "output": rule["id"], "result": "UNSAT", "sha256": sha(path.read_bytes())})
        if name == "private_account":
            mutant = z3.And(variables["covered_institution"], variables["required_minimum_usd_cents"] > 100000000,
                           variables["non_us_owner"], variables["liaison"], variables["established_us"])
            solver = z3.Solver(); solver.add(*domain, variables["required_minimum_usd_cents"] == 100000000,
                                           mutant != targets["applies"])
            if solver.check() != z3.sat:
                raise ValueError("Threshold mutation escaped the independent check")
            mutants.append({"name": "exclusive_threshold_and_missing_territorial_alternatives", "witness": str(solver.model())})
        if name == "cmic":
            for description, mutation in (("omit_other_permissibility", z3.BoolVal(True)),
                ("ignore_ultimate_party", z3.substitute(targets["satisfied"], (variables["ultimate_party_us_person"], z3.BoolVal(False))))):
                solver = z3.Solver(); solver.add(mutation != targets["satisfied"])
                if solver.check() != z3.sat:
                    raise ValueError("CMIC mutation escaped the independent check")
                mutants.append({"name": description, "witness": str(solver.model())})
    return {"obligations": obligations, "detected_mutations": mutants,
            "domain": "All Boolean values and nonnegative integer amounts for the declared formal specifications",
            "solver": z3.get_version_string(), "natural_language_entailment": "NOT_ESTABLISHED"}


def cases(name):
    d = specifications()[name]
    # The cases are inputs only. A separately implemented interpreter computes
    # reference results, and SMT covers the full declared mathematical domain.
    low = {k: False if t == "bool" else 0 for k, t in d["facts"]}
    high = {k: True if t == "bool" else 10000000000 for k, t in d["facts"]}
    if name == "product_threshold":
        high.update(gross=100, maximum=100)
    values = [low, high]
    for key, typ in d["facts"]:
        if typ == "bool":
            values.extend([{**high, key: False}, {**low, key: True}])
        else:
            boundaries = {"required_minimum_usd_cents": 100000000, "portfolio": 4000000000,
                          "net_assets": 8000000000, "gross": 100, "maximum": 100}
            boundary = boundaries.get(key, 0)
            for amount in (max(0, boundary - 1), boundary, boundary + 1):
                base = dict(high)
                if name == "product_financial":
                    base.update(portfolio=0, net_assets=0)
                values.append({**base, key: amount})
    unique = {canonical(v): v for v in values}
    rows = []
    for i, value in enumerate(unique.values()):
        evidence = {"/" + k: ["generated:bank:" + name + ":" + str(i) + ":" + k] for k in value}
        rows.append({"id": name + "." + str(i), "valid_at": AT, "known_at": AT,
            "snapshot": {"subject_id": "synthetic-bank-transaction", "evidence": evidence, "facts": {
                k: {"status": "known", "type": t, "value": value[k] if t == "bool" else str(value[k]),
                    "evidence_ids": evidence["/" + k], "complete": True, "valid_from": AT,
                    "valid_until": None, "recorded_at": AT} for k, t in d["facts"]}}})
    return rows
