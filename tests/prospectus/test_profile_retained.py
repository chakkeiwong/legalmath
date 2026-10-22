from copy import deepcopy
import hashlib
import pytest
from scripts import prospectus_profile_retained as c


def test_current_retained_exact_bridge():
    blobs = {c.prior.SCRIPT: b'def validate_submission(root, attempt, task):\n    return False\n', "fixed": b"same"}
    frozen = {p: hashlib.sha256(b).hexdigest() for p, b in blobs.items()}
    snapshots = {p: b.hex() for p, b in blobs.items()}
    current = {**frozen, c.prior.SCRIPT: hashlib.sha256(c.dispatch_candidate(blobs[c.prior.SCRIPT].decode()).encode()).hexdigest()}
    assert c.exact_bridge(frozen, snapshots, current) == frozen
    for bad in ({**current, "fixed": "0" * 64}, frozen, {**current, "extra": "0" * 64}):
        with pytest.raises(ValueError, match="Unreviewed|inventory"):
            c.exact_bridge(frozen, snapshots, bad)
    with pytest.raises(ValueError, match="Forged"):
        c.exact_bridge(frozen, {**snapshots, "fixed": b"changed".hex()}, current)


def test_current_retained_exact_timeout_envelope():
    rows = [{"stage": s, "status": "PASS", "error": None, "wall_seconds": 1} for s in c.prior.STAGES[:-1]]
    rows[-1].update(status="FAIL", error={"type": "TimeoutError", "message": "Current native preparation stage exceeded its time bound"}, wall_seconds=111.0746665536426)
    c.stage_envelope(rows)
    for i, k, v in ((0, "status", "FAIL"), (0, "wall_seconds", 116), (-1, "status", "PASS"),
                    (-1, "error", {"type": "ValueError", "message": "wrong"}), (-1, "wall_seconds", 112)):
        bad = deepcopy(rows); bad[i][k] = v
        with pytest.raises(ValueError): c.stage_envelope(bad)
    with pytest.raises(ValueError): c.stage_envelope(rows[:-1])


def test_current_retained_selector_zero_calls():
    task = {"id": "native-confinement", "validator": c.prior.prior.INSTALLED,
        "annual_profile_compatibility": c.prior.SELECTOR, "retained_current_profile": c.SELECTOR,
        "native_call_allowance": 0, "retained_acceptance_only": True}
    c.selector(task)
    for k, v in (("native_call_allowance", 1), ("retained_acceptance_only", False), ("retained_current_profile", {})):
        with pytest.raises(ValueError, match="zero-call"): c.selector({**task, k: v})


def test_current_retained_dispatch_preserves_fallback(tmp_path):
    before = (c.ROOT / c.REVIEW / "dispatch-before.py").read_text()
    assert (c.ROOT / c.prior.SCRIPT).read_text() == c.dispatch_candidate(before)
    with pytest.raises(ValueError, match="zero-call"):
        c.prior.validate_submission(tmp_path, tmp_path, {"retained_current_profile": {}})
    with pytest.raises(ValueError, match="Unreviewed installed profile"):
        c.prior.validate_submission(tmp_path, tmp_path, {})
