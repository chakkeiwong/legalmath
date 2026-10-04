from copy import deepcopy
import runpy
from pathlib import Path

import pytest

from legalmath.prospectus import feature_investigation as integration, source_obligations as obligations
from legalmath.prospectus.loss_absorption_reader import analyze_issue
from legalmath.transaction.intake import record
from tests.prospectus.test_loss_absorption import fixture, ORDINARY

AT = "2026-06-01T00:00:00Z"


def setup(tmp_path):
    issue, docs, _ = fixture(tmp_path, [ORDINARY + " The Notes are subject to the Agency Agreement dated 1 May 2025. Upon a Capital Event, the principal amount of the Notes shall be permanently reduced."])
    docs[next(iter(docs))]["url"] = "synthetic:prospectus"
    row = analyze_issue(issue, docs, tmp_path)
    bank_fixture = runpy.run_path(str(Path(__file__).parents[1]/"compliance/test_transaction.py"))["fixture"]
    store, bank = bank_fixture(tmp_path/"bank")
    bank["context"].update(instrument_id=issue["id"], effective_at=AT, known_at=AT)
    return issue, docs, row, store, bank


@pytest.mark.parametrize("mutation", ["answer", "condition", "source", "identity"])
def test_verified_feature_rejects_forged_or_stale_input(tmp_path, mutation):
    issue, docs, row, store, bank = setup(tmp_path)
    if mutation == "answer": row["answer"] = False
    elif mutation == "condition":
        e = next(e for e in row["evidence"] if e["kind"] == "principal_write_down")
        e["quote"] = e["quote"].replace("Upon a Capital Event, ", "")
    elif mutation == "source": docs[next(iter(docs))]["sha256"] = "0"*64
    else: bank["context"]["instrument_id"] = "another-bond"
    with pytest.raises(ValueError): integration.investigate(row, issue, docs, tmp_path, bank, store)


@pytest.mark.parametrize("mutation", ["drop_reference", "drop_condition", "closed", "edition"])
def test_obligation_and_condition_mutations_rejected_even_with_new_hash(tmp_path, mutation):
    from legalmath.prospectus.common import digest
    issue, docs, row, _, _ = setup(tmp_path)
    packet = obligations.build(row, issue, docs, tmp_path, as_of=AT)
    assert obligations.verify(packet, row, issue, docs, tmp_path) == packet
    if mutation == "drop_reference": packet["references"] = []
    elif mutation == "drop_condition": packet["mechanisms"][0]["full_condition_quote"]["quote"] = "Unconditional reduction"
    elif mutation == "closed": packet["all_dependencies_found"] = True
    else: packet["bindings"][0]["selection"]["required_markers"] = ["Wrong edition"]
    # Recompute a content hash; integrity alone is not permission to change meaning.
    packet["sha256"] = digest({k: v for k, v in packet.items() if k != "sha256"})
    with pytest.raises(ValueError): obligations.verify(packet, row, issue, docs, tmp_path)


def test_actual_bank_dispatch_does_not_promote_feature_to_scope_or_permission(tmp_path):
    issue, docs, row, store, bank = setup(tmp_path)
    assert row["answer"] is True
    r = integration.investigate(row, issue, docs, tmp_path, bank, store)
    assert len(r["bank_investigation"]["inventory"]) == 14
    assert not r["may_execute_transaction"]
    assert r["bank_investigation"]["calculations"]["scope"]["in_scope_product"]["status"] == "UNKNOWN"
    assert "qualifying_contingent_loss_absorption" in r["required_product_evidence"]
    assert r["source_obligations"]["all_dependencies_found"] is False


@pytest.mark.parametrize("case", ["statutory_only", "stale", "conflict"])
def test_actual_bank_preserves_separate_scope_staleness_and_conflict(tmp_path, case):
    issue, docs, row, store, bank = setup(tmp_path)
    records = store.json(bank["registry_sha256"])
    values = {"debt_legal_form": True, "qualifying_wrapper": False,
              "qualifying_contingent_loss_absorption": False, "plain_debt_or_deposit": False}
    records["explicit_scope"] = record(store.put(values), "facts", "synthetic:explicit-scope", "2026-01-01T00:00:00Z",
        media_type="application/json", provenance="synthetic", effective_from="2026-01-01T00:00:00Z",
        fresh_until="2026-02-01T00:00:00Z" if case == "stale" else "2027-01-01T00:00:00Z")
    assertions = {k: [{"source": "explicit_scope", "pointer": "/"+k}] for k in values}
    if case == "conflict":
        records["contrary_scope"] = {**records["explicit_scope"], "blob": store.put({"qualifying_contingent_loss_absorption": True})}
        assertions["qualifying_contingent_loss_absorption"].append({"source": "contrary_scope", "pointer": "/qualifying_contingent_loss_absorption"})
    bank["registry_sha256"] = store.put(records)
    r = integration.investigate(row, issue, docs, tmp_path, bank, store, product_assertions_sha256=store.put(assertions))
    scope = r["bank_investigation"]["calculations"]["scope"]["in_scope_product"]
    if case == "statutory_only": assert scope["status"] == "KNOWN" and scope["value"] is False
    else: assert scope["status"] == {"stale": "UNKNOWN", "conflict": "CONFLICT"}[case]
    assert not r["may_execute_transaction"]
