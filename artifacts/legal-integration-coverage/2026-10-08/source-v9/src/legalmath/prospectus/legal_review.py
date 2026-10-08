"""Conditional legal-review guards, not an English-to-law interpretation oracle.

The predicates implement the explicitly bounded specification in the CoCo survey.
Callers must establish source scope and meaning separately. Unknown is never a
negative factual finding, and satisfaction of one restriction is not sale permission.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
from pathlib import Path

from .semantics import possible_decision


AUTHORITY_FACTS = (
    "jurisdiction_matches", "entity_covered", "instrument_covered",
    "basis_in_force", "event_conditions_met", "procedure_satisfied",
    "legal_authority_established",
)
DIRECT_DEBT_FACTS = (
    "debt_legal_form", "qualifying_contingent_loss_absorption",
    "plain_debt_or_deposit", "bail_in_possible",
)
HKMA_SALE_FACTS = (
    "registered_institution", "in_scope_product", "professional_investor",
    "faq9_exception_established",
)
SALE_FACTS = (
    "applicable_rules_identified", "source_versions_current",
    "offering_restrictions_satisfied", "hkma_requirement_satisfied",
    "sfc_requirements_satisfied", "mandate_satisfied",
    "client_facts_complete", "interpretation_obligations_discharged",
)


def authority_preconditions(observations):
    """Necessary premises of a specified power; TRUE does not mean it was used."""
    return possible_decision(AUTHORITY_FACTS, observations,
                             lambda w: all(w[k] for k in AUTHORITY_FACTS))


def hkma_direct_debt_scope(observations):
    """Annex 1/FAQ 1–2 candidate for direct debt only, not funds or wrappers.

    `qualifying_contingent_loss_absorption` includes the relevant trigger/regime
    interpretation. Merely finding a statutory bail-in warning cannot establish it.
    Legal-form or exclusion conflicts must be supplied as conflict, not guessed.
    """
    return possible_decision(DIRECT_DEBT_FACTS, observations, lambda w:
        w["debt_legal_form"] and w["qualifying_contingent_loss_absorption"]
        and not w["plain_debt_or_deposit"])


def hkma_pi_restriction(observations):
    """Only the conditional PI restriction, including the established FAQ 9 route.

    The exception is a compound premise: all four conditions and the specific
    service arrangement must be established. It does not exempt the adviser from
    its own obligations, nor permit an intermediary to evade the requirements.
    """
    return possible_decision(HKMA_SALE_FACTS, observations, lambda w:
        not (w["registered_institution"] and w["in_scope_product"])
        or w["faq9_exception_established"] or w["professional_investor"])


def sale_preconditions(observations, *, spi_eligible=None):
    """Necessary sale conditions, independent of procedural SPI eligibility.

    This does not enumerate all laws; rules-identified and interpretation premises
    must remain unknown until their separate obligations have been discharged.
    """
    if spi_eligible is not None and type(spi_eligible) is not bool:
        raise ValueError("SPI eligibility must be Boolean or unknown")
    return possible_decision(SALE_FACTS, observations,
                             lambda w: all(w[k] for k in SALE_FACTS))


def _aware(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("A timezone-aware datetime is required")


@dataclass(frozen=True)
class LegalVersion:
    """One provision's stipulated validity and knowledge intervals.

    Open-ended validity means no recorded end, not proof of present currentness.
    `known_from` belongs to the replay's knowledge history, not an invented date
    inferred from downloading an old document today.
    """
    valid_from: datetime
    valid_until: datetime | None
    known_from: datetime

    def __post_init__(self):
        for value in (self.valid_from, self.known_from):
            _aware(value)
        if self.valid_until is not None:
            _aware(self.valid_until)
            if self.valid_until <= self.valid_from:
                raise ValueError("Invalid provision interval")

    def visible_and_in_period(self, effective_at, known_at):
        _aware(effective_at)
        _aware(known_at)
        if self.known_from > known_at:
            return "NOT_KNOWN"
        if effective_at < self.valid_from or (
                self.valid_until is not None and effective_at >= self.valid_until):
            return "OUT_OF_PERIOD"
        return "IN_RECORDED_PERIOD"


def judgment_result(*, proceeding, disposition, final, suspensive_effect,
                    repayment_received):
    """Report distinct propositions; procedural dismissal never settles merits.

    These are supplied event observations. The function does not infer the legal
    effect of a stay or infer receipt of money from any court disposition.
    """
    allowed = {
        "procedural": {"inadmissible", "dismissed", "allowed"},
        "merits": {"annulled", "upheld", "remitted"},
    }
    if proceeding not in allowed or disposition not in allowed[proceeding]:
        raise ValueError("Disposition does not match proceeding")
    for value in (final, suspensive_effect, repayment_received):
        if value is not None and type(value) is not bool:
            raise ValueError("Event observations must be Boolean or unknown")
    if final is True and suspensive_effect is True:
        raise ValueError("A final judgment cannot have a pending appeal stay")
    return {
        "merits": "NOT_DECIDED" if proceeding == "procedural" else disposition.upper(),
        "final": final, "suspensive_effect": suspensive_effect,
        "repayment_received": repayment_received,
    }


def verify_source_dependencies(root, expected):
    """Compare retained bytes only; no authenticity/entailment verdict is implied."""
    root = Path(root).resolve()
    if not expected:
        raise ValueError("At least one source dependency is required")
    changed = []
    for relative, digest in expected.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Source dependency escapes archive")
        if (not isinstance(digest, str) or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)):
            raise ValueError("Expected SHA-256 required")
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            changed.append(relative)
    return {"status": "STALE" if changed else "UNCHANGED", "changed": sorted(changed),
            "legal_currentness": "NOT_ESTABLISHED", "source_entailment": "NOT_ESTABLISHED"}


def dossier_inputs(root):
    """Enumerate the bounded, locally retained legal dossier for campaign hashes."""
    root = Path(root).resolve()
    manifest = root / "docs/prospectus/legal/manifest.json"
    data = json.loads(manifest.read_text())
    rows = data["sources"]
    if not 1 <= len(rows) <= 32 or len({r["key"] for r in rows}) != len(rows):
        raise ValueError("Invalid legal source inventory")
    expected = {}
    for row in rows:
        for field, hash_field in (("path", "sha256"), ("text_path", "text_sha256")):
            name, digest = row[field], row[hash_field]
            path = (root / name).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Legal dossier dependency escapes workspace")
            if name in expected and expected[name] != digest:
                raise ValueError("Conflicting legal source digest")
            expected[name] = digest
    return manifest, data, expected


def dossier_files(root):
    manifest, _, expected = dossier_inputs(root)
    return [manifest, *(Path(root) / name for name in sorted(expected))]


def verify_dossier(root):
    _, data, expected = dossier_inputs(root)
    integrity = verify_source_dependencies(root, expected)
    if integrity["status"] != "UNCHANGED":
        raise ValueError("Legal source dossier is stale: " + ", ".join(integrity["changed"]))
    by_key = {r["key"]: r for r in data["sources"]}
    amendment_checks = []
    for check in data.get("amendment_checks", []):
        row = by_key[check["source_key"]]
        result = required_articles((Path(root) / row["text_path"]).read_text(),
                                   check["required_articles"])
        amendment_checks.append({**check, **result})
        if result["missing"] and check["use_for_applicable_law"]:
            raise ValueError("Required amendment absent: " + row["key"])
    return {**integrity, "sources": len(data["sources"]),
            "amendment_checks": amendment_checks,
            "unknowns": data["open_obligations"], "human_quality_evidence": False}


def required_articles(text, articles):
    """Structural omission diagnostic; presence is not faithful legal meaning.

    An exact supplied article identifier may be followed by a PDF footnote number.
    The checker does not infer which amendments are legally applicable.
    """
    if not articles or len(set(articles)) != len(articles) or any(
            not re.fullmatch(r"[0-9]+[a-z]*", a) for a in articles):
        raise ValueError("Distinct explicit article identifiers required")
    missing = [a for a in articles if not re.search(
        r"^Art\.\s*" + re.escape(a) + r"(?=\s|[0-9]|$)", text, re.MULTILINE)]
    return {"status": "MISSING_REQUIRED_ARTICLES" if missing else "HEADINGS_PRESENT",
            "missing": missing, "semantic_incorporation": "NOT_ESTABLISHED"}
