"""Exact raw-to-selected occurrence uses; quotation alone is not applicability."""
from .anchors import bind, fields
from .contracts import digest


def anchor(unit, start=0, end=None):
    end = len(unit["raw"]) if end is None else end
    return {"unit": unit["id"], "document": unit["document"],
            "source_sha256": unit["source_sha256"], "start": start, "end": end,
            "quote": unit["raw"][start:end]}


def _raw_index(graph):
    raw = {row['id']:row for row in graph['units']}
    if len(raw) != len(graph['units']):
        raise ValueError('Duplicate source occurrence identity')
    return raw


def segments(graph, unit, *, _raw=None):
    """Return only character-for-character copies, never inferred replacements."""
    raw = _raw_index(graph) if _raw is None else _raw
    maps = unit.get("character_map")
    if maps is None:
        original = raw.get(unit["unit"])
        if original and original["raw"] == unit["text"] and original.get("visible"):
            return [{"source": anchor(original), "start": 0, "end": len(unit["text"])}]
        return []
    result = []
    for piece in maps:
        if piece.get("operation") not in {"Text", "Field"}:
            continue
        source = piece.get("source")
        if source is not None:
            source = {k: source[k] for k in ("unit", "document", "source_sha256", "start", "end", "quote")}
        elif piece.get("unit") in raw:
            source = anchor(raw[piece["unit"]], piece["source_start"], piece["source_end"])
        else:
            continue
        if source["start"] == source["end"]:
            continue
        # The per-invocation index has checked uniqueness. Validate against the
        # same raw occurrence without rescanning every PDF line for each piece.
        bind({'units':[raw[source['unit']]] if source['unit'] in raw else []}, source)
        start, end = piece["start"], piece["end"]
        # Historical AST pieces used global rendered offsets. Each AST unit
        # represents precisely one piece; normalize that old representation.
        if unit["unit"].startswith("ast:") and len(maps) == 1:
            start, end = 0, end - start
        if (type(start) is not int or type(end) is not int or
                not 0 <= start < end <= len(unit["text"]) or
                unit["text"][start:end] != source["quote"]):
            raise ValueError("Selected occurrence map differs from source text")
        result.append({"source": source, "start": start, "end": end})
    return result


def uses(graph, assembly, source, *, roles=("OPERATIVE",), question=None):
    """Locate complete unchanged copies. Ambiguity is returned, never guessed."""
    bind(graph, source)
    raw_index = _raw_index(graph)
    result = []
    for unit in assembly["units"]:
        if unit["role"] not in roles or question and question not in unit["questions"]:
            continue
        pieces = []
        for piece in segments(graph, unit, _raw=raw_index):
            raw = piece["source"]
            if (raw["unit"], raw["document"], raw["source_sha256"]) != (
                    source["unit"], source["document"], source["source_sha256"]):
                continue
            left, right = max(raw["start"], source["start"]), min(raw["end"], source["end"])
            if left < right:
                pieces.append((left, right, piece["start"] + left - raw["start"]))
        pieces.sort()
        cursor, selected = source["start"], []
        for left, right, output in pieces:
            if left != cursor or selected and output != selected[-1][1]:
                break
            selected.append((output, output + right - left))
            cursor = right
        else:
            if cursor == source["end"] and selected:
                result.append({"unit": unit["unit"], "start": selected[0][0],
                               "end": selected[-1][1], "source": source})
    return result


def target(graph, assembly, value):
    raw = {u["id"]: u for u in graph["units"]}
    selected = {u["unit"]: u for u in assembly["units"]}
    explicit = None
    if isinstance(value, dict):
        fields(value, {"source", "use"}, {"source", "use"})
        source, explicit = value["source"], value["use"]
    elif isinstance(value, str) and value in raw:
        source = anchor(raw[value])
    elif isinstance(value, str) and value in selected:
        unit = selected[value]
        parts = segments(graph, unit)
        if len(parts) != 1 or parts[0]["start"] != 0 or parts[0]["end"] != len(unit["text"]):
            raise ValueError("Reference target requires explicit source intervals and use")
        source, explicit = parts[0]["source"], value
    else:
        raise ValueError("Reference targets must be available operative source units")
    matches = uses(graph, assembly, source, roles=("OPERATIVE", "UNKNOWN"))
    if explicit is not None:
        matches = [m for m in matches if m["unit"] == explicit]
    if len(matches) != 1:
        raise ValueError("Reference target unavailable or ambiguous; exact selected occurrence required")
    return matches[0]


def constraints(graph, assembly, rows, question):
    """Admit service premises; direct solver semantics remain independent."""
    result, admissions = [], []
    allowed = {"id", "expression", "source", "reason", "applicability"}
    for row in rows:
        fields(row, allowed, allowed - {"applicability"})
        bind(graph, row["source"])
        decision = row.get("applicability")
        if decision is not None:
            fields(decision, {"role", "assembly_sha256", "context", "questions", "use"},
                   {"role", "assembly_sha256", "context", "questions"})
            if (decision["assembly_sha256"] != digest(assembly) or
                    decision["context"] != graph["context"] or
                    not isinstance(decision["questions"], list) or not decision["questions"] or
                    set(decision["questions"]) - {"Q1", "Q2"}):
                raise ValueError("Predicate applicability is stale or has invalid question scope")
            if question not in decision["questions"]:
                continue
        role = decision["role"] if decision else "OPERATIVE"
        if role == "OPERATIVE":
            matches = uses(graph, assembly, row["source"], question=question)
            if decision and "use" in decision:
                matches = [m for m in matches if m["unit"] == decision["use"]]
            if len(matches) != 1:
                raise ValueError("Predicate source is not an unambiguous operative occurrence for " + question)
            admission = {"role": role, "use": matches[0]}
        elif role == "CONSTRUCTION_AUTHORITY":
            premises = assembly.get("rendered_ast", {}).get("dispositions", [])
            matched = [p for p in premises if p["disposition"] == "PREMISE" and
                       p["source"] == row["source"] and p.get("use", [])[-1:] in (["selection"], ["authority"])]
            if not matched:
                raise ValueError("External premise lacks consumed construction authority")
            admission = {"role": role, "construction_premises": matched}
        else:
            raise ValueError("Unsupported predicate applicability role")
        admissions.append({"id": row["id"], "question": question,
                           "assembly_sha256": digest(assembly), **admission})
        result.append({k: v for k, v in row.items() if k != "applicability"})
    return result, admissions
