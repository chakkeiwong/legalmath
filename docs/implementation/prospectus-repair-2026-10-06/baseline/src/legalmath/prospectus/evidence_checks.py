"""Independent arithmetic and native preservation checks for the new branches."""
from copy import deepcopy
from itertools import product
from pathlib import Path
import re
import subprocess

import z3

from .common import write, sha
from .models import make_model, AT
from .instrument_checks import ast


def specifications():
    return {
        "notice_window": {"facts": [("days_elapsed","integer")],
            "outputs": [("within_window","bool","(and (>= days_elapsed (integer 30)) (>= (integer 60) days_elapsed))")],
            "meaning":"Series SS selected notice interval: 30 through 60 calendar days, both endpoints included; an elapsed-day input does not prove a notice occurred."},
        "capital_window": {"facts": [("days_elapsed","integer"),("full_redemption","bool"),("capital_event","bool")],
            "outputs": [("within_window","bool","(and capital_event full_redemption (>= (integer 90) days_elapsed))")],
            "meaning":"Controlling certificate's selected special redemption window, given nonnegative elapsed days since an actual Capital Treatment Event. Notice and approvals checked separately."},
        "declaration": {"facts": [("declared","bool"),("lawful_funds","bool")],
            "outputs": [("declared_and_funded","bool","(and declared lawful_funds)")],
            "meaning":"Necessary declared-dividend premises only; no future arrears or actual payment inferred."},
        "redemption_acts": {"facts": [(n,"bool") for n in ("issuer_elected","funds_available","regulator_approval","notice_complete")],
            "outputs": [("acts_supplied","bool","(and issuer_elected funds_available regulator_approval notice_complete)")],
            "meaning":"Necessary selected factual acts; timing, amount, scope and effectiveness remain separate."}}


def valuations(name):
    if name == "notice_window": return [{"days_elapsed":n} for n in (0,1,29,30,31,59,60,61,90,1000000)]
    if name == "capital_window": return [dict(days_elapsed=n,full_redemption=f,capital_event=e) for n in (0,1,89,90,91,1000000) for f,e in product((False,True),repeat=2)]
    names=[n for n,_ in specifications()[name]["facts"]]
    return [dict(zip(names,values)) for values in product((False,True),repeat=len(names))]


def cases(name):
    spec=specifications()[name]; result=[]
    for i,values in enumerate(valuations(name)):
        evidence={"/"+n:[f"hypothesis:{name}:{i}:{n}"] for n,_ in spec["facts"]}
        facts={n:{"type":t,"status":"known","value":values[n] if t=="bool" else str(values[n]),
            "evidence_ids":evidence["/"+n],"complete":True,"valid_from":AT,"valid_until":None,"recorded_at":AT} for n,t in spec["facts"]}
        result.append({"id":f"{name}.{i}","snapshot":{"subject_id":"hypothetical-series-ss","evidence":evidence,"facts":facts},"valid_at":AT,"known_at":AT})
    for status in ("unknown","conflict"):
        row=deepcopy(result[0]);row["id"]+="."+status
        n,t=spec["facts"][0]
        row["snapshot"]["facts"][n]={"type":t,"status":status,**({"reason":"MISSING"} if status=="unknown" else {"evidence_ids":["a","b"]})}
        if status=="conflict":row["snapshot"]["evidence"]["/"+n]=["a","b"]
        result.append(row)
    return result


def prove(directory, lean):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    prelude=Path(__file__).with_name("InstrumentArithmetic.lean")
    copied=directory/prelude.name;copied.write_bytes(prelude.read_bytes())
    run=subprocess.run([str(lean),str(copied.resolve())],capture_output=True,text=True,timeout=60)
    log=run.stdout+run.stderr;(directory/"lean.log").write_text(log)
    dependencies=re.findall(r"'LegalMathInstrument\.([a-z_]+)' depends on axioms: \[([^\]]*)\]",log)
    expected={"floor_bounds","half_up_bounds","half_up_tie","deadline_minimal","deadline_unique"}
    axioms={x.strip() for _,names in dependencies for x in names.split(',') if x.strip()}
    if run.returncode or "sorry" in log or {n for n,_ in dependencies}!=expected or not axioms <= {"propext","Quot.sound","Classical.choice"}:
        raise ValueError("Arithmetic theorem/axiom check failed")
    obligations=[]; mutants=[]
    for name,spec in specifications().items():
        v={n:z3.Bool(n) if t=="bool" else z3.Int(n) for n,t in spec["facts"]}
        domain=[v[n]>=0 for n,t in spec["facts"] if t=="integer"]
        if name=="notice_window": reference=z3.Not(z3.Or(v["days_elapsed"]<30,v["days_elapsed"]>60))
        elif name=="capital_window": reference=z3.If(v["days_elapsed"]>90,z3.BoolVal(False),z3.And(v["full_redemption"],v["capital_event"]))
        else: reference=z3.Sum([z3.If(x,1,0) for x in v.values()])==len(v)
        equation=ast(make_model("ss_"+name,spec)["rules"][0]["body"],v)
        solver=z3.Solver();solver.set(timeout=10000);solver.add(*domain,equation!=reference)
        smt=directory/(name+".smt2");smt.write_text(solver.to_smt2())
        if solver.check()!=z3.unsat:raise ValueError("Independent relation failed: "+name)
        obligations.append({"model":name,"status":"UNSAT","sha256":sha(smt.read_bytes())})
        candidates={"inverted_output":z3.Not(equation)}
        if name=="notice_window":
            candidates.update(excludes_30=z3.And(v["days_elapsed"]>30,v["days_elapsed"]<=60),excludes_60=z3.And(v["days_elapsed"]>=30,v["days_elapsed"]<60))
        if name=="capital_window": candidates["notice_date_instead_of_redemption_date"]=z3.And(v["capital_event"],v["full_redemption"],v["days_elapsed"]<=150)
        for mutation,candidate in candidates.items():
            solver=z3.Solver();solver.add(*domain,candidate!=reference)
            if solver.check()!=z3.sat:raise ValueError("Mutant escaped: "+mutation)
            mutants.append({"model":name,"mutation":mutation,"counterexample":str(solver.model())})
    result={"lean":{"status":"KERNEL_CHECKED","theorems":sorted(expected),"axioms":sorted(axioms),
        "prelude_sha256":sha(prelude.read_bytes()),"tool_sha256":sha(Path(lean).read_bytes()),
        "scope":"Nonnegative rational floor/half-up arithmetic and cumulative-open-day deadline characterization; not a proof of Python, actual calendars or contract meaning"},
        "independent_relations":obligations,"mutants":mutants,"solver":z3.get_version_string(),"human_quality_evidence":False}
    write(directory/"result.json",result)
    return result
