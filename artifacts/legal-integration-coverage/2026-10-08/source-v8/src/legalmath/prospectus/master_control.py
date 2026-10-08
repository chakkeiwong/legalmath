"""Append-only, locked phase supervisor with evidence-driven continuation."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/implementation/prospectus-evidence-master"
DATA = ROOT / "docs/prospectus/evidence-master"
PLAN = ROOT / "docs/plans/prospectus-evidence-master.md"
PREFIX = [".venv/bin/python", "scripts/run_prospectus_evidence_master.py"]
PHASES = ("E0", "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8")
PURPOSE = dict(zip(PHASES, (
    "Preserve baseline and validate execution prerequisites", "Execute metadata and context repair",
    "Validate conditional calculations and missing-input requirements", "Run regression and freeze before new source inspection",
    "Acquire bounded public source evidence", "Analyze sealed unseen-source selections",
    "Execute causal repairs and verify affected evidence", "Integrate source findings and bank investigations",
    "Verify and deliver qualified results")))
SUCCESS = {"PASS", "QUALIFIED"}
ACTIONS = ("authorize", "review", "run", "status", "verify", "phase", "refresh", "freeze", "acquire", "inspect", "register", "check", "repair")


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value, *, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if exclusive:
        with path.open("x") as stream:
            stream.write(content)
    else:
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(content)
        os.replace(temporary, path)


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def campaign_path(value):
    path = (ROOT / value).resolve()
    if not any(path.is_relative_to(base) for base in (DATA, OUT)):
        raise ValueError("Input path must be inside the new campaign")
    return path


def hashes(directory):
    return {str(p.relative_to(directory)): sha(p) for p in sorted(directory.rglob("*"))
            if p.is_file() and p.name != "receipt.json" and "__pycache__" not in p.parts}


def method_files():
    paths = list((ROOT / "src/legalmath").rglob("*.py"))
    paths += list((ROOT / "src/legalmath/prospectus").glob("*.lean"))
    paths += list((ROOT / "tests/prospectus").glob("*.py")) + list((ROOT / "tests/compliance").glob("*.py"))
    paths += [PLAN, OUT / "allowlist.json", OUT / "allow.rules", ROOT / "scripts/run_prospectus_evidence_master.py",
              ROOT / "scripts/run_bond_loss_absorption_classification.py"]
    return {relative(p): sha(p) for p in sorted(paths)}


def state():
    path = OUT / "state.json"
    return read(path) if path.exists() else {"version": "prospectus-evidence-master.v1", "started_at": now(),
        "wall_seconds": 0, "phases": {}, "events": [], "semantic_repairs": []}


@contextmanager
def locked():
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / ".controller.lock").open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another master command is running") from exc
        yield


def command(argv, log, *, timeout=900):
    started = time.monotonic()
    with Path(log).open("wb") as stream:
        result = subprocess.run(argv, cwd=ROOT, env={**os.environ, "CUDA_VISIBLE_DEVICES": "-1", "PYTHONPATH": str(ROOT / "src")},
                                stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    record = {"argv": argv, "exit_code": result.returncode, "wall_seconds": time.monotonic()-started,
              "log": relative(log), "log_sha256": sha(log)}
    if result.returncode:
        raise RuntimeError("Command failed; preserved " + relative(log))
    return record


def policy_checks():
    policy = read(OUT / "allowlist.json")
    if policy["entrypoint"] != PREFIX or policy["actions"] != list(ACTIONS):
        raise ValueError("Policy and fixed entrypoint differ")
    rows = []
    for argv, allowed in [(PREFIX+[a], True) for a in ACTIONS] + [
            (["python3", PREFIX[1], "run"], False), ([PREFIX[0], "-c", "print(1)"], False),
            ([PREFIX[0], "scripts/another.py", "run"], False), (["bash", "-c", " ".join(PREFIX)+" run"], False)]:
        result = subprocess.run(["codex", "execpolicy", "check", "--rules", str(OUT / "allow.rules"), "--", *argv],
                                capture_output=True, text=True, timeout=20)
        if result.returncode:
            raise ValueError("Rule check failed: " + result.stderr)
        parsed = json.loads(result.stdout)
        if (parsed.get("decision") == "allow") != allowed:
            raise ValueError("Unexpected prefix rule decision: " + str(argv))
        rows.append({"argv": argv, "expected_allow": allowed, "result": parsed})
    return rows


def review():
    directory = OUT / "reviews" / f"attempt-{len(list((OUT/'reviews').glob('attempt-*')))+1:03d}"
    directory.mkdir(parents=True)
    rules = policy_checks()
    run = command([str(ROOT / ".venv/bin/python"), "-m", "pytest", "tests/prospectus/test_evidence_master.py", "-q",
                   "--junitxml="+str(directory / "tests.xml")], directory / "tests.log", timeout=180)
    result = {"status": "PASS", "at": now(), "method_hash": digest(method_files()), "rule_checks": rules, "controller_and_arithmetic_tests": run,
              "skeptical_review": relative(OUT / "implementation-review.md"),
              "decision": "Run bounded program; source meaning and actual private facts are not established by these checks."}
    write(directory / "result.json", result, exclusive=True)
    write(OUT / "review.json", result)
    return result


def authorize():
    policy = read(OUT / "allowlist.json")
    checks = policy_checks()
    target = Path.home() / ".codex/rules/legalmath-prospectus-evidence.rules"
    content = (OUT / "allow.rules").read_bytes()
    if target.exists() and target.read_bytes() != content:
        backup = OUT / ("prior-rule-"+sha(target)[:16]+".rules")
        if not backup.exists():
            backup.write_bytes(target.read_bytes())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    result = {"status": "READY", "at": now(), "installed_rule": str(target), "installed_sha256": sha(target),
              "entrypoint": PREFIX, "policy": policy, "rule_checks": checks,
              "note": "Saved rule applies to this literal prefix; platform restrictions remain in force."}
    write(OUT / "approval.json", result)
    return result


def inputs(phase, current):
    paths = [ROOT / "docs/prospectus/gap-closure/final-inventory.json"]
    if PHASES.index(phase) >= 2 and current["phases"].get("E1", {}).get("status") in SUCCESS:
        paths.append(ROOT / current["phases"]["E1"]["directory"] / "inventory.json")
    if phase == "E4":
        paths.append(DATA / "sources.json")
        queue = read(DATA / "sources.json") if (DATA / "sources.json").exists() else {"requests": []}
        urls = {r["url"] for r in queue["requests"]}
        paths += [p for p in sorted((DATA / "requests").glob("*/receipt.json")) if read(p)["url"] in urls]
    if PHASES.index(phase) >= 5:
        paths += [DATA / name for name in ("selection.json", "registered.json")]
        if (DATA / "registered.json").exists():
            registration = read(DATA / "registered.json")
            inv = campaign_path(registration["inventory"])
            paths += [inv, inv.parent / "registration.json"]
            if inv.exists():
                selected = read(inv)
                paths.append(campaign_path(selected["freeze"]))
                for doc in selected["documents"].values():
                    paths += [campaign_path(doc[k]) for k in ("original", "text", "acquisition_receipt")]
    if PHASES.index(phase) >= 6:
        paths.append(DATA / "witness-review.json")
    if PHASES.index(phase) >= 7:
        paths.append(DATA / "source-review.json")
        paths += sorted((DATA / "requests").glob("*/receipt.json"))
    if phase in ("E6", "E7", "E8"):
        paths += sorted((OUT / "repairs").glob("*.json"))
    upstream = {p: current["phases"].get(p, {}).get("receipt_hash") for p in PHASES[:PHASES.index(phase)]}
    return {"method": digest(method_files()), "files": {relative(p): sha(p) if p.exists() else None for p in paths}, "upstream": upstream}


def current_phase(phase, current):
    item = current["phases"].get(phase)
    if not item or item["status"] not in SUCCESS:
        return False
    path = ROOT / item["directory"]
    return item["inputs_hash"] == digest(inputs(phase, current)) and item["outputs"] == hashes(path)


def open_requirements(current):
    issues = []
    for p in PHASES[:-1]:
        item = current["phases"].get(p)
        if not item or not (ROOT/item["directory"]/"result.json").exists():
            continue
        result = read(ROOT/item["directory"]/"result.json")
        if p == "E4" and current_phase("E5", current) and result.get("status") in SUCCESS:
            continue
        if p == "E5" and current_phase("E6", current) and result.get("classification"):
            continue
        issues += result.get("open_issues", [])
    return list(dict.fromkeys(issues))


def refresh(current, phase=None, result=None, directory=None):
    next_phase = next((p for p in PHASES if not current_phase(p, current)), None)
    open_issues = open_requirements(current)
    plan = {"at": now(), "after": phase, "next_phase": next_phase, "purpose": PURPOSE.get(next_phase, "Collect missing external evidence under a new protocol"),
            "phase_status": result.get("status") if result else None,
            "result_hash": digest(result) if result else None,
            "required_result": relative(directory/"result.json") if directory else None,
            "carry_forward": list(dict.fromkeys(open_issues)), "repairs_executed": result.get("repairs", []) if result else [],
            "next_command": " ".join(PREFIX + (["phase", next_phase] if next_phase else ["verify"])),
            "repair_rule": "Repair candidate failures; stop dependent work only for invalid evidence or exhausted applicable budget.",
            "legal_accuracy": "NOT_ESTABLISHED", "actual_trade_permission": False}
    if directory:
        write(directory/"next-phase-plan.json", plan)
        write(directory/"review.json", {"outcome": result["status"], "resolved": result.get("resolved", []),
            "open_issues": result.get("open_issues", []), "repairs_executed": result.get("repairs", []),
            "candidate_vs_direction": "A rejected candidate is not rejection of the research direction.",
            "decision": "Repair before dependent promotion" if result["status"] not in SUCCESS else "Continue with recorded qualifications"})
    write(OUT / "next-phase-plan.json", plan)
    (OUT / "next-phase.md").write_text("# Refreshed next-phase plan\n\n"+plan["purpose"]+"\n\nCommand: `"+plan["next_command"]+"`\n\n"+
        "\n".join("- "+x for x in plan["carry_forward"])+"\n")
    return plan


def run_phase(phase, current):
    if any(not current_phase(p, current) for p in PHASES[:PHASES.index(phase)]):
        raise ValueError("Prerequisite phase missing or stale; run the master from the first stale phase")
    if current_phase(phase, current):
        return current["phases"][phase]
    policy = read(OUT / "allowlist.json")
    if current["wall_seconds"] >= policy["max_execution_seconds"]:
        raise RuntimeError("Execution budget exhausted")
    fingerprint = digest(inputs(phase, current))
    previous_failures = [e for e in current["events"] if e.get("phase")==phase and e.get("inputs_hash")==fingerprint and e.get("event")=="FAILED"]
    if len(previous_failures) >= policy["max_failures_per_input"]:
        raise RuntimeError("Repeated identical failure budget exhausted; review before further work")
    folder = OUT / "phases" / phase
    directory = folder / f"attempt-{len(list(folder.glob('attempt-*')))+1:03d}"
    directory.mkdir(parents=True)
    started = time.monotonic()
    started_at = now()
    before_method = digest(method_files())
    current["phases"][phase] = {"status": "RUNNING", "directory": relative(directory), "inputs_hash": fingerprint}
    write(OUT / "state.json", current)
    print(json.dumps({"phase": phase, "status": "RUNNING", "attempt": directory.name}), flush=True)
    try:
        from .master_phases import execute
        result = execute(phase, directory, current)
        if digest(method_files()) != before_method:
            raise ValueError("Method changed during phase execution; dependent evidence is invalid")
    except Exception as exc:
        result = {"status": "FAILED", "error": type(exc).__name__, "detail": str(exc),
                  "open_issues": [f"Repair {phase}: {exc}"], "research_direction_rejected": False}
    write(directory/"result.json", result, exclusive=True)
    # Mark phase provisionally so the refreshed plan advances after successful work.
    item = {"status": result["status"], "directory": relative(directory), "inputs_hash": digest(inputs(phase, current)),
            "receipt_hash": digest(result), "outputs": hashes(directory)}
    current["phases"][phase] = item
    refresh(current, phase, result, directory)
    item["outputs"] = hashes(directory)
    receipt = {**item, "phase": phase, "started_at": started_at, "finished_at": now(),
               "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "command": PREFIX+["phase",phase], "invocation": sys.argv,
               "environment": sys.executable, "platform": platform.platform(), "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1",
               "seeds": "N/A deterministic", "plan": relative(PLAN), "method_files": method_files(),
               "wall_seconds": time.monotonic()-started}
    item["receipt_hash"] = digest(receipt)
    write(directory/"receipt.json", receipt, exclusive=True)
    current["events"].append({"event": result["status"], "phase": phase, "at": now(), "inputs_hash": fingerprint, "directory": relative(directory)})
    current["wall_seconds"] += receipt["wall_seconds"]
    write(OUT/"state.json", current)
    print(json.dumps({"phase": phase, "status": result["status"], "result": relative(directory/"result.json")}), flush=True)
    return item


def recover_interruption(current):
    for phase,item in current["phases"].items():
        if item["status"] == "RUNNING":
            directory = ROOT/item["directory"]
            result = {"status":"INTERRUPTED", "open_issues":["Interrupted phase preserved; rerun in a new attempt"], "repair":"resume_new_attempt"}
            write(directory/"interruption.json",result)
            item["status"]="INTERRUPTED"
            current["events"].append({"event":"INTERRUPTED","phase":phase,"at":now()})
    write(OUT/"state.json",current)


def freeze(current):
    requests = sorted((DATA/'requests').glob('*/receipt.json'))
    prior = read(ROOT/current["freeze"]) if current.get("freeze") else None
    if prior and prior["files"] == method_files():
        return {"freeze": current["freeze"], "sha256": sha(ROOT/current["freeze"])}
    inspected_pdfs = [p for p in requests if read(p).get("kind") == "pdf" and read(p).get("status") == "RETAINED"]
    if inspected_pdfs and prior and prior["files"] != method_files():
        repairs = current.setdefault("semantic_repairs", [])
        if len(repairs) >= read(OUT/"allowlist.json")["max_semantic_repairs"]:
            raise ValueError("Two post-exposure repair/freeze cycles exhausted")
        repair_records = sorted((OUT/"repairs").glob("*.json"))
        if not repair_records:
            raise ValueError("Post-exposure method change needs a recorded counterexample, causal change and validation plan")
        matches = [p for p in repair_records if read(p).get("old_method_hash") == digest(prior["files"])
                   and read(p).get("new_method_hash") == digest(method_files())]
        if not matches:
            raise ValueError("Repair record must bind this old and new method hash")
        repair = read(matches[-1])
        if not all(repair.get(k) for k in ("counterexample", "causal_change", "validation", "candidate_vs_direction")):
            raise ValueError("Incomplete causal repair record")
        repairs.append({"at":now(),"record":relative(matches[-1]),"old_freeze":current["freeze"],"new_method":digest(method_files())})
    directory = OUT / "freezes" / f"candidate-{len(list((OUT/'freezes').glob('candidate-*')))+1:03d}"
    directory.mkdir(parents=True)
    data = {"at":now(), "files":method_files(), "plan":relative(PLAN), "source_requests_before_freeze":[relative(p) for p in sorted((DATA/'requests').glob('*/receipt.json'))],
            "retained_pdfs_before_freeze": [relative(p) for p in inspected_pdfs],
            "discovery_requests_before_freeze": [relative(p) for p in requests if p not in inspected_pdfs],
            "previous_cases":"All 32 previous issues are exposed. Fresh means uninspected issue PDFs, not wholly unseen issuer families; prior discovery pages are recorded."}
    write(directory/"freeze.json",data,exclusive=True)
    with zipfile.ZipFile(directory/"method.zip","w",zipfile.ZIP_DEFLATED) as archive:
        for path in data["files"]:archive.write(ROOT/path,path)
    current["freeze"]=relative(directory/"freeze.json")
    write(OUT/"state.json",current)
    return {"freeze":current["freeze"],"sha256":sha(directory/"freeze.json")}


def verify():
    current = state()
    verified = 0
    for p in sorted((OUT/"phases").glob("*/attempt-*/receipt.json")):
        r=read(p)
        if r["outputs"] != hashes(p.parent):raise ValueError("Historical phase artifact changed: "+str(p))
        verified+=len(r["outputs"])
    from .master_sources import verify_sources
    source_checks = verify_sources()
    for item in current["phases"].values():
        receipt = ROOT/item["directory"]/"receipt.json"
        if receipt.exists() and item.get("receipt_hash") != digest(read(receipt)):
            raise ValueError("Latest phase receipt changed")
    for frozen in sorted((OUT/"freezes").glob("candidate-*/freeze.json")):
        data = read(frozen)
        with zipfile.ZipFile(frozen.parent/"method.zip") as archive:
            for name, expected in data["files"].items():
                if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                    raise ValueError("Frozen method archive changed")
    stale=[p for p in PHASES if not current_phase(p,current)]
    result={"status":"PASS" if not stale else "INCOMPLETE","at":now(),"verified_artifacts":verified,"source_checks":source_checks,"stale_or_unfinished":stale,
            "legal_accuracy":"NOT_ESTABLISHED","actual_trade_permission":False}
    write(OUT/"verification.json",result)
    return result


def emit(result):
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    status = result.get("status") if isinstance(result, dict) else None
    return 2 if status in {"FAILED", "ACTION_REQUIRED", "INCOMPLETE", "WAITING_REVIEW", "WAITING_SELECTION", "REPAIR_REQUIRED"} else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=ACTIONS)
    parser.add_argument("arguments",nargs="*")
    args=parser.parse_args()
    if Path.cwd()!=ROOT:os.chdir(ROOT)
    # Atomic state reads must not acquire the execution lock or mark its live
    # RUNNING attempt interrupted. Extraction/search still use the write lock.
    if args.action == "status":
        current = state()
        return emit({"phases": {p: ("CURRENT" if current_phase(p,current) else current["phases"].get(p,{}).get("status","PENDING")) for p in PHASES},
                     "directories": {p: v["directory"] for p,v in current["phases"].items()},
                     "freeze": current.get("freeze"), "wall_seconds": current["wall_seconds"],
                     "next": read(OUT/"next-phase-plan.json") if (OUT/"next-phase-plan.json").exists() else None})
    if args.action == "inspect" and args.arguments and args.arguments[0] in {"requests", "file", "file-search", "code", "links", "baseline", "image"}:
        from .master_phases import auxiliary
        return emit(auxiliary("inspect", args.arguments, state()))
    with locked():
        current=state();recover_interruption(current)
        if args.action=="authorize":result=authorize()
        elif args.action=="review":result=review()
        elif args.action=="status":result={"phases":{p:("CURRENT" if current_phase(p,current) else current["phases"].get(p,{}).get("status","PENDING")) for p in PHASES},"next":refresh(current),"wall_seconds":current["wall_seconds"]}
        elif args.action=="verify":result=verify()
        elif args.action=="refresh":result=refresh(current)
        elif args.action=="freeze":
            if not current_phase("E3",current):raise ValueError("Run current development validation before an auxiliary freeze")
            result=freeze(current)
        elif args.action in {"acquire","inspect","register","check","repair"}:
            from .master_phases import auxiliary
            result=auxiliary(args.action,args.arguments,current)
            refresh(state())
        else:
            approved=read(OUT/"approval.json")
            if approved["entrypoint"]!=PREFIX:raise ValueError("Entry point approval mismatch")
            if read(OUT/"review.json")["method_hash"]!=digest(method_files()):raise ValueError("Method changed; review again before execution")
            phases=PHASES if args.action=="run" else tuple(args.arguments)
            if args.action=="phase" and (len(phases)!=1 or phases[0] not in PHASES):raise ValueError("Expected one declared phase")
            for phase in phases:
                result=run_phase(phase,current)
                if result["status"] not in SUCCESS:break
            refresh(current)
            result={"status": "COMPLETE_WITH_QUALIFICATIONS" if all(current_phase(p,current) for p in PHASES) else "ACTION_REQUIRED",
                    "last":{k:result.get(k) for k in ("status","directory")},"next":read(OUT/"next-phase-plan.json")}
    return emit(result)
