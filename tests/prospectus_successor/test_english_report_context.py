"""Inspected original English audit language must survive supplied annotations."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import report_scope
from legalmath.prospectus.successor.contracts import digest

FIXTURE = Path(__file__).parent / "fixtures/bes_2009_english_audit"
TEXT = (FIXTURE / "reading.txt").read_text()
FACTS = json.loads((FIXTURE / "facts.json").read_text())
REVIEW = {"kind": "DEVELOPMENT", "reviewer": "inspected-source regression",
          "reason": "Original English audit; no independent legal acceptance"}
UNKNOWN = {"status": "UNKNOWN", "reason": "Not supplied for this control"}


def fixture(text=TEXT, derivative=False):
    body = {"id": "audit", "document": "annual-report",
            "source_sha256": digest(text.encode()) if derivative else
                "5a8e79459e2109bd43173320af39aa4bc4ee08392746772f3bf7e4ffac8027c8",
            "pages": [{"page": 174, "mode": "raw"}, {"page": 175, "mode": "raw"}],
            "text": text, "characters": [
                {"output": i, "unit": "literal-source", "source_offset": i, "character": c}
                for i, c in enumerate(text)]}
    selected = {"version": "admitted-report-readings.v1",
                "reports": [{**body, "sha256": digest(body)}]}
    scope = {"version": "source-report-scope.v1", "readings_sha256": digest(selected),
             "review": REVIEW, "reports": [{"id": "audit",
                 "reading_sha256": selected["reports"][0]["sha256"], "facts": deepcopy(FACTS)}]}
    return selected, scope


def direct(selected, scope):
    return report_scope.explain(report_scope.admit(selected, scope))[0]


def rehash(selected, scope):
    row = selected["reports"][0]
    row["sha256"] = digest({k: v for k, v in row.items() if k != "sha256"})
    scope["reports"][0]["reading_sha256"] = row["sha256"]
    scope["readings_sha256"] = digest(selected)


def test_complete_inspected_audit_retains_qualifications():
    selected, scope = fixture()
    answer = direct(selected, scope)
    assert answer["status"] == "CONDITIONAL_SUPPLIED_READING"
    assert answer["english_report_context"]["normalized_closing_date"] == "2010-03-04"
    assert not answer["english_report_context"]["general_semantic_truth_established"]
    assert "in all\nmaterial respects" in answer["facts"]["conclusion"]["spans"][0]["quote"]
    assert "European Union" in answer["facts"]["conclusion"]["spans"][0]["quote"]
    assert "reasonable basis" in answer["facts"]["purpose"]["spans"][0]["quote"]
    assert "reasonable basis" not in answer["facts"]["assurance_level"]["spans"][0]["quote"]
    assert all(answer["facts"][f]["status"] == "UNKNOWN" for f in report_scope.EXTERNAL)
    assert answer["use_assessment"]["bond_repayment_or_conversion"] == "NOT_ESTABLISHED_BY_THIS_READING"


@pytest.mark.parametrize("field,omission", [
    ("subject", "Banco Espirito Santo"), ("subject", "December 2009"),
    ("assurance_level", "reasonable"), ("conclusion", "material respects"),
    ("conclusion", "European Union"), ("conclusion", "complete, true, current, clear, objective and lawful."),
    ("criteria", "European Union"), ("criteria", "Portuguese Institute"),
    ("purpose", "going concern"), ("purpose", "on a test basis"),
    ("translation_status", "free translation"),
])
def test_omitted_words_withhold_even_with_exact_remaining_spans(field, omission):
    selected, scope = fixture()
    fact = scope["reports"][0]["facts"][field]
    original = next(s for s in fact["spans"] if omission in s["quote"])
    start = TEXT.index(omission, original["start"], original["end"])
    fact["spans"].remove(original)
    for a, b in ((original["start"], start), (start + len(omission), original["end"])):
        if TEXT[a:b].strip():
            fact["spans"].append({"start": a, "end": b, "quote": TEXT[a:b]})
    answer = direct(selected, scope)
    assert answer["status"] == "INCOMPLETE_SOURCE_READING"
    assert field in answer["unresolved_english_report_fields"]


@pytest.mark.parametrize("field", [
    "identity", "subject", "purpose", "assurance_level", "criteria", "conclusion",
    "translation_status", "report_date"])
def test_unknown_required_context_withholds(field):
    selected, scope = fixture()
    scope["reports"][0]["facts"][field] = deepcopy(UNKNOWN)
    assert direct(selected, scope)["status"] == "INCOMPLETE_SOURCE_READING"


@pytest.mark.parametrize("field,quote,append", [
    ("assurance_level", "reasonable basis for our opinion.", False),
    ("report_date", "31\nDecember 2009", False),
    ("report_date", "31\nDecember 2009", True),
])
def test_literal_but_wrong_role_withholds(field, quote, append):
    selected, scope = fixture()
    a = TEXT.index(quote)
    spans = scope["reports"][0]["facts"][field]["spans"]
    if not append:
        spans.clear()
    spans.append({"start": a, "end": a + len(quote), "quote": quote})
    assert field in direct(selected, scope)["unresolved_english_report_fields"]


@pytest.mark.parametrize("kind", ["COMMITTEE_REPORT", "LIMITED_FINANCIAL_REVIEW",
                                "LIMITED_SUSTAINABILITY_ASSURANCE", "UNAUDITED_FINANCIAL_RELEASE"])
def test_false_consistent_category_refused(kind):
    selected, scope = fixture()
    facts = scope["reports"][0]["facts"]
    facts["identity"]["value"] = kind
    for field, value in report_scope.PROFILES[kind].items():
        facts[field]["value"] = value
    if kind == "COMMITTEE_REPORT":
        facts["assurance_level"] = deepcopy(UNKNOWN)
    if kind == "UNAUDITED_FINANCIAL_RELEASE":
        facts["conclusion"] = deepcopy(UNKNOWN)
    with pytest.raises(ValueError, match="English report contradicts"):
        direct(selected, scope)


@pytest.mark.parametrize("mutation,derivative", [
    ("append_exception", False), ("append_exception", True),
    ("drop_scope", False), ("drop_scope", True),
    ("changed_date", False), ("changed_date", True), ("drop_title", False)])
def test_changed_reading_cannot_inherit_finite_support(mutation, derivative):
    text = TEXT
    if mutation == "append_exception":
        text += "\nExcept for an unresolved material qualification."
    elif mutation == "drop_scope":
        text = text[:text.index("\nScope\n")] + text[text.index("\nOpinion\n"):]
    elif mutation == "changed_date":
        text = text.replace("4 March 2010", "4 March 2011")
    else:
        text = text.replace("AUDITORS’ REPORT", "ALTERED TITLE")
    selected, scope = fixture(text, derivative)
    scope["reports"][0]["facts"] = {f: deepcopy(UNKNOWN) for f in report_scope.FACTS}
    answer = direct(selected, scope)
    assert answer["status"] == "INCOMPLETE_SOURCE_READING"
    assert answer["english_report_context"]["status"] == "UNRECOGNIZED_OR_CHANGED_SOURCE_READING"


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "wrong_character", "negative_offset"])
def test_rehashing_cannot_hide_damaged_character_provenance(mutation):
    selected, scope = fixture()
    chars = selected["reports"][0]["characters"]
    if mutation == "missing":
        chars.pop(TEXT.index("AUDITORS"))
    elif mutation == "duplicate":
        chars.append(deepcopy(chars[0]))
    elif mutation == "wrong_character":
        chars[0]["character"] = "X"
    else:
        chars[0]["source_offset"] = -1
    rehash(selected, scope)
    with pytest.raises(ValueError, match="provenance|unmapped"):
        direct(selected, scope)
