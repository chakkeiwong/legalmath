#!/usr/bin/env python3
"""Build Catala in an isolated switch from explicitly downloaded upstream files.

opam and the pinned Catala archive/source must already be present. This optional
preparation command downloads opam dependencies but never changes system tools.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_COMMIT = "0f895e048d19dbe72f24cdd6d5f3398bfe1335fa"


def digest_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--switch", default="catala-clean-1.2.1")
    args = parser.parse_args()
    base = ROOT / ".localresources/catala-toolchain"
    opam = base / "opam-2.5.2"
    source = base / ("catala-" + UPSTREAM_COMMIT)
    # Preserve user identity and network settings, never compiler activation state.
    names = ("HOME", "USER", "LOGNAME", "LANG", "TMPDIR", "SSL_CERT_FILE",
             "SSL_CERT_DIR", "HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "NO_PROXY")
    env = {key: os.environ[key] for key in names if key in os.environ}
    env.update(PATH=str(base / "bin") + ":/usr/bin:/bin", OPAMROOT=str(base / "opam-root"),
               CC="/usr/bin/gcc", CXX="/usr/bin/g++", LC_ALL="C.UTF-8")
    records = []

    def run(stage, argv, timeout=1200):
        started = time.monotonic()
        log = base / (stage + ".log")
        print(stage, flush=True)
        with log.open("w") as stream:
            result = subprocess.run(list(map(str, argv)), cwd=ROOT, env=env,
                                    stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        records.append({"stage": stage, "argv": list(map(str, argv)), "returncode": result.returncode,
                        "wall_seconds": time.monotonic()-started, "log": str(log),
                        "log_sha256": digest_file(log)})
        (base / "preparation.json").write_text(json.dumps(records, indent=2) + "\n")
        result.check_returncode()

    if not (base / "opam-root/config").exists():
        run("clean-init", [opam, "init", "--bare", "--no-setup", "--disable-sandboxing", "-y"], 180)
    switch = base / "opam-root" / args.switch
    if not (switch / "bin/ocamlc").exists():
        run("clean-switch", [opam, "switch", "create", args.switch, "ocaml-base-compiler.4.14.2", "-y", "--jobs=4"])
    run("clean-catala", [opam, "pin", "add", "catala.1.2.1", source,
        "--switch=" + args.switch, "--assume-depexts", "-y", "--jobs=4"])
    compiler = switch / "bin/catala"
    config = subprocess.check_output([switch / "bin/ocamlc", "-config"], text=True, env=env)
    if "conda" in config.lower():
        raise RuntimeError("Conda build settings remain in the OCaml compiler")
    packages = subprocess.check_output([opam, "list", "--installed", "--short", "--columns=name,version",
        "--switch=" + args.switch], env=env, text=True)
    exported = base / "dependencies.opam.export"
    subprocess.run([opam, "switch", "export", exported, "--switch=" + args.switch], env=env, check=True)
    version = subprocess.check_output([compiler, "--version"], env=env, text=True).strip()
    paths = [p for p in source.rglob("*") if p.is_file() and "_build" not in p.parts
             and ".git" not in p.parts]
    lock = {"upstream_commit": UPSTREAM_COMMIT, "upstream_tag": "1.2.1", "compiler_version": version,
            "compiler_sha256": digest_file(compiler), "compiler_path": str(compiler.relative_to(ROOT)),
            "source_archive_sha256": digest_file(base / "catala-1.2.1.tar.gz"),
            "opam_version": "2.5.2", "opam_sha256": digest_file(opam),
            "ninja_sha256": digest_file(base / "bin/ninja"), "ocaml_config": config,
            "packages": packages, "dependency_export_sha256": digest_file(exported),
            "source_files": {str(p.relative_to(source)): digest_file(p) for p in sorted(paths)},
            "preparation": records}
    target = ROOT / "docs/implementation/catala/toolchain-lock.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(lock, indent=2) + "\n")
    print("Pinned compiler ready: " + str(compiler), flush=True)


if __name__ == "__main__":
    main()
