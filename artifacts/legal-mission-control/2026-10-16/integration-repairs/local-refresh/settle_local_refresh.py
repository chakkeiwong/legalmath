"""Retain bounded, actual post-adoption checks; never dispatch a model call."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time


root = Path.cwd()
work = Path(__file__).resolve().parent
base = root / "artifacts/legal-mission-control/2026-10-13/master"
program = root / "docs/implementation/legal-mission-control/integration-master.json"
assert json.loads(program.read_text()).get("local_refresh"), "Register first"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


def reference(path):
    return {"path": str(path.relative_to(root)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


identity = [reference(path) for path in (
    program, root / "docs/implementation/legal-mission-control/mission.json",
    base / "execution-state.json", base / "live-calls.json",
    base / "current-binding.json")]
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
for name, command in (
    ("refresh-after", [".venv/bin/python", "scripts/legal_mission_control.py", "refresh"]),
    ("verify-after", [".venv/bin/python", "scripts/legal_integration_master.py", "verify"]),
):
    output = work / (name + ".json")
    error = work / (name + ".stderr")
    manifest = work / (name + ".manifest.json")
    assert not output.exists() and not manifest.exists(), "Preserve prior results"
    started = datetime.now(timezone.utc).isoformat()
    begin = time.monotonic()
    timed_out = False
    with output.open("x") as out, error.open("x") as err:
        try:
            result = subprocess.run(command, cwd=root, stdout=out, stderr=err, timeout=900)
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            returncode = 124
    unchanged = all(reference(root / item["path"]) == item for item in identity)
    record = dict(command=command, started_utc=started,
        finished_utc=datetime.now(timezone.utc).isoformat(),
        wall_seconds=time.monotonic() - begin, returncode=returncode,
        timeout_seconds=900, timed_out=timed_out,
        input_identity=identity, inputs_unchanged=unchanged, provider_calls=0,
        environment=".venv launcher; master verify selects established .venv-context",
        cpu_gpu="CPU only; CUDA_VISIBLE_DEVICES=-1 intentionally hides GPUs",
        random_seeds="N/A: deterministic evidence validation", git_commit=commit,
        working_tree="Reviewed local amendment pending commit",
        data_version="Frozen post-R10 campaign plus registered local amendment",
        plan=str((work / "plan-review.md").relative_to(root)),
        output=reference(output), stderr=reference(error))
    manifest.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"check": name, "returncode": returncode,
        "wall_seconds": record["wall_seconds"], "inputs_unchanged": unchanged,
        "manifest": str(manifest.relative_to(root))}), flush=True)
    if returncode or not unchanged:
        raise SystemExit(returncode or 2)
    value = json.loads(output.read_text())
    if name == "refresh-after":
        status = value["status"]
        summary = {"mission": status["mission"], "admission": value["admission"],
            "detours": status["detours_since_substantive_advance"],
            "execution": status["integration_master"]["execution"]}
    else:
        summary = {key: value[key] for key in ("execution", "ready", "running",
            "calls", "tools_fully_evaluated", "local_refresh_verified",
            "live_binding_current", "integration_complete")}
    print(json.dumps(summary), flush=True)
