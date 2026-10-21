"""Retain the reviewed preparation without adopting code or allocating calls."""
from datetime import datetime, timezone
import fcntl
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts import legal_mission_control as control
from scripts.legal_mission_execution import read, ref, require, save

WORK = Path(__file__).resolve().parent
MISSION = ROOT / "docs/implementation/legal-mission-control/mission.json"
IDENTIFIER = "post-p10-continuation-20261018-preparation"
REASON = (
    "Continue the existing authenticated P10 worker and its eligible consumers. "
    "The corrected census is 70 validated, six failed and nine unprocessed. "
    "Use the reviewed staged supplement to prepare independent failed-account, "
    "evidence-packing/capacity and P14/Gatecoin receipt repairs; adoption requires "
    "settled old writers, passing controls and explicit available owner authority. "
    "No call, attempt, repair or deadline allocation was renewed."
)


def main():
    paths = [
        ROOT / "docs/implementation/legal-mission-control/results/post-p10-continuation-2026-10-18.md",
        WORK / "evidence/result.json",
        WORK / "originals/result.json",
        WORK / "p10-census/result.json",
    ]
    with MISSION.with_suffix(".execution.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        mission = read(MISSION)
        require(mission["current_task"] == "product-contribution", "Admission changed")
        previous = [row for row in mission["history"] if row["id"] == IDENTIFIER]
        evidence = [ref(ROOT, path) for path in paths]
        if previous:
            require(len(previous) == 1 and previous[0]["result_evidence"] == evidence,
                    "Preparation history conflicts with current evidence")
        else:
            mission["history"].append({
                "id": IDENTIFIER,
                "task_id": "product-contribution",
                "kind": "product_evaluation",
                "outcome": "no_advance",
                "next_task": "product-contribution",
                "next_task_reason": REASON,
                "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                "decision": (
                    "Zero-provider-call production diagnostics corrected the P10 census, "
                    "reproduced evidence packing/capacity limits and validated exact-original "
                    "P14/Gatecoin responses offline. Same-master continuation supplement "
                    "reviewed and staged; recovery/adoption hook not installed. "
                    "No legal integration or account repair completion claimed."
                ),
                "result_evidence": evidence,
            })
            mission["next_task_reason"] = REASON
            control.validate(mission, read(ROOT / "docs/implementation/legal-mission-control/tools.json"), ROOT)
            save(MISSION, mission)
    command = [".venv/bin/python", "scripts/legal_mission_control.py", "refresh"]
    with (WORK / "mission-refresh.json").open("w") as output, (WORK / "mission-refresh.stderr").open("w") as error:
        # Match the existing master's reviewed allowance for historical validation.
        process = subprocess.run(command, cwd=ROOT, stdout=output, stderr=error, timeout=900)
    result = {
        "history_id": IDENTIFIER,
        "command": command,
        "exit_code": process.returncode,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "refresh_output": ref(ROOT, WORK / "mission-refresh.json"),
        "refresh_error": ref(ROOT, WORK / "mission-refresh.stderr"),
        "adopted": False,
        "provider_calls": 0,
    }
    save(WORK / "mission-record.json", result)
    print(result)
    require(process.returncode == 0, "Mission refresh failed; inspect retained output")


if __name__ == "__main__":
    main()
