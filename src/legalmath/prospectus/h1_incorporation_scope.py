"""Two conditional source-scope readings of BES prospectus p37(e).

This finite optional reader preserves source membership under supplied
constructions. It does not decide which construction has legal authority.
"""
from collections import Counter
from copy import deepcopy
from pathlib import Path

from . import h1_risk_tables
from .successor.anchors import bind, fields
from .successor.contracts import digest
from .successor.occurrences import anchor

VERSION = "bes-h1-incorporation-scope-review.v1"
INTRO = "bes-base-2010"
REPORT = "bes-interim-h1-2010"
SOURCE_HASHES = {"introducer": "f6391acb72db7f88fb5b51df8bd0668a747580ddf6357bc00c0b7e5347b80d60",
    "report": "b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7"}
IMAGES = {"introducer": [(37, "72e31eb3296655cf8bd92c2786a73e7aaa630a9032c929596cff17eafe690eaa")],
    "report": [(55, "63574b61c6692f5d39bae590641fb8e08c7fba3afcf448209e3c459fa5451bae"),
               (59, "b2bb3f9f85bcdaea7f871c32ce3f3e62a3918a62fb4df9d9117892b0579bd8f8")]}
INTRO_HASH = "12f282bb951f5da8f8cef52af33b075521fee9e8da6447548f747b9dea801b8e"
TARGET_HASH = "8f5f6b89c115ed9f13851b86c845434e9c4ff6c61e1362326c942b0dd510bc39"
INTRO_GROUPS = {"heading": [0], "restriction": [1,2,3], "item-e-label": [20], "identity-and-range": [45,46],
    "income-subitem": [47,48], "balance-subitem": [49,50], "cash-flow-subitem": [51,52],
    "notes-subitem": [53,54], "report-subitem": [55,56],
    "other-items": [i for i in range(4,45) if i != 20], "next-item": [57,58,59], "footer-and-native-metadata": list(range(60,73))}
ENUMERATED = {"income": [52,54,56,57], "balance": [51,53,58], "cash-flow": [60],
    "notes": list(range(61,172)), "auditor-report": [172,173]}
CONSTRUCTIONS = (
    {"id": "overall-range", "basis": "Overall51–173 range and including treated as non-exhaustive", "pages": list(range(51,174))},
    {"id": "enumerated-information", "basis": "Specific enumerated pages read with the introductory information-only restriction",
     "pages": sorted({p for pages in ENUMERATED.values() for p in pages})},
)
CHARACTERIZATIONS = [
    {"page": 55, "role": "SECTION_DIVIDER", "title": "II. INTERIM CONSOLIDATED FINANCIAL STATEMENTS AND NOTES",
     "title_units": [REPORT + ":p55:l1", REPORT + ":p55:l2"], "period_unit": None,
     "dates": [], "complete_financial_reading": False, "source_limit": "Section divider; no financial table"},
    {"page": 59, "role": "CONSOLIDATED_CHANGES_IN_EQUITY", "title": "CONSOLIDATED STATEMENT OF CHANGES IN EQUITY",
     "title_units": [REPORT + ":p59:l2"], "period_unit": REPORT + ":p59:l3",
     "dates": ["2010-06-30", "2009-12-31", "2009-06-30"], "complete_financial_reading": False,
     "source_limit": "Right-hand total-equity figures and unit text are clipped in both the retained render and native reading; no complete numerical reading supplied"},
]
LIMITS = {"financial_values_validated": False, "independent_legal_acceptance": False,
    "source_authenticity_established": False, "historical_publication_established": False,
    "individual_statement_audit_opinion": False, "selected_reading": None}
PRIOR_KEYS = ("answer", "cash_flow_review", "cash_flow_explanation", "risk_table_review", "risk_table_explanation")


def original_targets(graph):
    return [u for u in graph["units"] if u["document"] == REPORT and 51 <= u["page"] <= 173]


def membership_delta(first, second):
    """Set difference with duplicate detection; source ordering stays inspectable."""
    for items in (first, second):
        if not isinstance(items, list) or len(set(items)) != len(items):
            raise ValueError("Unique ordered source memberships required")
    a, b = set(first), set(second)
    return {"common": [x for x in first if x in b], "first_only": [x for x in first if x not in b],
            "second_only": [x for x in second if x not in a]}


def make_profile(graph, prior, source):
    units = {u["id"]: u for u in graph["units"]}
    def group(ids):
        return [anchor(units[INTRO + ":p37:l" + str(i)]) for i in ids]
    target = original_targets(graph)
    return {"version": VERSION, "graph_sha256": digest(graph), "prior_sha256": digest(prior),
        "source": deepcopy(source), "reviewer": {"identity": "Codex original H1 incorporation-scope reading 2026-10-16",
            "basis": "AGENT_EXPOSED_DEVELOPMENT_REVIEW", "independent": False},
        "intro": {key: group(ids) for key, ids in INTRO_GROUPS.items()},
        "period": {"end": "2010-06-30", "months": 6}, "enumerated_subitems": deepcopy(ENUMERATED),
        "candidates": [{**deepcopy(c), "source_units": [u["id"] for u in target if u["page"] in c["pages"]]} for c in CONSTRUCTIONS],
        "difference_pages": deepcopy(CHARACTERIZATIONS), "limits": deepcopy(LIMITS)}


def evaluate(graph, prior, profile, root, *, expected_profile_sha256):
    keys = {"version", "graph_sha256", "prior_sha256", "source", "reviewer", "intro", "period",
            "enumerated_subitems", "candidates", "difference_pages", "limits"}
    fields(profile, keys, keys)
    if (profile["version"] != VERSION or digest(profile) != expected_profile_sha256
            or profile["graph_sha256"] != digest(graph) or profile["prior_sha256"] != digest(prior)):
        raise ValueError("Pinned H1 scope profile, graph or complete prior consumer changed")
    if profile["limits"] != LIMITS:
        raise ValueError("Conditional scope cannot establish legal selection, financial validation or source authority")
    reviewer = profile["reviewer"]
    fields(reviewer, {"identity", "basis", "independent"}, {"identity", "basis", "independent"})
    if (not isinstance(reviewer["identity"], str) or not reviewer["identity"].strip()
            or reviewer["basis"] != "AGENT_EXPOSED_DEVELOPMENT_REVIEW" or reviewer["independent"] is not False):
        raise ValueError("Unsupported H1 scope review authority")
    if profile["period"] != {"end": "2010-06-30", "months": 6}:
        raise ValueError("Original Bank six-month H1 period required")
    fields(profile["source"], {"introducer", "report"}, {"introducer", "report"})
    root = Path(root).resolve()
    for key, document in (("introducer", INTRO), ("report", REPORT)):
        source = profile["source"][key]
        fields(source, {"document", "path", "sha256", "images"}, {"document", "path", "sha256", "images"})
        if source["document"] != document or source["sha256"] != SOURCE_HASHES[key]:
            raise ValueError("Original H1 scope source editions required")
        if not isinstance(source["images"], list) or len(source["images"]) != len(IMAGES[key]):
            raise ValueError("Complete reviewed H1 scope image inventory required")
        for image, (page, sha) in zip(source["images"], IMAGES[key]):
            fields(image, {"page", "path", "sha256"}, {"page", "path", "sha256"})
            if image["page"] != page or image["sha256"] != sha:
                raise ValueError("Original reviewed H1 scope image changed")
        for item in [source, *source["images"]]:
            name = item["path"]
            path = (root / name).resolve()
            if Path(name).is_absolute() or not path.is_relative_to(root) or not path.is_file() or digest(path.read_bytes()) != item["sha256"]:
                raise ValueError("Original H1 scope source/image unavailable or changed")
    units = {u["id"]: u for u in graph["units"]}
    intro = [u for u in graph["units"] if u["document"] == INTRO and u["page"] == 37]
    target = original_targets(graph)
    if (len(units) != len(graph["units"]) or len(intro) != 73 or digest(intro) != INTRO_HASH
            or len(target) != 12777 or digest(target) != TARGET_HASH
            or any(not u["visible"] for u in intro + target)):
        raise ValueError("Complete original introduction and H1 target occurrences required")
    fields(profile["intro"], INTRO_GROUPS, INTRO_GROUPS)
    used, intro_result = [], {}
    for key, ids in INTRO_GROUPS.items():
        values = profile["intro"][key]
        if not isinstance(values, list) or len(values) != len(ids):
            raise ValueError("Complete H1 introduction source-fragment inventory required")
        intro_result[key] = []
        for a, i in zip(values, ids):
            unit = units[INTRO + ":p37:l" + str(i)]
            if a != anchor(unit):
                raise ValueError("Exact original H1 introduction occurrence/character association required")
            intro_result[key].append(bind({"units": [unit]}, a))
            used.append(unit["id"])
    if Counter(used) != Counter(u["id"] for u in intro):
        raise ValueError("Every original introductory-page character must occur exactly once")
    if profile["enumerated_subitems"] != ENUMERATED:
        raise ValueError("Exact original H1 enumerated subitem page sets required")
    if not isinstance(profile["candidates"], list) or [c["id"] for c in profile["candidates"]] != [c["id"] for c in CONSTRUCTIONS]:
        raise ValueError("Both original conditional scope constructions required")
    candidates = []
    for candidate, expected in zip(profile["candidates"], CONSTRUCTIONS):
        fields(candidate, {"id", "basis", "pages", "source_units"}, {"id", "basis", "pages", "source_units"})
        if candidate["basis"] != expected["basis"] or candidate["pages"] != expected["pages"]:
            raise ValueError("Exact conditional H1 page membership and construction basis required")
        selected = [u["id"] for u in target if u["page"] in expected["pages"]]
        if candidate["source_units"] != selected:
            raise ValueError("Complete ordered conditional H1 target occurrences required")
        candidates.append({**deepcopy(candidate), "status": "CONDITIONAL_SUPPLIED_SCOPE",
            "page_count": len(expected["pages"]), "source_occurrences": len(selected),
            "independent_legal_acceptance": False})
    if profile["difference_pages"] != CHARACTERIZATIONS:
        raise ValueError("Exact divider/equity roles, periods and incomplete financial-reading limits required")
    delta = membership_delta(candidates[0]["source_units"], candidates[1]["source_units"])
    page_delta = membership_delta(candidates[0]["pages"], candidates[1]["pages"])
    if page_delta["first_only"] != [55,59] or page_delta["second_only"] or len(delta["first_only"]) != 468:
        raise ValueError("Original H1 difference must preserve55/59 and468 occurrences")
    fields(prior, PRIOR_KEYS, PRIOR_KEYS)
    answer = prior["answer"]
    original_ids = {"BES-DEP-" + str(n).zfill(2) for n in range(1,12)} | {"BES-DEP-AGENCY-" + str(n).zfill(2) for n in range(1,4)}
    deps = [d for d in answer["dependencies"] if d["id"] in original_ids]
    if (answer["questions"]["Q3"]["status"] != "PARTIAL" or answer["may_execute_transaction"] is not False
            or answer["independent_legal_acceptance"] is not False or len(deps) != 14
            or {d["id"] for d in deps} != original_ids or any(d["status"] != "UNRESOLVED" for d in deps)
            or prior["risk_table_review"]["source_occurrences"] != 933
            or prior["cash_flow_review"]["source_occurrences"] != 166):
        raise ValueError("Complete unresolved prior answer, cash-flow and risk readings required")
    # Complete source pool is retained once. Candidate/difference lists refer
    # to original occurrence IDs rather than inventing copied text or geometry.
    pool = [{**bind({"units": [u]}, anchor(u)), "original_words": deepcopy(u.get("words", [])),
             "original_extraction_image_sha256": u.get("image_sha256")} for u in target]
    return {"version": VERSION, "status": "CONDITIONAL_INCORPORATION_SCOPE", "source": deepcopy(profile["source"]),
        "graph_sha256": digest(graph), "profile_sha256": digest(profile), "prior_sha256": digest(prior),
        "reviewer": deepcopy(reviewer), "intro": intro_result, "introduction_occurrences": 73,
        "complete_intro_characters_once": True, "target_sources": pool, "target_occurrences": len(pool),
        "all_target_characters_once_in_pool": True, "candidates": candidates, "difference": delta, "page_difference": page_delta,
        "difference_pages": deepcopy(CHARACTERIZATIONS), "enumerated_subitems": deepcopy(ENUMERATED),
        "period": deepcopy(profile["period"]), "limits": deepcopy(LIMITS)}


def explain(review):
    common = set(review["page_difference"]["common"])
    return {"question": "Does p37(e) include the complete51–173 range or only its enumerated information?",
        "constructions": [{"id": c["id"], "basis": c["basis"], "pages": c["pages"],
            "page_count": c["page_count"], "source_occurrences": c["source_occurrences"]} for c in review["candidates"]],
        "difference_pages": deepcopy(review["difference_pages"]), "difference_occurrences": len(review["difference"]["first_only"]),
        "common_occurrences": len(review["difference"]["common"]),
        "source_wording": {key: "\n".join(a["quote"] for a in review["intro"][key]) for key in
            ("restriction", "identity-and-range", "income-subitem", "balance-subitem", "cash-flow-subitem", "notes-subitem", "report-subitem")},
        "downstream_effects": {"cash_flow_page60_common": 60 in common, "risk_pages162_163_common": {162,163} <= common,
            "page55": "The overall-range construction includes the section divider; the enumerated-information construction does not.",
            "page59": "The overall-range construction includes the changes-in-equity statement and its footnotes; the enumerated-information construction does not. Neither construction supplies a complete numeric reading.",
            "prior_source_readings": "Preserved in full; common page membership does not establish their legal authority or financial validity."},
        "assurance_limit": "The retained moderate-assurance limited review concerns consolidated interim information. It is not an audit opinion and does not establish assurance on the individual statements.",
        "unresolved_authority": "Controlling interpretation of including and the introductory restriction, the applicable edition/Portuguese priority, authenticity and independent adjudication remain required.",
        "financial_reading_limit": CHARACTERIZATIONS[1]["source_limit"],
        "selected_reading": None, "actual_incorporation_resolved": False,
        "legal_dependency_resolution": "UNCHANGED", "independent_legal_acceptance": False}


def consume(products, cash_profile, risk_profile, profile, root, *, expected_cash_profile_sha256,
            expected_risk_profile_sha256, expected_profile_sha256, unit_profile=None,
            expected_unit_profile_sha256=None, relationship_profile=None,
            expected_relationship_profile_sha256=None, reference_profile=None,
            expected_reference_profile_sha256=None, context_profile=None,
            expected_context_profile_sha256=None):
    if context_profile is None and expected_context_profile_sha256 is not None:
        raise ValueError('Statement context profile missing for supplied identity')
    if context_profile is not None and any(v is None for v in
            (unit_profile, relationship_profile, reference_profile, expected_context_profile_sha256)):
        raise ValueError('Current unit, relationship and reference profiles required for statement context')
    prior = h1_risk_tables.consume(products, cash_profile, risk_profile, root,
        expected_cash_flow_profile_sha256=expected_cash_profile_sha256, expected_profile_sha256=expected_risk_profile_sha256)
    review = evaluate(products["P1"]["payload"]["graph"], prior, profile, root, expected_profile_sha256=expected_profile_sha256)
    answer = {**prior, "h1_scope_review": review, "h1_scope_explanation": explain(review)}
    if unit_profile is None:
        if expected_unit_profile_sha256 is not None:
            raise ValueError('H1 unit profile missing for supplied identity')
        if relationship_profile is not None or expected_relationship_profile_sha256 is not None:
            raise ValueError('Current H1 unit review required for source relationships')
        if reference_profile is not None or expected_reference_profile_sha256 is not None:
            raise ValueError('Current H1 source relationships required for reference availability')
        return answer
    from . import h1_unit_conflict
    unit_review = h1_unit_conflict.evaluate(products['P1']['payload']['graph'], answer, unit_profile, root,
        expected_profile_sha256=expected_unit_profile_sha256)
    answer = {**answer, 'h1_individual_unit_review': unit_review,
              'h1_individual_unit_explanation': h1_unit_conflict.explain(unit_review)}
    if relationship_profile is None:
        if expected_relationship_profile_sha256 is not None:
            raise ValueError('H1 relationship profile missing for supplied identity')
        if reference_profile is not None or expected_reference_profile_sha256 is not None:
            raise ValueError('Current H1 source relationships required for reference availability')
        return answer
    from . import h1_source_relationships
    relationships = h1_source_relationships.evaluate(products['P1']['payload']['graph'],
        answer, relationship_profile, expected_profile_sha256=expected_relationship_profile_sha256)
    answer = {**answer, 'h1_source_relationship_review': relationships,
              'h1_source_relationship_explanation': h1_source_relationships.explain(relationships)}
    if reference_profile is None:
        if expected_reference_profile_sha256 is not None:
            raise ValueError('H1 reference profile missing for supplied identity')
        return answer
    from . import h1_reference_availability
    references = h1_reference_availability.evaluate(products['P1']['payload']['graph'],
        answer, reference_profile, expected_profile_sha256=expected_reference_profile_sha256)
    answer = {**answer, 'h1_reference_availability_review': references,
              'h1_reference_availability_explanation': h1_reference_availability.explain(references)}
    if context_profile is None:
        return answer
    from . import h1_statement_context
    context = h1_statement_context.evaluate(products['P1']['payload']['graph'], answer, context_profile,
        expected_profile_sha256=expected_context_profile_sha256)
    return {**answer, 'h1_statement_context_review': context,
            'h1_statement_context_explanation': h1_statement_context.explain(context)}
