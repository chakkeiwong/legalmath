"""Bounded geometry repair stages with retained results and next-action refresh."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus.successor.contracts import digest, write

BASE = ROOT / "docs/implementation/prospectus-integration-closure"
HERE = BASE / "ocr-geometry-repair-2026-10-12"
OLD = BASE / "bes-original-acquisition/portuguese-2009-reports"
PLAN = ROOT / "docs/plans/prospectus-ocr-geometry-repair-2026-10-12.md"
STAGES = ("focused", "consumer", "matched", "controller")


def read(path):
    return json.loads(path.read_text())


def verify(folder):
    for name, sha in read(folder / "manifest.json")["files"].items():
        if digest((folder / name).read_bytes()) != sha:
            raise ValueError("Retained evidence changed: " + str(folder / name))


def seal(folder):
    write(folder / "manifest.json", {"files": {str(p.relative_to(folder)): digest(p.read_bytes())
        for p in sorted(folder.rglob("*")) if p.is_file() and p != folder / "manifest.json"}})


def freeze():
    verify(OLD)
    verify(BASE / "source-report-scope-2026-10-12")
    folder = HERE / "freeze-001"
    folder.mkdir(parents=True, exist_ok=False)
    inputs = [OLD / "manifest.json", OLD / "critical-spans.json",
        OLD / "ocr-consumer-001/worker.json", OLD / "ocr-consumer-001/request.json",
        OLD / "pdf-geometry-trace-001/RESULT.md", PLAN,
        BASE / "source-report-scope-2026-10-12/manifest.json"]
    write(folder / "inputs.json", {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in inputs})
    write(folder / "controls.json", {
        "strict": "Original invalid colon must still be rejected by v1",
        "optional": "Every word preserved; only finite ordered out-of-page boxes become unknown",
        "legal_word": "A word containing a substantive negation receives exactly the same policy",
        "malformed": ["nonfinite", "inverted", "wrong-type", "missing-image", "wrong-source", "wrong-page"],
        "geometry": "No clipping; original coordinates retained; affected line bbox also null",
        "layout": "Both layout entry points refuse geometric selection on affected pages",
        "anchors_corrections": "Exact text offsets and image identity survive without spatial precision",
        "normal": "Valid v1 graphs and four matched final answers unchanged",
        "source_spans": "Eleven pre-OCR image spans; missing recognition triggers separate reviewed correction",
        "unknowns": "No promotion of authenticity, availability, source completeness or legal acceptance"})
    seal(folder)


def method():
    paths = list((ROOT / "src/legalmath/prospectus/successor").glob("*.py"))
    paths += list((ROOT / "scripts").glob("prospectus_geometry*.py"))
    paths += [ROOT / "tests/prospectus_successor/test_ocr_geometry.py"]
    return {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths if p.is_file()}


def refresh():
    verify(HERE / "freeze-001")
    for name, sha in read(HERE / "freeze-001/inputs.json").items():
        if digest((ROOT / name).read_bytes()) != sha:
            raise ValueError("Frozen input changed: " + name)
    rows = []
    ready = True
    for stage in STAGES:
        attempts = sorted((HERE / stage).glob("attempt-*/result.json"))
        result = read(attempts[-1]) if attempts else {}
        if attempts:
            verify(attempts[-1].parent)
        current = result.get("status") == "PASS" and result.get("method") == method()
        rows.append({"stage": stage, "current": current,
            "attempt": str(attempts[-1].parent.relative_to(HERE)) if attempts else None,
            "ready": ready and not current, "result": result.get("status", "NOT_RUN")})
        ready = ready and current
    state = {"phases": rows, "next": next((r["stage"] for r in rows if r["ready"]), None),
        "engineering_complete": all(r["current"] for r in rows), "legal_acceptance": "NOT_ESTABLISHED"}
    write(HERE / "next-phase.json", state)
    return state


def execute(stage, attempt):
    state = refresh()
    if state["next"] != stage:
        raise ValueError("Stage is not ready: " + stage)
    folder = HERE / stage / f"attempt-{attempt:03d}"
    folder.mkdir(parents=True, exist_ok=False)
    python = str(ROOT / ".venv/bin/python")
    commands = {
        "focused": [python, "-m", "pytest", "-q", "tests/prospectus_successor/test_ocr_geometry.py",
            "tests/prospectus_successor/test_closure_real_scan.py", "tests/prospectus_successor/test_report_scope.py",
            "--junitxml=" + str(folder / "tests.xml")],
        "consumer": [python, "-m", "scripts.prospectus_geometry_consumer", "--output", str(folder / "evidence")],
        "matched": [python, "-m", "scripts.prospectus_geometry_matched", "--output", str(folder / "evidence")],
        "controller": [python, "-m", "scripts.prospectus_geometry_ladder", "--output", str(folder / "evidence")],
    }
    limits = {"focused": 600, "consumer": 600, "matched": 1800, "controller": 7200}
    binding = method()
    start = time.monotonic()
    write(folder / "started.json", {"command": commands[stage], "method": binding, "pid": os.getpid(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "plan": str(PLAN.relative_to(ROOT)), "interpreter": python, "seeds": "N/A; deterministic replay",
        "cpu_gpu": "CPU only; GPU intentionally hidden", "timeout_seconds": limits[stage],
        "created_utc": datetime.now(timezone.utc).isoformat()})
    try:
        with (folder / "execution.log").open("w") as log:
            run = subprocess.run(commands[stage], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                timeout=limits[stage], env={**os.environ, "PYTHONPATH": str(ROOT / "src"),
                    "CUDA_VISIBLE_DEVICES": "-1", "OMP_THREAD_LIMIT": "1",
                    "LEGALMATH_OCR_PYTHON": "/home/chakwong/miniconda3/envs/tfgpu/bin/python"})
        result = {"status": "PASS" if run.returncode == 0 and binding == method() else "FAIL",
            "returncode": run.returncode}
    except Exception as error:
        result = {"status": "FAIL", "error": type(error).__name__ + ": " + str(error)}
    result.update(method=binding, wall_seconds=time.monotonic() - start)
    write(folder / "result.json", result)
    seal(folder)
    refresh()
    print(stage + " " + result["status"], flush=True)
    return result["status"] == "PASS"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "status", "run"))
    parser.add_argument("--through", choices=STAGES, default="matched")
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    HERE.mkdir(parents=True, exist_ok=True)
    with (HERE / "program.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == "freeze":
            freeze()
        if args.action == "run":
            for stage in STAGES[:STAGES.index(args.through) + 1]:
                row = next(r for r in refresh()["phases"] if r["stage"] == stage)
                if not row["current"] and not execute(stage, args.attempt):
                    return 1
        print(json.dumps(refresh()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
