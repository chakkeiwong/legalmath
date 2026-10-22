"""Installed live admission, real failure accounting and exact source controls."""
from copy import deepcopy
import subprocess
import pytest

from legalmath.prospectus.execution_authority import read, write, digest, file_hash
from legalmath.prospectus.successor import process_ledger
from scripts import prospectus_installed_live as driver
from scripts import prospectus_installed_live_worker as worker
from tests.prospectus.test_installed_current import installed


@pytest.fixture
def live(installed):
    a, name, folder = installed
    program, tasks, _ = a.spec(); task = tasks["native-confinement"]
    task.update(preparation_only=False, native_call_allowance=2, installed_live=deepcopy(driver.GRANT))
    row = read(folder / "admission.json")
    row.update(task_spec=task, task_sha256=digest(task), program_sha256=digest(program))
    write(folder / "admission.json", row)
    a.events()[-1]["admission_sha256"] = file_hash(folder / "admission.json")
    return a, name, folder


@pytest.mark.parametrize("change", ["none", "history", "closed", "native", "limit", "program", "input", "symlink"])
def test_installed_live_admission_refuses_before_any_launch(live, change):
    a, name, folder = live
    if change == "none":
        assert driver.admission(a, name)[0] == folder
        return
    if change == "history": name = name.replace("004", "002")
    elif change == "closed": a.events()[-1]["kind"] = "RECORD"
    elif change == "native": a.spec()[1]["native-confinement"]["native_call_allowance"] += 1
    elif change == "limit": a.spec()[1]["native-confinement"]["installed_live"]["maximum_native_reservations"] += 1
    elif change == "program": a.spec()[0]["revision"] += 1
    elif change == "input": (a.root / "input").write_text("changed")
    else: (folder / "stages").symlink_to(a.root, target_is_directory=True)
    before = sorted(str(p.relative_to(folder)) for p in folder.rglob("*"))
    with pytest.raises((ValueError, FileNotFoundError)): driver.run_stage(a, name, "prepare")
    assert sorted(str(p.relative_to(folder)) for p in folder.rglob("*")) == before


@pytest.mark.parametrize("error", [ValueError("actual failure"), TimeoutError("stage bound"), KeyboardInterrupt("cancel")])
def test_installed_live_failure_seals_real_error(live, monkeypatch, error):
    a, name, folder = live
    def fail(*args): raise error
    monkeypatch.setattr(driver, "prepare", fail)
    code, result = driver.run_stage(a, name, "prepare")
    assert code and result["error"]["message"] == str(error)
    manifest = read(folder / "outputs.json")
    assert all(file_hash(folder / n) == h for n, h in manifest.items())
    assert read(folder / "result.json")["status"] == "FAIL"
    with pytest.raises(ValueError, match="Sealed"): driver.run_stage(a, name, "prepare")


def test_installed_retained_requires_fresh_full_canary(live):
    a, name, folder = live
    for stage in ("prepare", "source-fresh", "construct-fresh", "finish-fresh"):
        write(folder / "stages" / stage / "result.json", {"status": "PASS"})
    with pytest.raises(ValueError, match="verify-fresh"): driver.run_stage(a, name, "source-retained")
    assert not (folder / "stages/source-retained").exists()


def test_installed_native_failed_spawn_is_counted_and_extra_refused(tmp_path, monkeypatch):
    ledger = tmp_path / "native.json"; process_ledger.create(ledger, 4, 4, "test")
    calls = []
    def failed(*args, **kwargs):
        calls.append(1)
        raise FileNotFoundError("actual spawn failure")
    monkeypatch.setattr(subprocess, "Popen", failed)
    with pytest.raises(ValueError, match="Missing, failed or extra"):
        with worker.native_calls(ledger, 1):
            with pytest.raises(FileNotFoundError): subprocess.Popen(["first"])
            with pytest.raises(ValueError, match="allowance exhausted"): subprocess.Popen(["second"])
    rows = process_ledger.checked(ledger)["reservations"]
    assert len(calls) == len(rows) == 1 and rows[0]["state"] == "SPAWN_FAILED"


def test_installed_native_missing_call_refuses(tmp_path):
    ledger = tmp_path / "native.json"; process_ledger.create(ledger, 4, 4, "test")
    with pytest.raises(ValueError, match="Missing"):
        with worker.native_calls(ledger, 2): pass


@pytest.mark.parametrize("mode", ["fresh", "retained"])
def test_installed_source_comparison_only_allows_verified_receipts(mode):
    old = {"documents": [{"native_extraction": {"sealed_execution": {"old": 1}, "xml": "unchanged"},
        "runtime": {"sealed_execution": {"old": 2}},
        "ocr_extraction": {"runtime": {"sealed_execution": {"old": 2}}, "ocr_sha256": "old-hash"},
        "image_verification": {"verification_runtime": {"sealed_execution": {"old": 3}}},
        "unknown": "PENDING"}], "units": [{"raw": "a  b"}]}
    new = deepcopy(old); receipts = [{"actual": 1}, {"actual": 2}]
    new["documents"][0]["native_extraction"]["sealed_execution"] = receipts[0]
    target = new["documents"][0]["runtime"] if mode == "fresh" else new["documents"][0]["image_verification"]["verification_runtime"]
    target["sealed_execution"] = receipts[1]
    if mode == "fresh":
        new["documents"][0]["ocr_extraction"]["runtime"]["sealed_execution"] = receipts[1]
        new["documents"][0]["ocr_extraction"]["ocr_sha256"] = "new-hash"
    hashes = ("new-hash", "old-hash") if mode == "fresh" else None
    driver.compare_source_graph(new, old, mode, receipts, hashes)
    changed = deepcopy(new); changed["units"][0]["raw"] = "a b"
    with pytest.raises(ValueError, match="beyond checked receipts"): driver.compare_source_graph(changed, old, mode, receipts, hashes)
    changed = deepcopy(new); changed["documents"][0]["unknown"] = "RESOLVED"
    with pytest.raises(ValueError, match="beyond checked receipts"): driver.compare_source_graph(changed, old, mode, receipts, hashes)
    with pytest.raises(ValueError, match="receipt not delivered"): driver.compare_source_graph(new, old, mode, [{"forged": 1}, receipts[1]], hashes)


def test_installed_live_missing_matrix_refuses(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, "check_methods", lambda *a: {})
    with pytest.raises(FileNotFoundError): driver.validate(tmp_path, tmp_path)


def test_installed_live_offline_guard_detects_caught_attempt():
    with pytest.raises(ValueError, match="caught offline"):
        with driver.offline():
            with pytest.raises(RuntimeError): subprocess.Popen(["forbidden"])


def test_installed_product_binding_uses_product_hash_domain_and_refuses_wrong_parent(tmp_path):
    product = driver.native_profile
    request = {"version": "fixture", "bundle": {"language": "Português", "instrument_id": "BES"}}
    profile = {"version": "fixture", "repository": str(tmp_path)}
    p1 = product.service.seal("P1", request["bundle"], {"request": product.digest(request)}, {"request": request, "graph": {}})
    execution = {"profile": str(tmp_path), "profile_sha256": product.digest(profile),
        "request_sha256": product.digest(request), "native_reuse_allowed": False}
    assert digest(request) != product.digest(request)
    driver.product_bindings(p1, request, execution, profile, tmp_path)
    bad = product.service.seal("P1", request["bundle"], {"request": digest(request)}, {"request": request, "graph": {}})
    with pytest.raises(ValueError, match="parent bindings"): driver.product_bindings(bad, request, execution, profile, tmp_path)
    for key in ("profile_sha256", "request_sha256"):
        wrong = deepcopy(execution); wrong[key] = digest(profile if key == "profile_sha256" else request)
        with pytest.raises(ValueError, match="profile selection"): driver.product_bindings(p1, request, wrong, profile, tmp_path)


def test_real_installed005_source_and_complete_ocr_provenance_without_new_calls():
    root = driver.ROOT
    folder = root / "docs/implementation/prospectus-execution-authority/attempts/native-confinement/attempt-005"
    before = process_ledger.checked(folder / "native-ledger.json")
    with driver.offline():
        result = driver.source_evidence(root, folder, "fresh")
    assert result["complete_source_equal_except_validated_receipts"] and result["complete_native_streams_equal"]
    assert before == process_ledger.checked(folder / "native-ledger.json")
    prior, _ = driver.prepared(root, folder)
    manifest = read(prior / "profile/snapshot/manifest.json")
    receipt = read(folder / "fresh/native/1/receipt.json")
    stdout = (folder / "fresh/native/1/stdout").read_bytes()
    doc = driver.helper.read(folder / "fresh/P1.json.gz")["payload"]["graph"]["documents"][0]
    driver.checked_fresh_ocr(doc, stdout, receipt, manifest)
    wrong = deepcopy(doc); wrong["ocr_extraction"]["ocr_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="complete OCR hash"): driver.checked_fresh_ocr(wrong, stdout, receipt, manifest)
    wrong = deepcopy(doc); wrong["ocr_extraction"]["runtime"]["gpu"] = "invented"
    with pytest.raises(ValueError, match="runtime differs"): driver.checked_fresh_ocr(wrong, stdout, receipt, manifest)
