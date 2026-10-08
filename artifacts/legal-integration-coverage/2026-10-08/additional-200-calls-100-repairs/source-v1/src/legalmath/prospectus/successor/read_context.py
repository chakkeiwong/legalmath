"""Recorded capabilities for cooperating Python jobs; not an OS sandbox."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from .contracts import bound_path, digest, timestamp


class ReadContext:
    def __init__(self, root, snapshots, *, clock=None):
        self.root, self.snapshots = Path(root).resolve(), Path(snapshots)
        self.clock_value = clock
        self.records = []

    def _record(self, record):
        # Re-reading changed inputs in one phase is invalid, including absence.
        identity = (record["kind"], record["name"])
        for previous in self.records:
            if (previous["kind"], previous["name"]) == identity:
                if previous != record:
                    raise ValueError("Input changed during phase: " + record["name"])
                return
        self.records.append(record)

    def read_bytes(self, relative, *, expected=None, optional=False, _external=False):
        path = external_path(relative) if _external else bound_path(self.root, relative)
        kind = "external-file" if _external else "file"
        if not path.exists() and optional:
            self._record({"kind": kind, "name": str(relative), "sha256": None, "snapshot": None})
            return None
        raw = path.read_bytes()
        sha = digest(raw)
        if expected is not None and sha != expected:
            raise ValueError("Input hash mismatch: " + str(relative))
        self.snapshots.mkdir(parents=True, exist_ok=True)
        snapshot = self.snapshots / sha
        if snapshot.exists():
            if digest(snapshot.read_bytes()) != sha:
                raise ValueError("Corrupt input snapshot")
        else:
            with tempfile.NamedTemporaryFile(dir=self.snapshots, prefix=".snapshot-", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            try:
                try:
                    os.link(temporary, snapshot)
                except FileExistsError:
                    if digest(snapshot.read_bytes()) != sha:
                        raise ValueError("Corrupt input snapshot")
                descriptor = os.open(self.snapshots, os.O_RDONLY | os.O_DIRECTORY)
                try: os.fsync(descriptor)
                finally: os.close(descriptor)
            finally:
                temporary.unlink(missing_ok=True)
        self._record({"kind": kind, "name": str(relative), "sha256": sha,
                      "snapshot": str(snapshot.relative_to(self.root))})
        return raw

    def external_bytes(self, path, *, expected=None):
        return self.read_bytes(str(path), expected=expected, _external=True)

    def external_tree(self, path):
        self._record({"kind": "external-tree", "name": str(path), "files": tree_bindings(path)})

    def read_json(self, relative, **kwargs):
        raw = self.read_bytes(relative, **kwargs)
        return json.loads(raw) if raw is not None else None

    def entries(self, relative):
        path = bound_path(self.root, relative)
        names = sorted(p.name for p in path.iterdir()) if path.is_dir() else None
        self._record({"kind": "directory", "name": str(relative), "entries": names})
        return names

    def environment(self, name):
        # Do not put credentials or arbitrary environment dumps into receipts.
        if name not in {"CUDA_VISIBLE_DEVICES", "LANG", "LC_ALL", "TZ"}:
            raise ValueError("Unapproved environment capability")
        value = os.environ.get(name)
        self._record({"kind": "environment", "name": name, "value": value})
        return value

    def clock(self):
        if self.clock_value is None:
            raise ValueError("A result-dependent clock must be supplied explicitly")
        timestamp(self.clock_value)
        self._record({"kind": "clock", "name": "evaluation_time", "value": self.clock_value})
        return self.clock_value

    def tool(self, argv, *, inputs=(), timeout=60, env=None):
        if not isinstance(argv, list) or not argv or not 0 < timeout <= 1800:
            raise ValueError("Bounded argv tool capability required")
        for relative in inputs:
            self.read_bytes(relative)
        path = Path(shutil.which(argv[0]) or argv[0]).resolve(strict=True)
        self._record({"kind": "tool", "name": argv[0], "path": str(path), "sha256": digest(path.read_bytes())})
        result = subprocess.run(argv, cwd=self.root, env=env, capture_output=True, timeout=timeout)
        self.records.append({"kind": "invocation", "name": str(len(self.records)), "argv": argv,
                             "returncode": result.returncode, "stdout_sha256": digest(result.stdout),
                             "stderr_sha256": digest(result.stderr), "timeout": timeout,
                             "native_reads": "UNENFORCED; explicit inputs and broad bindings retained"})
        return result

    def manifest(self):
        return {"version": "observed-reads.v1", "records": self.records,
                "boundary": "Cooperating Python reads only; native imports/subprocess reads are not confined"}


def external_path(name):
    path = Path(name).resolve()
    if not any(path.is_relative_to(Path(prefix)) for prefix in
               ("/tmp/prospectus-adoption-tools", "/tmp/prospectus-adoption-models")):
        raise ValueError("External read outside declared sidecar roots")
    return path


def tree_bindings(name):
    path = external_path(name)
    if not path.is_dir():
        raise ValueError("Missing declared tool distribution tree")
    return {str(p.relative_to(path)): digest(external_path(p).read_bytes()) for p in sorted(path.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def current(root, manifest):
    try:
        for row in manifest["records"]:
            if row["kind"] in {"file", "external-file"}:
                path = external_path(row["name"]) if row["kind"] == "external-file" else bound_path(root, row["name"])
                if row["sha256"] is None and path.exists():
                    return False
                if (digest(path.read_bytes()) if path.is_file() else None) != row["sha256"]:
                    return False
                if row["sha256"] is not None and digest(bound_path(root, row["snapshot"]).read_bytes()) != row["sha256"]:
                    return False
            elif row["kind"] == "directory":
                path = bound_path(root, row["name"])
                if (sorted(p.name for p in path.iterdir()) if path.is_dir() else None) != row["entries"]:
                    return False
            elif row["kind"] == "environment" and os.environ.get(row["name"]) != row["value"]:
                return False
            elif row["kind"] == "external-tree" and tree_bindings(row["name"]) != row["files"]:
                return False
            elif row["kind"] == "tool":
                path = Path(shutil.which(row["name"]) or row["name"]).resolve(strict=True)
                if str(path) != row["path"] or digest(path.read_bytes()) != row["sha256"]:
                    return False
        return True
    except (KeyError, TypeError, ValueError, OSError):
        return False
