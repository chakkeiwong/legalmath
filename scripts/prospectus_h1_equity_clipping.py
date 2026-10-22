"""One bounded original-PDF diagnosis of the retained page59 truncation."""
from collections import Counter
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTHONNOUSERSITE="1", PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts.prospectus_basf_pension_source import files, load, require
from scripts.prospectus_installed_profile_worker import execution_guard

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
HERE = BASE / "attempts/source-bes-dep-05/attempt-008"
PRIOR = HERE.parent / "attempt-007"
RISK = HERE.parent / "attempt-006"
REVIEW = BASE / "reviews/h1-equity-clipping-164"
PLAN = "docs/plans/prospectus-h1-equity-clipping-2026-10-16.md"
STAGES = ("prepare", "inspect", "analyze", "seal")
SELECTOR = {"version": "bes-h1-equity-clipping-diagnosis.v1", "stages": list(STAGES),
    "work_seconds": 110, "stage_seconds": 115, "execution_seconds": 360,
    "combined006_008_seconds": 1800, "combined006_008_bytes": 700 * 1024**2, "new_bytes": 32 * 1024**2,
    "source_parses": 1, "text_extractions": 1, "outer_children": 0, "renders": 0, "ocr_calls": 0,
    "network_calls": 0, "unchanged_retries": 0, "production_edits": 0}


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    with path.open("xb") as stream:
        stream.write(gzip.compress(raw, mtime=0) if path.suffix == ".gz" else raw+b"\n")


def storage():
    folders = [HERE, PRIOR, RISK]
    for folder in (PRIOR,RISK):
        if (folder/"workspace.json").is_file():
            folders.append(Path(read(folder/"workspace.json")["directory"]))
    return sum(p.stat().st_size for folder in folders for p in folder.rglob("*") if p.is_file())


def new_storage():
    return sum(p.stat().st_size for p in HERE.rglob("*") if p.is_file())


def parser_files():
    import pypdf
    return {str(p): file_hash(p) for p in Path(pypdf.__file__).parent.rglob("*.py")}


def bindings():
    authority = Authority(ROOT)
    program,tasks,_ = authority.spec()
    task=tasks["source-bes-dep-05"]
    admitted=read(HERE/"admission.json")
    event=next(e for e in reversed(authority.events()) if e.get("task")==task["id"])
    require(task.get("equity_clipping_diagnosis")==SELECTOR and event["kind"]=="ADMIT"
        and event["attempt"]==str(HERE.relative_to(ROOT)) and admitted["program_sha256"]==digest(program)
        and admitted["task_spec"]==task and admitted["binding"]==authority.binding(task), "Current unchanged clipping admission required")
    require(not (HERE/"outputs.json").exists(), "Clipping evidence already sealed")
    for name in ("protected-inputs.json","methods.json"):
        if (HERE/name).is_file():
            require(all(file_hash(ROOT/p)==h for p,h in read(HERE/name).items()), "Frozen clipping evidence/method changed")
    if (HERE/"parser-files.json").is_file():
        require(parser_files()==read(HERE/"parser-files.json"), "Pinned diagnostic parser changed")
    return admitted


def prepare():
    import pypdf
    history=read(REVIEW/"history.json")
    require(pypdf.__version__=="6.8.0" and parser_files()==history["parser_files"], "Inspected pypdf6.8.0 required")
    require(all(file_hash(ROOT/p)==h for p,h in history["protected"].items()), "Historical source/method evidence changed")
    save("protected-inputs.json",history["protected"])
    save("parser-files.json",history["parser_files"])
    paths=[Path(__file__),ROOT/PLAN,REVIEW/"REVIEW.md",REVIEW/"PARSER-REVIEW.md",REVIEW/"history.json",
        ROOT/"scripts/prospectus_basf_pension_source.py",ROOT/"scripts/prospectus_installed_profile_worker.py"]
    save("methods.json",{str(p.relative_to(ROOT)):file_hash(p) for p in paths})
    source=read(PRIOR/"rendered-source.json")["report"]
    require(file_hash(ROOT/source["path"])==source["sha256"], "Original H1 PDF changed")
    save("source.json",source)
    units=[u for u in read(PRIOR/"source-units.json") if u["page"]==59]
    require(len(units)==463, "Original463 equity occurrences required")
    save("original-page59-units.json",units)
    save("source-action-allowance.json",{"parses":1,"extract_text_calls":1,"renders_ocr_network_gpu":0})
    return {"parser_version":pypdf.__version__,"original_occurrences":463,"production_changes":0}


def inspect():
    import pypdf
    from pypdf.generic import ContentStream,IndirectObject,ByteStringObject,TextStringObject
    source=read(HERE/"source.json")
    save("source-action-started.json",{"parse":1,"extract_text":1,"page":59,"source_sha256":source["sha256"],
         "pdf_reader_strict":False,"mode":"plain","source_mutation":False})
    def serial(value):
        if isinstance(value,IndirectObject):
            return {"indirect":[value.idnum,value.generation]}
        if isinstance(value,ByteStringObject) or isinstance(value,bytes):
            return {"bytes_hex":bytes(value).hex()}
        if isinstance(value,TextStringObject):
            result={"decoded":str(value)}
            try: result["original_bytes_hex"]=value.original_bytes.hex()
            except Exception: result["original_bytes_available"]=False
            return result
        if isinstance(value,dict):
            return {str(k):serial(v) for k,v in value.items() if str(k) not in {"/Parent"}}
        if isinstance(value,(list,tuple)): return [serial(v) for v in value]
        if value is None or isinstance(value,(str,int,float,bool)): return value
        return str(value)
    with (HERE/"parser.log").open("x") as log,redirect_stdout(log),redirect_stderr(log):
        reader=pypdf.PdfReader(str(ROOT/source["path"]),strict=False)
        page=reader.pages[58]
        content=page.get_contents()
        require(content is not None, "Original page59 contents unavailable")
        raw=content.get_data()
        require(len(raw)<16*1024**2, "Original decoded page stream exceeds diagnostic bound")
        (HERE/"page59-decoded-content.bin").write_bytes(raw)
        save("page59-operators.json.gz",[{"index":i,"operator":op.decode("ascii"),"operands":serial(args)}
             for i,(args,op) in enumerate(content.operations)])
        forms,seen=[],set()
        def visit_forms(resources,parent,depth=0):
            require(depth<9, "Form nesting exceeds diagnostic bound")
            if not resources: return
            if hasattr(resources,"get_object"): resources=resources.get_object()
            xobjects=resources.get("/XObject",{})
            if hasattr(xobjects,"get_object"): xobjects=xobjects.get_object()
            for name,ref in xobjects.items():
                key=(ref.idnum,ref.generation) if isinstance(ref,IndirectObject) else (parent,str(name))
                if key in seen: continue
                seen.add(key)
                obj=ref.get_object()
                if obj.get("/Subtype")!="/Form": continue
                data=obj.get_data()
                require(len(data)<8*1024**2, "Form content exceeds diagnostic bound")
                index=len(forms)
                (HERE/("form-"+str(index)+".bin")).write_bytes(data)
                stream=ContentStream(obj,reader,"bytes")
                forms.append({"index":index,"name":str(name),"parent":parent,"reference":serial(ref),
                    "dictionary":serial(obj),"sha256":digest(data),
                    "operators":[{"index":i,"operator":op.decode("ascii"),"operands":serial(args)} for i,(args,op) in enumerate(stream.operations)]})
                visit_forms(obj.get("/Resources",resources),str(name),depth+1)
        visit_forms(page.get("/Resources"),"page59")
        save("forms.json.gz",forms)
        operands,texts=[],[]
        def before(op,args,cm,tm):
            operands.append({"index":len(operands),"operator":op.decode("ascii"),"operands":serial(args),
                "cm":list(cm),"tm":list(tm)})
        def text_callback(text,cm,tm,font,size):
            if text:
                texts.append({"index":len(texts),"text":text,"cm":list(cm),"tm":list(tm),
                    "font":None if font is None else {k:serial(font[k]) for k in ("/BaseFont","/Subtype","/Encoding") if k in font},
                    "size":size})
        text=page.extract_text(extraction_mode="plain",visitor_operand_before=before,visitor_text=text_callback)
        (HERE/"pypdf-page59.txt").write_text(text)
        save("visitor-operands.json.gz",operands)
        save("visitor-text.json.gz",texts)
        summary={"status":"INSPECTED","physical_page":59,"page_count":len(reader.pages),
            "media_box":list(page.mediabox),"crop_box":list(page.cropbox),"rotation":page.rotation,
            "page_dictionary":serial(page),"decoded_content_sha256":digest(raw),"decoded_bytes":len(raw),
            "operator_counts":dict(Counter(op.decode("ascii") for _,op in content.operations)),
            "forms":len(forms),"text_characters":len(text),"visitor_text_fragments":len(texts),
            "visitor_operator_callbacks":len(operands),"parser_version":pypdf.__version__,
            "source_sha256":source["sha256"],"pdf_reader_strict":False,"clip_aware_extraction":False,
            "financial_values_validated":False,"independent_legal_acceptance":False}
        save("inspection.json",summary)
    require(file_hash(ROOT/source["path"])==source["sha256"], "Original changed during parse")
    save("source-action-result.json",{"parses":1,"extract_text_calls":1,"renders_ocr_network_gpu":0,"source_unchanged":True})
    return {k:summary[k] for k in ("status","decoded_bytes","forms","text_characters","visitor_text_fragments")}


def analyze():
    result=read(HERE/"analysis.json")
    require((HERE/"SOURCE-ANALYSIS.md").is_file(), "Actual causal source analysis required")
    require(result["classification"] in {"ENCODED_CONTENT_BEYOND_CLIP","ENCODED_STRINGS_TRUNCATED","INCONCLUSIVE"}, "Explicit diagnostic classification required")
    require(result["financial_values_validated"] is False and result["automatic_recovery_complete"] is False, "Diagnostic cannot validate accounts or automatic recovery")
    require(result["evidence"] and all(file_hash(HERE/p)==h for p,h in result["evidence"].items()), "Bound actual analysis evidence required")
    require(read(HERE/"source-action-result.json")=={"parses":1,"extract_text_calls":1,"renders_ocr_network_gpu":0,"source_unchanged":True}, "Single source action required")
    save("verified-analysis.json",{**result,"source_analysis_sha256":file_hash(HERE/"SOURCE-ANALYSIS.md")})
    return {"classification":result["classification"],"diagnostic_only":True}


def seal():
    require((HERE/"RESULT.md").is_file() and (HERE/"verified-analysis.json").is_file(), "Actual clipping result required")
    return {"diagnosis_retained":True,"task_complete":False,"independent_legal_acceptance":False}


def run(stage):
    with Authority(ROOT).lock():
        admitted=bindings()
        index=STAGES.index(stage)
        started={p.parent.name for p in (HERE/"stages").glob("*/started.json")}
        finished={p.parent.name for p in (HERE/"stages").glob("*/result.json")}
        require(started==finished==set(STAGES[:index]), "Repeated, skipped or interrupted clipping stage")
        previous=sum(read(p/"result.json")["cumulative_seconds"] for p in (RISK,PRIOR))
        rows=[read(HERE/"stages"/s/"result.json") for s in STAGES[:index]]
        require(all(r["status"]=="PASS" and r["wall_seconds"]<115 for r in rows), "Failed clipping predecessor")
        spent=sum(r["wall_seconds"] for r in rows)
        require(spent<360 and previous+spent<1800 and storage()<698*1024**2 and new_storage()<31*1024**2, "Clipping cumulative allowance exhausted")
        save("stages/"+stage+"/started.json",{"command":["timeout","120",".venv/bin/python","-m","scripts.prospectus_h1_equity_clipping",stage],
            "at":datetime.now(timezone.utc).isoformat(),"git_commit":admitted["git_commit"],"python":sys.executable,
            "cpu_gpu":"CPU only; GPU devices intentionally hidden","random_seeds":"N/A deterministic PDF source diagnosis",
            "plan":PLAN,"data_version":str((PRIOR/"outputs.json").relative_to(ROOT)),"result":str((HERE/"RESULT.md").relative_to(ROOT))})
        tick,details,error=time.monotonic(),None,None
        def expire(signum,frame): raise TimeoutError("Clipping work limit;no unchanged retry")
        old=signal.signal(signal.SIGALRM,expire)
        signal.setitimer(signal.ITIMER_REAL,min(110,360-spent,1800-previous-spent))
        try:
            with execution_guard() as guard:
                details=globals()[stage]()
                require(guard.result()=={"starts":0,"blocked":0},"Unexpected clipping process/network action")
            details={**details,"process_guard":guard.result()}
            bindings()
            elapsed=time.monotonic()-tick
            require(elapsed<115 and spent+elapsed<360 and previous+spent+elapsed<1800,"Clipping time bound")
            require(storage()<698*1024**2 and new_storage()<31*1024**2,"Clipping storage bound")
        except BaseException as exc:
            error={"type":type(exc).__name__,"message":str(exc)}
            save("stages/"+stage+"/error.json",{"traceback":traceback.format_exc()})
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
            signal.signal(signal.SIGALRM,old)
        value={"stage":stage,"status":"FAIL" if error else "PASS","error":error,"details":details,
               "wall_seconds":time.monotonic()-tick,"retained_bytes006_008":storage(),"new_bytes":new_storage()}
        value["cumulative_seconds"]=spent+value["wall_seconds"]
        value["combined006_008_seconds"]=previous+value["cumulative_seconds"]
        save("stages/"+stage+"/result.json",value)
        if error or stage=="seal":
            save("result.json",{**value,"task":"source-bes-dep-05","task_complete":False,"whole_program_complete":False,
                "independent_legal_acceptance":False})
            save("outputs.json",files(HERE))
        print(json.dumps({k:value[k] for k in ("stage","status","error","wall_seconds","cumulative_seconds")}))
        return int(error is not None)


if __name__=="__main__":
    require(len(sys.argv)==2 and sys.argv[1] in STAGES,"Choose clipping prepare/inspect/analyze/seal")
    raise SystemExit(run(sys.argv[1]))
