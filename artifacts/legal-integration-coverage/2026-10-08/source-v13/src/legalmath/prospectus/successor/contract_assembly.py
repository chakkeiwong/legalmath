"""Traceable text transformations; unresolved units cannot certify completeness."""
from .contracts import digest

ROLES = {"OPERATIVE", "EXCLUDED", "EXAMPLE", "HEADER", "INSTRUCTION", "UNKNOWN"}


def anchor(graph, item):
    units = {u["id"]: u for u in graph["units"]}
    u = units[item["unit"]]
    start, end = item.get("start", 0), item.get("end", len(u["raw"]))
    if not 0 <= start <= end <= len(u["raw"]) or u["raw"][start:end] != item["quote"]:
        raise ValueError("Source anchor changed or invalid")
    if not u["visible"]:
        raise ValueError("Anchor uses an unavailable source version")
    return {**item, "source_sha256": u["source_sha256"], "page": u["page"], "bbox": u["bbox"]}


def assemble(graph, specification=None):
    specification = specification or {}
    operations = specification.get("operations", [])
    units = {u["id"]: u for u in graph["units"]}
    by_unit = {}
    for op in operations:
        if op["unit"] not in units or op["unit"] in by_unit:
            raise ValueError("Unknown or duplicate unit disposition")
        if op["role"] not in ROLES or not op.get("reason"):
            raise ValueError("Every unit role needs a reason")
        if op["source_text_sha256"] != units[op["unit"]]["text_sha256"]:
            raise ValueError("Assembly disposition is stale")
        by_unit[op["unit"]] = op
    assembled, trace, unresolved = [], [], []
    for unit in graph["units"]:
        op = by_unit.get(unit["id"], {"role": "UNKNOWN", "reason": "No disposition supplied"})
        role = op["role"] if unit["visible"] else "EXCLUDED"
        text = unit["raw"]
        edits = sorted(op.get("edits", []), key=lambda e: e["start"])
        cursor = 0
        fragments, character_map, output_offset = [], [], 0
        for edit in edits:
            start, end = edit["start"], edit["end"]
            if not cursor <= start <= end <= len(text) or text[start:end] != edit["old"]:
                raise ValueError("Overlapping or stale substitution")
            if not edit.get("reason") or not edit.get("basis"):
                raise ValueError("Deletion/substitution requires source basis")
            evidence = [anchor(graph, a) for a in edit["basis"]]
            if start > cursor:
                character_map.append({"start":output_offset,"end":output_offset+start-cursor,
                                      "unit":unit["id"],"source_start":cursor,"source_end":start,"operation":"Text"})
                output_offset += start-cursor
            character_map.append({"start":output_offset,"end":output_offset+len(edit["new"]),
                                  "unit":unit["id"],"source_start":start,"source_end":end,
                                  "operation":"Substitution","basis":evidence,"reason":edit["reason"]})
            output_offset += len(edit["new"])
            fragments.extend([text[cursor:start], edit["new"]])
            trace.append({**edit, "unit": unit["id"], "basis": evidence})
            cursor = end
        fragments.append(text[cursor:])
        character_map.append({"start":output_offset,"end":output_offset+len(text)-cursor,
                              "unit":unit["id"],"source_start":cursor,"source_end":len(text),"operation":"Text"})
        transformed = "".join(fragments)
        if not text.strip() and role == "OPERATIVE":
            role = "UNKNOWN"
        if role == "UNKNOWN":
            unresolved.append(unit["id"])
        assembled.append({"unit": unit["id"], "role": role, "reason": op["reason"],
            "text": transformed, "original_sha256": unit["text_sha256"],
            "character_map": character_map,
            "questions": op.get("questions", ["Q1", "Q2"]), "order": op.get("order", len(assembled)),
            "context": op.get("context", unit["parent"]), "language": unit["language"],
            "source": {"document": unit["document"], "page": unit["page"], "bbox": unit["bbox"]}})
    assembled.sort(key=lambda r: r["order"])
    result = {"version": "assembled-contract.v2", "source_graph_sha256": digest(graph),
        "units": assembled, "operations": trace, "unresolved": unresolved,
        "status": "PARTIAL" if unresolved else "COMPLETE_UNDER_SUPPLIED_DISPOSITIONS",
        "independent_legal_review": False,
        "continuous_text": "\n".join(r["text"] for r in assembled if r["role"] in {"OPERATIVE", "UNKNOWN"})}
    if specification.get("ast"):
        from .construction_ast import assemble as construct_ast
        return construct_ast(graph, specification["ast"], result)
    return result
