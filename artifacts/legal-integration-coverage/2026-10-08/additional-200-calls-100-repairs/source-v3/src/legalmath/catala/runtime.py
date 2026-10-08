"""Bounded subprocess access and immutable file manifests for the Catala pilot."""
import hashlib
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import zipfile

from .adapter import finish
from ..canonical import digest


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


class Commands:
    def __init__(self, root, directory):
        self.root = Path(root)
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.records = []

    def run(self, argv, *, timeout=60, input=None, check=True):
        number = len(self.records)
        started = time.monotonic()
        environment = dict(os.environ, PYTHONPATH=str(self.root / "src"),
                           LC_ALL="C.UTF-8")
        record = {"argv": list(map(str, argv)), "cwd": str(self.root), "timeout": timeout,
                  "stdin_sha256": hashlib.sha256(input.encode()).hexdigest() if input else None}
        try:
            proc = subprocess.run(record["argv"], input=input, cwd=self.root,
                                  env=environment, text=True, capture_output=True, timeout=timeout)
            record.update(returncode=proc.returncode, wall_seconds=time.monotonic()-started)
            (self.directory / f"{number:04d}.stdout").write_text(proc.stdout)
            (self.directory / f"{number:04d}.stderr").write_text(proc.stderr)
            if check and proc.returncode:
                raise RuntimeError(f"Command failed ({proc.returncode}): {argv}; {proc.stderr[-3000:]}")
            return proc
        except subprocess.TimeoutExpired:
            record.update(returncode=None, timed_out=True, wall_seconds=time.monotonic()-started)
            raise
        finally:
            self.records.append(record)
            write_json(self.directory / "commands.json", self.records)


def interpret(packet, binary, source, commands):
    identity = {"compiler_sha256": sha(binary), "source_sha256": sha(source)}
    if packet["preflight"]:
        return finish(packet, None, "legalmath-catala-interpreter/0.1", identity)
    proc = commands.run([binary, "interpret", source, "--no-stdlib", "--scope=" + packet["scope"],
                         "--input=" + json.dumps(packet["inputs"]), "--output-format=json"])
    return finish(packet, json.loads(proc.stdout, parse_float=Decimal), "legalmath-catala-interpreter/0.1", identity)


def jar_file(classes, target):
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(Path(classes).rglob("*.class")):
            info = zipfile.ZipInfo(path.relative_to(classes).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def java_packets(packets, jar, jdk, commands):
    identity = {"jar_sha256": sha(jar)}
    executable = [p for p in packets if p["preflight"] is None]
    if executable:
        proc = commands.run([str(Path(jdk) / "bin/java"), "-cp", str(jar), "CatalaPilotHost"],
            input="".join(json.dumps({"scope": p["scope"], "inputs": p["inputs"]}) + "\n" for p in executable))
        native = [json.loads(line) for line in proc.stdout.splitlines()]
        if len(native) != len(executable):
            raise ValueError("Missing or extra Java results")
    else:
        native = []
    iterator = iter(native)
    return [finish(p, None if p["preflight"] else next(iterator), "legalmath-catala-java/0.1", identity)
            for p in packets]


def manifest(directory):
    directory = Path(directory)
    return {str(p.relative_to(directory)): sha(p) for p in sorted(directory.rglob("*"))
            if p.is_file() and p != directory / "manifest.json"}


def verify_package(directory, expected_manifest_sha256):
    directory = Path(directory)
    path = directory / "manifest.json"
    if sha(path) != expected_manifest_sha256:
        raise ValueError("Untrusted Catala package manifest")
    expected = json.loads(path.read_text())
    if any(p.is_symlink() for p in directory.rglob("*")) or expected != manifest(directory):
        raise ValueError("Catala package bytes differ from the trusted manifest")
    metadata = json.loads((directory / "package.json").read_text())
    if metadata.get("release_eligible") is not False:
        raise ValueError("Pilot package cannot be released")
    return metadata


def evaluate_package(directory, expected_manifest_sha256, case, jdk, commands):
    """Execute copied, checked bytes. Trust in the manifest hash is caller-owned."""
    from .adapter import prepare
    directory = Path(directory)
    verify_package(directory, expected_manifest_sha256)
    manifest_bytes = (directory / "manifest.json").read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != expected_manifest_sha256:
        raise ValueError("Package changed during verification")
    committed = json.loads(manifest_bytes)
    with tempfile.TemporaryDirectory(prefix="catala-host-") as temporary:
        temporary = Path(temporary)
        for name in ("policy.jar", "profile.json"):
            data = (directory / name).read_bytes()
            if hashlib.sha256(data).hexdigest() != committed[name]:
                raise ValueError("Package changed during copying")
            (temporary / name).write_bytes(data)
        packet = prepare(case, json.loads((temporary / "profile.json").read_text()))
        result = java_packets([packet], temporary / "policy.jar", jdk, commands)[0]
        result["implementation"]["package_manifest_sha256"] = expected_manifest_sha256
        result["result_hash"] = digest({k: v for k, v in result.items() if k != "result_hash"})
        return result
