"""Local, resumable successor to the OCR round. No network actions."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, fcntl, hashlib, json, os, shutil, subprocess, sys, time
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/implementation/prospectus-closure-refresh-2026-10-05"
PLAN = ROOT / "docs/plans/prospectus-closure-refresh-2026-10-05.md"
PRIOR = ROOT / "docs/implementation/prospectus-closure-2026-10-05"
PHASES = ("baseline", "prepare", "checks", "admit", "document", "verify")
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["OMP_THREAD_LIMIT"] = "1"
def read(path):
    return json.loads(Path(path).read_text())
def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))
def checked_path(name):
    path = (ROOT / name).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Path outside worktree: " + name)
    return path
def require(ok, why):
    if not ok:
        raise ValueError(why)
def verify_bindings(bindings):
    for name, digest in bindings.items():
        path = checked_path(name)
        require(path.is_file() and sha(path) == digest, "Changed/missing bound file: " + name)
    return len(bindings)
def method():
    paths = sorted((ROOT / "scripts").glob("prospectus_refresh*.py"))
    paths += sorted((ROOT / "tests/closure_refresh").glob("test_*.py"))
    paths += [PLAN]
    return {relative(p): sha(p) for p in paths}
def receipts():
    return sorted((OUT / "phases").glob("*/receipt.json"))
def history():
    records = []
    for path in receipts():
        item = read(path)
        verify_bindings(item["outputs"])
        verify_bindings({name:digest for name,digest in item["inputs"].items() if name not in item.get("input_snapshots",{})})
        verify_bindings({saved:item["inputs"][name] for name,saved in item.get("input_snapshots",{}).items()})
        verify_bindings(item.get("previous_receipts",{}))
        for name, digest in item["method"].items():
            snapshot = path.parent / "method" / name
            require(snapshot.is_file() and sha(snapshot) == digest, "Method snapshot changed")
        records.append((path, item))
    successful = [p for p,r in records if r["phase"] == "baseline" and r["status"] == "PASS"]
    if successful:
        verify_bindings(read(successful[-1].parent / "baseline.json")["files"])
    return records
def latest(phase, current=False):
    matches = [p for p in receipts() if read(p)["phase"] == phase]
    require(bool(matches), "Missing prerequisite phase: " + phase)
    path = matches[-1]; record = read(path)
    require(record["status"] == "PASS", "Latest prerequisite failed: " + phase)
    verify_bindings(record["outputs"])
    if current:
        require(record["method"] == method(), "Stale " + phase + " method; rerun checks and affected phases")
        verify_bindings(record["inputs"])
    return path.parent
def run_command(argv, folder, label, timeout=180):
    start = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    (folder / (label + ".log")).write_text(result.stdout + result.stderr)
    write(folder / (label + ".json"), {
        "command": argv, "exit_code": result.returncode,
        "wall_seconds": time.monotonic() - start,
        "log": relative(folder / (label + ".log")),
        "log_sha256": sha(folder / (label + ".log"))})
    require(result.returncode == 0, label + " failed; see phase log")
    return result.stdout
def refresh(path, record):
    phase = record["phase"]
    if record["status"] != "PASS":
        following = phase
        why = "Repair the recorded failure, then rerun this phase. Earlier work remains preserved."
    elif phase == "verify":
        following = None
        why = "This bounded round is verified. See remaining-gaps.json for source, independent-review and actual-fact prerequisites."
    else:
        following = PHASES[PHASES.index(phase) + 1]
        why = {
            "prepare": "Implement/review the bounded repair and record original-page review before admission.",
            "checks": "Run source admission and the frozen-reader comparison with the passing method.",
            "admit": "Write source-based results and render the separate addendum.",
            "document": "Inspect the rendered pages and record review, then verify the round."
        }.get(phase, "Execute the next source and extraction phase.")
    command = "python3 -m scripts.prospectus_refresh " + following if following else None
    result = {"last_phase": phase, "status": record["status"], "receipt": relative(path),
              "next_phase": following, "command": command, "action": why,
              "production_promotion": False, "new_http_requests": 0}
    write(OUT / "next-phase.json", result)
    (OUT / "NEXT-PHASE.md").write_text(
        "# Refreshed closure: next phase\n\n" + why + "\n\nLast receipt: " +
        relative(path) + "\n\n" + ("Command: " + command + "\n\n" if command else "") +
        "Independent legal adjudication, complete applicable sources, actual facts and intended-use acceptance remain open.\n")
    print(json.dumps(result, indent=2))
def execute(phase):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / ".lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        prior = history()
        if phase != "baseline":
            latest(PHASES[PHASES.index(phase) - 1])
        if phase == "baseline":
            require(not any(r["status"] == "PASS" and r["phase"] == "baseline" for _,r in prior), "Baseline already preserved; continue with the next phase")
        number = max([int(p.name.split("-")[0]) for p in (OUT / "phases").glob("[0-9]*-*") if p.is_dir()] + [0]) + 1
        folder = OUT / "phases" / f"{number:03d}-{phase}"
        folder.mkdir(parents=True)
        start = time.monotonic()
        record = {
            "phase": phase, "started": datetime.now(timezone.utc).isoformat(),
            "command": [sys.executable, "-m", "scripts.prospectus_refresh", phase],
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "python": sys.executable, "python_version": sys.version,
            "compute": "CPU; CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden",
            "seeds": "N/A deterministic", "method": method(), "inputs": {},
            "plan": relative(PLAN), "result_directory": relative(folder),
            "new_http_requests": 0, "prior_receipts_verified": len(prior),
            "previous_receipts": {relative(p):sha(p) for p,_ in prior}, "input_snapshots": {}}
        for name in record["method"]:
            dest = folder / "method" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        try:
            from scripts import prospectus_refresh_work as work
            record["inputs"] = work.inputs(phase)
            verify_bindings(record["inputs"])
            for name in record["inputs"]:
                if checked_path(name).is_relative_to(OUT):
                    dest = folder / "inputs" / name
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(ROOT / name,dest)
                    record["input_snapshots"][name] = relative(dest)
            getattr(work, phase)(folder)
            record["status"] = "PASS"
        except Exception as exc:
            record.update(status="FAIL", error=type(exc).__name__ + ": " + str(exc))
            raise
        finally:
            record["wall_seconds"] = time.monotonic() - start
            record["outputs"] = {
                relative(p): sha(p) for p in sorted(folder.rglob("*"))
                if p.is_file() and "method" not in p.relative_to(folder).parts and p.name != "receipt.json"}
            write(folder / "receipt.json", record)
            refresh(folder / "receipt.json", record)
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=(*PHASES, "status", "image", "run"))
    parser.add_argument("path", nargs="?")
    args = parser.parse_args()
    if args.phase == "image":
        import base64
        path = checked_path(args.path)
        require(path.is_relative_to(OUT) and path.suffix == ".png", "Image outside refresh output")
        print(base64.b64encode(path.read_bytes()).decode())
    elif args.phase == "status":
        history()
        print(json.dumps(read(OUT / "next-phase.json"), indent=2))
    elif args.phase == "run":
        while True:
            state = read(OUT / "next-phase.json") if (OUT / "next-phase.json").exists() else {"next_phase": "baseline"}
            phase = state["next_phase"]
            if phase is None:
                break
            if phase == "checks" and not (OUT / "source-review.json").exists():
                print("Original-page review pending: prepare source-review.json before checks/admission.")
                break
            if phase == "verify" and not (OUT / "rendered-review.json").exists():
                print("Rendered addendum review pending: inspect pages and record rendered-review.json.")
                break
            execute(phase)
    else:
        execute(args.phase)
if __name__ == "__main__":
    main()
