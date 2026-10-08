"""Bounded phase execution with repair receipts and refreshed plans."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from . import PROTOCOL
from .common import ARCHIVE, JDK, LEAN, PLAN, PROGRAM, PYTHON, ROOT, RUNS, TOOLCHAIN
from .common import digest, now, read, relative, sha, write
from . import archive

PHASES = ("P0", "P1", "P2", "P3", "P4", "P5", "P6")


class RepairableError(RuntimeError):
    """Only the fixed derivative-rebuild repair is eligible for automatic retry."""

PURPOSES = {
    "P0": "Preserve every supplied source and selected SFC premises",
    "P1": "Execute source-package completion repairs and retain unresolved dependencies",
    "P2": "Extract source-linked candidates and construct conditional instrument and legal models",
    "P3": "Check scoped universal proofs and independent exact semantics",
    "P4": "Execute identical formal programs through RuleIR and direct Catala",
    "P5": "Run semantic, evidence, amendment and controller challenges",
    "P6": "Verify evidence, freeze future protocol and report qualifications",
}


def command_prefix():
    return [str(PYTHON), str(ROOT / "scripts/prospectus_master.py")]


def policy_checks():
    policy = read(PROGRAM / "allowlist.json")
    if policy["entrypoint"] != command_prefix():
        raise ValueError("Entry point differs from allow list")
    receipts = []
    for action in policy["actions"]:
        argv = command_prefix() + [action] + (["P0"] if action == "phase" else [])
        check = subprocess.run(["codex", "execpolicy", "check", "--rules", str(PROGRAM / "allow.rules"), "--", *argv],
                               capture_output=True, text=True, timeout=15)
        if check.returncode:
            raise ValueError(check.stderr)
        result = json.loads(check.stdout)
        if result.get("decision") != "allow":
            raise ValueError("Command is not allowed: " + str(argv))
        receipts.append({"argv": argv, "result": result})
    return receipts


def preflight():
    checks = {}
    for name, argv in {
        "python": [str(PYTHON), "--version"], "lean": [str(LEAN), "--version"],
        "java": [str(JDK / "bin/java"), "-version"],
        "catala": [str(TOOLCHAIN["compiler"]), "--version"], "curl": ["curl", "--version"],
        "pdftotext": ["/usr/bin/pdftotext", "-v"],
    }.items():
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=20)
        checks[name] = {"argv": argv, "returncode": proc.returncode,
                        "version": (proc.stdout + proc.stderr).splitlines()[:2]}
        if proc.returncode:
            raise ValueError("Unavailable required tool: " + name)
    import pypdf, pytest, z3
    checks["libraries"] = {"pypdf": pypdf.__version__, "pytest": pytest.__version__, "z3": z3.get_version_string()}
    checks["policy"] = policy_checks()
    checks["sources"] = len(archive.catalog())
    checks["cpu_only"] = True
    write(PROGRAM / "preflight.json", checks)
    return checks


def authorize():
    result = preflight()
    target = Path("/home/chakwong/.codex/rules/legalmath-prospectus.rules")
    content = (PROGRAM / "allow.rules").read_bytes()
    if target.exists() and target.read_bytes() != content:
        backup = PROGRAM / ("previous-platform-rules-" + sha(target.read_bytes())[:12] + ".rules")
        backup.write_bytes(target.read_bytes())
    target.write_bytes(content)
    result["installed_rule"] = str(target)
    result["current_session_note"] = "Use the identical escalated prefix; saved rules load on session startup. Platform restrictions remain in force."
    write(PROGRAM / "approval-setup.json", result)
    return {"status": "READY", "installed_rule": str(target), "entrypoint": command_prefix()}


def state():
    path = RUNS / "state.json"
    return read(path) if path.exists() else {"protocol": PROTOCOL, "started_at": now(), "wall_seconds": 0,
                                             "phases": {}, "events": []}


def material_inputs(phase):
    files = [PLAN, PROGRAM / "allowlist.json", PROGRAM / "allow.rules", ROOT / "scripts/prospectus_master.py"]
    files += sorted(Path(__file__).parent.glob("*.py")) + sorted(Path(__file__).parent.glob("*.lean"))
    rows = archive.catalog()
    if phase == "P0":
        rows = [r for r in rows if r["group"] != "repair"]
        files = [p for p in files if p.name in ("archive.py", "common.py", "campaign.py", "prospectus_master.py", "allowlist.json", "allow.rules", PLAN.name)]
    else:
        from .legal_review import dossier_files
        files += dossier_files(ROOT)
    files += [ARCHIVE / "originals" / (r["id"] + "." + r["kind"]) for r in rows]
    if phase not in ("P0", "P1"):
        files += [ARCHIVE / "text" / (r["id"] + ".json") for r in rows]
        files += sorted((ROOT / "tests/prospectus").glob("*.py"))
        files += [ROOT / "pyproject.toml", PROGRAM / "preflight.json"]
        files += sorted((PROGRAM / "specification").glob("*.json")) if (PROGRAM / "specification").exists() else []
        from ..qualification.assurance import method_manifest
        downstream = method_manifest()
    else:
        downstream = None
    previous = state()["phases"]
    upstream = {p: {k: previous.get(p, {}).get(k) for k in ("inputs_hash", "outputs", "status")}
                for p in PHASES[:PHASES.index(phase)]}
    return {"sources": rows, "files": {relative(p): sha(p.read_bytes()) if p.exists() else None for p in files},
            "backend_methods": downstream, "upstream": upstream}


def output_files(directory):
    return {str(p.relative_to(directory)): sha(p.read_bytes()) for p in sorted(Path(directory).rglob("*"))
            if p.is_file() and p.name != "receipt.json" and "__pycache__" not in p.parts}


def completed(current, phase):
    item = current["phases"].get(phase)
    if not item or item["status"] != "COMPLETE":
        return False
    directory = ROOT / item["directory"]
    return (item["inputs_hash"] == digest(material_inputs(phase))
            and item["outputs"] == output_files(directory))


def refresh(current, phase, result, directory):
    index = PHASES.index(phase)
    following = phase if result.get("status") == "FAILED" else PHASES[index + 1] if index + 1 < len(PHASES) else None
    review = {"phase": phase, "purpose": PURPOSES[phase], "outcome": result.get("status", "CHECKED"),
              "resolved": result.get("resolved", []), "open_issues": result.get("open_issues", []),
              "repair_executed": result.get("repairs", []),
              "candidate_vs_direction": "Qualified premises or candidate failure do not reject the research direction.",
              "legal_correctness": "NOT_ESTABLISHED", "human_quality_evidence": False}
    plan = {"after": phase, "next_phase": following, "purpose": PURPOSES.get(following, "Preserve qualified results and collect future observations"),
            "required_result": relative(Path(directory) / "result.json"),
            "result_hash": digest(result), "carry_forward": review["open_issues"],
            "actions": {
                "P0": ["Preserve original bytes or retain the exact failed URL and reason"],
                "P1": ["Acquire listed final terms and issuer mirrors", "Keep base/issue dates and missing references explicit"],
                "P2": ["Check current source bytes and page quotations", "Construct conditional feature alternatives and source-bound specifications"],
                "P3": ["Run Lean kernel and independent SMT equivalence on the actual shared models", "Find counterexamples to deliberate wrong encodings"],
                "P4": ["Use identical formal cases in native RuleIR and Catala", "Include real-document candidate completions with their qualifications"],
                "P5": ["Challenge absent/conflicting premises, exact boundaries and source amendments", "Inject derivative failure, execute repair, verify downstream invalidation"],
                "P6": ["Replay archive and backend verification", "Freeze methods and write result-driven prospective plan"],
                None: ["Freeze before new sources; repairs remain development; no existing document is a future observation"],
            }[following],
            "stop_if": ["Corrupted original", "Invalid checker", "Unrepaired semantic mismatch", "Budget exhausted"]}
    write(Path(directory) / "review.json", review)
    write(Path(directory) / "next-phase-plan.json", plan)
    write(PROGRAM / "next-phase-plan.json", plan)
    return review


def work(phase, directory, current):
    if phase == "P0":
        rows = archive.acquire([r for r in archive.catalog() if r["group"] != "repair"], directory)
        missing = [r["id"] for r in rows if r["status"] != "PRESERVED"]
        return {"status": "QUALIFIED" if missing else "CHECKED", "acquisition": rows,
                "open_issues": ["Acquire missing source " + key for key in missing],
                "resolved": ["Preserved " + r["id"] for r in rows if r["status"] == "PRESERVED"]}
    from .phases import execute
    return execute(phase, directory, current)


def run_phase(phase, current):
    index = PHASES.index(phase)
    if any(not completed(current, earlier) for earlier in PHASES[:index]):
        raise ValueError("Run or refresh prerequisite phases first")
    if completed(current, phase):
        return current["phases"][phase]
    policy = read(PROGRAM / "allowlist.json")
    attempts = sum(e.get("phase") == phase and e["event"] == "attempt" for e in current["events"])
    failures = sum(e.get("phase") == phase and e["event"] == "failure" and e.get("method_hash") == digest(material_inputs(phase)) for e in current["events"])
    if failures >= policy["max_attempts_per_phase"] or current["wall_seconds"] >= policy["max_campaign_seconds"]:
        raise ValueError("Campaign attempt/time budget exhausted")
    directory = RUNS / phase / f"attempt-{attempts + 1:03d}"
    directory.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    before = digest(material_inputs(phase))
    current["events"].append({"event": "attempt", "phase": phase, "at": now(), "method_hash": before})
    write(RUNS / "state.json", current)
    print(json.dumps({"phase": phase, "attempt": attempts + 1, "status": "RUNNING"}), flush=True)
    try:
        result = work(phase, directory, current)
        if phase not in ("P0", "P1") and before != digest(material_inputs(phase)):
            raise ValueError("Material inputs changed while phase was executing")
        write(directory / "result.json", result)
        refresh(current, phase, result, directory)
        item = {"status": "COMPLETE", "directory": relative(directory), "inputs_hash": digest(material_inputs(phase)),
                "outputs": output_files(directory), "completed_at": now()}
        current["phases"][phase] = item
        write(directory / "receipt.json", item)
        current["events"].append({"event": "complete", "phase": phase, "at": now(), "result_hash": digest(result)})
    except Exception as exc:
        failure = {"error": type(exc).__name__, "detail": str(exc), "phase": phase,
                   "classification": "IMPLEMENTATION_OR_ENVIRONMENT", "research_direction_rejected": False}
        write(directory / "failure.json", failure)
        current["phases"][phase] = {"status": "FAILED", "directory": relative(directory)}
        current["events"].append({"event": "failure", "phase": phase, "at": now(), "method_hash": before, **failure})
        refresh(current, phase, {"status": "FAILED", "open_issues": [str(exc)]}, directory)
        raise
    finally:
        current["wall_seconds"] += time.monotonic() - started
        write(RUNS / "state.json", current)
    print(json.dumps({"phase": phase, "status": "COMPLETE", "result_status": result.get("status")}), flush=True)
    return item


def run_with_repairs(phase, current):
    for _ in range(read(PROGRAM / "allowlist.json")["max_attempts_per_phase"]):
        try:
            return run_phase(phase, current)
        except RepairableError:
            repairs = archive.derivative_repairs(execute=True)
            if not repairs:
                raise ValueError("Declared derivative repair has no applicable action")
            current["events"].append({"event": "repair", "phase": phase, "at": now(), "repairs": repairs})
            write(RUNS / "state.json", current)
    raise ValueError("Bounded derivative recovery exhausted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("authorize", "preflight", "run", "phase", "status", "verify", "future"))
    parser.add_argument("phase", nargs="?", choices=PHASES)
    args = parser.parse_args()
    if (args.action == "phase") != (args.phase is not None):
        parser.error("Only phase requires a phase identifier")
    os.chdir(ROOT)
    if args.action == "authorize":
        result = authorize()
    elif args.action == "preflight":
        result = preflight()
    elif args.action == "status":
        current = state()
        result = {"phases": {p: ("CURRENT" if completed(current, p) else "STALE" if current["phases"].get(p, {}).get("status") == "COMPLETE" else current["phases"].get(p, {}).get("status", "PENDING")) for p in PHASES},
                  "wall_seconds": current["wall_seconds"]}
    elif args.action == "verify":
        from .phases import verify_campaign
        result = verify_campaign(state())
    elif args.action == "future":
        from .future import intake
        result = intake(state())
    else:
        current = state()
        for phase in ([args.phase] if args.action == "phase" else PHASES):
            run_with_repairs(phase, current)
        result = {"status": "COMPLETE", "phases": list(current["phases"])}
    print(json.dumps(result, indent=2), flush=True)
    return 0
