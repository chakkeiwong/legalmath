"""Bounded S-phase executor with independent history and explicit evidence waits."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import zipfile

from . import master_control as c
from . import evidence_continuation as old

ROOT = c.ROOT
OUT = ROOT / "docs/implementation/prospectus-evidence-closure"
DATA = ROOT / "docs/prospectus/evidence-closure"
PLAN = ROOT / "docs/plans/prospectus-evidence-closure.md"
PREFIX = c.PREFIX + ["close"]
PHASES = tuple("S" + str(i) for i in range(8))
DEPENDENCIES = {"S0": (), "S1": ("S0",), "S2": ("S1",), "S3": ("S1",),
                "S4": ("S1",), "S5": ("S1", "S3"), "S6": ("S2", "S4", "S5"),
                "S7": ("S1", "S2", "S3", "S4", "S5", "S6")}
INPUTS = {"S0": (), "S1": ("admissions.json", "decisions.json", "assessment.json", "source-inputs.json"),
          "S2": ("public-queue.json", "source-work-reviews.json"), "S3": ("facts.json", "assessment.json"),
          "S4": ("clause-reviews.json",), "S5": ("scenarios.json", "mechanism-reviews.json"),
          "S6": ("challenge.json", "challenge-evidence.json", "challenge-adjudication.json"), "S7": ("human-review.json",)}
EVALUATED = {"PASS", "QUALIFIED", "WAITING_EVIDENCE", "WAITING_PROTOCOL", "WAITING_HUMAN"}


def policy():
    return c.read(OUT / "allowlist.json")


def method():
    paths = list((ROOT / "src/legalmath").rglob("*.py")) + list((ROOT / "tests/prospectus").glob("*.py"))
    paths += list((ROOT / "tests/compliance").glob("*.py"))
    paths += [ROOT / "scripts/run_prospectus_evidence_master.py", PLAN, OUT / "allowlist.json", OUT / "execution-review.md", OUT / "calculation-protocol.md", ROOT / "docs/plans/prospectus-public-recovery-2026-10-04.md"]
    return {c.relative(p): c.sha(p) for p in sorted(paths)}


def state():
    path = OUT / "state.json"
    return c.read(path) if path.exists() else {"version": "prospectus-closure.v1", "wall_seconds": 0,
                                              "phases": {}, "attempts": []}


def artifacts(directory):
    return {str(p.relative_to(directory)): c.sha(p) for p in sorted(directory.rglob("*"))
            if p.is_file() and p != directory / "receipt.json" and "__pycache__" not in p.parts}


def protected():
    paths = [p for base in (c.OUT, c.DATA, old.OUT, old.DATA) for p in base.rglob("*")
             if p.is_file() and not p.name.startswith(".") and "__pycache__" not in p.parts]
    inv = c.read(old.BASE / "inventory.json")
    paths += [ROOT / d[k] for d in inv["documents"].values() for k in ("original", "text")]
    return {c.relative(p): c.sha(p) for p in sorted(set(paths))}


def preserve():
    actual = protected()
    path = OUT / "baseline.json"
    if path.exists():
        if c.read(path)["files"] != actual:
            raise ValueError("Protected historical campaign or source changed")
    else:
        # Verify old receipts by their preserved output bindings, independent of current code.
        old.verify_parent()
        for item in old.state()["attempts"]:
            folder = ROOT / item["directory"]
            if c.sha(folder / "receipt.json") != item["receipt_sha256"] or c.read(folder / "receipt.json")["outputs"] != old.artifacts(folder):
                raise ValueError("Continuation receipt changed")
        c.write(path, {"commit": "2d6b737b", "at": c.now(), "files": actual}, exclusive=True)
        archive = OUT / "baseline-method.zip"
        subprocess.run(["git", "archive", "--format=zip", "--output=" + str(archive), "2d6b737b", "src/legalmath",
                        "tests/prospectus", "tests/compliance", "scripts/run_prospectus_evidence_master.py"],
                       cwd=ROOT, check=True, capture_output=True, timeout=30)
        c.write(OUT / "baseline-method.json", {"commit": "2d6b737b", "sha256": c.sha(archive)}, exclusive=True)
    archive_record = c.read(OUT / "baseline-method.json")
    if c.sha(OUT / "baseline-method.zip") != archive_record["sha256"]:
        raise ValueError("Baseline method archive changed")
    return {"files": len(actual), "snapshot_sha256": c.sha(path)}


def linked_inputs(value):
    """Bind local evidence files as well as the JSON that names them."""
    result = {}
    def visit(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if key in {"path", "original", "text", "render_path", "acquisition_receipt"} and isinstance(child, str):
                    path = (ROOT / child).resolve()
                    if path.is_relative_to(ROOT.resolve()):
                        result[str(path.relative_to(ROOT))] = c.sha(path) if path.is_file() else None
                    else:
                        result[child] = "OUTSIDE_CHECKOUT"
                elif isinstance(child, (dict, list)):
                    visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
    visit(value)
    return result


def fingerprint(phase, current):
    inputs = {name: c.sha(DATA / name) if (DATA / name).exists() else None for name in INPUTS[phase]}
    evidence = {name: linked_inputs(c.read(DATA / name)) for name in INPUTS[phase] if (DATA / name).exists()}
    return c.digest({"method": method(), "inputs": inputs, "linked_evidence": evidence,
                     "baseline": c.sha(OUT / "baseline.json") if (OUT / "baseline.json").exists() else None,
                     "upstream": {p: current["phases"].get(p, {}).get("receipt_sha256") for p in DEPENDENCIES[phase]}})


def external_valid(receipt):
    for name, expected in receipt.get("external_outputs", {}).items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file() or c.sha(path) != expected:
            return False
    return True


def current_phase(phase, current):
    item = current["phases"].get(phase)
    if not item or item["status"] not in EVALUATED or item["inputs"] != fingerprint(phase, current):
        return False
    if any(not current_phase(p, current) for p in DEPENDENCIES[phase]):
        return False
    folder = ROOT / item["directory"]
    return (folder / "receipt.json").exists() and c.sha(folder / "receipt.json") == item["receipt_sha256"] and c.read(folder / "receipt.json")["outputs"] == artifacts(folder) and external_valid(c.read(folder / "receipt.json"))


def refresh(current, *, save=True):
    stale = [p for p in PHASES if not current_phase(p, current)]
    ready = [p for p in stale if all(current_phase(q, current) for q in DEPENDENCIES[p])]
    remaining, evaluated = [], []
    failures = []
    for p, item in current["phases"].items():
        if not current_phase(p, current):
            if item["status"] in {"FAILED", "INTERRUPTED"}:
                failures.append({"phase": p, "result": item["directory"] + "/result.json"})
                remaining.extend(c.read(ROOT / item["directory"] / "result.json").get("remaining", []))
            continue
        result = c.read(ROOT / item["directory"] / "result.json")
        evaluated.append({"phase": p, "status": result["status"], "result": item["directory"] + "/result.json"})
        remaining.extend(result.get("remaining", []))
    value = {"ready": ready, "stale": stale, "evaluated": evaluated,
             "failures": failures, "next_command": " ".join(PREFIX + (["run"] if ready else ["status"])),
             "remaining": list(dict.fromkeys(remaining)), "actual_permission": False,
             "all_gaps_closed": not stale and not remaining}
    if save:
        c.write(OUT / "next-phase-plan.json", value)
    return value


def command(argv, log, *, timeout=900):
    limit = min(timeout, policy()["max_command_seconds"])
    started = time.monotonic()
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "-1", "PYTHONPATH": str(ROOT / "src")}
    with log.open("w") as stream:
        process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=limit)
        except BaseException:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
    if code:
        raise ValueError("Command failed: " + " ".join(argv) + "; see " + str(log))
    return {"argv": argv, "wall_seconds": time.monotonic() - started, "exit_code": code}


def execute(phase, folder, current):
    from .closure_phases import execute as action
    return action(phase, folder, current)


def seal(phase, folder, item, result, elapsed, current):
    c.write(folder / "result.json", result, exclusive=True)
    receipt = {"phase": phase, "inputs": item["inputs"], "status": result["status"],
               "wall_seconds": elapsed, "outputs": artifacts(folder), "external_outputs": result.get("external_outputs", {})}
    c.write(folder / "receipt.json", receipt, exclusive=True)
    completed = {**item, "phase": phase, "status": result["status"], "receipt_sha256": c.sha(folder / "receipt.json")}
    current["phases"][phase] = completed
    if not any(x["directory"] == completed["directory"] for x in current["attempts"]):
        current["attempts"].append(completed)
        current["wall_seconds"] += elapsed
    c.write(OUT / "state.json", current)
    refresh(current)
    return completed


def run_phase(phase, current):
    if current_phase(phase, current):
        return current["phases"][phase]
    if any(not current_phase(p, current) for p in DEPENDENCIES[phase]):
        raise ValueError("Stale predecessor")
    inputs = fingerprint(phase, current)
    failed = [x for x in current["attempts"] if x["phase"] == phase and x["inputs"] == inputs and x["status"] in {"FAILED", "INTERRUPTED"}]
    if len(failed) >= policy()["max_failures_per_input"]:
        raise ValueError("Identical failure budget exhausted")
    available = policy()["max_execution_seconds"] - current["wall_seconds"]
    if available <= 0:
        raise ValueError("Execution budget exhausted")
    base = OUT / "phases" / phase
    folder = base / f"attempt-{len(list(base.glob('attempt-*'))) + 1:03d}"
    folder.mkdir(parents=True, exist_ok=False)
    item = {"status": "RUNNING", "directory": c.relative(folder), "inputs": inputs, "started_at": c.now()}
    current["phases"][phase] = item
    c.write(OUT / "state.json", current)
    started = time.monotonic()
    manifest = {"git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "command": " ".join(PREFIX + ["phase", phase]), "invocation": " ".join(sys.argv),
                "python": sys.version, "cpu_only": True, "gpu": "intentionally hidden", "seeds": "N/A deterministic",
                "plan": c.relative(PLAN), "method": method(), "inputs": inputs, "started_at": item["started_at"]}
    c.write(folder / "manifest.json", manifest)
    def deadline(*unused):
        raise TimeoutError("Phase execution time budget exceeded")
    prior = signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, min(available, policy()["max_command_seconds"]))
    try:
        result = execute(phase, folder, current)
        if inputs != fingerprint(phase, current):
            raise ValueError("Method or inputs changed during phase")
        if result["status"] not in EVALUATED:
            raise ValueError("Unknown phase result")
    except Exception as exc:
        result = {"status": "FAILED", "remaining": [phase + ": " + str(exc)],
                  "repair_required": True, "research_direction_rejected": False}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prior)
    elapsed = time.monotonic() - started
    c.write(folder / "manifest.json", {**manifest, "wall_seconds": elapsed, "result": c.relative(folder / "result.json")})
    c.write(folder / "phase-review.json", {"repairs_executed": result.get("repairs", []),
        "next_dependencies": list(DEPENDENCIES[phase]), "remaining": result.get("remaining", []),
        "result_sha256": c.digest(result), "candidate_failure_is_direction_rejection": False})
    return seal(phase, folder, item, result, elapsed, current)


def recover(current):
    for phase, item in list(current["phases"].items()):
        if item["status"] != "RUNNING":
            continue
        folder = ROOT / item["directory"]
        if (folder / "receipt.json").exists():
            receipt = c.read(folder / "receipt.json")
            if receipt["outputs"] != artifacts(folder):
                raise ValueError("Interrupted receipt changed")
            completed = {**item, "phase": phase, "status": receipt["status"], "receipt_sha256": c.sha(folder / "receipt.json")}
            current["phases"][phase] = completed
            if not any(x["directory"] == item["directory"] for x in current["attempts"]):
                current["attempts"].append(completed)
                current["wall_seconds"] += receipt["wall_seconds"]
            c.write(OUT / "state.json", current)
        else:
            # A crash after result writing but before receipt is not an accepted run.
            if (folder / "result.json").exists():
                (folder / "result.json").rename(folder / "unsealed-result.json")
            elapsed = max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(item["started_at"])).total_seconds())
            seal(phase, folder, item, {"status": "INTERRUPTED", "remaining": [phase + ": interrupted; rerun after checking evidence"]}, elapsed, current)


def verify(current):
    baseline = preserve()
    for item in current["attempts"]:
        folder = ROOT / item["directory"]
        if c.sha(folder / "receipt.json") != item["receipt_sha256"] or c.read(folder / "receipt.json")["outputs"] != artifacts(folder):
            raise ValueError("Closure receipt or artifact changed")
        if not external_valid(c.read(folder / "receipt.json")):
            raise ValueError("Retained external source or acquisition receipt changed")
    result = refresh(current, save=False)
    return {"status": "PASS" if not result["stale"] else "INCOMPLETE", "baseline": baseline,
            "attempts": len(current["attempts"]), "next": result}


@contextmanager
def locked():
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / ".lock").open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "check", "phase", "run", "verify", "inspect", "render", "rules"))
    parser.add_argument("subject", nargs="?")
    parser.add_argument("pages", nargs="?", help="At most six comma-separated positive page numbers")
    args = parser.parse_args(argv)
    if args.action in {"phase", "inspect", "render"}:
        if args.subject is None or (args.action == "phase" and args.subject not in PHASES):
            parser.error("Declared phase or source subject required")
    elif args.subject is not None:
        parser.error("This action accepts no extra arguments")
    if args.pages and args.action not in {"inspect", "render"}:
        parser.error("Only source inspection accepts pages")
    if args.action == "status":
        return c.emit({"status": "STATUS", "next": refresh(state(), save=False)})
    with locked():
        from . import closure_phases as p
        if args.action in {"inspect", "render", "rules"}:
            return c.emit(p.inspect_source(args.action, args.subject, args.pages))
        preserve()
        if args.action == "check":
            return c.emit(p.check())
        current = state()
        recover(current)
        if args.action == "verify":
            return c.emit(verify(current))
        verify(current)  # Corrupted retained attempts veto execution before any retry.
        for phase in PHASES if args.action == "run" else (args.subject,):
            if any(not current_phase(q, current) for q in DEPENDENCIES[phase]):
                continue
            run_phase(phase, current)
        next_step = refresh(current)
        return c.emit({"status": "GAPS_CLOSED" if next_step["all_gaps_closed"] else "EVIDENCE_OR_REPAIR_REQUIRED", "next": next_step})
