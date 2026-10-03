"""Adversarial full-reader cases for the audited successor, not legal labels."""
import pytest

from legalmath.prospectus.loss_absorption_reader import analyze_issue
from tests.prospectus.test_loss_absorption import fixture, ORDINARY


PARTIAL = (
    "In the case of a partial redemption of, or a partial exercise of the Issuer’s option in respect of, "
    "Dematerialised Notes, the redemption will be effected by reducing the nominal amount of all such "
    "Dematerialised Notes in a Series in proportion to the aggregate nominal amount redeemed, subject "
    "to compliance with any other applicable laws and requirements of the Regulated Market on which "
    "the Notes are listed and admitted to trading.")
FLOOR = (
    "In no event, the outstanding nominal amount of each Note following such reduction shall be below "
    "any amount which would prevent the Issuer from choosing its home Member State "
    "(as such term is defined in the Prospectus Regulation).")
INTEREST = (
    "Any interest not paid on an Optional Interest Payment Date shall, so long as the same remains "
    "unpaid, constitute “ Arrears of Interest”, which term shall include interest on such unpaid "
    "interest as referred to below, except if the relevant Final Terms specify that any interest "
    "not paid on an Optional Interest Payment Date shall be forfeited and accordingly not due or "
    "payable by the Issuer any longer.")
HEADER = "Example issuer. Example senior notes. The Notes are unsecured obligations. "


@pytest.mark.parametrize("clause", [INTEREST, PARTIAL, PARTIAL + " " + FLOOR,
    PARTIAL.replace("will be effected by", "will be effected, by").replace(
        "requirements of the Regulated Market on which the Notes are listed and admitted to trading",
        "Regulated Market or stock exchange requirements") + " " + FLOOR])
def test_cash_redeemed_principal_and_interest_forfeiture_are_distinct_from_loss(tmp_path, clause):
    issue, docs, _ = fixture(tmp_path, [ORDINARY + " " + clause])
    row = analyze_issue(issue, docs, tmp_path)
    assert row["answer"] is False
    assert not [e for e in row["evidence"] if e["disposition"].startswith("unresolved")]


@pytest.mark.parametrize("ordinary", [
    "The Notes purchased or redeemed shall be cancelled",
    "Holders may approve amendments by Extraordinary Resolution",
    "Interest on the Notes may be cancelled at the Issuer's discretion",
])
def test_ordinary_clause_cannot_hide_separate_principal_loss(tmp_path, ordinary):
    clause = ordinary + ", and the principal amount of the Notes shall be permanently reduced upon a Solvency Event."
    issue, docs, _ = fixture(tmp_path, [ORDINARY + " " + clause])
    row = analyze_issue(issue, docs, tmp_path)
    assert row["facts"]["principal_write_down"] is True
    assert row["answer"] is True


def test_ordinary_clause_cannot_hide_unsupported_principal_loss(tmp_path):
    clause = "The Notes purchased or redeemed shall be cancelled, and holders shall surrender all rights to repayment of principal."
    issue, docs, _ = fixture(tmp_path, [ORDINARY + " " + clause])
    assert analyze_issue(issue, docs, tmp_path)["answer"] is not False


@pytest.mark.parametrize("clause", [
    PARTIAL.replace("amount redeemed", "amount forgiven"),
    INTEREST.replace("Any interest", "Any principal").replace("any interest", "any principal"),
    FLOOR,
    PARTIAL + " An unrelated condition intervenes. " + FLOOR,
    PARTIAL + " However, the principal amount of the Notes shall be permanently written down upon a Trigger Event.",
])
def test_redemption_exclusion_requires_its_exact_relation_and_antecedent(tmp_path, clause):
    issue, docs, _ = fixture(tmp_path, [ORDINARY + " " + clause])
    assert analyze_issue(issue, docs, tmp_path)["answer"] is not False


def test_context_cannot_cross_a_declared_section_boundary(tmp_path):
    issue, docs, _ = fixture(tmp_path, [HEADER + PARTIAL, ORDINARY + " " + FLOOR], operative=[[2, 2]])
    assert analyze_issue(issue, docs, tmp_path)["answer"] is not False


@pytest.mark.parametrize("clause", [
    "The Notes will not be redeemed at maturity at 100% of their principal amount.",
    "The Notes shall never be repaid at 100% of principal.",
    "Redemption of the Notes will not be at 100% of principal.",
])
def test_negated_par_repayment_is_not_an_affirmative_cash_witness(tmp_path, clause):
    issue, docs, _ = fixture(tmp_path, [HEADER + clause])
    row = analyze_issue(issue, docs, tmp_path)
    assert not any(e["kind"] == "cash_repayment" and e["disposition"] == "applicable" for e in row["evidence"])
    assert row["answer"] is None


@pytest.mark.parametrize("ranges", [[[1, 0]], [[1, 3]], [[True, 1]], [[1, 1], [1, 1]], []])
def test_invalid_scope_cannot_silently_omit_loss(tmp_path, ranges):
    issue, docs, _ = fixture(tmp_path, [ORDINARY, "The Notes shall be written down upon a Trigger Event."], operative=ranges)
    row = analyze_issue(issue, docs, tmp_path)
    assert row["answer"] is None
    assert any("scope" in x.lower() for x in row["open_issues"])


def test_overlapping_shelf_and_operative_scope_is_invalid(tmp_path):
    issue, docs, _ = fixture(tmp_path, [ORDINARY], operative=[[1, 1]])
    issue["documents"][0]["shelf_pages"] = [[1, 1]]
    row = analyze_issue(issue, docs, tmp_path)
    assert row["answer"] is None
    assert any("scope" in x.lower() for x in row["open_issues"])


def test_monetary_field_must_be_fully_inside_the_selected_scope(tmp_path):
    issue, docs, _ = fixture(tmp_path, [HEADER + "Final Redemption Amount of each Note EUR 1,000 per Note of",
        "EUR 1,000 Specified Denomination"], operative=[[1, 1]])
    assert analyze_issue(issue, docs, tmp_path)["answer"] is None


@pytest.mark.parametrize("clause", [
    "If all holders consent to the amendment by Extraordinary Resolution, the Notes purchased or redeemed shall be cancelled, "
    "and the principal amount of the Notes shall be reduced upon a Solvency Event.",
    "The Notes purchased or redeemed shall be cancelled, and the principal amount of the Notes shall be reduced "
    "by the amount repaid in cash.",
])
def test_coordination_does_not_detach_consent_or_turn_cash_payment_into_loss(tmp_path, clause):
    issue, docs, _ = fixture(tmp_path, [ORDINARY + " " + clause])
    row = analyze_issue(issue, docs, tmp_path)
    assert row["answer"] is not True



def test_monetary_relation_cannot_skip_an_explicit_other_series_binding(tmp_path):
    title = "Example Series A Notes"
    issue, docs, _ = fixture(tmp_path, ["Example issuer. " + title + ". The Notes are unsecured obligations. "
        "Calculation Amount: EUR 1,000. These fields apply to Series B Notes. "
        "Final Redemption Amount: EUR 1,000 per Calculation Amount."], title=title)
    assert analyze_issue(issue, docs, tmp_path)["answer"] is None


@pytest.mark.parametrize("clause", [
    "Forfeiture shall not absolve a previous member for amounts payable by him/her (which may continue to accrue interest).",
    "If a member fails to pay in full any call or instalment of a call on or before the due date for payment, then, following notice by the directors requiring payment of the unpaid amount with any accrued interest and any expenses incurred, such share may be forfeited by a resolution of the directors to that effect (including all dividends declared in respect of the forfeited share and not actually paid before such forfeiture).",
    "A member whose shares have been forfeited will cease to be a member in respect of the shares, but will, notwithstanding the forfeiture, remain liable to pay to LBG all monies which at the date of forfeiture were presently payable together with interest.",
    "Interest accrues on the Notes that will be forfeited upon an Event of Default."
])
def test_incidental_interest_cannot_exempt_share_or_note_forfeiture(tmp_path, clause):
    issue, docs, _ = fixture(tmp_path, [ORDINARY + " " + clause])
    row = analyze_issue(issue, docs, tmp_path)
    assert not any(e["quote"] == clause and e["disposition"] == "distribution_only" for e in row["evidence"])
    assert row["answer"] is None
