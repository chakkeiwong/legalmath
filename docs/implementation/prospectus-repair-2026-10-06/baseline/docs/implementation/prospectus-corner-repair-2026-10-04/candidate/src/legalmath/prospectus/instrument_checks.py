"""Independent mathematical obligations and native inputs for the declared terms."""
from copy import deepcopy
from itertools import product
from pathlib import Path

import z3

from .common import write, sha
from .models import make_model, AT
from . import eligibility


def specifications():
    return {
        "capital": {"facts": [(n, "integer") for n in ("cet1", "higher_amount", "rwa")],
            "outputs": [("breach", "bool", "(> (scale rwa 7 1) (scale (+ cet1 higher_amount) 100 1))")],
            "meaning": "Conditional Annex A strict seven-percent ratio. Nonnegative capital amounts in the same unit; risk-weighted assets strictly positive; published higher-trigger amount added before comparison."},
        "restoration": {"facts": [(n, "bool") for n in ("ordinary", "requested", "written", "restored", "above_threshold", "adequate", "prior_to_both")],
            "outputs": [("exception", "bool", "(and ordinary requested written restored above_threshold adequate prior_to_both)")],
            "meaning": "Declared Condition 7(b)(iii) necessary exception predicates. Each act/timing assertion remains a factual premise; same-day ordering cannot be assumed."},
        "schedule": {"facts": [(n, "date") for n in ("notice_date", "conversion_date", "deadline")],
            "outputs": [("in_interval", "bool", "(and (> conversion_date notice_date) (>= deadline conversion_date))")],
            "meaning": "Conditional notice/creation/conversion interval. The deadline is independently computed using the declared event anchor and evidenced business calendar."},
        "scope": eligibility.specifications()["scope"],
        "restriction": eligibility.specifications()["restriction"],
    }


def reference(name, v):
    if name == "capital":
        return {"breach": z3.ToReal(v["cet1"] + v["higher_amount"])/z3.ToReal(v["rwa"]) < z3.RealVal("7/100")}
    if name == "restoration":
        return {"exception": z3.Sum([z3.If(x, 0, 1) for x in v.values()]) == 0}
    if name == "schedule":
        return {"in_interval": z3.Not(z3.Or(v["conversion_date"] <= v["notice_date"], v["conversion_date"] > v["deadline"]))}
    from .eligibility_checks import reference as hkma
    return hkma(name, v)


def ast(node, v):
    op = node["op"]
    if op == "literal":
        return z3.BoolVal(node["value"]) if node["type"] == "bool" else z3.IntVal(node["value"])
    if op == "fact":
        return v[node["name"]]
    if op in {"all", "any"}:
        return (z3.And if op == "all" else z3.Or)(*[ast(n, v) for n in node["args"]])
    if op == "not":
        return z3.Not(ast(node["arg"], v))
    if op in {"add", "sub", "compare"}:
        a, b = ast(node["left"], v), ast(node["right"], v)
        if op == "add": return a+b
        if op == "sub": return a-b
        return {"eq": a == b, "ge": a >= b, "gt": a > b}[node["cmp"]]
    if op == "scale" and node["denominator"] == "1":
        return ast(node["arg"], v)*int(node["numerator"])
    raise ValueError("No independent semantics for " + op)


def prove(directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    obligations, mutants = [], []
    for name, spec in specifications().items():
        model = make_model("ubs_" + name, spec)
        variables = {n: z3.Bool(n) if t == "bool" else z3.Int(n) for n, t in spec["facts"]}
        domain = [variables[n] >= 0 for n, t in spec["facts"] if t != "bool"]
        if name == "capital": domain.append(variables["rwa"] > 0)
        target = reference(name, variables)
        for rule in model["rules"]:
            equation = ast(rule["body"], variables)
            solver = z3.Solver(); solver.set(timeout=10000)
            solver.add(*domain, equation != target[rule["id"]])
            path = directory/(name + ".smt2"); path.write_text(solver.to_smt2())
            if solver.check() != z3.unsat:
                raise ValueError("Unproved independent equation: " + name)
            obligations.append({"model": name, "result": "UNSAT", "sha256": sha(path.read_bytes())})
            solver = z3.Solver(); solver.add(*domain, z3.Not(equation) != target[rule["id"]])
            if solver.check() != z3.sat: raise ValueError("Inverted output escaped")
            mutants.append({"model": name, "mutation": "inverted_output", "counterexample": str(solver.model())})
        if name == "capital":
            c, h, r = (variables[n] for n in ("cet1", "higher_amount", "rwa"))
            for label, mutant in {"inclusive_threshold": 100*(c+h) <= 7*r, "omitted_higher_capital": 100*c < 7*r}.items():
                solver = z3.Solver(); solver.add(*domain, mutant != target["breach"])
                if solver.check() != z3.sat: raise ValueError("Capital mutant escaped")
                mutants.append({"model": name, "mutation": label, "counterexample": str(solver.model())})
    result = {"obligations": obligations, "mutants": mutants, "solver": z3.get_version_string(),
        "scope": "All valuations in the specified Boolean, positive-RWA integer and date-order domains",
        "legal_entailment": "NOT_ESTABLISHED", "human_quality_evidence": False}
    write(directory/"result.json", result)
    return result


def inputs(name, spec):
    if name == "capital":
        values = [dict(cet1=c, higher_amount=h, rwa=r) for c,h,r in
            [(0,0,1), (6,0,100), (7,0,100), (8,0,100), (6,1,100), (6,2,100),
             (699,0,10000), (700,0,10000), (701,0,10000), (10**20,10**20,10**23)]]
    elif name == "schedule":
        values = [dict(notice_date="2026-09-07", conversion_date=d, deadline="2026-10-05")
            for d in ["2026-09-06", "2026-09-07", "2026-09-08", "2026-10-05", "2026-10-06"]]
    else:
        # Exhaust all valuations in the small Boolean profiles (largest: 128).
        names = [n for n,_ in spec["facts"]]
        values = [dict(zip(names, row)) for row in product((False, True), repeat=len(names))]
    cases = []
    for i, value in enumerate(values):
        evidence = {"/"+n: ["declared-hypothesis:"+name+":"+str(i)+":"+n] for n,_ in spec["facts"]}
        facts = {n: {"type": t, "status": "known", "value": value[n] if t == "bool" else str(value[n]),
            "evidence_ids": evidence["/"+n], "complete": True, "valid_from": AT, "valid_until": None, "recorded_at": AT}
            for n,t in spec["facts"]}
        cases.append({"id": name+"."+str(i), "snapshot": {"subject_id": "hypothetical-ubs", "evidence": evidence, "facts": facts},
            "valid_at": AT, "known_at": AT})
    for status in ("unknown", "conflict"):
        case = deepcopy(cases[0]); case["id"] += "."+status
        n,t = spec["facts"][0]
        case["snapshot"]["facts"][n] = {"type": t, "status": status, **({"reason": "MISSING"} if status == "unknown" else {"evidence_ids": ["x","y"]})}
        if status == "conflict": case["snapshot"]["evidence"]["/"+n] = ["x","y"]
        cases.append(case)
    return cases
