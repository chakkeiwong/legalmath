"""Bounded, locked, hash-invalidating phase execution with immutable attempts."""
import fcntl
import inspect
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from .contracts import digest, read, write

REL = "docs/implementation/prospectus-successor-2026-10-06"
DAG = {"P0": [], "P1": ["P0"], "P2": ["P1"], "P3": ["P2"], "P4": ["P1"],
       "P5": ["P2"], "P6": ["P3", "P4", "P5"], "P7": ["P0", "P6"], "P8": ["P6", "P7"]}


def handler(phase):
    from . import jobs
    return getattr(jobs, phase.lower(), None)


def bindings(root):
    paths = list((root / "src/legalmath/prospectus/successor").glob("*.py"))
    paths += list((root / "tests/prospectus_successor").glob("*.py"))
    paths += [root / "scripts/prospectus_delivery.py", root / "src/legalmath/cli.py"]
    paths += list((root / REL / "inputs").glob("*.json"))
    # Conservative invalidation includes reused kernels and retained source bytes.
    for directory in ("src/legalmath/prospectus", "src/legalmath/transaction"):
        paths += list((root / directory).glob("*.py"))
    packet = root / "docs/implementation/prospectus-basf-continuation-2026-10-05/phases/012-construct/basf-selection-admission.json"
    paths.append(packet)
    for row in read(packet)["sources"].values():
        paths += [root / row[k] for k in ("original", "text", "acquisition_receipt")]
    law = root / "docs/prospectus/legal/manifest.json"
    paths.append(law)
    for row in read(law)["sources"]:
        paths += [root / row[k] for k in ("path", "text_path")]
    return {str(p.relative_to(root)): digest(p.read_bytes()) for p in sorted(paths)}


def current(root, state):
    method = digest(bindings(root))
    valid = {}
    for phase, deps in DAG.items():
        row = state.get(phase)
        valid[phase] = bool(row and row.get("method") == method and row.get("artifact_ready")
            and all(valid[d] and row["dependencies"].get(d) == state[d]["receipt_sha256"] for d in deps))
        if valid[phase]:
            receipt = root / row["directory"] / "receipt.json"
            valid[phase] = receipt.is_file() and digest(receipt.read_bytes()) == row["receipt_sha256"]
        if valid[phase]:
            for relative, expected in read(receipt)["outputs"].items():
                p = root / row["directory"] / relative
                if not p.is_file() or digest(p.read_bytes()) != expected:
                    valid[phase] = False
                    break
    return valid


def _refresh(root, state):
    valid = current(root, state)
    rows = []
    for phase, deps in DAG.items():
        fn = handler(phase)
        r = state.get(phase, {})
        rows.append({"phase": phase, "handler_exists": callable(fn), "current": valid[phase],
            "execution": r.get("execution", "NOT_EXECUTED"),
            "engineering": r.get("engineering", "NOT_EXECUTED"),
            "evidence": r.get("evidence", "PENDING"), "release": "NOT_ACCEPTED",
            "can_dispatch": callable(fn) and all(valid[d] for d in deps),
            "first_failed_interface": r.get("remaining", ["Implement registered phase"])[0] if r.get("remaining") else None,
            "remaining": r.get("remaining", []),
            "command": ["python3", "-m", "scripts.prospectus_delivery", "phase", "--phase", phase],
            "invalidation_set": [p for p in DAG if phase in ancestors(p)],
            "limits": {"attempts_per_identical_input": 3, "semantic_repairs": 2, "timeout_seconds": 1800}})
    result = {"phases": rows, "source_requests_used": 188, "source_request_cap": 212,
              "independent_reviewers": [], "automatic_release": False}
    write(root / REL / "next-phase.json", result)
    return result


def ancestors(phase):
    return set(DAG[phase]).union(*(ancestors(p) for p in DAG[phase]))


def refresh(root):
    root = Path(root)
    out = root / REL
    out.mkdir(parents=True, exist_ok=True)
    with (out / "controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _refresh(root, read(out / "state.json") if (out / "state.json").exists() else {})


def execute(root, phase):
    root = Path(root)
    out = root / REL
    out.mkdir(parents=True, exist_ok=True)
    with (out / "controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = read(out / "state.json") if (out / "state.json").exists() else {}
        fn = handler(phase)
        if not callable(fn):
            return {"phase": phase, "execution": "NOT_IMPLEMENTED"}
        valid = current(root, state)
        if valid[phase]:
            return {"phase": phase, "execution": "REUSED", "engineering": state[phase]["engineering"]}
        if not all(valid[d] for d in DAG[phase]):
            _refresh(root, state)
            return {"phase": phase, "execution": "DEPENDENCY_NOT_CURRENT"}
        method_bindings = bindings(root)
        method = digest(method_bindings)
        dependencies = {d: state[d]["receipt_sha256"] for d in DAG[phase]}
        identity = digest({"method": method, "dependencies": dependencies})
        parent = out / "phases" / phase
        parent.mkdir(parents=True, exist_ok=True)
        attempts = sorted(parent.glob("attempt-*"))
        existing = [read(p / "started.json") for p in attempts if (p / "started.json").exists()]
        same = sum(r["input_identity"] == identity for r in existing)
        failed_methods = {r["method"] for r in existing if (parent / r["attempt"] / "failure.json").exists()}
        if same >= 3 or (method not in failed_methods and len(failed_methods) > 2):
            return {"phase": phase, "execution": "REPAIR_REQUIRED", "reason": "Bounded attempt/repair cap"}
        folder = parent / f"attempt-{len(attempts)+1:03d}"
        folder.mkdir()
        started = time.monotonic()
        write(folder / "started.json", {"phase": phase, "attempt": folder.name,
              "input_identity": identity, "method": method, "dependencies": dependencies,
              "dispatched_at": time.time(), "budget_consumed_before_dispatch": True})
        old_alarm = signal.getsignal(signal.SIGALRM)
        def alarm(_signum, _frame):
            raise TimeoutError("Phase exceeded 1800 second limit")
        signal.signal(signal.SIGALRM, alarm)
        signal.alarm(1800)
        try:
            result = fn(root, folder, state)
            if not isinstance(result, dict) or "engineering" not in result or "remaining" not in result:
                raise ValueError("Phase omitted acceptance disposition")
            result = {**result, "execution": "EXECUTED", "release": "NOT_ACCEPTED"}
        except Exception as exc:
            import traceback
            write(folder / "failure.json", {"error": str(exc), "traceback": traceback.format_exc()})
            result = {"execution": "FAILED", "engineering": "REPAIR_REQUIRED", "evidence": "PENDING",
                      "artifact_ready": False, "remaining": [str(exc)]}
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_alarm)
        write(folder / "result.json", result)
        manifest = {"phase": phase, "command": ["python3", "-m", "scripts.prospectus_delivery", "phase", "--phase", phase],
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "environment": sys.executable, "python": sys.version, "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1",
            "random_seeds": "N/A deterministic engineering", "wall_seconds": time.monotonic()-started,
            "plan": "docs/plans/prospectus-delivery-execution-2026-10-06.md",
            "result_file": str((folder / "result.json").relative_to(root)), "input_bindings": method_bindings,
            "dependencies": dependencies, "data_version": identity}
        write(folder / "manifest.json", manifest)
        outputs = {str(p.relative_to(folder)): digest(p.read_bytes()) for p in sorted(folder.rglob("*"))
                   if p.is_file() and p.name != "receipt.json"}
        write(folder / "receipt.json", {"outputs": outputs, "result": result, "input_identity": identity})
        state[phase] = {**result, "method": method, "dependencies": dependencies,
            "directory": str(folder.relative_to(root)), "receipt_sha256": digest((folder / "receipt.json").read_bytes())}
        write(out / "state.json", state)
        _refresh(root, state)
        return {"phase": phase, **result, "directory": state[phase]["directory"]}
