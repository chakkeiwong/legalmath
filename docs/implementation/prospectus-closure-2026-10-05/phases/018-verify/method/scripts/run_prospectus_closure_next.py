"""Bounded tooling and source inventory for the next prospectus closure."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT/"docs/implementation/prospectus-closure-2026-10-05"
DATA=ROOT/"docs/prospectus/closure-2026-10-05"
RA=Path("/home/chakwong/python/ResearchAssistant")
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
os.environ["OMP_THREAD_LIMIT"]="1"
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,data):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
def tools():
    bins=[Path(p) for p in os.environ.get("PATH","").split(os.pathsep) if p]
    for base in (RA,ROOT):
        bins += [base/".venv/bin",base/"venv/bin"]
    bins += list(Path("/home/chakwong/miniconda3/envs").glob("*/bin"))
    bins += list(Path("/tmp").glob("*ocr*/bin"))+list(Path("/tmp").glob("*marker*/bin"))
    names=("tesseract","ocrmypdf","pdftotext","pdftoppm","marker_single","magic-pdf","mineru","ra")
    found={name:sorted({str(p/name) for p in bins if (p/name).is_file()}) for name in names}
    versions={}
    for name in ("tesseract","pdftotext"):
        if found[name]:
            run=subprocess.run([found[name][0],"--version" if name=="tesseract" else "-v"],capture_output=True,text=True,timeout=15)
            versions[name]=(run.stdout+run.stderr)[:3000]
    if found["tesseract"]:
        run=subprocess.run([found["tesseract"][0],"--list-langs"],capture_output=True,text=True,timeout=15)
        versions["languages"]=(run.stdout+run.stderr)[:3000]
    sys.path.insert(0,str(RA/"src"))
    from research_assistant.ingest.parser_preflight import check_command
    ra_checks=[check_command(name,cmd).to_dict() for name,cmd in
               (("pdftotext","pdftotext"),("marker","marker_single"),("mineru","magic-pdf"))]
    result={"at":datetime.now(timezone.utc).isoformat(),"git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "python":sys.executable,"python_version":sys.version,"compute":"CPU only; CUDA_VISIBLE_DEVICES=-1; no GPU probe",
        "research_assistant":str(RA),"ra_preflight":ra_checks,"ra_preflight_sha256":sha(RA/"src/research_assistant/ingest/parser_preflight.py"),
        "executables":found,"versions":versions,"fitz_available":importlib.util.find_spec("fitz") is not None}
    write(OUT/"tooling.json",result)
    print(json.dumps(result,indent=2))
def inventory():
    old=ROOT/"docs/implementation/prospectus-corner-repair-2026-10-04/phases/016-intake"
    extracts=read(old/"extraction.json")
    bundles=read(old/"bes-bundles.json")
    docs=bundles["documents"]
    result={"extraction":[{"id":r["id"],"status":r["status"],"empty_pages":r["empty_selected_pages"],
                           "page_count":len(r["selected_pages"])} for r in extracts],
        "bes_documents":[{"key":k,"pages":r.get("pages"),"original":r["original"],"sha256":r["sha256"],
                          "edition_date":r["edition_date"],"role":r["role"],
                          "intact":sha(ROOT/r["original"])==r["sha256"]} for k,r in docs.items()],
        "bes_issues":bundles["issues"]}
    assert all(r["intact"] for r in result["bes_documents"])
    write(OUT/"inventory.json",result)
    print(json.dumps({k:v for k,v in result.items() if k!="bes_issues"},ensure_ascii=False,indent=2))

TEXTPY="/home/chakwong/miniconda3/envs/tfgpu/bin/python"
def language():
    import time
    folder=DATA/"tools";folder.mkdir(parents=True,exist_ok=True)
    path=folder/"eng.traineddata"
    receipt=folder/"language-receipt.json"
    if receipt.exists():
        record=read(receipt);assert sha(path)==record["sha256"]
        print(json.dumps(record,indent=2));return
    url="https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/eng.traineddata"
    start=time.monotonic()
    cmd=["curl","--silent","--show-error","--fail","--max-time","45","--max-redirs","0",
         "--output",str(path),"--dump-header",str(folder/"headers.txt"),
         "--write-out","%{http_code}",url]
    run=subprocess.run(cmd,capture_output=True,text=True,timeout=50)
    record={"url":url,"command":cmd,"at":datetime.now(timezone.utc).isoformat(),
            "exit_code":run.returncode,"http_status":run.stdout,"stderr":run.stderr,
            "wall_seconds":round(time.monotonic()-start,3),"request_count":1,
            "prior_requests":187,"cumulative_requests":188,
            "sha256":sha(path) if path.exists() else None,"bytes":path.stat().st_size if path.exists() else 0,
            "purpose":"Official Tesseract English OCR model; no executable package installation"}
    write(receipt,record)
    assert run.returncode==0 and 1000000<path.stat().st_size<20000000,record
    print(json.dumps(record,indent=2))
def smoke():
    cmd=[TEXTPY,str(ROOT/"scripts/prospectus_closure_pdf_worker.py"),"jur-more-bes-1315263","1","smoke"]
    run=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=90)
    (OUT/"ocr-smoke.log").write_text(run.stdout+run.stderr)
    print(run.stdout+run.stderr)
    assert run.returncode==0
def ocr():
    for key,pages,mode in [
        ("jur-more-bes-1315263","1,2,3,4,5,6","ocr"),
        ("jur-more-bes-1922255","1,2,3,4,5,6","ocr"),
        ("jur-bes-2014-ptbeqkom0019","1,2,3,4,5","ocr"),
        ("jur-more-bes-1217215","287","render")]:
        cmd=[TEXTPY,str(ROOT/"scripts/prospectus_closure_pdf_worker.py"),key,pages,mode]
        run=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=240)
        (OUT/(key+"-ocr.log")).write_text(run.stdout+run.stderr)
        print(run.stdout+run.stderr,flush=True)
        assert run.returncode==0,key
def execute(phase):
    import fcntl,time
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/".lock").open("a+") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        phases=OUT/"phases";phases.mkdir(exist_ok=True)
        from scripts.prospectus_closure_runtime import verify_history, snapshot, method_snapshot, refresh
        historical_receipts=verify_history()
        number=max([int(p.name.split('-')[0]) for p in phases.iterdir() if p.is_dir()]+[0])+1
        folder=phases/f"{number:03d}-{phase}";folder.mkdir()
        start=time.monotonic()
        receipt={"phase":phase,"started":datetime.now(timezone.utc).isoformat(),
                 "command":[sys.executable,*sys.argv],"git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                 "driver_sha256":sha(__file__),"plan_sha256":sha(ROOT/"docs/plans/prospectus-closure-execution-2026-10-05.md"),
                 "python":sys.executable,"compute":"CPU only; CUDA_VISIBLE_DEVICES=-1","seeds":"N/A deterministic"}
        receipt["verified_prior_receipts"]=historical_receipts
        receipt["method"]=method_snapshot(folder)
        snapshot(folder,"before")
        try:
            globals()[phase]()
            receipt["status"]="PASS"
        except Exception as exc:
            receipt.update(status="FAIL",error=type(exc).__name__+": "+str(exc))
            raise
        finally:
            receipt["wall_seconds"]=round(time.monotonic()-start,3)
            snapshot(folder,"artifacts")
            receipt["outputs"]={str(p.relative_to(folder)):sha(p) for p in folder.rglob("*") if p.is_file()}
            receipt["data"]={str(p.relative_to(ROOT)):sha(p) for p in DATA.rglob("*") if p.is_file()}
            write(folder/"receipt.json",receipt)
            refresh(folder,receipt)


def review():
    from scripts.prospectus_closure_review import run
    run()
def validate():
    from scripts.prospectus_closure_validate import run
    run()
def dossiers():
    from scripts.prospectus_closure_dossiers import run
    run()

def checks():
    cmd=[sys.executable,"-m","pytest","-q","tests/closure_next"]
    run=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=180)
    (OUT/"closure-tests.log").write_text(run.stdout+run.stderr)
    write(OUT/"closure-tests.json",{"command":cmd,"exit_code":run.returncode,"log_sha256":sha(OUT/"closure-tests.log")})
    print(run.stdout+run.stderr)
    if run.returncode:raise ValueError("Closure regression failure")
def repairs():
    from scripts.prospectus_closure_repairs import run
    run()
def packet():
    from scripts.prospectus_closure_packet import run
    run()
def verify():
    from scripts.prospectus_closure_verify import run
    run()
def document():
    from scripts.prospectus_closure_document import run
    run()

def main():
    if len(sys.argv)>2 and sys.argv[1]=="inspect":
        from scripts.prospectus_closure_inspect import main as inspect
        inspect(sys.argv[2:]);return
    if len(sys.argv)==3 and sys.argv[1]=="image":
        import base64
        path=(ROOT/sys.argv[2]).resolve()
        assert (path.is_relative_to(DATA.resolve()) or path.is_relative_to((OUT/"addendum-pages").resolve())) and path.suffix==".png" and path.is_file()
        print(base64.b64encode(path.read_bytes()).decode());return
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("phase",choices=("tools","inventory","language","smoke","ocr","review","validate","dossiers","checks","repairs","packet","document","verify"));a=p.parse_args()
    execute(a.phase)
if __name__=="__main__":main()
