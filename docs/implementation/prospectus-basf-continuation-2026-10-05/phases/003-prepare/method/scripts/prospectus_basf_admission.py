"""Scoped BASF development admission; no complete contract or legal conclusion."""
import copy
import hashlib
import re
from collections import Counter
from pathlib import Path
from scripts import prospectus_refresh as old
from scripts.prospectus_refresh_work import sources, BASF, SUPPLEMENT, ANNUAL
from scripts.prospectus_refresh_admission import source_document
from scripts.prospectus_refresh_sources import anchor, norm, require, replay

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "scripts/prospectus_basf_spec.json"
OLD_PACKET = ROOT / "docs/implementation/prospectus-closure-refresh-2026-10-05/phases/013-admit/basf-admission.json"
OLD_PACKET_SHA = "d42092e16b72842b744e9b879dfe6a421cb3ee8bd5a6f565fd864df3d4bee87b"
GLYPHS = r"[\uf078\uf06f☒☐]"

def selectors(document, spec):
    """Account for every checkbox and bilingual decision in this exact Part I."""
    texts = {p: norm(document["pages"][p-1]["text"]) for p in range(3, 8)}
    require([p["page"] for p in document["pages"]] == list(range(1, len(document["pages"])+1)),
            "Invalid final-term page mapping")
    ids = [v["id"] for v in spec["checkboxes"] + spec["yesno"]]
    require(len(ids) == len(set(ids)), "Duplicate selection id")
    declared = Counter((b["page"], b["label"]) for b in spec["checkboxes"])
    covered = []
    result = []
    for row in spec["checkboxes"]:
        text = texts[row["page"]]
        matches = list(re.finditer(GLYPHS + r"\s*" + re.escape(row["label"]) + r"(?=\s|$)", text))
        require(len(matches) == declared[(row["page"], row["label"])], "Ambiguous/missing checkbox: " + row["id"])
        require(type(row["occurrence"]) is int and 0 <= row["occurrence"] < len(matches), "Invalid occurrence")
        match = matches[row["occurrence"]]
        selected = match.group()[0] in ("\uf078", "☒")
        require(selected is row["selected"], "Reviewed selection changed: " + row["id"])
        require(not row.get("excluded_parent") or not selected, "Selected excluded branch")
        covered.append((row["page"], match.start()))
        result.append({**row, "kind": "checkbox", "start": match.start(), "end": match.end(),
                       "quote": match.group(), "disposition": "SELECTED" if selected else "DELETED"})
    expected = [(p, m.start()) for p, text in texts.items() for m in re.finditer(GLYPHS, text)]
    require(Counter(covered) == Counter(expected), "Unaccounted or multiply-accounted checkbox")
    answers = []
    for row in spec["yesno"]:
        text = texts[row["page"]]
        pattern = re.escape(row["en"]) + r"\s+(Yes|No)\s+" + re.escape(row["de"]) + r"\s+(Ja|Nein)(?=\s|$)"
        if row["de_tail"]:
            pattern += r"\s+" + re.escape(row["de_tail"])
        matches = list(re.finditer(pattern, text))
        require(len(matches) == 1, "Ambiguous/missing bilingual response: " + row["id"])
        match = matches[0]
        require((match.group(1) == "Yes") == (match.group(2) == "Ja"), "Bilingual conflict")
        selected = match.group(1) == "Yes"
        require(selected is row["selected"], "Reviewed bilingual response changed: " + row["id"])
        answers.extend([match.start(1), match.start(2)])
        result.append({**row, "kind": "yes_no", "start": match.start(), "end": match.end(),
                       "quote": match.group(), "disposition": "SELECTED" if selected else "DELETED"})
    expected_answers = [m.start() for m in re.finditer(r"\b(?:Yes|No|Ja|Nein)\b", texts[6])]
    require(Counter(answers) == Counter(expected_answers), "Unaccounted bilingual response")
    require(len(spec["yesno"]) == 8, "Expected eight source response pairs")
    return result

def annual_scope(doc, row, supplement, sup_row):
    """Admit explicit detailed ranges only; preserve contradictory broad heading."""
    ranges = [
        ("Auditors' report", 197, 202, "Auditors' report (p. 197 – p. 202)"),
        ("Income", 203, 203, "Consolidated statement of income (p. 203)"),
        ("Balance sheet", 205, 206, "Consolidated balance sheet (p. 205 – p. 206)"),
        ("Cash flows", 207, 207, "Consolidated statement of cash flows (p. 207)"),
        ("Notes", 209, 290, "Notes (p. 209 – p. 290)"),
    ]
    require(doc["source_sha256"] == row["sha256"], "Report/source mismatch")
    require([p["page"] for p in doc["pages"]] == list(range(1, len(doc["pages"])+1)), "Report pages reordered")
    admitted = sorted({p for _, start, stop, _ in ranges for p in range(start, stop+1)})
    page_records = []
    for p in admitted:
        text = doc["pages"][p-1]["text"]
        header = next(line for line in text.splitlines() if line.strip())
        require("BASF Report 2022" in header and re.search(r"\b" + str(p) + r"\s*$", header),
                "Printed/physical annual page mismatch: " + str(p))
        page_records.append({"physical_page": p, "printed_page": p, "text_sha256": hashlib.sha256(text.encode()).hexdigest()})
    return {
        "status": "EXPLICIT_DETAILED_RANGES_ADMITTED_FOR_SOURCE_IDENTITY",
        "source": row,
        "incorporation": anchor(sup_row, supplement, 12, "the published audited consolidated annual financial statements of BASF Group (English language version) dated December 31, 2022, including the auditors' report thereon."),
        "ranges": [{"name": name, "printed": [start, stop], "physical": [start, stop],
                    "basis": anchor(sup_row, supplement, 12, quote)} for name, start, stop, quote in ranges],
        "pages": page_records,
        "broad_heading": anchor(sup_row, supplement, 12, "(p. 195 – p. 209 )"),
        "range_discrepancy": "Overall heading ends at 209; explicit Notes range ends at 290. Both preserved. Only enumerated detailed ranges admitted; full incorporation interpretation remains unresolved.",
        "auditor_language": anchor(row, doc, 197, "This is a translation of the German original. Solely the original text in German language is authoritative."),
        "financial_values_validated": False,
        "column_extraction_qualified": False,
        "complete_incorporation_scope": False,
    }

def build_packet():
    require(old.sha(OLD_PACKET) == OLD_PACKET_SHA, "Predecessor packet changed")
    spec = old.read(SPEC)
    require(spec["schema"] == "basf-selection-spec.v1" and spec["independent_adjudication"] is False,
            "Specification scope changed")
    rows = {k:v for k,v in sources().items() if k != "deutsche-at1-2025"}
    docs = {k: source_document(v) for k,v in rows.items()}
    def a(k, page, quote):
        return anchor(rows[k], docs[k], page, quote)
    decisions = selectors(docs["basf-2032-final"], spec)
    for decision in decisions:
        decision["source"] = a("basf-2032-final", decision["page"], decision["quote"])
        target = spec["targets"][decision["target"]]
        decision["german_clause_locator"] = a(BASF, target["page"], target["quote"])
        decision["clause"] = target["clause"]
        decision["locator_is_complete_clause"] = False
    context = [
        ("issuer", "BASF SE", 2, "BASF SE EUR 500,000,000 4.250 per cent. Notes due March 8, 2032"),
        ("currency", "EUR", 3, "Specified Currency Euro (EUR) Festgelegte Währung Euro (EUR)"),
        ("denomination", "EUR 100000", 3, "Specified Denomination EUR 100,000 Festgelegte Stückelung EUR 100.000"),
        ("rate", "4.250 percent per annum", 4, "Rate of Interest 4.250 per cent. per annum Zinssatz 4,250 % per annum"),
        ("first_interest", "2024-03-08", 4, "First Interest Payment Date March 8, 2024 Erster Zinszahlungstag 8. März 2024"),
        ("call_window", "2031-12-08 to 2032-03-07", 6, "festgelegte Wahlrückzahlungstag(e) (Call) 8. Dezember 2031 – 7. März 2032"),
        ("benchmark_spread", "0.300 percentage points", 7, "Vergleichbare Benchmark Rendite der entsprechenden zuzüglich 0,300%"),
        ("calculation_agent", "NatWest Markets N.V.", 7, "Berechnungsstelle NatWest Markets N.V."),
    ]
    contexts = [{"id": key, "value": value, "source": a("basf-2032-final", page, quote)}
                for key, value, page, quote in context]
    # These locators supplement, but never flatten, the full German source pages.
    conditions = [
        {"id": "initial_finance_guarantee", "disposition": "EXCLUDED_FOR_INITIAL_BASF_SE_ISSUER",
         "source": a(BASF, 110, "[(3) Garantie und Negativverpflichtung der Garantin."),
         "continuation": a(BASF, 111, "von BASF Finance und pünktliche Zahlung von Kapital und Zinsen und sonstiger auf die"),
         "reason": "Finance-only initial guarantee; issuer selection is BASF SE."},
        {"id": "successor_guarantee", "disposition": "CONDITIONAL_REQUIREMENT_RETAINED",
         "source": a(BASF, 129, "[(d) sichergestellt ist, dass sich die Verpflichtungen der Emittentin aus der Garantie"),
         "condition": "Section 10 substitution conditions, including all of (a)–(e), must be retained. This does not establish an actual substitution or guarantee performance."},
        {"id": "canada", "disposition": "EXCLUDED_CURRENCY_AND_CLEARING",
         "source": a(BASF, 113, "[(5) Interest Act (Canada).")},
        {"id": "rmb_settlement", "disposition": "EXCLUDED_EUR_ISSUE",
         "source": a(BASF, 115, "[(7) (a) Zahlungsverschiebung oder Abwicklung zum USD-Gegenwert.")},
        {"id": "cleanup_threshold", "disposition": "SELECTED_CONDITIONAL_RIGHT",
         "source": a(BASF, 122, "Gesamtnennbetrag von 75% oder mehr des ursprünglich begebenen"),
         "condition": "Acquisition AND reduction of principal in global note; whole residual issue; 30–60 days notice; par plus accrued interest. No actual exercise established."},
        {"id": "control_rating", "disposition": "SELECTED_CONDITIONAL_HOLDER_RIGHT",
         "source": a(BASF, 119, 'Kontrollwechselzeitraums zu einer Absenkung des Ratings auf Grund des'),
         "condition": "Both change of control and rating downgrade; the full definitions, issuer tax-call qualification and exercise procedure on pages 119–120 remain relevant."},
        {"id": "majority_amendment", "disposition": "RETAINED_UNCONSTRUCTED_CLAUSE",
         "source": a(BASF, 129, "Die Mehrheitsbeschlüsse der Gläubiger sind für alle Gläubiger gleichermaßen verbindlich."),
         "condition": "Creditor amendment power under SchVG is distinct from issuer redemption or statutory resolution."},
    ]
    predecessor = old.read(OLD_PACKET)
    packet = {
        "schema": "basf-selection-admission.v1", "issue_id": "basf-senior-2032", "isin": "XS2595418596",
        "predecessor": {"path": old.relative(OLD_PACKET), "sha256": OLD_PACKET_SHA},
        "sources": rows, "specification_sha256": old.sha(SPEC),
        "status": "EXPLICIT_SELECTION_COVERAGE_COMPLETE", "controlling_language": "de",
        "decisions": decisions, "issue_context": contexts, "conditional_branches": conditions,
        "annual_2022": annual_scope(docs[ANNUAL], rows[ANNUAL], docs[SUPPLEMENT], rows[SUPPLEMENT]),
        "construction_basis": predecessor["links"],
        "full_german_contract_constructed": False, "full_dossier_status": "UNRESOLVED",
        "certified_legal_answer": None, "independent_legal_adjudication": False, "production_promotion": False,
        "limits": [
            "All explicit Part I checkboxes and Yes/No responses accounted for; text fields and every nested template instruction are not a complete contract.",
            "Clause quotations locate provisions only; original margin/column extraction is retained and must not be treated as composed operative text.",
            "Earlier/interim Group and Finance reports, applicable agreements, amendment coverage and report-range discrepancy remain unresolved.",
            "English report is incorporated but its auditor report expressly makes the German original authoritative.",
            "No actual event, regulatory application, settlement facts, independent labels or unseen validation.",
        ],
    }
    return packet

def load_packet(packet):
    """Reject edited, rehashed, stale or overstated data by complete reconstruction."""
    expected = build_packet()
    require(packet == expected, "BASF packet differs from current source reconstruction")
    return copy.deepcopy(expected)

def consume(packet):
    """Expose validated selection facts to a successor without feeding template prose."""
    value = load_packet(packet)
    return {
        "schema": "basf-successor-selection-view.v1",
        "issue_id": value["issue_id"], "isin": value["isin"],
        "selected": [d["id"] for d in value["decisions"] if d["selected"]],
        "deleted": [d["id"] for d in value["decisions"] if not d["selected"]],
        "german_locators": {d["id"]: d["german_clause_locator"] for d in value["decisions"]},
        "conditional_branches": value["conditional_branches"],
        "annual_source_pages": [r["physical_page"] for r in value["annual_2022"]["pages"]],
        "full_dossier_status": "UNRESOLVED", "legal_answer": None,
        "full_german_contract_constructed": False, "production_promotion": False,
    }

def verify_anchors(value):
    if isinstance(value, dict):
        if {"original", "text_sha256", "quote", "start", "end", "page"} <= set(value):
            replay(value, ROOT)
        for child in value.values():
            verify_anchors(child)
    elif isinstance(value, list):
        for child in value:
            verify_anchors(child)
