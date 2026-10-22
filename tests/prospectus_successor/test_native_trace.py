"""Trace accounting cannot turn ambiguous syntax into native reuse evidence."""
import pytest

from legalmath.prospectus.successor.native_trace import account
from legalmath.prospectus.successor.contracts import digest


def one(body):
    return account(("15 " + body + "\n").encode())["events"][0]


def test_descriptor_empty_path_retains_object_metadata():
    row = one('newfstatat(3</lib/test.so>, "", {st_mode=S_IFREG|0644, st_size=42, ...}, AT_EMPTY_PATH) = 0')
    assert row["path"] == "/lib/test.so"
    assert row["path_argument"] == ""
    assert row["path_role"] == "descriptor_object"
    assert row["observed_type"] == "S_IFREG"
    assert row["operation"] == "metadata"
    assert row["status"] == "PATH_OPERATION_SUCCEEDED"


@pytest.mark.parametrize("base", ["AT_FDCWD</path/to/link>", "3</path/to/link>"])
def test_relative_path_uses_decoded_base_without_normalizing_symlinks(base):
    row = one(f'openat({base}, "../target", O_RDONLY|O_CLOEXEC) = 4</path/to/target>')
    assert row["path"] == "/path/to/link/../target"
    assert row["path_role"] == "relative_to_decoded_base"
    assert row["operation"] == "open"


def test_errno_is_not_content_or_absence_evidence():
    row = one('readlink("/plain/file", 0xabcd, 4096) = -1 EINVAL (Invalid argument)')
    assert row["status"] == "PATH_OPERATION_FAILED"
    assert row["errno"] == "EINVAL" and row["path"] == "/plain/file"
    absent = one('access("/missing/component/file", R_OK) = -1 ENOENT (No such file or directory)')
    assert absent["status"] == "PATH_OPERATION_ENOENT"
    denied = one('openat(AT_FDCWD, "/restricted/file", O_RDONLY) = -1 EACCES (Permission denied)')
    assert denied["status"] == "PATH_OPERATION_FAILED"


def test_readlink_target_is_separate_from_input_path():
    row = one('readlink("/proc/self/exe", "/bin/python", 4096) = 11')
    assert row["path"] == "/proc/self/exe"
    assert row["reported_link_target"] == "/bin/python"
    assert row["dynamic_namespace"] is True


def test_truncated_return_buffer_cannot_be_presented_as_whole_target():
    row = one('readlink("/link", "/some/ta"..., 8) = 8')
    assert row["path"] == "/link"
    assert row["reported_link_target"] is None
    assert row["link_target_issue"]


@pytest.mark.parametrize("body", [
    'openat(AT_FDCWD, "relative", O_RDONLY) = 3',
    'stat("relative", {st_mode=S_IFREG|0644}) = 0',
    'newfstatat(3</x>, "", {st_mode=S_IFREG|0644}, 0) = 0',
    'newfstatat(3, "", {st_mode=S_IFREG|0644}, AT_EMPTY_PATH) = 0',
    'newfstatat(3</x (deleted)>, "", {}, AT_EMPTY_PATH) = 0',
    'openat(3<socket:[321]>, "relative", O_RDONLY) = 3',
    'stat("/long/path"..., {}) = 0',
    'stat("/bad\\qpath", {}) = 0',
    'stat("/nul\\0path", {}) = 0',
    'stat("/path", {}) = -1',
    'stat("/path", {}) = 0 ENOENT (No such file)',
    'stat("/path", {}, extra) = 0',
    'unknown_call(42) = 0',
    'openat(AT_FDCWD, "/path", O_RDONLY <unfinished ...>',
    '<... openat resumed>) = 3',
    '--- SIGINT {si_signo=SIGINT} ---',
    'stat("/path", {broken) = 0',
])
def test_unsupported_or_ambiguous_records_stay_unresolved(body):
    row = one(body)
    assert row["status"] == "UNRESOLVED"
    assert row["path"] is None and row["reason"]


def test_quoted_delimiters_and_c_escapes_keep_exact_path():
    row = one(r'stat("/tmp/a,[]()\"b\\c\040d", {st_mode=S_IFDIR|0755}) = 0')
    assert row["path"] == '/tmp/a,[]()"b\\c d'
    assert row["observed_type"] == "S_IFDIR"


def test_all_lines_retained_including_non_file_process_and_unresolved():
    raw = b'15 exit_group(0) = ?\n15 +++ exited with 0 +++\n\nunknown raw\n'
    result = account(raw, digest(raw))
    assert result["line_count"] == 4
    assert [r["raw"] for r in result["events"]] == raw.decode().splitlines()
    assert [r["line"] for r in result["events"]] == [1, 2, 3, 4]
    assert result["counts"] == {"PROCESS_EVENT": 2, "UNRESOLVED": 2}
    assert result["native_reuse_allowed"] is False
    assert result["complete_native_closure"] is False
    with pytest.raises(ValueError, match="Trace bytes changed"):
        account(raw + b"x", digest(raw))


def test_parser_does_not_query_live_filesystem(monkeypatch):
    from pathlib import Path
    def refuse(*args, **kwargs):
        raise AssertionError("No current filesystem query is allowed")
    for name in ("stat", "resolve", "open"):
        monkeypatch.setattr(Path, name, refuse)
    assert one('stat("/fictional", {st_mode=S_IFREG|0644}) = 0')["path"] == "/fictional"


def test_optional_bracketed_pid_and_direct_exec_arguments():
    raw = b'[pid 27] execve("/bin/python", ["python", "argument"], 0x1234 /* 5 vars */) = 0\n'
    row, = account(raw)["events"]
    assert row["pid"] == 27 and row["path"] == "/bin/python"
    assert row["operation"] == "execute"
