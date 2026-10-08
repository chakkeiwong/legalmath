"""Bounded public retrieval and sealed issue registration, never legal clearance."""
from html.parser import HTMLParser
import re
import json
import subprocess
import time
from urllib.parse import urlparse, urljoin

from .master_control import ROOT, OUT, DATA, read, write, sha, now, relative, digest, method_files, campaign_path


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[];self.parts=[];self.anchor=None;self.skip=0
    def handle_starttag(self,tag,attrs):
        # Public CMS document lists may be JSON in attributes rather than anchors.
        # HTMLParser has already decoded HTML entities; JSON is data, never code.
        for name,value in attrs:
            if name in {"first-results", "data-documents"} and value:
                try:
                    payload=json.loads(value)
                except (ValueError,TypeError):
                    continue
                rows=payload.get("results",[]) if isinstance(payload,dict) else payload
                if isinstance(rows,list):
                    for row in rows:
                        if not isinstance(row,dict):continue
                        target=row.get("uri") or row.get("url")
                        if isinstance(target,str) and target.startswith("https://"):
                            self.links.append({"href":target,"text":str(row.get("name_2") or row.get("name") or ""),
                                               "origin":"publisher_document_metadata"})
        if tag in ("script","style"):self.skip+=1
        if tag=="a":self.anchor={"href":dict(attrs).get("href",""),"text":""}
    def handle_endtag(self,tag):
        if tag in ("script","style"):self.skip=max(0,self.skip-1)
        if tag=="a" and self.anchor:self.links.append(self.anchor);self.anchor=None
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)
        if self.anchor:self.anchor["text"]+=data


def valid_url(url,policy):
    parsed=urlparse(url)
    if parsed.scheme!="https" or parsed.hostname not in policy["public_hosts"] or parsed.username or parsed.password or parsed.port not in (None,443):
        raise ValueError("Only approved HTTPS public source hosts are accepted")
    return url


def acquire(key,url,purpose,current):
    policy=read(OUT/"allowlist.json")
    valid_url(url,policy)
    if not re.fullmatch(r"[a-z0-9-]{1,80}",key) or purpose not in {"contract","authority","corporate","capital","discovery"}:raise ValueError("Invalid source key or purpose")
    if "freeze" not in current:raise ValueError("Freeze before public-source inspection")
    previous=sorted((DATA/"requests").glob("*/receipt.json"))
    if len(previous)>=policy["max_http_requests"]:raise ValueError("80-request protocol budget exhausted")
    if sum(read(p)["url"]==url for p in previous)>=policy["max_requests_per_url"]:raise ValueError("Per-URL retry budget exhausted")
    directory=DATA/"requests"/f"{len(previous)+1:03d}-{key}"
    directory.mkdir(parents=True,exist_ok=False)
    receipt={"at":now(),"key":key,"url":url,"purpose":purpose,"status":"DISPATCH_RESERVED","freeze":current["freeze"],
             "original":relative(directory/"response.body"),"budget_sequence":len(previous)+1}
    write(directory/"receipt.json",receipt)
    # Redirects are recorded and followed explicitly so every HTTP request is
    # budgeted and each destination host is validated before dispatch.
    command=["curl","--max-time",str(policy["max_http_seconds"]),"--connect-timeout","15","--max-filesize",str(policy["max_response_bytes"]),
             "--proto","=https","-A","LegalMath public-source research","-sS","-D",str(directory/"headers.txt"),
             "-o",str(directory/"response.body"),"-w","%{http_code}",url]
    started=time.monotonic()
    try:
        p=subprocess.run(command,capture_output=True,timeout=policy["max_http_seconds"]+5)
        (directory/"stderr.log").write_bytes(p.stderr)
        code=int(p.stdout.strip()) if p.stdout.strip().isdigit() else 0
        receipt.update(exit_code=p.returncode,http_status=code,status="RETAINED" if code==200 and p.returncode==0 else "FAILED_OR_REDIRECT")
    except subprocess.TimeoutExpired as exc:
        (directory/"stderr.log").write_bytes(exc.stderr or b"")
        receipt.update(exit_code=124,http_status=0,status="TIMEOUT")
    path=directory/"response.body"
    if not path.exists():path.write_bytes(b"")
    receipt.update(command=command,sha256=sha(path),bytes=path.stat().st_size,wall_seconds=time.monotonic()-started)
    raw=path.read_bytes()
    receipt["kind"]="pdf" if raw.startswith(b"%PDF") else "html_or_other"
    headers=(directory/"headers.txt").read_text(errors="replace") if (directory/"headers.txt").exists() else ""
    location=re.findall(r"(?im)^location:\s*(.*?)\s*$",headers)
    if location:receipt["redirect"]=urljoin(url,location[-1])
    if receipt["status"]=="RETAINED" and receipt["kind"]!="pdf":
        parser=Links();parser.feed(raw.decode(errors="replace"))
        write(directory/"links.json",[{"url":urljoin(url,x["href"]),"text":" ".join(x["text"].split())} for x in parser.links])
        (directory/"text.txt").write_text("\n".join(parser.parts))
    write(directory/"receipt.json",receipt)
    return receipt


def extract(receipt_path):
    receipt=read(receipt_path);original=campaign_path(receipt["original"])
    if receipt["status"]!="RETAINED" or sha(original)!=receipt["sha256"]:raise ValueError("Source unavailable or changed")
    target=DATA/"extractions"/receipt["sha256"]
    path=target/"pages.json"
    if path.exists():
        data=read(path)
        if data["source_sha256"]!=receipt["sha256"]:raise ValueError("Extraction source identity changed")
        if not (target/"extraction.json").exists() or read(target/"extraction.json")["pages_sha256"] != sha(path):
            raise ValueError("Extraction derivative changed or lacks its retained hash")
        return path
    target.mkdir(parents=True,exist_ok=True)
    repairs=[]
    if receipt["kind"]=="pdf":
        from pypdf import PdfReader
        try:
            pages=[{"page":i+1,"text":p.extract_text() or ""} for i,p in enumerate(PdfReader(original).pages)]
            if not pages or sum(len(p["text"].strip()) for p in pages)<100:raise ValueError("Insufficient extracted text")
        except Exception as exc:
            write(target/"pypdf-failure.json",{"error":repr(exc)},exclusive=True)
            result=subprocess.run(["pdftotext","-layout",str(original),str(target/"poppler.txt")],capture_output=True,timeout=60)
            (target/"poppler.log").write_bytes(result.stdout+result.stderr)
            if result.returncode:raise ValueError("Both extraction engines failed")
            text=(target/"poppler.txt").read_text();parts=text.split("\f")
            if not parts[-1].strip():parts.pop()
            pages=[{"page":i+1,"text":t} for i,t in enumerate(parts)]
            if sum(len(p["text"].strip()) for p in pages)<100:raise ValueError("OCR required; no text evidence")
            repairs.append("Executed Poppler fallback after retained pypdf failure")
    else:
        parser=Links();parser.feed(original.read_text(errors="replace"))
        pages=[{"page":1,"text":" ".join(parser.parts)}]
    write(path,{"id":receipt["key"],"source_sha256":receipt["sha256"],"pages":pages,"preliminary_indicator":False,
                "extraction":"pypdf with bounded Poppler fallback; no English equivalence claim","repairs":repairs},exclusive=True)
    write(target/"extraction.json", {"source_sha256":receipt["sha256"],"pages_sha256":sha(path)}, exclusive=True)
    return path


def register(selection_path,current):
    if selection_path.resolve() != DATA/"selection.json":
        raise ValueError("Seal the campaign selection.json path")
    selection=read(selection_path)
    frozen=read(ROOT/current["freeze"])
    if frozen["files"]!=method_files():raise ValueError("Method changed since freeze; rerun development validation")
    issues=selection["issues"]
    if not issues and not selection.get("acquisition_exhausted"):raise ValueError("No selected issues or recorded exhausted acquisition")
    documents={};families=set();issue_ids=set();categories={"capital":0,"corporate":0}
    exposed_sources=set(frozen["source_requests_before_freeze"])
    for src in selection.get("sources",[]):
        if src["id"] in documents:raise ValueError("Duplicate document identity")
        receipt_path=campaign_path(src["receipt"]);receipt=read(receipt_path)
        if receipt["kind"]!="pdf":raise ValueError("New issue selections require retained PDF originals")
        path=extract(receipt_path);text=read(path)
        if not src.get("identity_markers"):raise ValueError("Issue identity markers required")
        alltext=" ".join(" ".join(p["text"].split()) for p in text["pages"])
        if any(marker not in alltext for marker in src["identity_markers"]):raise ValueError("Source identity marker missing")
        documents[src["id"]]={"id":src["id"],"original":receipt["original"],"sha256":receipt["sha256"],"text":relative(path),
                               "text_sha256":sha(path),"pages":len(text["pages"]),"url":receipt["url"],"identity_markers":src["identity_markers"],
                               "acquisition_receipt":relative(receipt_path)}
    old_issues=read(ROOT/"docs/prospectus/gap-closure/final-inventory.json")["issues"]
    old_ids={i["id"] for i in old_issues};old_identifiers={v for i in old_issues for v in i["identifiers"]}
    for issue in issues:
        if issue["id"] in issue_ids:raise ValueError("Duplicate issue identity")
        issue_ids.add(issue["id"])
        if not issue.get("documents") or not issue.get("identifiers"):raise ValueError("Issue sources and identifiers required")
        if {"answer","expected_answer","expected_answers","quality"}&set(issue):raise ValueError("No answer or quality labels")
        if issue["id"] in old_ids or set(issue["identifiers"])&old_identifiers:raise ValueError("Existing issue cannot be called unseen")
        if issue["category"] not in categories:raise ValueError("Unknown category")
        if issue["family"] not in read(OUT/"allowlist.json")["source_family_order"][issue["category"]]:raise ValueError("Undeclared family")
        if issue["family"] in families:raise ValueError("Use distinct families for the challenge")
        families.add(issue["family"]);categories[issue["category"]]+=1
        if not issue.get("selection_basis"):raise ValueError("Source-based selection reason required")
        for s in issue["documents"]:
            if s["id"] not in documents:raise ValueError("Missing selected source")
            if not s.get("scope_basis"):raise ValueError("Document scope must be explained before classification")
        issue["data_role"]="exposed-after-repair" if any(documents[s["id"]]["acquisition_receipt"] in exposed_sources for s in issue["documents"]) else "new-issue-pdf-frozen-challenge"
        issue["family_discovery_before_freeze"]=bool(frozen.get("discovery_requests_before_freeze"))
    targets=read(OUT/"allowlist.json")["target_new_issues"]
    if any(categories[k]>targets[k] for k in categories):raise ValueError("Selection exceeds declared category targets")
    if any(categories[k]<targets[k] for k in categories) and not selection.get("acquisition_exhausted"):
        raise ValueError("Incomplete challenge requires explicit acquisition_exhausted and remaining-gap disclosure")
    directory=DATA/"registrations"/f"selection-{len(list((DATA/'registrations').glob('selection-*')))+1:03d}"
    directory.mkdir(parents=True)
    inventory={"documents":documents,"issues":issues,"freeze":current["freeze"],"scope":"Selected dated issue documents; full contracts and actual bank permission remain unestablished."}
    write(directory/"inventory.json",inventory,exclusive=True)
    write(directory/"registration.json",{"at":now(),"selection_sha256":sha(selection_path),"freeze_sha256":sha(ROOT/current["freeze"]),
          "inventory_sha256":sha(directory/"inventory.json"),"categories":categories,"classified_before_selection":False},exclusive=True)
    write(DATA/"registered.json",{"inventory":relative(directory/"inventory.json"),"sha256":sha(directory/"inventory.json"),"selection_sha256":sha(selection_path)})
    return {"status":"REGISTERED","inventory":relative(directory/"inventory.json"),"categories":categories}

def verify_sources():
    originals = derivatives = registrations = 0
    for path in sorted((DATA/"requests").glob("*/receipt.json")):
        receipt = read(path)
        if "sha256" in receipt:
            if sha(campaign_path(receipt["original"])) != receipt["sha256"]:
                raise ValueError("Retained response bytes changed: "+relative(path))
            originals += 1
    for path in sorted((DATA/"extractions").glob("*/extraction.json")):
        if read(path)["pages_sha256"] != sha(path.parent/"pages.json"):
            raise ValueError("Extraction changed: "+relative(path))
        derivatives += 1
    for path in sorted((DATA/"registrations").glob("selection-*/registration.json")):
        record=read(path);inv=path.parent/"inventory.json"
        if sha(inv)!=record["inventory_sha256"]:raise ValueError("Sealed inventory changed")
        inventory=read(inv)
        if sha(campaign_path(inventory["freeze"]))!=record["freeze_sha256"]:raise ValueError("Sealed freeze changed")
        for doc in inventory["documents"].values():
            for field,hash_field in (("original","sha256"),("text","text_sha256")):
                if sha(campaign_path(doc[field]))!=doc[hash_field]:raise ValueError("Registered source changed")
        registrations += 1
    return {"responses": originals, "derivatives": derivatives, "registrations": registrations}


def validate_source_review(review):
    for finding in review["findings"]:
        if not all(finding.get(k) for k in ("subject","finding","remaining","evidence")):
            raise ValueError("Source finding requires reasoning, remaining scope and retained evidence")
        for anchor in finding["evidence"]:
            receipt_path=campaign_path(anchor["receipt"]);receipt=read(receipt_path)
            if receipt.get("sha256")!=sha(campaign_path(receipt["original"])):
                raise ValueError("Source-review bytes changed")
            if receipt["status"]=="RETAINED":
                text=read(extract(receipt_path))["pages"]
                page=anchor.get("page",0)
                if not 1<=page<=len(text) or not anchor.get("quote"):
                    raise ValueError("Source review needs a page and exact quote")
                normalize=lambda value:" ".join(value.split())
                if normalize(anchor["quote"]) not in normalize(text[page-1]["text"]):
                    raise ValueError("Source-review quote missing")
            elif anchor.get("http_status")!=receipt.get("http_status"):
                raise ValueError("Failed-request finding has incorrect HTTP status")
    return {**review,"status":"SOURCE_BOUND_MODEL_REVIEW","human_legal_adjudication":False}
