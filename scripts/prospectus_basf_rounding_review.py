"""Bounded source-specific BASF rounding discrimination; no package promotion."""
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
import gzip
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/"src"),str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1",PYTHONDONTWRITEBYTECODE="1",PYTHONNOUSERSITE="1",PYTHONPATH="")
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read
from scripts.prospectus_basf_pension_source import files,load,require
from scripts.prospectus_installed_profile_worker import execution_guard
from scripts import prospectus_basf_pension_install as installed

BASE=ROOT/"docs/implementation/prospectus-execution-authority"
HERE=BASE/"attempts/basf-references/attempt-007"
PRIOR=HERE.parent/"attempt-005"
REVIEW=BASE/"reviews/basf-rounding-173"
PLAN="docs/plans/prospectus-basf-rounding-discrimination-2026-10-16.md"
DOCUMENT="basf-annual-2022-exchange"
STAGES=("prepare","analyze","seal")
SELECTOR={"version":"basf-rounding-discrimination.v1","stages":list(STAGES),
    "stage_seconds":60,"new_seconds":180,"cumulative005_007_seconds":900,
    "new_bytes":15*1024**2,"cumulative005_007_bytes":500*1024**2,
    "source_pages":[204,209,256,264],"new_render_pages":[209],"child_seconds":25,
    "extraction_OCR_network_model_GPU_install_production_edit_retry":0}


def save(name,value):
    p=HERE/name
    p.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()
    with p.open("xb") as stream: stream.write(gzip.compress(raw,mtime=0) if p.suffix==".gz" else raw+b"\n")


def storage():
    new=sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file())
    return {"new_bytes":new,"combined_bytes":installed.storage()+new,
            "previous_seconds":read(installed.HERE/"result.json")["cumulative_seconds"]}


def bindings():
    a=Authority(ROOT)
    program,tasks,_=a.spec()
    task=tasks["basf-references"]
    admitted=read(HERE/"admission.json")
    event=next(e for e in reversed(a.events()) if e.get("task")==task["id"])
    require(event["kind"]=="ADMIT" and event["attempt"]==str(HERE.relative_to(ROOT))
        and task.get("rounding_review")==SELECTOR and admitted["task_spec"]==task
        and admitted["program_sha256"]==digest(program) and admitted["binding"]==a.binding(task),
        "Current unchanged rounding admission required")
    require(not (HERE/"outputs.json").exists(),"Rounding evidence already sealed")
    history=read(REVIEW/"history.json")
    require(all(file_hash(ROOT/p)==h for p,h in history["protected"].items()),"Retained evidence changed")
    require(files(ROOT/"src/legalmath")==history["package"],"Production package changed")
    if (HERE/"source-review-pin.json").exists():
        require(file_hash(HERE/"SOURCE-REVIEW.md")==read(HERE/"source-review-pin.json")["sha256"],"Source review changed")
    return admitted


def render_command():
    doc=read(PRIOR/"original-source.json")
    renderer=read(REVIEW/"history.json")["renderer"]
    require(file_hash(ROOT/doc["path"])==doc["sha256"],"Original PDF changed")
    require(file_hash(Path(renderer["path"]))==renderer["sha256"],"Renderer changed")
    return [renderer["path"],"-f","209","-l","209","-scale-to","2600","-png",str(ROOT/doc["path"]),str(HERE/"policy")]


def prepare():
    products=load(PRIOR/"products.json.gz")
    units=[u for u in products["P1"]["payload"]["graph"]["units"] if u["document"]==DOCUMENT and u["page"] in SELECTOR["source_pages"]]
    save("source-units.json",units)
    (HERE/"native-source.txt").write_text("\n".join(u["id"]+" "+u["raw"] for u in units)+"\n")
    with (HERE/"render.stdout").open("xb") as out,(HERE/"render.stderr").open("xb") as err:
        result=subprocess.run(render_command(),stdout=out,stderr=err,timeout=25,env=dict(os.environ))
    require(result.returncode==0,"Original policy render failed")
    old_images=read(REVIEW/"history.json")["images"]
    image=HERE/"policy-209.png"
    save("images.json",old_images+[{"page":209,"path":str(image.relative_to(ROOT)),"sha256":file_hash(image)}])
    return {"source_occurrences":len(units),"pages":SELECTOR["source_pages"],"new_renders":1,"extractions":0}


def residual_interval(amounts,coefficients,error_bound):
    """Exact conditional interval for the underlying signed residual."""
    require(len(amounts)==len(coefficients) and bool(amounts),"Matched nonempty relation required")
    require(all(type(v) is int for v in amounts),"Unknown/noninteger source amount cannot be rounded away")
    require(all(type(v) is int for v in coefficients),"Integer relation coefficients required")
    epsilon=Fraction(error_bound)
    require(epsilon>=0,"Nonnegative per-quantity error bound required")
    residual=sum(a*c for a,c in zip(amounts,coefficients))
    bound=sum(abs(c) for c in coefficients)*epsilon
    lower,upper=Fraction(residual)-bound,Fraction(residual)+bound
    return {"displayed_residual":residual,"per_quantity_error_bound":str(epsilon),
        "maximum_relation_error":str(bound),"underlying_residual_interval":[str(lower),str(upper)],
        "zero_feasible_under_hypothesis":lower<=0<=upper,
        "actual_rounding_algorithm_established":False,"common_scope_assumed_for_test":True}


def analyze():
    require((HERE/"SOURCE-REVIEW.md").is_file(),"Full original image/source review required")
    save("source-review-pin.json",{"sha256":file_hash(HERE/"SOURCE-REVIEW.md")})
    units=read(HERE/"source-units.json")
    index={u["id"]:u for u in units}
    require(all(file_hash(ROOT/r["path"])==r["sha256"] for r in read(HERE/"images.json")),"Original images changed")
    def source(page,line): return deepcopy(index[f"{DOCUMENT}:p{page}:l{line}"])
    def quantity(page,line):
        s=source(page,line)
        raw=s["raw"].strip().replace(",","").replace("–","-")
        return {"value":None if raw=="-" else int(raw),"source":s,"unit":"million EUR"}
    def claim(ok,message): require(ok,message)
    prior=load(PRIOR/"pension-consumer.json.gz")
    movement={r["id"]:r for r in prior["pension_note_review"]["tables"]["net"]["rows"]}
    statement={r["id"]:r for r in prior["statement_review"]["rows"]}
    comparisons=[]
    for year,reported_line,component_lines in (("2022",13,[86,80,140]),("2021",14,[87,81,141])):
        reported=quantity(204,reported_line)
        parts=[quantity(264,n) for n in component_lines]
        claim(reported["value"]==statement["pensions"]["cells"][year]["integer_millions"],"Prior statement changed")
        for q,row in zip(parts,("actuarial","return_deviation","ceiling")):
            claim(q["value"]==movement[row]["cells"][year]["value"],"Prior pension movement changed")
        values=[reported["value"]]+[p["value"] for p in parts]
        cases=[] if None in values else [residual_interval(values,[1,-1,-1,-1],bound) for bound in ("1/2","1")]
        comparisons.append({"year":year,"reported":reported,"components":parts,"rounding_hypotheses":cases,
            "unknown_ceiling":None in values,"symbolic_residual":"45 - unknown signed asset-ceiling amount" if year=="2021" else None,
            "scope_equivalence_established":False,"residual_attributed":False})
    subtotals=[]
    for year,lines in (("2022",[21,13,16,18]),("2021",[22,14,17,19])):
        qs=[quantity(204,n) for n in lines]
        subtotals.append({"year":year,"quantities":qs,"hypotheses":[residual_interval([q["value"] for q in qs],[1,-1,-1,-1],b) for b in ("1/2","1")],
            "rounding_cause_established":False})
    # Analytical edge checks include feasible boundary cases, impossible cases,
    # negative residual symmetry, exact cancellation, scaling and unknown refusal.
    controls=[]
    for name,amounts,coefs,eps,feasible in (
        ("thirty-nearest",[3758,6800,-2641,-431],[1,-1,-1,-1],"1/2",False),
        ("thirty-unit-bound",[3758,6800,-2641,-431],[1,-1,-1,-1],"1",False),
        ("one-nearest",[2586,3758,-1256,83],[1,-1,-1,-1],"1/2",True),
        ("exact-relation",[2709,3476,-811,44],[1,-1,-1,-1],"0",True),
        ("positive-boundary",[2,0,0,0],[1,-1,-1,-1],"1/2",True),
        ("negative-boundary",[-2,0,0,0],[1,-1,-1,-1],"1/2",True),
        ("beyond-boundary",[3,0,0,0],[1,-1,-1,-1],"1/2",False),
        ("scaled-coefficients",[1,0],[2,-2],"1/2",True)):
        actual=residual_interval(amounts,coefs,eps)
        claim(actual["zero_feasible_under_hypothesis"] is feasible,"Interval boundary error: "+name)
        controls.append({"case":name,"expected_feasible":feasible,"actual":actual})
    for name,args,reason in (
        ("unknown-ceiling",([3476,1496,1935,None],[1,-1,-1,-1],"1/2"),"Unknown/noninteger source amount cannot be rounded away"),
        ("negative-error",([1,1],[1,-1],"-1"),"Nonnegative per-quantity error bound required"),
        ("missing-component",([1],[1,-1],"1/2"),"Matched nonempty relation required"),
        ("boolean-value",([True,1],[1,-1],"1/2"),"Unknown/noninteger source amount cannot be rounded away")):
        try: residual_interval(*args)
        except ValueError as exc:
            claim(str(exc)==reason,"Unintended rounding refusal")
            controls.append({"case":name,"refused":True,"reason":str(exc)})
        else: raise ValueError("Invalid rounding relation accepted")
    analysis={"source":"original English BASF2022 report; German written origin is source-reported",
        "policy_source":[source(209,n) for n in range(14,38)],"source_occurrences":len(units),
        "candidate_bridges":comparisons,"after_tax_subtotals":subtotals,
        "derivation":"If sum(a_i*x_i)=0 and abs(d_i-x_i)<=epsilon_i, triangle inequality implies abs(sum(a_i*d_i))<=sum(abs(a_i)*epsilon_i). Source does not specify epsilon or rounding algorithm.",
        "2021_numeric_coincidence":{"known_component_residual":45,"acquisitions_divestitures":quantity(264,133),"attribution_established":False},
        "answer_effect":[
            "The report states amounts are in millions of euros and rounded totals may differ; it does not specify a rounding algorithm.",
            "The2022 candidate reconciliation has a30million residual. If its four displayed quantities share the proposed complete scope, nearest-million rounding permits at most2million and per-quantity errors bounded by1million permit at most4million. Neither hypothesis explains30.",
            "The2022 after-tax subtotal has a separate1million residual, compatible with those rounding bounds. This does not prove actual rounding caused it. The2021 after-tax subtotal agrees exactly.",
            "The2021 candidate bridge retains an unknown ceiling: its symbolic residual is45 minus that signed unknown. A displayed45 in acquisitions/divestitures does not establish attribution or authorize substituting zero.",
            "The30million difference still needs a complete accounting-scope bridge or authoritative source clarification. No fundamental extraction/package defect or source error has been established."],
        "clarification_questions":["Which component or scope difference reconciles2022 statement3,758 with Note22 components3,728?",
            "What does the2021 asset-ceiling dash denote, and which complete bridge reconciles3,476?",
            "Does a controlling German edition or official correction change either source amount or scope?"],
        "independent_acceptance":False,"financial_values_validated":False,"source_error_established":False,"package_defect_established":False}
    supplement={**prior,"pension_rounding_agent_review":analysis}
    claim({k:supplement[k] for k in prior}==prior,"Whole prior pension consumer changed")
    save("analysis.json",analysis)
    save("actual-controls.json",controls)
    save("answer-supplement.json.gz",supplement)
    save("comparison.json",{"whole_prior_consumer_equal":True,"prior_sha256":file_hash(PRIOR/"pension-consumer.json.gz"),
         "controls":len(controls),"source_occurrences":len(units),"task_complete":False})
    return {"whole_prior_consumer_equal":True,"controls":len(controls),"thirty_million_unresolved":True}


def seal():
    require((HERE/"RESULT.md").is_file(),"Actual result review required")
    require(read(HERE/"comparison.json")["whole_prior_consumer_equal"],"Prior answer preservation required")
    save("verified-result.json",{**read(HERE/"comparison.json"),"result_sha256":file_hash(HERE/"RESULT.md")})
    return {"retained":True,"task_complete":False}


def run(stage):
    with Authority(ROOT).lock():
        admitted=bindings()
        i=STAGES.index(stage)
        require({p.parent.name for p in (HERE/"stages").glob("*/started.json")}==
                {p.parent.name for p in (HERE/"stages").glob("*/result.json")}==set(STAGES[:i]),"Repeated/skipped/interrupted rounding stage")
        rows=[read(HERE/"stages"/s/"result.json") for s in STAGES[:i]]
        require(all(r["status"]=="PASS" for r in rows),"Failed rounding predecessor")
        spent=sum(r["wall_seconds"] for r in rows)
        before=storage()
        save("stages/"+stage+"/started.json",{"command":["timeout","65",".venv/bin/python","-m","scripts.prospectus_basf_rounding_review",stage],
            "at":datetime.now(timezone.utc).isoformat(),"git_commit":admitted["git_commit"],"python":sys.executable,
            "cpu_gpu":"CPU only; GPU devices intentionally hidden","seeds":"N/A deterministic exact arithmetic",
            "plan":PLAN,"data":str((PRIOR/"outputs.json").relative_to(ROOT)),"result":str((HERE/"RESULT.md").relative_to(ROOT))})
        def expire(signum,frame): raise TimeoutError("Rounding stage bound; no retry")
        old=signal.signal(signal.SIGALRM,expire)
        signal.setitimer(signal.ITIMER_REAL,55)
        tick,details,error=time.monotonic(),None,None
        try:
            require(spent<180 and before["previous_seconds"]+spent<900 and before["new_bytes"]<14*1024**2 and before["combined_bytes"]<498*1024**2,"Rounding cumulative bounds exhausted")
            commands=[render_command()] if stage=="prepare" else []
            with execution_guard(commands) as guard: details=globals()[stage]()
            require(guard.result()=={"starts":len(commands),"blocked":0},"Unexpected process/network operation")
            details["process_guard"]=guard.result()
            bindings()
            limits=storage()
            elapsed=time.monotonic()-tick
            require(elapsed<60 and spent+elapsed<180 and limits["previous_seconds"]+spent+elapsed<900
                and limits["new_bytes"]<14*1024**2 and limits["combined_bytes"]<498*1024**2,"Rounding bound exceeded")
        except BaseException as exc:
            error={"type":type(exc).__name__,"message":str(exc)}
            save("stages/"+stage+"/error.json",{"traceback":traceback.format_exc()})
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
            signal.signal(signal.SIGALRM,old)
        result={"stage":stage,"status":"FAIL" if error else "PASS","error":error,"details":details,
                "wall_seconds":time.monotonic()-tick,"bounds":storage()}
        result["cumulative_seconds"]=spent+result["wall_seconds"]
        save("stages/"+stage+"/result.json",result)
        if error or stage=="seal":
            save("result.json",{**result,"task":"basf-references","task_complete":False,"whole_program_complete":False,"independent_legal_acceptance":False})
            save("outputs.json",files(HERE))
        print(json.dumps({k:result[k] for k in ("stage","status","error","wall_seconds","cumulative_seconds")}))
        return int(error is not None)


if __name__=="__main__": raise SystemExit(run(sys.argv[1]))
