"""Reproduce the bounded bank-compliance checks without live client data."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/implementation/bank-compliance"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    started = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = ROOT / "docs/compliance/sources/manifest.json"
    archive = json.loads(manifest.read_text())
    for row in archive["sources"]:
        for name, hash_name in (("path", "sha256"), ("text_path", "text_sha256")):
            path = (ROOT / row[name]).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file() or sha(path) != row[hash_name]:
                raise ValueError("Source identity changed: " + row["key"])
        if row["status"] not in ("RETAINED", "REJECTED_ACCESS_PAGE"):
            raise ValueError("Unrecognized source disposition")
    command = [sys.executable, "-m", "pytest", "-q", "tests/compliance", "tests/prospectus",
               "tests/translation/test_qualification_windows.py", "--junitxml=" + str(OUT / "tests.xml")]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300)
    (OUT / "tests.log").write_text(proc.stdout + proc.stderr)
    if proc.returncode:
        raise RuntimeError("Regression failure: repair using tests.log, then rerun this command")
    suites = ET.parse(OUT / "tests.xml").getroot().iter("testsuite")
    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for field in counts:
            counts[field] += int(suite.get(field, 0))
    if any(counts[k] for k in ("failures", "errors", "skipped")):
        raise RuntimeError("All specified checks must execute and pass")
    method_files = [ROOT / "src/legalmath/compliance.py", Path(__file__), manifest,
                    ROOT / "docs/plans/bank-compliance-layers.md",
                    *sorted((ROOT / "tests/compliance").glob("*.py"))]
    report = {
        "status": "CHECKED_CONDITIONAL_ENGINEERING",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "preexisting_dirty_workspace": True,
        "command": [sys.executable, "scripts/check_bank_compliance.py"],
        "test_command": command, "environment": sys.executable,
        "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1; no GPU framework imported",
        "seeds": "N/A: deterministic specifications and finite enumeration",
        "wall_seconds": time.monotonic() - started, **counts,
        "source_records": len(archive["sources"]),
        "rejected_access_responses": sum(r["status"] == "REJECTED_ACCESS_PAGE" for r in archive["sources"]),
        "source_currentness": "NOT_ESTABLISHED",
        "conditional_checks": {"layer_combinations": 3 ** 7, "ownership_graph_seed_combinations": 2 ** 9},
        "plan": "docs/plans/bank-compliance-layers.md",
        "result": "docs/implementation/bank-compliance/report.md",
        "outputs": ["docs/implementation/bank-compliance/tests.xml", "docs/implementation/bank-compliance/tests.log"],
        "files": {str(p.relative_to(ROOT)): sha(p) for p in method_files},
        "complete_legal_compliance": "NOT_ESTABLISHED",
        "human_quality_evidence": False,
    }
    (OUT / "run-manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "tests", "source_records", "conditional_checks")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
