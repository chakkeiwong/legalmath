"""One finite closure pass after the reviewed source-report implementation."""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from legalmath.prospectus.successor import closure_program as controller
from legalmath.prospectus.successor.contracts import digest, write

HERE = ROOT / "docs/implementation/prospectus-integration-closure/source-report-scope-2026-10-12/controller-001"


def main():
    HERE.mkdir(parents=True, exist_ok=True)
    with (HERE / "coordinator.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (HERE / "started.json").exists():
            raise ValueError("Retained controller attempt exists; inspect before any continuation")
        for name in ("statutory-2009", "committee-2009", "sustainability-2010-en", "sustainability-2010-pt"):
            folder = HERE.parent / "cases" / name / "attempt-001"
            manifest = json.loads((folder / "manifest.json").read_text())
            if any(digest((folder / path).read_bytes()) != sha for path, sha in manifest["files"].items()):
                raise ValueError("Matched consumer evidence changed")
            if json.loads((folder / "result.json").read_text())["status"] != "PASS":
                raise ValueError("Matched consumer failed")
        from scripts.prospectus_closure_attribution import report
        report(ROOT)
        start = time.monotonic()
        write(HERE / "started.json", {"pid": os.getpid(), "created_utc": datetime.now(timezone.utc).isoformat(),
            "command": "timeout 7200 .venv/bin/python -m scripts.prospectus_report_scope_ladder",
            "interpreter": sys.executable, "controller": controller.__file__, "max_dispatches": 9,
            "cpu_gpu": "CPU only; GPU intentionally hidden", "seeds": "N/A; deterministic engineering checks",
            "plan": "docs/plans/prospectus-source-report-scope-2026-10-12.md",
            "limits": "No automatic retry; existing R4 timeout retained; historical receipts preserved"})
        attempted, completed = [], []
        while len(attempted) < 9:
            state = controller.refresh(ROOT)
            write(HERE / "status.json", state)
            ready = [row for row in state["phases"] if row["can_dispatch"] and
                     not row["current"] and row["phase"] not in attempted]
            if not ready:
                break
            phase = ready[0]["phase"]
            attempted.append(phase)
            write(HERE / "progress.json", {"pid": os.getpid(), "running": phase,
                "attempted": attempted, "completed": completed, "wall_seconds": time.monotonic() - start})
            print("Starting " + phase, flush=True)
            try:
                result = controller.execute(ROOT, phase)
            except Exception as error:
                result = {"phase": phase, "execution": "COORDINATOR_CAUGHT_ERROR",
                          "error": type(error).__name__ + ": " + str(error)}
            write(HERE / (phase + ".json"), result)
            completed.append({key: result.get(key) for key in
                             ("phase", "execution", "engineering_checks", "directory", "error")})
            write(HERE / "progress.json", {"pid": os.getpid(), "running": None,
                "attempted": attempted, "completed": completed, "wall_seconds": time.monotonic() - start})
            print(phase + " " + str(result.get("engineering_checks", result.get("execution"))), flush=True)
        state = controller.refresh(ROOT)
        write(HERE / "status.json", state)
        passed = all(row["current"] and row["engineering_checks"] == "PASS" for row in state["phases"])
        write(HERE / "result.json", {"status": "PASS" if passed else "INCOMPLETE_OR_FAILED",
            "phases": completed, "all_engineering_receipts_current": passed,
            "program_complete": False, "legal_acceptance": "NOT_ESTABLISHED",
            "wall_seconds": time.monotonic() - start})
        print("Final source-report ladder " + ("PASS" if passed else "INCOMPLETE_OR_FAILED"), flush=True)
        return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
