"""Fixed, resumable operations for the finite legal tool comparison."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/legal-tool-comparison/2026-10-06"
RES = ROOT / ".localresources/legal-tool-comparison"
DOC = ROOT / "docs/implementation/legal-tool-comparison"
PLAN = ROOT / "docs/plans/legal-tool-comparison-master-program.md"
PREFIX = [".venv/bin/python", "scripts/run_legal_tool_program.py"]
ACTIONS = ("setup", "execute", "status", "verify", "check")
PHASES = ("T0", "T1", "T2", "T3", "T4")
LIMITS = {"provider_calls": 48, "network_processes": 12, "repair_attempts": 4,
          "execution_seconds": 14400, "download_bytes": 512 * 1024 * 1024}
RULE = Path.home() / ".codex/rules/legalmath-tool-comparison.rules"

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def safe(path, base=ROOT):
    path = Path(path)
    if not path.is_absolute():
        path = base / path
    if not path.resolve().is_relative_to(base.resolve()):
        raise ValueError("Path escapes permitted root")
    if any(p.is_symlink() for p in (path, *path.parents) if p != base.parent):
        raise ValueError("Symlink in program output path")
    return path

def read(path):
    return json.loads(Path(path).read_text())

def save(path, value):
    path = safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)

def ref(path):
    path = Path(path)
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}

def check_ref(value):
    path = safe(value["path"])
    if sha(path) != value["sha256"]:
        raise ValueError("Changed retained file: " + str(path))
    return path

def rules_text():
    return "# Fixed legal tool comparison; no arbitrary command arguments.\n" + "".join(
        "prefix_rule(pattern=" + json.dumps(PREFIX + [a]) + ', decision="allow")\n'
        for a in ACTIONS)

def policy_check(path):
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("Codex execpolicy checker missing")
    positive = [PREFIX + [a] for a in ACTIONS]
    negative = [["python3", *PREFIX[1:], "execute"], PREFIX + ["shell"],
                [".venv/bin/python", "-c", "print(1)"]]
    rows = []
    for cmd, expected in [(c, True) for c in positive] + [(c, False) for c in negative]:
        r = subprocess.run([codex, "execpolicy", "check", "--rules", str(path),
                            *cmd], capture_output=True, text=True, timeout=20, check=True)
        value = json.loads(r.stdout)
        if (value.get("decision") == "allow") != expected:
            raise ValueError("Dedicated execpolicy mismatch")
        rows.append({"argv": cmd, "decision": value.get("decision"), "expected_allow": expected})
    return rows

def command(argv, directory, name, *, timeout=180, env=None, cwd=ROOT):
    directory = safe(directory)
    directory.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    environment = {**os.environ, "CUDA_VISIBLE_DEVICES": "-1", "PYTHONNOUSERSITE": "1"}
    if env:
        environment.update(env)
    with (directory / (name + ".log")).open("w") as log:
        proc = subprocess.Popen(list(map(str, argv)), cwd=cwd, env=environment,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            proc.wait(timeout=timeout)
        except BaseException:
            import signal
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise
    value = {"argv": list(map(str, argv)), "returncode": proc.returncode,
             "wall_seconds": round(time.monotonic()-start, 3),
             "log": ref(directory / (name + ".log")), "cpu_only": True}
    save(directory / (name + ".json"), value)
    if proc.returncode:
        raise RuntimeError(name + " failed; see " + str(directory / (name + ".log")))
    return value

def reserve_network(label):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "network.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = OUT / "network.json"
        value = read(path) if path.exists() else {"maximum": LIMITS["network_processes"], "actions": []}
        if len(value["actions"]) >= value["maximum"]:
            raise RuntimeError("Network-process budget exhausted")
        value["actions"].append({"label": label, "reserved_at": time.time()})
        save(path, value)
        return len(value["actions"])

def used_provider():
    p = OUT / "provider-allowance.json"
    return len(read(p)["calls"]) if p.exists() else 0

def used_repairs(state):
    path=OUT/"repairs.json"
    explicit=len(read(path)["repairs"]) if path.exists() else 0
    return explicit+len(state["failures"])

def baseline(work):
    paths = [
      "artifacts/legal-interpretation-program/successor-s4/attempt-1/result.json",
      "artifacts/legal-interpretation-program/problem-led-follow-up/result.json",
      "docs/implementation/legal-interpretation-program/follow-up/final-decision.md",
      "artifacts/legal-interpretation-program/problem-led-follow-up/obligation-traces.json",
      "artifacts/legal-interpretation-program/problem-led-follow-up/premise-register.json",
      "artifacts/legal-interpretation-program/problem-led-follow-up/question-provenance.json",
      "artifacts/legal-interpretation-program/2026-10-06-offline-v1/P0/attempt-2/packet.json",
      "docs/research/legal-interpretation-reuse-2026-10-05.md",
    ]
    result = read(ROOT / paths[1])
    for name in ("plan", "decision", "validation", "diagnostic"):
        check_ref(result[name])
    if result["open_qualified_obligations"] != 46:
        raise ValueError("Unexpected baseline obligations")
    trace = read(ROOT / paths[3])
    if len(trace) != 46:
        raise ValueError("Lost obligations")
    from scripts.legal_tool_inputs import build_corpus, QUESTIONS
    corpus = build_corpus()
    save(work / "corpus.json", corpus)
    save(work / "questions.json", QUESTIONS)
    return {"status": "FROZEN", "inputs": [ref(ROOT/p) for p in paths],
            "corpus": ref(work/"corpus.json"), "questions": ref(work/"questions.json"),
            "obligations": 46, "unformalized_readings": 32,
            "question_provenance": "Named development questions; original wording retained in bound register",
            "legal_correctness": "NOT_ESTABLISHED"}

def setup():
    DOC.mkdir(parents=True, exist_ok=True)
    proposed = DOC / "allow.rules"
    if proposed.read_text() != rules_text():
        raise ValueError("Reviewed worktree policy changed")
    checks = policy_check(proposed)
    if RULE.is_symlink() or any(p.is_symlink() for p in RULE.parents):
        raise ValueError("Protected policy path is a symlink")
    if not RULE.parent.is_dir():
        raise ValueError("Expected existing user rules directory")
    if RULE.exists() and RULE.read_text() != rules_text():
        raise ValueError("Existing different rule preserved")
    if not RULE.exists():
        with RULE.open("x") as stream:
            stream.write(rules_text())
    save(DOC/"policy-check.json", {"status": "PASS", "checks": checks,
        "installed_path": str(RULE), "installed_sha256": sha(RULE),
        "limits": "Dedicated policy only; managed session restrictions and inherited rules remain separate"})
    print(json.dumps({"status": "READY", "rules": str(RULE), "limits": LIMITS}), flush=True)

def accounting(state):
    if state["limits"] != LIMITS:
        raise ValueError("Program budget changed")
    check_ref(state["plan"])
    for failure in state["failures"]:check_ref(failure)
    counts = {"provider_calls": used_provider(), "repairs_used": used_repairs(state)}
    for filename, field, limit in (("provider-allowance.json", "calls", "provider_calls"),
                                   ("network.json", "actions", "network_processes"),
                                   ("repairs.json", "repairs", "repair_attempts")):
        path = OUT / filename
        if path.exists():
            ledger = read(path)
            if ledger["maximum"] != LIMITS[limit] or len(ledger[field]) > LIMITS[limit]:
                raise ValueError("Invalid budget ledger: " + filename)
            if field == "actions":counts["network_processes"] = len(ledger[field])
    if counts["repairs_used"] > LIMITS["repair_attempts"]:
        raise ValueError("Repair cap exceeded")
    from scripts.legal_tool_window import deadline
    deadline(state)  # Validate the grant; historical verification may occur after expiry.
    return counts

def verify():
    state = read(OUT / "state.json")
    counts = accounting(state)
    for phase, value in state["completed"].items():
        p = check_ref(value)
        r = read(p)
        for item in r["outputs"]:
            check_ref(item)
        for item in r["method"]:
            check_ref(item)
        if phase == "T3" and "external_evidence" in r["result"]:
            for item in read(check_ref(r["result"]["external_evidence"])):check_ref(item)
            if r["result"]["provider_calls"] != counts["provider_calls"]:
                raise ValueError("Provider spending changed after terminal live receipt")
        if phase == "T4":
            for item in r["result"]["audit_references"]:check_ref(item)
        if phase == "T0":
            for item in r["result"]["inputs"]:
                check_ref(item)
    if used_provider() > LIMITS["provider_calls"]:
        raise ValueError("Provider cap exceeded")
    return {"status": "VERIFIED", "completed": list(state["completed"]),
            **counts, "state": state["status"]}

def execute():
    if not RULE.is_file() or RULE.read_text() != rules_text():
        raise RuntimeError("Run reviewed setup first")
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/"master.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        statepath = OUT/"state.json"
        state = read(statepath) if statepath.exists() else {
            "status": "RUNNING", "started": time.time(), "limits": LIMITS,
            "completed": {}, "failures": [], "plan": ref(PLAN)}
        check_ref(state["plan"])
        if state["limits"] != LIMITS:
            raise ValueError("Program budget changed")
        if state["completed"]:
            verify()
        for phase in PHASES:
            if phase in state["completed"]:
                continue
            from scripts.legal_tool_window import remaining
            if remaining(state) <= 0:
                raise RuntimeError("Execution window exhausted")
            failures = used_repairs(state)
            if failures > LIMITS["repair_attempts"]:
                raise RuntimeError("Repair budget exhausted")
            attempts = OUT / phase
            attempt = attempts / ("attempt-" + str(len(list(attempts.glob("attempt-*"))) + 1))
            attempt.mkdir(parents=True, exist_ok=False)
            state["status"] = "RUNNING"
            state["active_phase"] = phase
            save(statepath, state)
            previous = next(reversed(state["completed"].values()), None) if state["completed"] else None
            save(attempt/"refreshed-plan.json", {
                "phase": phase, "predecessor": previous, "governing_plan": state["plan"],
                "remaining_provider_calls": LIMITS["provider_calls"] - used_provider(),
                "remaining_repairs": LIMITS["repair_attempts"] - failures,
                "remaining_seconds": remaining(state),
                "action": {"T0":"freeze original questions and evidence",
                    "T1":"pinned external acquisition and isolated runtime",
                    "T2":"actual tool component checks and attribution",
                    "T3":"paired live and actual product investigation",
                    "T4":"evidence audit and terminal adoption decisions"}[phase],
                "continuation_veto": "corrupt inputs, broken budget, unauthorized action, unresolved harness defect",
                "promotion_veto": "lost source/question/unknown state or unsupported legal inference",
                "previous_failures": state["failures"]})
            print("START " + phase + " " + str(attempt.relative_to(ROOT)), flush=True)
            start = time.monotonic()
            try:
                if phase == "T0":
                    result = baseline(attempt)
                elif phase == "T1":
                    from scripts.legal_tool_acquire import run
                    result = run(attempt)
                elif phase == "T2":
                    from scripts.legal_tool_components import run
                    result = run(attempt)
                elif phase == "T3":
                    from scripts.legal_tool_live import run
                    result = run(attempt)
                else:
                    from scripts.legal_tool_decide import run
                    result = run(attempt)
                methoddir = attempt/"method"
                methoddir.mkdir()
                method = []
                for p in sorted((ROOT/"scripts").glob("legal_tool_*.py")) + [ROOT/"scripts/run_legal_tool_program.py"]:
                    target = methoddir/p.name
                    shutil.copyfile(p,target)
                    method.append(ref(target))
                receipt = {"phase": phase, "status": "EXECUTED", "result": result,
                    "wall_seconds": round(time.monotonic()-start,3),
                    "git_commit": subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
                    "dirty_worktree": True, "command": PREFIX+["execute"],
                    "environment": {"python":sys.version,"executable":sys.executable,"cpu_only":True},
                    "seeds": "N/A for deterministic tools; provider sampling seed unavailable",
                    "plan": state["plan"], "method": method,
                    "outputs": [ref(p) for p in sorted(attempt.rglob("*"))
                                if p.is_file() and not p.is_relative_to(methoddir)]}
                save(attempt/"result.json",receipt)
                state["completed"][phase] = ref(attempt/"result.json")
                state["status"] = "COMPLETE_WITH_DECISIONS" if phase == "T4" else "RUNNING"
                save(statepath,state)
                print("DONE " + phase + " " + result.get("status","RECORDED"),flush=True)
                if phase != "T4":
                    print("PHASE_REVIEW_REQUIRED before the next exact execute invocation",flush=True)
                    return
            except BaseException as exc:
                failure={"phase":phase,"error":type(exc).__name__,"message":str(exc),
                         "attempt":str(attempt.relative_to(ROOT)),"traceback":traceback.format_exc()}
                save(attempt/"failure.json",failure)
                state["failures"].append(ref(attempt/"failure.json"))
                state["status"]="REPAIR_REQUIRED"
                save(statepath,state)
                print("STOP "+phase+" "+type(exc).__name__+": "+str(exc),flush=True)
                raise
        print(json.dumps(verify()),flush=True)

def main(argv=None):
    os.environ["CUDA_VISIBLE_DEVICES"]="-1"
    if Path.cwd().resolve() != ROOT:
        raise ValueError("Use exact command from repository root")
    p=argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument("action",choices=ACTIONS)
    args=p.parse_args(argv)
    if args.action=="setup":
        setup()
    elif args.action=="execute":
        execute()
    elif args.action=="verify":
        print(json.dumps(verify(),indent=2))
    elif args.action=="status":
        value=read(OUT/"state.json") if (OUT/"state.json").exists() else {"status":"PREPARED"}
        if "started" in value:
            from scripts.legal_tool_window import remaining
            try: seconds=remaining(value); window_status="ACTIVE" if seconds>0 else "EXPIRED"
            except ValueError: seconds=0; window_status="INVALID_UNCONFIRMED_RENEWAL"
            value={**value,"remaining_seconds":seconds,"execution_window":window_status,
                   "provider_calls":used_provider(),"repairs_used":used_repairs(value)}
        print(json.dumps(value,indent=2))
    else:
        import ast
        for script in (ROOT/"scripts").glob("legal_tool_*.py"):ast.parse(script.read_text())
        r=command([sys.executable,"-m","pytest","-q","tests/tooling/test_legal_tool_program.py"],
                  OUT/"checks","tests",timeout=120)
        print(json.dumps(r,indent=2))
