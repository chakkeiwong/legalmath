from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.legal_integration_master import task, MasterExecution
from scripts.legal_mission_execution import save, ref


def test_failure_blocks_only_success_descendants(tmp_path):
    tasks = [task("source"), task("independent"), task("dependent", ["source"]),
             task("assessment", after=["source"])]
    program = {"profile": "legal-mission-execution.v1", "workers": 2,
        "deadline_utc": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "protected_evidence": [], "artifact_directory": "out", "tasks": tasks}
    save(tmp_path / "program.json", program)
    execution = MasterExecution(tmp_path, "program.json", "state.json")
    execution.start("source")
    save(tmp_path / "evidence.json", {"failure": "reproduced"})
    save(tmp_path / "result.json", {"task_id": "source", "status": "FAILED", "conclusion": "Source failed",
         "next_action": "Continue independent", "evidence": [ref(tmp_path, "evidence.json")]})
    execution.finish("source", "result.json")
    view = execution.summary()
    assert set(view["ready"]) == {"independent", "assessment"}
    assert view["tasks"]["dependent"]["status"] == "DEPENDENCY_BLOCKED"
