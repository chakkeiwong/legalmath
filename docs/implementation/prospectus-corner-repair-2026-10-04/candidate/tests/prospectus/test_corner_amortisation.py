
"""Paired real amortisation and unpaid-loss controls."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
from legalmath.prospectus import loss_absorption_reader as reader
from legalmath.prospectus.reader_scope import paid_amortisation

DATA=Path(__file__).parent/"fixtures/corner-mizuho.json"
ROWS=json.loads(DATA.read_text())["witnesses"]

@pytest.mark.parametrize("row", ROWS, ids=lambda r:r["id"])
def test_retained_paid_amortisation(row):
    assert paid_amortisation(row["quote"])
    features=reader.clause_features(row["quote"])
    assert any(f["disposition"]=="principal_repaid_in_partial_redemption" for f in features)
    assert not any(f["kind"]=="principal_write_down" and f["disposition"]=="applicable" for f in features)

@pytest.mark.parametrize("row", ROWS, ids=lambda r:r["id"])
def test_payment_words_cannot_hide_separate_loss(row):
    text=row["quote"]+" The unpaid principal of the Notes shall be cancelled."
    assert not paid_amortisation(text)
    assert any(f["kind"]=="principal_write_down" for f in reader.clause_features(text))

@pytest.mark.parametrize("text", [
    "Without payment of the relevant Amortization Amount the outstanding principal amount of such Note shall be reduced by the same proportion which the relevant Amortization Amount bears to the aggregate of all Amortization Amounts.",
    "Each Note outstanding on an Amortization Date shall not be partially redeemed on such Amortization Date at the specified Amortization Amount and the outstanding principal amount of such Note shall be reduced accordingly.",
    "The Issuer discusses amortization. On a Trigger Event the principal amount of the Notes shall be written down.",
])
def test_missing_payment_relation_cannot_use_paid_exclusion(text):
    assert not paid_amortisation(text)
    assert not any(f["disposition"]=="principal_repaid_in_partial_redemption" for f in reader.clause_features(text))
