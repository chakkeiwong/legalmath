"""Actual distinct2010 report roles, qualifications and dates."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import report_scope
from legalmath.prospectus.successor.contracts import digest
from test_english_report_context import direct, fixture as earlier, rehash, UNKNOWN

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(kind="audit", text=None):
    folder = FIXTURES / ("bes_2010_english_" + kind)
    selected, scope = earlier((folder / "reading.txt").read_text() if text is None else text)
    selected["reports"][0]["source_sha256"] = "f6c1196ffcbaed34dc4068b4fbc095b4494e421e224977bfa54b215134e32f25"
    selected["reports"][0]["pages"] = [{"page": 190 if kind == "audit" else 191, "mode": "raw"}]
    scope["reports"][0]["facts"] = json.loads((folder / "facts.json").read_text())
    rehash(selected, scope)
    return selected, scope


def test_statutory_financial_and_other_legal_conclusions_are_distinct():
    report = direct(*fixture())
    assert report["status"] == "CONDITIONAL_SUPPLIED_READING"
    context = report["english_report_context"]
    assert context["normalized_closing_date"] == "2011-03-04"
    statements = context["distinct_source_statements"]
    assert "7. In our opinion" in statements["financial_statement_opinion"]["quote"]
    assert "8. It is also our opinion" in statements["other_legal_requirements"]["quote"]
    assert "article 245.º-A" in statements["other_legal_requirements"]["quote"]
    assert statements["financial_statement_opinion"]["end"] < statements["other_legal_requirements"]["start"]


def test_committee_concurrence_retains_knowledge_and_recommendation():
    report = direct(*fixture("committee"))
    assert report["status"] == "CONDITIONAL_SUPPLIED_READING"
    assert report["facts"]["assurance_level"]["status"] == "UNKNOWN"
    assert report["english_report_context"]["normalized_closing_date"] == "2011-03-07"
    assert report["use_assessment"]["financial_statement_audit_opinion"] == "NOT_ESTABLISHED_BY_THIS_READING"
    statements = report["english_report_context"]["distinct_source_statements"]
    assert "dated 4 March 2011" in statements["auditor_concurrence"]["quote"]
    assert "best of their knowledge" in statements["qualified_declaration"]["quote"]
    assert "255,997,121.83 euros" in statements["approval_recommendation"]["quote"]
    assert all(report["facts"][f]["status"] == "UNKNOWN" for f in report_scope.EXTERNAL)


@pytest.mark.parametrize("kind,field,omission", [
    ("audit", "subject", "31 December 2010"), ("audit", "conclusion", "material respects"),
    ("audit", "conclusion", "article 245.º-A"), ("audit", "conclusion", "European Union"),
    ("audit", "purpose", "article 451"), ("audit", "translation_status", "free translation"),
    ("committee", "conclusion", "best of their knowledge"),
    ("committee", "conclusion", "main risks and uncertainties"),
    ("committee", "conclusion", "Unconsolidated and Consolidated"),
    ("committee", "conclusion", "255,997,121.83 euros"),
    ("committee", "subject", "appropriation of the unconsolidated profit"),
])
def test_exact_remaining_spans_cannot_drop_qualifications(kind, field, omission):
    selected, scope = fixture(kind)
    text = selected["reports"][0]["text"]
    fact = scope["reports"][0]["facts"][field]
    original = next(s for s in fact["spans"] if omission in s["quote"])
    a = text.index(omission, original["start"], original["end"])
    fact["spans"].remove(original)
    for start, end in ((original["start"], a), (a + len(omission), original["end"])):
        if text[start:end].strip():
            fact["spans"].append({"start": start, "end": end, "quote": text[start:end]})
    report = direct(selected, scope)
    assert report["status"] == "INCOMPLETE_SOURCE_READING"
    assert field in report["unresolved_english_report_fields"]


@pytest.mark.parametrize("kind,field", [
    ("audit", "identity"), ("audit", "subject"), ("audit", "conclusion"),
    ("audit", "purpose"), ("audit", "criteria"), ("audit", "report_date"),
    ("audit", "assurance_level"), ("audit", "translation_status"),
    ("committee", "identity"), ("committee", "subject"), ("committee", "conclusion"),
    ("committee", "purpose"), ("committee", "addressee"), ("committee", "report_date"),
])
def test_unknown_required_field_withholds(kind, field):
    selected, scope = fixture(kind)
    scope["reports"][0]["facts"][field] = deepcopy(UNKNOWN)
    assert field in direct(selected, scope)["unresolved_english_report_fields"]


@pytest.mark.parametrize("kind,quote", [("audit", "31 December 2010"), ("committee", "4 March 2011")])
@pytest.mark.parametrize("append", [False, True])
def test_dated_event_cannot_replace_or_contaminate_closing(kind, quote, append):
    selected, scope = fixture(kind)
    text = selected["reports"][0]["text"]
    a = text.index(quote)
    spans = scope["reports"][0]["facts"]["report_date"]["spans"]
    if not append:
        spans.clear()
    spans.append({"start": a, "end": a + len(quote), "quote": quote})
    assert "report_date" in direct(selected, scope)["unresolved_english_report_fields"]


@pytest.mark.parametrize("kind", ["audit", "committee"])
def test_roles_cannot_be_swapped_with_consistent_codes(kind):
    selected, scope = fixture(kind)
    facts = scope["reports"][0]["facts"]
    opposite = "COMMITTEE_REPORT" if kind == "audit" else "STATUTORY_FINANCIAL_AUDIT"
    facts["identity"]["value"] = opposite
    for field, value in report_scope.PROFILES[opposite].items():
        facts[field] = {"status": "SUPPLIED", "spans": deepcopy(facts["identity"]["spans"]), "value": value}
    if opposite == "COMMITTEE_REPORT":
        facts["assurance_level"] = deepcopy(UNKNOWN)
    with pytest.raises(ValueError, match="English report contradicts"):
        direct(selected, scope)


@pytest.mark.parametrize("kind", ["audit", "committee"])
@pytest.mark.parametrize("mutation", ["append", "merged", "drop_body"])
def test_fresh_hashes_do_not_bless_changed_or_merged_reports(kind, mutation):
    text = (FIXTURES / ("bes_2010_english_" + kind) / "reading.txt").read_text()
    if mutation == "append":
        text += "\nExcept for an unresolved qualification."
    elif mutation == "merged":
        other = "committee" if kind == "audit" else "audit"
        text += "\n" + (FIXTURES / ("bes_2010_english_" + other) / "reading.txt").read_text()
    else:
        text = text[:400]
    selected, scope = fixture(kind, text)
    scope["reports"][0]["facts"] = {f: deepcopy(UNKNOWN) for f in report_scope.FACTS}
    report = direct(selected, scope)
    assert report["english_report_context"]["status"] == "UNRECOGNIZED_OR_CHANGED_SOURCE_READING"
    assert report["status"] == "INCOMPLETE_SOURCE_READING"
