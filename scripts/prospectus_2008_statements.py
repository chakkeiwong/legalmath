"""Bounded original2008 bilingual primary-statement agent reading."""
from datetime import datetime, timezone
import gzip
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/"src"),str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1",PYTHONNOUSERSITE="1",PYTHONPATH="",PYTHONDONTWRITEBYTECODE="1")
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read
from scripts.prospectus_basf_pension_source import files,load,require
from scripts.prospectus_installed_profile_worker import execution_guard

BASE=ROOT/"docs/implementation/prospectus-execution-authority"
HERE=BASE/"attempts/source-bes-dep-07/attempt-004"
PRIOR=HERE.parent/"attempt-003"
ORIGINAL=PRIOR/"original-P1.json.gz"
COMPARATOR=BASE/"attempts/source-bes-dep-06/attempt-005"
REVIEW=BASE/"reviews/2008-statements-176"
PLAN="docs/plans/prospectus-2008-bilingual-statements-2026-10-17.md"
STAGES=("prepare","render-en","render-pt","profile","answer","controls","seal")
SELECTOR={"version":"bes-2008-bilingual-primary-statements-agent.v1","stages":list(STAGES),
    "source_pages":[71,72,73,74],"occurrences":1488,"work_seconds":110,"stage_seconds":115,
    "new_seconds":240,"combined003_004_seconds":1080,"new_bytes":64*1024**2,
    "combined003_004_bytes":160*1024**2,"render_children":2,"child_seconds":45,
    "minimum_semantic_controls":32,"extraction_OCR_network_model_GPU_install_production_edits_retries":0}
LIMITS={"financial_values_validated":False,"source_authenticity_established":False,
    "independent_accounting_interpretation":False,"independent_legal_acceptance":False,
    "actual_incorporation_resolved":False,"production_integration_claimed":False,
    "automatic_extraction":False,"BES_Finance_standalone_accounts_supplied":False,
    "all_report_notes_interpreted":False,"prior_2008_discrepancy_resolved":False}


def save(name,value):
    p=HERE/name
    p.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()
    with p.open("xb") as stream: stream.write(gzip.compress(raw,mtime=0) if p.suffix==".gz" else raw+b"\n")


def storage():
    return {"previous_seconds":sum(read(p)["wall_seconds"] for p in (PRIOR/"stages").glob("*/result.json")),
        "combined_bytes":sum(p.stat().st_size for d in (PRIOR,HERE) for p in d.rglob("*") if p.is_file()),
        "new_bytes":sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file())}


def bindings():
    a=Authority(ROOT)
    program,tasks,_=a.spec()
    task=tasks["source-bes-dep-07"]
    admitted=read(HERE/"admission.json")
    event=next(e for e in reversed(a.events()) if e.get("task")==task["id"])
    require(event["kind"]=="ADMIT" and event["attempt"]==str(HERE.relative_to(ROOT))
        and task.get("statements_reading")==SELECTOR and admitted["task_spec"]==task
        and admitted["program_sha256"]==digest(program) and admitted["binding"]==a.binding(task),"Current unchanged2008 statement admission required")
    require(not (HERE/"outputs.json").exists(),"2008 statements already sealed")
    history=read(REVIEW/"history.json")
    require(all(file_hash(ROOT/p)==h for p,h in history["protected"].items()),"Historical evidence changed")
    require(files(ROOT/"src/legalmath")==history["package"],"Production files changed")
    if (HERE/"reading-methods.json").exists():
        require(all(file_hash(ROOT/p)==h for p,h in read(HERE/"reading-methods.json").items()),"Frozen2008 reading changed")
    return admitted


def prepare():
    product=load(ORIGINAL)
    documents=product["payload"]["request"]["bundle"]["documents"]
    require({d["id"] for d in documents}=={"bes-2008-en","bes-2008-pt"},"Original2008 language pair required")
    require(all(file_hash(ROOT/d["path"])==d["sha256"] for d in documents),"Original2008 PDF changed")
    units=[u for u in product["payload"]["graph"]["units"] if u["page"] in SELECTOR["source_pages"]]
    require(len(units)==1488 and len({u["id"] for u in units})==1488,"Complete1488 original occurrences required")
    save("source-units.json",units)
    (HERE/"native-source.txt").write_text("\n".join(u["id"]+" "+u["raw"] for u in units)+"\n")
    renderer=read(REVIEW/"history.json")["renderer"]
    for doc in documents:
        lang=doc["language"]
        save("render-spec-"+lang+".json",{"source":doc,"renderer":renderer,"argv":[renderer["path"],"-f","71","-l","74","-scale-to","2200","-png",str(ROOT/doc["path"]),str(HERE/("statements-"+lang))]})
    return {"source_occurrences":1488,"source_pages":SELECTOR["source_pages"],"languages":["en","pt"]}


def render_language(lang):
    spec=read(HERE/("render-spec-"+lang+".json"))
    require(file_hash(ROOT/spec["source"]["path"])==spec["source"]["sha256"] and file_hash(Path(spec["renderer"]["path"]))==spec["renderer"]["sha256"],"Original source/renderer changed")
    with (HERE/("render-"+lang+".stdout")).open("xb") as out,(HERE/("render-"+lang+".stderr")).open("xb") as err:
        result=subprocess.run(spec["argv"],stdout=out,stderr=err,timeout=45,env=dict(os.environ))
    paths=sorted(HERE.glob("statements-"+lang+"-*.png"))
    require(result.returncode==0 and [int(p.stem.split("-")[-1]) for p in paths]==SELECTOR["source_pages"],"Exactly four original images per language required")
    save("images-"+lang+".json",[{"document":spec["source"]["id"],"page":int(p.stem.split("-")[-1]),"path":str(p.relative_to(ROOT)),"sha256":file_hash(p)} for p in paths])
    if lang=="pt": save("images.json",read(HERE/"images-en.json")+read(HERE/"images-pt.json"))
    return {"rendered_pages":4,"language":lang,"new_text_extractions":0}


def evaluator():
    spec=importlib.util.spec_from_file_location("original2008_reading",HERE/"reading.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(value,pin):
    units=read(HERE/"source-units.json")
    require(digest(value)==pin,"2008 profile pin changed")
    require(value["version"]==SELECTOR["version"] and value["limits"]==LIMITS,"2008 reading cannot establish unsupported authority or integration")
    require(value["source_units"]==[{"id":u["id"],"quote":u["raw"]} for u in units],"Complete original1488 quotes required")
    require(value["images"]==read(HERE/"images.json") and all(file_hash(ROOT/i["path"])==i["sha256"] for i in value["images"]),"Original2008 images changed")
    require(value["prior_sha256"]==file_hash(PRIOR/"candidate-answer.json.gz") and value["comparative_sha256"]==file_hash(COMPARATOR/"answer-supplement.json.gz"),"Complete prior/comparative source changed")
    return evaluator().evaluate(units,value["reading"])


def profile():
    names=("SOURCE-REVIEW.md","IMPLEMENTATION-REVIEW.md","draft-profile.json","reading.py")
    require(all((HERE/name).is_file() for name in names),"Complete original reading and reviews required")
    paths=[Path(__file__),ROOT/PLAN,REVIEW/"REVIEW.md",HERE/"source-units.json",HERE/"images.json"]+[HERE/name for name in names]
    save("reading-methods.json",{str(p.relative_to(ROOT)):file_hash(p) for p in paths})
    value=read(HERE/"draft-profile.json")
    validate(value,digest(value))
    cases=evaluator().CASES
    require(len(cases)>=32,"At least32 semantic controls required")
    save("profile.json",value)
    save("profile-pin.json",{"sha256":digest(value)})
    save("intended-refusals.json",cases)
    return {"reading_frozen":True,"controls":len(cases)}


def answer():
    value=read(HERE/"profile.json")
    analysis=validate(value,read(HERE/"profile-pin.json")["sha256"])
    prior=load(PRIOR/"candidate-answer.json.gz")
    original={"BES-DEP-"+str(i).zfill(2) for i in range(1,12)}|{"BES-DEP-AGENCY-"+str(i).zfill(2) for i in range(1,4)}
    require(len([d for d in prior["dependencies"] if d["id"] in original and d["status"]=="UNRESOLVED"])==14 and prior["questions"]["Q3"]["status"]=="PARTIAL","Original unresolved answer required")
    analysis["limits"]=LIMITS
    supplement={**prior,"original2008_primary_statement_agent_reading":{"source_units":read(HERE/"source-units.json"),"profile":value,"analysis":analysis}}
    require({k:supplement[k] for k in prior}==prior,"Complete prior answer changed")
    save("answer-supplement.json.gz",supplement)
    save("analysis.json",analysis)
    save("comparison.json",{"complete_prior_consumer_equal":True,"source_occurrences":1488,"original_BES_dependencies_unresolved":14,"Q3":"PARTIAL","supplement_sha256":digest(supplement)})
    return {"complete_prior_consumer_equal":True,"primary_statement_reading_added":True}


def controls():
    value=read(HERE/"profile.json")
    method=evaluator()
    results=[]
    for name,reason in read(HERE/"intended-refusals.json").items():
        bad=method.altered(value,name)
        pin=digest(bad)
        save("adverse-inputs/"+name+".json",{"profile":bad,"expected_pin":pin})
        try: validate(bad,pin)
        except ValueError as exc:
            row={"case":name,"refused":True,"repinned":True,"reason":str(exc)}
            save("adverse-results/"+name+".json",row)
            require(str(exc)==reason,"Wrong2008 semantic refusal: "+name+": "+str(exc))
            results.append(row)
        else: raise ValueError("Changed2008 reading accepted: "+name)
    save("actual-controls.json",results)
    return {"actual_refusals":len(results),"repinned":len(results)}


def seal():
    require((HERE/"RESULT.md").is_file(),"Actual2008 result required")
    controls=read(HERE/"actual-controls.json")
    require(len(controls)>=32 and all(r["reason"]==read(HERE/"intended-refusals.json")[r["case"]] for r in controls),"Complete actual refusals required")
    save("verified-result.json",{**read(HERE/"comparison.json"),"actual_refusals":len(controls),"task_complete":False,"result_sha256":file_hash(HERE/"RESULT.md")})
    return {"primary_statements_retained":True,"task_complete":False}


def run(stage):
    with Authority(ROOT).lock():
        admitted=bindings()
        i=STAGES.index(stage)
        require({p.parent.name for p in (HERE/"stages").glob("*/started.json")}=={p.parent.name for p in (HERE/"stages").glob("*/result.json")}==set(STAGES[:i]),"Repeated/skipped/interrupted2008 stage")
        rows=[read(HERE/"stages"/s/"result.json") for s in STAGES[:i]]
        require(all(r["status"]=="PASS" and r["wall_seconds"]<115 for r in rows),"Failed2008 predecessor")
        spent=sum(r["wall_seconds"] for r in rows)
        before=storage()
        require(spent<240 and before["previous_seconds"]+spent<1080 and before["new_bytes"]<63*1024**2 and before["combined_bytes"]<158*1024**2,"2008 cumulative bounds exhausted")
        save("stages/"+stage+"/started.json",{"command":["timeout","120",".venv/bin/python","-m","scripts.prospectus_2008_statements",stage],
            "at":datetime.now(timezone.utc).isoformat(),"git_commit":admitted["git_commit"],"python":sys.executable,
            "cpu_gpu":"CPU only; GPU devices intentionally hidden","random_seeds":"N/A deterministic source reading",
            "plan":PLAN,"data_version":str(ORIGINAL.relative_to(ROOT)),"result":str((HERE/"RESULT.md").relative_to(ROOT))})
        tick,details,error=time.monotonic(),None,None
        def expire(signum,frame): raise TimeoutError("2008 stage bound; no unchanged retry")
        old=signal.signal(signal.SIGALRM,expire)
        signal.setitimer(signal.ITIMER_REAL,min(110,240-spent,1080-before["previous_seconds"]-spent))
        try:
            commands=[read(HERE/("render-spec-"+stage.split("-")[1]+".json"))["argv"]] if stage.startswith("render-") else []
            with execution_guard(commands) as guard: details=render_language(stage.split("-")[1]) if stage.startswith("render-") else globals()[stage]()
            require(guard.result()=={"starts":len(commands),"blocked":0},"Unexpected process/network action")
            details["process_guard"]=guard.result()
            bindings()
            now=storage()
            elapsed=time.monotonic()-tick
            require(elapsed<115 and spent+elapsed<240 and now["previous_seconds"]+spent+elapsed<1080 and now["new_bytes"]<63*1024**2 and now["combined_bytes"]<158*1024**2,"2008 bound exceeded")
        except BaseException as exc:
            error={"type":type(exc).__name__,"message":str(exc)}
            save("stages/"+stage+"/error.json",{"traceback":traceback.format_exc()})
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
            signal.signal(signal.SIGALRM,old)
        result={"stage":stage,"status":"FAIL" if error else "PASS","error":error,"details":details,"wall_seconds":time.monotonic()-tick,"bounds":storage()}
        result["cumulative_seconds"]=spent+result["wall_seconds"]
        save("stages/"+stage+"/result.json",result)
        if error or stage=="seal":
            save("result.json",{**result,"task":"source-bes-dep-07","task_complete":False,"whole_program_complete":False,"independent_legal_acceptance":False})
            save("outputs.json",files(HERE))
        print(json.dumps({k:result[k] for k in ("stage","status","error","wall_seconds","cumulative_seconds")}))
        return int(error is not None)


if __name__=="__main__": raise SystemExit(run(sys.argv[1]))
