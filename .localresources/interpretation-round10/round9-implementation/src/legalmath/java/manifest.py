"""Clean, reproducible candidate builds; verification is a later immutable record."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

from ..canonical import canonical, digest, raw_digest, loads
from ..errors import LegalMathError
from ..ir.evaluate import ENGINE
from ..ir.trace import verify_result
from ..conformance import evaluate_case
from .emit import emit, runtime_sources


def toolchain(jdk):
    root = Path(jdk).resolve()
    javac = root / "bin/javac"
    java = root / "bin/java"
    if not javac.is_file() or not java.is_file():
        raise LegalMathError("E_NOT_FOUND")
    version = subprocess.run([str(javac), "-version"], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    if not version.startswith("javac 17."):
        raise LegalMathError("E_UNSUPPORTED_PROFILE")
    return root, version


def build_candidate(bundle, output, jdk):
    jdk, version = toolchain(jdk)
    name, source = emit(bundle)
    runtime = runtime_sources()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="legalmath-javac-") as td:
        staging = Path(td)
        src, classes = staging / "src", staging / "classes"
        src.mkdir()
        classes.mkdir()
        all_sources = {**runtime, name + ".java": source}
        for filename, text in all_sources.items():
            (src / filename).write_text(text)
        flags = ["--release", "17", "-encoding", "UTF-8", "-g:none", "-Xlint:all", "-Werror"]
        command = [str(jdk / "bin/javac"), *flags, "-d", str(classes), *map(str, sorted(src.glob("*.java")))]
        subprocess.run(command, capture_output=True, text=True, check=True, timeout=60)
        jar = staging / "policy.jar"
        with zipfile.ZipFile(jar, "w", compression=zipfile.ZIP_STORED) as z:
            for path in sorted(classes.rglob("*.class")):
                info = zipfile.ZipInfo(path.relative_to(classes).as_posix(), (1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o100644 << 16
                z.writestr(info, path.read_bytes())
        jar_bytes = jar.read_bytes()
    jar_hash = raw_digest(jar_bytes)
    manifest = {"record_type": "JavaBuildManifest", "bundle_hash": digest(bundle),
        "source_hashes": sorted({s["raw_sha256"] for s in bundle["source_spans"]}),
        "generated_sha256": raw_digest(source.encode()), "runtime_sha256": digest(runtime),
        "jar_sha256": jar_hash, "java_target": 17, "compiler": version,
        "command": ["javac", *flags, "-d", "classes", *sorted(all_sources)],
        "dependencies": ["Java SE 17"], "licenses": ["Project-authored runtime; deployment license review pending"],
        "decision_engine": "legalmath-java/0.1.0", "event_engine": "legalmath-java-events/0.1.0"}
    (output / (jar_hash + ".jar")).write_bytes(jar_bytes)
    (output / (name + ".java")).write_text(source)
    (output / "build-manifest.json").write_bytes(canonical(manifest))
    return {"manifest": manifest, "manifest_hash": digest(manifest), "jar": str(output / (jar_hash + ".jar")), "class_name": "hk.legalmath." + name}


def run_java(jar, cases, jdk, class_name=None):
    jdk, _ = toolchain(jdk)
    requests = [{k: c[k] for k in ("bundle", "snapshot", "rule_id", "valid_at", "known_at", "mode") if k in c} for c in cases]
    command = [str(jdk / "bin/java"), "-cp", str(jar), "hk.legalmath.Runner"]
    if class_name is not None:
        command.append(class_name)
    result = subprocess.run(command,
        input=b"\n".join(canonical(r) for r in requests) + b"\n", capture_output=True, check=True, timeout=60)
    rows = [loads(line) for line in result.stdout.splitlines()]
    if len(rows) != len(cases):
        raise LegalMathError("E_INTEGRITY")
    return rows


def verify_candidate(build, cases, jdk, event_cases=None):
    jar = Path(build["jar"])
    manifest = build["manifest"]
    if raw_digest(jar.read_bytes()) != manifest["jar_sha256"]:
        raise LegalMathError("E_HASH_MISMATCH")
    if not cases or any(digest(c["bundle"]) != manifest["bundle_hash"] for c in cases):
        raise LegalMathError("E_REFERENCE")
    actual = run_java(jar, cases, jdk, build["class_name"])
    results = []
    for c, java in zip(cases, actual):
        python = evaluate_case(c)
        verify_result(c["bundle"], c["snapshot"], c["rule_id"], python)
        verify_result(c["bundle"], c["snapshot"], c["rule_id"], java)
        for key, val in c["expected"].items():
            if key == "reason_codes_include":
                good = set(val) <= set(java["reason_codes"])
            else:
                good = java.get(key) == val
            if not good:
                raise LegalMathError("E_INTEGRITY", details=c.get("id"))
        exclude = {"engine_version", "result_hash"}
        if {k:v for k,v in java.items() if k not in exclude} != {k:v for k,v in python.items() if k not in exclude}:
            raise LegalMathError("E_INTEGRITY", details=c.get("id"))
        if java["engine_version"] == python["engine_version"]:
            raise LegalMathError("E_INTEGRITY")
        results.append({"id": c["id"], "python": python, "java": java})
    checks = [{"name": "full-semantic-conformance", "passed": True, "evidence_hash": digest(results)}]
    commands = [["java", "-cp", manifest["jar_sha256"] + ".jar", "hk.legalmath.Runner", build["class_name"]]]
    if event_cases:
        from ..events.replay import replay
        requests = [c["request"] for c in event_cases]
        jdk_path, _ = toolchain(jdk)
        process = subprocess.run([str(jdk_path / "bin/java"), "-cp", str(jar), "hk.legalmath.Runner"],
            input=b"\n".join(canonical({"event_request": r}) for r in requests) + b"\n", capture_output=True, check=True, timeout=60)
        java_events = [loads(line) for line in process.stdout.splitlines()]
        if len(java_events) != len(requests): raise LegalMathError("E_INTEGRITY")
        event_results = []
        for c, java in zip(event_cases, java_events):
            python = replay(c["request"])
            if any(java.get(k) != v for k, v in c["expected"].items()): raise LegalMathError("E_INTEGRITY")
            for result in (python, java):
                if result["result_hash"] != digest({"request": c["request"], "result": {k:v for k,v in result.items() if k != "result_hash"}}):
                    raise LegalMathError("E_HASH_MISMATCH")
            if {k:v for k,v in python.items() if k not in ("engine_version", "result_hash")} != {k:v for k,v in java.items() if k not in ("engine_version", "result_hash")}:
                raise LegalMathError("E_INTEGRITY")
            event_results.append({"case": c, "python": python, "java": java})
        checks.append({"name": "attributed-event-conformance", "passed": True, "evidence_hash": digest(event_results)})
        commands.append(["java", "-cp", manifest["jar_sha256"] + ".jar", "hk.legalmath.Runner"])
        (jar.parent / "event-verification-results.json").write_bytes(canonical(event_results))
    report = {"record_type": "VerificationReport", "build_manifest_hash": digest(manifest),
        "jar_sha256": manifest["jar_sha256"], "bundle_hash": manifest["bundle_hash"],
        "reference_engine": ENGINE, "corpus_hash": digest(cases),
        "commands": commands, "checks": checks, "passed": True}
    out = jar.parent
    (out / "verification-report.json").write_bytes(canonical(report))
    (out / "verification-results.json").write_bytes(canonical(results))
    return report
