from copy import deepcopy
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.semantics.operative import build_overlay, write_overlay

def sample():
    records = [{"role": "structure-reader", "reading_id": "r.1",
                "original": {"reading": "untouched"},
                "operative": {"reading": {"remaining_questions": ["prior text"]},
                              "candidate_repair": {"formalization": {"result": "(and x y)"}}},
                "accepted_substantive_repair": False}]
    patch = {"role": "structure-reader", "reading_id": "r.1",
             "path": ["reading", "remaining_questions", 0], "before": "prior text",
             "after": "Source acquired; applicability unresolved.", "reason": "Acquisition differs from applicability",
             "evidence_ids": ["source.1"]}
    return records, patch

def build(records, patches, pointer=lambda: "a"*64):
    return build_overlay(records, patches, expected_pointer="a"*64, current_pointer=pointer,
                         evidence={"source.1": {"source_hash": "b"*64}})

def test_overlay_preserves_originals_formula_and_predecessor():
    records, patch = sample()
    before = deepcopy(records)
    out = build(records, [patch])
    assert records == before
    assert out["records"][0]["original"] == before[0]["original"]
    assert out["records"][0]["operative"]["candidate_repair"] == before[0]["operative"]["candidate_repair"]
    assert out["changes"][0]["predecessor_record_hash"] == digest(before[0])
    assert out["accepted_substantive_repairs"] == out["formula_changes"] == 0
    assert out["records"][0]["operative"]["reading"]["remaining_questions"][0] == patch["after"]

@pytest.mark.parametrize("mutation", ["text", "duplicate", "formula", "negative_index", "unknown_source", "status"])
def test_invalid_overlay_is_rejected(mutation):
    records, patch = sample()
    if mutation == "text": patch["before"] = "stale"
    if mutation == "formula": patch["path"] = ["candidate_repair", "formalization", "result"]
    if mutation == "negative_index": patch["path"][-1] = -1
    if mutation == "unknown_source": patch["evidence_ids"] = ["absent"]
    if mutation == "status": patch["path"] = ["reading", "status"]
    with pytest.raises(LegalMathError):
        build(records, [patch, patch] if mutation == "duplicate" else [patch])

def test_pointer_changes_before_writing(tmp_path):
    records, patch = sample()
    with pytest.raises(LegalMathError):
        build(records, [patch], pointer=lambda: "changed")
    out = build(records, [patch])
    target = tmp_path/"overlay.json"
    with pytest.raises(LegalMathError):
        write_overlay(target, out, current_pointer=lambda: "changed")
    assert not target.exists()
    write_overlay(target, out, current_pointer=lambda: "a"*64)
    with pytest.raises(LegalMathError):
        write_overlay(target, out, current_pointer=lambda: "a"*64)
