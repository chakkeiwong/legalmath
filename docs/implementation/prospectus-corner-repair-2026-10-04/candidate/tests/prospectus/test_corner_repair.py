"""Source-based cancellation conditions and adversarial payment controls."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
import legalmath.prospectus.loss_absorption_reader as reader
from legalmath.prospectus.cancellation import cancellation_features, evaluate_cancellation, valid_cancellation_witness
from tests.prospectus.test_loss_absorption import fixture, ORDINARY

ROOT = Path(__file__).resolve().parents[2]
assert reader.__file__.startswith(str(ROOT / "src")), reader.__file__


def source(key, pages):
    values = json.loads((ROOT / "docs/prospectus/corner-cases-2026-10-04/sources" /
                         key / "pages.json").read_text())["pages"]
    return [values[n-1]["text"] for n in pages]


def case(key, pages, marker):
    text, _ = reader.joined({"pages": [{"text": s} for s in source(key, pages)]})
    return next(text[a:b] for a,b in reader.segments(text) if marker in text[a:b])


CLAUSES = [
    ("final", case("jur-more-hypo-1314069", [140], "If the Issuer has insufficient"),
     {"insufficient_funds", "at_final_maturity"}, {"improper_withholding_or_refusal"}),
    ("exhaustion", case("jur-more-hypo-1314069", [144,145], "the Noteholders shall have no further claim"),
     {"servicer_certificate", "no_further_recoveries", "representative_notice"}, set()),
    ("later", case("jur-more-hypo-843665", [121], "If the Notes cannot be redeemed in full"),
     {"insufficient_funds", "at_cancellation_date"}, {"issuer_gross_negligence", "issuer_wilful_misconduct"})
]


@pytest.mark.parametrize("name,clause,requirements,exceptions", CLAUSES)
def test_real_conditions_and_exceptions(name, clause, requirements, exceptions, tmp_path):
    features = reader.clause_features(clause)
    assert not any(f["disposition"] == "repurchase_or_redemption_cancellation" for f in features)
    loss = next(f for f in features if f["kind"] == "principal_write_down")
    w = loss["semantic_witness"]
    assert {s["kind"] for s in w["requirements"]} == requirements
    assert {s["kind"] for s in w["exceptions"]} == exceptions
    for s in w["requirements"] + w["exceptions"]:
        assert clause[s["start"]:s["end"]] == s["quote"]
    facts = {**{k: True for k in requirements}, **{k: False for k in exceptions},
             "unpaid_principal": True}
    assert evaluate_cancellation(w, facts) is True
    for key in requirements | exceptions | {"unpaid_principal"}:
        assert evaluate_cancellation(w, {**facts, key: not facts[key]}) is False
        assert evaluate_cancellation(w, {**facts, key: None}) is None
    issue, docs, _ = fixture(tmp_path, [ORDINARY + " " + clause])
    result = reader.analyze_issue(issue, docs, tmp_path)
    assert result["facts"]["principal_write_down"] is True
    assert result["certified_legal_answer"] is None


@pytest.mark.parametrize("name,clause,requirements,exceptions", CLAUSES)
def test_qualifier_tamper_and_missing_condition(name, clause, requirements, exceptions):
    f = next(f for f in cancellation_features(clause) if "semantic_witness" in f)
    item = {**f, "quote": clause}
    assert valid_cancellation_witness(item)
    damaged = deepcopy(item)
    if damaged["semantic_witness"]["exceptions"]:
        damaged["semantic_witness"]["exceptions"].pop()
    else:
        damaged["semantic_witness"]["requirements"].pop()
    assert not valid_cancellation_witness(damaged)
    with pytest.raises(ValueError):
        evaluate_cancellation(damaged["semantic_witness"], {"unpaid_principal": True})


@pytest.mark.parametrize("clause", [
    "The Notes purchased or redeemed shall be cancelled.",
    "The Notes have been repaid in full and shall be cancelled.",
    "The Notes shall be cancelled after delivery of the Conversion Shares to holders.",
    "The principal amount is reduced by the cash instalment actually paid.",
    "Unpaid interest shall be cancelled.",
    "The unpaid principal shall not be cancelled.",
])
def test_payment_interest_and_negation_controls(clause, tmp_path):
    issue, docs, _ = fixture(tmp_path, [ORDINARY + " " + clause])
    result = reader.analyze_issue(issue, docs, tmp_path)
    assert result["facts"]["principal_write_down"] is not True


def test_remaining_unpaid_balance_is_distinct_from_paid_amount():
    clause = "The repaid Notes are cancelled; the unpaid principal of the Notes shall be cancelled."
    features = reader.clause_features(clause)
    assert any(f["kind"] == "principal_write_down" for f in features)
    assert not any(f["disposition"] == "repurchase_or_redemption_cancellation" for f in features)


def test_missing_certificate_or_notice_blocks_complete_reading():
    clause = CLAUSES[1][1].replace("the Representative of the Noteholders has given notice",
                                  "the Representative of the Noteholders may consider giving notice")
    features = reader.clause_features(clause)
    assert not any(f["kind"] == "principal_write_down" and f["disposition"] == "applicable" for f in features)
    assert any(f["disposition"].startswith("unresolved") for f in features)


def test_cross_page_condition_keeps_certificate_and_notice(tmp_path):
    pages = source("jur-more-hypo-1314069", [144,145])
    issue, docs, _ = fixture(tmp_path, [ORDINARY + " " + pages[0], pages[1]])
    result = reader.analyze_issue(issue, docs, tmp_path)
    item = next(e for e in result["evidence"] if e.get("semantic_witness", {}).get("construction") == "certified_exhaustion")
    assert item["page"] == 1 and item["end_page"] == 2
    assert "if the Servicer has certified" in item["quote"]
    assert "has given notice" in item["quote"]
