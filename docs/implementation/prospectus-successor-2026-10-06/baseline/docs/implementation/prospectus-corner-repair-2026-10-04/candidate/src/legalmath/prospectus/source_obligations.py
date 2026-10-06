"""Quoted source obligations and mechanism conditions; no claim of legal closure."""
import re
from copy import deepcopy
from bisect import bisect_right

from .common import digest
from .loss_absorption_reader import analyze_issue, joined, load_document

REFERENCES = {
    "contract": r"\b(?:agency agreement|trust deed|deed of (?:guarantee|covenant)|fiscal agency agreement)\b",
    "incorporation": r"\b(?:incorporated by reference|incorporation by reference)\b",
    "edition": r"\b(?:base prospectus|offering memorandum|supplement dated|as amended|as supplemented)\b",
    "language": r"\b(?:German language|German version|English translation|English language)\b",
}
CONDITIONS = {
    "trigger": r"trigger|capital ratio|viability|solvency|upon|if |where ",
    "loss_amount": r"amount|principal|nominal|reduc|written|write",
    "restoration": r"restor|write.up|written.up|reinstat",
    "notice": r"notice|notify|notification|publication",
    "authority": r"authority|regulator|FINMA|PRA|resolution|Issuer|Bank",
    "settlement": r"deliver|settle|shares|conversion price|convert",
}


def replay(row, issue, documents, root):
    current = analyze_issue(issue, documents, root)
    # Check every generated field, including conditions, scope and issue identity.
    # Older presentation-only extra fields are permitted but never consumed.
    if any(row.get(k) != value for k, value in current.items()):
        raise ValueError("Feature report changed or belongs to another issue/method")
    return current


def anchor(document_id, source, text, starts, start, end):
    return {"document": document_id, "source_sha256": source,
            "start": start, "end": end, "page": bisect_right(starts, start),
            "end_page": bisect_right(starts, end-1), "quote": text[start:end]}


def build(row, issue, documents, root, *, as_of):
    from ..transaction.evidence import instant
    instant(as_of)
    current = replay(row, issue, documents, root)
    references, bindings = [], []
    for selection in issue["documents"]:
        key = selection["id"]
        doc = load_document(documents[key], root)
        text, starts = joined(doc)
        bindings.append({"document": key, "sha256": documents[key]["sha256"],
                         "text_sha256": documents[key]["text_sha256"],
                         "selection": deepcopy(selection)})
        for kind, pattern in REFERENCES.items():
            for match in re.finditer(pattern, text, re.I):
                a, b = max(0, match.start()-180), min(len(text), match.end()+360)
                item = {"kind": kind, "status": "OPEN_CANDIDATE_REFERENCE",
                        "anchor": anchor(key, doc["source_sha256"], text, starts, a, b),
                        "matched_text": match.group(), "match_start": match.start(),
                        "match_end": match.end()}
                item["id"] = digest(item)[:24]
                references.append(item)
    mechanisms = []
    for e in current["evidence"]:
        if e["disposition"] != "applicable" or e["kind"] not in {"principal_write_down", "mandatory_common_conversion"}:
            continue
        slots = e["semantic_witness"]["slots"]
        mechanisms.append({"evidence_id": e["id"], "kind": e["kind"], "origin": e["origin"],
            "subject": slots.get("subject"), "action": slots.get("action"),
            "modal": slots.get("modal"), "actor": slots.get("actor"),
            "full_condition_quote": {k: e[k] for k in ("document", "source_sha256", "start", "end", "page", "end_page", "quote")},
            "referenced_clauses": re.findall(r"(?:Condition|Section|Article|paragraph|§)\s*[0-9]+(?:[.()]?[a-z0-9]+)*", e["quote"], re.I),
            "conditions": {k: {"status": "QUOTED_NOT_FULLY_RESOLVED" if re.search(pattern, e["quote"], re.I) else "NOT_RESOLVED_BY_THIS_WITNESS",
                                "evidence_id": e["id"] if re.search(pattern, e["quote"], re.I) else None}
                           for k, pattern in CONDITIONS.items()},
            "event_or_loss_calculation": "NOT_ESTABLISHED"})
    result = {"version": "feature-source-obligations.v1", "issue_id": issue["id"],
        "as_of": as_of, "as_of_meaning": "Requested assessment instant; no assertion of current legal completeness",
        "feature_report_sha256": digest(current), "bindings": bindings,
        "references": references, "mechanisms": mechanisms,
        "selected_source_identity": "CHECKED", "reference_discovery": "BOUNDED_HEURISTIC",
        "all_dependencies_found": False, "edition_and_amendment_completeness": "NOT_ESTABLISHED",
        "source_authority": "REQUIRES_SEPARATE_ORIGIN_REVIEW",
        "source_language": issue.get("source_language_qualification", "Controlling language not independently verified"),
        "boundary": issue.get("dependency_boundary", "Other applicable contracts and law have not been exhaustively reconstructed")}
    return {**result, "sha256": digest(result)}


def verify(packet, row, issue, documents, root):
    current = build(row, issue, documents, root, as_of=packet["as_of"])
    if packet != current:
        raise ValueError("Source obligation or mechanism conditions changed")
    return current
