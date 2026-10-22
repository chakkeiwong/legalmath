"""Optional Linux worker-file snapshot; not a cache or legal acceptance policy.

Only explicit files are copied into a new namespace. The host kernel,
Bubblewrap setup, private procfs and minimal devices remain trusted inputs.
"""
from contextlib import ExitStack, contextmanager
import fcntl
import hashlib
import json
import os
import platform
from pathlib import Path, PurePosixPath
import re
import resource
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time

VERSION = "sealed-native-files.v1"
MAX_FILES = 2048
MAX_BYTES = 512 * 1024 * 1024
MAX_STREAM = 20 * 1024 * 1024
MAX_EXPLICIT_STREAM = 64 * 1024 * 1024
SEALS = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
ENVIRONMENT = {
    "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
    "TZ": "UTC", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0", "CUDA_VISIBLE_DEVICES": "-1", "OMP_THREAD_LIMIT": "1",
    "OMP_NUM_THREADS": "1", "PWD": "/",
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def destination(value):
    if (not isinstance(value, str) or not value.startswith("/") or value.startswith("//") or "\x00" in value
            or str(PurePosixPath(value)) != value or value == "/"
            or ".." in PurePosixPath(value).parts
            or value.split("/")[1] in {"proc", "dev", "tmp"}):
        raise ValueError("Invalid or reserved snapshot destination")
    return value


def validate(manifest):
    if not isinstance(manifest, dict) or set(manifest) != {
            "version", "files", "directories", "environment", "native_reuse_allowed"}:
        raise ValueError("Invalid snapshot manifest fields")
    if (manifest["version"] != VERSION or manifest["environment"] != ENVIRONMENT
            or manifest["native_reuse_allowed"] is not False):
        raise ValueError("Unsupported runtime/environment or reuse claim")
    rows = manifest["files"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_FILES:
        raise ValueError("Invalid snapshot file count")
    names, total = set(), 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "size", "mode"}:
            raise ValueError("Invalid snapshot file fields")
        name = destination(row["path"])
        if name in names:
            raise ValueError("Duplicate snapshot destination")
        names.add(name)
        if (not isinstance(row["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
                or type(row["size"]) is not int or not 0 <= row["size"] <= MAX_BYTES
                or type(row["mode"]) is not int or row["mode"] not in (0o444, 0o555)):
            raise ValueError("Invalid snapshot hash, size or mode")
        total += row["size"]
    if total > MAX_BYTES:
        raise ValueError("Snapshot exceeds byte bound")
    directories = manifest["directories"]
    if not isinstance(directories, list) or len(directories) > MAX_FILES * 8:
        raise ValueError("Invalid snapshot directory count")
    if len(set(directories)) != len(directories):
        raise ValueError("Duplicate snapshot directory")
    for name in [*names, *directories]:
        destination(name)
        if any(str(p) in names for p in PurePosixPath(name).parents):
            raise ValueError("Snapshot file has children")
    if names.intersection(directories):
        raise ValueError("Snapshot file/directory collision")
    return manifest


@contextmanager
def regular_file(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("Snapshot source is not a regular file")
        yield fd
    finally:
        os.close(fd)


def snapshot(folder, sources, directories=()):
    """Capture explicitly resolved regular sources; no directory traversal."""
    folder = Path(folder)
    if not isinstance(sources, dict) or not 1 <= len(sources) <= MAX_FILES:
        raise ValueError("Invalid snapshot sources")
    for name in sources:
        destination(name)
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "blobs").mkdir()
    rows, provenance, total = [], [], 0
    for name, source in sorted(sources.items()):
        with regular_file(source) as fd:
            before = os.fstat(fd)
            if total + before.st_size > MAX_BYTES:
                raise ValueError("Snapshot exceeds byte bound")
            with tempfile.TemporaryFile(dir=folder) as copied:
                h, size = hashlib.sha256(), 0
                while chunk := os.read(fd, 1024 * 1024):
                    h.update(chunk)
                    size += len(chunk)
                    if total + size > MAX_BYTES:
                        raise ValueError("Snapshot exceeds byte bound")
                    copied.write(chunk)
                after = os.fstat(fd)
                identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
                if identity(before) != identity(after) or size != before.st_size:
                    raise ValueError("Source changed during snapshot")
                hashed = h.hexdigest()
                target = folder / "blobs" / hashed
                if not target.exists():
                    copied.seek(0)
                    with target.open("xb") as out:
                        while chunk := copied.read(1024 * 1024):
                            out.write(chunk)
                total += size
                rows.append({"path": name, "sha256": hashed, "size": size,
                             "mode": 0o555 if before.st_mode & 0o111 else 0o444})
                provenance.append({"path": name, "captured_from": str(source)})
    manifest = validate({"version": VERSION, "files": rows,
                         "directories": sorted(set(directories)),
                         "environment": dict(ENVIRONMENT), "native_reuse_allowed": False})
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (folder / "capture.json").write_text(json.dumps(provenance, indent=2) + "\n")
    return manifest


@contextmanager
def sealed_file(path, expected_hash, expected_size):
    """Verify the sealed copy, not a host path that will be reopened by a worker."""
    fd = os.memfd_create("prospectus-input", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        h, size = hashlib.sha256(), 0
        with regular_file(path) as source:
            while chunk := os.read(source, 1024 * 1024):
                size += len(chunk)
                if size > expected_size or size > MAX_BYTES:
                    raise ValueError("Snapshot blob exceeds declared size")
                h.update(chunk)
                remaining = memoryview(chunk)
                while remaining:
                    remaining = remaining[os.write(fd, remaining):]
        if size != expected_size or h.hexdigest() != expected_hash:
            raise ValueError("Snapshot blob hash/size mismatch")
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, SEALS)
        if fcntl.fcntl(fd, fcntl.F_GET_SEALS) != SEALS:
            raise ValueError("Required memory-file seals missing")
        os.lseek(fd, 0, os.SEEK_SET)
        yield fd
    finally:
        os.close(fd)


@contextmanager
def command(folder, manifest, argv):
    """Prepare the namespace from sealed copies, without launching a process."""
    validate(manifest)
    if (not isinstance(argv, list) or not argv or len(argv) > 64
            or any(not isinstance(s, str) or "\x00" in s or len(s) > 100000 for s in argv)):
        raise ValueError("Invalid runtime argv")
    executable = next((r for r in manifest["files"] if r["path"] == argv[0]), None)
    if not executable or executable["mode"] != 0o555:
        raise ValueError("Command executable is not an explicit executable input")
    with ExitStack() as stack:
        args = ["/usr/bin/bwrap", "--die-with-parent", "--new-session", "--unshare-all",
                "--unshare-user", "--cap-drop", "ALL", "--clearenv", "--chdir", "/",
                "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
        for name in sorted(manifest["directories"], key=lambda s: (s.count("/"), s)):
            args.extend(["--dir", name])
        fds = []
        for row in manifest["files"]:
            fd = stack.enter_context(sealed_file(Path(folder) / "blobs" / row["sha256"],
                                                 row["sha256"], row["size"]))
            fds.append(fd)
            args.extend(["--perms", format(row["mode"], "o"), "--ro-bind-data", str(fd), row["path"]])
        for name, value in sorted(manifest["environment"].items()):
            args.extend(["--setenv", name, value])
        args.extend(["--remount-ro", "/", "--", *argv])
        yield args, tuple(fds)


def stream_bound(value=None):
    value = MAX_STREAM if value is None else value
    if type(value) is not int or not 0 < value <= MAX_EXPLICIT_STREAM:
        raise ValueError('Invalid runtime stream bound')
    return value


def capture_process(args, fds, stdin, timeout, *, max_stream=None):
    """Drain bounded streams independently of the child's runtime-file writes."""
    max_stream = stream_bound(max_stream)
    def limits():
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_BYTES, MAX_BYTES))
    child = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env=dict(ENVIRONMENT), pass_fds=fds, close_fds=True,
                             start_new_session=True, preexec_fn=limits)
    outputs = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + timeout
    pending = memoryview(stdin)
    try:
        with selectors.DefaultSelector() as selector:
            for name in ("stdout", "stderr"):
                stream = getattr(child, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            if pending:
                os.set_blocking(child.stdin.fileno(), False)
                selector.register(child.stdin, selectors.EVENT_WRITE, "stdin")
            else:
                child.stdin.close()
            while selector.get_map():
                left = deadline - time.monotonic()
                if left <= 0:
                    raise subprocess.TimeoutExpired(args, timeout)
                for key, _ in selector.select(min(left, 1)):
                    stream, name = key.fileobj, key.data
                    if name == "stdin":
                        try:
                            pending = pending[os.write(stream.fileno(), pending[:4096]):]
                        except BrokenPipeError:
                            pending = memoryview(b"")
                        if not pending:
                            selector.unregister(stream)
                            stream.close()
                    else:
                        data = os.read(stream.fileno(), 65536)
                        if not data:
                            selector.unregister(stream)
                            stream.close()
                        else:
                            if len(outputs[name]) + len(data) >= max_stream:
                                raise ValueError("Runtime output stream bound reached")
                            outputs[name].extend(data)
            child.wait(timeout=max(0.001, deadline - time.monotonic()))
    except BaseException:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait(timeout=5)
        raise
    finally:
        for stream in (child.stdin, child.stdout, child.stderr):
            stream.close()
    return child.returncode, bytes(outputs["stdout"]), bytes(outputs["stderr"])


def trusted_runtime():
    from . import process_ledger
    hashed = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    return {'kernel_system': platform.system(), 'kernel_release': platform.release(),
            'kernel_version': platform.version(), 'machine': platform.machine(),
            'bubblewrap_sha256': hashed('/usr/bin/bwrap'), 'supervisor_python_sha256': hashed(sys.executable),
            'launcher_method_sha256': hashed(__file__), 'process_ledger_method_sha256': hashed(process_ledger.__file__),
            'trust_scope': 'Host kernel/CPU, launcher setup, private proc/dev; not immutable host attestation'}


def verify_receipt(receipt, manifest, argv, stdin, stdout, stderr, *, require_current=True):
    """Check exact retained bytes and parent identity, without authenticating an author."""
    validate(manifest)
    keys = {'version', 'returncode', 'manifest_sha256', 'argv', 'stdin', 'stdout', 'stderr',
            'trusted_runtime', 'file_namespace', 'native_reuse_allowed', 'receipt_sha256'}
    if isinstance(receipt, dict) and receipt.get('version') == 'sealed-native-execution.v2':
        keys.add('limits')
    if not isinstance(receipt, dict) or set(receipt) != keys:
        raise ValueError('Invalid runtime receipt fields')
    body = {k: v for k, v in receipt.items() if k != 'receipt_sha256'}
    if (receipt['version'] not in {'sealed-native-execution.v1', 'sealed-native-execution.v2'} or receipt['receipt_sha256'] != digest(body)
            or type(receipt['returncode']) is not int or receipt['native_reuse_allowed'] is not False
            or receipt['manifest_sha256'] != digest(manifest) or receipt['argv'] != argv):
        raise ValueError('Runtime receipt identity mismatch')
    if receipt['version'] == 'sealed-native-execution.v2':
        if not isinstance(receipt['limits'], dict) or set(receipt['limits']) != {'max_stream_bytes'}:
            raise ValueError('Invalid runtime receipt limits')
        cap = stream_bound(receipt['limits']['max_stream_bytes'])
        if len(stdout) >= cap or len(stderr) >= cap:
            raise ValueError('Runtime receipt stream exceeds declared bound')
    for name, data in (('stdin', stdin), ('stdout', stdout), ('stderr', stderr)):
        if not isinstance(data, bytes) or receipt[name] != {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}:
            raise ValueError('Runtime receipt stream mismatch: ' + name)
    if require_current and receipt['trusted_runtime'] != trusted_runtime():
        raise ValueError('Runtime receipt method/tool/kernel changed')
    return True


def run(folder, manifest, argv, stdin=b"", timeout=60, *, after_capture=None, max_stream=None):
    """Run a bounded optional worker. Nonzero exits remain nonzero in the result."""
    if (type(timeout) not in (float, int) or not 0 < timeout <= 60
            or not isinstance(stdin, bytes) or len(stdin) > 1024 * 1024):
        raise ValueError("Invalid runtime command bounds")
    max_stream = stream_bound(max_stream)
    before = trusted_runtime()
    with command(folder, manifest, argv) as (args, fds):
        if after_capture is not None:
            after_capture()  # Test hook; all worker file bytes are already sealed.
        returncode, stdout, stderr = capture_process(args, fds, stdin, timeout, max_stream=max_stream)
    if before != trusted_runtime():
        raise ValueError('Trusted runtime changed during execution')
    streams = {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
               for name, data in (('stdin', stdin), ('stdout', stdout), ('stderr', stderr))}
    receipt = {"version": "sealed-native-execution.v2", "returncode": returncode,
            "manifest_sha256": digest(manifest), "argv": argv, **streams, "trusted_runtime": before,
            "file_namespace": "sealed explicit files; private proc/dev/tmp; no host directory mounts",
            "native_reuse_allowed": False, 'limits': {'max_stream_bytes': max_stream}}
    receipt['receipt_sha256'] = digest(receipt)
    verify_receipt(receipt, manifest, argv, stdin, stdout, stderr)
    return {"returncode": returncode, "stdout": stdout, "stderr": stderr, "receipt": receipt}
