from copy import deepcopy
import pytest
from legalmath.ir.normalize import normalize
from legalmath.errors import LegalMathError

BEFORE = "2026-09-01T00:00:00.000000Z"
NOW = "2026-09-02T00:00:00.000000Z"
AFTER = "2026-09-03T00:00:00.000000Z"
DECL = [{"name": "wealth", "type": "money_hkd"}]


def record():
    return {"record_id": "old", "subject_id": "client", "fact_name": "wealth", "type": "money_hkd", "value": "100", "evidence_ids": ["e.old"], "valid_from": BEFORE, "valid_until": None, "recorded_at": BEFORE, "supersedes_record_ids": []}


def test_interval_local_and_late_corrections():
    old = record()
    new = {**old, "record_id": "new", "value": "200", "evidence_ids": ["e.new"], "valid_from": AFTER, "recorded_at": NOW, "supersedes_record_ids": ["old"]}
    assert normalize([old, new], DECL, "client", NOW, NOW)["facts"]["wealth"]["value"] == "100"
    assert normalize([old, new], DECL, "client", AFTER, AFTER)["facts"]["wealth"]["value"] == "200"
    new["valid_from"], new["recorded_at"] = BEFORE, AFTER
    assert normalize([old, new], DECL, "client", NOW, NOW)["facts"]["wealth"]["value"] == "100"
    assert normalize([old, new], DECL, "client", NOW, AFTER)["facts"]["wealth"]["value"] == "200"


def test_conflict_and_bad_correction():
    old = record()
    new = {**old, "record_id": "new", "value": "200", "evidence_ids": ["e.new"]}
    assert normalize([old, new], DECL, "client", NOW, NOW)["facts"]["wealth"]["status"] == "conflict"
    new["supersedes_record_ids"] = ["absent"]
    with pytest.raises(LegalMathError): normalize([old, new], DECL, "client", NOW, NOW)
    new["supersedes_record_ids"], old["supersedes_record_ids"] = ["old"], ["new"]
    with pytest.raises(LegalMathError) as e: normalize([old, new], DECL, "client", NOW, NOW)
    assert e.value.code == "E_CYCLE"
