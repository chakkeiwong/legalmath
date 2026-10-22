"""One bounded reference-retention repair for the sealed2008 summary candidate."""
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import signal
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
from scripts import prospectus_2008_presentation as original

BASE=ROOT/"docs/implementation/prospectus-execution-authority"
HERE=BASE/"attempts/source-bes-dep-07/attempt-006"
PREVIOUS=tuple(HERE.parent/("attempt-00"+str(i)) for i in (3,4,5))
PRIOR=PREVIOUS[1]
CANDIDATE=PREVIOUS[2]
REVIEW=BASE/"reviews/2008-summary-retention-178"
PLAN="docs/plans/prospectus-2008-summary-retention-repair-2026-10-17.md"
STAGES=("verify","controls","seal")
SELECTOR={"version":"bes-2008-summary-retention-repair.v1","stages":list(STAGES),
    "source_occurrences":506,"controls":43,"new_seconds":120,"combined003_006_seconds":1080,
    "new_bytes":2*1024**2,"combined003_006_bytes":160*1024**2,
    "new_reserve_bytes":128*1024,"combined_reserve_bytes":256*1024,
    "work_seconds":60,"stage_seconds":65,"new_process_calls":0,"maximum_repair_attempts":1}


def save(name,value):
    p=HERE/name
    p.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()
    with p.open("xb") as stream: stream.write(gzip.compress(raw,mtime=0) if p.suffix==".gz" else raw+b"\n")


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
        task.get("presentation_retention_repair")==SELECTOR and admitted["task_spec"]==task and
        admitted["program_sha256"]==digest(program) and admitted["binding"]==a.binding(task),"Current unchanged retention-repair admission required")
    require(not (HERE/"outputs.json").exists(),"Retention repair already sealed")
    history=read(REVIEW/"history.json")
    require(all(file_hash(ROOT/p)==h for p,h in history["protected"].items()),"Historical evidence changed")
    require(files(ROOT/"src/legalmath")==history["package"],"Production files changed")
    require(all(file_hash(ROOT/p)==h for p,h in read(CANDIDATE/"reading-methods.json").items()),"Frozen source reading changed")
    require(read(CANDIDATE/"result.json")["status"]=="FAIL","Original005 failure must remain")
    return admitted


def reference(path,value=None):
    return {"path":str(path.relative_to(ROOT)),"file_sha256":file_hash(path),"bytes":path.stat().st_size,
        **({"content_sha256":digest(value)} if value is not None else {})}


def verify():
    value=read(CANDIDATE/"profile.json")
    analysis=original.validate(value,read(CANDIDATE/"profile-pin.json")["sha256"])
    analysis["limits"]=original.LIMITS
    prior=load(PRIOR/"answer-supplement.json.gz")
    candidate=load(CANDIDATE/"answer-supplement.json.gz")
    key="original2008_summary_statement_agent_reading"
    require(set(candidate)==set(prior)|{key} and {k:candidate[k] for k in prior}==prior,"Whole original004 answer changed")
    require(candidate[key]=={"source_units":read(CANDIDATE/"source-units.json"),"profile":value,"analysis":analysis},"Complete saved005 supplement differs from frozen reading")
    require(read(CANDIDATE/"analysis.json")==analysis,"Saved005 analysis differs")
    require(len(original.evaluator().CASES)==43 and read(CANDIDATE/"intended-refusals.json")==original.evaluator().CASES,"Frozen43 intended controls required")
    unresolved={"BES-DEP-"+str(i).zfill(2) for i in range(1,12)}|{"BES-DEP-AGENCY-"+str(i).zfill(2) for i in range(1,4)}
    require({d["id"] for d in candidate["dependencies"] if d["id"] in unresolved and d["status"]=="UNRESOLVED"}==unresolved,"All14 original dependencies must remain unresolved")
    require(candidate["questions"]["Q3"]["status"]=="PARTIAL","Q3 partial status changed")
    save("verified-answer-reference.json",{"baseline":reference(PRIOR/"answer-supplement.json.gz",prior),
        "candidate":reference(CANDIDATE/"answer-supplement.json.gz",candidate),"analysis":reference(CANDIDATE/"analysis.json",analysis),
        "complete_prior_consumer_equal":True,"complete_saved_supplement_equal":True,
        "new_answer_copies":0,"original005_resource_failure_reversed":False,"source_occurrences":506})
    return {"whole_prior_equal":True,"whole_saved_supplement_equal":True,"new_answer_copies":0}


def controls():
    value=read(CANDIDATE/"profile.json")
    method=original.evaluator()
    results=[]
    for name,reason in read(CANDIDATE/"intended-refusals.json").items():
        bad=method.altered(value,name)
        pin=digest(bad)
        save("adverse-inputs/"+name+".json.gz",{"profile":bad,"expected_pin":pin})
        try: original.validate(bad,pin)
        except ValueError as exc:
            row={"case":name,"refused":True,"repinned":True,"reason":str(exc)}
            save("adverse-results/"+name+".json",row)
            require(str(exc)==reason,"Wrong repaired-summary refusal: "+name+": "+str(exc))
            results.append(row)
        else: raise ValueError("Changed summary reading accepted: "+name)
    save("actual-controls.json",results)
    return {"actual_refusals":len(results),"repinned":len(results)}


def seal():
    require((HERE/"RESULT.md").is_file(),"Actual retention-repair result required")
    controls=read(HERE/"actual-controls.json")
    expected=read(CANDIDATE/"intended-refusals.json")
    require(len(controls)==43 and {r["case"] for r in controls}==set(expected) and
        all(r["refused"] is True and r["repinned"] is True and r["reason"]==expected[r["case"]] for r in controls),"All43 actual refusals required")
    save("verified-result.json",{**read(HERE/"verified-answer-reference.json"),"actual_refusals":43,
        "task_complete":False,"result_sha256":file_hash(HERE/"RESULT.md")})
    return {"summary_reading_verified_by_reference":True,"task_complete":False}


def run(stage):
    with Authority(ROOT).lock():
        admitted=bindings()
        i=STAGES.index(stage)
        require({p.parent.name for p in (HERE/"stages").glob("*/started.json")}==
            {p.parent.name for p in (HERE/"stages").glob("*/result.json")}==set(STAGES[:i]),"Repeated/skipped/interrupted repair stage")
        rows=[read(HERE/"stages"/s/"result.json") for s in STAGES[:i]]
        require(all(r["status"]=="PASS" and r["wall_seconds"]<65 for r in rows),"Failed repair predecessor")
        spent=sum(r["wall_seconds"] for r in rows)
        before=storage()
        def within(now,elapsed=0):
            return spent+elapsed<120 and now["previous_seconds"]+spent+elapsed<1080 and \
                now["new_bytes"]<2*1024**2-128*1024 and now["combined_bytes"]<160*1024**2-256*1024
        require(within(before),"Retention-repair cumulative bounds exhausted")
        save("stages/"+stage+"/started.json",{"command":["timeout","70",".venv/bin/python","-m","scripts.prospectus_2008_summary_retention",stage],
            "at":datetime.now(timezone.utc).isoformat(),"git_commit":admitted["git_commit"],"python":sys.executable,
            "cpu_gpu":"CPU only; GPU devices intentionally hidden","random_seeds":"N/A deterministic source reading",
            "plan":PLAN,"data_version":str(CANDIDATE.relative_to(ROOT)),"result":str((HERE/"RESULT.md").relative_to(ROOT))})
        tick,details,error=time.monotonic(),None,None
        def expire(signum,frame): raise TimeoutError("Retention repair bound; no retry")
        old=signal.signal(signal.SIGALRM,expire)
        signal.setitimer(signal.ITIMER_REAL,min(60,120-spent,1080-before["previous_seconds"]-spent))
        try:
            with execution_guard([]) as guard: details=globals()[stage]()
            require(guard.result()=={"starts":0,"blocked":0},"Unexpected repair process/network action")
            details["process_guard"]=guard.result()
            bindings()
            elapsed=time.monotonic()-tick
            require(elapsed<65 and within(storage(),elapsed),"Retention repair bound exceeded")
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
            save("result.json",{**result,"task":"source-bes-dep-07","task_complete":False,
                "whole_program_complete":False,"independent_legal_acceptance":False})
            save("outputs.json",files(HERE))
        print(json.dumps({k:result[k] for k in ("stage","status","error","wall_seconds","cumulative_seconds")}))
        return int(error is not None)


if __name__=="__main__": raise SystemExit(run(sys.argv[1]))
