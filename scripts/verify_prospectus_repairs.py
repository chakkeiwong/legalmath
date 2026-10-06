"""Execute and preserve the ordered repair acceptance checks (CPU, offline)."""
import json
import os
from pathlib import Path
import subprocess
import time
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/implementation/prospectus-repair-2026-10-06/finalization"


def main():
    global OUT
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--focused", action="store_true", help="Use focused checks after a bounded subsequent repair")
    args = parser.parse_args()
    if (OUT / "manifest.json").exists():
        index = 1
        while (OUT / ("run-%03d" % index)).exists():
            index += 1
        OUT = OUT / ("run-%03d" % index)
    OUT.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "-1"}
    commands = [
        ("execution", ["python3", "-m", "scripts.prospectus_delivery", "run"]),
        ("regression", ["python3", "-m", "scripts.prospectus_delivery", "check", "tests/prospectus_successor",
                        *(["tests/prospectus/test_closure_mechanisms.py"] if args.focused else ["tests/prospectus", "tests/compliance"]),
                        "--junitxml", str(OUT / "tests.xml")]),
        ("replay", ["python3", "-m", "scripts.prospectus_delivery", "run"]),
        ("status", ["python3", "-m", "scripts.prospectus_delivery", "status"]),
    ]
    records = []
    for name, argv in commands:
        started = time.monotonic()
        run = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
        (OUT / (name + ".log")).write_text(run.stdout + run.stderr)
        records.append({"name": name, "command": argv, "returncode": run.returncode,
                        "wall_seconds": time.monotonic() - started})
        if run.returncode:
            print(run.stdout[-5000:] + run.stderr[-5000:])
            raise RuntimeError("Acceptance command failed: " + name)
        if name in {"execution", "replay", "status"}:
            result = json.loads(run.stdout)
            (OUT / (name + ".json")).write_text(json.dumps(result, indent=2) + "\n")
            if name == "replay" and any(row["execution"] != "REUSED" for row in result):
                raise ValueError("Identical replay did not reuse every phase")
            if name == "status" and not all(row["current"] for row in result["phases"]):
                raise ValueError("A phase remains stale after execution")
        print(name + ": PASS", flush=True)
    sys.path.insert(0, str(ROOT / "src"))
    from legalmath.prospectus.successor.contracts import digest, read, write
    state = read(ROOT / "docs/implementation/prospectus-repair-2026-10-06/state.json")
    import xml.etree.ElementTree as ET
    suites = ET.parse(OUT / "tests.xml").getroot()
    counts = {k: sum(int(s.get(k, "0")) for s in suites.iter("testsuite"))
              for k in ("tests", "failures", "errors", "skipped")}
    manifest = {"status": "ENGINEERING_CHECKS_PASS; RELEASE_NOT_ACCEPTED", "commands": records,
                "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "environment": str(ROOT / ".venv/bin/python"), "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1",
                "random_seeds": "N/A deterministic engineering", "test_counts": counts,
                "plan": "docs/plans/prospectus-phase-repair-execution-2026-10-06.md",
                "result_file": "docs/implementation/prospectus-repair-2026-10-06/RESULT.md",
                "code_files": {str(p.relative_to(ROOT)): digest(p.read_bytes())
                               for p in sorted((ROOT / "src/legalmath/prospectus/successor").glob("*.py"))},
                "phase_receipts": {p: {k: row[k] for k in ("directory", "receipt_sha256", "method", "input_identity")}
                                   for p, row in state.items()},
                "outputs": {p.name: digest(p.read_bytes()) for p in OUT.iterdir() if p.is_file() and p.name != "manifest.json"}}
    write(OUT / "manifest.json", manifest)
    print(json.dumps({"status": manifest["status"], "tests": counts, "out": str(OUT)}))


if __name__ == "__main__":
    main()
