"""Issue-specific source proposal; source fidelity is not English entailment."""
import json
from pathlib import Path
import re

from ..canonical import digest
from ..transaction.evidence import sha

KEY = "ubs-sgd-at1-2024-final-published"
ISIN = "CH1357852636"
PDF_SHA = "9549d2725727ab50eaaedbbeb420c3f6cb4b27f6976a1dcf55a12c50134a0a88"
TEXT_SHA = "186a3a33efcda414ebf6d22ce6bec5c7618c2c76994a5b8ee540110a95fb1813"

# Page numbers refer to the PDF, not the printed page counter. Annex B is excluded.
ANCHORS = {
    "identity": (1, "CH1357852636"),
    "calendar": (4, "otherwise, Singapore and Zurich"),
    "initial_price": (5, '"Conversion Price" means SGD 37.77'),
    "issue_date": (10, '"Issue Date" means 24 June 2024'),
    "share_creation": (15, "on or prior to the applicable Conversion Date"),
    "threshold": (16, '"Threshold Ratio" means 7 per cent.'),
    "ratio": (16, "the Higher-Trigger Amount as of such Publication Date"),
    "denomination": (17, "minimum denominations of SGD 250,000"),
    "debt": (17, "direct, unsecured and subordinated obligations"),
    "trigger": (25, "if the Issuer gives the Holders a Trigger"),
    "ordinary_notice": (25, "within five Business Days"),
    "extraordinary_notice": (26, "on such Extraordinary Publication Date"),
    "trigger_conversion": (26, "no more than 20 Business Days after the date of such notice"),
    "higher_trigger": (26, "such date will be deemed to be the Trigger Event Notice Date"),
    "restoration": (26, "prior to the earlier of"),
    "viability_notice": (27, "within three days of the date"),
    "viability_conversion": (27, "20 Business Days following the occurrence of the Viability Event"),
    "viability_basis": (27, "FINMA has notified UBS Group AG in writing"),
    "final_publication": (28, "subsequently published will have no effect"),
    "alternative": (28, "from the date of such notice, such provisions will cease to apply"),
    "interest": (28, "cancellation of any accrued and unpaid interest"),
    "price_date": (29, "subject to adjustment to (and including) the date"),
    "split": (29, "consolidation, reclassification, redesignation or subdivision"),
    "extraordinary_distribution": (30, "Extraordinary Distribution"),
    "rights": (31, "less than 95 per cent."),
    "floor": (33, "par value"),
    "carry_forward": (34, "carried forward"),
    "successor_price": (35, '"New Conversion Price"'),
    "fractions": (36, "no cash payment will be made in lieu thereof"),
    "offer": (37, "a Trigger Event only"),
    "delivery": (38, "within five Business Days"),
    "adviser": (39, "fails to make such determination"),
    "notices": (43, "date of the first such publication"),
    "substitution": (43, "ISSUER SUBSTITUTION"),
    "governing_law": (45, "governed by and construed in accordance with the laws of Switzerland"),
}

DEPENDENCIES = [
    ("agency_agreement", [3], "MISSING", "Agency agreement and amendments; do not infer incorporated obligations."),
    ("settlement_agreement", [15], "MISSING", "Settlement agency agreement and amendments."),
    ("applicable_swiss_law", [15, 16, 45], "QUALIFIED", "Retained Swiss legal dossier; dated force, applicability, procedure and actual order remain separate."),
    ("hk_selling_rules", [], "RETAINED_QUALIFIED", "HKMA 2022 Annex 1/FAQ and SFC sources; currentness and actual institution/client facts remain open."),
    ("bank_sanctions_inventory", [], "RETAINED_QUALIFIED", "All fourteen existing bank obligations remain; issuer nationality is not a sanctions decision."),
    ("publication_and_capital", [8, 10, 16, 28], "MISSING", "Publication snapshot, higher-trigger capital/FX and balance-sheet amounts; later restatements do not replace that snapshot."),
    ("business_calendars", [4], "MISSING", "Covered Zurich and Singapore bank/FX opening dates; public holidays alone are insufficient."),
    ("notice_history", [26, 27, 28, 43], "MISSING", "Actual issuer/FINMA notices, publication/delivery channel and higher-trigger events."),
    ("corporate_action_history", [29, 30, 31, 32, 33, 34, 35, 36, 43], "MISSING", "Complete history through notice, changes to terms and issuer substitution; absence of data is not a clean history."),
    ("market_inputs", [5, 6, 13, 17, 31, 35, 36], "MISSING", "Relevant-market VWAP windows and dated FX; cash/valuation is not implied by a share count."),
    ("contractual_determinations", [33, 34, 39], "MISSING", "Issuer/FINMA/adviser acts required by the terms are factual inputs, never quality labels."),
    ("private_account_and_route", [], "MISSING", "Booking entity, mandate, PI status, route, holdings, policy and client evidence."),
]


def dossier(root):
    root = Path(root)
    original = root / "docs/prospectus/originals" / (KEY + ".pdf")
    extracted = root / "docs/prospectus/text" / (KEY + ".json")
    if sha(original.read_bytes()) != PDF_SHA or sha(extracted.read_bytes()) != TEXT_SHA:
        raise ValueError("Unsupported source edition: reassess the instrument profile")
    document = json.loads(extracted.read_text())
    if document["source_sha256"] != PDF_SHA:
        raise ValueError("Extraction is detached from the retained PDF")
    pages = {row["page"]: " ".join(row["text"].split()) for row in document["pages"]}
    bindings = {}
    for name, (page, quote) in ANCHORS.items():
        if quote not in pages[page]:
            raise ValueError("Changed or missing source anchor: " + name)
        bindings[name] = {"pdf_page": page, "quote": quote, "page_text_sha256": sha(pages[page].encode())}

    def number(page, pattern):
        matches = re.findall(pattern, pages[page])
        if not matches or len(set(matches)) != 1:
            raise ValueError("Nonunique or missing literal term: " + pattern)
        return matches[0].replace(",", "")

    terms = {
        "issue_date": "2024-06-24", "currency": "SGD",
        "initial_conversion_price": number(5, r'"Conversion Price" means SGD ([0-9.]+),'),
        "threshold_percent": number(16, r'"Threshold Ratio" means (\d+) per cent\.'),
        "denomination": number(17, r"minimum denominations of SGD ([0-9,]+) and integral multiples"),
        "initial_principal": number(17, r"initial aggregate principal amount of the Notes will be SGD ([0-9,]+)\."),
    }
    values = {"debt_legal_form": True, "qualifying_contingent_loss_absorption": True,
              "plain_debt_or_deposit": False, "qualifying_wrapper": False, "loss_absorption_fund": False}
    interpretation = {"values": values, "status": "SOURCE_DEPENDENT_PROPOSAL",
        "source_anchors": ["debt", "trigger", "viability_basis", "fractions"],
        "reason": "Direct notes with contingent share conversion; neither an equity-form preference share nor a fund wrapper. Contractual conversion is distinct from statutory write-down powers.",
        "legal_entailment": "NOT_ESTABLISHED"}
    data = {"profile": "ubs-june2024-annex-a.v1", "instrument": ISIN, "source": KEY,
        "pdf_sha256": PDF_SHA, "text_sha256": TEXT_SHA, "annex": "A", "pdf_pages": [3, 45],
        "terms": terms, "anchors": bindings, "product_interpretation": interpretation,
        "dependencies": [{"id": key, "pdf_pages": pp, "status": status, "reason": why}
                         for key, pp, status, why in DEPENDENCIES],
        "anomalies": [{"id": "extraordinary_distribution_denominator", "pdf_page": 30,
            "printed_formula": "(A-B)/B", "alternative_not_adopted": "(A-B)/A",
            "rendered_inspection": "PDF formula denominator is B; this is not merely an extraction defect",
            "operational_price": "QUALIFIED_PENDING_AUTHORITATIVE_CLARIFICATION"}],
        "current_applicability": "NOT_ESTABLISHED", "human_quality_evidence": False}
    return {**data, "dossier_hash": digest(data)}


def verify(packet, root):
    if packet != dossier(root):
        raise ValueError("Changed source, terms or interpretation; reassessment required")
    return packet
