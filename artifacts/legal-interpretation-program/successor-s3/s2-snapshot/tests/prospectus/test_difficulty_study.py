"""Diagnostic study safeguards; not tests of legal truth."""
import importlib.util
from pathlib import Path
import pytest

path = Path(__file__).resolve().parents[2] / "scripts/prospectus_difficulty_study.py"
spec = importlib.util.spec_from_file_location("difficulty_study", path)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def test_method_tampering_rejected():
    with pytest.raises(ValueError, match="Frozen study method"):
        study.validate_frozen({"reader.py": "old"}, {"reader.py": "changed"})


def test_unavailable_and_errors_stay_in_denominator():
    rows = [{"status": "UNAVAILABLE"}, {"status": "ENGINE_ERROR"},
            {"status": "ABSTAIN", "answer": None}, {"status": "CONDITIONAL_READING", "answer": True}]
    result = study.summarize(rows)
    assert result["selected"] == 4
    assert result["statuses"] == dict.fromkeys(["UNAVAILABLE", "ENGINE_ERROR", "ABSTAIN", "CONDITIONAL_READING"], 1)


def test_duplicate_case_identity_rejected():
    rows = [{"id": "same", "issuer": "bank", "review": {"anchors": []}, "difficulty": "scope"} for _ in range(24)]
    with pytest.raises(ValueError, match="Duplicate case"):
        study.checked_cases(rows)
