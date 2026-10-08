"""Reproducible diagnostics on retained originals; legal specifications are not engine passes."""
from pathlib import Path
from collections import Counter
import argparse, fcntl, hashlib, json, os, platform, re, signal, subprocess, sys, tempfile, time
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from scripts import prospectus_corner_cases as c
from legalmath.prospectus.loss_absorption_reader import analyze_issue, load_document, quote_valid
DATA,OUT=c.DATA,c.OUT
PLAN=ROOT/"docs/plans/prospectus-corner-cases-2026-10-04.md"
def norm(text):return re.sub(r"\s+"," ",text).strip()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def audit():
    original=c.j.read(ROOT/"docs/prospectus/difficulty-2026-10-04/freeze.json")
    for name,value in original["method"].items():
        assert c.j.sha(ROOT/name)==value,("Frozen method changed",name)
    assert c.j.sha(ROOT/"docs/prospectus/difficulty-2026-10-04/method.zip")==original["archive_sha256"]
    sources={r["key"]:r for r in c.j.read(DATA/"source-index.json")["sources"]}
    specs=c.j.read(OUT/"test-specifications.json")["cases"]
    assert len(specs)==30 and len({r["id"] for r in specs})==30
    manual={r["key"]:r for r in c.j.read(DATA/"manual-transcriptions.json")["sources"]}
    catalogue=c.j.read(OUT/"reviewed-catalogue.json")
    for source in catalogue["sources"]:
        assert source["sha256"]==sources[source["key"]]["sha256"]
        assert c.j.sha(ROOT/source["original"])==source["sha256"]
        assert c.j.sha(ROOT/source["receipt"])==source["receipt_sha256"]
        assert c.j.sha(ROOT/source["text"])==source["text_sha256"]
    anchors=0
    for row in specs:
        assert row["expected"] and row["forbidden_inference"] and row["anchors"]
        assert row["independent_adjudication"] is False and row["observed_legal_outcome"] is None
        for a in row["anchors"]:
            source=sources[a["source_key"]]
            assert source["status"]=="RETAINED" and source["sha256"]==a["source_sha256"]
            if a["method"]=="rendered_transcription":
                m=manual[source["key"]]
                assert m["sha256"]==source["sha256"]
                assert any(f["page"]==a["page"] and f["quote"]==a["quote"] for f in m["fields"])
                assert (OUT/"source-render"/source["key"]/f"page-{a['page']:03d}.png").exists()
            elif "page" in a:
                pages=c.j.read(DATA/"sources"/source["key"]/"pages.json")["pages"]
                assert norm(a["quote"]) in norm(pages[a["page"]-1]["text"]),(row["id"],a)
            else:
                text=(ROOT/source["text"]).read_text()
                parts=re.split(r"\n(?=\d+\n)",text)
                paragraphs={p.split("\n",1)[0]:p.split("\n",1)[1] for p in parts if re.match(r"^\d+\n",p)}
                assert norm(a["quote"]) in norm(paragraphs[str(a["paragraph"])]),(row["id"],a)
            anchors+=1
    selection=c.j.read(DATA/"reader-selection.json")
    offerings=selection["offering_documents"]
    assert len(offerings)==7 and len({sources[r["source_key"]]["sha256"] for r in offerings})==7
    assert all(r["role"] in ("final_terms","base_prospectus","prospectus") for r in offerings)
    assert all(sources[r["source_key"]]["media"]=="pdf" for r in offerings)
    assert len(c.j.receipts())<=212
    return {"status":"PASS","specifications":len(specs),"anchors_checked":anchors,"offering_pdfs":len(offerings),
            "frozen_method_files":len(original["method"]),"independent_legal_adjudication":False},sources,selection,original
def analyze():
    checked,sources,selection,original=audit()
    inputs={str(p.relative_to(ROOT)):c.j.sha(p) for p in [
        Path(__file__),DATA/"reader-selection.json",DATA/"source-index.json",DATA/"manual-transcriptions.json",
        OUT/"test-specifications.json",OUT/"reviewed-catalogue.json",PLAN]}
    binding=digest({"inputs":inputs,"method":original["method"]})
    target=OUT/"run-001";freeze=DATA/"reader-freeze.json"
    if freeze.exists():assert c.j.read(freeze)["binding"]==binding,"Frozen inputs changed"
    else:c.j.write(freeze,{"binding":binding,"at":c.j.now(),"inputs":inputs})
    if target.exists():
        result=verify()
        return {"status":"RETAINED","verification":result}
    began=c.j.now();tick=time.monotonic()
    rows=[]
    with tempfile.TemporaryDirectory(prefix=".corner-run-",dir=OUT) as name:
        staging=Path(name);(staging/"extractions").mkdir()
        metadata={}
        for source_key in {r["source_key"] for r in selection["offering_documents"]}:
            s=sources[source_key];pages=c.j.read(DATA/"sources"/source_key/"pages.json")["pages"]
            extraction=staging/"extractions"/(source_key+".json")
            c.j.write(extraction,{"source_sha256":s["sha256"],"pages":pages})
            metadata[source_key]={"id":source_key,"original":s["original"],"sha256":s["sha256"],"pages":s["pages"],
                                  "text":str(extraction.relative_to(ROOT)),"text_sha256":c.j.sha(extraction)}
        for mode,cases in [("whole_document",selection["offering_documents"]),("clause_probe",selection["probes"])]:
            for case in cases:
                key=case["source_key"];meta=metadata[key]
                selected={"id":key,"operative_pages":case.get("operative_pages",[[1,meta["pages"]]]),
                          "scope_basis":case.get("scope_basis","Whole-PDF diagnostic; series, dependencies and external law not adjudicated")}
                issue={k:case[k] for k in ("id","issuer","title","identifiers") if k in case}
                issue.update(security_type="debt",documents=[selected])
                row={"id":case["id"],"source_key":key,"mode":mode,"source_sha256":meta["sha256"],
                     "extraction_status":sources[key]["extraction_status"],"empty_pages":sources[key]["empty_text_pages"],
                     "issue_answer_certified":False}
                start=time.monotonic()
                def expired(*args):raise TimeoutError("60-second per-input limit")
                prior=signal.signal(signal.SIGALRM,expired);signal.alarm(60)
                try:
                    result=analyze_issue(issue,{key:meta},ROOT)
                    document=load_document(meta,ROOT)
                    assert all(quote_valid(e,document) for e in result["evidence"]),"Evidence span/hash mismatch"
                    assert result["certified_legal_answer"] is None
                    c.j.write(staging/(case["id"]+".json"),result)
                    unresolved=[e for e in result["evidence"] if e["disposition"].startswith("unresolved")]
                    row.update(status="ABSTAIN" if result["answer"] is None else "CONDITIONAL_READING",
                               answer=result["answer"],facts=result["facts"],unresolved_clauses=len(unresolved),
                               unresolved_dispositions=dict(Counter(e["disposition"] for e in unresolved)),
                               derivation_check=result.get("derivation_check"),evidence_count=len(result["evidence"]),
                               open_issues=result["open_issues"])
                except Exception as exc:
                    row.update(status="ENGINE_ERROR",reason=type(exc).__name__+": "+str(exc))
                finally:
                    signal.alarm(0);signal.signal(signal.SIGALRM,prior)
                row["wall_seconds"]=round(time.monotonic()-start,4);rows.append(row)
                print(json.dumps({k:row.get(k) for k in ("id","mode","status","answer","unresolved_clauses")}),flush=True)
        # Extraction paths were temporary inputs; rewrite metadata paths to their final location.
        for meta in metadata.values():meta["text"]=str((target/"extractions"/Path(meta["text"]).name).relative_to(ROOT))
        c.j.write(staging/"reader-documents.json",metadata)
        whole=[r for r in rows if r["mode"]=="whole_document"]
        summary={"engineering_status":"FAIL" if any(r["status"]=="ENGINE_ERROR" for r in rows) else "PASS",
                 "whole_documents":len(whole),"whole_statuses":dict(Counter(r["status"] for r in whole)),
                 "whole_answers":dict(Counter(str(r.get("answer")) for r in whole)),
                 "whole_unresolved_clauses":sum(r.get("unresolved_clauses",0) for r in whole),
                 "clause_probes":len(rows)-len(whole),"cases":rows,"specification_count":30,
                 "legal_specifications_passed":"NOT_MEASURED","population_accuracy":"NOT_ESTABLISHED",
                 "method_changed":False,"may_execute_transaction":False}
        c.j.write(staging/"summary.json",summary)
        outputs={str(p.relative_to(staging)):c.j.sha(p) for p in staging.rglob("*") if p.is_file()}
        commit=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
        branch=subprocess.run(["git","branch","--show-current"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
        c.j.write(staging/"manifest.json",{"binding":binding,"inputs":inputs,"outputs":outputs,"started_at":began,
            "finished_at":c.j.now(),"wall_seconds":round(time.monotonic()-tick,3),
            "command":"python3 -m scripts.run_prospectus_corner_tests analyze","git_commit":commit,"branch":branch,
            "python_executable":sys.executable,"python":sys.version,"platform":platform.platform(),
            "compute":"CPU only; CUDA_VISIBLE_DEVICES=-1; no framework import or device probe",
            "seeds":"N/A deterministic","data_version":c.j.sha(DATA/"source-index.json"),
            "plan":str(PLAN.relative_to(ROOT)),"result":str((OUT/"REPORT.md").relative_to(ROOT)),
            "global_requests":len(c.j.receipts()),"new_requests":len(c.j.receipts())-112})
        staging.rename(target)
    return {k:v for k,v in summary.items() if k!="cases"}
def verify():
    checked,sources,selection,original=audit()
    path=OUT/"run-001"
    if path.exists():
        manifest=c.j.read(path/"manifest.json")
        assert manifest["binding"]==c.j.read(DATA/"reader-freeze.json")["binding"]
        for name,value in manifest["inputs"].items():assert c.j.sha(ROOT/name)==value,("Input changed",name)
        for name,value in manifest["outputs"].items():assert c.j.sha(path/name)==value,("Output changed",name)
        summary=c.j.read(path/"summary.json")
        checked["engine_execution"]=summary["engineering_status"]
        checked["legal_specifications_passed"]="NOT_MEASURED"
        checked["result_files_verified"]=len(manifest["outputs"])
    checked.update(global_requests=len(c.j.receipts()),new_requests=len(c.j.receipts())-112,remaining=212-len(c.j.receipts()))
    c.j.write(OUT/"verification.json",checked)
    return checked
def main():
    p=argparse.ArgumentParser();p.add_argument("action",choices=("audit","analyze","verify"));a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    with (ROOT/"docs/implementation/prospectus-evidence-closure/.lock").open("a+") as stream:
        fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result=audit()[0] if a.action=="audit" else globals()[a.action]()
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
