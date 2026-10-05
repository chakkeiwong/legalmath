"""Validate source-bound reviewed OCR without changing frozen reader code.

These checks establish consistency of retained evidence, not authenticity of a
reviewer's identity or correctness of the original OCR. Image review remains a
separate recorded action.
"""
import hashlib,json
from pathlib import Path
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def norm(text):return " ".join(text.split())
def bound(root,name,digest):
    path=(Path(root)/name).resolve()
    if not path.is_relative_to(Path(root).resolve()) or not path.is_file() or sha(path)!=digest:
        raise ValueError("Missing or changed bound file: "+name)
    return path
def text_hash(text):return hashlib.sha256(text.encode()).hexdigest()
def numbers(values,n):
    return (isinstance(values,list) and all(type(p) is int and 1<=p<=n for p in values)
            and values==sorted(set(values)))
def load(meta,root):
    source=bound(root,meta["original"],meta["sha256"])
    raw_path=bound(root,meta["raw"],meta["raw_sha256"])
    review_path=bound(root,meta["review"],meta["review_sha256"])
    derivative=bound(root,meta["text"],meta["text_sha256"])
    raw=json.loads(raw_path.read_text());review=json.loads(review_path.read_text());doc=json.loads(derivative.read_text())
    n=meta["pages"]
    if type(n) is not int or n<1:raise ValueError("Invalid page count")
    expected=list(range(1,n+1))
    if any([p["page"] for p in x["pages"]]!=expected or
           any(type(p["page"]) is not int or not isinstance(p["text"],str) for p in x["pages"])
           for x in (raw,doc)):
        raise ValueError("Missing, duplicate or reordered page")
    if raw["source_sha256"]!=meta["sha256"] or doc["source_sha256"]!=meta["sha256"] or raw["source"]!=meta["original"]:
        raise ValueError("Wrong source")
    if review["raw_sha256"]!=meta["raw_sha256"] or review["source_sha256"]!=meta["sha256"]:
        raise ValueError("Stale review")
    processed=raw["rendered_pages"];ocr=raw["ocr_pages"];rows=review["pages"]
    if not numbers(processed,n) or not numbers(ocr,n) or not set(ocr)<=set(processed):
        raise ValueError("Invalid rendered/OCR page coverage")
    if [p["page"] for p in rows]!=processed or any(type(p["page"]) is not int for p in rows):
        raise ValueError("Incomplete page review")
    if (review.get("reviewer_type")!="agent_visual_review" or
        review.get("legal_adjudication")!="PENDING" or review.get("human_acceptance")!="PENDING" or
        doc.get("review_scope")!="agent_visual_review"):
        raise ValueError("Review scope misrepresented")
    lookup={r["page"]:r for r in rows};blank=[]
    for a,b in zip(raw["pages"],doc["pages"]):
        text=a["text"]
        if a["page"] in lookup:
            item=lookup[a["page"]]
            if item["raw_text_sha256"]!=text_hash(text):raise ValueError("Page text changed")
            for kind in ("image","review_image"):
                bound(root,a[kind],a[kind+"_sha256"])
                if item[kind+"_sha256"]!=a[kind+"_sha256"]:raise ValueError("Wrong page image")
            if item["status"]!="VISUALLY_CHECKED" or type(item["blank"]) is not bool:
                raise ValueError("Unreviewed page")
            if item["blank"]:
                if text.strip() or item["corrections"]:raise ValueError("Nonblank text hidden")
                blank.append(a["page"]);text=""
            else:
                text=norm(text)
                for correction in item["corrections"]:
                    if (not isinstance(correction.get("reason"),str) or not correction["reason"].strip()
                        or not isinstance(correction.get("old"),str) or not correction["old"]
                        or not isinstance(correction.get("new"),str) or not correction["new"].strip()
                        or text.count(correction["old"])!=1):
                        raise ValueError("Unbound correction")
                    text=text.replace(correction["old"],correction["new"],1)
        if b["text"]!=text:raise ValueError("Derivative exceeds reviewed corrections")
    if doc["reviewed_blank_pages"]!=blank or set(doc["blank_page_reviews"])!={str(n) for n in blank}:
        raise ValueError("Blank-page declaration changed")
    for number in blank:
        if doc["blank_page_reviews"][str(number)]["reviewed_image_sha256"]!=lookup[number]["image_sha256"]:
            raise ValueError("Blank image misbound")
    if type(doc["automatic_ocr_performed"]) is not bool or doc["automatic_ocr_performed"]!=bool(ocr):
        raise ValueError("OCR status changed")
    if ocr:bound(root,meta["language_model"],raw["runtime"]["language_sha256"])
    return doc
