"""Finite native input observations, never a native reuse certificate."""
import hashlib
import os
from pathlib import Path
import stat

ENVIRONMENT_NAMES = (
    "PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "LD_LIBRARY_PATH", "LD_PRELOAD",
    "PYTHONPATH", "PYTHONHOME", "PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE",
    "TESSDATA_PREFIX", "OMP_THREAD_LIMIT", "OMP_NUM_THREADS", "CUDA_VISIBLE_DEVICES",
)


def environment_bindings():
    return {name: (hashlib.sha256(os.environ[name].encode()).hexdigest()
                   if name in os.environ else None) for name in ENVIRONMENT_NAMES}


def file_state(name):
    path = Path(name).absolute()
    resolved = str(path.resolve())
    try:
        before = path.stat()
    except FileNotFoundError:
        return {"path": str(path), "resolved": resolved, "state": "MISSING"}
    if not stat.S_ISREG(before.st_mode):
        return {"path": str(path), "resolved": resolved, "state": "NONREGULAR"}
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
        after = os.fstat(stream.fileno())
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if (identity(before) != identity(opened) or identity(opened) != identity(after)
            or identity(after) != identity(path.stat()) or resolved != str(path.resolve())):
        raise ValueError("Native input changed while observed: " + str(path))
    return {"path": str(path), "resolved": resolved, "state": "FILE",
            "size": after.st_size, "sha256": digest.hexdigest()}


def snapshot(paths):
    return {"version": "native-observations.v1",
            "files": [file_state(p) for p in sorted(set(map(str, paths)))],
            "environment": environment_bindings(), "complete_native_closure": False}


def observations_current(value):
    """Compare only the listed observations; true does not authorize reuse."""
    try:
        if (value["version"] != "native-observations.v1"
                or value["complete_native_closure"] is not False
                or value.get("issues") or value.get("status") == "INCOMPLETE"
                or value["environment"] != environment_bindings()):
            return False
        rows = value["files"]
        if not isinstance(rows, list) or not rows:
            return False
        if len({r["path"] for r in rows}) != len(rows):
            return False
        return all(r["state"] in {"FILE", "MISSING"} and file_state(r["path"]) == r for r in rows)
    except (OSError, KeyError, TypeError, ValueError, RuntimeError):
        return False


def loaded_inputs():
    """Observe current Linux mappings, explicitly retaining incomplete coverage."""
    issues, paths = [], set()
    try:
        lines = Path("/proc/self/maps").read_text().splitlines()
        for line in lines:
            parts = line.split(maxsplit=5)
            if len(parts) == 6 and parts[5].startswith("/"):
                name = parts[5]
                if name.endswith(" (deleted)"):
                    issues.append("Deleted mapped input: " + name)
                else:
                    paths.add(name)
        if not paths:
            issues.append("No file mappings observed")
    except OSError as exc:
        issues.append("Native mappings unavailable: " + type(exc).__name__)
    rows = []
    for path in sorted(paths):
        try:
            row = file_state(path)
            rows.append(row)
            if row["state"] != "FILE":
                issues.append("Mapped input is not a regular file: " + path)
        except (OSError, ValueError) as exc:
            issues.append("Mapped input unavailable: " + path + ": " + type(exc).__name__)
    return {"version": "native-observations.v1", "files": rows,
            "environment": environment_bindings(), "complete_native_closure": False,
            "status": "PARTIAL" if not issues else "INCOMPLETE", "issues": issues,
            "method_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "limits": ["Post-execution mappings omit unloaded libraries and nonmapped reads",
                       "Negative lookups require separate trace observations",
                       "Mutable host inputs and races prevent a reuse certificate"]}
