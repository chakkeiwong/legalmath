"""Current compatibility must preserve old behavior, exact deltas and all routes."""
import ast
from copy import deepcopy
import hashlib
import types

import pytest
from legalmath.prospectus.execution_authority import write
from scripts import prospectus_profile_delta as check


def test_annual_shape_protects_old_profiles_and_functions():
    old = '"""Old."""\nPROFILES = {"old": {"source": "old"}}\ndef admit(x): return x\ndef explain(x): return x\n'
    a, b = check.PROFILE_KEYS
    new = old.replace('"Old."', '"New."').replace('"source": "old"}}',
        '"source": "old"}, "' + a + '": {"pages": (1, 2)}, "' + b + '": {"pages": (1, 2, 3)}}')
    new = new.replace('def explain(x): return x', 'def explain(x): return {"reading": x}')
    explanation = ast.dump(ast.parse(new).body[-1], include_attributes=False)
    profiles = {a: {"pages": [1, 2]}, b: {"pages": [1, 2, 3]}}
    check.annual_shape(old, new, profiles, explanation)
    for bad in (new.replace('"source": "old"', '"source": "forged"'),
                new.replace('def admit(x): return x', 'def admit(x): return None'),
                new.replace('(1, 2, 3)', '(1, 2, 4)'),
                new.replace('"reading": x', '"reading": None'),
                new.replace('"old":', '"extra": {}, "old":')):
        with pytest.raises(ValueError, match="profile|implementation|explanation"):
            check.annual_shape(old, bad, profiles, explanation)


def test_method_bridge_refuses_repinning_and_inventory_changes():
    sha = lambda b: hashlib.sha256(b).hexdigest()
    frozen = {"fixed": sha(b"same"), "changed": sha(b"before")}
    snapshots = {"fixed": b"same".hex(), "changed": b"before".hex()}
    current = {"fixed": sha(b"same"), "changed": sha(b"after"), "addition": sha(b"new")}
    changes = {"changed": {"before": frozen["changed"], "after": current["changed"]}}
    added = {"addition": current["addition"]}
    assert check.method_bridge(frozen, snapshots, current, changes, added) == ["changed"]
    for bad in ({**current, "fixed": sha(b"other")}, {**current, "addition": sha(b"forged")},
                {**current, "another": sha(b"new")}, {k: v for k, v in current.items() if k != "fixed"}):
        with pytest.raises(ValueError): check.method_bridge(frozen, snapshots, bad, changes, added)
    with pytest.raises(ValueError, match="Forged"):
        check.method_bridge(frozen, {**snapshots, "changed": b"false".hex()}, current, changes, added)


def test_package_delta_refuses_unreviewed_modules():
    cells = check.CELLS.removeprefix("src/legalmath/")
    before = {cells: "before", "fixed.py": "same"}
    after = {cells: "after", "fixed.py": "same", "new.py": "new"}
    check.package_delta(before, after, {"new.py": "new"}, {"before": "before", "after": "after"})
    for bad in ({**after, "fixed.py": "changed"}, {**after, "extra.py": "unreviewed"},
                {**after, "new.py": "changed"}, {cells: "after", "new.py": "new"}):
        with pytest.raises(ValueError):
            check.package_delta(before, bad, {"new.py": "new"}, {"before": "before", "after": "after"})


def test_native_dispatch_preserves_fallback_and_enforces_selector(monkeypatch):
    before = 'def validate_submission(root, attempt, task):\n    return "old-strict-path"\n'
    after = check.dispatch_candidate(before)
    candidate = types.ModuleType("candidate_profile_dispatch")
    exec(compile(after, "candidate_profile_dispatch", "exec"), candidate.__dict__)
    assert candidate.validate_submission(None, None, {}) == "old-strict-path"
    calls = []
    def selected(root, attempt, task):
        check.selector(task)
        calls.append(task["id"])
        return "native"
    monkeypatch.setattr(check, "validate_submission", selected)
    native = {"id": "native-binding", "validator": check.prior.NATIVE,
        "product_delta_acceptance": deepcopy(check.old.SELECTOR),
        "annual_profile_compatibility": deepcopy(check.SELECTOR),
        "native_call_allowance": 0, "retained_acceptance_only": True}
    assert candidate.validate_submission(None, None, native) == "native"
    assert calls == ["native-binding"]
    for bad in ({"annual_profile_compatibility": {}}, {**native, "id": "recovery"},
                {**native, "id": "native-confinement"},
                {**native, "annual_profile_compatibility": None},
                {**native, "annual_profile_compatibility": {"version": "unknown"}}):
        with pytest.raises(ValueError, match="Unreviewed annual-profile"):
            candidate.validate_submission(None, None, bad)
    assert calls == ["native-binding"]


def test_selector_refuses_other_scope_or_allowance():
    task = {"id": "native-binding", "validator": check.prior.NATIVE,
        "product_delta_acceptance": deepcopy(check.old.SELECTOR),
        "annual_profile_compatibility": deepcopy(check.SELECTOR), "native_call_allowance": 0,
        "retained_acceptance_only": True}
    check.selector(task)
    for key, value in (("id", "recovery"), ("native_call_allowance", 1),
                       ("retained_acceptance_only", False), ("annual_profile_compatibility", {}),
                       ("product_delta_acceptance", {})):
        with pytest.raises(ValueError, match="Unreviewed"):
            check.selector({**task, key: value})


def test_all_five_routes_are_required(tmp_path):
    for name in check.STAGES:
        if name != "replay-2010-retained":
            write(tmp_path / "stages" / name / "result.json", {"stage": name, "status": "PASS", "wall_seconds": 1})
    with pytest.raises(ValueError, match="Missing or additional"):
        check.checked_stages(tmp_path)
    write(tmp_path / "stages/replay-2010-retained/result.json",
        {"stage": "replay-2010-retained", "status": "PASS", "wall_seconds": 1})
    assert len(check.checked_stages(tmp_path)) == 9
