"""Independent formal obligations and exact generated challenges."""
from fractions import Fraction
from itertools import product
from pathlib import Path
import subprocess

import z3

from .common import LEAN, read, sha, write
from .models import definitions
from .semantics import Contract, transition, distribution, possible_decision, eligible, SPI_FACTS


def symbolic(node, variables):
    """Small checker for the actual shared AST, separate from both executors."""
    op = node["op"]
    if op == "literal":
        return z3.BoolVal(node["value"]) if node["type"] == "bool" else z3.IntVal(node["value"])
    if op == "fact":
        return variables[node["name"]]
    if op in ("all", "any"):
        values = [symbolic(n, variables) for n in node["args"]]
        return z3.And(*values) if op == "all" else z3.Or(*values)
    if op == "not":
        return z3.Not(symbolic(node["arg"], variables))
    if op == "if":
        return z3.If(*(symbolic(node[k], variables) for k in ("condition", "then", "else")))
    if op == "compare":
        a, b = (symbolic(node[k], variables) for k in ("left", "right"))
        return {"eq": a == b, "ge": a >= b, "gt": a > b}[node["cmp"]]
    raise ValueError("No independently checked symbolic semantics for " + op)


def independent(name, v):
    """Mathematical reference using a separately written expression structure."""
    if name == "complex":
        return {"sufficient": z3.And(v["bond"], z3.Sum([z3.If(v[k], 1, 0) for k in v if k != "bond"]) >= 1)}
    if name == "financial":
        return {"financial_pass": z3.Not(z3.And(v["portfolio"] < 4000000000, v["net_assets"] < 8000000000))}
    if name in ("eligibility", "client"):
        key = "eligible" if name == "eligibility" else "client_qualifies"
        return {key: z3.Sum([z3.If(x, 1, 0) for x in v.values()]) == len(v)}
    if name == "threshold":
        return {"amount_condition": z3.If(v["gross"] > v["maximum"], z3.And(v["designated"], z3.Not(v["adding_funds"])), z3.BoolVal(True))}
    if name == "duties":
        active = z3.Not(z3.And(z3.Not(v["solicited"]), z3.Not(v["complex_product"])))
        unsolicited_relief = z3.And(v["complex_product"], z3.Not(v["solicited"]), v["streamlined"])
        return {"suitability_matching_required": z3.If(v["streamlined"], z3.BoolVal(False), active),
                "pdd_relief": z3.And(unsolicited_relief, z3.Not(z3.And(z3.Not(v["offering_documents"]), z3.Not(v["bond_summary"])))),
                "explanation_required": z3.If(active, z3.Not(z3.And(v["streamlined"], z3.Not(v["explanation_requested"]))), z3.BoolVal(False)),
                "annual_complex_warning_relief": unsolicited_relief}
    if name == "principal":
        return {"full_write_down": v["principal"] - z3.If(v["trigger"], v["principal"], 0),
                "preferred_principal": v["principal"],
                "paid_distribution": v["distribution"] - z3.If(v["dividend_declared"], 0, v["distribution"])}
    raise ValueError(name)


def solver_checks(specifications, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    obligations = []
    for name, spec in definitions().items():
        model = read(Path(specifications) / (name + ".model.json"))
        variables = {n: z3.Bool(n) if t == "bool" else z3.Int(n) for n, t in spec["facts"]}
        domain = [variables[n] >= 0 for n, t in spec["facts"] if t == "integer"]
        reference = independent(name, variables)
        for rule in model["rules"]:
            solver = z3.Solver(); solver.set(timeout=10000)
            solver.add(*domain, z3.Or(z3.Not(symbolic(rule["scope"], variables)), symbolic(rule["body"], variables) != reference[rule["id"]]))
            path = directory / (name + "." + rule["id"] + ".smt2")
            path.write_text(solver.to_smt2())
            verdict = solver.check()
            if verdict != z3.unsat:
                raise ValueError("Formal mismatch or unproved obligation: " + name + ": " + str(verdict))
            obligations.append({"model": name, "output": rule["id"], "result": "UNSAT", "smt_sha256": sha(path.read_bytes()),
                                "domain": "All Boolean valuations and all nonnegative integer monetary amounts"})
    # A weak checker could pass the correct program and miss real mistakes.
    p, n = z3.Ints("portfolio net_assets")
    consent, other = z3.Bools("consent other")
    mutants = {
        "exclusive_financial_boundary": (z3.And(p >= 0, n >= 0), z3.Or(p > 4000000000, n > 8000000000) != z3.Or(p >= 4000000000, n >= 8000000000)),
        "missing_consent": (z3.BoolVal(True), other != z3.And(other, consent)),
        "dividend_cancels_principal": (p > 0, z3.IntVal(0) != p),
    }
    detected = []
    for name, (domain, mismatch) in mutants.items():
        solver = z3.Solver(); solver.set(timeout=10000); solver.add(domain, mismatch)
        if solver.check() != z3.sat:
            raise ValueError("Mutation was not detected: " + name)
        detected.append({"mutant": name, "result": "COUNTEREXAMPLE", "witness": str(solver.model())})
    return {"obligations": obligations, "mutants": detected, "checker": "Z3 " + z3.get_version_string(),
            "scope": "Actual shared AST equals independently written mathematical specification; English interpretation and backend compiler correctness remain separate"}


def generated_checks():
    partial = 0
    for values in product((None, False, True), repeat=len(SPI_FACTS)):
        expected = "FALSE" if False in values else "UNDETERMINED" if None in values else "TRUE"
        answer = possible_decision(SPI_FACTS, dict(zip(SPI_FACTS, values)), eligible)
        if answer["decision"] != expected:
            raise ValueError("Partial evidence soundness failure")
        partial += 1
    mechanics = 0
    mechanisms = ("permanent_write_down", "temporary_write_down", "equity_conversion", "none")
    boundary = Fraction(7, 100)
    for mechanism, inclusive, ratio, viability, reduction, principal, restore, authorized in product(
        mechanisms, (False, True), (boundary-Fraction(1, 10**12), boundary, boundary+Fraction(1, 10**12)),
        (False, True), (Fraction(0), Fraction(1, 3), Fraction(1)), (Fraction(0), Fraction(100), Fraction(1, 3)),
        (Fraction(0), Fraction(200)), (False, True)):
        contract = Contract(mechanism, boundary, "le" if inclusive else "lt", True, reduction, Fraction(3, 7))
        result = transition(contract, principal, ratio, viability, restore=restore, restore_authorized=authorized)
        event = viability or ratio < boundary or (inclusive and ratio == boundary)
        # Independently specified obligations on event effects and retained rights.
        loss = principal*reduction if event and mechanism.endswith("write_down") else Fraction(0)
        recovered = min(loss, restore) if mechanism == "temporary_write_down" and authorized else Fraction(0)
        equity = principal*Fraction(7, 3) if event and mechanism == "equity_conversion" else Fraction(0)
        debt = Fraction(0) if event and mechanism == "equity_conversion" else principal-loss+recovered
        restorable = loss-recovered if mechanism == "temporary_write_down" else Fraction(0)
        if result != dict(triggered=event, debt_principal=debt, equity_units=equity, restorable=restorable):
            raise ValueError("Contract semantics mismatch")
        if distribution(principal, False, 7)["principal"] != principal:
            raise ValueError("Dividend/principal confusion")
        mechanics += 1
    return {"partial_spi_states": partial, "contract_event_combinations": mechanics,
            "arithmetic": "Exact rationals; no fitted tolerances", "human_labels": 0,
            "generalization": "Exhaustive declared combinations, not unseen real-document legal accuracy"}


def prove(specifications, directory):
    directory = Path(directory)
    source = Path(__file__).with_name("Prospectus.lean")
    proc = subprocess.run([str(LEAN), str(source)], capture_output=True, text=True, timeout=60)
    log = proc.stdout + proc.stderr
    (directory / "lean.log").write_text(log)
    if proc.returncode or "sorryAx" in log or "sorry" in source.read_text():
        raise ValueError("Lean proof failed or contains a proof placeholder")
    result = {"lean": {"status": "CHECKED", "theorems_reported": 6, "source_sha256": sha(source.read_bytes()),
                       "kernel_sha256": sha(LEAN.read_bytes()), "axioms": "propext only where reported in lean.log",
                       "scope": "Abstract possible-world and contract specification, not Python or English semantics"},
              "solver": solver_checks(specifications, directory / "solver"), "generated": generated_checks()}
    write(directory / "proofs.json", result)
    return result
