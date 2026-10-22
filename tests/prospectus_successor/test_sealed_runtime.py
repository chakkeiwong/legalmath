"""Actual seal and malformed-input controls; live namespace/OCR is retained separately."""
from copy import deepcopy
import errno
import hashlib
import os
import sys
from pathlib import Path

import pytest

from legalmath.prospectus.successor import sealed_runtime as runtime


def captured(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"original bytes")
    source.chmod(0o755)
    folder = tmp_path / "snapshot"
    manifest = runtime.snapshot(folder, {"/case/tool": source})
    return source, folder, manifest


def test_sealed_copy_rejects_write_shrink_and_grow(tmp_path):
    source = tmp_path / "original"
    source.write_bytes(b"retained")
    with runtime.sealed_file(source, hashlib.sha256(b"retained").hexdigest(), 8) as fd:
        for mutate in (lambda: os.write(fd, b"changed!"), lambda: os.ftruncate(fd, 0),
                       lambda: os.ftruncate(fd, 9)):
            with pytest.raises(OSError) as caught:
                mutate()
            assert caught.value.errno == errno.EPERM
        source.write_bytes(b"mutated!")
        assert os.pread(fd, 8, 0) == b"retained"


def test_capture_survives_original_deletion_and_blob_mutation_after_sealing(tmp_path):
    source, folder, manifest = captured(tmp_path)
    source.unlink()
    with runtime.command(folder, manifest, ["/case/tool"]) as (argv, fds):
        (folder / "blobs" / manifest["files"][0]["sha256"]).write_bytes(b"changed")
        assert os.pread(fds[0], 100, 0) == b"original bytes"
        assert "--ro-bind" not in argv
    with pytest.raises(ValueError, match="size|hash"):
        with runtime.command(folder, manifest, ["/case/tool"]):
            pytest.fail("Changed blob was accepted")


@pytest.mark.parametrize("path", ["relative", "/", "//alias", "/a/../b", "/a//b", "/a/.",
                                 "/tmp/escape", "/dev/null", "/proc/self/root", "/x\x00y"])
def test_destination_refuses_aliases_and_dynamic_namespaces(path):
    with pytest.raises(ValueError):
        runtime.destination(path)


@pytest.mark.parametrize("case", ["duplicate", "parent-file", "hash", "size", "mode",
                                 "environment", "reuse", "directory-collision", "extra"])
def test_manifest_refuses_invalid_boundary_declarations(tmp_path, case):
    _, _, manifest = captured(tmp_path)
    bad = deepcopy(manifest)
    if case == "duplicate": bad["files"].append(deepcopy(bad["files"][0]))
    if case == "parent-file": bad["directories"] = ["/case/tool/child"]
    if case == "hash": bad["files"][0]["sha256"] = "../outside"
    if case == "size": bad["files"][0]["size"] = True
    if case == "mode": bad["files"][0]["mode"] = 0o777
    if case == "environment": bad["environment"]["LD_PRELOAD"] = "/host/library"
    if case == "reuse": bad["native_reuse_allowed"] = True
    if case == "directory-collision": bad["directories"] = ["/case/tool"]
    if case == "extra": bad["host_mount"] = "/"
    with pytest.raises(ValueError): runtime.validate(bad)


def test_symlink_and_fifo_sources_refuse_without_blocking(tmp_path):
    target = tmp_path / "target"
    target.write_bytes(b"data")
    link = tmp_path / "link"
    link.symlink_to(target)
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    for path in (link, fifo, tmp_path):
        with pytest.raises((OSError, ValueError)):
            with runtime.regular_file(path): pytest.fail("Nonregular source accepted")


def test_wrong_expected_hash_and_truncated_blob_refuse(tmp_path):
    _, folder, manifest = captured(tmp_path)
    row = manifest["files"][0]
    blob = folder / "blobs" / row["sha256"]
    with pytest.raises(ValueError, match="hash"):
        with runtime.sealed_file(blob, "0" * 64, row["size"]): pytest.fail("Wrong hash accepted")
    blob.write_bytes(b"short")
    with pytest.raises(ValueError, match="hash/size"):
        with runtime.sealed_file(blob, row["sha256"], row["size"]): pytest.fail("Truncation accepted")


def test_undeclared_executable_and_unbounded_command_refuse(tmp_path):
    _, folder, manifest = captured(tmp_path)
    with pytest.raises(ValueError, match="explicit executable"):
        with runtime.command(folder, manifest, ["/usr/bin/python"]): pytest.fail("Host executable accepted")
    for timeout in (0, 61, True):
        with pytest.raises(ValueError, match="bounds"):
            runtime.run(folder, manifest, ["/case/tool"], timeout=timeout)


def test_parent_caps_actual_child_output(monkeypatch):
    monkeypatch.setattr(runtime, 'MAX_STREAM', 1024)
    with pytest.raises(ValueError, match='stream bound'):
        runtime.capture_process([sys.executable, '-c', 'import os; os.write(1,b"x"*2048)'], (), b'', 5)


def test_early_child_failure_closes_large_stdin():
    code, out, err = runtime.capture_process([sys.executable, '-c', 'raise SystemExit(7)'], (), b'x' * 100000, 5)
    assert (code, out, err) == (7, b'', b'')


def test_explicit_capacity_does_not_change_default(monkeypatch):
    monkeypatch.setattr(runtime, 'MAX_STREAM', 1024)
    code,out,err=runtime.capture_process([sys.executable,'-c','import os;os.write(1,b"x"*2048)'],(),b'',5,max_stream=4096)
    assert (code,len(out),err)==(0,2048,b'')
    assert runtime.stream_bound()==1024


@pytest.mark.parametrize('cap',[0,-1,True,64*1024*1024+1,'large'])
def test_invalid_capacity_refuses_before_any_launch(monkeypatch,cap):
    import subprocess
    def no_launch(*args,**kwargs):pytest.fail('Invalid cap launched a process')
    monkeypatch.setattr(subprocess,'Popen',no_launch)
    with pytest.raises(ValueError,match='stream bound'):
        runtime.capture_process(['/case/none'],(),b'',5,max_stream=cap)
