"""Adverse checks for the exact registration bridge and current evidence."""
from copy import deepcopy
import hashlib
from pathlib import Path
import types
import pytest

from legalmath.prospectus.execution_authority import read, write, file_hash
from scripts import prospectus_current_acceptance as check
from tests.prospectus.test_installed_live import test_installed_product_binding_uses_product_hash_domain_and_refuses_wrong_parent


def baseline():
    root = Path(__file__).resolve().parents[2]
    path = root / check.PATCH_ATTEMPT / "registry-before.py"
    return path.read_text() if path.exists() else (root / check.REGISTRY).read_text()


def test_registry_only_delta_rejects_unrelated_edits():
    before = baseline(); after = check.registry_candidate(before)
    assert check.registration_only(before, after)
    assert check.registration_only(before, before)
    assert not check.registration_only(before, after.replace("return False", "return True"))
    assert not check.registration_only(before, after + "\n# unrelated edit\n")
    assert not check.registration_only(before, before.replace("import ast", "import os"))


def test_bridge_refuses_product_change_or_forged_snapshot(tmp_path):
    names = {check.REGISTRY: baseline(), "src/product.py": "exact product bytes\n"}
    hashes = {n: hashlib.sha256(v.encode()).hexdigest() for n, v in names.items()}
    snapshots = {n: v.encode().hex() for n, v in names.items()}
    for name, value in names.items():
        path = tmp_path / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(value)
    (tmp_path / check.REGISTRY).write_text(check.registry_candidate(names[check.REGISTRY]))
    current = {n: file_hash(tmp_path / n) for n in names}
    assert check.method_bridge(tmp_path, hashes, snapshots, current, hex_encoded=True) == [check.REGISTRY]
    changed = dict(current); changed["src/product.py"] = "0" * 64
    with pytest.raises(ValueError, match="Unreviewed current method"): check.method_bridge(tmp_path, hashes, snapshots, changed, hex_encoded=True)
    forged = dict(snapshots); forged["src/product.py"] = b"forged".hex()
    with pytest.raises(ValueError, match="snapshot hash"): check.method_bridge(tmp_path, hashes, forged, current, hex_encoded=True)
    extra = dict(current); extra["src/new.py"] = "0" * 64
    with pytest.raises(ValueError, match="inventory"): check.method_bridge(tmp_path, hashes, snapshots, extra, hex_encoded=True)


def test_new_registry_dispatches_real_validator(tmp_path):
    candidate = check.registry_candidate(baseline())
    module = types.ModuleType("legalmath.prospectus.candidate_registry")
    module.__package__ = "legalmath.prospectus"
    exec(compile(candidate, "candidate_registry", "exec"), module.__dict__)
    for version, task_id in ((check.NATIVE, "native-binding"), (check.INSTALLED, "native-confinement")):
        task = {"id": task_id, "handler": "agent", "stream": "engineering", "validator": version}
        with pytest.raises(ValueError, match="Explicit zero-call"): module.validate(tmp_path, tmp_path, task)
        task["id"] = "unrelated"
        with pytest.raises(ValueError, match="unknown or outside"): module.check_task(task)
    assert module.VALIDATORS["native-current-files.v2"] == "native-binding"
    assert module.VALIDATORS["native-installed-profile.v1"] == "native-confinement"


def test_missing_retained_evidence_cannot_be_pass(tmp_path):
    for validator in (check.native_evidence, check.installed_evidence):
        with pytest.raises((ValueError, FileNotFoundError)): validator(tmp_path)


def test_reconstructed_ocr_and_product_hash_regressions_remain_active(tmp_path):
    test_installed_product_binding_uses_product_hash_domain_and_refuses_wrong_parent(tmp_path)
    from tests.prospectus.test_installed_live import test_real_installed005_source_and_complete_ocr_provenance_without_new_calls
    root = Path(__file__).resolve().parents[2]
    # The real-source regression uses the old exact-method preparation validator.
    # After registration, the dedicated acceptance bridge checks that delta;
    # the same OCR/content comparator remains unchanged and directly tested.
    before = baseline(); current = (root / check.REGISTRY).read_text()
    if before == current:
        test_real_installed005_source_and_complete_ocr_provenance_without_new_calls()
    else:
        assert check.registration_only(before, current)
        folder = root / check.BASE / "attempts/native-confinement/attempt-005"
        prep = root / check.BASE / "attempts/native-confinement/attempt-004"
        doc = check.helper.read(folder / "fresh/P1.json.gz")["payload"]["graph"]["documents"][0]
        stdout = (folder / "fresh/native/1/stdout").read_bytes(); receipt = read(folder / "fresh/native/1/receipt.json")
        manifest = read(prep / "profile/snapshot/manifest.json")
        check.live.checked_fresh_ocr(doc, stdout, receipt, manifest)
        changed = deepcopy(doc); changed["ocr_extraction"]["ocr_sha256"] = "0" * 64
        with pytest.raises(ValueError, match="OCR hash"): check.live.checked_fresh_ocr(changed, stdout, receipt, manifest)


def test_retained_stage_hashes_refuse_rehashed_missing_outputs(tmp_path):
    write(tmp_path / "stages/source/result.json", {"status": "PASS", "files": {"missing": "0" * 64}})
    with pytest.raises(FileNotFoundError): check.product.checked_stage(tmp_path, "source")
    write(tmp_path / "stages/prepare/result.json", {"status": "PASS", "wall_seconds": 121})
    with pytest.raises(ValueError, match="Failed or missing"): check.checked_stages(tmp_path, ("prepare",))
