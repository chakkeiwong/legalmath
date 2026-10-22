"""Bounded complete-note reading of the changed 2008 asset comparative."""
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
HERE=BASE/"attempts/source-bes-dep-06/attempt-006"
PREVIOUS=tuple(HERE.parent/("attempt-00"+str(i)) for i in (3,4,5))
PRIOR=PREVIOUS[-1]
ORIGINAL=BASE/"attempts/source-bes-dep-07/attempt-003/original-P1.json.gz"
REPORT2009=HERE.parent/"attempt-001/source-product.json.gz"
PRIMARY2008=BASE/"attempts/source-bes-dep-07/attempt-004/source-units.json"
PRIMARY2009=PREVIOUS[1]/"source-units.json"
EPS=BASE/"attempts/source-bes-dep-07/attempt-007/answer-composition.json"
REVIEW=BASE/"reviews/2009-classification-180"
PLAN="docs/plans/prospectus-2009-asset-classification-2026-10-17.md"
KEY="original2008_2009_asset_classification_agent_reading"
STAGES=("prepare","render-policy08","render-notes08","render-policy09","render-notes09","profile","answer","controls","seal")
PAGES={"bes-2008-en":[86,90,119,124,125],"bes-report-2009":[91,92,125,130,131]}
RENDERS={"policy08":("bes-2008-en",[(86,86),(90,90)]),
    "notes08":("bes-2008-en",[(119,119),(124,125)]),
    "policy09":("bes-report-2009",[(91,92)]),
    "notes09":("bes-report-2009",[(125,125),(130,131)])}
SELECTOR={"version":"bes-2008-2009-asset-classification.v1","stages":list(STAGES),
    "context_occurrences":830,"section_occurrences":446,"source_pages":PAGES,
    "minimum_semantic_controls":24,"new_seconds":180,"combined003_006_seconds":1080,
    "new_bytes":16*1024**2,"combined003_006_bytes":160*1024**2,
    "new_reserve_bytes":256*1024,"combined_reserve_bytes":1024**2,
    "work_seconds":45,"stage_seconds":50,"render_children":7,"child_seconds":15,
    "render_scale":1800,"render_gray":True,
    "extraction_OCR_network_model_GPU_install_production_edits_retries":0}
LIMITS={"financial_values_validated":False,"source_authenticity_established":False,
    "independent_acceptance":False,"production_integration":False,"automatic_discovery":False,
    "accounting_standard_compliance_determined":False,"dated_Portuguese_law_checked":False,
    "individual_asset_flows_established":False,"controlling_edition_selected":False,
    "all_notes_read":False,"BES_Finance_standalone_accounts_supplied":False}


def save(name,value):
    path=HERE/name
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()
    with path.open("xb") as stream:
        stream.write(gzip.compress(raw,mtime=0) if path.suffix==".gz" else raw+b"\n")


def storage():
    return {"previous_seconds":sum(read(p)["wall_seconds"] for d in PREVIOUS for p in (d/"stages").glob("*/result.json")),
        "combined_bytes":sum(p.stat().st_size for d in (*PREVIOUS,HERE) for p in d.rglob("*") if p.is_file()),
        "new_bytes":sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file())}


def bindings():
    a=Authority(ROOT)
    program,tasks,_=a.spec()
    task=tasks["source-bes-dep-06"]
    admitted=read(HERE/"admission.json")
    event=next(e for e in reversed(a.events()) if e.get("task")==task["id"])
    require(event["kind"]=="ADMIT" and event["attempt"]==str(HERE.relative_to(ROOT)) and
        task.get("classification_reading")==SELECTOR and admitted["task_spec"]==task and
        admitted["program_sha256"]==digest(program) and admitted["binding"]==a.binding(task),"Current unchanged classification admission required")
    require(not (HERE/"outputs.json").exists(),"Classification attempt already sealed")
    history=read(REVIEW/"history.json")
    require(all(file_hash(ROOT/p)==h for p,h in history["protected"].items()),"Historical evidence changed")
    require(files(ROOT/"src/legalmath")==history["package"],"Production files changed")
    if (HERE/"reading-methods.json").exists():
        require(all(file_hash(ROOT/p)==h for p,h in read(HERE/"reading-methods.json").items()),"Frozen classification reading changed")
    return admitted


def prepare():
    units=[]
    docs=[]
    for graph,docid in ((ORIGINAL,"bes-2008-en"),(REPORT2009,"bes-report-2009")):
        product=load(graph)
        doc=next(d for d in product["payload"]["request"]["bundle"]["documents"] if d["id"]==docid)
        require(file_hash(ROOT/doc["path"])==doc["sha256"],"Original classification PDF changed")
        docs.append(doc)
        units.extend(u for u in product["payload"]["graph"]["units"] if u["document"]==docid and u["page"] in PAGES[docid])
    require(len(units)==830 and len({u["id"] for u in units})==830,"Exact830 document/page context required")
    save("source-units.json.gz",units)
    with (HERE/"native-source.txt").open("x") as stream:
        stream.write("\n".join(u["id"]+" "+u["raw"] for u in units)+"\n")
    links=[u for path,doc,page in ((PRIMARY2008,"bes-2008-en",72),(PRIMARY2009,"bes-report-2009",77))
        for u in read(path) if u["document"]==doc and u["page"]==page]
    require(links and {u["document"] for u in links}==set(PAGES),"Both retained primary balance sheets required")
    save("linked-primary-units.json.gz",links)
    baseline=load(PRIOR/"answer-supplement.json.gz")
    save("baseline-reference.json",{"path":str((PRIOR/"answer-supplement.json.gz").relative_to(ROOT)),
        "file_sha256":file_hash(PRIOR/"answer-supplement.json.gz"),"content_sha256":digest(baseline)})
    renderer=read(REVIEW/"history.json")["renderer"]
    for name,(docid,batches) in RENDERS.items():
        doc=next(d for d in docs if d["id"]==docid)
        specs=[]
        for first,last in batches:
            specs.append({"source":doc,"renderer":renderer,"pages":list(range(first,last+1)),
                "prefix":"classification-"+name+"-"+str(first),
                "argv":[renderer["path"],"-f",str(first),"-l",str(last),"-scale-to","1800","-gray","-png",str(ROOT/doc["path"]),str(HERE/("classification-"+name+"-"+str(first)))]})
        save("render-spec-"+name+".json",specs)
    return {"context_occurrences":830,"linked_primary_occurrences":len(links),"new_text_extractions":0,"large_answer_copies":0}


def render_group(name):
    images=[]
    for spec in read(HERE/("render-spec-"+name+".json")):
        require(file_hash(ROOT/spec["source"]["path"])==spec["source"]["sha256"] and
            file_hash(Path(spec["renderer"]["path"]))==spec["renderer"]["sha256"],"Source/renderer changed")
        with (HERE/(spec["prefix"]+".stdout")).open("xb") as out,(HERE/(spec["prefix"]+".stderr")).open("xb") as err:
            result=subprocess.run(spec["argv"],stdout=out,stderr=err,timeout=15,env=dict(os.environ))
        paths=sorted(HERE.glob(spec["prefix"]+"-*.png"))
        require(result.returncode==0 and [int(p.stem.split("-")[-1]) for p in paths]==spec["pages"],"Exact original classification images required")
        images.extend({"document":spec["source"]["id"],"page":int(p.stem.split("-")[-1]),"path":str(p.relative_to(ROOT)),"sha256":file_hash(p)} for p in paths)
    save("images-"+name+".json",images)
    if name=="notes09": save("images.json",[i for group in RENDERS for i in read(HERE/("images-"+group+".json"))])
    return {"rendered_pages":len(images),"render_children":len(read(HERE/("render-spec-"+name+".json")))}


def evaluator():
    spec=importlib.util.spec_from_file_location("original_asset_classification_reading",HERE/"reading.py")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(value,pin):
    require(digest(value)==pin,"Classification profile pin changed")
    require(value["version"]==SELECTOR["version"] and value["limits"]==LIMITS,"Classification authority/integration limits required")
    require(value["images"]==read(HERE/"images.json") and len(value["images"])==10 and
        all(file_hash(ROOT/i["path"])==i["sha256"] for i in value["images"]),"Exact ten original images required")
    require(value["baseline_reference"]==read(HERE/"baseline-reference.json") and
        file_hash(ROOT/value["baseline_reference"]["path"])==value["baseline_reference"]["file_sha256"],"Complete retained source06 answer required")
    require(value["EPS_composition_reference"]=={"path":str(EPS.relative_to(ROOT)),"sha256":file_hash(EPS)},"Completed EPS composition must be preserved")
    return evaluator().evaluate(load(HERE/"source-units.json.gz"),load(HERE/"linked-primary-units.json.gz"),value["reading"])


def profile():
    names=("reading.py","prepare-reading.py","SOURCE-REVIEW.md","IMPLEMENTATION-REVIEW.md","draft-profile.json")
    require(all((HERE/name).is_file() for name in names),"Full classification reading and actual image/implementation reviews required")
    paths=[Path(__file__),ROOT/PLAN,REVIEW/"REVIEW.md",HERE/"source-units.json.gz",HERE/"linked-primary-units.json.gz",HERE/"images.json",HERE/"baseline-reference.json"]+[HERE/name for name in names]
    save("reading-methods.json",{str(p.relative_to(ROOT)):file_hash(p) for p in paths})
    value=read(HERE/"draft-profile.json")
    analysis=validate(value,digest(value))
    cases=evaluator().CASES
    require(len(cases)>=24,"At least24 meaningful classification refusals required")
    save("profile.json",value)
    save("profile-pin.json",{"sha256":digest(value)})
    save("intended-refusals.json",cases)
    return {"reading_frozen":True,"intended_controls":len(cases),"section_occurrences":analysis["section_occurrences"]}


def answer():
    value=read(HERE/"profile.json")
    analysis=validate(value,read(HERE/"profile-pin.json")["sha256"])
    ref=read(HERE/"baseline-reference.json")
    baseline=load(ROOT/ref["path"])
    require(digest(baseline)==ref["content_sha256"],"Complete baseline content changed")
    unresolved={"BES-DEP-"+str(i).zfill(2) for i in range(1,12)}|{"BES-DEP-AGENCY-"+str(i).zfill(2) for i in range(1,4)}
    require({d["id"] for d in baseline["dependencies"] if d["id"] in unresolved and d["status"]=="UNRESOLVED"}==unresolved and baseline["questions"]["Q3"]["status"]=="PARTIAL","Original unresolved dependencies/Q3 required")
    eps=read(EPS)
    prior_eps=load(ROOT/eps["baseline"]["path"])
    eps_overlay=load(ROOT/eps["overlay"]["path"])
    require(all(file_hash(ROOT/r["path"])==r["file_sha256"] for r in (eps["baseline"],eps["overlay"])) and
        digest(prior_eps)==eps["baseline"]["content_sha256"] and digest(eps_overlay)==eps["overlay"]["content_sha256"] and
        not (set(prior_eps)&set(eps_overlay)) and digest({**prior_eps,**eps_overlay})==eps["complete_composed_answer_sha256"],"Complete original2008/EPS answer chain changed")
    overlay={"source_units":load(HERE/"source-units.json.gz"),"linked_primary_units":load(HERE/"linked-primary-units.json.gz"),
        "profile":value,"analysis":analysis,"limits":LIMITS,"EPS_composition_reference":value["EPS_composition_reference"]}
    require(KEY not in baseline,"Classification addition already present")
    combined={**baseline,KEY:overlay}
    require({k:combined[k] for k in baseline}==baseline,"Complete prior answer changed")
    save("answer-overlay.json.gz",{KEY:overlay})
    save("analysis.json",analysis)
    save("answer-composition.json",{"baseline":ref,"overlay":{"path":str((HERE/"answer-overlay.json.gz").relative_to(ROOT)),
        "file_sha256":file_hash(HERE/"answer-overlay.json.gz"),"content_sha256":digest({KEY:overlay})},
        "composition_rule":"Exact source06 baseline plus sole new overlay field; reject duplicate keys; original2008/EPS retained separately by its verified composition reference",
        "complete_composed_answer_sha256":digest(combined),"complete_prior_consumer_equal":True,
        "original2008_EPS_full_composition_verified":True,"materialized_in_memory":True,"large_answer_copies":0,
        "source_occurrences":830,"section_occurrences":446,"original_BES_dependencies_unresolved":14,"Q3":"PARTIAL"})
    return {"full_answer_composition_verified":True,"original2008_EPS_preserved":True,"new_large_answer_copies":0}


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
            require(str(exc)==reason,"Wrong classification semantic refusal: "+name+": "+str(exc))
            results.append(row)
        else: raise ValueError("Changed classification reading accepted: "+name)
    save("actual-controls.json",results)
    return {"actual_refusals":len(results),"repinned":len(results)}


def seal():
    require((HERE/"RESULT.md").is_file(),"Actual classification result required")
    controls=read(HERE/"actual-controls.json")
    expected=read(HERE/"intended-refusals.json")
    require(len(controls)==len(expected)>=24 and {r["case"] for r in controls}==set(expected) and
        all(r["refused"] and r["repinned"] and r["reason"]==expected[r["case"]] for r in controls),"All exact classification refusals required")
    save("verified-result.json",{**read(HERE/"answer-composition.json"),"actual_refusals":len(controls),"task_complete":False,"result_sha256":file_hash(HERE/"RESULT.md")})
    return {"conditional_classification_reading_retained":True,"task_complete":False}


def run(stage):
    with Authority(ROOT).lock():
        admitted=bindings()
        i=STAGES.index(stage)
        require({p.parent.name for p in (HERE/"stages").glob("*/started.json")}==
            {p.parent.name for p in (HERE/"stages").glob("*/result.json")}==set(STAGES[:i]),"Repeated/skipped/interrupted classification stage")
        rows=[read(HERE/"stages"/s/"result.json") for s in STAGES[:i]]
        require(all(r["status"]=="PASS" and r["wall_seconds"]<50 for r in rows),"Failed classification predecessor")
        spent=sum(r["wall_seconds"] for r in rows)
        before=storage()
        def within(now,elapsed=0):
            return spent+elapsed<180 and now["previous_seconds"]+spent+elapsed<1080 and \
                now["new_bytes"]<16*1024**2-256*1024 and now["combined_bytes"]<160*1024**2-1024**2
        require(within(before),"Cumulative classification bounds exhausted")
        save("stages/"+stage+"/started.json",{"command":["timeout","55",".venv/bin/python","-m","scripts.prospectus_2009_classification",stage],
            "at":datetime.now(timezone.utc).isoformat(),"git_commit":admitted["git_commit"],"python":sys.executable,
            "cpu_gpu":"CPU only; GPU devices intentionally hidden","random_seeds":"N/A deterministic source reading",
            "plan":PLAN,"data_version":[str(ORIGINAL.relative_to(ROOT)),str(REPORT2009.relative_to(ROOT))],"result":str((HERE/"RESULT.md").relative_to(ROOT))})
        tick,details,error=time.monotonic(),None,None
        def expire(signum,frame): raise TimeoutError("Classification cumulative bound; no retry")
        old=signal.signal(signal.SIGALRM,expire)
        signal.setitimer(signal.ITIMER_REAL,min(45,180-spent,1080-before["previous_seconds"]-spent))
        try:
            render=stage.startswith("render-")
            commands=[s["argv"] for s in read(HERE/("render-spec-"+stage[7:]+".json"))] if render else []
            with execution_guard(commands) as guard:
                details=render_group(stage[7:]) if render else globals()[stage]()
            require(guard.result()=={"starts":len(commands),"blocked":0},"Unexpected classification process/network action")
            details["process_guard"]=guard.result()
            bindings()
            require(time.monotonic()-tick<50 and within(storage(),time.monotonic()-tick),"Classification cumulative bound exceeded")
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
            save("result.json",{**result,"task":"source-bes-dep-06","task_complete":False,"whole_program_complete":False,"independent_legal_acceptance":False})
            save("outputs.json",files(HERE))
        print(json.dumps({k:result[k] for k in ("stage","status","error","wall_seconds","cumulative_seconds")}))
        return int(error is not None)


if __name__=="__main__": raise SystemExit(run(sys.argv[1]))
