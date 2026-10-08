from fractions import Fraction as F
from itertools import product
import pytest
from legalmath.prospectus.semantics import (
    Contract, transition, distribution, possible_decision, SPI_FACTS, eligible,
    CLASS_FACTS, complex_bond, financial, threshold, duties,
)
from legalmath.prospectus.checks import generated_checks


def test_complete_declared_combinations():
    result = generated_checks()
    assert result["partial_spi_states"] == 2187
    assert result["contract_event_combinations"] == 1728


@pytest.mark.parametrize("missing", SPI_FACTS)
def test_unknown_and_conflict_cannot_create_permission(missing):
    facts = dict.fromkeys(SPI_FACTS, True)
    facts[missing] = None
    assert possible_decision(SPI_FACTS, facts, eligible)["decision"] == "UNDETERMINED"
    facts[missing] = "conflict"
    assert possible_decision(SPI_FACTS, facts, eligible)["decision"] == "CONFLICT"


def test_no_quality_labels_as_inputs():
    for label in ("expected", "human_verified", "reviewer", "ground_truth", "issuer_country"):
        with pytest.raises(ValueError):
            possible_decision(SPI_FACTS, {label: True}, eligible)


def test_refining_evidence_keeps_definite_answers():
    for values in product((None, False, True), repeat=5):
        facts = dict(zip(CLASS_FACTS, values))
        prior = possible_decision(CLASS_FACTS, facts, complex_bond)
        if prior["decision"] not in ("TRUE", "FALSE"):
            continue
        for key in prior["missing"]:
            for value in (True, False):
                after = possible_decision(CLASS_FACTS, {**facts, key: value}, complex_bond)
                assert after["decision"] == prior["decision"]


def test_dividend_loss_is_not_principal_loss():
    assert distribution(25, False, "1.1875") == {"principal": 25, "paid": 0, "arrears": 0}
    loss = transition(Contract("permanent_write_down", F(7, 100)), 25, 0, False)
    assert loss["debt_principal"] == 0
    conversion = transition(Contract("equity_conversion", F(7, 100), conversion_price=F(3, 2)), 25, 0, False)
    assert conversion["equity_units"] == F(50, 3)
    with pytest.raises(ValueError, match="arrears"):
        distribution(25, True, 1, cumulative=False, arrears=2)


def test_authorized_restoration_and_no_restore_on_permanent_loss():
    for mechanism in ("temporary_write_down", "permanent_write_down"):
        c = Contract(mechanism, F(7, 100), reduction=F(1, 3))
        result = transition(c, 100, 0, False, restore=1000, restore_authorized=True)
        assert result["debt_principal"] == (100 if mechanism.startswith("temporary") else F(200, 3))


@pytest.mark.parametrize("bad", [0.07, True, "0.07"])
def test_contract_rejects_implicit_numeric_coercion(bad):
    with pytest.raises(ValueError):
        Contract("permanent_write_down", bad)


def test_exact_financial_boundaries_and_designated_account_exception():
    assert not financial(3999999999, 7999999999)
    assert financial(4000000000, 0) and financial(0, 8000000000)
    assert not threshold(101, 100, False, False)
    assert threshold(101, 100, True, False)
    assert not threshold(101, 100, True, True)
    assert threshold(100, 100, False, True)
    with pytest.raises(ValueError):
        financial(4e9, 0)
    with pytest.raises(ValueError):
        threshold(F(1, 3), 100, False, False)


def test_retained_duties_and_information_condition():
    a = duties(False, True, True, False, False, True)
    assert a["explanation_required"] and not a["pdd_relief"]
    assert duties(False, True, True, False, True, True)["pdd_relief"]
    assert not duties(True, True, True, True, True, False)["pdd_relief"]
