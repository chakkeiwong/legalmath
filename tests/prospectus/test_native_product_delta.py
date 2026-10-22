"""Refusals for exact reviewed product changes and complete native route evidence."""
from copy import deepcopy
import hashlib
from pathlib import Path
import types

import pytest
from legalmath.prospectus.execution_authority import write
from scripts import prospectus_native_product_delta as check


def test_exact_delta_rejects_unreviewed_bytes():
    old = {"service.py": b"old", "fixed.py": b"fixed"}
    new = {**old, "service.py": b"reviewed"}
    approval = {"service.py": {"before": hashlib.sha256(b"old").hexdigest(),
                              "after": hashlib.sha256(b"reviewed").hexdigest()}}
    assert check.exact_delta(old, new, approval) == ["service.py"]
    for bad in ({**new, "service.py": b"unreviewed"}, {**new, "fixed.py": b"changed"},
                {**new, "extra.py": b"new"}):
        with pytest.raises(ValueError, match="Unreviewed exact|Unexpected changed|inventory"):
            check.exact_delta(old, bad, approval)
    with pytest.raises(ValueError, match="Unreviewed exact"):
        check.exact_delta({**old, "service.py": b"forged"}, new, approval)


def test_fy_delta_rejects_extra_profile_or_changed_old_entry():
    old = '"""Old description."""\nPROFILES = {"old": {"value": 1}}\ndef use(): return PROFILES\n'
    candidate = old.replace('"value": 1}}', '"value": 1}, "bes-fy2010-statement-cells.v1": {"pages": (41, 42), "source": "pin"}}')
    profile = {"pages": [41, 42], "source": "pin"}
    check.cells_shape(old, candidate.replace("Old description", "Updated description"), profile)
    for bad in (candidate.replace('"value": 1', '"value": 2'), candidate.replace('"source": "pin"', '"source": "changed"'),
                candidate.replace('"old":', '"extra": {}, "old":'), candidate.replace("return PROFILES", "return {}")):
        with pytest.raises(ValueError, match="profile|implementation"):
            check.cells_shape(old, bad, profile)


def test_service_shape_rejects_globals_and_other_functions():
    old = "SETTING = 1\ndef interpretation_product(): return 0\ndef consume(): return 0\ndef seal(): return 0\n"
    candidate = old.replace("def consume(): return 0", "def consume(): return 1") + "def _bound_report_readings(): return 1\n"
    check.service_shape(old, candidate)
    for bad in (candidate.replace("SETTING = 1", "SETTING = 2"), candidate.replace("def seal(): return 0", "def seal(): return 1")):
        with pytest.raises(ValueError, match="globals or other functions"):
            check.service_shape(old, bad)


def test_dispatch_preserves_old_validator_and_refuses_unknown_selector(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    before = (root / check.REVIEW / "acceptance-before.py").read_text()
    after = check.dispatch_candidate(before)
    assert (root / check.prior.SCRIPT).read_text() == after
    module = types.ModuleType("candidate_acceptance")
    exec(compile(after, "candidate_acceptance", "exec"), module.__dict__)
    # Absent selector follows the unchanged strict old function, including its first refusal.
    with pytest.raises(ValueError, match="Explicit zero-call"):
        module.validate_submission(tmp_path, tmp_path, {})
    for selector in ({}, {**check.SELECTOR, "new_native_calls": 1}):
        with pytest.raises(ValueError, match="Unreviewed product-delta selector"):
            module.validate_submission(tmp_path, tmp_path, {"product_delta_acceptance": selector})
    with pytest.raises(ValueError, match="Unreviewed installed profile selector"):
        module.validate_submission(tmp_path, tmp_path, {"id": "native-confinement", "product_delta_acceptance": {}})
    called = []
    monkeypatch.setattr(check, "validate_submission", lambda *args: called.append(args) or True)
    task = {"product_delta_acceptance": deepcopy(check.SELECTOR)}
    assert module.validate_submission(tmp_path, tmp_path, task) is True
    assert called == [(tmp_path, tmp_path, task)]
    # Byte-for-byte reconstruction proves the whole old validator remains intact.
    branch = ('    if "product_delta_acceptance" in task:\n'
              '        if task.get("id") == "native-confinement":\n'
              '            from scripts.prospectus_installed_profile_refresh import validate_submission as validate_installed\n'
              '            return validate_installed(root, attempt, task)\n'
              '        from scripts.prospectus_native_product_delta import validate_submission as validate_delta\n'
              '        return validate_delta(root, attempt, task)\n')
    assert after.replace(branch, "", 1) == before


def test_missing_route_cannot_validate(tmp_path):
    for stage in check.STAGES:
        if stage != "replay-2010-retained":
            write(tmp_path / "stages" / stage / "result.json", {"stage": stage, "status": "PASS", "wall_seconds": 1})
    with pytest.raises(ValueError, match="Missing or additional"):
        check.checked_stages(tmp_path)
    write(tmp_path / "stages/replay-2010-retained/result.json", {"stage": "replay-2010-retained", "status": "PASS", "wall_seconds": 1})
    assert len(check.checked_stages(tmp_path)) == len(check.STAGES)
    write(tmp_path / "stages/replay-2010-retained/result.json", {"stage": "replay-2010-retained", "status": "FAIL", "wall_seconds": 1})
    with pytest.raises(ValueError, match="Missing/failed"):
        check.checked_stages(tmp_path)
