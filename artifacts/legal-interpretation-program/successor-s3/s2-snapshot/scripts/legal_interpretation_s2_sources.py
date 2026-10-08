"""Bounded official-source retrieval and local projections for S2; no model calls."""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urljoin,urlsplit

ROOT=Path(__file__).resolve().parents[1]
if __name__=="__main__" and Path(sys.prefix)!=ROOT/".venv":
    os.execv(str(ROOT/".venv/bin/python"),[str(ROOT/".venv/bin/python"),"-m","scripts.legal_interpretation_s2_sources",*sys.argv[1:]])
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
BASE=ROOT/"artifacts/legal-interpretation-program/successor-s2"
P0=ROOT/"artifacts/legal-interpretation-program/2026-10-06-offline-v1/P0/attempt-2"
PLAN=ROOT/"docs/plans/legal-interpretation-program/S2-authority-and-standards.md"
HOSTS={"www.hkcfa.hk","www.judiciary.hk","legalref.judiciary.hk","www.sfc.hk","apps.sfc.hk",
       "www.doj.gov.hk","www.elegislation.gov.hk","www.hklii.hk"}
SEEDS=[
("cfa-cases","https://www.hkcfa.hk/en/work/cases/index.html","Cheung Kwun Yin; statutory interpretation"),
("cfa-role","https://www.hkcfa.hk/en/about/role/index.html","Court role and authority"),
("judiciary-index","https://www.judiciary.hk/en/court_services_facilities/judgments.html","Gatecoin; ownership"),
("judiciary-search","https://legalref.judiciary.hk/lrs/common/search/search.jsp","responsibility; outsourcing; Gatecoin"),
("sfc-codes","https://www.sfc.hk/en/Rules-and-standards/Codes-and-guidelines/Codes","Relevant source editions")]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {"path":str(p.relative_to(ROOT)),"sha256":sha(p)}
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x") as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write("\n")
def textsave(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x") as f:f.write(s)
def allowed(url):
    u=urlsplit(url)
    return u.scheme=="https" and u.hostname in HOSTS and u.port in (None,443) and not u.username and not u.password
class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.parts=[];self.links=[];self.current=None;self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style"):self.hidden+=1
        if tag in ("p","br","div","li","tr","h1","h2","h3"):self.parts.append("\n")
        if tag=="a":self.current={"url":dict(attrs).get("href",""),"text":""}
    def handle_endtag(self,tag):
        if tag in ("script","style"):self.hidden=max(0,self.hidden-1)
        if tag in ("p","div","li","tr"):self.parts.append("\n")
        if tag=="a" and self.current is not None:self.links.append(self.current);self.current=None
    def handle_data(self,data):
        if not self.hidden:self.parts.append(data)
        if self.current is not None:self.current["text"]+=data
def inspect():
    folder=BASE/"inspection"
    if folder.exists():
        print(json.dumps({"inspection":str(folder.relative_to(ROOT))}));return
    folder.mkdir(parents=True)
    packet=read(P0/"packet.json");overlay=read(P0/"overlay.json");obligations=read(P0/"obligation-map.json")
    selected={"ut-current.parent","ut-current.intro","tokenised-securities.circular","tokenised-securities.appendix"}
    lines=[]
    for u in packet["units"]:
        if u["unit_id"] in selected or any(x in u["text"] for x in ("ultimately responsible","1 Given that","confirm and, upon","at a minimum, they comply","proper records of token","obtain third party audit","obtain satisfactory legal opinion")):
            textsave(folder/(u["unit_id"]+".txt"),u["text"]+"\n")
            lines.append({"id":u["unit_id"],"characters":len(u["text"])})
    save(folder/"units.json",lines)
    mapped=[]
    for row in obligations:
        o=row["obligation"];found=[]
        for record in overlay["records"]:
            for value in record["operative"]["obligations"]:
                if value["question_id"]==o["obligation_id"]:
                    found.append({"role":record["role"],"reading_id":record["reading_id"],"response":value})
        mapped.append({"obligation":o,"responses":found})
    save(folder/"obligations.json",mapped)
    questions=[{"id":r["reading_id"],"role":r["role"],"question_texts":r["operative"]["question_texts"]}
               for r in overlay["records"]]
    save(folder/"questions.json",questions)
    textsave(folder/"obligations.txt","\n".join(json.dumps({"id":r["obligation"]["obligation_id"],
        "dimension":r["obligation"]["dimension"],"candidate":r["obligation"]["candidate_id"],
        "answers":[{"role":a["role"],"answer":a["response"]["answer"],"needed":a["response"]["needed_evidence"],
                    "evidence":a["response"]["evidence"]} for a in r["responses"]]},ensure_ascii=False) for r in mapped)+"\n")
    print(json.dumps({"inspection":str(folder.relative_to(ROOT)),"units":lines,"obligations":len(mapped),
                      "unmatched":[r["obligation"]["obligation_id"] for r in mapped if not r["responses"]]}))
def fetch(identity,url,query):
    import httpx
    if not re.fullmatch("[a-z0-9-]{1,70}",identity) or not allowed(url):raise ValueError("Outside official retrieval scope")
    folder=BASE/"acquisition";folder.mkdir(parents=True,exist_ok=True)
    target=folder/identity
    if target.exists():raise ValueError("Acquisition identity already exists; inspect or choose a new recorded attempt")
    used=len(list(folder.glob("*/request-*.json")))
    if used>=24:raise ValueError("HTTP attempt ceiling reached")
    target.mkdir()
    save(target/"spec.json",{"id":identity,"url":url,"query":query,"plan":ref(PLAN),
        "max_bytes":12_000_000,"max_http_attempts":24,"started_at":datetime.now(timezone.utc).isoformat()})
    start=time.monotonic();record={"id":identity,"requested_url":url,"query":query,"redirects":[],"documents":[]}
    try:
        current=url
        with httpx.Client(timeout=30,follow_redirects=False) as client:
            for index in range(4):
                if not allowed(current) or used>=24:raise ValueError("Redirect/HTTP scope limit")
                save(target/f"request-{index}.json",{"url":current,"at":datetime.now(timezone.utc).isoformat()})
                used+=1
                with client.stream("GET",current,headers={"User-Agent":"LegalMath-source-research/1.0"}) as response:
                    record.update(http_status=response.status_code,final_url=current,
                        content_type=response.headers.get("content-type",""),etag=response.headers.get("etag"),
                        last_modified=response.headers.get("last-modified"))
                    if response.is_redirect:
                        next_url=urljoin(current,response.headers["location"])
                        record["redirects"].append({"from":current,"to":next_url});current=next_url;continue
                    data=bytearray()
                    for chunk in response.iter_bytes(65536):
                        data.extend(chunk)
                        if len(data)>12_000_000 or time.monotonic()-start>90:raise ValueError("Byte/time limit")
                    (target/"response.bin").write_bytes(data)
                    record["documents"].append(ref(target/"response.bin"))
                    record["status"]="RETRIEVED" if response.status_code==200 else "HTTP_ERROR_RETAINED"
                    break
            else:raise ValueError("Redirect limit")
        if bytes(data).startswith(b"%PDF"):
            p=subprocess.run(["pdftotext","-layout",str(target/"response.bin"),"-"],capture_output=True,text=True,timeout=45)
            if p.returncode:raise ValueError("PDF extraction failed")
            text=p.stdout;links=[];record["format"]="PDF"
        elif bytes(data).startswith(b"PK") and (current.endswith(".docx") or "wordprocessingml" in record["content_type"]):
            import io, zipfile
            from xml.etree import ElementTree as ET
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names=[n for n in ("word/document.xml","word/footnotes.xml","word/endnotes.xml") if n in archive.namelist()]
                if not names or sum(archive.getinfo(n).file_size for n in names)>12_000_000:
                    raise ValueError("DOCX extraction size/profile limit")
                ns={"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                paragraphs=[]
                for name in names:
                    xml=ET.fromstring(archive.read(name))
                    paragraphs += ["".join(p.itertext()) for p in xml.findall(".//w:p",ns)]
                text="\n".join(paragraphs);links=[];record["format"]="DOCX_TEXT_WITH_FOOTNOTES"
        else:
            raw=bytes(data).decode("utf-8",errors="replace")
            page=Page();page.feed(raw)
            text=re.sub(r"\n[ \t]*\n+","\n","".join(page.parts)).strip()
            links=[{"url":urljoin(current,r["url"]),"text":" ".join(r["text"].split())} for r in page.links if allowed(urljoin(current,r["url"]))]
            record["format"]="HTML_OR_TEXT"
        textsave(target/"text.txt",text)
        save(target/"links.json",links)
        record["documents"] += [ref(target/"text.txt"),ref(target/"links.json")]
        record["characters"]=len(text)
        record["admission"]="UNREVIEWED_RESPONSE; full judgment and relevance not established"
    except Exception as error:
        record.update(status="UNAVAILABLE_OR_INCOMPLETE",error=type(error).__name__,details=str(error)[:600])
    record.update(elapsed_seconds=round(time.monotonic()-start,3),retrieved_at=datetime.now(timezone.utc).isoformat())
    save(target/"result.json",record)
    print(json.dumps({k:v for k,v in record.items() if k not in ("documents","redirects")}),flush=True)
def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("inspect","seeds","fetch"))
    parser.add_argument("values",nargs="*");args=parser.parse_args()
    if args.action=="inspect":inspect()
    elif args.action=="seeds":
        if args.values:raise ValueError("Unexpected argument")
        for row in SEEDS:
            if not (BASE/"acquisition"/row[0]).exists():fetch(*row)
    else:
        if len(args.values)!=3:raise ValueError("fetch ID OFFICIAL_URL QUERY")
        fetch(*args.values)
if __name__=="__main__":main()
