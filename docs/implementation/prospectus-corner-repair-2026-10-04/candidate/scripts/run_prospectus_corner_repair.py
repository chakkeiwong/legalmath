"""Execute and record the isolated prospectus corner-case repair phases."""
from pathlib import Path
from collections import Counter
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/implementation/prospectus-corner-repair-2026-10-04"
CANDIDATE = OUT / "candidate"
DATA = ROOT / "docs/prospectus/corner-cases-2026-10-04"
OLD = ROOT / "docs/implementation/prospectus-corner-cases-2026-10-04"
PLAN = ROOT / "docs/plans/prospectus-corner-repair-execution-2026-10-04.md"


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def method():
    if not CANDIDATE.exists():
        return {}
    return {str(p.relative_to(CANDIDATE)): sha(p) for prefix in ("src", "tests", "scripts")
            for p in sorted((CANDIDATE / prefix).rglob("*.py")) if "__pycache__" not in p.parts}


def environment():
    env = dict(os.environ)
    env["CUDA_VISIBLE_DEVICES"] = "-1"
    env["PYTHONPATH"] = str(CANDIDATE / "src") + os.pathsep + str(CANDIDATE)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def command(argv, folder, name, cwd=ROOT, timeout=180):
    start = time.monotonic()
    with (folder / (name + ".log")).open("w") as log:
        try:
            run = subprocess.run(argv, cwd=cwd, env=environment(), stdout=log,
                                 stderr=subprocess.STDOUT, timeout=timeout)
            code = run.returncode
        except subprocess.TimeoutExpired:
            code = 124
    return {"command": argv, "cwd": str(cwd), "exit_code": code,
            "wall_seconds": round(time.monotonic() - start, 3),
            "log": relative(folder / (name + ".log"))}


def prepare(folder, args):
    check = command([sys.executable, "-m", "scripts.verify_prospectus_corner_archive"],
                    folder, "baseline-archive", timeout=90)
    if check["exit_code"]:
        return {"status": "FAIL", "reason": "Baseline preservation veto", "check": check}
    freeze = read(ROOT / "docs/prospectus/difficulty-2026-10-04/freeze.json")
    archive = ROOT / "docs/prospectus/difficulty-2026-10-04/method.zip"
    assert sha(archive) == freeze["archive_sha256"]
    if not CANDIDATE.exists():
        CANDIDATE.mkdir()
        # Copy only test support and original evidence; no symlink writes to old runs.
        for directory in ("tests", "scripts"):
            shutil.copytree(ROOT / directory, CANDIDATE / directory,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy2(ROOT / "pyproject.toml", CANDIDATE / "pyproject.toml")
        with zipfile.ZipFile(archive) as package:
            for name in package.namelist():
                target = (CANDIDATE / name).resolve()
                assert target.is_relative_to(CANDIDATE) and not target.is_symlink()
            package.extractall(CANDIDATE)
        for name in ("docs/specs", "docs/prospectus"):
            shutil.copytree(ROOT / name, CANDIDATE / name,
                            ignore=shutil.ignore_patterns("__pycache__"))
        fixture = "docs/implementation/bond-loss-absorption-classification/execution/reader-gap-diagnostic.json"
        target = CANDIDATE / fixture
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / fixture, target)
        # Extra runtime package data are copied separately from the frozen Python method.
        for source in (ROOT / "src").rglob("*"):
            if source.is_file() and source.suffix != ".pyc" and "__pycache__" not in source.parts:
                target = CANDIDATE / source.relative_to(ROOT)
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
        for name, expected in freeze["method"].items():
            assert sha(CANDIDATE / name) == expected, name
        write(OUT / "candidate-baseline.json",
              {"at": now(), "archive_sha256": sha(archive), "files": method()})
    versions = {}
    for name in ("pytest", "fitz", "pypdf", "jsonschema", "z3", "hypothesis"):
        spec = importlib.util.find_spec(name)
        versions[name] = spec.origin if spec else None
    return {"status": "PASS", "baseline": check, "candidate": relative(CANDIDATE),
            "frozen_files": len(freeze["method"]),
            "archive_entries": len(zipfile.ZipFile(archive).namelist()),
            "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
            "packages": versions, "ocr": shutil.which("tesseract"),
            "latex": shutil.which("pdflatex"),
            "compute": "CPU only; CUDA_VISIBLE_DEVICES=-1; no device probe"}


def diagnose(folder, args):
    result = []
    for key, pages, anchors in [
        ("jur-more-hypo-1314069", [140, 144, 145],
         ["If the Issuer has insufficient", "9.2.3", "the Noteholders shall have no further claim"]),
        ("jur-more-hypo-843665", [121],
         ["If the Notes cannot be redeemed in full"])]:
        records = read(DATA / "sources" / key / "pages.json")["pages"]
        result.append({"key": key, "pages": [records[p - 1] for p in pages], "anchors": anchors})
    write(folder / "original-passages.json", result)
    failures = read(OLD / "regression-findings.json")
    quotes = []
    for row in failures["findings"]:
        output = read(OLD / "run-001" / (row["run"] + ".json"))
        quotes.append({"check": row["id"], "matches": [e for e in output["evidence"]
                      if " ".join(row["quote"].split()) in " ".join(e["quote"].split())]})
    write(folder / "baseline-segments.json", quotes)
    return {"status": "PASS", "known_failed_checks": failures["failed"],
            "passages": relative(folder / "original-passages.json"),
            "segments": relative(folder / "baseline-segments.json")}


def test(folder, args):
    files = (["tests/prospectus/test_corner_repair.py",
              "tests/prospectus/test_loss_absorption.py",
              "tests/prospectus/test_loss_absorption_repair.py"]
             if args.suite == "focused" else ["tests/prospectus"])
    run = command([sys.executable, "-m", "pytest", *files, "-q",
                   "--junitxml=" + str(folder / "pytest.xml")],
                  folder, "pytest", cwd=CANDIDATE, timeout=300)
    return {"status": "PASS" if run["exit_code"] == 0 else "FAIL",
            "suite": args.suite, **run}


def delegated(phase, folder, args):
    from scripts import prospectus_corner_repair_phases as phases
    return getattr(phases, phase)(folder, args)


def refresh(receipt, receipt_path):
    state_path = OUT / "state.json"
    state = read(state_path) if state_path.exists() else {"phases": []}
    state["phases"].append({"phase": receipt["phase"], "status": receipt["result"]["status"],
                            "receipt": relative(receipt_path), "sha256": sha(receipt_path),
                            "candidate_method": receipt["candidate_method"]})
    write(state_path, state)
    next_step = {
        "prepare": "Inspect preserved spans with diagnose, then implement the isolated clause repair.",
        "diagnose": "Implement action-bound cancellation and condition witnesses; run focused tests.",
        "test": "Repair any failed checks; when focused tests pass, execute intake and legal phases, then the full suite.",
        "intake": "Keep missing OCR/dependencies explicit; execute the source-bound legal evaluator.",
        "legal": "Resolve implementation failures and then acquire specific missing public originals.",
        "fetch": "Review retained originals; update candidate premises only when supported, then compare.",
        "compare": "Repair regressions or preserve remaining source gaps; finalize the report and LaTeX addendum.",
        "finalize": "Verify baseline, candidate results, report and patch.",
        "verify": "Execution recorded. Remaining independent legal review and inaccessible originals stay open."
    }[receipt["phase"]]
    (OUT / "NEXT-PHASE.md").write_text(
        "# Refreshed next phase\n\nLast phase: " + receipt["phase"] +
        "\n\nStatus: " + receipt["result"]["status"] + "\n\n" + next_step +
        "\n\nA failed candidate triggers repair. Source corruption or invalid evidence "
        "invalidates the run. Missing legal adjudication blocks promotion, not local work.\n"
        "\nReceipt: " + relative(receipt_path) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "diagnose", "test", "intake", "legal",
                                        "fetch", "compare", "finalize", "verify"))
    parser.add_argument("--suite", choices=("focused", "all"), default="focused")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with (ROOT / "docs/implementation/prospectus-evidence-closure/.lock").open("a+") as lock:
        # prepare invokes the old lock-owning verifier, so check it before taking this lock.
        if args.phase != "prepare":
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        folder = OUT / "phases" / f"{len(list((OUT/'phases').glob('*'))) + 1:03d}-{args.phase}"
        folder.mkdir(parents=True, exist_ok=False)
        start = time.monotonic()
        receipt = {"phase": args.phase, "started": now(), "plan": relative(PLAN),
                   "plan_sha256": sha(PLAN), "command": [sys.executable, "-m",
                   "scripts.run_prospectus_corner_repair", *sys.argv[1:]],
                   "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                   "compute": "CPU only; CUDA_VISIBLE_DEVICES=-1; no device probe",
                   "seeds": "N/A deterministic", "python_executable": sys.executable}
        try:
            result = globals()[args.phase](folder, args) if args.phase in {
                "prepare", "diagnose", "test"} else delegated(args.phase, folder, args)
        except Exception as exc:
            result = {"status": "FAIL", "error": type(exc).__name__ + ": " + str(exc)}
        receipt.update(result=result, candidate_method=method(), finished=now(),
                       wall_seconds=round(time.monotonic() - start, 3),
                       outputs={str(p.relative_to(folder)): sha(p)
                                for p in folder.rglob("*") if p.is_file()})
        write(folder / "receipt.json", receipt)
        refresh(receipt, folder / "receipt.json")
        print(json.dumps({"phase": args.phase, "receipt": relative(folder / "receipt.json"),
                          **result}, ensure_ascii=False, indent=2))
        raise SystemExit(1 if result["status"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
