"""Source-bound association of BASF's initial-agent introduction.

This optional report retains introductory provenance without filling the
calculation-agent office or changing the ordinary P3 interpretation.
"""
from copy import deepcopy
from pathlib import Path

from . import basf_body_coverage
from .successor.anchors import fields
from .successor.contracts import digest
from .successor.occurrences import anchor

VERSION = "basf-agent-introduction.v1"
DOC = "basf-base-september-2022-exchange"
FINAL = "basf-2032-final"
RANGES = {
    "introduction": (DOC, 123, 82, 84),
    "initial_fiscal_paying": (DOC, 124, 8, 14),
    "calculation_placeholder": (DOC, 124, 43, 44),
    "office_replacement": (DOC, 124, 45, 47),
    "excluded_cds_branch": (DOC, 124, 22, 25),
    "final_agent_labels": (FINAL, 7, 22, 29),
}
EXPECTED_FINAL = [
    "Fiscal and Paying Agent", "Fiscal Agent und Zahlstelle",
    "Calculation Agent", "Berechnungsstelle",
    "Deutsche Bank Aktiengesellschaft", "Deutsche Bank Aktiengesellschaft",
    "NatWest Markets N.V.", "NatWest Markets N.V.",
]


def _units(products):
    graph = products["P1"]["payload"]["graph"]
    raw = {u["id"]: u for u in graph["units"]}
    selected = {u["unit"]: u for u in products["P2"]["payload"]["assembly"]["units"]}
    if len(raw) != len(graph["units"]):
        raise ValueError("Duplicate original source identity")
    return graph, raw, selected


def source_groups(products):
    graph, raw, selected = _units(products)
    groups = {}
    for name, (document, page, start, end) in RANGES.items():
        rows = []
        for line in range(start, end + 1):
            key = f"{document}:p{page}:l{line}"
            if key not in raw or key not in selected:
                raise ValueError("Complete agent-introduction source unit missing")
            original = raw[key]
            if not original["visible"] or original["text_sha256"] != digest(original["raw"].encode()):
                raise ValueError("Original agent-introduction source changed")
            chosen = selected[key]
            selected_start = 45 if name == "introduction" and line == 82 else 0
            mapping = (basf_body_coverage.selected_sources(graph, chosen, selected_start, len(chosen["text"]), raw=raw)
                       if chosen["text"] else [])
            rows.append({"source": anchor(original), "selected_start": selected_start,
                         "selected_end": len(chosen["text"]),
                         "selected_text": chosen["text"][selected_start:],
                         "assembly_role": chosen["role"], "selected_sources": mapping})
        groups[name] = rows
    intro = " ".join(r["selected_text"] for r in groups["introduction"])
    initial = " ".join(r["selected_text"] for r in groups["initial_fiscal_paying"])
    placeholder = " ".join(r["selected_text"] for r in groups["calculation_placeholder"])
    final = [r["source"]["quote"] for r in groups["final_agent_labels"]]
    if "anfänglich bestellte Fiscal Agent" not in intro or "lauten wie folgt" not in intro:
        raise ValueError("Introductory initially-appointed sentence changed")
    if "Deutsche Bank Aktiengesellschaft" not in initial or "Taunusanlage 12" not in initial:
        raise ValueError("Selected Fiscal/Paying designation changed")
    if placeholder != "Berechnungsstelle: [Name und bezeichnete Geschäftsstelle]":
        raise ValueError("Calculation-agent placeholder changed")
    if any(r["assembly_role"] != "UNKNOWN" for r in groups["introduction"]):
        raise ValueError("Unresolved introduction was promoted")
    if any(r["assembly_role"] != "EXCLUDED" for r in groups["excluded_cds_branch"]):
        raise ValueError("Excluded CDS alternative was selected")
    if final != EXPECTED_FINAL:
        raise ValueError("Final-term agent labels or names changed")
    return groups


def _source_rows(groups, group, role, indexes=None):
    rows = groups[group] if indexes is None else [groups[group][i] for i in indexes]
    return [{"role": role, "source": deepcopy(row["source"]),
             "selected_sources": deepcopy(row["selected_sources"])}
            for row in rows]


def associations(groups):
    """Return directed source links; no link establishes an actual appointment."""
    intro = _source_rows(groups, "introduction", "INTRODUCTION")
    designation = _source_rows(groups, "initial_fiscal_paying", "SELECTED_OPERATIVE_DESIGNATION")
    fiscal_and_paying = _source_rows(groups, "final_agent_labels", "FINAL_TERM_ROLE_AND_NAME", [0, 1, 4, 5])
    calculation = _source_rows(groups, "final_agent_labels", "FINAL_TERM_ROLE_AND_NAME", [2, 3, 6, 7])
    return [
        {"id": "initial-fiscal-agent", "role": "Fiscal Agent", "introduction": intro,
         "designation": designation, "final_term_label": fiscal_and_paying,
         "status": "SELECTED_ROLE_BLOCK",
         "office": "Deutsche Bank Aktiengesellschaft, Taunusanlage 12, 60325 Frankfurt am Main, Bundesrepublik Deutschland",
         "office_status": "SOURCE_REPORTED_SELECTED_BLOCK"},
        {"id": "initial-paying-agent", "role": "Paying Agent", "introduction": intro,
         "designation": designation, "final_term_label": fiscal_and_paying,
         "status": "SELECTED_ROLE_BLOCK",
         "office": "Deutsche Bank Aktiengesellschaft, Taunusanlage 12, 60325 Frankfurt am Main, Bundesrepublik Deutschland",
         "office_status": "SOURCE_REPORTED_SELECTED_BLOCK"},
        {"id": "initial-calculation-agent", "role": "Calculation Agent", "introduction": intro,
         "designation": _source_rows(groups, "calculation_placeholder", "SELECTED_PLACEHOLDER"),
         "final_term_label": calculation, "status": "PLACEHOLDER_REMAINS_UNRESOLVED",
         "office": None, "office_status": "UNRESOLVED", "named_entity": "NatWest Markets N.V.",
         "actual_appointment_or_notice": "NOT_ESTABLISHED"},
    ]


def evaluate(products, prior, profile, root, *, expected_profile_sha256):
    required = {"version", "products_sha256", "prior_sha256", "reviewer", "sources", "groups", "associations",
                "excluded_branch_preserved", "p3_core_changed", "calculation_agent_office",
                "initial_appointment_established", "independent_legal_acceptance"}
    fields(profile, required, required)
    if (profile["version"] != VERSION or digest(profile) != expected_profile_sha256
            or profile["products_sha256"] != digest(products) or profile["prior_sha256"] != digest(prior)):
        raise ValueError("Pinned agent-introduction baseline changed")
    reviewer = profile["reviewer"]
    fields(reviewer, {"identity", "basis", "independent"}, {"identity", "basis", "independent"})
    if (reviewer["identity"] != "Codex supplied original-image review 2026-10-15"
            or reviewer["basis"] != "AGENT_EXPOSED_DEVELOPMENT_REVIEW" or reviewer["independent"] is not False):
        raise ValueError("Unsupported introduction review authority")
    if (profile["excluded_branch_preserved"] is not True or profile["p3_core_changed"] is not False
            or profile["calculation_agent_office"] != "UNRESOLVED"
            or profile["initial_appointment_established"] is not False
            or profile["independent_legal_acceptance"] is not False):
        raise ValueError("Introduction association cannot promote appointment or office authority")
    documents = products["P1"]["payload"]["request"]["bundle"]["documents"]
    sources = profile["sources"]
    if [s.get("document") for s in sources] != [DOC, FINAL]:
        raise ValueError("Both original agent-introduction editions required")
    root = Path(root).resolve()
    for source in sources:
        fields(source, {"document", "path", "sha256", "images"},
               {"document", "path", "sha256", "images"})
        actual = next(d for d in documents if d["id"] == source["document"])
        if (source["path"], source["sha256"]) != (actual["path"], actual["sha256"]):
            raise ValueError("Original agent-introduction PDF identity changed")
        required_pages = [82, 126, 127, 133, 123, 124] if source["document"] == DOC else [7]
        if [item.get("page") for item in source["images"]] != required_pages:
            raise ValueError("Original agent-introduction image inventory changed")
        for item in [source, *source["images"]]:
            path = item["path"]
            resolved = (root / path).resolve()
            if (Path(path).is_absolute() or not resolved.is_relative_to(root)
                    or not resolved.is_file() or digest(resolved.read_bytes()) != item["sha256"]):
                raise ValueError("Original agent-introduction PDF or image changed")
    groups = source_groups(products)
    if profile["groups"] != groups or profile["associations"] != associations(groups):
        raise ValueError("Exact introduction groups or directed role links changed")
    answer = prior.get("answer", {})
    agents = answer.get("basf_agents", {})
    if agents.get("calculation_agent_office") != "UNRESOLVED" or agents.get("independent_legal_acceptance") is not False:
        raise ValueError("Prior conditional agent answer or unresolved office changed")
    questions = prior.get("body_coverage_review", {}).get("remaining_questions", [])
    if not any(q.get("id") == "UNRESOLVED_AGENT_INTRODUCTION" and q.get("status") == "UNRESOLVED"
               for q in questions):
        raise ValueError("Prior unresolved introduction question was removed")
    initial = [r for r in agents.get("readings", []) if r.get("id") == "basf-agents:initial-agent"]
    if len(initial) != 1:
        raise ValueError("Prior initial-agent reading missing or duplicated")
    prior_units = [r["occurrence"]["unit"] for r in initial[0]["source_spans"]]
    expected_units = [f"{DOC}:p124:l{i}" for i in range(8, 15)]
    if prior_units != expected_units:
        raise ValueError("Prior P3 initial-agent source extent changed")
    intro_units = [f"{DOC}:p123:l{i}" for i in range(82, 85)]
    return {"version": VERSION, "profile_sha256": digest(profile), "sources": deepcopy(sources),
        "groups": deepcopy(groups),
        "associations": deepcopy(profile["associations"]), "association_status": "SUPPLEMENTAL_SOURCE_PROVENANCE",
        "p3_initial_agent_source_units": prior_units,
        "supplemental_intro_source_units": intro_units,
        "p3_initially_appointed_provenance_gap": True,
        "initial_appointment_established": False, "calculation_agent_name": "NatWest Markets N.V.",
        "calculation_agent_office": "UNRESOLVED",
        "office_authority_needed": "Applicable original appointment or designated-office authority for this instrument and effective period.",
        "excluded_branch_preserved": True, "p3_core_changed": False,
        "actual_notice_or_change": "NOT_ESTABLISHED",
        "independent_legal_acceptance": False,
        "questions": ["The introduction associates following role blocks with initially appointed agents.",
            "The selected Fiscal/Paying block supplies a source-reported office.",
            "The calculation-agent placeholder remains unfilled although final terms name NatWest Markets N.V."],
        "next_evidence": "Role-specific appointment/designated-office authority, effective-period notices and qualified independent construction."}


def consume(products, prior, profile, root, *, expected_prior_sha256, expected_profile_sha256):
    if digest(prior) != expected_prior_sha256:
        raise ValueError("Pinned meanings013 complete consumer changed")
    result = evaluate(products, prior, profile, root, expected_profile_sha256=expected_profile_sha256)
    return {**deepcopy(prior), "agent_introduction_review": result}
