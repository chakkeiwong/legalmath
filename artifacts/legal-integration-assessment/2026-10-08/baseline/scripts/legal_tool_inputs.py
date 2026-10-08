"""Frozen public-source questions; no model answer keys."""
import json
from scripts.legal_tool_program import ROOT, read, ref

QUESTIONS = [
 {"id":"p10","question":"Under paragraph 10 and footnote 1 of 26EC22, what would justify concluding that the Product Provider has retained responsibility and fulfilled the requirement? Distinguish allocation of authority, supervisory conduct and operational or record-keeping outcomes. What remains unresolved without an applicable standard and actual facts?"},
 {"id":"p14","question":"How do paragraph 14 and footnote 5 attach the request trigger, object and standard of confirmation and demonstration? What follows when no SFC request has been made, and how do paragraphs 15 and 16 differ? Preserve supported rival readings."},
 {"id":"evidence","question":"Does a recorded supervision event or a completed reconciliation establish adequate supervision or proper ownership records under the retained provisions? Identify the additional legal standard and factual premises needed, with source support."},
 {"id":"gatecoin","question":"What do the retained 2023 and 2025 Gatecoin judgments support concerning ownership, customer consent and distinct party relationships? Explain what would be needed to transfer a proposition to a Product Provider under 26EC22; preserve unresolved later treatment and the scenario-seven text tension."},
]
def build_corpus():
    p=ROOT/"artifacts/legal-interpretation-program/2026-10-06-offline-v1/P0/attempt-2/packet.json"
    packet=read(p)
    units=[{"id":u["unit_id"],"text":u["text"],"source":"retained-SFC-packet",
            "role":"regulatory-text","provenance":ref(p)} for u in packet["units"]]
    from scripts.legal_interpretation_s2_cases import build
    cases=build()
    for case in cases["cases"]:
        for passage in case["passages"]:
            units.append({"id":passage["passage_id"],"text":passage["text"],
                "source":case["manifest"]["judgment_id"],"role":passage["role"],
                "provenance":case["raw_source"],"role_status":"proposed",
                "limit":"Selected retained passage; full reasons and application require checking"})
    return {"units":units,"questions":QUESTIONS,"case_source_files":[c["raw_source"] for c in cases["cases"]],
            "scope":"Retained public sources, no new legal retrieval or private data",
            "selection_limit":"Development corpus; case passages selected in historical review, not blind evidence"}
