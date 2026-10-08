from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path

import pytest

from legalmath.catala.adapter import UnsupportedProfile, finish, native_integer, prepare
from legalmath.catala.runtime import manifest, sha, verify_package, write_json
from legalmath.canonical import digest

ROOT = Path(__file__).resolve().parents[2]
PROFILE = json.loads((ROOT / "examples/catala/profile.json").read_text())
CASES = json.loads((ROOT / "docs/specs/v0.1/fixtures/decision-cases.json").read_text())["cases"]


def case(name):
    return deepcopy(next(c for c in CASES if c["id"] == name))


@pytest.mark.parametrize("mutation", ["threshold", "source", "rule", "mode"])
def test_altered_rules_and_production_are_rejected(mutation):
    c = case("f01")
    if mutation == "threshold":
        c["bundle"]["rules"][0]["body"]["args"][0]["right"]["value"] = "1"
    elif mutation == "source":
        c["bundle"]["source_spans"][0]["raw_sha256"] = "0" * 64
    elif mutation == "rule":
        c["rule_id"] = "another.rule"
    else:
        c["mode"] = "production"
    with pytest.raises(UnsupportedProfile):
        prepare(c, PROFILE)


def test_missing_amount_is_masked_not_promoted():
    p = prepare(case("f06"), PROFILE)
    assert p["inputs"]["portfolio_known"] is False
    assert p["base"]["missing_inputs"] == ["portfolio"]
    result = finish(p, {"decision": "1"}, "test-only")
    assert result["status"] == "TRUE" and result["missing_inputs"] == ["portfolio"]
    assert result["blocking_inputs"] == []
    assert "trace" not in result and result["release_eligible"] is False


def test_known_at_boundary_changes_available_evidence():
    c = case("f01")
    assert prepare(c, PROFILE)["inputs"]["portfolio_known"]
    c["known_at"] = "2026-08-31T23:59:59.999999Z"
    p = prepare(c, PROFILE)
    assert not p["inputs"]["portfolio_known"] and not p["inputs"]["assets_known"]


def test_interpreter_decimal_encoding_is_exact():
    assert native_integer(Decimal("1.0")) == 1
    assert native_integer(Decimal("123456789012345678901234567890")) == 123456789012345678901234567890
    with pytest.raises(ValueError):
        native_integer(Decimal("1.00000000000000000001"))


def test_conflict_precedes_scope_skip():
    c = case("scope.false")
    c["snapshot"]["facts"]["portfolio"] = {
        "status": "conflict", "type": "money_hkd", "evidence_ids": ["a", "b"]}
    p = prepare(c, PROFILE)
    assert p["preflight"] == "input_conflict"
    assert p["base"]["blocking_inputs"] == ["portfolio"]


def test_expired_bundle_retains_complete_diagnostic():
    result = finish(prepare(case("time.version"), PROFILE), None, "test-only")
    assert result["status"] == "ERROR"
    assert result["diagnostics"] == [{"code": "E_VERSION_TIME", "pointer": "/valid_at",
        "message": "Assessment time is outside the bundle interval."}]


def test_result_identity_commits_to_implementation_bytes():
    p = prepare(case("f01"), PROFILE)
    first = finish(p, {"decision": "1"}, "test-only", {"jar_sha256": "a" * 64})
    second = finish(p, {"decision": "1"}, "test-only", {"jar_sha256": "b" * 64})
    assert first["result_hash"] != second["result_hash"]
    assert first["result_hash"] == digest({k: v for k, v in first.items() if k != "result_hash"})


@pytest.mark.parametrize("native", [{}, {"decision": "3"}, {"decision": "99"},
                                   {"decision": True}, {"decision": 1.5}])
def test_malformed_native_financial_response_is_not_accepted(native):
    with pytest.raises(ValueError):
        finish(prepare(case("f01"), PROFILE), native, "test-only")


def test_package_needs_external_hash_and_exact_contents(tmp_path):
    write_json(tmp_path / "package.json", {"release_eligible": False})
    (tmp_path / "policy.jar").write_bytes(b"synthetic integrity test")
    write_json(tmp_path / "manifest.json", manifest(tmp_path))
    trusted = sha(tmp_path / "manifest.json")
    verify_package(tmp_path, trusted)
    (tmp_path / "policy.jar").write_bytes(b"changed")
    with pytest.raises(ValueError):
        verify_package(tmp_path, trusted)
    write_json(tmp_path / "manifest.json", manifest(tmp_path))
    with pytest.raises(ValueError):
        verify_package(tmp_path, trusted)
