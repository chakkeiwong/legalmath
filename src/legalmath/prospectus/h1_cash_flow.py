"""Optional complete supplied image reading of one original H1 cash-flow page.

Raw OCR remains immutable. Supplied printed literals, image-backed corrections,
arithmetic observations and legal scope have separate representations.
"""
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import re

from . import h1_cash_flow_spec as spec
from .successor.anchors import bind, fields
from .successor.contracts import digest
from .successor.occurrences import anchor
from .successor import service

VERSION = "bes-h1-cash-flow-review.v1"
IMAGE = "14d3a524ccf1ef99a4d4bea1690f2c215536089fbc0310206d534e6f58348b75"
PAGE_UNITS = "e83e5301ac0169a9f23f947457acee057a3ac8a1d33b207504dabf977ed30865"
BASIS = "SUPPLIED_ORIGINAL_IMAGE_READING"


def quantity(literal):
    """Parse reviewed signed integer thousands; never repair raw OCR implicitly."""
    if literal == "-":
        return {"printed": literal, "status": "PRINTED_DASH_UNKNOWN", "integer_thousands": None, "unit": "thousand EUR"}
    if not isinstance(literal, str):
        raise ValueError("Reviewed money literal required")
    negative = literal.startswith("(") and literal.endswith(")")
    text = literal[1:-1] if negative else literal
    if re.fullmatch(r"(?:0|[1-9][0-9]{0,2}(?: [0-9]{3})*)", text) is None:
        raise ValueError("Reviewed grouped integer thousands or printed dash required")
    value = int(text.replace(" ", "")) * (-1 if negative else 1)
    return {"printed": literal, "status": "REVIEWED_PRINTED_INTEGER", "integer_thousands": value, "unit": "thousand EUR"}


def span(unit, selector):
    if ":" not in selector:
        return 0, len(unit["raw"])
    name, side = selector.split(":")
    if name != "ocr126" or unit["raw"] != "(4687 606) 6888 625" or side not in {"left", "separator", "right"}:
        raise ValueError("Original merged financing occurrence changed")
    return {"left": (0,10), "separator": (10,11), "right": (11,19)}[side]


def make_profile(graph, prior, source):
    units = {u["id"].rsplit(":", 1)[1]: u for u in graph["units"] if u["document"] == spec.DOCUMENT and u["page"] == spec.PAGE}
    def group(selectors):
        return [anchor(units[s.split(":")[0]], *span(units[s.split(":")[0]], s)) for s in selectors]
    return {"version": VERSION, "graph_sha256": digest(graph), "prior_sha256": digest(prior), "source": deepcopy(source),
        "reviewer": {"identity": "Codex complete original page60 image reading 2026-10-16",
            "basis": "AGENT_EXPOSED_DEVELOPMENT_REVIEW", "independent": False},
        "years": list(spec.YEARS), "unit": "thousand EUR", "context": {k: group(ids) for k, ids in spec.CONTEXT.items()},
        "separator": group(["ocr126:separator"]),
        "rows": [{"id": r["id"], "section": r["section"], "role": r["role"], "label": group(r["label"]),
            "notes": group(r["notes"]), "cells": {year: {"source": group(ids), "printed": literal, "basis": BASIS}
                for year, ids, literal in zip(spec.YEARS, r["cells"], r["printed"])}} for r in spec.ROWS],
        "financial_values_validated": False, "selected_reading": None}


def arithmetic(rows):
    indexed = {r["id"]: r for r in rows}
    result = []
    for name, target, components in spec.CHECKS:
        for year in spec.YEARS:
            left = indexed[target]["cells"][year]["quantity"]["integer_thousands"]
            values = [indexed[key]["cells"][year]["quantity"]["integer_thousands"] for key in components]
            missing = [key for key, value in zip(components, values) if value is None]
            right = None if missing else sum(values)
            delta = None if left is None or right is None else left - right
            result.append({"name": name, "year": year, "target": target, "components": components,
                "printed_target": left, "component_sum": right, "unknown_components": missing,
                "left_minus_right": delta, "unit": "thousand EUR",
                "status": "UNKNOWN_COMPONENT" if delta is None else "EQUAL_PRINTED_VALUES" if delta == 0 else "PRINTED_DIFFERENCE",
                "diagnostic_role": "EXPLANATORY_ONLY"})
    return result


def evaluate(graph, prior, profile, root, *, expected_profile_sha256):
    keys = {"version", "graph_sha256", "prior_sha256", "source", "reviewer", "years", "unit", "context",
        "separator", "rows", "financial_values_validated", "selected_reading"}
    fields(profile, keys, keys)
    if (profile["version"] != VERSION or digest(profile) != expected_profile_sha256
            or profile["graph_sha256"] != digest(graph) or profile["prior_sha256"] != digest(prior)):
        raise ValueError("Pinned H1 profile, graph or complete previous answer changed")
    if profile["financial_values_validated"] is not False or profile["selected_reading"] is not None:
        raise ValueError("Cash-flow reading cannot validate accounts or select legal incorporation")
    if profile["years"] != list(spec.YEARS) or profile["unit"] != "thousand EUR":
        raise ValueError("Original six-month periods and thousand-euro unit required")
    reviewer = profile["reviewer"]
    fields(reviewer, {"identity", "basis", "independent"}, {"identity", "basis", "independent"})
    if (not isinstance(reviewer["identity"], str) or not reviewer["identity"].strip()
            or reviewer["basis"] != "AGENT_EXPOSED_DEVELOPMENT_REVIEW" or reviewer["independent"] is not False):
        raise ValueError("Unsupported cash-flow review authority")
    source = profile["source"]
    fields(source, {"document", "page", "path", "sha256", "image"}, {"document", "page", "path", "sha256", "image"})
    fields(source["image"], {"path", "sha256"}, {"path", "sha256"})
    if (source["document"] != spec.DOCUMENT or source["page"] != spec.PAGE or source["sha256"] != spec.SOURCE
            or source["image"]["sha256"] != IMAGE):
        raise ValueError("Original H1 PDF and reviewed page image required")
    root = Path(root).resolve()
    for item in (source, source["image"]):
        name = item["path"]
        path = (root / name).resolve()
        if Path(name).is_absolute() or not path.is_relative_to(root) or not path.is_file() or digest(path.read_bytes()) != item["sha256"]:
            raise ValueError("Original H1 source/image changed or unavailable")
    pages = [u for u in graph["units"] if u["document"] == spec.DOCUMENT and u["page"] == spec.PAGE]
    if (len(pages) != 166 or digest(pages) != PAGE_UNITS or any(not u["visible"] for u in pages)
            or len({u["id"] for u in graph["units"]}) != len(graph["units"])):
        raise ValueError("Complete original H1 page occurrences changed")
    units = {u["id"].rsplit(":", 1)[1]: u for u in pages}
    used = defaultdict(list)

    def original(anchors, selectors):
        if not isinstance(anchors, list) or len(anchors) != len(selectors):
            raise ValueError("Complete cash-flow source-fragment inventory required")
        result = []
        for a, selector in zip(anchors, selectors):
            unit = units[selector.split(":")[0]]
            start, end = span(unit, selector)
            expected = anchor(unit, start, end)
            if a != expected:
                raise ValueError("Exact original cash-flow occurrence/character association required")
            bound = bind(graph, a)
            used[unit["id"]].append((start, end))
            result.append(bound)
        return result

    fields(profile["context"], spec.CONTEXT, spec.CONTEXT)
    context = {k: original(profile["context"][k], ids) for k, ids in spec.CONTEXT.items()}
    separator = original(profile["separator"], ["ocr126:separator"])
    if [a["quote"] for a in separator] != [" "]:
        raise ValueError("Merged financing separator changed")
    if not isinstance(profile["rows"], list) or [r["id"] for r in profile["rows"]] != [r["id"] for r in spec.ROWS]:
        raise ValueError("Complete ordered cash-flow row inventory required")
    rows, corrections = [], []
    for row, expected in zip(profile["rows"], spec.ROWS):
        fields(row, {"id", "section", "role", "label", "notes", "cells"}, {"id", "section", "role", "label", "notes", "cells"})
        if row["section"] != expected["section"] or row["role"] != expected["role"]:
            raise ValueError("Cash-flow section or balance/flow role changed")
        label, notes = original(row["label"], expected["label"]), original(row["notes"], expected["notes"])
        fields(row["cells"], spec.YEARS, spec.YEARS)
        cells = {}
        for year, ids, literal in zip(spec.YEARS, expected["cells"], expected["printed"]):
            cell = row["cells"][year]
            fields(cell, {"source", "printed", "basis"}, {"source", "printed", "basis"})
            if cell["printed"] != literal or cell["basis"] != BASIS:
                raise ValueError("Reviewed original-image money literal or correction basis changed")
            sources = original(cell["source"], ids)
            raw = " ".join(a["quote"] for a in sources)
            change = "IMAGE_CONFIRMED" if raw == literal else "SPACING_READING" if "".join(raw.split()) == "".join(literal.split()) else "OCR_CHARACTER_CORRECTION"
            cells[year] = {"raw_ocr": raw, "source": sources, "quantity": quantity(literal), "basis": BASIS,
                "reading_relation": change, "reviewed_image_sha256": IMAGE,
                "geometry": "ORIGINAL_WHOLE_OCCURRENCE_BOX; character spans retain original source identity"}
            if change == "OCR_CHARACTER_CORRECTION":
                corrections.append({"row": row["id"], "year": year, "raw_ocr": raw, "printed": literal,
                    "source": sources, "basis": BASIS, "image_sha256": IMAGE})
        rows.append({"id": row["id"], "section": row["section"], "role": row["role"], "label": label, "notes": notes, "cells": cells})
    if set(used) != {u["id"] for u in pages}:
        raise ValueError("Missing or extra cash-flow occurrence")
    for unit in pages:
        end = 0
        for start, stop in sorted(used[unit["id"]]):
            if start != end or stop <= start:
                raise ValueError("Each original cash-flow character must occur exactly once")
            end = stop
        if end != len(unit["raw"]):
            raise ValueError("Incomplete original cash-flow character coverage")
    if (prior["may_execute_transaction"] is not False or prior["independent_legal_acceptance"] is not False
            or prior["questions"]["Q3"]["status"] != "PARTIAL"):
        raise ValueError("Original unresolved legal and transaction limits required")
    original_ids = {"BES-DEP-" + str(n).zfill(2) for n in range(1, 12)} | {"BES-DEP-AGENCY-" + str(n).zfill(2) for n in range(1, 4)}
    dependencies = [d for d in prior["dependencies"] if d["id"] in original_ids]
    if {d["id"] for d in dependencies} != original_ids or len(dependencies) != 14 or any(d["status"] != "UNRESOLVED" for d in dependencies):
        raise ValueError("All fourteen original BES dependencies must remain unresolved")
    reports = {r["id"]: r for r in prior["source_reports"]}
    if (set(reports) != {"context", "limited-review", "cash-flow", "risk-tables"}
            or reports["limited-review"]["status"] != "CONDITIONAL_SUPPLIED_READING"
            or any(reports[k]["status"] != "INCOMPLETE_SOURCE_READING" for k in ("cash-flow", "risk-tables"))):
        raise ValueError("Complete original four-report comparator required")
    return {"version": VERSION, "source": deepcopy(source), "reviewer": deepcopy(reviewer),
        "graph_sha256": digest(graph), "profile_sha256": digest(profile), "prior_sha256": digest(prior),
        "source_occurrences": 166, "complete_original_characters_once": True, "context": context,
        "separator": separator, "rows": rows, "money_cells": len(rows) * 2, "corrections": corrections,
        "arithmetic": arithmetic(rows), "financial_values_validated": False, "independent_financial_acceptance": False,
        "scope": "Complete supplied page60 reading only; risk pages162–163, source authority and incorporation unresolved"}


def explain(review):
    rows = {r["id"]: r for r in review["rows"]}
    selected = ("operating-net", "investing-net", "financing-net", "net-change", "opening-cash", "exchange-effect", "closing-cash", "mandatory-central-bank")
    amounts = {key: {year: deepcopy(rows[key]["cells"][year]["quantity"]) for year in spec.YEARS} for key in selected}
    return {"entity": "Grupo Banco Espírito Santo", "statement": "Consolidated cash-flow statement",
        "periods": ["Six months ended 30 June 2010", "Six months ended 30 June 2009"], "unit": "thousand EUR",
        "amounts": amounts, "cash_rollforward": "Opening cash plus exchange effects plus net cash change equals closing cash; the repeated net-change row is included once.",
        "cash_components": "Mandatory central-bank deposits are a printed negative component in this source's cash-equivalent reconciliation.",
        "notes_qualification": "The following notes form an integral part of these interim consolidated financial statements.",
        "source_corrections": deepcopy(review["corrections"]), "arithmetic": deepcopy(review["arithmetic"]),
        "dash_policy": "Printed dash retained as unknown; no zero imputation", "automatic_ocr_correction": False,
        "audit_opinion_established": False, "legal_dependency_resolution": "UNCHANGED",
        "independent_financial_acceptance": False,
        "limit": "Supplied original-image reading of one page; arithmetic is descriptive, not financial validation or a statement of cash available to noteholders."}


def consume(products, profile, root, *, expected_profile_sha256):
    prior = service.consume(products, root, include_artifacts=True)
    review = evaluate(products["P1"]["payload"]["graph"], prior, profile, root, expected_profile_sha256=expected_profile_sha256)
    return {"answer": prior, "cash_flow_review": review, "cash_flow_explanation": explain(review)}
