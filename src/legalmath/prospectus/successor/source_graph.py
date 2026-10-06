"""Lossless page/line inventory. Geometry and order remain reviewable premises."""
import re
import subprocess
import xml.etree.ElementTree as ET
from .contracts import TextUnit, bound_path, digest, timestamp

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
                raw = " ".join("".join(w.itertext()) for w in line.findall("x:word", ns))
                box = [float(line.attrib[k]) for k in ("xMin", "yMin", "xMax", "yMax")]
                units.append(TextUnit(f"{document['id']}:p{p}:l{order}", document["id"],
                    document["sha256"], p, order, raw, box, f"p{p}:b{b}", document["language"],
                    "pdftotext-bbox-layout").json())
                order += 1
        if order == 0:
            units.append(TextUnit(f"{document['id']}:p{p}:blank", document["id"], document["sha256"],
                p, 0, "", None, f"p{p}", document["language"], "blank-or-unread").json())
    if not pages:
        raise ValueError("No PDF pages extracted")
    return units, len(pages), {"extractor": "pdftotext-bbox-layout",
        "raw_xml_sha256": digest(run.stdout), "xml_illegal_characters": removed, "geometry_review": "PENDING"}


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
        if doc.get("format") == "text":
            pages = path.read_text().split("\f")
            extracted = [TextUnit(f"{doc['id']}:p{p}:l0", doc["id"], doc["sha256"], p, 0,
                text, None, f"p{p}", doc["language"], "plain-text").json()
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
            references.append({"unit": unit["id"], "text": m.group(), "target": m.group(1) or m.group(2),
                               "start": m.start(), "end": m.end(), "status": "UNRESOLVED"})
    return {"version": "source-graph.v1", "instrument_id": bundle["instrument_id"],
            "bundle_sha256": digest(bundle), "documents": records, "units": units,
            "references": references, "unresolved": unresolved,
            "source_authenticity": "CONDITIONAL_ON_RETAINED_ACQUISITION",
            "unit_count": len(units)}
