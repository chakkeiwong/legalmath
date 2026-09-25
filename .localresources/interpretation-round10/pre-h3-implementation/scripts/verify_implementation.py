"""Record actual commands and exit status for the core engineering acceptance."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/runs/acceptance"
OUT.mkdir(parents=True, exist_ok=True)
commands = [
    ("tests", [sys.executable, "-m", "pytest", "-q", "--junitxml=artifacts/runs/acceptance/tests.xml"]),
    ("contracts", [sys.executable, "scripts/check_contracts.py"]),
    ("spec-runtime", [sys.executable, "scripts/check_spec_pack.py", "--runtime", "legalmath.conformance:evaluate_case"]),
    ("walkthrough", [str(ROOT / ".venv/bin/legalmath"), "acceptance", "--scenario", "spi-23ec35", "--offline", "--out", "artifacts/runs/mvp-accepted"]),
]
inputs = {}
for directory in ("src", "tests", "corpus"):
    for path in sorted((ROOT / directory).rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and ".egg-info" not in str(path):
            inputs[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
for name in ("pyproject.toml", "requirements-dev.lock", "scripts/verify_implementation.py", "scripts/check_contracts.py", "scripts/fresh_install.sh", "scripts/browser_walkthrough.py"):
    inputs[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
manifest = {"question": "Do the local public/synthetic implementation and exported Java satisfy the engineering acceptance contracts?",
    "plan": "docs/plans/implementation-execution.md", "result": "docs/implementation/execution-report.md",
    "git_commit": "N/A: this workspace is not a Git repository", "environment": {"python": sys.version, "executable": sys.executable, "platform": platform.platform()},
    "execution_context": "trusted host; sandbox blocks TestClient thread wakeups", "device": "CPU only; no ML framework or GPU invoked",
    "random_seeds": "N/A: deterministic cases and controlled thread barriers", "data_version": "public SFC snapshots 2026-09-21; synthetic clients and amendment",
    "started_utc": datetime.now(timezone.utc).isoformat(), "input_sha256": inputs, "commands": [], "status": "RUNNING"}
start = time.monotonic()
for name, command in commands:
    print("Running " + name, flush=True)
    began = time.monotonic()
    with (OUT / (name + ".log")).open("w") as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    manifest["commands"].append({"name": name, "command": command, "exit_code": result.returncode,
        "wall_seconds": round(time.monotonic() - began, 3), "output": str((OUT / (name + ".log")).relative_to(ROOT))})
    manifest["status"] = "FAILED" if result.returncode else "RUNNING"
    (OUT / "run-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if result.returncode:
        print((OUT / (name + ".log")).read_text())
        raise SystemExit(result.returncode)
manifest.update(status="CORE_ACCEPTANCE_PASSED", wall_seconds=round(time.monotonic() - start, 3), finished_utc=datetime.now(timezone.utc).isoformat())
(OUT / "run-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("Core acceptance passed; inspect artifacts/runs/acceptance.")
