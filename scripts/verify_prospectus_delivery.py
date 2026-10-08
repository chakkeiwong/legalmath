"""Verify retained prospectus execution without repeating current phase work."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    from legalmath.prospectus.successor.contracts import read, write, digest
    from legalmath.prospectus.successor.controller import current, REL
    from legalmath.prospectus.successor.jobs import checks

    started = time.monotonic()
    out = ROOT / REL / "finalization"
    out.mkdir(parents=True, exist_ok=True)
    state = read(ROOT / REL / "state.json")
    valid = current(ROOT, state)
    if not all(valid.values()):
        raise RuntimeError("Saved run has stale receipts: " + repr(valid))
    snapshot = Path(tempfile.mkdtemp(prefix="prospectus-manuscript-before-"))
    baseline = {}
    for relative in ("docs/monograph/chapters/02f-prospectus-delivery.tex",
                     "docs/monograph/chapters/02f-prospectus-execution.tex",
                     "docs/monograph/monograph.pdf", "docs/monograph/technical-companion.pdf"):
        source = ROOT / relative
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        baseline[relative] = {"path": str(target), "sha256": digest(source.read_bytes())}
    cmd = ["python3", "-m", "scripts.prospectus_delivery", "run"]
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    (out / "resume.log").write_text(run.stdout + run.stderr)
    if run.returncode:
        raise RuntimeError("Program continuation failed")
    resumed = json.loads(run.stdout)
    if not all(row["execution"] == "REUSED" for row in resumed):
        raise RuntimeError("Unexpected new execution during current-receipt verification")
    write(out / "resume.json", {"command": cmd, "returncode": run.returncode, "phases": resumed})
    print(checks(ROOT, out, ""), flush=True)
    suite = ET.parse(out / "tests.xml").getroot()
    totals = {key: sum(int(row.get(key, "0")) for row in suite.iter("testsuite"))
              for key in ("tests", "failures", "errors", "skipped")}
    if totals["tests"] == 0 or totals["failures"] or totals["errors"]:
        raise RuntimeError("Missing or failing test suite")
    p1 = read(ROOT / state["P1"]["directory"] / "source-summary.json")
    p2 = read(ROOT / state["P2"]["directory"] / "assembly-summary.json")
    p6 = ROOT / state["P6"]["directory"]
    report = read(p6 / "integrated-report.json")
    bank = read(p6 / "bank-obligations.json")
    installed = read(p6 / "installed-package.json")
    release = read(ROOT / state["P8"]["directory"] / "release.json")
    questions = {key: {"status": value.get("status"), "qualification": value.get("qualification")}
                 for key, value in report["questions"].items()}
    if len(bank["value"]["inventory"]) != 14 or bank["value"]["may_execute_transaction"]:
        raise RuntimeError("Bank obligation preservation/clearance mismatch")
    if report["may_execute_transaction"] or report["independent_legal_acceptance"]:
        raise RuntimeError("Unexpected accepted integrated report")
    if installed["service_sha256"] != digest((ROOT / "src/legalmath/prospectus/successor/service.py").read_bytes()):
        raise RuntimeError("Installed service differs from current source")
    if release["status"] != "BLOCKED" or release["may_execute_transaction"]:
        raise RuntimeError("Unexpected release state")
    summary = {
        "status": "PASS_ENGINEERING_VERIFICATION; LEGAL_RELEASE_BLOCKED",
        "current_receipts": valid, "baseline": baseline, "tests": totals,
        "source": {"documents": len(p1["documents"]), "pages": sum(d["page_count"] for d in p1["documents"]),
                   "units": p1["units"], "references": p1["references"]},
        "assembly": p2, "questions": questions,
        "installed_service_sha256": installed["service_sha256"],
        "installed_source_path_injection": installed["source_path_injection"],
        "bank_inventory": len(bank["value"]["inventory"]),
        "independent_legal_acceptance": report["independent_legal_acceptance"],
        "release": release, "may_execute_transaction": report["may_execute_transaction"]}
    write(out / "verification.json", summary)
    write(out / "manifest.json", {
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "command": ["python3", "-m", "scripts.verify_prospectus_delivery"],
        "script_sha256": digest(Path(__file__).read_bytes()),
        "environment": sys.executable, "python": sys.version,
        "application_interpreter": str(ROOT / ".venv/bin/python"),
        "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1; GPU deliberately hidden",
        "random_seeds": "N/A deterministic engineering verification",
        "data_version": state["P0"]["method"],
        "wall_seconds": time.monotonic() - started,
        "plan": str(Path(REL) / "FINALIZATION-REVIEW.md"),
        "result_file": str(Path(REL) / "finalization/verification.json"),
        "receipts": {k: {"path": v["directory"] + "/receipt.json", "sha256": v["receipt_sha256"]}
                     for k, v in state.items()}})
    print(json.dumps({k: v for k, v in summary.items() if k != "baseline"}, indent=2))


if __name__ == "__main__":
    main()
