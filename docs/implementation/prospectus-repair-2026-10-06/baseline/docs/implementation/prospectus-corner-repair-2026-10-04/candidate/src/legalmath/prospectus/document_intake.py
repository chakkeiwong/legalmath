"""Explicit extraction coverage and dated document dependency validation."""
from datetime import date
from pathlib import Path
from .common import sha


def extraction_coverage(document, selection):
    pages = document["pages"]
    selected = {p for a,b in selection.get("operative_pages", [[1,len(pages)]])
                for p in range(a,b+1)}
    reviewed = document.get("reviewed_blank_pages", [])
    if (not isinstance(reviewed, list) or any(type(p) is not int or p not in selected for p in reviewed)):
        raise ValueError("Invalid reviewed blank pages")
    # A declaration alone is insufficient: every blank disposition needs a reviewed source record.
    reviews = document.get("blank_page_reviews", {})
    for p in reviewed:
        if not isinstance(reviews.get(str(p)), dict) or not reviews[str(p)].get("reviewed_image_sha256"):
            raise ValueError("Blank-page review provenance missing")
    empty = [p for p in sorted(selected) if not pages[p-1]["text"].strip() and p not in reviewed]
    status = "OCR_REQUIRED" if len(empty) == len(selected) else "PARTIAL_TEXT" if empty else "TEXT_PRESENT"
    return {"status": status, "empty_selected_pages": empty,
            "selected_pages": sorted(selected), "reviewed_blank_pages": reviewed,
            "coverage_complete": not empty, "automatic_ocr_performed": False}


def validate_bundle(issue, documents, root):
    """Validate a reviewed dependency contract, never infer editions from recency."""
    contract = issue.get("document_contract")
    if contract is None:
        return {"status": "NOT_DECLARED", "issues": [], "legal_completeness": "NOT_ESTABLISHED"}
    problems, bound = [], []
    if not isinstance(contract, dict):
        raise ValueError("Document contract must be an object")
    required = contract.get("required_documents", [])
    if not required or len({r["id"] for r in required}) != len(required):
        raise ValueError("Nonempty distinct required documents needed")
    if issue.get("issuer") != contract.get("issuer"):
        problems.append("ISSUER_MISMATCH")
    if issue.get("security_class") != contract.get("security_class"):
        problems.append("SECURITY_CLASS_MISMATCH")
    if issue.get("issue_date") != contract.get("issue_date"):
        problems.append("ISSUE_DATE_MISMATCH")
    issued = date.fromisoformat(contract["issue_date"])
    selected = [s["id"] for s in issue["documents"]]
    expected = {r["id"] for r in required}
    if set(selected) != expected or len(selected) != len(set(selected)):
        problems.append("DEPENDENCY_SET_MISMATCH")
    for expected_row in required:
        key = expected_row["id"]
        actual = documents.get(key)
        if actual is None:
            problems.append("MISSING_DOCUMENT:" + key)
            continue
        fields = ("sha256", "role", "edition_date", "base_id")
        if any(actual.get(k) != expected_row.get(k) for k in fields):
            problems.append("EDITION_OR_ROLE_MISMATCH:" + key)
        if date.fromisoformat(actual["edition_date"]) > issued:
            problems.append("POST_ISSUE_DOCUMENT:" + key)
        if contract["issuer"] not in actual.get("programme_issuers", []):
            problems.append("ISSUER_NOT_COVERED:" + key)
        if actual.get("role") == "final_terms":
            if actual.get("issuer") != contract["issuer"]:
                problems.append("FINAL_TERMS_ISSUER_MISMATCH:" + key)
            if actual.get("security_class") != contract["security_class"]:
                problems.append("FINAL_TERMS_CLASS_MISMATCH:" + key)
            if set(actual.get("identifiers", [])) != set(issue.get("identifiers", [])):
                problems.append("FINAL_TERMS_IDENTIFIER_MISMATCH:" + key)
        if actual.get("role") == "supplement" and actual.get("base_id") not in expected:
            problems.append("SUPPLEMENT_BASE_MISSING:" + key)
        source = Path(root) / actual["original"]
        if not source.is_file() or sha(source.read_bytes()) != expected_row["sha256"]:
            problems.append("SOURCE_CHANGED:" + key)
        bound.append({"id": key, "sha256": expected_row["sha256"], "role": expected_row["role"]})
    problems.extend("OPEN_DEPENDENCY:" + x for x in contract.get("unresolved_dependencies", []))
    if contract.get("precedence_reviewed") is not True:
        problems.append("PRECEDENCE_NOT_REVIEWED")
    return {"status": "UNRESOLVED" if problems else "BOUND",
            "issues": sorted(set(problems)), "source_bindings": bound,
            "legal_completeness": "NOT_INDEPENDENTLY_ADJUDICATED"}
