#!/usr/bin/env python3
"""Apply guarded text edits within this checkout, /tmp and TMPDIR; no command execution.

Usage: .venv/bin/python scripts/edit_workspace_files.py /tmp/edits.json
Spec: {"edits": [{"path": "relative/or/absolute", "old": "exact text", "new": "replacement"}]}
For a new file use {"path": "...", "content": "...", "before_sha256": null}.
To replace a complete existing file supply its current before_sha256.
The approved prefix grants only this program's validated local-file operations.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = Path(os.environ.get("TMPDIR") or "/tmp").resolve()
if not TEMP_ROOT.is_absolute() or TEMP_ROOT == Path("/"):
    raise ValueError("TMPDIR must identify a temporary directory, not the filesystem root")
ROOTS = tuple(dict.fromkeys((ROOT, Path("/tmp").resolve(), TEMP_ROOT)))
PROTECTED = {".git", ".codex", ".agents"}
LIMIT = 64 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def allowed(value):
    if not isinstance(value, str) or not value:
        raise ValueError("A file path is required")
    lexical = Path(value) if Path(value).is_absolute() else ROOT / value
    if PROTECTED.intersection(lexical.parts):
        raise ValueError("Protected agent/Git metadata requires its normal permission path")
    resolved = lexical.resolve()
    if PROTECTED.intersection(resolved.parts) or not any(resolved.is_relative_to(root) for root in ROOTS):
        raise ValueError("File must resolve inside this checkout, /tmp or TMPDIR")
    if resolved.exists() and not resolved.is_file():
        raise ValueError("Only regular files are supported")
    return resolved


def prepare(spec):
    if set(spec) != {"edits"} or not isinstance(spec["edits"], list) or not 1 <= len(spec["edits"]) <= 100:
        raise ValueError("Supply one to 100 guarded edits")
    prepared, seen = [], set()
    for edit in spec["edits"]:
        path = allowed(edit["path"])
        if path in seen:
            raise ValueError("Duplicate target; combine its edits")
        seen.add(path)
        old = path.read_bytes() if path.exists() else None
        if old is not None and len(old) > LIMIT:
            raise ValueError("File exceeds local editing limit")
        if "content" in edit:
            if set(edit) != {"path", "content", "before_sha256"} or not isinstance(edit["content"], str):
                raise ValueError("Full writes require content and before_sha256")
            if edit["before_sha256"] != (sha(old) if old is not None else None):
                raise ValueError("Full-write precondition failed: " + str(path))
            new = edit["content"].encode("utf-8")
        else:
            if set(edit) != {"path", "old", "new"} or not isinstance(edit["old"], str) or not edit["old"] or not isinstance(edit["new"], str):
                raise ValueError("Replacement requires nonempty exact old text and new text")
            if old is None:
                raise ValueError("Replacement target is missing")
            text = old.decode("utf-8")
            if text.count(edit["old"]) != 1:
                raise ValueError("Exact replacement must match once: " + str(path))
            new = text.replace(edit["old"], edit["new"], 1).encode("utf-8")
        if len(new) > LIMIT:
            raise ValueError("Edited file exceeds local editing limit")
        prepared.append((path, old, new))
    return prepared


def apply(spec):
    # Validate the whole batch before writing, then recheck each target before
    # atomic replacement. This is not a multi-file transactional filesystem.
    edits = prepare(spec)
    results = []
    for path, old, new in edits:
        if allowed(str(path)) != path or (path.read_bytes() if path.exists() else None) != old:
            raise ValueError("Target changed during edit preparation")
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = stat.S_IMODE(path.stat().st_mode) & 0o777 if path.exists() else 0o644
        descriptor, temporary = tempfile.mkstemp(prefix=".workspace-edit-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(new)
                stream.flush()
                os.fsync(stream.fileno())
                os.fchmod(stream.fileno(), mode)
            if allowed(str(path)) != path or (path.read_bytes() if path.exists() else None) != old:
                raise ValueError("Target changed before replacement")
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        results.append({"path": str(path), "before_sha256": sha(old) if old is not None else None,
                        "after_sha256": sha(new), "bytes": len(new)})
    return results


def self_test():
    with tempfile.TemporaryDirectory(prefix="legalmath-edit-test-", dir="/tmp") as task_dir:
        path = Path(task_dir) / "new.txt"
        apply({"edits": [{"path": str(path), "content": "alpha\nbeta\n", "before_sha256": None}]})
        path.chmod(0o750)
        apply({"edits": [{"path": str(path), "old": "alpha", "new": "gamma"}]})
        assert path.read_text() == "gamma\nbeta\n" and stat.S_IMODE(path.stat().st_mode) == 0o750
        link = Path(task_dir) / "outside"
        link.symlink_to("/etc")
        for bad in ("/etc/passwd", str(link / "passwd"), str(ROOT / ".git/config"), str(ROOT / ".codex/config.toml")):
            try:
                allowed(bad)
            except ValueError:
                pass
            else:
                raise AssertionError("Unsafe path accepted")
        before = path.read_bytes()
        for bad in ({"path": str(path), "old": "missing", "new": "x"},
                    {"path": str(path), "content": "x", "before_sha256": "wrong"}):
            try:
                apply({"edits": [bad]})
            except ValueError:
                pass
            else:
                raise AssertionError("Stale edit accepted")
            assert path.read_bytes() == before
        try:
            apply({"edits": [{"path": str(path), "old": "gamma", "new": "changed"},
                             {"path": "/etc/passwd", "content": "x", "before_sha256": None}]})
        except ValueError:
            pass
        else:
            raise AssertionError("Unvalidated batch accepted")
        assert path.read_bytes() == before
    return {"status": "PASS", "checks": ["create", "replace", "mode preservation", "outside-root rejection",
            "symlink escape rejection", "protected metadata rejection", "stale preconditions", "batch preflight"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", nargs="?")
    parser.add_argument("--json", dest="json_spec", help="JSON specification as one literal argument; no shell execution")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        if args.spec or args.json_spec:
            parser.error("Self-test accepts no edit specification")
        result = self_test()
    else:
        if bool(args.spec) == bool(args.json_spec):
            parser.error("Supply either a local JSON file or --json")
        if args.json_spec:
            raw = args.json_spec
        else:
            path = allowed(args.spec)
            if path.stat().st_size > LIMIT:
                raise ValueError("Edit specification exceeds size limit")
            raw = path.read_text()
        if len(raw.encode("utf-8")) > LIMIT:
            raise ValueError("Edit specification exceeds size limit")
        result = {"status": "PASS", "edits": apply(json.loads(raw))}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
