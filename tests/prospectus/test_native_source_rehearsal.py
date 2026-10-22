"""Real runtime dispatch against immutable recorded-byte fixtures."""
from copy import deepcopy
import hashlib
import os
import subprocess

import pytest

from legalmath.prospectus import native_source_rehearsal as source
from legalmath.prospectus.execution_authority import read, write, file_hash
from legalmath.prospectus.successor import sealed_runtime as runtime, sealed_source
from scripts import prospectus_native_source_rehearsal as driver
from tests.prospectus.test_native_current_preparation import admitted, manifest


@pytest.fixture
def recorded(tmp_path):
    hashed = hashlib.sha256(b"abc").hexdigest()
    manifest0 = {"version": runtime.VERSION, "files": [{"path": "/worker", "mode": 0o555,
        "size": 3, "sha256": hashed}], "directories": [], "environment": dict(runtime.ENVIRONMENT),
        "native_reuse_allowed": False}
    write(tmp_path / "snapshot/manifest.json", manifest0)
    calls = []
    for index in range(2):
        name = "calls/" + str(index)
        folder = tmp_path / name
        folder.mkdir(parents=True)
        streams = {"stdin": ("input-" + str(index)).encode(), "stdout": ("output-" + str(index)).encode(), "stderr": b""}
        for key, value in streams.items(): (folder / key).write_bytes(value)
        refs = {k: {"sha256": hashlib.sha256(v).hexdigest(), "bytes": len(v)} for k, v in streams.items()}
        receipt = {"version": "sealed-native-execution.v2", "argv": ["/worker", str(index)], "returncode": 0,
            "manifest_sha256": runtime.digest(manifest0), **refs, "trusted_runtime": runtime.trusted_runtime(),
            "limits": {"max_stream_bytes": 20 * 1024 * 1024}, "native_reuse_allowed": False,
            "file_namespace": "sealed explicit files; private proc/dev/tmp; no host directory mounts"}
        receipt["receipt_sha256"] = runtime.digest(receipt)
        write(folder / "receipt.json", receipt)
        calls.append({"folder": name, "record": receipt, "streams": refs})
    row = {"route": "2009-fresh", "manifest": "snapshot/manifest.json", "calls": calls}
    candidate = sealed_source.SourceRuntime(tmp_path / "snapshot", runtime.digest(manifest0))
    return tmp_path, row, candidate, {"/worker": hashed}


def deliver(candidate, required, index):
    return candidate.execute(["/worker", str(index)], ("input-" + str(index)).encode(), required)


def test_actual_source_runtime_executes_recorded_boundary(recorded):
    root, row, candidate, required = recorded
    boundary = source.RecordedBoundary(root, row)
    previous = (subprocess.run, runtime.run)
    with boundary.installed():
        first, second = deliver(candidate, required, 0), deliver(candidate, required, 1)
    assert first["stdout"] == b"output-0" and second["stdout"] == b"output-1"
    assert candidate.receipts == [r["record"] for r in row["calls"]]
    assert (subprocess.run, runtime.run) == previous
    proof = boundary.complete()
    assert proof["native_processes"] == 0 and len(proof["deliveries"]) == 2
    assert all(r["kind"] == "RECORDED_BYTES_ONLY" for r in proof["deliveries"])


@pytest.mark.parametrize("change", ["argv", "stdin", "stream", "receipt", "bound", "manifest", "runtime", "required-hash"])
def test_recorded_boundary_refuses_changed_dispatch(recorded, change):
    root, row, candidate, required = recorded
    argv, stdin, kwargs = ["/worker", "0"], b"input-0", {}
    if change == "argv": argv[1] = "different"
    elif change == "stdin": stdin += b" "
    elif change == "stream": (root / "calls/0/stdout").write_bytes(b"changed")
    elif change == "receipt":
        receipt = read(root / "calls/0/receipt.json")
        receipt["returncode"] = 1
        write(root / "calls/0/receipt.json", receipt)
    elif change == "bound": kwargs["max_stream"] = 64 * 1024 * 1024
    elif change == "manifest": candidate.manifest["files"][0]["size"] += 1
    elif change == "runtime":
        receipt = row["calls"][0]["record"]
        receipt["trusted_runtime"]["kernel_release"] = "different recorded kernel"
        receipt["receipt_sha256"] = runtime.digest({k: v for k, v in receipt.items() if k != "receipt_sha256"})
        write(root / "calls/0/receipt.json", receipt)
    else: required["/worker"] = "0" * 64
    boundary = source.RecordedBoundary(root, row)
    with boundary.installed(), pytest.raises(ValueError):
        candidate.execute(argv, stdin, required, **kwargs)
    assert not boundary.deliveries


@pytest.mark.parametrize("extra", [False, True])
def test_missing_or_extra_recorded_calls_refuse(recorded, extra):
    root, row, candidate, required = recorded
    boundary = source.RecordedBoundary(root, row)
    with boundary.installed():
        deliver(candidate, required, 0)
        if extra:
            deliver(candidate, required, 1)
            with pytest.raises(ValueError, match="additional"):
                deliver(candidate, required, 1)
    with pytest.raises(ValueError, match="Missing, extra or refused"):
        boundary.complete()


def test_recorded_boundary_restores_after_failure(recorded):
    root, row, candidate, required = recorded
    boundary = source.RecordedBoundary(root, row)
    previous = (subprocess.run, runtime.run)
    with pytest.raises(ValueError), boundary.installed():
        candidate.execute(["/worker", "wrong"], b"input-0", required)
    assert (subprocess.run, runtime.run) == previous


def test_default_boundary_preserves_timeout_clamp_and_text(recorded):
    root, row, _, _ = recorded
    row["route"] = "2009-default"
    for call in row["calls"]:
        call["record"] = {"argv": call["record"]["argv"], "timeout": 60,
            "environment": {k: os.environ.get(k) for k in ("CUDA_VISIBLE_DEVICES", "OMP_THREAD_LIMIT", "LANG")}}
        write(root / call["folder"] / "command.json", call["record"])
        write(root / call["folder"] / "result.json", {"returncode": 0})
    boundary = source.RecordedBoundary(root, row)
    with boundary.installed():
        first = subprocess.run(["/worker", "0"], input="input-0", text=True, capture_output=True, timeout=90)
        second = subprocess.run(["/worker", "1"], input=b"input-1", capture_output=True, timeout=90)
    assert first.stdout == "output-0" and second.stdout == b"output-1"
    assert boundary.complete()["deliveries"][0]["recorded_timeout"] == 60


def test_rehearsal_driver_retains_source_failure(admitted, monkeypatch):
    authority, name, folder = admitted
    def fail(*args):
        raise ValueError("source request differs")
    monkeypatch.setattr(driver, "prepare", fail)
    code, result = driver.run_stage(authority, name, "prepare")
    assert code == 1 and result["error"]["message"] == "source request differs"
    assert manifest(folder)["fresh_native_execution_established"] is False


def test_rehearsal_rejects_fresh_stage(admitted):
    authority, name, folder = admitted
    before = {str(p.relative_to(folder)): file_hash(p) for p in folder.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="Fresh native"):
        driver.run_stage(authority, name, "source-2009-fresh")
    assert before == {str(p.relative_to(folder)): file_hash(p) for p in folder.rglob("*") if p.is_file()}
