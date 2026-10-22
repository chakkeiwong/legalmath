"""Finish only the report regressions, preserving the failed storage attempt."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from legalmath.prospectus.execution_authority import Authority, digest as authority_digest, file_hash
from legalmath.prospectus.successor import report_scope, service
from legalmath.prospectus.successor.contracts import digest
from scripts import prospectus_report_integrity as original
from scripts import prospectus_fy2010_product as fy

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
SOURCE = BASE / "attempts/source-bes-dep-09/attempt-003"
REVIEW = BASE / "reviews/report-regression-145"


def save(folder, name, value, final=False):
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode()
    original.require(original.size(folder) + len(raw) < (8 if final else 7) * 1024**2, "Resume evidence cap exceeded")
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)


def regressions(folder):
    # The old helper owns this small output directory, not the whole003 attempt.
    details = fy.prior_profiles(folder / "release-comparisons")
    source = BASE / "attempts/source-bes-dep-08/attempt-006"
    for label in ("baseline", "after"):
        values = fy.load_products(source, label)
        answer = original.consume(values)
        expected = original.read(source / (label + "-answer.json.gz"))
        original.require(answer == expected, "FY2010 complete answer changed: " + label)
        details["FY2010-" + label] = {"whole_answer_equal": True, "report_sha256": answer["report_sha256"],
            "complete_answer_sha256": digest(answer), "reference": str((source / (label + "-answer.json.gz")).relative_to(ROOT))}
    y = BASE / "attempts/source-bes-dep-06/attempt-002"
    selected = original.read(y.parent / "attempt-001/selected-reading.json")
    admitted = report_scope.admit(selected, original.read(y / "original-corrected-scope.json"))
    original.require(admitted == original.read(y / "original-corrected-admitted.json.gz") and
        report_scope.explain(admitted)[0] == original.read(y / "original-corrected-answer.json.gz"), "2009 original report changed")
    details["2009_direct_scope_and_explanation_equal"] = True
    save(folder, "regression-comparison.json", details)
    return details


def run(attempt, stage):
    a = Authority(ROOT)
    folder = a.path(attempt)
    program, tasks, _ = a.spec()
    task = tasks["source-bes-dep-09"]
    admission = original.read(folder / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    original.require(event["kind"] == "ADMIT" and event["attempt"] == attempt and
        admission["program_sha256"] == authority_digest(program) and admission["binding"] == a.binding(task), "Current unchanged admission required")
    original.require(not (folder / "outputs.json").exists(), "Sealed attempt refused")
    history = original.read(REVIEW / "history.json")
    original.require(a.retained_evidence_valid(history["event"]), "Failed003 changed")
    original.require(original.methods() == original.read(SOURCE / "final-methods.json"), "Repaired methods changed")
    results = [original.read(p) for p in (folder / "stages").glob("*/result.json")]
    starts = list((folder / "stages").glob("*/started.json"))
    original.require(len(results) == len(starts) == ("regressions", "seal").index(stage) and
                     all(r["status"] == "PASS" for r in results), "Repeated/skipped/failed stage")
    spent = sum(r["wall_seconds"] for r in results)
    save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
        "command": ["timeout", "120", ".venv/bin/python", "scripts/prospectus_report_regression_resume.py", "--attempt", attempt, "--stage", stage],
        "git_commit": admission["git_commit"], "interpreter": sys.executable, "module": service.__file__,
        "cpu_gpu": "CPU only; GPUs intentionally hidden", "random_seeds": "N/A deterministic",
        "inputs": admission["binding"], "methods": original.methods(), "history": history,
        "plan": task["dossier"], "result": str((folder / "result.json").relative_to(ROOT))})
    tick, error, details = time.monotonic(), None, None
    try:
        if stage == "regressions":
            details = regressions(folder)
        else:
            original.require((folder / "RESULT.md").is_file(), "Actual substantive result review required")
            details = {"report_integrity_and_original_2010": str(SOURCE.relative_to(ROOT)),
                       "completed_regressions": True, "installed_repair_evaluated": False}
        original.require(original.methods() == original.read(SOURCE / "final-methods.json") and admission["binding"] == a.binding(task), "Inputs/methods changed")
        original.require(spent + time.monotonic() - tick < 240 and history["seconds"] + spent + time.monotonic() - tick < 960,
                         "Cumulative execution cap exceeded")
        original.require(original.size(folder) < 8 * 1024**2 and original.size(folder) + history["bytes"] < 104 * 1024**2,
                         "Cumulative evidence cap exceeded")
    except BaseException as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
        save(folder, "stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, True)
    result = {"status": "FAIL" if error else "PASS", "stage": stage, "error": error,
              "wall_seconds": time.monotonic() - tick, "details": details}
    save(folder, "stages/" + stage + "/result.json", result, True)
    if error or stage == "seal":
        save(folder, "result.json", {**result, "task": task["id"], "task_complete": False,
            "installed_repair_evaluated": False, "independent_acceptance": False}, True)
        save(folder, "outputs.json", {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*")) if p.is_file()}, True)
    print(json.dumps({k: result[k] for k in ("status", "stage", "error", "wall_seconds")}))
    return int(error is not None)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--attempt", required=True)
    p.add_argument("--stage", choices=("regressions", "seal"), required=True)
    args = p.parse_args()
    def block(event, _):
        if event in ("subprocess.Popen", "os.system", "os.fork", "os.posix_spawn", "socket.connect"):
            raise RuntimeError("Resume forbids native/network processes: " + event)
    sys.addaudithook(block)
    def expired(*_):
        raise TimeoutError("Report resume stage exceeded115 seconds")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(115)
    try:
        return run(args.attempt, args.stage)
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
