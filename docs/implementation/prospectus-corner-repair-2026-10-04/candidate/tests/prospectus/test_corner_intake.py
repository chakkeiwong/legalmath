"""Bundle identity and empty-extraction integration checks."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus.document_intake import extraction_coverage, validate_bundle
from legalmath.prospectus.loss_absorption_reader import analyze_issue
from tests.prospectus.test_loss_absorption import fixture, ORDINARY


def bundle(tmp_path):
    issue, docs, _ = fixture(tmp_path, [ORDINARY])
    key = issue["documents"][0]["id"]
    issue.update(issuer="Issuer", security_class="senior", issue_date="2014-01-20", identifiers=["PTBENKOM0012"])
    docs[key].update(role="final_terms", edition_date="2014-01-20", base_id=None,
                     issuer="Issuer", programme_issuers=["Issuer"], security_class="senior",
                     identifiers=["PTBENKOM0012"])
    issue["document_contract"] = {
        "issuer":"Issuer", "security_class":"senior", "issue_date":"2014-01-20",
        "required_documents":[{k:docs[key].get(k) for k in ("id","sha256","role","edition_date","base_id")}],
        "unresolved_dependencies":[], "precedence_reviewed":True}
    return issue, docs, key


def test_complete_bundle_can_bind(tmp_path):
    issue, docs, _ = bundle(tmp_path)
    assert validate_bundle(issue, docs, tmp_path)["status"] == "BOUND"


@pytest.mark.parametrize("change", ["issuer", "class", "date", "id", "future", "base", "source", "missing", "duplicate", "precedence", "financials"])
def test_bundle_refuses_wrong_identity_and_incomplete_dependencies(tmp_path, change):
    issue, docs, key = bundle(tmp_path)
    if change == "issuer": docs[key]["issuer"] = "Guarantor"
    elif change == "class": docs[key]["security_class"] = "subordinated"
    elif change == "date": docs[key]["edition_date"] = "2013-07-17"
    elif change == "id": docs[key]["identifiers"] = ["PTBEQKOM0019"]
    elif change == "future": docs[key]["edition_date"] = "2014-04-23"
    elif change == "base": docs[key]["base_id"] = "newest-base"
    elif change == "source": (tmp_path / docs[key]["original"]).write_bytes(b"changed")
    elif change == "missing": issue["documents"] = []
    elif change == "duplicate": issue["documents"] *= 2
    elif change == "precedence": issue["document_contract"]["precedence_reviewed"] = False
    else: issue["document_contract"]["unresolved_dependencies"] = ["incorporated financial report"]
    assert validate_bundle(issue, docs, tmp_path)["status"] == "UNRESOLVED"
    if change != "source":
        result = analyze_issue(issue, docs, tmp_path)
        assert result["answer"] is None and result["facts"]["coverage_complete"] is None


@pytest.mark.parametrize("pages,expected", [([""],"OCR_REQUIRED"),([ORDINARY,""],"PARTIAL_TEXT")])
def test_empty_text_is_explicit_and_blocks_negative(tmp_path, pages, expected):
    issue, docs, _ = fixture(tmp_path, pages)
    result = analyze_issue(issue, docs, tmp_path)
    assert result["answer"] is None
    assert result["extraction"][0]["status"] == expected
    assert any(expected in s for s in result["open_issues"])


def test_foreign_blank_page_does_not_invalidate_selected_text(tmp_path):
    issue, docs, _ = fixture(tmp_path, [ORDINARY,""], operative=[[1,1]])
    assert analyze_issue(issue, docs, tmp_path)["answer"] is False


def test_blank_declaration_requires_review_provenance():
    with pytest.raises(ValueError):
        extraction_coverage({"pages":[{"text":""}],"reviewed_blank_pages":[1]}, {})
