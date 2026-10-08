"""Lossless page/line inventory. Geometry and order remain reviewable premises."""
import re
import subprocess
import xml.etree.ElementTree as ET
from .contracts import TextUnit, bound_path, digest, timestamp, read

REFERENCE = re.compile(r"\b(?:Condition|Section|Clause|Article)\s+(\d+(?:\.\d+)*(?:\([a-z0-9]+\))?)|§\s*(\d+(?:\([a-z0-9]+\))?)", re.I)


def pdf_units(path, document):
    run = subprocess.run(["pdftotext", "-bbox-layout", "-enc", "UTF-8", str(path), "-"],
                         capture_output=True, timeout=90, check=True)
    raw_xml = run.stdout.decode("utf-8")
    illegal = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
    removed = [{"offset": m.start(), "codepoint": ord(m.group())} for m in illegal.finditer(raw_xml)]
    tree = ET.fromstring(illegal.sub("", raw_xml))
    ns = {"x": "http://www.w3.org/1999/xhtml"}
    pages = tree.findall(".//x:page", ns)
    units = []
    for p, page in enumerate(pages, 1):
        order = 0
        for b, block in enumerate(page.findall(".//x:block", ns)):
            for line in block.findall("x:line", ns):
                words, offset = [], 0
                for word in line.findall("x:word", ns):
                    text = "".join(word.itertext())
                    words.append({"text": text, "start": offset, "end": offset + len(text),
                                  "bbox": [float(word.attrib[k]) for k in ("xMin", "yMin", "xMax", "yMax")]})
                    offset += len(text) + 1
                raw = " ".join(w["text"] for w in words)
                box = [float(line.attrib[k]) for k in ("xMin", "yMin", "xMax", "yMax")]
                units.append(TextUnit(f"{document['id']}:p{p}:l{order}", document["id"],
                    document["sha256"], p, order, raw, box, f"{document['id']}:p{p}:b{b}", document["language"],
                    "pdftotext-bbox-layout").json())
                units[-1]["words"] = words
                order += 1
        if order == 0:
            units.append(TextUnit(f"{document['id']}:p{p}:blank", document["id"], document["sha256"],
                p, 0, "", None, f"{document['id']}:p{p}", document["language"], "blank-or-unread").json())
    if not pages:
        raise ValueError("No PDF pages extracted")
    return units, len(pages), {"extractor": "pdftotext-bbox-layout",
        "raw_xml_sha256": digest(run.stdout), "xml_illegal_characters": removed, "geometry_review": "PENDING"}


def retained_ocr_units(document, root):
    """Consume a pinned existing CPU OCR result, retaining raw word geometry.

    Reviewed transcriptions are a separate interpretation; raw boxes are never
    silently assigned to corrected text with different characters or word order.
    """
    spec=document["ocr"]
    path=bound_path(root,spec["path"])
    if digest(path.read_bytes())!=spec["sha256"]:
        raise ValueError("OCR extraction changed")
    data=read(path)
    if data["source_sha256"]!=document["sha256"] or data["page_count"]!=len(data["pages"]):
        raise ValueError("OCR source identity or page count differs")
    if data["runtime"].get("dpi")!=300 or data["runtime"].get("language")!="eng":
        raise ValueError("Unsupported retained OCR settings; review a new profile")
    units=[]
    for p in data["pages"]:
        groups={}
        for w in p.get("words",[]):
            if len(w)!=8 or not all(isinstance(v,(int,float)) for v in w[:4]):
                raise ValueError("Invalid OCR word geometry")
            # PyMuPDF occasionally emits a sub-pixel negative/overrun at a page
            # edge. It is numerical noise, not evidence that the OCR box is
            # outside the page. Keep the raw extraction hash, but clamp only
            # values within the declared tolerance and record the normalization.
            tolerance = 1e-3
            if not (-tolerance <= w[0] < w[2] <= 10000 + tolerance and
                    -tolerance <= w[1] < w[3] <= 10000 + tolerance):
                raise ValueError("Invalid OCR word geometry")
            w = list(w)
            w[:4] = [min(10000.0, max(0.0, float(v))) for v in w[:4]]
            if not (w[0] < w[2] and w[1] < w[3]):
                raise ValueError("Invalid OCR word geometry")
            groups.setdefault((w[5],w[6]),[]).append(w)
        for order,((block,line),words) in enumerate(groups.items()):
            words.sort(key=lambda w:w[7]);raw=" ".join(w[4] for w in words)
            box=[min(w[0] for w in words),min(w[1] for w in words),max(w[2] for w in words),max(w[3] for w in words)]
            unit=TextUnit(f"{document['id']}:p{p['page']}:ocr{order}",document["id"],document["sha256"],
                          p["page"],order,raw,box,f"{document['id']}:p{p['page']}:b{block}",document["language"],
                          "retained-pymupdf-tesseract").json()
            offset=0;unit["words"]=[]
            for w in words:
                unit["words"].append({"text":w[4],"start":offset,"end":offset+len(w[4]),"bbox":w[:4]})
                offset+=len(w[4])+1
            units.append(unit)
        if not groups:
            units.append(TextUnit(f"{document['id']}:p{p['page']}:ocr-page",document["id"],document["sha256"],
                                  p["page"],0,p["text"],None,f"{document['id']}:p{p['page']}",
                                  document["language"],"retained-original-text-or-blank").json())
    return units,data["page_count"],{"extractor":"retained-ocr","runtime":data["runtime"],
                "ocr_sha256":spec["sha256"],
                "geometry_normalization":"clamp boundary noise <=1e-3 to [0,10000]",
                "geometry_review":"RAW_GEOMETRY; transcription corrections require separate maps"}


def build(bundle, root):
    units, records, unresolved = [], [], []
    for doc in bundle["documents"]:
        path = bound_path(root, doc["path"])
        if digest(path.read_bytes()) != doc["sha256"]:
            raise ValueError("Source bytes changed: " + doc["id"])
        visible, issues = True, []
        issued = doc.get("document_date")
        if not issued:
            issues.append("document date not established")
        elif bundle["purpose"] == "issue_formation" and timestamp(issued) > timestamp(bundle["issue_date"]):
            visible = False
            issues.append("post-issue source excluded from issue formation")
        if not doc.get("known_from"):
            issues.append("knowledge time not established")
        elif timestamp(doc["known_from"]) > timestamp(bundle["known_at"]):
            visible = False
            issues.append("source not known at query knowledge time")
        if doc.get("valid_from") and timestamp(doc["valid_from"]) > timestamp(bundle["effective_at"]):
            visible = False
            issues.append("source not yet effective")
        if doc.get("valid_until") and timestamp(bundle["effective_at"]) >= timestamp(doc["valid_until"]):
            visible = False
            issues.append("source outside recorded effective interval")
        receipt_status = "NOT_SUPPLIED"
        if doc.get("acquisition"):
            a = doc["acquisition"]
            receipt = bound_path(root, a["path"])
            if digest(receipt.read_bytes()) != a["sha256"]:
                raise ValueError("Acquisition receipt changed")
            receipt_status = "BYTES_BOUND; AUTHENTICITY_REQUIRES_REVIEW"
        if doc.get("ocr"):
            extracted, count, extraction = retained_ocr_units(doc, root)
        elif doc.get("format") == "text":
            pages = path.read_text().split("\f")
            extracted = [TextUnit(f"{doc['id']}:p{p}:l0", doc["id"], doc["sha256"], p, 0,
                text, None, f"{doc['id']}:p{p}", doc["language"], "plain-text").json()
                for p, text in enumerate(pages, 1)]
            count, extraction = len(pages), {"geometry_review": "NOT_APPLICABLE_TEXT"}
        else:
            extracted, count, extraction = pdf_units(path, doc)
        if doc.get("page_count", count) != count:
            raise ValueError("Source page count changed")
        units.extend({**u, "visible": visible} for u in extracted)
        records.append({**doc, "page_count": count, "visible": visible, "issues": issues,
                        "acquisition_status": receipt_status, **extraction})
        unresolved.extend({"document": doc["id"], "reason": i} for i in issues)
    references = []
    for unit in units:
        for m in REFERENCE.finditer(unit["raw"]):
            references.append({"id": unit["id"] + f":ref:{m.start()}", "document": unit["document"],
                               "source_sha256": unit["source_sha256"], "unit": unit["id"], "text": m.group(), "target": m.group(1) or m.group(2),
                               "start": m.start(), "end": m.end(), "status": "UNRESOLVED"})
    # Candidate headings preserve edition and occurrence identity. They are not
    # automatically resolved: a repeated number can designate another instrument.
    headings = {}
    for unit in units:
        match = REFERENCE.match(unit["raw"].lstrip())
        if match:
            headings.setdefault((unit["document"], match.group(1) or match.group(2)), []).append(unit["id"])
    for ref in references:
        ref["candidates"] = [u for u in headings.get((ref["document"], ref["target"]), []) if u != ref["unit"]]
    return {"version": "source-graph.v2", "instrument_id": bundle["instrument_id"],
            "context": {k:bundle[k] for k in ("purpose", "issue_date", "effective_at", "known_at")},
            "bundle_sha256": digest(bundle), "documents": records, "units": units,
            "references": references, "unresolved": unresolved,
            "source_authenticity": "CONDITIONAL_ON_RETAINED_ACQUISITION",
            "unit_count": len(units)}
