"""Bounded local document archive and public jurisdiction-source acquisition."""
from pathlib import Path
import argparse, datetime, fcntl, hashlib, html, json, platform, re, shutil, subprocess, sys, time
from html.parser import HTMLParser
from urllib.parse import urlparse
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/prospectus/jurisdiction-2026-10-04"
OUT = ROOT / "docs/implementation/prospectus-jurisdiction-2026-10-04"
SHARED = ROOT / "docs/prospectus/evidence-closure/requests"
OLD = ROOT / "docs/implementation/prospectus-evidence-continuation/phases"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def write(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + "\n")
def rel(p): return str(p.relative_to(ROOT))
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def receipts():
    return list(OLD.glob("C3/attempt-*/requests/*/receipt.json")) + list(SHARED.glob("*/receipt.json"))
def archive():
    baseline = OUT / "document-baseline"
    manifest = baseline / "manifest.json"
    if not manifest.exists():
        names = ["docs/monograph/chapters/02-circular.tex", "docs/monograph/technical-companion.tex",
                 "docs/monograph/monograph.pdf", "docs/monograph/technical-companion.pdf"]
        rows = []
        for name in names:
            source = ROOT / name
            target = baseline / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            rows.append({"path": name, "copy": rel(target), "sha256": sha(source)})
        write(manifest, {"at": now(), "files": rows})
    for row in read(manifest)["files"]:
        assert sha(ROOT / row["copy"]) == row["sha256"], "Document baseline changed"
    study = read(ROOT / "docs/implementation/prospectus-difficulty-2026-10-04/reviewed-catalogue.json")
    rows = []
    for case in study["cases"]:
        source = ROOT / case["source"]["local_pdf"]
        assert sha(source) == case["source"]["source_sha256"], "Original PDF changed"
        assert source.read_bytes().startswith(b"%PDF-"), "Not a PDF"
        target = ROOT / "docs/prospectus/difficulty-2026-10-04/pdfs" / (case["id"] + ".pdf")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists(): shutil.copyfile(source, target)
        assert sha(target) == sha(source), "PDF copy differs"
        rows.append({"id": case["id"], "issuer": case["reviewed_issuer"], "title": case["reviewed_title"],
                     "date": case["document_date"], "pdf": rel(target), "original": rel(source),
                     "sha256": sha(target), "receipt": case["source"]["receipt"]})
    write(DATA / "prior-24-pdf-index.json", {"at": now(), "count": len(rows), "files": rows})
    return {"status": "PASS", "stored_pdfs": len(rows), "baseline": rel(manifest)}
def fetch(key):
    policy = read(DATA / "acquisition-policy.json")
    queue = read(DATA / "public-queue.json")
    rows = [r for r in queue if not key or r["key"] == key]
    assert rows and len(queue) <= policy["max_new_requests"]
    assert len({r["key"] for r in queue}) == len(queue)
    result = []
    for row in rows:
        assert set(row) == {"key", "url", "gap", "review"} and row["review"]
        u = urlparse(row["url"])
        assert u.scheme == "https" and u.hostname in policy["public_hosts"]
        assert not u.username and not u.password and not u.fragment and u.port in (None, 443)
        assert re.fullmatch(r"jur-[a-z0-9-]{1,60}", row["key"])
        existing = [read(p) for p in receipts()]
        prior = [r for r in existing if r["key"] == row["key"]]
        if prior:
            assert len(prior) == 1 and prior[0]["url"] == row["url"]
            result.append(prior[0]); continue
        assert len(existing) < policy["global_ceiling"], "Cumulative request allowance exhausted"
        assert sum(r["url"] == row["url"] for r in existing) < policy["max_requests_per_url"]
        folder = SHARED / (str(len(existing)+1).zfill(3) + "-" + row["key"])
        folder.mkdir(parents=True, exist_ok=False)
        receipt = {**row, "sequence": len(existing)+1, "at": now(), "status": "RESERVED",
                   "acquisition_policy": rel(DATA / "acquisition-policy.json"),
                   "acquisition_policy_sha256": sha(DATA / "acquisition-policy.json")}
        write(folder / "receipt.json", receipt)
        args = ["curl", "--silent", "--show-error", "--max-time", str(policy["max_seconds"]),
                "--max-filesize", str(policy["max_bytes"]), "--proto", "=https",
                "--dump-header", str(folder / "headers.txt"), "--output", str(folder / "response.bin"),
                "--write-out", "%{http_code}"]
        if u.hostname == "graphqlaz.luxse.com": args += ["--header", "Apollo-Require-Preflight: true"]
        try:
            run = subprocess.run(args+[row["url"]], capture_output=True, text=True, timeout=policy["max_seconds"]+5)
            receipt.update(http_status=run.stdout[-3:], exit_code=run.returncode, error=run.stderr,
                           status="RETAINED" if run.returncode == 0 and run.stdout == "200" else "UNAVAILABLE")
        except subprocess.TimeoutExpired:
            receipt.update(status="TIMEOUT")
        for name in ("response.bin", "headers.txt"):
            p = folder/name
            if p.exists():
                receipt.setdefault("files", {})[rel(p)] = sha(p)
                if name == "response.bin": receipt.update(original=rel(p), sha256=sha(p), bytes=p.stat().st_size)
        write(folder / "receipt.json", receipt)
        result.append(receipt)
    write(DATA / "acquisition-summary.json", {"at": now(), "requests": result, "global_used": len(receipts())})
    return {"status": "RECORDED", "global_used": len(receipts()),
            "requests": [{"key": r["key"], "status": r["status"], "http": r.get("http_status"), "bytes":r.get("bytes")} for r in result]}
class Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.hidden=0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.hidden+=1
    def handle_endtag(self, tag):
        if tag in ("script", "style"): self.hidden=max(0,self.hidden-1)
    def handle_data(self, data):
        if not self.hidden and data.strip(): self.parts.append(data.strip())
def extract():
    output=[]
    keys={r["key"] for r in read(DATA / "public-queue.json")}
    for path in sorted(receipts()):
        r=read(path)
        if r["key"] not in keys or not r.get("original"): continue
        source=ROOT/r["original"]
        assert sha(source)==r["sha256"]
        folder=DATA/"sources"/r["key"]; folder.mkdir(parents=True,exist_ok=True)
        raw=source.read_bytes()
        media="pdf" if raw.startswith(b"%PDF-") else "html" if re.search(br"<(?:!doctype|html)", raw[:8000], re.I) else "other"
        ext=".pdf" if media=="pdf" else ".html" if media=="html" else ".bin"
        dest=folder/("source"+ext)
        if not dest.exists(): shutil.copyfile(source,dest)
        assert sha(dest)==sha(source)
        record={"key":r["key"],"status":r["status"],"url":r["url"],"original":rel(dest),"sha256":sha(dest),
                "receipt":rel(path),"receipt_sha256":sha(path),"media":media,"source_complete":False}
        if r["status"]=="RETAINED" and media=="pdf":
            subprocess.run(["pdftotext","-layout",str(dest),str(folder/"text.txt")],check=True,timeout=60)
            info=subprocess.run(["pdfinfo",str(dest)],capture_output=True,text=True,check=True,timeout=20)
            pages=(folder/"text.txt").read_text().split("\f")
            if pages and not pages[-1].strip():pages.pop()
            count=int(re.search(r"(?m)^Pages:\s+(\d+)",info.stdout)[1]);assert count==len(pages)
            write(folder/"pages.json",{"pages":[{"page":i+1,"text":p} for i,p in enumerate(pages)]})
            empty_pages=[i+1 for i,p in enumerate(pages) if not p.strip()]
            record.update(pages=count,text=rel(folder/"text.txt"),text_sha256=sha(folder/"text.txt"),
                          empty_text_pages=empty_pages,
                          extraction_status="OCR_REQUIRED" if len(empty_pages)==count else
                          "PARTIAL_TEXT_REVIEW_REQUIRED" if empty_pages else "TEXT_EXTRACTED_UNREVIEWED")
        elif r["status"]=="RETAINED" and media=="html":
            parser=Text();parser.feed(raw.decode("utf-8",errors="replace"))
            (folder/"text.txt").write_text("\n".join(parser.parts)+"\n")
            record.update(text=rel(folder/"text.txt"),text_sha256=sha(folder/"text.txt"))
        write(folder/"manifest.json",record);output.append(record)
    write(DATA/"source-index.json",{"at":now(),"sources":output})
    return {"status":"RECORDED","sources":[{k:r.get(k) for k in ("key","media","pages","status")} for r in output]}
def build():
    started=now();tick=time.monotonic()
    command=["python3","-m","scripts.build_reader_facing_monograph"]
    log=OUT/"build.log"
    with log.open("w") as stream:
        result=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=900)
    paths=["docs/monograph/monograph.pdf","docs/monograph/technical-companion.pdf",
           "docs/monograph/process-guide.pdf","docs/proposal/monograph.pdf",
           "docs/proposal/proposal.pdf","docs/proposal/technical-companion.pdf",
           "docs/monograph/review/reader-facing/document-check.json"]
    inputs=["docs/monograph/chapters/02-circular.tex","docs/monograph/chapters/02e-prospectus-difficulty.tex",
            "docs/monograph/technical-companion.tex","docs/monograph/appendices/prospectus-difficulty.tex",
            rel(DATA/"source-index.json"),rel(OUT/"reviewed-catalogue.json"),
            rel(OUT/"test-specifications.json"),"scripts/prospectus_jurisdiction_study.py"]
    commit=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    branch=subprocess.run(["git","branch","--show-current"],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    manifest={"schema":"prospectus-jurisdiction-document-build.v1","started":started,"finished":now(),
              "command":command,"launcher":"python3 -m scripts.prospectus_jurisdiction_study build",
              "cwd":str(ROOT),"git_commit":commit,"branch":branch,"uncommitted_source_hashes":{p:sha(ROOT/p) for p in inputs},
              "python_executable":sys.executable,"python_version":sys.version,"platform":platform.platform(),
              "compute":"CPU-only PDF and text tools; no GPU/framework import or device probe",
              "seeds":"N/A: deterministic documentation and source integrity checks",
              "data_version":sha(DATA/"source-index.json"),"wall_seconds":round(time.monotonic()-tick,3),
              "exit_code":result.returncode,"plan":"docs/plans/prospectus-jurisdiction-2026-10-04.md",
              "result":rel(OUT/"REPORT.md"),"log":rel(log),"outputs":{p:sha(ROOT/p) for p in paths if (ROOT/p).exists()},
              "status":"PASS" if result.returncode==0 else "FAIL"}
    write(OUT/"run-manifest.json",manifest)
    if result.returncode:raise RuntimeError("Document build failed; inspect "+rel(log))
    return {"status":"PASS","manifest":rel(OUT/"run-manifest.json"),"wall_seconds":manifest["wall_seconds"]}
def verify():
    tick=time.monotonic()
    rows=read(DATA/"prior-24-pdf-index.json")["files"]
    for r in rows: assert sha(ROOT/r["pdf"])==r["sha256"]==sha(ROOT/r["original"])
    assert len(rows)==24 and len({r["sha256"] for r in rows})==24
    sources=read(DATA/"source-index.json")["sources"]
    for r in sources:
        assert sha(ROOT/r["original"])==r["sha256"]
        assert sha(ROOT/r["receipt"])==r["receipt_sha256"]
        if "text" in r:assert sha(ROOT/r["text"])==r["text_sha256"]
    pdfs=[r for r in sources if r["media"]=="pdf" and r["status"]=="RETAINED"]
    assert len(pdfs)==3 and len({r["sha256"] for r in pdfs})==3
    assert not {r["sha256"] for r in pdfs}&{r["sha256"] for r in rows}
    by_key={r["key"]:r for r in pdfs}
    catalogue=read(OUT/"reviewed-catalogue.json")
    normalized=lambda text:" ".join(text.split()).casefold()
    anchor_count=0
    for case in catalogue["cases"]:
        source=case["source"];r=by_key[source["key"]]
        assert source["pdf"]==r["original"] and source["sha256"]==r["sha256"]
        assert source["receipt"]==r["receipt"] and source["receipt_sha256"]==r["receipt_sha256"]
        assert case["engine_result"] is None and case["legal_label"] is None
        assert case["extraction_status"]==r["extraction_status"]
        pages=read((ROOT/r["original"]).parent/"pages.json")["pages"]
        assert source["pdf_pages"]==len(pages)==r["pages"]
        for fact in case["facts"]:
            assert all(1<=n<=len(pages) for n in fact["pdf_pages"])
            if "text_anchor" in fact:
                text=" ".join(pages[n-1]["text"] for n in fact["pdf_pages"])
                assert normalized(fact["text_anchor"]) in normalized(text), (case["id"],fact["text_anchor"])
                anchor_count+=1
    bes=by_key["jur-bes-2014-ptbeqkom0019"]
    assert bes["extraction_status"]=="OCR_REQUIRED" and bes["empty_text_pages"]==[1,2,3,4,5]
    manual=read((ROOT/bes["original"]).parent/"manual-review.json")
    assert manual["source"]["sha256"]==bes["sha256"]
    tests=read(OUT/"test-specifications.json")["tests"]
    assert len(tests)==7 and len({t["id"] for t in tests})==7
    assert all(t["case_id"] in {c["id"] for c in catalogue["cases"]} for t in tests)
    baseline=read(OUT/"document-baseline/manifest.json")
    for r in baseline["files"]:assert sha(ROOT/r["copy"])==r["sha256"]
    frozen=read(ROOT/"docs/prospectus/difficulty-2026-10-04/freeze.json")
    for p,digest in frozen["method"].items(): assert sha(ROOT/p)==digest,"Frozen method changed: "+p
    link_count=0
    for name in ["chapters/02e-prospectus-difficulty.tex","appendices/prospectus-difficulty.tex"]:
        text=(ROOT/"docs/monograph"/name).read_text()
        for target in re.findall(r"\\href\{([^}]+)\}",text):
            if target.startswith("../prospectus/"):
                for parent in ["docs/monograph","docs/proposal"]:
                    assert (ROOT/parent/target).resolve().is_file(), target
                link_count+=1
    result={"status":"PASS","at":now(),"prior_pdfs":24,"new_pdfs":len(pdfs),
            "retained_new_response_records":len(sources),"source_text_anchors_checked":anchor_count,
            "test_specifications":len(tests),"engine_tests_run_in_this_phase":0,
            "local_source_links_checked":link_count,"global_requests":len(receipts()),
            "frozen_method_files":len(frozen["method"]),"frozen_method":"UNCHANGED",
            "document_baseline_files":len(baseline["files"]),"wall_seconds":round(time.monotonic()-tick,3),
            "limits":"Source integrity and declared boundary checks; no legal adjudication or engine accuracy result."}
    write(OUT/"verification.json",result)
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument("action",choices=("archive","fetch","extract","build","verify"));p.add_argument("key",nargs="?")
    a=p.parse_args();assert a.action=="fetch" or a.key is None
    OUT.mkdir(parents=True,exist_ok=True)
    lock=ROOT/"docs/implementation/prospectus-evidence-closure/.lock"
    with lock.open("a+") as stream:
        fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result=fetch(a.key) if a.action=="fetch" else globals()[a.action]()
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
