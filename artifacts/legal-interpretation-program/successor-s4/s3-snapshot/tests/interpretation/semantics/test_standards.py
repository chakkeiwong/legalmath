"""Behavioral challenges for the sufficient-implication and provenance boundary."""
from copy import deepcopy
import pytest
from legalmath.canonical import digest
from legalmath.interpretation.semantics.records import Interval
from legalmath.interpretation.semantics.standards import evaluate, verify, Standard
from scripts.legal_interpretation_s2_data import (
    packet, inventory, example_assessment, supplied, obligation_ledger)


@pytest.fixture
def setup():
    source = packet()
    cat, rules = inventory(source)
    return source, cat, {r.id: r for r in rules}, example_assessment()


def run(setup, name, changes=None, assessment=None):
    source, cat, rules, scope = setup
    rule = rules[name]
    evidence = supplied(rule, scope)
    if changes:
        evidence = changes(evidence)
    return evaluate((rule,), source, cat, assessment or scope, evidence)


def test_no_request_blocks_A_and_C_but_does_not_negate_duty_or_settle_B(setup):
    def absent(items):
        return tuple(e.model_copy(update={"positive":False}) if e.requirement_id=="p14-request" else e for e in items)
    for name in ("p14-A-demonstration", "fn5-C-demonstration"):
        result = run(setup, name, absent)["results"][0]
        assert result["status"] == "NOT_DERIVED"
        assert result["opposite_consequence"] == "NOT_ESTABLISHED"
        assert any(r["reason"]=="negative-antecedent" for r in result["reasons"])
    b = run(setup, "fn5-B-demonstration")["results"][0]
    assert b["status"] == "CONDITIONALLY_DERIVED"
    assert b["legal_correctness"] == "NOT_ESTABLISHED"
    a = run(setup, "p14-A-demonstration")["results"][0]
    c = run(setup, "fn5-C-demonstration")["results"][0]
    assert a["consequence"] != c["consequence"]


@pytest.mark.parametrize("name", ["p15-audit", "p16-opinion"])
def test_demonstration_request_does_not_satisfy_other_request(name, setup):
    def wrong_request(items):
        return tuple(e.model_copy(update={"requirement_id":"p14-request"})
            if e.requirement_id in ("p15-request", "p16-request") else e for e in items)
    assert run(setup, name, wrong_request)["results"][0]["status"] == "NOT_DERIVED"


def test_issuance_alone_cannot_supply_dealing_intention(setup):
    result = run(setup, "securities13-responsibility",
        lambda es: tuple(e for e in es if e.requirement_id!="dealing-advising-intent"))
    assert result["results"][0]["status"] == "NOT_DERIVED"
    assert any(r["premise"]=="dealing-advising-intent" for r in result["results"][0]["reasons"])


def test_general_outsourcing_does_not_supply_valuation_activity(setup):
    result = run(setup, "ut611c-valuation",
        lambda es: tuple(e for e in es if e.requirement_id!="valuation-outsourced"))
    assert result["results"][0]["status"] == "NOT_DERIVED"


def test_product_provider_role_does_not_supply_register_keeper_role(setup):
    result = run(setup, "ut68-register",
        lambda es: tuple(e.model_copy(update={"requirement_id":"product-provider"})
            if e.requirement_id=="register-actor" else e for e in es))
    assert result["results"][0]["status"] == "NOT_DERIVED"


def test_source_assertions_cannot_satisfy_interpretive_or_factual_premises(setup):
    result = run(setup, "p10-responsibility",
        lambda es: tuple(e.model_copy(update={"kind":"source-assertion"}) for e in es))
    assert result["results"][0]["status"] == "NOT_DERIVED"
    assert all(p["state"]=="unknown" for p in result["results"][0]["premises"])


def test_conflicting_applicability_is_retained_without_explosion(setup):
    result = run(setup, "p10-responsibility",
        lambda es: es+(es[0].model_copy(update={"id":"contrary","positive":False}),))
    row = result["results"][0]
    assert row["status"] == "NOT_DERIVED"
    assert row["premises"][0]["state"] == "conflict"
    assert row["opposite_consequence"] == "NOT_ESTABLISHED"


@pytest.mark.parametrize("change,reason", [
    ({"provider":"different"}, "different-identity"),
    ({"jurisdiction":"different"}, "different-identity"),
    ({"known_on":"2026-05-02"}, "learned-after-cutoff"),
    ({"known_on":None}, "unknown-knowledge-date"),
])
def test_identity_and_knowledge_scope(setup, change, reason):
    result = run(setup, "p10-responsibility", lambda es:tuple(e.model_copy(update=change) for e in es))
    assert result["results"][0]["status"] == "NOT_DERIVED"
    assert reason in result["results"][0]["premises"][0]["excluded"][0]["reasons"]


def test_single_event_or_overlapping_period_cannot_cover_full_assessment(setup):
    def partial(es):
        return tuple(e.model_copy(update={"scope":e.scope.model_copy(update={
            "interval":Interval(start="2026-04-25",end="2026-04-30")})}) for e in es)
    result=run(setup, "p10-responsibility", partial)
    assert result["results"][0]["status"] == "NOT_DERIVED"
    assert "incomplete-period-coverage" in result["results"][0]["premises"][0]["excluded"][0]["reasons"]


def test_unknown_assessment_cannot_be_dated_by_source_publication(setup):
    result=run(setup, "p10-responsibility", assessment=example_assessment(False))
    assert result["results"][0]["status"] == "NOT_DERIVED"


def test_source_change_invalidates_even_unchanged_quoted_unit(setup):
    source, cat, rules, scope = setup
    rule=rules["p10-responsibility"];evidence=supplied(rule,scope)
    changed=deepcopy(source)
    changed["units"][-1]["text"] += " Subsequent amendment."
    with pytest.raises(Exception):
        evaluate((rule,), changed, cat, scope, evidence)


def test_edition_or_speaker_role_change_cannot_reuse_rule(setup):
    source,cat,rules,scope=setup;rule=rules["p10-responsibility"]
    for field,value in (("edition","different"),("role","majority")):
        changed=deepcopy(cat);changed[rule.sources[0].unit_id][field]=value
        with pytest.raises(ValueError,match="edition or role"):
            evaluate((rule,),source,changed,scope,supplied(rule,scope))


def test_receipt_replay_binds_evidence_assessment_and_consequence(setup):
    source,cat,rules,scope=setup;rule=rules["p10-responsibility"];es=supplied(rule,scope)
    receipt=evaluate((rule,),source,cat,scope,es)
    assert verify(receipt,(rule,),source,cat,scope,es)["status"]=="PASS"
    corrupted=deepcopy(receipt);corrupted["results"][0]["consequence"]="Provider is legally compliant."
    with pytest.raises(ValueError,match="recomputation"):
        verify(corrupted,(rule,),source,cat,scope,es)
    with pytest.raises(ValueError,match="recomputation"):
        verify(receipt,(rule,),source,cat,scope,es[:-1])
    shifted=scope.model_copy(update={"scope":scope.scope.model_copy(update={
        "interval":Interval(start="2026-04-21",end="2026-04-30")})})
    with pytest.raises(ValueError,match="recomputation"):
        verify(receipt,(rule,),source,cat,shifted,es)


def test_shared_premise_identity_cannot_change_meaning(setup):
    source,cat,rules,scope=setup;a=rules["p10-responsibility"];b=rules["p11-records"]
    altered=b.model_copy(update={"requirements":(b.requirements[0].model_copy(
        update={"statement":"An unrelated source applies."}),)+b.requirements[1:]})
    with pytest.raises(ValueError,match="incompatible definitions"):
        evaluate((a,altered),source,cat,scope,())


def test_json_roundtrip_preserves_all_original_ids_roles_and_missing_premises(setup):
    source,cat,rules,scope=setup
    ledger=obligation_ledger(source,cat,list(rules.values()))
    assert len(ledger)==len({r["obligation_id"] for r in ledger})==46
    assert all(r["original_hash"]==digest(r["original"]) for r in ledger)
    assert all(r["role_responses"] and r["source_assertions"] and r["missing_premises"] for r in ledger)
    assert all(r["status"]=="OPEN_QUALIFIED" and r["closure_evidence"] is None for r in ledger)
    for rule in rules.values():
        assert Standard.model_validate_json(rule.model_dump_json())==rule

def test_case_records_use_original_court_bytes_and_retain_source_tension():
    import json
    from scripts.legal_interpretation_s2_cases import build
    records = build()
    assert len(records["cases"]) == 2
    assert records["unresolved_text_tension"]["status"] == "OPEN_SOURCE_INTERPRETATION"
    for case in records["cases"]:
        assert case["raw_source"]["url"].startswith("https://legalref.judiciary.hk/")
        assert case["source_check"]["status"] == "SOURCE_REFERENCES_CHECKED"
        assert all(a["assessment"]["status"] == "UNRESOLVED" for a in case["authority"])
    assert json.loads(json.dumps(records))["legal_force_for_26EC22"] == "NOT_ESTABLISHED"


def test_master_serialization_roundtrip_is_replayable():
    import json
    from scripts.run_legal_interpretation_master import build_outputs
    result = build_outputs()
    assert json.loads(json.dumps(result)) == result
    assert len(result["standards.json"]) == 14
    assert len(result["development-cases.json"]) == 112
    assert all(r["status"] == "NOT_DERIVED" for r in result["retained-evaluation.json"]["results"])

