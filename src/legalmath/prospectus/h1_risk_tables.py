"""Optional supplied reading of the three original BES H1 risk tables.

The finite reading preserves raw occurrences, reviewed image text, financial
units and descriptive arithmetic separately. It is not an OCR repair model.
"""
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal, localcontext
from pathlib import Path
import re

from . import h1_cash_flow, h1_risk_spec as spec
from .successor.anchors import bind, fields
from .successor.contracts import digest
from .successor.occurrences import anchor

VERSION = "bes-h1-risk-tables-review.v1"
BASIS = "SUPPLIED_ORIGINAL_IMAGE_READING"
PAGE_UNITS = "096bf5b420293d300c186350263edd68ae081c286ad4ee33c7de8fc09509a5e5"
IMAGES = {162: "d123115c44d76d7c36852863269390dd581850164c295b2eb3f925490fecac2c",
          163: "03ad004e8157dff7b038f5175286d0982c7d6b244adcc605040edf56ef2680c1"}


def quantity(literal, unit):
    """Parse supplied literals without guessing digits, units or missing values."""
    if unit in {"thousand EUR", "million EUR"}:
        value = h1_cash_flow.quantity(literal)
        return {"printed": literal, "integer_units": value["integer_thousands"],
                "unit": unit, "status": value["status"]}
    if unit != "percent" or not isinstance(literal, str):
        raise ValueError("Reviewed risk money or percentage unit required")
    if literal == "-":
        return {"printed": literal, "percent_hundredths": None, "unit": unit, "status": "PRINTED_DASH_UNKNOWN"}
    if re.fullmatch(r"(?:0|[1-9][0-9]*)\.[0-9]{2}%", literal) is None:
        raise ValueError("Reviewed two-decimal percentage required")
    value = int(literal[:-1].replace(".", ""))
    if not 0 <= value <= 10000:
        raise ValueError("Printed portfolio percentage outside zero to100")
    return {"printed": literal, "percent_hundredths": value, "unit": unit, "status": "REVIEWED_PRINTED_PERCENTAGE"}


def make_profile(graph, prior, source):
    units = {(u["page"], u["id"].rsplit(":", 1)[1]): u for u in graph["units"]
             if u["document"] == spec.DOCUMENT and u["page"] in IMAGES}
    def original(page, ids):
        return [anchor(units[page, "ocr" + str(i) if type(i) is int else i],
                       0, len(units[page, "ocr" + str(i) if type(i) is int else i]["raw"])) for i in ids]
    def label(page, row):
        return {"source": original(page, row["label"]), "printed": row["printed_label"], "basis": BASIS}
    tables = []
    for table in spec.tables():
        page = table["page"]
        tables.append({k: deepcopy(table[k]) for k in ("id", "page", "kind", "dates", "monetary_unit")})
        tables[-1].update(header={"source": original(page, table["header"]), "columns": deepcopy(table["columns"]), "basis": BASIS},
            groups=[{"id": g["id"], "row_ids": list(g["row_ids"]), "label": label(page, g)} for g in table["groups"]],
            rows=[{"id": r["id"], "role": r["role"], "group": r["group"], "label": label(page, r),
                "cells": {c["id"]: {"source": original(page, ids), "printed": literal, "basis": BASIS}
                    for c, ids, literal in zip(table["columns"], r["cells"], r["printed"])}} for r in table["rows"]])
    return {"version": VERSION, "graph_sha256": digest(graph), "prior_sha256": digest(prior),
        "source": {k: deepcopy(source[k]) for k in ("document", "path", "sha256", "images")},
        "reviewer": {"identity": "Codex complete original pages162–163 image reading 2026-10-16",
            "basis": "AGENT_EXPOSED_DEVELOPMENT_REVIEW", "independent": False},
        "context": {key: original(page, ids) for key, (page, ids) in spec.CONTEXT.items()},
        "tables": tables, "financial_values_validated": False, "selected_reading": None}


def component_sum(values):
    unknown = [key for key, value in values if value is None]
    known = sum(value for _, value in values if value is not None)
    return {"sum": None if unknown else known, "known_component_sum": known, "unknown_components": unknown}


def arithmetic(tables):
    """Describe printed differences without using them to correct the source."""
    sums, groups, ratios, cross_page = [], [], [], []
    for table in tables:
        total, components = table["rows"][-1], table["rows"][:-1]
        for col in table["header"]["columns"]:
            key = "percent_hundredths" if col["unit"] == "percent" else "integer_units"
            values = [(r["id"], r["cells"][col["id"]]["quantity"][key]) for r in components]
            observed = component_sum(values)
            target = total["cells"][col["id"]]["quantity"][key]
            delta = None if target is None or observed["sum"] is None else target - observed["sum"]
            sums.append({"table": table["id"], "column": col["id"], "date": col["date"],
                "unit": "hundredth of a percentage point" if key == "percent_hundredths" else col["unit"],
                "printed_total": target, **observed, "total_minus_components": delta,
                "status": "UNKNOWN_COMPONENT" if delta is None else "EQUAL_PRINTED_VALUES" if delta == 0 else "PRINTED_DIFFERENCE",
                "diagnostic_role": "EXPLANATORY_ONLY"})
    ratings = tables[2]
    for group in ratings["groups"]:
        for col in ratings["header"]["columns"]:
            key = "percent_hundredths" if col["unit"] == "percent" else "integer_units"
            values = [(r["id"], r["cells"][col["id"]]["quantity"][key]) for r in ratings["rows"] if r["id"] in group["row_ids"]]
            groups.append({"group": group["id"], "column": col["id"],
                "unit": "hundredth of a percentage point" if key == "percent_hundredths" else col["unit"],
                **component_sum(values), "printed_group_total": None, "diagnostic_role": "EXPLANATORY_ONLY"})
    for year, sector in zip(("2010", "2009"), tables[:2]):
        total = ratings["rows"][-1]["cells"][year + ":amount"]["quantity"]["integer_units"]
        for row in ratings["rows"]:
            amount = row["cells"][year + ":amount"]["quantity"]["integer_units"]
            pct = row["cells"][year + ":percent"]["quantity"]["percent_hundredths"]
            with localcontext() as ctx:
                ctx.prec = 28
                calculated = None if amount is None or not total else Decimal(amount) * 100 / total
                difference = None if calculated is None or pct is None else Decimal(pct) / 100 - calculated
                ratios.append({"row": row["id"], "group": row["group"], "year": year,
                    "amount": amount, "printed_total_amount": total, "printed_percent_hundredths": pct,
                    "calculated_percentage": None if calculated is None else format(calculated, ".8f"),
                    "printed_minus_calculated_percentage_points": None if difference is None else format(difference, ".8f"),
                    "exact_calculated_percentage_fraction": None if calculated is None else [amount * 100, total],
                    "rounding_cause_established": False, "diagnostic_role": "EXPLANATORY_ONLY"})
        sector_total = sector["rows"][-1]["cells"]["loans-gross"]["quantity"]["integer_units"]
        converted = None if total is None else total * 1000
        cross_page.append({"date": sector["dates"][0], "sector_gross_thousand_eur": sector_total,
            "rating_million_eur": total, "million_to_thousand_factor": 1000, "rating_thousand_eur": converted,
            "sector_minus_rating_thousand_eur": None if sector_total is None or converted is None else sector_total - converted,
            "scope_equivalence_established": False, "rounding_cause_established": False,
            "diagnostic_role": "EXPLANATORY_ONLY"})
    return {"column_sums": sums, "rating_group_sums": groups, "rating_ratios": ratios, "cross_page_totals": cross_page}


def evaluate(graph, prior, profile, root, *, expected_profile_sha256):
    keys = {"version", "graph_sha256", "prior_sha256", "source", "reviewer", "context", "tables",
            "financial_values_validated", "selected_reading"}
    fields(profile, keys, keys)
    if (profile["version"] != VERSION or digest(profile) != expected_profile_sha256
            or profile["graph_sha256"] != digest(graph) or profile["prior_sha256"] != digest(prior)):
        raise ValueError("Pinned risk profile, graph or complete previous consumer changed")
    if profile["financial_values_validated"] is not False or profile["selected_reading"] is not None:
        raise ValueError("Risk reading cannot validate accounts or select legal incorporation")
    reviewer = profile["reviewer"]
    fields(reviewer, {"identity", "basis", "independent"}, {"identity", "basis", "independent"})
    if (not isinstance(reviewer["identity"], str) or not reviewer["identity"].strip()
            or reviewer["basis"] != "AGENT_EXPOSED_DEVELOPMENT_REVIEW" or reviewer["independent"] is not False):
        raise ValueError("Unsupported risk review authority")
    source = profile["source"]
    fields(source, {"document", "path", "sha256", "images"}, {"document", "path", "sha256", "images"})
    if source["document"] != spec.DOCUMENT or source["sha256"] != spec.SOURCE:
        raise ValueError("Original risk PDF required")
    if not isinstance(source["images"], list) or len(source["images"]) != 2:
        raise ValueError("Both reviewed risk images required")
    for im, page in zip(source["images"], (162, 163)):
        fields(im, {"page", "path", "sha256"}, {"page", "path", "sha256"})
        if im["page"] != page or im["sha256"] != IMAGES[page]:
            raise ValueError("Original reviewed risk image changed")
    root = Path(root).resolve()
    for item in [source, *source["images"]]:
        name = item["path"]
        path = (root / name).resolve()
        if Path(name).is_absolute() or not path.is_relative_to(root) or not path.is_file() or digest(path.read_bytes()) != item["sha256"]:
            raise ValueError("Original risk source/image unavailable or changed")
    pages = [u for u in graph["units"] if u["document"] == spec.DOCUMENT and u["page"] in IMAGES]
    if (len(pages) != 933 or digest(pages) != PAGE_UNITS or any(not u["visible"] for u in pages)
            or len({u["id"] for u in graph["units"]}) != len(graph["units"])):
        raise ValueError("Complete original risk occurrences changed")
    units = {(u["page"], u["id"].rsplit(":", 1)[1]): u for u in pages}
    used, corrections = defaultdict(list), []

    def original(anchors, page, ids):
        if not isinstance(anchors, list) or len(anchors) != len(ids):
            raise ValueError("Complete risk source-fragment inventory required")
        result = []
        for a, i in zip(anchors, ids):
            unit = units[page, "ocr" + str(i) if type(i) is int else i]
            start, end = 0, len(unit["raw"])
            if a != anchor(unit, start, end):
                raise ValueError("Exact original risk occurrence/character association required")
            # A unique occurrence was already checked against the complete graph.
            # Bind its unchanged object locally, avoiding933 repeated full scans.
            bound = bind({"units": [unit]}, a)
            bound["original_words"] = deepcopy(unit.get("words", []))
            bound["original_extraction_image_sha256"] = unit.get("image_sha256")
            used[unit["id"]].append((start, end))
            result.append(bound)
        return result

    def reading(cell, page, ids, literal, location):
        fields(cell, {"source", "printed", "basis"}, {"source", "printed", "basis"})
        if cell["printed"] != literal or cell["basis"] != BASIS:
            raise ValueError("Reviewed original-image risk literal or correction basis changed")
        sources = original(cell["source"], page, ids)
        raw = " ".join(a["quote"] for a in sources)
        change = "IMAGE_CONFIRMED" if raw == literal else "SPACING_READING" if "".join(raw.split()) == "".join(literal.split()) else "OCR_CHARACTER_CORRECTION"
        if change == "OCR_CHARACTER_CORRECTION":
            corrections.append({"location": location, "raw_ocr": raw, "printed": literal,
                "source": deepcopy(sources), "basis": BASIS, "image_sha256": IMAGES[page]})
        return {"raw_ocr": raw, "printed": literal, "source": sources, "basis": BASIS,
            "reading_relation": change, "reviewed_image_sha256": IMAGES[page],
            "geometry": "Original whole-occurrence and word boxes; no invented subcell box"}

    fields(profile["context"], spec.CONTEXT, spec.CONTEXT)
    context = {key: original(profile["context"][key], page, ids) for key, (page, ids) in spec.CONTEXT.items()}
    expected_tables = spec.tables()
    if not isinstance(profile["tables"], list) or [t["id"] for t in profile["tables"]] != [t["id"] for t in expected_tables]:
        raise ValueError("Complete ordered risk table inventory required")
    tables = []
    for table, expected in zip(profile["tables"], expected_tables):
        keys = {"id", "page", "kind", "dates", "monetary_unit", "header", "groups", "rows"}
        fields(table, keys, keys)
        if any(table[k] != expected[k] for k in ("page", "kind", "dates", "monetary_unit")):
            raise ValueError("Original risk stock dates and thousand/million units required")
        page, header = table["page"], table["header"]
        fields(header, {"source", "columns", "basis"}, {"source", "columns", "basis"})
        if header["columns"] != expected["columns"] or header["basis"] != BASIS:
            raise ValueError("Reviewed risk columns, asset categories, measures and units required")
        header_result = {"source": original(header["source"], page, expected["header"]),
            "columns": deepcopy(header["columns"]), "basis": BASIS, "reviewed_image_sha256": IMAGES[page],
            "association": "Supplied column semantics linked to the complete original header region; corrupted shared OCR retained once"}
        if not isinstance(table["groups"], list) or [g["id"] for g in table["groups"]] != [g["id"] for g in expected["groups"]]:
            raise ValueError("Complete original rating group inventory required")
        groups = []
        for group, g in zip(table["groups"], expected["groups"]):
            fields(group, {"id", "label", "row_ids"}, {"id", "label", "row_ids"})
            if group["row_ids"] != g["row_ids"]:
                raise ValueError("Original rating model/internal-scale group scope required")
            groups.append({"id": g["id"], "row_ids": list(g["row_ids"]),
                "label": reading(group["label"], page, g["label"], g["printed_label"], table["id"] + "/group/" + g["id"])})
        if not isinstance(table["rows"], list) or [r["id"] for r in table["rows"]] != [r["id"] for r in expected["rows"]]:
            raise ValueError("Complete ordered risk row inventory required")
        rows = []
        for row, r in zip(table["rows"], expected["rows"]):
            fields(row, {"id", "role", "group", "label", "cells"}, {"id", "role", "group", "label", "cells"})
            if row["role"] != r["role"] or row["group"] != r["group"]:
                raise ValueError("Original risk row role and rating group required")
            location = table["id"] + "/" + r["id"]
            label = reading(row["label"], page, r["label"], r["printed_label"], location + "/label")
            columns = [c["id"] for c in expected["columns"]]
            fields(row["cells"], columns, columns)
            cells = {}
            for col, ids, literal in zip(expected["columns"], r["cells"], r["printed"]):
                cells[col["id"]] = {**reading(row["cells"][col["id"]], page, ids, literal, location + "/" + col["id"]),
                    "quantity": quantity(literal, col["unit"]), "column": deepcopy(col)}
            rows.append({"id": r["id"], "role": r["role"], "group": r["group"], "label": label, "cells": cells})
        tables.append({**{k: deepcopy(table[k]) for k in ("id", "page", "kind", "dates", "monetary_unit")},
                       "header": header_result, "groups": groups, "rows": rows})
    if set(used) != {u["id"] for u in pages}:
        raise ValueError("Missing or extra original risk occurrence")
    if any(used[u["id"]] != [(0, len(u["raw"]))] for u in pages):
        raise ValueError("Each original risk character must occur exactly once")
    fields(prior, {"answer", "cash_flow_review", "cash_flow_explanation"}, {"answer", "cash_flow_review", "cash_flow_explanation"})
    answer = prior["answer"]
    original_ids = {"BES-DEP-" + str(n).zfill(2) for n in range(1, 12)} | {"BES-DEP-AGENCY-" + str(n).zfill(2) for n in range(1, 4)}
    deps = [d for d in answer["dependencies"] if d["id"] in original_ids]
    if (answer["may_execute_transaction"] is not False or answer["independent_legal_acceptance"] is not False
            or answer["questions"]["Q3"]["status"] != "PARTIAL" or len(deps) != 14
            or {d["id"] for d in deps} != original_ids or any(d["status"] != "UNRESOLVED" for d in deps)
            or prior["cash_flow_review"]["source_occurrences"] != 166
            or prior["cash_flow_review"]["financial_values_validated"] is not False):
        raise ValueError("Complete unresolved prior answer and supplied cash-flow reading required")
    return {"version": VERSION, "source": deepcopy(source), "reviewer": deepcopy(reviewer),
        "graph_sha256": digest(graph), "prior_sha256": digest(prior), "profile_sha256": digest(profile),
        "source_occurrences": 933, "complete_original_characters_once": True,
        "numeric_cells": 720, "money_cells": 640, "percentage_cells": 80, "context": context,
        "tables": tables, "corrections": corrections, "arithmetic": arithmetic(tables),
        "financial_values_validated": False, "independent_financial_acceptance": False,
        "scope": "Complete supplied image reading of pages162–163; source authenticity, incorporation and independent review unresolved"}


def explain(review):
    tables = [{"id": t["id"], "page": t["page"], "dates": t["dates"], "monetary_unit": t["monetary_unit"],
        "columns": deepcopy(t["header"]["columns"]),
        "groups": [{"id": g["id"], "name": g["label"]["printed"], "row_ids": g["row_ids"]} for g in t["groups"]],
        "rows": [{"id": r["id"], "group": r["group"], "role": r["role"], "label": r["label"]["printed"],
            "cells": {key: deepcopy(cell["quantity"]) for key, cell in r["cells"].items()},
            "source_location": t["id"] + "/" + r["id"]} for r in t["rows"]]} for t in review["tables"]]
    return {"entity": "Banco Espírito Santo", "status": "COMPLETE_SUPPLIED_RISK_TABLE_READING",
        "tables": tables, "arithmetic": deepcopy(review["arithmetic"]), "source_corrections": deepcopy(review["corrections"]),
        "dates": "Stocks at30 June2010 and31 December2009; these are not the cash-flow comparison periods.",
        "amounts": "Sector values are thousands of euro; rating credit amounts are millions of euro. Percentages remain separate.",
        "aggregation": "Gross amounts, impairments, asset categories and guarantees remain separate columns. No combined exposure is inferred.",
        "rating_scope": "An internal scale identifies a row only together with its rating/scoring model; unrated loans are a separate category.",
        "header_reading": "Complete original header occurrences are retained once, with supplied image-backed column associations.",
        "dash_policy": "Printed dashes remain unknown; component sums with a dash are unknown.",
        "arithmetic_interpretation": "Differences between printed totals, component sums and amount-based percentages are descriptive. No residual establishes a rounding cause or changes a printed value.",
        "historical_answer": "The preserved answer and cash-flow explanation describe their original scope. This supplement supplies the risk tables without changing those historical results.",
        "automatic_ocr_correction": False, "audit_opinion_established": False,
        "legal_dependency_resolution": "UNCHANGED", "independent_financial_acceptance": False}


def consume(products, cash_flow_profile, profile, root, *, expected_cash_flow_profile_sha256, expected_profile_sha256):
    prior = h1_cash_flow.consume(products, cash_flow_profile, root, expected_profile_sha256=expected_cash_flow_profile_sha256)
    review = evaluate(products["P1"]["payload"]["graph"], prior, profile, root, expected_profile_sha256=expected_profile_sha256)
    return {**prior, "risk_table_review": review, "risk_table_explanation": explain(review)}
