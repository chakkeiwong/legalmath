from copy import deepcopy
from pathlib import Path

import pytest

from legalmath.prospectus import instrument_cases as cases, instrument_investigation as engine
from legalmath.prospectus import instrument_checks as checks

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture
def fixture(tmp_path):
    return cases.request(ROOT,tmp_path/"bank")


def test_real_source_populates_conditional_scope_without_client_or_clearance(fixture):
    request,store=fixture
    report=engine.investigate(request,store,ROOT)
    assert report["source_dependent_product_premises"] == 5
    assert report["calculations"]["scope"]["in_scope_product"]["value"] is True
    assert report["observations"]["professional_investor"]["status"] == "UNKNOWN"
    assert report["instrument_event"]["status"] == "UNKNOWN"
    assert len(report["inventory"]) == 14 and not report["may_execute_transaction"]
    assert report["observations"]["debt_legal_form"]["truth_of_assertion"] == "SOURCE_DEPENDENT_PROPOSAL"
    assert report["joined"]["source_issues"]
    engine.revalidate(report,request,store,ROOT)


def test_pi_nonpi_and_conversion_scenarios_retain_all_bank_layers(fixture):
    request,store=fixture
    examples=cases.scenarios(store)
    for name in ("pi","non_pi"):
        r={**request,"scenario_sha256":store.put(examples[name])}
        report=engine.investigate(r,store,ROOT)
        assert report["calculations"]["restriction"]["pi_restriction_satisfied"]["value"] == (name=="pi")
        assert report["instrument_event"]["settlement"]["issuer_obligation_discharged"] is True
        assert report["scenario_kind"] == "HYPOTHETICAL"
        assert len(report["inventory"]) == 14 and not report["may_execute_transaction"]


@pytest.mark.parametrize("name",["missing_notice","missing_calendar","missing_higher_inventory","printed_formula_anomaly"])
def test_incomplete_events_do_not_discharge(fixture,name):
    request,store=fixture
    report=engine.investigate({**request,"scenario_sha256":store.put(cases.scenarios(store)[name])},store,ROOT)
    assert report["instrument_event"]["settlement"].get("issuer_obligation_discharged") is not True
    assert report["calculations"]["scope"]["in_scope_product"]["value"] is True
    assert len(report["inventory"]) == 14


def test_source_conflict_and_stale_scenario_cannot_be_hidden(fixture):
    request,store=fixture
    scenario=cases.scenarios(store)["non_pi"]
    r={**request,"scenario_sha256":store.put(scenario)}
    report=engine.investigate(r,store,ROOT)
    scenario["product_facts"]["professional_investor"]=True
    changed={**request,"scenario_sha256":store.put(scenario)}
    with pytest.raises(ValueError,match="changed"): engine.revalidate(report,changed,store,ROOT)
    scenario["product_facts"]["debt_legal_form"]=False
    conflict=engine.investigate({**request,"scenario_sha256":store.put(scenario)},store,ROOT)
    assert conflict["observations"]["debt_legal_form"]["status"] == "CONFLICT"
    assert not conflict["may_execute_transaction"]


def test_publication_restatement_and_issue_substitution_are_rejected(fixture):
    request,store=fixture
    scenario=cases.scenarios(store)["non_pi"]
    scenario["event"]["publication"]["cet1"]="50"
    with pytest.raises(ValueError,match="snapshot"):
        engine.investigate({**request,"scenario_sha256":store.put(scenario)},store,ROOT)
    changed=deepcopy(request)
    changed["joined_request"]["bank_request"]["context"]["instrument_id"]="different-issue"
    with pytest.raises(ValueError,match="another instrument"): engine.investigate(changed,store,ROOT)


def test_independent_equations_and_mutants(tmp_path):
    report=checks.prove(tmp_path/"proof")
    assert len(report["obligations"]) == 5
    assert {m["mutation"] for m in report["mutants"]} >= {"inclusive_threshold","omitted_higher_capital"}
