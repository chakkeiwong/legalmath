"""One local actual-refresh profile; no model invocation."""
from pathlib import Path
from datetime import datetime, timezone
import json
import subprocess
import time

root = Path.cwd()
work = Path(__file__).resolve().parent
command = [".venv/bin/python", "-m", "cProfile", "-o", str(work / "refresh-before.prof"),
           "scripts/legal_mission_control.py", "refresh"]
started = datetime.now(timezone.utc).isoformat()
begin = time.monotonic()
with (work / "refresh-before.json").open("w") as out, (work / "refresh-before.stderr").open("w") as err:
    result = subprocess.run(command, cwd=root, stdout=out, stderr=err)
manifest = dict(command=command, started_utc=started,
    finished_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic()-begin,
    returncode=result.returncode, provider_calls=0, environment=".venv; CPU-only validator",
    gpu="N/A", seed="N/A", data="frozen post-R10 program and evidence",
    git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    plan=str(work.relative_to(root) / "plan-review.md"),
    output=str(work.relative_to(root) / "refresh-before.json"))
(work / "refresh-before.manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
print(json.dumps(manifest, indent=2))
raise SystemExit(result.returncode)
