"""Audited public acquisition for the 100-request prospectus corner-case extension."""
from pathlib import Path
import argparse, fcntl, json, re, shutil
from html.parser import HTMLParser
from urllib.parse import urljoin
from scripts import prospectus_jurisdiction_study as j
ROOT=j.ROOT
DATA=ROOT/"docs/prospectus/corner-cases-2026-10-04"
OUT=ROOT/"docs/implementation/prospectus-corner-cases-2026-10-04"
j.DATA=DATA
j.OUT=OUT
class Links(HTMLParser):
    def __init__(self,base):super().__init__();self.base=base;self.links=[]
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key=="href" and value:self.links.append(urljoin(self.base,value))
def snapshot():
    target=OUT/"baseline";target.mkdir(parents=True,exist_ok=True)
    names=["docs/monograph/chapters/02e-prospectus-difficulty.tex","docs/monograph/appendices/prospectus-difficulty.tex",
           "docs/monograph/monograph.pdf","docs/monograph/technical-companion.pdf",
           "scripts/prospectus_jurisdiction_study.py"]
    manifest=target/"manifest.json"
    if not manifest.exists():
        rows=[]
        for name in names:
            source=ROOT/name;dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,dest);rows.append({"path":name,"copy":j.rel(dest),"sha256":j.sha(source)})
        j.write(manifest,{"at":j.now(),"files":rows})
    for row in j.read(manifest)["files"]:assert j.sha(ROOT/row["copy"])==row["sha256"]
    return {"status":"PASS","baseline":j.rel(manifest),"files":len(names)}
def verify():
    frozen=j.read(ROOT/"docs/prospectus/difficulty-2026-10-04/freeze.json")
    for p,digest in frozen["method"].items():assert j.sha(ROOT/p)==digest,p
    sources=j.read(DATA/"source-index.json")["sources"] if (DATA/"source-index.json").exists() else []
    for row in sources:
        assert j.sha(ROOT/row["original"])==row["sha256"]
        assert j.sha(ROOT/row["receipt"])==row["receipt_sha256"]
        if "text" in row:assert j.sha(ROOT/row["text"])==row["text_sha256"]
    result={"status":"PASS","at":j.now(),"global_requests":len(j.receipts()),"remaining":212-len(j.receipts()),
            "source_records":len(sources),"pdfs":sum(r["media"]=="pdf" and r["status"]=="RETAINED" for r in sources),
            "frozen_method_files":len(frozen["method"]),"frozen_method":"UNCHANGED"}
    assert result["remaining"]>=0
    j.write(OUT/"verification.json",result);return result
def inspect(key,pattern=None):
    receipt=next((j.read(p) for p in j.receipts() if j.read(p)["key"]==key),None)
    assert receipt is not None,key
    print(json.dumps({k:receipt.get(k) for k in ["key","url","http_status","status","bytes","original"]},ensure_ascii=False))
    if not receipt.get("original"):return
    source=ROOT/receipt["original"]
    raw=source.read_bytes()
    if raw.startswith(b"%PDF-"):
        parsed=DATA/"sources"/key/"pages.json"
        if not parsed.exists():return
        for page in j.read(parsed)["pages"]:
            if pattern and re.search(pattern,page["text"],re.I):
                print(json.dumps(page,ensure_ascii=False))
        return
    content=raw.decode("utf-8",errors="replace")
    parser=j.Text();parser.feed(content)
    lines=parser.parts if parser.parts else content.splitlines()
    selected=[t for t in lines if not pattern or re.search(pattern,t,re.I)]
    print("\n".join(selected)[:24000])
    links=Links(receipt["url"]);links.feed(content)
    selected_links=list(dict.fromkeys(links.links))
    if pattern:selected_links=[v for v in selected_links if re.search(pattern,v,re.I)]
    print(json.dumps({"links":selected_links[:100]},ensure_ascii=False,indent=2))
    headers=source.parent/"headers.txt"
    if headers.exists():
        print("\n".join(t for t in headers.read_text().splitlines() if t.lower().startswith(("http/","location:","content-type:"))))
def build():
    import subprocess, sys, platform, time
    start=j.now();tick=time.monotonic()
    command=["python3","-m","scripts.build_reader_facing_monograph"]
    with (OUT/"build.log").open("w") as stream:
        run=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=900)
    inputs=[ROOT/"docs/monograph/chapters/02e-prospectus-difficulty.tex",ROOT/"docs/monograph/appendices/prospectus-difficulty.tex",
            OUT/"reviewed-catalogue.json",OUT/"test-specifications.json",Path(__file__)]
    outputs=[ROOT/"docs/monograph"/(n+".pdf") for n in ["monograph","technical-companion","process-guide"]]
    record={"status":"PASS" if run.returncode==0 else "FAIL","started":start,"finished":j.now(),
            "wall_seconds":round(time.monotonic()-tick,3),"command":command,"launcher":"python3 -m scripts.prospectus_corner_cases build",
            "git_commit":subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip(),
            "branch":subprocess.run(["git","branch","--show-current"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip(),
            "python":sys.version,"executable":sys.executable,"platform":platform.platform(),"compute":"CPU PDF and text tools; no device probe",
            "seeds":"N/A deterministic","data_version":j.sha(DATA/"source-index.json"),
            "plan":"docs/plans/prospectus-corner-cases-2026-10-04.md","result":j.rel(OUT/"REPORT.md"),
            "inputs":{j.rel(p):j.sha(p) for p in inputs},"outputs":{j.rel(p):j.sha(p) for p in outputs},
            "exit_code":run.returncode,"log":j.rel(OUT/"build.log")}
    j.write(OUT/"build-manifest.json",record)
    assert run.returncode==0,"Build failed; see build.log"
    return {"status":"PASS","manifest":j.rel(OUT/"build-manifest.json"),"wall_seconds":record["wall_seconds"]}
def main():
    p=argparse.ArgumentParser();p.add_argument("action",choices=("snapshot","fetch","extract","inspect","verify","build"))
    p.add_argument("key",nargs="?");p.add_argument("--pattern");a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if a.action=="inspect":inspect(a.key,a.pattern);return
    assert a.pattern is None
    with (ROOT/"docs/implementation/prospectus-evidence-closure/.lock").open("a+") as stream:
        fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.action=="fetch":
            policy=DATA/"acquisition-policy.json"
            j.write(DATA/"policy-snapshots"/(j.sha(policy)+".json"),j.read(policy))
            queue=j.read(DATA/"public-queue.json")
            existing={j.read(p)["key"] for p in j.receipts()}
            keys=[r["key"] for r in queue if r["key"]==a.key or (a.key is None and r["key"] not in existing)]
            assert a.key is None or keys
            for key in keys:print(json.dumps(j.fetch(key),ensure_ascii=False),flush=True)
            return
        result=j.extract() if a.action=="extract" else globals()[a.action]()
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
