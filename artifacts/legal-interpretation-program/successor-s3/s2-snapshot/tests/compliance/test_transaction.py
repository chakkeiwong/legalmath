"""Evidence and orchestration attacks, independent of human quality labels."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from legalmath.canonical import digest
from legalmath.transaction import catalog
from legalmath.transaction.checks import prove_equations
from legalmath.transaction.engine import DERIVED, conditional, investigate, revalidate
from legalmath.transaction.evidence import Registry, Store, facts, pointer
from legalmath.transaction.intake import record
from legalmath.transaction.lifecycle import business_deadline, replay
from legalmath.transaction.sanctions import parse, candidates, changes

AT = "2026-09-29T00:00:00+00:00"
BEFORE = "2026-09-01T00:00:00+00:00"
AFTER = "2026-10-01T00:00:00+00:00"


def fixture(directory):
    store = Store(directory / "store")
    registry = {}
    for d in catalog.specifications().values():
        for source, quote in d["anchors"]:
            old = store.get(registry[source]["blob"]).decode() if source in registry else "Synthetic formal-premise source.\n"
            registry[source] = record(store.put((old + (quote or "Declared product premise") + "\n").encode()),
                "law", "synthetic:" + source, BEFORE, provenance="synthetic", effective_from=BEFORE, fresh_until=AFTER)
    values = {name: True if typ == "bool" else 100000000 for name, typ in catalog.declarations().items() if name not in DERIVED}
    values.update(portfolio=4000000000, net_assets=8000000000)
    registry["account"] = record(store.put(values), "facts", "synthetic:account", BEFORE,
        media_type="application/json", provenance="synthetic", effective_from=BEFORE, fresh_until=AFTER)
    assertions = {k: [{"source": "account", "pointer": "/" + k}] for k in values}
    route = {"capacity": "principal", "currencies": ["USD"], "roles": [
        {"role": role, "entity_id": "synthetic-bank", "name": "Synthetic Bank", "establishment_id": "hk",
         "jurisdiction": "HK", "source_ids": ["account"]} for role in ("booking", "executing", "custody", "payment")]}
    request = {"profile": catalog.PROFILE, "capacity": "principal", "registry_sha256": store.put(registry),
        "context": {"instrument_id": "synthetic-instrument", "instrument_kind": "ordinary_bond", "client_id": "synthetic-client",
            "booking_entity_id": "synthetic-bank", "establishment_id": "hk", "service": "purchase-investigation", "action": "buy",
            "effective_at": AT, "known_at": AT, "facts_sha256": store.put(assertions), "route_sha256": store.put(route),
            "policy_sha256": store.put({"source_ids": [], "mandate_source_ids": []})}}
    return store, request


def update_registry(store, request, edit):
    records = store.json(request["registry_sha256"])
    edit(records)
    request["registry_sha256"] = store.put(records)


def update_values(store, request, edit):
    def update(records):
        values = store.json(records["account"]["blob"])
        edit(values)
        records["account"]["blob"] = store.put(values)
    update_registry(store, request, update)


@pytest.fixture
def scenario(tmp_path):
    return fixture(tmp_path)


def test_all_catalog_obligations_derived_and_missing_policy_retained(scenario):
    store, request = scenario
    result = investigate(request, store)
    assert len(result["inventory"]) == 14
    assert len(result["formal_assessment"]["trace"]) == 14
    assert result["calculations"]["bsa_program"]["satisfied"]["value"] is True
    assert result["decision"] == "QUALIFIED" and not result["may_execute_transaction"]
    assert any("policy.internal" in gap for gap in result["formal_assessment"]["unresolved"])
    assert result["complete_legal_coverage"] == "NOT_ESTABLISHED"
    assert all(x["source_meaning"] == "NOT_ESTABLISHED" for x in result["interpretation_limits"])
    assert revalidate(result, request, store) == result


@pytest.mark.parametrize("injection", ["requirements", "findings", "human_approved", "expected", "quality"])
def test_request_cannot_supply_inventory_or_answers(scenario, injection):
    store, request = scenario
    request[injection] = []
    with pytest.raises(ValueError):
        investigate(request, store)


@pytest.mark.parametrize("field", ["facts_sha256", "route_sha256", "policy_sha256"])
def test_hashes_must_resolve_to_actual_content(scenario, field):
    store, request = scenario
    request["context"][field] = "0" * 64
    with pytest.raises(FileNotFoundError):
        investigate(request, store)


def test_nonapplicability_is_computed_from_facts(scenario):
    store, request = scenario
    update_values(store, request, lambda v: v.update(national_bank=False, covered_savings_association=False))
    result = investigate(request, store)
    row = next(x for x in result["formal_assessment"]["trace"] if x["rule_id"] == "bank.bsa_program")
    assert row["status"] == "NOT_APPLICABLE"
    update_values(store, request, lambda v: v.pop("national_bank"))
    result = investigate(request, store)
    row = next(x for x in result["formal_assessment"]["trace"] if x["rule_id"] == "bank.bsa_program")
    assert row["status"] == "UNKNOWN"


@pytest.mark.parametrize("source_change", ["bytes", "late", "expired", "stale", "effective_unknown", "dependency", "amendment", "cycle"])
def test_source_changes_prevent_stale_positive_finding(scenario, source_change):
    store, request = scenario
    receipt = investigate(request, store)
    key = "us-bank-bsa-program-2025"
    def edit(records):
        row = records[key]
        if source_change == "bytes":
            store.path(row["blob"]).write_text("corrupted")
        elif source_change == "late": row["recorded_at"] = AFTER
        elif source_change == "expired": row["effective_until"] = AT
        elif source_change == "stale": row["fresh_until"] = AT
        elif source_change == "effective_unknown": row["effective_from"] = None
        elif source_change == "dependency": row["dependencies"] = ["missing-law"]
        elif source_change == "cycle": row["dependencies"] = [key]
        else:
            records["amendment"] = {**deepcopy(row), "supersedes": [key]}
    update_registry(store, request, edit)
    result = investigate(request, store)
    row = next(x for x in result["formal_assessment"]["trace"] if x["rule_id"] == "bank.bsa_program")
    assert row["status"] == "UNKNOWN"
    with pytest.raises(ValueError): revalidate(receipt, request, store)


def test_conflicting_factual_documents_survive(scenario):
    store, request = scenario
    def edit(records):
        records["contradiction"] = {**records["account"], "blob": store.put({"national_bank": False})}
    update_registry(store, request, edit)
    assertions = store.json(request["context"]["facts_sha256"])
    assertions["national_bank"].append({"source": "contradiction", "pointer": "/national_bank"})
    request["context"]["facts_sha256"] = store.put(assertions)
    result = investigate(request, store)
    assert result["observations"]["national_bank"]["status"] == "CONFLICT"
    assert result["calculations"]["bsa_program"]["applies"]["status"] == "CONFLICT"


@pytest.mark.parametrize("value", ["true", 1, None])
def test_boolean_facts_are_not_coerced(scenario, value):
    store, request = scenario
    update_values(store, request, lambda v: v.update(national_bank=value))
    assert investigate(request, store)["observations"]["national_bank"]["status"] == "UNKNOWN"


@pytest.mark.parametrize("change", ["action", "entity", "policy", "route", "receipt"])
def test_changed_context_or_forged_receipt_rejected(scenario, change):
    store, request = scenario
    result = investigate(request, store)
    if change == "action": request["context"]["action"] = "hold"
    elif change == "entity": request["context"]["booking_entity_id"] = "different-bank"
    elif change == "policy": request["context"]["policy_sha256"] = store.put({"source_ids": ["account"], "mandate_source_ids": []})
    elif change == "route":
        route = store.json(request["context"]["route_sha256"]); route["currencies"] = ["HKD"]
        request["context"]["route_sha256"] = store.put(route)
    else:
        result["may_execute_transaction"] = True
        result["receipt_hash"] = digest({k: v for k, v in result.items() if k != "receipt_hash"})
    with pytest.raises(ValueError): revalidate(result, request, store)


@pytest.mark.parametrize("action", ["conversion", "redemption", "write_down", "dividend_reinvestment", "transfer"])
def test_unsupported_corporate_actions_do_not_use_buy_sell_result(scenario, action):
    store, request = scenario
    request["context"]["action"] = action
    result = investigate(request, store)
    row = next(x for x in result["formal_assessment"]["trace"] if x["rule_id"] == "sanctions.cmic")
    assert row["status"] == "UNKNOWN"
    assert result["calculations"]["cmic"]["satisfied"]["value"] is None


def test_private_account_threshold_territory_and_definition(scenario):
    store, request = scenario
    for amount, expected in ((99999999, False), (100000000, True), (100000001, True)):
        update_values(store, request, lambda v: v.update(required_minimum_usd_cents=amount))
        assert investigate(request, store)["calculations"]["private_account"]["applies"]["value"] is expected
    update_values(store, request, lambda v: v.update(established_us=False, maintained_us=False, administered_us=False, managed_us=False))
    assert investigate(request, store)["calculations"]["private_account"]["applies"]["value"] is False
    update_values(store, request, lambda v: v.update(managed_us=True))
    assert investigate(request, store)["calculations"]["private_account"]["applies"]["value"] is True


def test_independent_equations_and_mutant_witnesses(tmp_path):
    result = prove_equations(tmp_path)
    assert len(result["obligations"]) >= 14
    assert len(result["detected_mutations"]) == 3


def xml(program="NS-CMIC", count=1, name="Example Company", uid="1"):
    return f'''<sdnList><publshInformation><Publish_Date>09/14/2026</Publish_Date><Record_Count>{count}</Record_Count></publshInformation>
<sdnEntry><uid>{uid}</uid><lastName>{name}</lastName><programList><program>{program}</program></programList></sdnEntry></sdnList>'''.encode()


def test_feed_count_program_identity_and_changes():
    a = parse(xml(), list_kind="CONSOLIDATED")
    assert candidates(a, "EXAMPLE Company", program="NS-CMIC")["status"] == "IDENTITY_CANDIDATES"
    absent = candidates(a, "Unknown future issuer")
    assert absent["sanctions_clearance"] == "NOT_ESTABLISHED"
    b = parse(xml(uid="2"), list_kind="CONSOLIDATED")
    assert changes(a, b) == {"added": ["2"], "removed": ["1"], "changed": [], "invalidate_prior_screening": True}
    with pytest.raises(ValueError): parse(xml(count=2), list_kind="CONSOLIDATED")
    with pytest.raises(ValueError): parse(xml(), list_kind="SDN")
    with pytest.raises(ValueError): parse(b"<html>Access denied</html>", list_kind="SDN")
    with pytest.raises(ValueError): parse(b'<!DOCTYPE x [<!ENTITY y "x">]><sdnList/>', list_kind="SDN")
    mixed = xml().replace(b"<program>NS-CMIC</program>", b"<program>NS-PLC</program><program>SDGT</program>")
    assert parse(mixed, list_kind="SDN")["entries"][0]["programs"] == ["NS-PLC", "SDGT"]


def test_pointers_do_not_coerce_or_escape():
    assert pointer({"a/b": {"~": [True]}}, "/a~1b/~0/0") is True
    for path in ("a", "/~2", "/a~1b/~0/01", "/a~1b/~0/-1"):
        with pytest.raises((ValueError, KeyError)): pointer({"a/b": {"~": [True]}}, path)


def test_business_calendar_is_explicit_and_bounded(tmp_path):
    store = Store(tmp_path)
    calendar = {"id": "synthetic-calendar", "start": "2026-09-01", "end": "2026-10-31",
                "holidays": ["2026-09-28"], "weekend": [5, 6]}
    calendar["source_sha256"] = store.put(calendar)
    assert business_deadline("2026-09-25", 1, calendar=calendar, store=store) == "2026-09-29"
    with pytest.raises(ValueError): business_deadline("2026-10-31", 1, calendar=calendar, store=store)
    calendar["holidays"] = []
    with pytest.raises(ValueError): business_deadline("2026-09-25", 1, calendar=calendar, store=store)


def test_event_invalidation_idempotency_and_duty_evidence(scenario):
    store, request = scenario
    receipt = investigate(request, store)
    assessment = {"id": "assessment-1", "at": AT, "kind": "assessment", "payload": {"request": request, "receipt": receipt}}
    source = store.put(b"Synthetic duty premise; not a legal certification")
    duty = {"id": "duty-1", "at": AT, "kind": "duty_created", "payload": {
        "duty_id": "report-1", "kind": "report", "actor": "synthetic-bank", "trigger": "synthetic-rejection",
        "due_at": AFTER, "source_sha256": source, "basis_receipt": receipt["receipt_hash"]}}
    completion = {"id": "complete-1", "at": AT, "kind": "duty_completed", "payload": {"duty_id": "report-1", "evidence_sha256": source}}
    result = replay([assessment, duty, duty, completion], store=store)
    assert len(result["duties"]) == 1
    assert result["duties"]["report-1"]["state"] == "EVIDENCE_RECORDED"
    assert result["duties"]["report-1"]["actual_performance"] == "NOT_ESTABLISHED"
    change = {"id": "change-1", "at": AT, "kind": "corporate_action", "payload": {"evidence_sha256": source, "description": "conversion"}}
    result = replay([assessment, change], store=store)
    assert result["current_assessment"] is None
    with pytest.raises(ValueError): replay([assessment, change, {"id": "settle", "at": AT,
        "kind": "settlement_requested", "payload": {"receipt_hash": receipt["receipt_hash"]}}], store=store)
    with pytest.raises(ValueError): replay([assessment, {**assessment, "kind": "facts_changed"}], store=store)
    with pytest.raises(ValueError): replay([assessment, {**change, "at": BEFORE}], store=store)


def test_new_instrument_names_do_not_remove_obligations(scenario):
    store, request = scenario
    expected = {r["rule_id"] for r in catalog.inventory(catalog.PROFILE)}
    for kind in ("preferred_share", "fund", "derivative", "future_unrecognized_instrument"):
        request["context"]["instrument_kind"] = kind
        result = investigate(request, store)
        assert {r["rule_id"] for r in result["inventory"]} == expected
        assert not result["may_execute_transaction"]


def test_ownership_data_is_retrieved_and_program_specific(scenario):
    store, request = scenario
    graph = {"directly_blocked": ["x"], "program": "blocking_50_percent", "interests": [
        {"owner": "x", "owned": "a", "numerator": 1, "denominator": 2},
        {"owner": "a", "owned": "b", "numerator": 1, "denominator": 2}]}
    def edit(records):
        records["ownership-observations"] = {**records["account"], "blob": store.put(graph)}
    update_registry(store, request, edit)
    result = investigate(request, store)
    assert result["ownership"]["proven_blocked"] == ["a", "b", "x"]
    assert result["ownership"]["others"] == "NOT_CLEARED"
    graph["program"] = "NS-CMIC"
    update_registry(store, request, edit)
    with pytest.raises(ValueError): investigate(request, store)
    graph.update(program="blocking_50_percent", directly_blocked="issuer-name-is-not-a-list")
    update_registry(store, request, edit)
    with pytest.raises(ValueError): investigate(request, store)


def test_passage_of_time_requires_new_settlement_assessment(scenario):
    store, request = scenario
    receipt = investigate(request, store)
    with pytest.raises(ValueError):
        replay([{"id": "a", "at": AT, "kind": "assessment", "payload": {"request": request, "receipt": receipt}},
                {"id": "s", "at": AFTER, "kind": "settlement_requested", "payload": {"receipt_hash": receipt["receipt_hash"]}}], store=store)


def test_frozen_future_method_rejects_changed_code_and_reused_corpus(scenario):
    from legalmath.transaction.prospective import freeze, observe
    store, request = scenario
    hashes = [r["blob"] for r in store.json(request["registry_sha256"]).values()]
    frozen = freeze(at=BEFORE, known_source_hashes=hashes)
    with pytest.raises(ValueError): observe(frozen, request, store)
    update_values(store, request, lambda v: v.update(required_minimum_usd_cents=99999999))
    observed = observe(frozen, request, store)
    assert observed["new_source_hashes"]
    assert observed["prospective_legal_accuracy"] == "NOT_ESTABLISHED"
    frozen["method_hash"] = "0" * 64
    with pytest.raises(ValueError): observe(frozen, request, store)


def test_command_line_help_has_all_executable_paths():
    import subprocess
    import sys
    p = subprocess.run([sys.executable, "-m", "legalmath.transaction", "--help"], capture_output=True, text=True)
    assert p.returncode == 0
    for name in ("example", "evaluate", "verify", "screen", "replay", "freeze", "observe", "refresh-feeds"):
        assert name in p.stdout


def test_derived_product_claim_cannot_override_its_numbers(scenario):
    store, request = scenario
    update_values(store, request, lambda v: v.update(portfolio=0, net_assets=0, financial_pass=True))
    result = investigate(request, store)
    assert result["observations"]["financial_pass"]["status"] == "CONFLICT"
    assert result["calculations"]["product_eligibility"]["eligible"]["status"] == "CONFLICT"


def test_amount_test_cannot_substitute_for_threshold_controls(scenario):
    store, request = scenario
    update_values(store, request, lambda v: v.pop("threshold_controls_established"))
    result = investigate(request, store)
    assert result["observations"]["threshold_compliant"]["status"] == "UNKNOWN"


def test_sufficient_complexity_failure_does_not_prove_simplicity(scenario):
    store, request = scenario
    update_values(store, request, lambda v: v.update(bond=False, complex_product=True))
    result = investigate(request, store)
    assert result["observations"]["complex_product"]["value"] is True
