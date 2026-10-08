"""Durable, bounded controller; closed CLI and immutable phase receipts."""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/legal-tool-gap-validation/2026-10-08"
DOC = ROOT / "docs/implementation/legal-tool-gap-validation"
PLAN = ROOT / "docs/plans/legal-tool-gap-validation-program.md"
OLD = ROOT / "artifacts/legal-tool-comparison/2026-10-06"
RES = ROOT / ".localresources/legal-tool-comparison"
PREFIX = [".venv/bin/python", "scripts/run_legal_gap_program.py"]
ACTIONS = ("check", "setup", "execute", "status", "verify")
PHASES = ("G0", "G1", "G2", "G3", "G4")
LIMITS = {"provider_calls": 96, "repair_attempts": 12, "seconds": 86400}
RULE = Path.home() / ".codex/rules/legalmath-gap-validation.rules"


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.resolve().is_relative_to(ROOT.resolve()) or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Unsafe program path")
    return path


def save(path, value):
    path = safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def ref(path):
    return {"path": str(Path(path).relative_to(ROOT)), "sha256": sha(path)}


def check_ref(row):
    path = safe(row["path"])
    if sha(path) != row["sha256"]:
        raise ValueError("Changed program input: " + row["path"])
    return path


def ledger():
    path = OUT / "provider-allowance.json"
    return read(path) if path.exists() else {"maximum": LIMITS["provider_calls"], "calls": []}


def remaining():
    return max(0, read(OUT / "state.json")["started"] + LIMITS["seconds"] - time.time())


class Allowance:
    def __init__(self, arm, maximum):
        self.arm, self.arm_maximum = arm, maximum
        self.path = OUT / "provider-allowance.json"
        self.maximum = self.reservation_ceiling = LIMITS["provider_calls"]
        self.grant_path = DOC / "authorization.json"

    def reserve(self, request_hash):
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT / "provider.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            value = ledger()
            if value["maximum"] != self.maximum:
                raise ValueError("Changed allowance")
            if remaining() < 5 or len(value["calls"]) >= self.maximum:
                raise RuntimeError("Program time/call budget exhausted")
            if sum(r["arm"] == self.arm for r in value["calls"]) >= self.arm_maximum:
                raise RuntimeError("Arm allowance exhausted: " + self.arm)
            value["calls"].append({"arm": self.arm, "request_hash": request_hash,
                                   "issued_at_ns": str(time.time_ns())})
            save(self.path, value)
            return len(value["calls"])


def repair(reason, evidence):
    path = OUT / "repairs.json"
    value = read(path) if path.exists() else {"maximum": LIMITS["repair_attempts"], "repairs": []}
    if value["maximum"] != LIMITS["repair_attempts"]:
        raise ValueError("Changed repair allowance")
    if len(value["repairs"]) >= value["maximum"]:
        raise RuntimeError("Repair cap exhausted")
    value["repairs"].append({"reason": reason, "evidence": evidence, "recorded": time.time()})
    save(path, value)


def command(argv, folder, label, timeout=90, env=None, cwd=ROOT):
    folder = safe(folder)
    folder.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    environment = {**os.environ, "CUDA_VISIBLE_DEVICES": "-1", "PYTHONNOUSERSITE": "1"}
    environment.update(env or {})
    failed = None
    with (folder / (label + ".log")).open("w") as log:
        proc = subprocess.Popen([str(x) for x in argv], stdout=log, stderr=subprocess.STDOUT,
                                cwd=cwd, env=environment, start_new_session=True)
        try:
            proc.wait(timeout=timeout)
        except BaseException as exc:
            import signal
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            failed = exc
    result = {"argv": [str(x) for x in argv], "returncode": proc.returncode,
              "wall_seconds": time.monotonic() - start, "cpu_only": True,
              "log": ref(folder / (label + ".log"))}
    if failed is not None:
        result["interruption"] = {"type": type(failed).__name__, "error": str(failed)}
    save(folder / (label + ".command.json"), result)
    if failed is not None:
        raise failed
    if proc.returncode:
        raise RuntimeError("Command failed: " + label)
    return result


def worker(action, data, folder):
    folder.mkdir(parents=True, exist_ok=True)
    save(folder / "input.json", data)
    command([RES / "venv/bin/python", ROOT / "scripts/legal_gap_worker.py", action,
             folder / "input.json", folder / "output.json"], folder, "worker")
    return read(folder / "output.json")


def rules_text():
    return "# Fixed legal gap validation actions.\n" + "".join(
        "prefix_rule(pattern=" + json.dumps(PREFIX + [a]) + ', decision="allow")\n' for a in ACTIONS)


def policy_check(path):
    rows = []
    for cmd, expected in [(PREFIX + [a], True) for a in ACTIONS] + [
        (PREFIX + ["shell"], False), (["python3", *PREFIX[1:], "execute"], False)]:
        result = subprocess.run(["codex", "execpolicy", "check", "--rules", str(path), *cmd],
                                capture_output=True, text=True, timeout=20, check=True)
        row = json.loads(result.stdout)
        assert (row.get("decision") == "allow") == expected
        rows.append({"argv": cmd, "expected_allow": expected, "decision": row.get("decision")})
    return rows


def setup():
    proposed = DOC / "allow.rules"
    if proposed.read_text() != rules_text():
        raise ValueError("Reviewed rules changed")
    checks = policy_check(proposed)
    if any(p.is_symlink() for p in (RULE, *RULE.parents)):
        raise ValueError("Protected rule path is a symlink")
    if RULE.exists() and RULE.read_text() != rules_text():
        raise ValueError("Existing different rule preserved")
    if not RULE.exists():
        with RULE.open("x") as stream:
            stream.write(rules_text())
    save(DOC / "policy-check.json", {"status": "PASS", "checks": checks,
         "installed": str(RULE), "sha256": sha(RULE), "managed_review": "SEPARATE"})


def method_files():
    return sorted((ROOT / "scripts").glob("legal_gap_*.py")) + [ROOT / "scripts/run_legal_gap_program.py"]


def freeze(folder):
    from scripts.legal_tool_program import verify as old_verify
    old_verify()
    base = ROOT / "artifacts/legal-interpretation-program/problem-led-follow-up"
    inputs = [OLD / "T0/attempt-1/corpus.json", OLD / "T0/attempt-1/questions.json",
              OLD / "T4/attempt-1/result.json", OLD / "T4/attempt-1/result.md",
              base / "obligation-traces.json", base / "premise-register.json",
              base / "question-provenance.json", DOC / "benchmark.json"]
    trace, premises, readings = read(inputs[4]), read(inputs[5]), read(inputs[6])["readings"]
    assert len(trace) == 46 and len(readings) == 35
    mapping = []
    for row in trace:
        original = row["original_record"]
        requests = [r for r in premises["requests"] if r["obligation_id"] == original["obligation_id"]]
        mapping.append({"ordinal": row["ordinal"], "obligation_id": original["obligation_id"],
            "original_hash": original["original_hash"], "first_unresolved_step": row["first_unresolved_step"],
            "missing_premises": original["missing_premises"],
            "topics": sorted({a["topic"] for r in requests for a in r["atoms"]}),
            "classes": sorted({a["class"] for r in requests for a in r["atoms"]}),
            "closure_requires": "Source argument and established applicability/facts; unchanged original question",
            "status": "OPEN_QUALIFIED"})
    from scripts.legal_gap_report import tool_scope
    for row in mapping:
        row["planned_tool_roles"] = tool_scope(row["classes"], row["topics"])
    assert len({r["obligation_id"] for r in mapping}) == 46
    save(folder / "obligations.json", mapping)
    save(folder / "readings.json", readings)
    inputs += sorted(RES.glob("*.json"))
    inputs += [OLD / "T2/attempt-1/carneades-adapter/trial",
               ROOT / "artifacts/legal-interpretation-program/2026-10-06-offline-v1/P3/attempt-4/graph.json"]
    save(folder / "inputs.json", [ref(p) for p in inputs])
    # Current product, including uncommitted modules, is the actual comparator.
    paths = [p for p in (ROOT / "src/legalmath").rglob("*") if p.is_file() and p.suffix in (".py", ".lean", ".java", ".json", ".sql")]
    paths += list((ROOT / "scripts").glob("legal_interpretation_*.py"))
    paths += list((ROOT / "scripts").glob("legal_tool_*.py"))
    frozen = []
    for path in sorted(paths):
        target = folder / "product" / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        frozen.append({"live": ref(path), "copy": ref(target)})
    save(folder / "product-method.json", frozen)
    return {"status": "FROZEN", "obligations": 46, "readings": 35,
            "unformalized": 32, "inputs": ref(folder / "inputs.json"),
            "product_method": ref(folder / "product-method.json")}


def accepted(phase):
    return read(check_ref(read(OUT / "state.json")["completed"][phase]))


def verify():
    state = read(OUT / "state.json")
    check_ref(state["plan"])
    if state["limits"] != LIMITS or ledger()["maximum"] != LIMITS["provider_calls"]:
        raise ValueError("Budget changed")
    if (OUT / "repairs.json").exists():
        repairs = read(OUT / "repairs.json")
        if repairs["maximum"] != LIMITS["repair_attempts"] or len(repairs["repairs"]) > LIMITS["repair_attempts"]:
            raise ValueError("Invalid repair ledger")
        for row in repairs["repairs"]:
            check_ref(row["evidence"])
    for row in state["failures"]:
        check_ref(row)
    for row in state["completed"].values():
        receipt = read(check_ref(row))
        for item in receipt["outputs"] + receipt["method"]:
            check_ref(item)
    if "G0" in state["completed"]:
        baseline = accepted("G0")["result"]
        for item in read(check_ref(baseline["inputs"])):
            check_ref(item)
        for item in read(check_ref(baseline["product_method"])):
            check_ref(item["live"])
            check_ref(item["copy"])
    if "G3" in state["completed"]:
        for item in read(check_ref(accepted("G3")["result"]["evidence"])):
            check_ref(item)
    assert len(ledger()["calls"]) <= LIMITS["provider_calls"]
    return {"status": "VERIFIED", "program_state": state["status"],
            "completed": list(state["completed"]), "calls": len(ledger()["calls"])}


def execute():
    if not RULE.is_file() or RULE.read_text() != rules_text():
        raise RuntimeError("Reviewed setup required")
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "master.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = OUT / "state.json"
        state = read(path) if path.exists() else {"status": "RUNNING", "started": time.time(),
                 "limits": LIMITS, "plan": ref(PLAN), "completed": {}, "failures": []}
        save(path, state)
        verify()
        for phase in PHASES:
            if phase in state["completed"]:
                continue
            if remaining() <= 0:
                raise RuntimeError("Execution window exhausted")
            folder = OUT / phase / ("attempt-" + str(len(list((OUT / phase).glob("attempt-*"))) + 1))
            folder.mkdir(parents=True)
            save(folder / "refreshed-plan.json", {"phase": phase, "predecessors": state["completed"],
                 "remaining_calls": LIMITS["provider_calls"] - len(ledger()["calls"]),
                 "remaining_seconds": remaining(), "plan": state["plan"],
                 "review": "Source parity, original denominator, missing evidence and phase prerequisites checked",
                 "prior_failures": state["failures"]})
            print("START " + phase, flush=True)
            started = time.monotonic()
            methods = []
            for source in method_files():
                target = folder / "method" / source.name
                target.parent.mkdir(exist_ok=True)
                shutil.copyfile(source, target)
                methods.append(ref(target))
            try:
                if phase == "G0":
                    result = freeze(folder)
                elif phase == "G1":
                    from scripts.legal_gap_tools import run
                    result = run(folder)
                elif phase == "G2":
                    from scripts.legal_gap_live import probe
                    result = probe(folder)
                elif phase == "G3":
                    from scripts.legal_gap_live import compare
                    result = compare(folder)
                else:
                    from scripts.legal_gap_report import run
                    result = run(folder)
                receipt = {"phase": phase, "result": result, "method": methods,
                    "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                    "command": PREFIX + ["execute"], "cpu_only": True, "python": sys.version,
                    "seed": "N/A deterministic controls; provider seed unavailable",
                    "wall_seconds": time.monotonic() - started, "plan": state["plan"],
                    "outputs": [ref(p) for p in sorted(folder.rglob("*")) if p.is_file()
                                and "method" not in p.relative_to(folder).parts]}
                save(folder / "result.json", receipt)
                state["completed"][phase] = ref(folder / "result.json")
                state["status"] = result["status"] if phase == "G4" else "RUNNING"
                save(path, state)
                print("DONE " + phase + " " + result["status"], flush=True)
                return  # Supervisor reviews before the next exact invocation.
            except Exception as exc:
                import traceback
                save(folder / "failure.json", {"type": type(exc).__name__, "error": str(exc),
                     "traceback": traceback.format_exc(), "method": methods})
                state["failures"].append(ref(folder / "failure.json"))
                state["status"] = "REPAIR_REQUIRED"
                save(path, state)
                raise
        print(json.dumps(verify()), flush=True)


def main(argv=None):
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    if Path.cwd().resolve() != ROOT:
        raise ValueError("Use documented repository root")
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("action", choices=ACTIONS)
    action = parser.parse_args(argv).action
    if action == "setup":
        setup()
    elif action == "execute":
        execute()
    elif action == "verify":
        print(json.dumps(verify(), indent=2))
    elif action == "status":
        print(json.dumps(read(OUT / "state.json") if (OUT / "state.json").exists() else {"status": "PREPARED"}, indent=2))
    else:
        result = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/tooling/test_legal_gap_program.py"], timeout=120)
        raise SystemExit(result.returncode)
