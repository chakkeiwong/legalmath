"""Source-bound development review of suggestions; no relation admission."""
from copy import deepcopy
from pathlib import Path

from .successor.anchors import bind, fields
from .successor.contracts import digest

VERSION = "relation-review-packet.v1"
DISPOSITIONS = {"REVIEWABLE_PRINTED_RELATION", "WRONG_PRINTED_SCOPE",
                "UNRESOLVED_TRANSCRIPTION"}


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Nonempty review text required")


def _file(root, path, expected):
    if not isinstance(path, str) or Path(path).is_absolute():
        raise ValueError("Repository-relative evidence path required")
    target = (root / path).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError("Evidence file unavailable or outside root")
    if digest(target.read_bytes()) != expected:
        raise ValueError("Evidence file identity changed")


def validate_review_packet(graph, discovery, protected_targets, packet, root):
    """Check provenance and accounting, not the truth of authored judgments.

    Callers provide the pinned graph, discovery result and development targets.
    Exact anchors and file hashes make a judgment inspectable. A valid packet
    cannot establish independent review, legal scope or answer correctness.
    No input is mutated and no discovery or interpretation is rerun.
    """
    required = {"version", "source_graph_sha256", "discovery_sha256",
                "protected_targets_sha256", "reviewer", "sources", "reviews",
                "accepted_relations", "legal_scope_inferred"}
    fields(packet, required, required)
    if (packet["version"] != VERSION or
            packet["source_graph_sha256"] != digest(graph) or
            packet["discovery_sha256"] != digest(discovery) or
            packet["protected_targets_sha256"] != digest(protected_targets)):
        raise ValueError("Review input identity changed")
    if (packet["accepted_relations"] != [] or packet["legal_scope_inferred"] is not False or
            discovery.get("accepted_relations") != [] or
            discovery.get("legal_scope_inferred") is not False or
            discovery.get("source_graph_sha256") != digest(graph)):
        raise ValueError("Review cannot admit governing relations")
    reviewer = packet["reviewer"]
    fields(reviewer, {"identity", "basis", "independent"},
           {"identity", "basis", "independent"})
    _text(reviewer["identity"])
    if (reviewer["basis"] != "AGENT_EXPOSED_DEVELOPMENT_REVIEW" or
            reviewer["independent"] is not False):
        raise ValueError("Unsupported independent-review claim")
    units = {u["id"]: u for u in graph["units"]}
    if len(units) != len(graph["units"]):
        raise ValueError("Duplicate source occurrence")
    for unit in units.values():
        if unit["text_sha256"] != digest(unit["raw"].encode()):
            raise ValueError("Source transcription changed")
    candidates = {}
    for candidate in discovery["candidates"]:
        key = candidate["id"]
        if key in candidates or key != "relation-candidate:" + digest(
                {k: v for k, v in candidate.items() if k != "id"}):
            raise ValueError("Duplicate or altered candidate")
        if candidate.get("status") != "REQUIRES_REVIEW" or candidate.get("legal_scope_established") is not False:
            raise ValueError("Candidate already claims legal acceptance")
        if not candidate.get("from") or not candidate.get("to"):
            raise ValueError("Candidate endpoints required")
        candidates[key] = candidate
    if not candidates:
        raise ValueError("Empty discovery is not a review campaign")
    matches = {key: [] for key in candidates}
    target_ids = set()
    for target in protected_targets:
        fields(target, {"id", "kind", "from", "to"}, {"id", "kind", "from", "to"})
        if target["id"] in target_ids:
            raise ValueError("Duplicate protected target")
        target_ids.add(target["id"])
        found = [key for key, c in candidates.items()
                 if all(c[k] == target[k] for k in ("kind", "from", "to"))]
        if len(found) != 1:
            raise ValueError("Protected target absent or ambiguous")
        matches[found[0]].append(target["id"])
    root = Path(root).resolve()
    pages, documents = {}, set()
    for source in packet["sources"]:
        keys = {"document", "source_path", "source_sha256", "pages"}
        fields(source, keys, keys)
        document = source["document"]
        if document in documents:
            raise ValueError("Duplicate source evidence")
        documents.add(document)
        source_units = [u for u in units.values() if u["document"] == document]
        if not source_units or any(u["source_sha256"] != source["source_sha256"] for u in source_units):
            raise ValueError("Foreign source evidence")
        _file(root, source["source_path"], source["source_sha256"])
        for page in source["pages"]:
            fields(page, {"page", "path", "sha256"}, {"page", "path", "sha256"})
            key = (document, page["page"])
            if type(page["page"]) is not int or page["page"] < 1 or key in pages:
                raise ValueError("Invalid or duplicate rendered page")
            _file(root, page["path"], page["sha256"])
            pages[key] = page
    def checked_anchor(value):
        unit = units.get(value.get("unit"))
        bound = bind({"units": [unit] if unit else []}, value)
        if (bound["document"], bound["page"]) not in pages:
            raise ValueError("Missing rendered source page")
        return bound
    seen = set()
    for row in packet["reviews"]:
        keys = {"candidate_id", "candidate_sha256", "protected_target_ids",
                "disposition", "reason", "repair", "excess", "omitted",
                "transcription_anchors", "evidence_anchors", "transcription_note"}
        fields(row, keys, keys)
        key = row["candidate_id"]
        if key not in candidates or key in seen:
            raise ValueError("Foreign or duplicate reviewed candidate")
        seen.add(key)
        candidate = candidates[key]
        if row["candidate_sha256"] != digest(candidate):
            raise ValueError("Reviewed candidate identity changed")
        if row["protected_target_ids"] != sorted(matches[key]):
            raise ValueError("Protected target accounting changed")
        if row["disposition"] not in DISPOSITIONS:
            raise ValueError("Unsupported review disposition")
        for text_key in ("reason", "repair", "transcription_note"):
            _text(row[text_key])
        endpoints = candidate["from"] + candidate["to"]
        anchors = endpoints + [candidate[k] for k in ("row_marker", "scope_marker") if k in candidate]
        for value in anchors:
            checked_anchor(value)
        evidence = row["evidence_anchors"]
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("Source evidence anchors required")
        if any(a not in evidence for a in anchors):
            raise ValueError("Complete candidate endpoints and markers required in evidence")
        source_pages = {(units[a["unit"]]["document"], units[a["unit"]]["page"]) for a in anchors}
        for group in ("evidence_anchors", "excess", "omitted", "transcription_anchors"):
            values = row[group]
            if not isinstance(values, list) or len({digest(a) for a in values}) != len(values):
                raise ValueError("Duplicate or invalid review anchors")
            for value in values:
                bound = checked_anchor(value)
                if (bound["document"], bound["page"]) not in source_pages:
                    raise ValueError("Review evidence crosses candidate page")
        if any(a not in endpoints for a in row["excess"] + row["transcription_anchors"]):
            raise ValueError("Disputed anchor outside candidate endpoints")
        if any(a in endpoints for a in row["omitted"]):
            raise ValueError("Omitted anchor is already present")
        if any(a not in evidence for a in row["excess"] + row["omitted"] + row["transcription_anchors"]):
            raise ValueError("Disputed anchors lack explicit evidence")
        if row["disposition"] == "WRONG_PRINTED_SCOPE" and not (row["excess"] or row["omitted"]):
            raise ValueError("Wrong scope requires exact excess or omission")
        if row["disposition"] == "UNRESOLVED_TRANSCRIPTION" and not row["transcription_anchors"]:
            raise ValueError("Transcription uncertainty requires exact anchors")
        if row["disposition"] == "REVIEWABLE_PRINTED_RELATION" and any(row[k] for k in ("excess", "omitted", "transcription_anchors")):
            raise ValueError("Reviewable relation has unresolved endpoint disputes")
    if seen != set(candidates):
        raise ValueError("Incomplete candidate review coverage")
    return {"version": VERSION, "packet": deepcopy(packet),
            "packet_sha256": digest(packet), "candidate_count": len(seen),
            "protected_target_count": len(target_ids),
            "additional_candidate_count": sum(not matches[k] for k in seen),
            "dispositions": {d: sum(r["disposition"] == d for r in packet["reviews"])
                             for d in sorted(DISPOSITIONS)},
            "accepted_relations": [], "legal_scope_inferred": False,
            "independent_legal_acceptance": False, "may_change_answer": False}
