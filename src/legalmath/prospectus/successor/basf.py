"""Pinned German Option I construction proposal with complete line accounting."""
import re
from .contracts import digest

KEY = "basf-base-september-2022-exchange"
SHA = "aac3da33755fae327f7542a9be08008d53d1dbcdfa3b01596e48d97debe1cfef"


def construct(graph, admission):
    if admission["sources"][KEY]["sha256"] != SHA:
        raise ValueError("BASF edition mismatch")
    expected = {k: r["sha256"] for k, r in admission["sources"].items()}
    if {d["id"]: d["sha256"] for d in graph["documents"]} != expected:
        raise ValueError("BASF source graph differs from admission")
    lines, accounting = [], []
    for u in graph["units"]:
        if u["document"] != KEY or not 108 <= u["page"] <= 133:
            accounting.append({"unit": u["id"], "role": "OTHER_DOSSIER_SOURCE",
                               "reason": "Outside German Option I; retained in source graph"})
            continue
        box = u["bbox"]
        role = "BODY_CANDIDATE"
        if not box or not u["raw"].strip():
            role = "UNREAD"
        elif box[1] < 60:
            role = "PAGE_HEADER"
        elif box[0] < 155:
            role = "MARGIN_INSTRUCTION"
        accounting.append({"unit": u["id"], "role": role, "bbox": box,
            "reason": "Pinned page geometry; independent reading-order review pending"})
        if role == "BODY_CANDIDATE":
            lines.append(u)
    lines.sort(key=lambda u: (u["page"], round(u["bbox"][1], 1), u["bbox"][0]))
    raw, source_map = "", []
    for line in lines:
        start = len(raw)
        raw += line["raw"] + "\n"
        source_map.append({"start": start, "end": len(raw)-1, "unit": line["id"],
                           "page": line["page"], "bbox": line["bbox"]})
    pairs, stack, unbalanced = [], [], []
    for i, ch in enumerate(raw):
        if ch == "[":
            stack.append(i)
        elif ch == "]":
            if stack:
                start = stack.pop()
                pairs.append((start, i + 1, len(stack)))
            else:
                unbalanced.append(i)
    unbalanced += stack
    decisions = {d["id"]: d for d in admission["decisions"]}
    # Each rule locates a full balanced source branch, not just an anchor quote.
    deletion_rules = [
        ("permanent_global", r"^\[\(3\) Dauerglobal", "permanent"),
        ("holder_put", r"^\[\[?\(\d+\)\]? Vorzeitige Rückzahlung nach Wahl des Gläubigers", "holder_put"),
        ("initial_finance_guarantee", r"^\[\(3\) Garantie und Negativverpflichtung", None),
        ("canada", r"^\[\(5\) Interest Act \(Canada\)", None),
        ("rmb_settlement", r"^\[\(7\) \(a\) Zahlungsverschiebung", None),
        ("finance_successor", r"^\[\(d\) sichergestellt ist, dass sich die Verpflichtungen der Garantin", None),
    ]
    edits, applied = [], []
    for name, pattern, selection in deletion_rules:
        matches = [(a,b,d) for a,b,d in pairs if re.search(pattern, raw[a:b])]
        if selection and selection not in decisions:
            continue
        if selection and decisions[selection]["selected"]:
            continue
        if len(matches) != 1:
            applied.append({"rule": name, "status": "UNRESOLVED", "matches": len(matches)})
            continue
        a,b,_ = matches[0]
        basis = decisions[selection]["source"] if selection else admission["issue_context"][0]["source"]
        edits.append({"start": a, "end": b, "old": raw[a:b], "new": "", "reason": name,
                      "basis": basis, "review": "IMPLEMENTER_PROPOSAL"})
        applied.append({"rule": name, "status": "DELETED", "start": a, "end": b})
    # Only source-supported scalars; unresolved placeholders remain literal.
    substitutions = [
        ("[BASF SE] [BASF Finance Europe N.V.]", "BASF SE", "issuer"),
        ('["BASF"]["BASF Finance"]', '"BASF"', "issuer"),
        ("[festgelegte Währung]", "Euro (EUR)", "currency"),
        ("[festgelegte Stückelung]", "EUR 100.000", "denomination"),
    ]
    context = {c["id"]: c for c in admission["issue_context"]}
    for old, new, key in substitutions:
        for m in re.finditer(re.escape(old), raw):
            if any(e["start"] <= m.start() < e["end"] for e in edits):
                continue
            edits.append({"start": m.start(), "end": m.end(), "old": old, "new": new,
                "reason": "Final terms " + key, "basis": context[key]["source"],
                "review": "IMPLEMENTER_PROPOSAL"})
    edits.sort(key=lambda e:e["start"])
    cursor, parts, output_map = 0, [], []
    for e in edits:
        if e["start"] < cursor or raw[e["start"]:e["end"]] != e["old"]:
            raise ValueError("BASF assembly overlap")
        parts.append(raw[cursor:e["start"]])
        parts.append(e["new"])
        output_map.append({**e, "source_units": [s["unit"] for s in source_map if
            s["start"] < e["end"] and s["end"] > e["start"]]})
        cursor=e["end"]
    parts.append(raw[cursor:])
    candidate="".join(parts)
    remaining=[{"start":a,"end":b,"depth":d,"preview":" ".join(raw[a:min(b,a+200)].split())}
        for a,b,d in sorted(pairs) if not any(e["start"] <= a and b <= e["end"] for e in edits)]
    return {"instrument_id": admission["issue_id"], "source_sha256": SHA,
        "raw_body": raw, "source_map": source_map, "unit_accounting": accounting,
        "candidate_text": candidate, "operations": output_map, "rules": applied,
        "remaining_brackets": remaining, "unbalanced_offsets": unbalanced,
        "conditional_branches": admission["conditional_branches"],
        "annual_range_discrepancy": admission["annual_2022"]["range_discrepancy"],
        "status": "PARTIAL", "full_german_contract_constructed": False,
        "independent_legal_review": False,
        "remaining": ["Resolve every retained bracket and marginal instruction",
                      "Review continuous text and clause renumbering",
                      "Resolve incorporated agreements and conflicting annual ranges"]}

def as_assembly(graph, construction):
    """Apply the constructed spans to every original unit, including deletions."""
    by_unit={s["unit"]:s for s in construction["source_map"]}
    roles={r["unit"]:r["role"] for r in construction["unit_accounting"]}
    units=[]
    for u in graph["units"]:
        mapping=by_unit.get(u["id"])
        text=u["raw"]
        role={"PAGE_HEADER":"HEADER","MARGIN_INSTRUCTION":"INSTRUCTION"}.get(roles[u["id"]],"UNKNOWN")
        if mapping:
            start,end=mapping["start"],mapping["end"]
            cursor=start
            parts=[]
            for edit in construction["operations"]:
                if edit["end"]<=start or edit["start"]>=end:
                    continue
                left,right=max(edit["start"],start),min(edit["end"],end)
                parts.append(construction["raw_body"][cursor:left])
                if start<=edit["start"]<end:
                    parts.append(edit["new"])
                cursor=right
            parts.append(construction["raw_body"][cursor:end])
            text="".join(parts)
            if not text.strip() and u["raw"].strip():
                role="EXCLUDED"
        units.append({"unit":u["id"],"text":text,"role":role,"questions":["Q1","Q2"],
            "context":u["document"]+":german-option-i" if mapping else u["document"]+":"+u["parent"],
            "source":{"document":u["document"],"page":u["page"],"bbox":u["bbox"]},
            "original_sha256":u["text_sha256"],"language":u["language"],
            "reason":"Source-mapped construction proposal; unreviewed text remains unknown"})
    return {"version":"assembled-contract.v1","source_graph_sha256":digest(graph),
        "units":units,"operations":construction["operations"],"status":"PARTIAL",
        "unresolved":[u["unit"] for u in units if u["role"]=="UNKNOWN"],
        "continuous_text":construction["candidate_text"],"independent_legal_review":False}

