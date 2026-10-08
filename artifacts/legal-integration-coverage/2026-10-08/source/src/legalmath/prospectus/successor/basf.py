"""Pinned German Option I construction proposal with complete line accounting."""
import re
from .contracts import digest
from .basf_order import reviewed_order
from .basf_scope import reviewed_edits

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
    lines, reading_order = reviewed_order(lines)
    raw, source_map = "", []
    for line in lines:
        start = len(raw)
        raw += line["raw"] + "\n"
        source_map.append({"start": start, "end": len(raw)-1, "unit": line["id"],
                           "page": line["page"], "bbox": line["bbox"]})
    decisions = {d["id"]: d for d in admission["decisions"]}
    # Printed p112 has no closing bracket for the long-coupon alternative.
    # Its margin rule and the next definition delimit this explicitly unselected
    # branch. Never insert punctuation or let its stack swallow the whole contract.
    malformed = []
    if decisions["long_stub"]["selected"] is False:
        starts = [m.start() for m in re.finditer(re.escape("[die Summe aus:"), raw)]
        if len(starts) == 1:
            a = starts[0]
            b = raw.find('["Bezugsperiode" bezeichnet', a)
            if b < 0 or not any(s["start"] <= a <= s["end"] and s["page"] == 112 for s in source_map):
                raise ValueError("Reviewed malformed-branch geometry changed")
            malformed.append((a,b))
    pairs, stack, unbalanced = [], [], []
    for i, ch in enumerate(raw):
        if any(a <= i < b for a,b in malformed):
            continue
        if ch == "[":
            stack.append(i)
        elif ch == "]":
            if stack:
                start = stack.pop()
                pairs.append((start, i + 1, len(stack)))
            else:
                unbalanced.append(i)
    unbalanced += stack
    # Each rule locates a full balanced source branch, not just an anchor quote.
    deletion_rules = [
        ("permanent_global", r"^\[\(3\) Dauerglobal", "permanent"),
        ("holder_put", r"^\[\[?\(\d+\)\]? Vorzeitige Rückzahlung nach Wahl des Gläubigers", "holder_put"),
        ("initial_finance_guarantee", r"^\[\(3\) Garantie und Negativverpflichtung", None),
        ("canada", r"^\[\(5\) Interest Act \(Canada\)", None),
        ("rmb_settlement", r"^\[\(7\) \(a\) Zahlungsverschiebung", None),
        ("finance_successor", r"^\[\(d\) sichergestellt ist, dass sich die Verpflichtungen der Garantin", None),
        ("cbf", r"^\[Clearstream Banking AG,", "cbf"),
        ("cds", r"^\[CDS & Co\.", "cds"),
        ("classical_global", r"^\[Die Schuldverschreibungen werden in Form einer Classical", "classical_global"),
        ("cds_ownership", r"^\[Das wirtschaftliche Eigentum an der Dauerglobalurkunde", "cds"),
        ("cds_holder", r"^\[Im Fall von Schuldverschreibungen, die durch eine Dauerglobalurkunde", "cds"),
        ("different_rates", r"^\[Die Schuldverschreibungen werden bezogen auf ihren Gesamtnennbetrag wie folgt", "different_rates"),
        ("initial_broken", r"^\[Sofern der erste Zinszahlungstag nicht der erste Jahrestag", "initial_broken"),
        ("final_broken", r"^\[Sofern der Fälligkeitstag kein Festzinstermin", "final_broken"),
        ("actual_365", r"^\[die tatsächliche Anzahl von Tagen im Zinsberechnungszeitraum, dividiert durch 365", "actual_365"),
        ("bond_basis", r"^\[die Anzahl von Tagen im Zinsberechnungszeitraum, dividiert durch 360", "bond_basis"),
        ("eurobond_basis", r"^\[die Anzahl der Tage im Zinsberechnungszeitraum, dividiert durch 360", "eurobond_basis"),
        ("cds_payment", r"^\[Zahlung von Kapital und Zinsen, Erfüllung", "cds"),
        ("payment_centres", r"^\[ein Tag.*?Geschäftsbanken", "payment_centres"),
        ("transaction_call_reference", r"^\[Falls die Emittentin das Wahlrecht hat, die Schuldverschreibungen vorzeitig nach Veröffentlichung", "transaction_call"),
        ("rmb_call", r"^\[\[\(7\)\] Vorzeitige Rückzahlung", "rmb_call"),
        ("transaction_call", r"^\[\[\(9\)\] Vorzeitige Rückzahlung", "transaction_call"),
        ("canadian_agent", r"^\[Fiscal Agent und Zahlstelle: \[Name und bezeichnete Geschäftsstelle des/der Kanadischen", "cds"),
        ("representative_terms", r"^\[Gemeinsamer Vertreter ist", "representative_terms"),
        ("english_controls", r"^\[Diese Anleihebedingungen sind in englischer Sprache", "english_controls"),
        ("annual_short", r"^\[die Anzahl von Tagen.*?geteilt durch die Anzahl der Tage", "annual_short"),
        ("multiple_periods", r"^\[die Anzahl von Tagen.*?geteilt durch das Produkt", "multiple_periods"),
        ("short_reference_adjustment", r"^\[Im Fall eines ersten oder letzten kurzen Zinsberechnungszeitraumes", "annual_short"),
        ("long_reference_adjustment", r"^\[Im Fall eines ersten oder letzten langen Zinsberechnungszeitraumes", "long_stub"),
        ("uk_benchmark", r"^\[durch HM Treasury", "uk_benchmark"),
        ("swiss_benchmark", r"^\[Schweizer Franken-Referenz", "swiss_benchmark"),
        ("us_benchmark", r"^\[Referenz-U.S.", "us_benchmark"),
    ]
    edits = [{"start":a,"end":b,"old":raw[a:b],"new":"","reason":"Unselected long-coupon alternative; printed p112 margin boundary",
              "basis":decisions["long_stub"]["source"],"review":"IMPLEMENTER_SOURCE_IMAGE_REVIEW"} for a,b in malformed]
    applied = [{"rule":"long_stub_malformed","status":"DELETED","start":a,"end":b,
                "source_defect":"Missing closing bracket in printed source, not repaired by insertion"} for a,b in malformed]
    for name, pattern, selection in deletion_rules:
        matches = [(a,b,d) for a,b,d in pairs if re.search(pattern, " ".join(raw[a:b].split()))]
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
    # Selected brackets are syntax around a branch, not contractual characters.
    # Remove only their own delimiters; nested unresolved fields stay explicit.
    resolved_pairs = set()
    selected_rules = [
        ("temporary_global", r"^\[\(3\) Vorläufige Globalurkunde", False),
        ("new_global", r"^\[Die Schuldverschreibungen werden in Form einer New Global", False),
        ("single_rate", r"^\[Die Schuldverschreibungen werden bezogen auf ihren Gesamtnennbetrag verzinst", False),
        ("annual_no_stub", r"^\[die tatsächliche Anzahl von Tagen.*?jeweiligen Zinsperiode", False),
        # Printed p112 says this definition applies to ALL Actual/Actual options.
        # The unchecked final-terms reference-period item does not delete it.
        ("icma", r'^\["Bezugsperiode" bezeichnet', False),
        ("payment_target", r"^\[ein Tag.*?Trans-European", False),
        ("change_of_control", r"^\[\(3\) Kontrollwechsel", False),
        ("dated_call", r"^\[\[\(4\)\] Vorzeitige Rückzahlung", False),
        ("make_whole_call", r"^\[\[\(5\)\] Vorzeitige Rückzahlung", False),
        ("cleanup_call", r"^\[\[\(8\)\] Rückkauf", False),
        ("higher_pv", r"^\[\(b\) Für die Zwecke", False),
        ("euro_benchmark", r"^\[Euro-Referenz-Anleihe", False),
        ("representative_vote", r"^\[Die Gläubiger können durch Mehrheitsbeschluß", False),
        ("notice_web", r"^\[\(1\) Bekanntmachung", False),
        ("german_controls", r"^\[Diese Anleihebedingungen sind in deutscher Sprache abgefasst. Eine Übersetzung", False),
        ("new_global", r"^\[Falls die Globalurkunde eine NGN ist", True),
        ("temporary_global", r"^\[Falls die vorläufige Globalurkunde eine NGN ist", True),
        ("temporary_global", r"^\[Die Zahlung von Zinsen auf Schuldverschreibungen, die durch die vorläufige", False),
    ]
    for selection, pattern, instruction in selected_rules:
        if not decisions[selection]["selected"]:
            continue
        matches = [(a,b) for a,b,_ in pairs if re.search(pattern," ".join(raw[a:b].split()))]
        if len(matches) != 1:
            applied.append({"rule":selection+":selected", "status":"UNRESOLVED", "matches":len(matches)})
            continue
        a,b = matches[0]
        opening_end = raw.index(":",a,b)+1 if instruction else a+1
        for left,right in ((a,opening_end),(b-1,b)):
            edits.append({"start":left,"end":right,"old":raw[left:right],"new":"",
                          "reason":"Selected branch "+selection,"basis":decisions[selection]["source"],
                          "review":"IMPLEMENTER_SOURCE_READING"})
        resolved_pairs.add((a,b))
        applied.append({"rule":selection+":selected","status":"SELECTED","start":a,"end":b})
    # Only source-supported scalars; unresolved placeholders remain literal.
    substitutions = [
        ("[BASF SE] [BASF Finance Europe N.V.]", "BASF SE", "issuer"),
        ('["BASF"]["BASF Finance"]', '"BASF"', "issuer"),
        ("[festgelegte Währung]", "Euro (EUR)", "currency"),
        ("[festgelegte Stückelung]", "EUR 100.000", "denomination"),
        ("[Zinssatz]", "4,250", "rate"),
        ("[erster Zinszahlungstag]", "8. März 2024", "first_interest"),
    ]
    context = {c["id"]: c for c in admission["issue_context"]}
    for old, new, key in substitutions:
        for m in re.finditer(re.escape(old), raw):
            if any(e["start"] <= m.start() < e["end"] for e in edits):
                continue
            edits.append({"start": m.start(), "end": m.end(), "old": old, "new": new,
                "reason": "Final terms " + key, "basis": context[key]["source"],
                "review": "IMPLEMENTER_PROPOSAL"})
    scope_edits, scope_pairs, scope_rules, scope_review = reviewed_edits(
        graph, admission, raw, source_map, pairs)
    edits.extend(scope_edits)
    resolved_pairs.update(scope_pairs)
    applied.extend(scope_rules)
    edits.sort(key=lambda e:e["start"])
    cursor, parts, output_map, character_map = 0, [], [], []
    output_offset = 0
    def append_part(left, right, text, operation, basis=None):
        nonlocal output_offset
        parts.append(text)
        if text:
            character_map.append({"start":output_offset,"end":output_offset+len(text),
                                  "raw_start":left,"raw_end":right,"operation":operation,"basis":basis})
            output_offset += len(text)
    for e in edits:
        if e["start"] < cursor or raw[e["start"]:e["end"]] != e["old"]:
            raise ValueError("BASF assembly overlap")
        append_part(cursor,e["start"],raw[cursor:e["start"]],"COPY")
        append_part(e["start"],e["end"],e["new"],"SUBSTITUTE",e["basis"])
        output_map.append({**e, "source_units": [s["unit"] for s in source_map if
            s["start"] < e["end"] and s["end"] > e["start"]]})
        cursor=e["end"]
    append_part(cursor,len(raw),raw[cursor:],"COPY")
    candidate="".join(parts)
    remaining=[{"start":a,"end":b,"depth":d,"preview":" ".join(raw[a:min(b,a+200)].split())}
        for a,b,d in sorted(pairs) if (a,b) not in resolved_pairs and not any(e["start"] <= a and b <= e["end"] for e in edits)]
    # Project raw-body operations onto exact line occurrences independently of
    # the output map. Margins remain visible obligations, including shared scope.
    dispositions = []
    by_id = {u["id"]: u for u in graph["units"]}
    def record(unit, a, b, kind, reason, binding=None, use="body"):
        if a == b:
            return
        dispositions.append({"source": {"unit": unit["id"], "document": unit["document"],
            "source_sha256": unit["source_sha256"], "start": a, "end": b, "quote": unit["raw"][a:b]},
            "disposition": kind, "use": ["basf-option-i", unit["id"], use], "reason": reason, "binding": binding})
    for span in source_map:
        unit = by_id[span["unit"]]
        relevant_edits = [e for e in edits if e["start"] < span["end"] and e["end"] > span["start"]]
        boundaries = sorted({span["start"], span["end"]} | {
            max(span["start"], min(span["end"], e[k])) for e in relevant_edits for k in ("start", "end")})
        for a, b in zip(boundaries, boundaries[1:]):
            edit = next((e for e in relevant_edits if e["start"] <= a and b <= e["end"]), None)
            kind = "COPIED" if edit is None else "REPLACED_TEMPLATE" if edit["new"] else "EXCLUDED_BY_CHOICE"
            record(unit, a-span["start"], b-span["start"], kind,
                   edit["reason"] if edit else "Unchanged proposal text; legal disposition pending",
                   {"basis": edit["basis"], "reason": edit["reason"]} if edit else None)
        for i, branch in enumerate(remaining):
            a, b = max(branch["start"], span["start"]), min(branch["end"], span["end"])
            if a < b:
                record(unit, a-span["start"], b-span["start"], "UNRESOLVED", "Retained construction branch", use="branch:"+str(i))
    for row in accounting:
        if row["role"] in {"MARGIN_INSTRUCTION", "PAGE_HEADER", "UNREAD"}:
            unit = by_id[row["unit"]]
            record(unit, 0, len(unit["raw"]), "UNRESOLVED", "Margin/header requires source-bound scope disposition", use=row["role"])
    from .intervals import check
    interval_check = check(graph, dispositions, [r["unit"] for r in accounting if r["role"] != "OTHER_DOSSIER_SOURCE"])
    return {"instrument_id": admission["issue_id"], "source_sha256": SHA,
        "disposition_version": "basf-occurrences.v1", "dispositions": dispositions, "interval_accounting": interval_check,
        "source_defects": [{"start":a,"end":b,"kind":"missing bracket in unselected long-coupon alternative",
                            "source_page":112,"decision":"excluded by final terms long_stub=false"} for a,b in malformed],
        "raw_body": raw, "source_map": source_map, "unit_accounting": accounting,
        "reading_order": {"version": "basf-reviewed-order.v1", "decisions": reading_order,
                          "other_rows": "Legacy geometry order; full source review pending"},
        "scope_review": scope_review,
        "candidate_text": candidate, "character_map":character_map, "operations": output_map, "rules": applied,
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
        if not u["visible"]:
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
