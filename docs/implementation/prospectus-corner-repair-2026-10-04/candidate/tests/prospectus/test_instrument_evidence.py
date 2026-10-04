from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import pytest

from legalmath.prospectus.instrument_evidence import resolve, attach_private, CoveredCalendar, source_change, BANK_SCOPE
from legalmath.prospectus import instrument_cases
from legalmath.transaction import engine, prospective, intake
from legalmath.transaction.evidence import Store

ROOT = Path(__file__).resolve().parents[2]
AT = "2026-09-29T00:00:00Z"


def evidence(store, value, scope, kind, **changes):
    row = dict(source_sha256=store.put(value), scope=scope, kind=kind, recorded_at=AT,
        effective_from=AT, effective_until=None, fresh_until="2026-10-01T00:00:00Z",
        complete=True, premise_kind="HYPOTHETICAL")
    row.update(changes)
    return store.put(row)


def test_scoped_false_is_preserved_and_unknown_is_not_false(tmp_path):
    store = Store(tmp_path)
    scope = {"instrument_id": "A", "client_id": "B"}
    identity = evidence(store, {"allowed": False}, scope, "private_facts")
    assert resolve(store, identity, scope=scope, kind="private_facts", at=AT, known_at=AT)["value"] == {"allowed": False}
    assert resolve(store, None, scope=scope, kind="private_facts", at=AT, known_at=AT)["status"] == "UNKNOWN"
    for other in ({"instrument_id": "X", "client_id": "B"}, {"instrument_id": "A"}):
        assert resolve(store, identity, scope=other, kind="private_facts", at=AT, known_at=AT)["status"] == "UNKNOWN"


@pytest.mark.parametrize("change", [{"complete": False}, {"effective_from": None},
    {"fresh_until": None}, {"recorded_at": "2026-09-30T00:00:00Z"},
    {"fresh_until": AT}, {"effective_until": "2026-09-29T00:00:00Z", "effective_from": "2026-09-28T00:00:00Z"}])
def test_missing_stale_future_and_incomplete_records_do_not_fill_facts(tmp_path, change):
    store = Store(tmp_path)
    identity = evidence(store, {}, {}, "law_coverage", **change)
    assert resolve(store, identity, scope={}, kind="law_coverage", at=AT, known_at=AT)["status"] == "UNKNOWN"


def test_tampering_rejected(tmp_path):
    store = Store(tmp_path)
    identity = evidence(store, {"x": True}, {}, "publication")
    store.path(store.json(identity)["source_sha256"]).write_bytes(b'{"x":false}')
    with pytest.raises(ValueError, match="changed"):
        resolve(store, identity, scope={}, kind="publication", at=AT, known_at=AT)


def calendar(market="SIX", closures=()):
    a, b = date(2026,9,1), date(2026,9,30)
    days = {(a+timedelta(days=i)).isoformat(): (a+timedelta(days=i)).weekday()<5 for i in range((b-a).days+1)}
    for d in closures: days[d] = False
    return {"market": market, "purpose": "exchange_dealing", "start": a.isoformat(), "end": b.isoformat(), "days": days}


def test_calendar_purpose_complete_coverage_and_rank():
    record = calendar(closures=["2026-09-07"])
    c = CoveredCalendar(record, market="SIX", purpose="exchange_dealing")
    assert c.preceding("2026-09-10",5) == ["2026-09-02","2026-09-03","2026-09-04","2026-09-08","2026-09-09"]
    with pytest.raises(ValueError, match="purpose"): CoveredCalendar(record,market="SIX",purpose="bank_fx")
    del record["days"]["2026-09-07"]
    with pytest.raises(ValueError,match="Every"): CoveredCalendar(record,market="SIX",purpose="exchange_dealing")
    with pytest.raises(ValueError,match="cover"): c.preceding("2026-10-01",5)


def test_watch_reopens_dependents_without_certifying_unchanged_law():
    prior = dict(url="https://official.example/calendar.pdf", sha256="1"*64, retrieved_at=AT, purpose="clearing-2026")
    current = dict(prior, sha256="2"*64, retrieved_at="2026-09-30T00:00:00Z", purpose="clearing-2027")
    assert source_change(prior,current,dependent_receipts=["r1","r2"])["reassess_receipts"] == ["r1","r2"]
    unchanged = dict(prior,retrieved_at=current["retrieved_at"])
    result = source_change(prior,unchanged,dependent_receipts=["r1"])
    assert not result["changed"] and result["current_legal_force"] == "NOT_ESTABLISHED"


def test_private_adapter_preserves_all_layers_conflicts_and_route_identity(tmp_path):
    request, store = instrument_cases.request(ROOT,tmp_path)
    bank = request["joined_request"]["bank_request"]
    bank["context"].update(effective_at=AT,known_at=AT)
    scope = {k:bank["context"][k] for k in BANK_SCOPE}
    yes = evidence(store,{"professional_investor":True},scope,"private_facts")
    no = evidence(store,{"professional_investor":False},scope,"private_facts")
    wrong = evidence(store,{"professional_investor":True},dict(scope,route_sha256="9"*64),"private_facts")
    adapted = attach_private(bank,store,[yes,no,wrong])
    assert len(adapted["accepted"]) == 2 and len(adapted["unresolved"]) == 1
    report = engine.investigate(adapted["request"],store)
    assert report["observations"]["professional_investor"]["status"] == "CONFLICT"
    assert len(report["inventory"]) == 14 and not report["may_execute_transaction"]
    evil = evidence(store,{"human_verified_correct":True},scope,"private_facts")
    with pytest.raises(ValueError,match="quality labels"): attach_private(bank,store,[evil])


def test_new_private_fact_and_old_source_are_not_future_legal_observations(tmp_path):
    request, store = intake.bootstrap(ROOT,tmp_path,at=AT)
    records = store.json(request["registry_sha256"])
    frozen = prospective.freeze(at="2026-09-28T00:00:00Z",known_source_hashes=[r["blob"] for r in records.values()])
    chronology = {}
    for key, kind, published in [("new-fact","facts",AT),("old-law","law","2020-01-01T00:00:00Z"),("later-law","law",AT)]:
        blob = store.put({"name":key})
        records[key] = intake.record(blob,kind,"https://official.example/"+key,AT)
        chronology[blob] = dict(published_at=published,retrieved_at=AT,origin=records[key]["origin"],date_evidence_sha256=store.put({"published":published}))
    request["registry_sha256"] = store.put(records)
    result = prospective.observe_sources(frozen,request,store,chronology_sha256=store.put(chronology))
    assert {r["classification"] for r in result["source_observations"]} == {
        "NEW_FACT_OR_MIXED_KIND_NOT_NEW_LAW", "PREEXISTING_DOCUMENT_NEW_TO_INVENTORY", "POST_FREEZE_PUBLICATION_UNATTESTED"}
    assert result["future_legal_accuracy"] == "NOT_ESTABLISHED"
    chronology[next(iter(chronology))]["published_at"] = "2026-09-30T00:00:00Z"
    with pytest.raises(ValueError,match="Publication"):
        prospective.observe_sources(frozen,request,store,chronology_sha256=store.put(chronology))
