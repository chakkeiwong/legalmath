from copy import deepcopy
import hashlib

import pytest
from scripts import prospectus_installed_retained_validation as check


def test_exact_bridge_refuses_any_other_change():
    before = b'def validate_submission(root, attempt, task):\n    return True\n'
    blobs = {check.prior.SCRIPT: before, "unchanged.py": b"fixed"}
    frozen = {p: hashlib.sha256(v).hexdigest() for p, v in blobs.items()}
    snapshots = {p: v.hex() for p, v in blobs.items()}
    candidate = {**frozen, check.prior.SCRIPT: hashlib.sha256(check.dispatch_candidate(before.decode()).encode()).hexdigest()}
    assert check.exact_bridge(frozen, snapshots, candidate) == frozen
    for bad in ({**candidate, "unchanged.py": "0" * 64}, {**candidate, "extra.py": "0" * 64},
                {**candidate, check.prior.SCRIPT: frozen[check.prior.SCRIPT]}):
        with pytest.raises(ValueError, match="Unreviewed|inventory"):
            check.exact_bridge(frozen, snapshots, bad)
    with pytest.raises(ValueError, match="Forged"):
        check.exact_bridge(frozen, {**snapshots, "unchanged.py": b"forged".hex()}, candidate)


def test_envelope_refuses_other_timing_failures():
    rows = [{"stage": s, "status": "PASS", "error": None, "wall_seconds": 115.07405699742958 if s == "validate" else 1} for s in check.prior.STAGES]
    check.stage_envelope(rows)
    for index, field, value in ((0, "status", "FAIL"), (0, "wall_seconds", 115.01),
                                (check.prior.STAGES.index("validate"), "wall_seconds", 116)):
        bad = deepcopy(rows); bad[index][field] = value
        with pytest.raises(ValueError, match="failed|timing"):
            check.stage_envelope(bad)
    with pytest.raises(ValueError, match="stages differ"):
        check.stage_envelope(rows[:-1])


def test_retained_selector_requires_zero_calls():
    task = {"id": "native-confinement", "validator": check.prior.prior.INSTALLED,
        "product_delta_acceptance": check.prior.SELECTOR, "retained_profile_validation": check.SELECTOR,
        "native_call_allowance": 0, "retained_acceptance_only": True}
    check.selector(task)
    for field, value in (("native_call_allowance", 1), ("retained_acceptance_only", False), ("retained_profile_validation", {})):
        with pytest.raises(ValueError, match="Unreviewed retained"):
            check.selector({**task, field: value})


def test_retained_dispatch_preserves_old_validator(tmp_path):
    with pytest.raises(ValueError, match="Unreviewed retained"):
        check.prior.validate_submission(tmp_path, tmp_path, {"retained_profile_validation": {}})
    with pytest.raises(ValueError, match="Unreviewed installed profile"):
        check.prior.validate_submission(tmp_path, tmp_path, {})
