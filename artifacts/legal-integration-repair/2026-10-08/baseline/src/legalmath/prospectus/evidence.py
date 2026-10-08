"""Mechanical quotation retrieval and explicitly provisional source interpretations."""
from pathlib import Path
import re

from .common import ARCHIVE, digest, read, sha, write
from .semantics import CLASS_FACTS, SPI_FACTS, complex_bond, eligible, possible_decision

PATTERNS = {
    "preferred_stock": r"(?:perpetual\s+)?(?:fixed.rate\s+(?:reset\s+)?)?non.cumulative\s+(?:perpetual\s+)?preferred\s+stock",
    "bond": r"(?:(?:tier\s*1|AT1)\s+capital\s+notes|perpetual\s+subordinated\s+contingent\s+convertible\s+securities)",
    "perpetual": r"(?:notes|securities|preferred stock).{0,90}?(?:are|will be|is|shall be).{0,40}?perpetual|perpetual.{0,80}?(?:notes|securities|preferred stock)",
    "subordinated": r"(?:notes|securities).{0,90}?subordinated|subordinated.{0,70}?(?:notes|securities)",
    "contingent_conversion": r"(?:trigger event|viability event|automatic conversion).{0,240}?(?:convert|ordinary shares)|(?:notes|securities).{0,130}?(?:converted into|conversion into).{0,90}?(?:shares|equity)",
    "no_conversion": r"(?:preferred stock|notes|securities).{0,65}?(?:not|never)\s+(?:be\s+)?convertible",
    "write_down_mention": r"(?:principal|notes|securities|claims).{0,180}?(?:written.down|write.down|reduced to zero|cancelled|canceled)",
    "statutory_resolution": r"(?:bail.in power|restructuring proceedings|resolution authority)",
    "non_cumulative": r"(?:dividends|interest|payments).{0,65}?(?:not be cumulative|non.cumulative|will not accumulate)",
    "capital_trigger": r"(?:CET1|common equity tier\s*1|capital ratio).{0,200}?(?:less than|below|at or below|equal to or less than)\s*(?:a\s+)?(?:ratio of\s+)?\d+(?:\.\d+)?\s*(?:%|per cent)",
    "dependency": r"(?:incorporated by reference|relevant final terms|as amended|supplemented from time to time)",
}


def normalized(text):
    return re.sub(r"\s+", " ", text).strip()


def locate(page, pattern):
    # Normalize only whitespace. Preserve an exact normalized quotation, original
    # page hash and a deterministic location; never call this an entailment proof.
    text = normalized(page["text"])
    for match in re.finditer(pattern, text, flags=re.I):
        start, end = max(0, match.start() - 130), min(len(text), match.end() + 180)
        yield {"page": page["page"], "start": start, "end": end, "quote": text[start:end],
               "matched_text": match.group(), "page_text_sha256": sha(page["text"].encode())}


def quote_check(claim, document):
    page = next((p for p in document["pages"] if p["page"] == claim["page"]), None)
    if page is None or claim["source_sha256"] != document["source_sha256"]:
        return False
    return (sha(page["text"].encode()) == claim["page_text_sha256"] and
            normalized(page["text"])[claim["start"]:claim["end"]] == claim["quote"] and
            claim["matched_text"] in claim["quote"])


def observations(row, document):
    claims = []
    for page in document["pages"]:
        for field, pattern in PATTERNS.items():
            for evidence in locate(page, pattern):
                # A reference to other instruments cannot identify this instrument.
                foreign = bool(re.search(r"\b(?:other|another|such other)\s+(?:capital\s+)?(?:instruments|securities|notes)\b",
                                         evidence["quote"], re.I))
                negative = field != "no_conversion" and bool(re.search(r"\b(?:not|never|no)\b", evidence["matched_text"], re.I))
                local_negation = field == "no_conversion" and bool(re.search(
                    r"not\s+(?:be\s+)?convertible\b[^.;]{0,100}\b(?:at|on|by)\b[^.;]{0,60}\b(?:option|request|election|holder)",
                    evidence["quote"], re.I))
                claims.append({"id": digest([row["id"], field, evidence])[:24], "document": row["id"],
                               "source_sha256": document["source_sha256"], "field": field,
                               "status": "CANDIDATE", "scope": "FOREIGN_REFERENT" if foreign else "LIMITED_NEGATION" if local_negation else "NEGATED_OR_UNCERTAIN" if negative else "REFERENT_NOT_PROVED",
                               "legal_entailment": "NOT_ESTABLISHED", **evidence})
    if any(not quote_check(c, document) for c in claims):
        raise ValueError("Quotation locator failed")
    return claims


def describe(row, document, claims):
    primary = [c for c in claims if c["page"] <= 8 and c["scope"] == "REFERENT_NOT_PROVED"]
    fields = {name: [c["id"] for c in primary if c["field"] == name] for name in PATTERNS}
    facts = {k: None for k in CLASS_FACTS}
    if row["role"] in ("issue", "preliminary", "terms"):
        if fields["bond"] and not fields["preferred_stock"]:
            facts["bond"] = True
        elif fields["preferred_stock"] and not fields["bond"]:
            facts["bond"] = False
        elif fields["bond"] and fields["preferred_stock"]:
            facts["bond"] = "conflict"
        for k in ("perpetual", "subordinated", "contingent_conversion"):
            if fields[k]:
                facts[k] = True
        if fields["no_conversion"]:
            facts["contingent_conversion"] = "conflict" if facts["contingent_conversion"] else False
    # A write-down mention can concern statutory powers or another security.
    # It deliberately does not become a contractual-write-down fact.
    conditional = possible_decision(CLASS_FACTS, facts, complex_bond)
    conclusion = "COMPLEX_BOND_UNDER_CANDIDATE_PREMISES" if conditional["decision"] == "TRUE" else "UNDETERMINED"
    issues = ["Natural-language entailment and referent scope are not proved",
              "Complete incorporated-document and amendment closure is not established",
              "The SFC example list is non-exhaustive; a false sufficient-condition result does not establish non-complexity",
              "No client, consent, category choice, trade exposure or assessment-date facts were supplied"]
    if document["preliminary_indicator"]:
        issues.append("Preliminary issue terms cannot establish final issued terms")
    if row["role"] == "base-programme":
        issues.append("Programme terms require a specific issue and its final terms")
    mechanisms = []
    if fields["contingent_conversion"]:
        mechanisms.append("equity_conversion_candidate")
    if fields["write_down_mention"]:
        mechanisms.append("write_down_mention_requires_contractual_vs_statutory_resolution")
    if fields["non_cumulative"] or fields["preferred_stock"]:
        mechanisms.append("discretionary_distribution_candidate")
    return {"document": row["id"], "instrument": row["instrument"], "role": row["role"],
            "source_sha256": document["source_sha256"], "preliminary": document["preliminary_indicator"],
            "candidate_facts": facts, "supporting_claim_ids": fields, "mechanisms": mechanisms,
            "classification": conclusion, "formal_sufficient_condition": conditional,
            "spi_eligibility": possible_decision(SPI_FACTS, {}, eligible), "open_issues": issues,
            "legal_correctness": "NOT_ESTABLISHED", "human_quality_evidence": False}


def investigate(rows, directory, *, root=ARCHIVE):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    reports, all_claims, absent = [], [], []
    for row in rows:
        path = Path(root) / "text" / (row["id"] + ".json")
        if not path.exists():
            absent.append(row["id"])
            continue
        doc = read(path)
        original = Path(root) / "originals" / (row["id"] + "." + row["kind"])
        if not original.exists() or sha(original.read_bytes()) != doc["source_sha256"]:
            raise ValueError("Candidate evidence is not bound to preserved original: " + row["id"])
        claims = observations(row, doc)
        all_claims.extend(claims)
        if row["role"] in ("issue", "preliminary", "terms", "base-programme", "duplicate-edition"):
            reports.append(describe(row, doc, claims))
    write(directory / "quotations.json", all_claims)
    write(directory / "instruments.json", reports)
    result = {"documents_requested": len(rows), "documents_missing": absent, "quotations_checked": len(all_claims),
              "instrument_reports": len(reports), "conditional_complex_candidates": sum(r["classification"].startswith("COMPLEX") for r in reports),
              "unconditional_legal_decisions": 0, "legal_meaning": "NOT_ESTABLISHED",
              "purpose": "Transparent bounded retrieval and conditional interpretations; not an evaluated general English interpreter"}
    write(directory / "summary.json", result)
    return result
