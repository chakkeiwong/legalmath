"""The actual BES review wording must not support a false statutory audit."""
from copy import deepcopy
from pathlib import Path

import pytest

from legalmath.prospectus.successor import report_scope, service
from legalmath.prospectus.successor.contracts import digest
from test_report_scope import REVIEW, exact_span, products
from test_successor import request

# Exact retained pp172–173 text; source PDF hash:
# b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7.
TEXT = (Path(__file__).parent / "fixtures/bes_interim_review.txt").read_text()
UNKNOWN = {"status": "UNKNOWN", "reason": "Not established by this supplied reading"}


def fixture(tmp_path, text=TEXT):
    req = request(tmp_path, [text])
    req.pop("assembly")
    req.pop("scope")
    p1 = service.source_product(req, tmp_path)
    graph = p1["payload"]["graph"]
    retained = "\n".join(u["raw"] for u in graph["units"])
    req["source_report_readings"] = {
        "version": "source-report-readings.v1", "graph_sha256": digest(graph), "review": REVIEW,
        "reports": [{"id": "review", "document": "d",
            "source_sha256": req["bundle"]["documents"][0]["sha256"],
            "pages": [{"page": 1, "mode": "raw"}], "text_sha256": digest(retained.encode())}]}
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    selected = p2["payload"]["source_report_readings"]
    facts = {field: deepcopy(UNKNOWN) for field in report_scope.FACTS}
    quotes = {
        "identity": ["LIMITED REVIEW REPORT"],
        "subject": [retained.split("1.\n", 1)[1].split("\n2.\n", 1)[0]],
        "assurance_level": ["objective of obtaining a moderate\nlevel of assurance",
                            "objective of obtaining moderate assurance"],
        "criteria": [retained.split("b) ", 1)[1].split("\nc) ", 1)[0]],
        "conclusion": [retained.split("\n8.\n", 1)[1].split("\nLisbon,", 1)[0]],
        "purpose": [retained.split("\nScope\n", 1)[1].split("\nConclusion\n", 1)[0]],
        "report_date": ["Lisbon, 13 August 2010"],
    }
    codes = {"identity": "LIMITED_FINANCIAL_REVIEW",
             "subject": "INTERIM_CONSOLIDATED_FINANCIAL_INFORMATION",
             "assurance_level": "MODERATE", "conclusion": "NEGATIVE_ASSURANCE"}
    for field, passages in quotes.items():
        facts[field] = {"status": "SUPPLIED", "spans": [exact_span(retained, q) for q in passages],
                        **({"value": codes[field]} if field in codes else {})}
    scope = {"version": "source-report-scope.v1", "readings_sha256": digest(selected), "review": REVIEW,
             "reports": [{"id": "review", "reading_sha256": selected["reports"][0]["sha256"], "facts": facts}]}
    return p1, p2, scope, retained


def direct(p2, scope):
    return report_scope.explain(report_scope.admit(p2["payload"]["source_report_readings"], scope))[0]


def test_source_review_reaches_current_consumer_without_claiming_audit(tmp_path):
    p1, p2, scope, _ = fixture(tmp_path)
    baseline = service.consume(products(p1, p2), tmp_path, mode="current", include_artifacts=True)
    actual = service.consume(products(p1, p2, scope), tmp_path, mode="current", include_artifacts=True)
    report, = actual["source_reports"]
    assert report["status"] == "CONDITIONAL_SUPPLIED_READING"
    assert report["use_assessment"]["financial_interim_review"] == "SUPPLIED_SOURCE_SUPPORT"
    assert report["use_assessment"]["financial_statement_audit_opinion"] == "NOT_ESTABLISHED_BY_THIS_READING"
    assert report["use_assessment"]["limited_sustainability_assurance"] == "NOT_ESTABLISHED_BY_THIS_READING"
    assert report["facts"]["assurance_level"]["value"] == "MODERATE"
    assert "reasonable basis" in report["facts"]["purpose"]["spans"][0]["quote"]
    assert report["interim_review_context"]["normalized_closing_date"] == "2010-08-13"
    assert not report["interim_review_context"]["general_semantic_truth_established"]
    assert all(report["facts"][field]["status"] == "UNKNOWN" for field in report_scope.EXTERNAL)
    for key in ("questions", "dependencies", "assembly"):
        assert actual[key] == baseline[key]
    assert actual["mode"] == "ASSISTED" and not actual["independent_legal_acceptance"]


@pytest.mark.parametrize("category", [
    "STATUTORY_FINANCIAL_AUDIT", "LIMITED_SUSTAINABILITY_ASSURANCE", "COMMITTEE_REPORT"])
def test_mutually_consistent_false_codes_reject_even_in_v1(tmp_path, category):
    p1, p2, scope, _ = fixture(tmp_path)
    facts = scope["reports"][0]["facts"]
    facts["identity"]["value"] = category
    for field, value in report_scope.PROFILES[category].items():
        facts[field]["value"] = value
    if category == "COMMITTEE_REPORT":
        facts["assurance_level"] = deepcopy(UNKNOWN)
    with pytest.raises(ValueError, match="Source interim review contradicts"):
        service.interpretation_product(p1, p2, {"source_report_scope": scope})


@pytest.mark.parametrize("field", ["assurance_level", "conclusion"])
def test_unknown_identity_does_not_bypass_known_assurance_contradiction(tmp_path, field):
    _, p2, scope, _ = fixture(tmp_path)
    facts = scope["reports"][0]["facts"]
    facts["identity"] = deepcopy(UNKNOWN)
    facts[field]["value"] = "REASONABLE" if field == "assurance_level" else "AFFIRMATIVE_FINANCIAL_OPINION"
    with pytest.raises(ValueError, match="Source interim review contradicts"):
        direct(p2, scope)


@pytest.mark.parametrize("field,omission", [
    ("assurance_level", "moderate"), ("conclusion", "nothing"),
    ("conclusion", "not free"), ("conclusion", "and that is not"),
    ("criteria", "as required by the CVM"), ("criteria", "IAS 34"),
    ("subject", "six-months period ended 30 June 2010"),
    ("subject", "consolidated"), ("purpose", "substantive tests on material non current transactions."),
])
def test_exact_fragments_cannot_omit_decisive_language(tmp_path, field, omission):
    _, p2, scope, text = fixture(tmp_path)
    fact = scope["reports"][0]["facts"][field]
    original = next(s for s in fact["spans"] if omission in s["quote"])
    start = text.index(omission, original["start"], original["end"])
    fact["spans"].remove(original)
    for a, b in ((original["start"], start), (start + len(omission), original["end"])):
        if text[a:b].strip():
            fact["spans"].append({"start": a, "end": b, "quote": text[a:b]})
    report = direct(p2, scope)
    assert report["status"] == "INCOMPLETE_SOURCE_READING"
    assert field in report["unresolved_interim_review_fields"]
    assert report["use_assessment"]["financial_interim_review"] == "NOT_ESTABLISHED_BY_THIS_READING"


@pytest.mark.parametrize("mutation", ["reasonable_basis", "period_date", "both_dates", "unknown_date",
                                    "unknown_criteria", "unknown_identity", "unknown_assurance"])
def test_other_exact_passages_and_unknowns_withhold_support(tmp_path, mutation):
    _, p2, scope, text = fixture(tmp_path)
    facts = scope["reports"][0]["facts"]
    if mutation == "reasonable_basis":
        facts["assurance_level"]["spans"] = [exact_span(text, "a reasonable basis to issue our report")]
    elif mutation == "period_date":
        facts["report_date"]["spans"] = [exact_span(text, "30 June 2010")]
    elif mutation == "both_dates":
        facts["report_date"]["spans"].append(exact_span(text, "30 June 2010"))
    else:
        field = {"unknown_date": "report_date", "unknown_criteria": "criteria",
                 "unknown_identity": "identity", "unknown_assurance": "assurance_level"}[mutation]
        facts[field] = deepcopy(UNKNOWN)
    assert direct(p2, scope)["status"] == "INCOMPLETE_SOURCE_READING"


@pytest.mark.parametrize("mutation", ["incidental_heading", "missing_scope", "missing_conclusion",
                                    "missing_criteria", "extra_conclusion", "missing_scope_body",
                                    "extra_scope_qualification"])
def test_unrecognized_sources_never_pass_new_category_by_absence_of_trigger(tmp_path, mutation):
    _, p2, scope, _ = fixture(tmp_path)
    # Bind a changed source reading and reconstruct every supplied span. These
    # are explicit source variants, not undetected mutations of a sealed source.
    selected = deepcopy(p2["payload"]["source_report_readings"])
    row = selected["reports"][0]
    old = row["text"]
    text = {
        "incidental_heading": "Commentary quoting a report follows.\n" + old,
        "missing_scope": old.replace("\nScope\n", "\nProcedures\n"),
        "missing_conclusion": old.replace("\nConclusion\n", "\nOther text\n"),
        "missing_criteria": old.replace("as required by the CVM;", "under other criteria;"),
        "extra_conclusion": old.replace("\nLisbon, 13", "\nExcept for an unresolved qualification.\nLisbon, 13"),
        "missing_scope_body": old.replace(
            old.split("misstatements. Our work", 1)[1].split("\nConclusion\n", 1)[0], ""),
        "extra_scope_qualification": old.replace("\nConclusion\n", "\nThis scope excludes some statements.\nConclusion\n"),
    }[mutation]
    row["text"] = text
    row["characters"] = [{"output": i, "source_offset": i, "character": c, "unit": "explicit-variant"}
                         for i, c in enumerate(text)]
    row["sha256"] = digest({k: v for k, v in row.items() if k != "sha256"})
    for fact in scope["reports"][0]["facts"].values():
        if fact["status"] == "SUPPLIED":
            passages = [s["quote"] for s in fact["spans"]]
            if any(q not in text for q in passages):
                # Exact whole-source spans make the check harder: coverage alone
                # cannot certify an unsupported source structure.
                passages = [text]
            fact["spans"] = [exact_span(text, q) for q in passages]
    scope["readings_sha256"] = digest(selected)
    scope["reports"][0]["reading_sha256"] = row["sha256"]
    report, = report_scope.explain(report_scope.admit(selected, scope))
    assert report["status"] == "INCOMPLETE_SOURCE_READING"
    assert report["interim_review_context"]["status"] == "UNRECOGNIZED_OR_INCOMPLETE_SOURCE_STRUCTURE"


@pytest.mark.parametrize("mutation", ["stale_edition", "changed_quote"])
def test_new_category_does_not_weaken_source_integrity(tmp_path, mutation):
    p1, p2, scope, _ = fixture(tmp_path)
    if mutation == "stale_edition":
        scope["reports"][0]["reading_sha256"] = "0" * 64
    else:
        scope["reports"][0]["facts"]["conclusion"]["spans"][0]["quote"] += " fabricated"
    with pytest.raises(ValueError):
        service.interpretation_product(p1, p2, {"source_report_scope": scope})
