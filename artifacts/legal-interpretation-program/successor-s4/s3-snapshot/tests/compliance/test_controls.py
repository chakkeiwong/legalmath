"""Conditional specifications and adversarial checks; no human quality labels."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from fractions import Fraction
import hashlib
from itertools import product

import pytest

from legalmath.compliance import (
    CMIC_FACTS, Context, Finding, Layer, Requirement, SourceRef, Status, assess,
    binding, blocked_ownership_closure, cmic_check, us_entity_under_586,
)


TIME = datetime(2026, 9, 29, tzinfo=timezone.utc)


@pytest.fixture
def example(tmp_path):
    source = tmp_path / "conditional-specification.txt"
    source.write_text("Synthetic premises, not a bank approval or legal source.")
    ref = SourceRef(source.name, hashlib.sha256(source.read_bytes()).hexdigest())
    context = Context("synthetic-security", "ordinary_bond", "synthetic-client",
                      "synthetic-US-bank", "HK-branch", "custody", "buy", TIME, TIME,
                      "a" * 64, "b" * 64, "c" * 64)
    requirements = tuple(Requirement(layer.name.lower(), "v1", layer) for layer in Layer)
    findings = tuple(Finding(r.rule_id, Status.SATISFIED, binding(context, requirements),
                             "Conditional engineering premise", (ref,), TIME - timedelta(days=1),
                             TIME + timedelta(days=1), TIME) for r in requirements)
    return tmp_path, context, requirements, findings


def run(example, findings=None, context=None, requirements=None):
    root, ctx, reqs, original = example
    return assess(context or ctx, requirements or reqs,
                  original if findings is None else findings, evidence_root=root)


def test_all_layer_combinations_against_set_specification(example):
    # Independent set specification: permission iff every required set contains
    # a satisfied member, no forbidden member and no unknown member.
    for states in product((Status.SATISFIED, Status.PROHIBITED, Status.UNKNOWN), repeat=7):
        result = run(example, tuple(replace(f, status=s) for f, s in zip(example[3], states)))
        satisfied = {i for i, s in enumerate(states) if s == Status.SATISFIED}
        assert result["may_proceed_under_declared_scope"] == (satisfied == set(range(7)))
        assert len(result["prohibitions"]) == states.count(Status.PROHIBITED)
        assert len(result["unresolved"]) == states.count(Status.UNKNOWN)
        assert result["complete_legal_compliance"] == "NOT_ESTABLISHED"


@pytest.mark.parametrize("layer", list(Layer))
def test_missing_or_conflicting_layer_cannot_pass(example, layer):
    original = example[3]
    missing = tuple(f for f in original if f.rule_id != layer.name.lower())
    assert run(example, missing)["outcome"] == "UNDETERMINED"
    selected = next(f for f in original if f.rule_id == layer.name.lower())
    conflict = run(example, (*original, replace(selected, status=Status.PROHIBITED)))
    assert conflict["outcome"] == "DO_NOT_PROCEED"
    assert conflict["unresolved"]
    assert conflict["duties"] == []  # A trade prohibition does not imply a freeze.


def test_policy_failure_and_legal_duties_are_distinct(example):
    original = list(example[3])
    policy = next(i for i, f in enumerate(original) if f.rule_id == "policy")
    original[policy] = replace(original[policy], status=Status.UNSATISFIED)
    report = run(example, original)
    assert report["outcome"] == "REQUIREMENTS_NOT_MET"
    assert report["prohibitions"] == []
    sanctions = next(i for i, f in enumerate(original) if f.rule_id == "sanctions")
    original[sanctions] = replace(original[sanctions], status=Status.PROHIBITED,
                                  duties=("specified blocking/reporting duty",))
    report = run(example, original)
    assert report["outcome"] == "DO_NOT_PROCEED"
    assert len(report["duties"]) == 1
    assert report["unmet_requirements"] == ["policy"]


@pytest.mark.parametrize("field,value", [
    ("booking_entity_id", "different-entity"), ("client_id", "different-client"),
    ("establishment_id", "different-branch"), ("action", "sell"),
    ("service", "principal_dealing"), ("instrument_id", "different-security"),
    ("instrument_kind", "equity"), ("facts_sha256", "d" * 64),
    ("route_sha256", "e" * 64), ("policy_sha256", "f" * 64),
    ("effective_at", TIME + timedelta(seconds=1)), ("known_at", TIME + timedelta(seconds=1)),
])
def test_context_change_invalidates_all_cached_findings(example, field, value):
    changed = replace(example[1], **{field: value})
    result = run(example, context=changed)
    assert result["outcome"] == "UNDETERMINED"
    assert len(result["unresolved"]) == 7


def test_evidence_interval_is_half_open_and_knowledge_cannot_travel_back(example):
    for change in ({"valid_until": TIME}, {"valid_from": TIME + timedelta(seconds=1)},
                   {"known_from": TIME + timedelta(seconds=1)}):
        findings = (replace(example[3][0], **change), *example[3][1:])
        assert run(example, findings)["outcome"] == "UNDETERMINED"
    findings = tuple(replace(f, valid_from=TIME) for f in example[3])
    assert run(example, findings)["may_proceed_under_declared_scope"]


def test_source_mutation_prevents_reuse(example):
    (example[0] / example[3][0].sources[0].path).write_text("Changed evidence")
    result = run(example)
    assert result["outcome"] == "UNDETERMINED"
    assert all("source bytes changed" in reason for reason in result["unresolved"])


def test_requirement_version_inventory_and_layer_coverage(example):
    root, ctx, reqs, findings = example
    changed = (replace(reqs[0], version="v2"), *reqs[1:])
    assert run(example, requirements=changed)["outcome"] == "UNDETERMINED"
    short = reqs[:-1]
    current = tuple(replace(f, binding=binding(ctx, short)) for f in findings[:-1])
    report = assess(ctx, short, current, evidence_root=root)
    assert report["outcome"] == "UNDETERMINED"
    assert any("missing layer" in issue for issue in report["unresolved"])
    with pytest.raises(ValueError):
        binding(ctx, (reqs[0], reqs[0]))
    with pytest.raises(ValueError):
        assess(ctx, short, findings, evidence_root=root)


def test_not_applicable_requires_evidence_and_does_not_bypass_other_layers(example):
    with pytest.raises(ValueError):
        replace(example[3][0], status=Status.NOT_APPLICABLE, sources=())
    findings = (replace(example[3][0], status=Status.NOT_APPLICABLE), *example[3][1:])
    assert run(example, findings)["may_proceed_under_declared_scope"]
    assert not run(example, findings[:-1])["may_proceed_under_declared_scope"]


def test_validation_and_archive_escape(example):
    with pytest.raises(ValueError):
        replace(example[1], effective_at=TIME.replace(tzinfo=None))
    with pytest.raises(ValueError):
        replace(example[1], facts_sha256="mutable-database-row")
    with pytest.raises(ValueError):
        replace(example[3][0], valid_until=TIME - timedelta(days=1))
    with pytest.raises(ValueError):
        replace(example[3][0], status="SATISFIED")
    with pytest.raises(ValueError):
        SourceRef("../outside", "a" * 64).matches(example[0])


def test_branch_subsidiary_and_us_presence_scope():
    assert us_entity_under_586(organized_under_us_law=True, present_in_us=False) is True
    assert us_entity_under_586(organized_under_us_law=False, present_in_us=False) is False
    assert us_entity_under_586(organized_under_us_law=False, present_in_us=True) is True
    assert us_entity_under_586(organized_under_us_law=None, present_in_us=False) is None
    with pytest.raises(ValueError):
        us_entity_under_586(organized_under_us_law="US bank", present_in_us=False)


def cmic_facts(**updates):
    return dict(dict.fromkeys(CMIC_FACTS, False), designated_issuer=True,
                covered_security=True, restriction_in_force=True,
                actor_us_person=True, otherwise_permissible=True, **updates)


def test_cmic_us_bank_support_is_not_principal_ownership():
    facts = cmic_facts()
    assert cmic_check(facts, action="buy", capacity="principal")["result"] == "FALSE"
    assert cmic_check(facts, action="buy", capacity="specified_support")["result"] == "TRUE"
    facts["ultimate_party_us_person"] = True
    assert cmic_check(facts, action="buy", capacity="specified_support")["result"] == "FALSE"


def test_cmic_non_us_principal_does_not_clear_a_prohibited_us_counterparty_trade():
    facts = cmic_facts()
    facts.update(actor_us_person=False, ultimate_party_us_person=True)
    for action in ("buy", "sell"):
        assert cmic_check(facts, action=action, capacity="principal")["result"] == "FALSE"


def test_cmic_holding_divestment_license_and_other_illegality():
    facts = cmic_facts()
    assert cmic_check(facts, action="hold", capacity="principal")["result"] == "TRUE"
    assert cmic_check(facts, action="sell", capacity="principal")["result"] == "FALSE"
    facts.update(solely_divestment=True, divestment_window_open=True)
    assert cmic_check(facts, action="sell", capacity="principal")["result"] == "TRUE"
    facts["divestment_window_open"] = False
    assert cmic_check(facts, action="sell", capacity="principal")["result"] == "FALSE"
    facts["applicable_ofac_authorization"] = True
    assert cmic_check(facts, action="buy", capacity="principal")["result"] == "TRUE"
    facts["otherwise_permissible"] = False
    assert cmic_check(facts, action="buy", capacity="principal")["result"] == "FALSE"


def test_cmic_missing_facts_and_unsupported_actions_are_not_cleared():
    assert cmic_check({}, action="buy", capacity="principal")["result"] == "UNDETERMINED"
    facts = cmic_facts()
    facts["designated_issuer"] = None
    assert cmic_check(facts, action="buy", capacity="principal")["result"] == "UNDETERMINED"
    facts["designated_issuer"] = "conflict"
    assert cmic_check(facts, action="buy", capacity="principal")["result"] == "CONFLICT"
    for change in ({"action": "automatic_conversion", "capacity": "principal"},
                   {"action": "buy", "capacity": "unanalysed_service"}):
        with pytest.raises(ValueError):
            cmic_check({}, **change)
    with pytest.raises(ValueError):
        cmic_check({"human_approved": True}, action="buy", capacity="principal")


@pytest.mark.parametrize("kind", ["ordinary_bond", "AT1", "preferred_share", "equity", "fund", "derivative"])
def test_layer_composition_does_not_depend_on_coco_label(example, kind):
    context = replace(example[1], instrument_kind=kind)
    findings = tuple(replace(f, binding=binding(context, example[2])) for f in example[3])
    findings = (replace(findings[0], status=Status.UNKNOWN), *findings[1:])
    assert run(example, findings, context=context)["outcome"] == "UNDETERMINED"


def closure(seeds, edges):
    return blocked_ownership_closure(seeds, edges, program="blocking_50_percent")


def test_blocked_ownership_against_independent_closed_set_specification():
    # For every three-node half-stake graph and seed set, intersect ALL closed
    # supersets of the seeds. This definition does not execute the propagation
    # algorithm under test; it checks the least-fixed-point characterization.
    nodes = ("A", "B", "C")
    pairs = [(a, b) for a in nodes for b in nodes if a != b]
    subsets = [set(n for n, present in zip(nodes, bits) if present)
               for bits in product((False, True), repeat=3)]
    for include in product((False, True), repeat=6):
        edges = [(a, b, Fraction(1, 2)) for (a, b), present in zip(pairs, include) if present]
        for seeds in subsets:
            closed_sets = [s for s in subsets if seeds <= s and all(
                target in s or sum(amount for owner, owned, amount in edges
                                   if owned == target and owner in s) < Fraction(1, 2)
                for target in nodes)]
            specified = set.intersection(*closed_sets)
            assert set(closure(seeds, edges)["proven_blocked"]) == specified


def test_blocked_chain_aggregation_boundary_and_cycle():
    result = closure({"X"}, [("X", "A", Fraction(1, 2)), ("A", "B", Fraction(1, 2))])
    assert result["proven_blocked"] == ["A", "B", "X"]
    assert closure({"X", "Y"}, [("X", "A", Fraction(1, 4)),
                                  ("Y", "A", Fraction(1, 4))])["proven_blocked"] == ["A", "X", "Y"]
    assert closure({"X"}, [("X", "A", Fraction(4999, 10000))])["proven_blocked"] == ["X"]
    cycle = closure(set(), [("A", "B", Fraction(1, 2)), ("B", "A", Fraction(1, 2))])
    assert cycle["proven_blocked"] == []
    assert cycle["others"] == "NOT_CLEARED"
    with pytest.raises(ValueError):
        blocked_ownership_closure({"X"}, [], program="NS-CMIC")


@pytest.mark.parametrize("edges", [
    [("A", "B", 0.5)], [("A", "B", True)], [("A", "A", Fraction(1, 2))],
    [("A", "B", Fraction(1, 2)), ("A", "B", Fraction(1, 2))],
    [("A", "C", Fraction(3, 4)), ("B", "C", Fraction(1, 2))],
])
def test_invalid_ownership_inputs_are_rejected(edges):
    with pytest.raises(ValueError):
        closure({"A"}, edges)
