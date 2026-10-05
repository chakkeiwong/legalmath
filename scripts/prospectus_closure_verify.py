"""Verify preserved history and current successor evidence without rewriting old results."""
import json,re,subprocess,sys
from pathlib import Path
from scripts import run_prospectus_closure_next as m
from scripts.prospectus_closure_runtime import verify_history
from scripts.prospectus_reviewed_extraction import load,norm

def require(ok,message):
    if not ok:raise ValueError(message)
def bindings(base,mapping):
    for name,digest in mapping.items():
        require(m.sha(base/name)==digest,"Changed evidence: "+str(base/name))
    return len(mapping)
def latest(phase,files):
    paths=sorted((m.OUT/"phases").glob("*-"+phase+"/receipt.json"))
    require(bool(paths),"Missing phase "+phase)
    path=paths[-1];value=m.read(path)
    require(value["status"]=="PASS","Latest "+phase+" did not pass")
    for name in files:
        require(value["method"][name]==m.sha(m.ROOT/name),"Stale "+phase+" method: "+name)
    return {"receipt":str(path.relative_to(m.ROOT)),"sha256":m.sha(path)}
def anchors(value):
    if isinstance(value,dict):
        if {"page","start","end","quote","text","text_sha256"}<=set(value):
            path=m.ROOT/value["text"];require(m.sha(path)==value["text_sha256"],"Anchor text changed")
            page=m.read(path)["pages"][value["page"]-1]
            require(norm(page["text"])[value["start"]:value["end"]]==value["quote"],"Anchor no longer replays")
        for child in value.values():anchors(child)
    elif isinstance(value,list):
        for child in value:anchors(child)
def run():
    original=m.ROOT/"docs/implementation/prospectus-corner-repair-2026-10-04"
    old=m.read(original/"run-manifest.json")
    counts={}
    for name in ("orchestration","inputs","artifacts"):
        counts[name]=bindings(m.ROOT,old[name])
    counts["candidate_method"]=bindings(original/"candidate",old["candidate_method"])
    state=m.read(original/"state.json")
    for phase in state["phases"]:
        receipt=m.ROOT/phase["receipt"]
        require(m.sha(receipt)==phase["sha256"],"Historical phase receipt changed")
        bindings(receipt.parent,m.read(receipt)["outputs"])
    counts["historical_phase_receipts"]=len(state["phases"])
    baseline=m.read(m.ROOT/"docs/implementation/prospectus-evidence-closure/baseline.json")
    counts["historical_baseline_files"]=bindings(m.ROOT,baseline["files"])
    require(not subprocess.check_output(["git","diff","--name-only","HEAD"],cwd=m.ROOT,text=True).strip(),
            "Previously tracked worktree file changed")
    metadata=m.read(m.DATA/"reviewed-extractions.json")
    for meta in metadata.values():load(meta,m.ROOT)
    previous=verify_history()
    accepted={
        "checks":latest("checks",["scripts/prospectus_reviewed_extraction.py","scripts/prospectus_closure_intake.py",
            "scripts/prospectus_closure_finance.py","tests/closure_next/test_reviewed_extraction.py","tests/closure_next/test_bes_finance.py"]),
        "validate":latest("validate",["scripts/prospectus_closure_validate.py","scripts/prospectus_closure_intake.py","scripts/prospectus_reviewed_extraction.py"]),
        "dossiers":latest("dossiers",["scripts/prospectus_closure_dossiers.py"]),
        "repairs":latest("repairs",["scripts/prospectus_closure_repairs.py","scripts/prospectus_closure_finance.py","scripts/prospectus_reviewed_extraction.py"]),
        "packet":latest("packet",["scripts/prospectus_closure_packet.py"]),
        "document":latest("document",["scripts/prospectus_closure_document.py"])}
    test=m.read(m.OUT/"closure-tests.json")
    require(test["exit_code"]==0 and test["log_sha256"]==m.sha(m.OUT/"closure-tests.log"),"Test record invalid")
    require("66 passed" in (m.OUT/"closure-tests.log").read_text(),"Unexpected test count")
    for name in ("dossier-review.json","repairs-results.json"):anchors(m.read(m.OUT/name))
    results=m.read(m.OUT/"validated-reader-results-v2.json")
    require(len(results)==7 and all(e["status"]=="TEXT_PRESENT" for r in results for e in r["extraction"]),"Extraction coverage failed")
    require(sum(r["answer"] is None for r in results)==5 and sum(r["answer"] is True for r in results)==2,"Unexpected reader comparison")
    packet=m.read(m.OUT/"packet-results.json")
    require(packet["scenario_forms"]==25 and packet["independent_adjudications"]==0,"Packet status misrepresented")
    for path in (m.OUT/"independent-review").glob("CC*.json"):
        require(m.read(path)["adjudication"]["status"]=="UNASSIGNED","Independent review forms changed; preserve separately")
    build=m.read(m.OUT/"document-build.json");pages=m.read(m.OUT/"addendum-pages.json");review=m.read(m.OUT/"rendered-review.json")
    require(build["tex_sha256"]==m.sha(m.OUT/"addendum.tex"),"Stale LaTeX build")
    require(build["pdf_sha256"]==pages["pdf_sha256"]==review["pdf_sha256"]==m.sha(m.OUT/"addendum.pdf"),"Stale rendered review")
    require(review["layout_status"]=="PASS" and review["human_prose_acceptance"]=="PENDING","Incorrect review scope")
    require(review["inspected_pages"]==[p["page"] for p in pages["pages"]],"Uninspected rendered pages")
    for p in pages["pages"]:require(m.sha(m.ROOT/p["image"])==p["sha256"],"Rendered page changed")
    for target in re.findall(r"\\href\{([^}]+)\}",(m.OUT/"addendum.tex").read_text()):
        require((m.OUT/target).resolve().is_file(),"Broken addendum link: "+target)
    language=m.read(m.DATA/"tools/language-receipt.json")
    require(language["request_count"]==1 and language["cumulative_requests"]==188 and language["exit_code"]==0,"Budget/model receipt mismatch")
    require(m.sha(m.DATA/"tools/eng.traineddata")==language["sha256"],"OCR model changed")
    result={"status":"PASS","preserved":counts,"prior_successor_receipts":previous,"reviewed_extractions":len(metadata),
        "focused_tests":66,"offering_inputs_with_text":7,"answers":{"abstain":5,"conditional_positive":2},
        "pdf_pages_inspected":len(pages["pages"]),"requests":{"total":188,"limit":212,"remaining":24},
        "independent_legal_adjudication":False,"production_promotion":False,
        "git_branch":subprocess.check_output(["git","branch","--show-current"],cwd=m.ROOT,text=True).strip()}
    m.write(m.OUT/"verification.json",result)
    method={str(p.relative_to(m.ROOT)):m.sha(p) for p in (m.ROOT/"scripts").glob("prospectus_closure_*.py")}
    for path in [m.ROOT/"scripts/run_prospectus_closure_next.py",m.ROOT/"scripts/prospectus_reviewed_extraction.py",*sorted((m.ROOT/"tests/closure_next").glob("*.py"))]:
        method[str(path.relative_to(m.ROOT))]=m.sha(path)
    artifacts={str(p.relative_to(m.ROOT)):m.sha(p) for p in m.OUT.rglob("*") if p.is_file()
        and "phases" not in p.relative_to(m.OUT).parts and p.name not in {".lock","run-manifest.json","NEXT-PHASE.md"}}
    manifest={"schema":"prospectus-closure-successor.v1","git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=m.ROOT,text=True).strip(),
        "command":".venv/bin/python scripts/run_prospectus_closure_next.py verify",
        "python":sys.executable,"python_version":sys.version,"ocr_runtime":m.TEXTPY,
        "compute":"CPU only; CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden","seeds":"N/A deterministic",
        "plan":"docs/plans/prospectus-closure-execution-2026-10-05.md","plan_sha256":m.sha(m.ROOT/"docs/plans/prospectus-closure-execution-2026-10-05.md"),
        "result":str((m.OUT/"REPORT.md").relative_to(m.ROOT)),"method":method,
        "data":{str(p.relative_to(m.ROOT)):m.sha(p) for p in m.DATA.rglob("*") if p.is_file()},
        "accepted_evaluations":accepted,"artifacts":artifacts,
        "preserved_manifest":{"path":str((original/"run-manifest.json").relative_to(m.ROOT)),"sha256":m.sha(original/"run-manifest.json")},
        "human_acceptance":"PENDING","legal_adjudication":"PENDING","production_promotion":False}
    m.write(m.OUT/"run-manifest.json",manifest)
    print(json.dumps(result,indent=2))
