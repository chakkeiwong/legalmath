"""Read the complete original EPS notes behind the 2008 comparative difference."""
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
HERE=BASE/"attempts/source-bes-dep-07/attempt-007"
PREVIOUS=tuple(HERE.parent/("attempt-00"+str(i)) for i in (3,4,5,6))
PRIOR=PREVIOUS[2]
VERIFIED=PREVIOUS[3]/"verified-answer-reference.json"
ORIGINAL=PREVIOUS[0]/"original-P1.json.gz"
REPORT2009=BASE/"attempts/source-bes-dep-06/attempt-001/source-product.json.gz"
PRIMARY2008=PREVIOUS[1]/"source-units.json"
PRIMARY2009=BASE/"attempts/source-bes-dep-06/attempt-004/source-units.json"
REVIEW=BASE/"reviews/2008-eps-179"
PLAN="docs/plans/prospectus-2008-eps-explanation-2026-10-17.md"
KEY="original2008_EPS_note_comparison_agent_reading"
STAGES=("prepare","render-en","render-pt","render-2009","profile","answer","controls","seal")
SELECTOR={"version":"bes-2008-EPS-source-explanation.v1","stages":list(STAGES),
    "context_occurrences":405,"note_occurrences":81,"minimum_semantic_controls":20,
    "new_seconds":100,"combined003_007_seconds":1080,"new_bytes":2300*1024,
    "combined003_007_bytes":160*1024**2,"new_reserve_bytes":128*1024,
    "combined_reserve_bytes":256*1024,"work_seconds":45,"stage_seconds":50,
    "render_children":3,"child_seconds":20,"render_scale":1800,"render_gray":True,
    "extraction_OCR_network_model_GPU_install_production_edits_retries":0}
LIMITS={"financial_values_validated":False,"source_authenticity_established":False,
    "independent_acceptance":False,"production_integration":False,"automatic_discovery":False,
    "accounting_standard_compliance_determined":False,"Note46_resolved":False,
    "all_notes_read":False,"BES_Finance_standalone_accounts_supplied":False}


def save(name,value):
    path=HERE/name
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()
    with path.open("xb") as stream:
        stream.write(gzip.compress(raw,mtime=0) if path.suffix==".gz" else raw+b"\n")


def storage():
    return {"previous_seconds":sum(read(p)["wall_seconds"] for folder in PREVIOUS for p in (folder/"stages").glob("*/result.json")),
        "combined_bytes":sum(p.stat().st_size for d in (*PREVIOUS,HERE) for p in d.rglob("*") if p.is_file()),
        "new_bytes":sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file())}


def bindings():
    a=Authority(ROOT)
    program,tasks,_=a.spec()
    task=tasks["source-bes-dep-07"]
    admitted=read(HERE/"admission.json")
    event=next(e for e in reversed(a.events()) if e.get("task")==task["id"])
    require(event["kind"]=="ADMIT" and event["attempt"]==str(HERE.relative_to(ROOT)) and
        task.get("eps_note_reading")==SELECTOR and admitted["task_spec"]==task and
        admitted["program_sha256"]==digest(program) and admitted["binding"]==a.binding(task),"Current unchanged EPS admission required")
    require(not (HERE/"outputs.json").exists(),"EPS attempt already sealed")
    history=read(REVIEW/"history.json")
    require(all(file_hash(ROOT/p)==h for p,h in history["protected"].items()),"Historical evidence changed")
    require(files(ROOT/"src/legalmath")==history["package"],"Production files changed")
    if (HERE/"reading-methods.json").exists():
        require(all(file_hash(ROOT/p)==h for p,h in read(HERE/"reading-methods.json").items()),"Frozen EPS reading changed")
    return admitted


def prepare():
    product=load(ORIGINAL)
    docs=product["payload"]["request"]["bundle"]["documents"]
    require({d["id"] for d in docs}=={"bes-2008-en","bes-2008-pt"},"Original bilingual2008 pair required")
    units=[u for u in product["payload"]["graph"]["units"] if u["document"] in {d["id"] for d in docs} and u["page"] in (105,106)]
    del product
    product=load(REPORT2009)
    doc=next(d for d in product["payload"]["request"]["bundle"]["documents"] if d["id"]=="bes-report-2009")
    units += [u for u in product["payload"]["graph"]["units"] if u["document"]==doc["id"] and u["page"]==112]
    docs=docs+[doc]
    require(len(units)==405 and len({u["id"] for u in units})==405,"All405 exact document/page occurrences required")
    require(all(file_hash(ROOT/d["path"])==d["sha256"] for d in docs),"Original EPS PDF changed")
    save("source-units.json.gz",units)
    with (HERE/"native-source.txt").open("x") as stream:
        stream.write("\n".join(u["id"]+" "+u["raw"] for u in units)+"\n")
    links=[]
    for path in (PRIMARY2008,PRIMARY2009):
        for u in read(path):
            line=int(u["id"].rsplit("l",1)[1])
            if (u["document"]=="bes-2008-en" and ((u["page"]==71 and 110<=line<=132) or (u["page"]==73 and 121<=line<=131) or (u["page"]==73 and line==282))) or \
                (u["document"]=="bes-report-2009" and ((u["page"]==75 and 102<=line<=123) or (u["page"]==78 and 286<=line<=296) or (u["page"]==78 and line==342))):
                links.append(u)
    require(len(links)==69,"Exact earlier primary links required")
    save("linked-primary-units.json.gz",links)
    renderer=read(REVIEW/"history.json")["renderer"]
    for d in docs:
        name=d["language"] if d["id"].startswith("bes-2008") else "2009"
        pages=[105,106] if name!="2009" else [112]
        save("render-spec-"+name+".json",{"source":d,"renderer":renderer,"pages":pages,
            "argv":[renderer["path"],"-f",str(pages[0]),"-l",str(pages[-1]),"-scale-to","1800","-gray","-png",str(ROOT/d["path"]),str(HERE/("eps-"+name))]})
    return {"context_occurrences":405,"linked_primary_occurrences":len(links),"new_text_extractions":0}


def render_language(name):
    spec=read(HERE/("render-spec-"+name+".json"))
    require(file_hash(ROOT/spec["source"]["path"])==spec["source"]["sha256"] and
        file_hash(Path(spec["renderer"]["path"]))==spec["renderer"]["sha256"],"Source/renderer changed")
    with (HERE/("render-"+name+".stdout")).open("xb") as out,(HERE/("render-"+name+".stderr")).open("xb") as err:
        result=subprocess.run(spec["argv"],stdout=out,stderr=err,timeout=20,env=dict(os.environ))
    paths=sorted(HERE.glob("eps-"+name+"-*.png"))
    require(result.returncode==0 and [int(p.stem.split("-")[-1]) for p in paths]==spec["pages"],"Exact EPS page images required")
    save("images-"+name+".json",[{"document":spec["source"]["id"],"page":int(p.stem.split("-")[-1]),"path":str(p.relative_to(ROOT)),"sha256":file_hash(p)} for p in paths])
    if name=="2009": save("images.json",[i for lang in ("en","pt","2009") for i in read(HERE/("images-"+lang+".json"))])
    return {"rendered_pages":len(paths),"source":spec["source"]["id"]}


def evaluator():
    spec=importlib.util.spec_from_file_location("original2008_eps_reading",HERE/"reading.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(value,pin):
    require(digest(value)==pin,"EPS profile pin changed")
    require(value["version"]==SELECTOR["version"] and value["limits"]==LIMITS,"EPS authority/integration limits required")
    require(value["images"]==read(HERE/"images.json") and all(file_hash(ROOT/i["path"])==i["sha256"] for i in value["images"]),"Exact five original EPS images required")
    require(value["baseline_reference"]==read(VERIFIED)["candidate"] and file_hash(PRIOR/"answer-supplement.json.gz")==value["baseline_reference"]["file_sha256"],"Verified complete prior answer required")
    return evaluator().evaluate(load(HERE/"source-units.json.gz"),load(HERE/"linked-primary-units.json.gz"),value["reading"])


def profile():
    names=("reading.py","prepare-reading.py","SOURCE-REVIEW.md","IMPLEMENTATION-REVIEW.md","draft-profile.json")
    require(all((HERE/name).is_file() for name in names),"Full EPS reading and actual image/implementation reviews required")
    paths=[Path(__file__),ROOT/PLAN,REVIEW/"REVIEW.md",HERE/"source-units.json.gz",HERE/"linked-primary-units.json.gz",HERE/"images.json"]+[HERE/name for name in names]
    save("reading-methods.json",{str(p.relative_to(ROOT)):file_hash(p) for p in paths})
    value=read(HERE/"draft-profile.json")
    validate(value,digest(value))
    cases=evaluator().CASES
    require(len(cases)>=20,"At least20 meaningful EPS refusal cases required")
    save("profile.json",value)
    save("profile-pin.json",{"sha256":digest(value)})
    save("intended-refusals.json",cases)
    return {"reading_frozen":True,"intended_controls":len(cases)}


def answer():
    value=read(HERE/"profile.json")
    analysis=validate(value,read(HERE/"profile-pin.json")["sha256"])
    baseline=load(PRIOR/"answer-supplement.json.gz")
    require(digest(baseline)==read(VERIFIED)["candidate"]["content_sha256"],"Complete saved baseline content changed")
    unresolved={"BES-DEP-"+str(i).zfill(2) for i in range(1,12)}|{"BES-DEP-AGENCY-"+str(i).zfill(2) for i in range(1,4)}
    require({d["id"] for d in baseline["dependencies"] if d["id"] in unresolved and d["status"]=="UNRESOLVED"}==unresolved and baseline["questions"]["Q3"]["status"]=="PARTIAL","Original unresolved dependencies/Q3 required")
    overlay={"source_units":load(HERE/"source-units.json.gz"),"linked_primary_units":load(HERE/"linked-primary-units.json.gz"),"profile":value,"analysis":analysis,"limits":LIMITS}
    require(KEY not in baseline,"EPS addition already present")
    combined={**baseline,KEY:overlay}
    require({k:combined[k] for k in baseline}==baseline,"Complete prior answer changed")
    save("answer-overlay.json.gz",{KEY:overlay})
    save("analysis.json",analysis)
    save("answer-composition.json",{"baseline":read(VERIFIED)["candidate"],"overlay":{"path":str((HERE/"answer-overlay.json.gz").relative_to(ROOT)),"file_sha256":file_hash(HERE/"answer-overlay.json.gz"),"content_sha256":digest({KEY:overlay})},
        "composition_rule":"Exact baseline object plus the sole new overlay field; reject duplicate keys",
        "complete_composed_answer_sha256":digest(combined),"complete_prior_consumer_equal":True,
        "materialized_in_memory":True,"large_answer_copies":0,"source_occurrences":405,"note_occurrences":81,
        "original_BES_dependencies_unresolved":14,"Q3":"PARTIAL"})
    return {"full_answer_composition_verified":True,"EPS_explanation_retained":True,"new_large_answer_copies":0}


def controls():
    value=read(HERE/"profile.json")
    method=evaluator()
    results=[]
    for name,reason in read(HERE/"intended-refusals.json").items():
        bad=method.altered(value,name)
        pin=digest(bad)
        save("adverse-inputs/"+name+".json.gz",{"profile":bad,"expected_pin":pin})
        try: validate(bad,pin)
        except ValueError as exc:
            row={"case":name,"refused":True,"repinned":True,"reason":str(exc)}
            save("adverse-results/"+name+".json",row)
            require(str(exc)==reason,"Wrong EPS semantic refusal: "+name+": "+str(exc))
            results.append(row)
        else: raise ValueError("Changed EPS reading accepted: "+name)
    save("actual-controls.json",results)
    return {"actual_refusals":len(results),"repinned":len(results)}


def seal():
    require((HERE/"RESULT.md").is_file(),"Actual EPS result required")
    controls=read(HERE/"actual-controls.json")
    expected=read(HERE/"intended-refusals.json")
    require(len(controls)==len(expected)>=20 and {r["case"] for r in controls}==set(expected) and
        all(r["refused"] and r["repinned"] and r["reason"]==expected[r["case"]] for r in controls),"All exact actual EPS refusals required")
    save("verified-result.json",{**read(HERE/"answer-composition.json"),"actual_refusals":len(controls),"task_complete":False,"result_sha256":file_hash(HERE/"RESULT.md")})
    return {"conditional_EPS_explanation_retained":True,"task_complete":False}


def run(stage):
    with Authority(ROOT).lock():
        admitted=bindings()
        i=STAGES.index(stage)
        require({p.parent.name for p in (HERE/"stages").glob("*/started.json")}==
            {p.parent.name for p in (HERE/"stages").glob("*/result.json")}==set(STAGES[:i]),"Repeated/skipped/interrupted EPS stage")
        rows=[read(HERE/"stages"/s/"result.json") for s in STAGES[:i]]
        require(all(r["status"]=="PASS" and r["wall_seconds"]<50 for r in rows),"Failed EPS predecessor")
        spent=sum(r["wall_seconds"] for r in rows)
        before=storage()
        def within(now,elapsed=0):
            return spent+elapsed<100 and now["previous_seconds"]+spent+elapsed<1080 and \
                now["new_bytes"]<2300*1024-128*1024 and now["combined_bytes"]<160*1024**2-256*1024
        require(within(before),"Cumulative EPS bounds exhausted")
        save("stages/"+stage+"/started.json",{"command":["timeout","55",".venv/bin/python","-m","scripts.prospectus_2008_eps",stage],
            "at":datetime.now(timezone.utc).isoformat(),"git_commit":admitted["git_commit"],"python":sys.executable,
            "cpu_gpu":"CPU only; GPU devices intentionally hidden","random_seeds":"N/A deterministic source reading",
            "plan":PLAN,"data_version":[str(ORIGINAL.relative_to(ROOT)),str(REPORT2009.relative_to(ROOT))],"result":str((HERE/"RESULT.md").relative_to(ROOT))})
        tick,details,error=time.monotonic(),None,None
        def expire(signum,frame): raise TimeoutError("EPS cumulative bound; no retry")
        old=signal.signal(signal.SIGALRM,expire)
        signal.setitimer(signal.ITIMER_REAL,min(45,100-spent,1080-before["previous_seconds"]-spent))
        try:
            render=stage.startswith("render-")
            commands=[read(HERE/("render-spec-"+stage[7:]+".json"))["argv"]] if render else []
            with execution_guard(commands) as guard:
                details=render_language(stage[7:]) if render else globals()[stage]()
            require(guard.result()=={"starts":int(render),"blocked":0},"Unexpected EPS process/network action")
            details["process_guard"]=guard.result()
            bindings()
            elapsed=time.monotonic()-tick
            require(elapsed<50 and within(storage(),elapsed),"EPS cumulative bound exceeded")
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
            save("result.json",{**result,"task":"source-bes-dep-07","task_complete":False,"whole_program_complete":False,"independent_legal_acceptance":False})
            save("outputs.json",files(HERE))
        print(json.dumps({k:result[k] for k in ("stage","status","error","wall_seconds","cumulative_seconds")}))
        return int(error is not None)


if __name__=="__main__": raise SystemExit(run(sys.argv[1]))
