"""Pinned, reproducible Catala-to-Java builds for the ordinary release contract."""
from pathlib import Path
import json
import subprocess
import tempfile
import zipfile

from ..canonical import canonical, digest, raw_digest
from ..errors import LegalMathError
from ..java.emit import emit, runtime_sources
from ..java.manifest import toolchain
from .generator import ENGINE, generate


def _pinned(compiler, upstream, lock):
    compiler, upstream = Path(compiler).resolve(), Path(upstream).resolve()
    locked = json.loads(Path(lock).read_bytes())
    if raw_digest(compiler.read_bytes()) != locked["compiler_sha256"]:
        raise LegalMathError("E_HASH_MISMATCH", details="Catala compiler")
    actual = {p.relative_to(upstream).as_posix(): p for p in (upstream / "runtimes/java").rglob("*.java")}
    expected = {n: h for n, h in locked["source_files"].items() if n.startswith("runtimes/java/") and n.endswith(".java")}
    if actual.keys() != expected.keys():
        raise LegalMathError("E_INTEGRITY", details="Catala runtime source inventory")
    runtime = {}
    for name, path in actual.items():
        data = path.read_bytes()
        if raw_digest(data) != expected[name]:
            raise LegalMathError("E_HASH_MISMATCH", details=name)
        runtime[name] = data.decode()
    license_bytes = (upstream / "LICENSE.txt").read_bytes()
    if raw_digest(license_bytes) != locked["source_files"]["LICENSE.txt"]:
        raise LegalMathError("E_HASH_MISMATCH", details="Catala license")
    version = subprocess.run([str(compiler), "--version"], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    if version != locked["compiler_version"]:
        raise LegalMathError("E_INTEGRITY", details="Catala version")
    return compiler, locked, runtime, license_bytes


def build_candidate(bundle, output, jdk, *, compiler, upstream, lock):
    generated = generate(bundle)  # validate all branches before invoking tools
    name, policy = emit(bundle, backend="catala")
    compiler, locked, catala_runtime, license_bytes = _pinned(compiler, upstream, lock)
    jdk, java_version = toolchain(jdk)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    local_runtime = runtime_sources()
    runtime = {**{"host/" + k: v for k, v in local_runtime.items()}, **catala_runtime}
    logs = []
    flags = ["--release", "17", "-encoding", "UTF-8", "-g:none"]

    def run(argv, cwd):
        # Preserve exact executed commands separately; manifests use relative names.
        try:
            proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=120)
            logs.append({"command": list(map(str, argv)), "exit_code": proc.returncode,
                         "stdout": proc.stdout, "stderr": proc.stderr})
            proc.check_returncode()
            return proc
        except subprocess.TimeoutExpired as error:
            def message(data):
                return data.decode(errors="replace") if isinstance(data, bytes) else data or ""
            logs.append({"command": list(map(str, argv)), "status": "TIMEOUT", "timeout_seconds": 120,
                         "stdout": message(error.stdout), "stderr": message(error.stderr)})
            raise
        finally:
            (output / "build-commands.json").write_bytes(canonical(logs))

    with tempfile.TemporaryDirectory(prefix="legalmath-catala-") as td:
        staging = Path(td)
        (staging / "Lowered.catala_en").write_text(generated["source"])
        catala_command = ["java", "Lowered.catala_en", "--no-stdlib", "--check-invariants", "--output", "Lowered.java"]
        run([str(compiler), *catala_command], staging)
        generated_java = (staging / "Lowered.java").read_text()
        sources = {"Lowered.catala_en": generated["source"], "Lowered.java": generated_java,
                   "RuleIRBackend.java": generated["bridge"], name + ".java": policy,
                   "source-map.json": canonical(generated["source_map"]).decode(),
                   "bundle.json": canonical(bundle).decode()}
        classes = staging / "classes"
        classes.mkdir()
        for filename, text in {**runtime, **sources}.items():
            path = staging / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        external_command = ["javac", *flags, "-d", "classes", *sorted(catala_runtime)]
        run([str(jdk / "bin/javac"), *external_command[1:]], staging)
        host_java = sorted(["host/" + f for f in local_runtime] + [f for f in sources if f.endswith(".java")])
        host_command = ["javac", *flags, "-Xlint:all", "-Werror", "-cp", "classes", "-d", "classes", *host_java]
        run([str(jdk / "bin/javac"), *host_command[1:]], staging)
        identity = {"backend": ENGINE, "bundle_hash": digest(bundle), "generated_sha256": digest(sources),
                    "runtime_sha256": digest(runtime), "compiler_sha256": locked["compiler_sha256"],
                    "compiler_version": locked["compiler_version"], "upstream_commit": locked["upstream_commit"],
                    "toolchain_lock_sha256": raw_digest(Path(lock).read_bytes()),
                    "generator_sha256": raw_digest(Path(__file__).with_name("generator.py").read_bytes()),
                    "builder_sha256": raw_digest(Path(__file__).read_bytes()),
                    "commands": [["catala", *catala_command], external_command, host_command]}
        jar = staging / "policy.jar"
        entries = {p.relative_to(classes).as_posix(): p.read_bytes() for p in classes.rglob("*.class")}
        entries["META-INF/legalmath/catala-build.json"] = canonical(identity)
        entries["META-INF/legalmath/Catala-LICENSE.txt"] = license_bytes
        entries.update({"META-INF/legalmath/sources/" + k: v.encode() for k, v in {**runtime, **sources}.items()})
        with zipfile.ZipFile(jar, "w", compression=zipfile.ZIP_STORED) as z:
            for filename, data in sorted(entries.items()):
                info = zipfile.ZipInfo(filename, (1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o100644 << 16
                z.writestr(info, data)
        jar_bytes = jar.read_bytes()
    jar_hash = raw_digest(jar_bytes)
    manifest = {"record_type": "JavaBuildManifest", "bundle_hash": digest(bundle),
                "source_hashes": sorted({s["raw_sha256"] for s in bundle["source_spans"]}),
                "generated_sha256": digest(sources), "runtime_sha256": digest(runtime), "jar_sha256": jar_hash,
                "java_target": 17, "compiler": f"Catala {locked['compiler_version']} ({locked['compiler_sha256']}); {java_version}",
                "command": host_command, "dependencies": ["Java SE 17", f"Catala Java runtime {locked['upstream_commit']}"],
                "licenses": ["Catala and bundled Apache Commons Numbers runtime: Apache-2.0", "Project-authored host: deployment license review pending"],
                "decision_engine": ENGINE, "event_engine": "legalmath-java-events/0.1.0"}
    for filename, text in sources.items():
        (output / filename).write_text(text)
    (output / "catala-build.json").write_bytes(canonical(identity))
    (output / "build-manifest.json").write_bytes(canonical(manifest))
    (output / (jar_hash + ".jar")).write_bytes(jar_bytes)
    return {"manifest": manifest, "manifest_hash": digest(manifest), "jar": str(output / (jar_hash + ".jar")),
            "class_name": "hk.legalmath." + name}
