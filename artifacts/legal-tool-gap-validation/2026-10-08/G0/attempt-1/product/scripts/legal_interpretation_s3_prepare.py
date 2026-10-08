"""Freeze verified S2 bytes before versioned S3 integration changes."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__" and Path(sys.prefix) != ROOT / ".venv":
    os.execv(str(ROOT / ".venv/bin/python"), [str(ROOT / ".venv/bin/python"), "-m",
        "scripts.legal_interpretation_s3_prepare", *sys.argv[1:]])
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


def prepare():
    from scripts import run_legal_interpretation_master as old
    from datetime import datetime, timezone
    import subprocess
    base = ROOT / "artifacts/legal-interpretation-program/successor-s3"
    target = base / "baseline.json"
    if target.exists():
        raise ValueError("S3 baseline already frozen; do not rerun S2 after editing")
    current = old.selected()
    if current["completed_phase"] != "S2":
        raise ValueError("Expected selected S2")
    result_path = old.checked(current["result"])
    verification = old.verify_attempt(result_path.parent)
    result = old.read(result_path)
    paths = {**result["method"]["source_and_tests"], **result["method"]["drivers"]}
    paths.update({str(old.POINTER.relative_to(ROOT)): old.sha(old.POINTER)})
    frozen = []
    for name, expected in sorted(paths.items()):
        source = ROOT / name
        if old.sha(source) != expected:
            raise ValueError("Cannot freeze changed S2 dependency: " + name)
        dest = base / "s2-snapshot" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("xb") as stream:
            stream.write(source.read_bytes())
        frozen.append({"original_path": name, **old.ref(dest)})
    old.save(target, {"at": datetime.now(timezone.utc).isoformat(),
        "s2_pointer": current, "s2_verification_before_edits": verification,
        "files": frozen, "source_and_tests": result["method"]["source_and_tests"],
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True),
        "scope": "Historical bytes and pre-edit verification; not current-method S2 execution"})
    print(json.dumps({"status": "FROZEN", "baseline": old.ref(target), "files": len(frozen)}))


if __name__ == "__main__":
    prepare()
