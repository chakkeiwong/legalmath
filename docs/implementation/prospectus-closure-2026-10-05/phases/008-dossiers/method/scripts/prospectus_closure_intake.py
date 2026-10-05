"""Admission boundary for reviewed derivatives and the frozen candidate."""
from copy import deepcopy
from scripts.prospectus_reviewed_extraction import load

def analyze(reader, issue, documents, root):
    admitted = {}
    for selection in issue["documents"]:
        key = selection["id"]
        meta = documents[key]
        if "review" in meta:
            admitted[key] = load(meta, root)
    raw = reader.analyze_issue(issue, documents, root)
    value = deepcopy(raw)
    for extraction in value["extraction"]:
        key = extraction["document"]
        if key in admitted:
            extraction["legacy_automatic_ocr_performed"] = extraction["automatic_ocr_performed"]
            extraction["automatic_ocr_performed"] = admitted[key]["automatic_ocr_performed"]
            extraction["ocr_provenance"] = {
                field: documents[key][field] for field in
                ("sha256", "raw_sha256", "review_sha256", "text_sha256")
            }
    value["reviewed_admission"] = sorted(admitted)
    return value, raw
