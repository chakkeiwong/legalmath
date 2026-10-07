"""Execute adoption, regression, identical replay and receipt verification offline."""
import json
import os
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REL = Path("docs/implementation/prospectus-adoption")


def main():
    base = ROOT / REL / "verification"
    base.mkdir(parents=True, exist_ok=True)
    index = 1
    while (base / f"attempt-{index:03d}").exists():
        index += 1
    out = base / f"attempt-{index:03d}"
    out.mkdir()
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "-1"}
    runner = ["python3", "-m", "scripts.prospectus_delivery", "--program", "adoption"]
    commands = [
        ("execution", [*runner, "run"]),
        ("regression", [*runner, "check", "--junitxml=" + str(out / "tests.xml")]),
        ("replay", [*runner, "run"]),
        ("status", [*runner, "status"]),
    ]
    records = []
    failure = None
    for name, argv in commands:
        started = time.monotonic()
        try:
            run = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=1800)
            (out / (name + ".log")).write_text(run.stdout + run.stderr)
            records.append({"name": name, "command": argv, "returncode": run.returncode,
                            "wall_seconds": time.monotonic() - started})
            if run.returncode:
                raise ValueError(name + " command failed; see preserved log")
            if name != "regression":
                data = json.loads(run.stdout)
                (out / (name + ".json")).write_text(json.dumps(data, indent=2) + "\n")
                if name == "replay" and any(r["execution"] != "REUSED" for r in data):
                    raise ValueError("Identical replay did not reuse every phase")
                if name == "status" and not all(r["current"] for r in data["phases"]):
                    raise ValueError("A phase remains stale")
            print(name + ": PASS", flush=True)
        except Exception as exc:
            failure = str(exc)
            (out / "failure.json").write_text(json.dumps({"command": argv, "error": failure}) + "\n")
            break
    import hashlib
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    state = json.loads((ROOT / REL / "state.json").read_text()) if (ROOT / REL / "state.json").exists() else {}
    counts = None
    if (out / "tests.xml").exists():
        suites = ET.parse(out / "tests.xml").getroot()
        counts = {key: sum(int(s.get(key, "0")) for s in suites.iter("testsuite"))
                  for key in ("tests", "failures", "errors", "skipped")}
    manifest = {
        "status": "FAILED" if failure else "BOUNDED_ENGINEERING_VERIFIED; RELEASE_NOT_ACCEPTED",
        "failure": failure, "commands": records,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "verifier_sha256": sha(Path(__file__)),
        "environment": str(ROOT / ".venv/bin/python"), "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1",
        "random_seeds": "Hypothesis derandomize=True, 30 examples x 25 steps; Z3 random_seed=0; layout upstream pretrained weights",
        "plan": "docs/plans/prospectus-adoption-execution-2026-10-07.md",
        "result_file": str(REL / "RESULT.md"), "tests": counts,
        "phase_receipts": {phase: {key: row[key] for key in ("directory", "receipt_sha256", "method", "input_identity")}
                           for phase, row in state.items()},
        "outputs": {p.name: sha(p) for p in out.iterdir() if p.is_file()},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"status": manifest["status"], "tests": counts, "directory": str(out)}, indent=2))
    if failure:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
