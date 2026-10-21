#!/usr/bin/env python3
"""Detached settlement hook for the registered integration master; no new grants.

Public actions take no paths or commands. A per-step receipt writer survives
loss of the watcher. Unknown outcomes are never silently replayed.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import Refused, require, read, ref, safe, verify

SCRIPT = Path("scripts/legal_integration_continuation.py")
WORK = Path("artifacts/legal-mission-control/2026-10-18/continuation-hook")
BASE = Path("artifacts/legal-mission-control/2026-10-13/master")
PROGRAM = Path("docs/implementation/legal-mission-control/integration-master.json")
MISSION = Path("docs/implementation/legal-mission-control/mission.json")
STATE = BASE / "execution-state.json"
PREDECESSOR = Path("artifacts/legal-mission-control/2026-10-17/gap-refresh/settled-recovery/execution")
PLAN = Path("docs/plans/legal-integration-continuation-hook-2026-10-18.md")
REVIEW = WORK / "review.json"
TESTS = Path("tests/tooling/test_integration_continuation_hook.py")
POLL_SECONDS = 15
CHECK_TIMEOUT = 900
COMMANDS = {
    **{a: [".venv/bin/python", "scripts/legal_mission_control.py", a]
       for a in ("refresh", "check", "status", "admit")},
    **{a: [".venv-context/bin/python", "scripts/legal_integration_master.py", a]
       for a in ("verify", "run", "live")},
}
GATES = ("refresh", "verify", "check", "status", "admit")


def now():
    return datetime.now(timezone.utc).isoformat()


def durable_save(path, value):
    """Publish one journal transition, including its directory entry."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".writing")
    with temp.open("w") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield handle


def identity(pid):
    """Distinguish a dead process from an unreadable process identity."""
    try:
        fields = Path(f"/proc/{int(pid)}/stat").read_text().rsplit(") ", 1)[1].split()
    except FileNotFoundError:
        return None
    except (OSError, ValueError, IndexError) as exc:
        raise Refused(f"Uncertain process identity {pid}: {exc}") from exc
    if fields[0] in ("Z", "X"):
        return None
    return {"pid": int(pid), "start": fields[19]}


def alive(value):
    if value is None:
        return False
    require(set(value) == {"pid", "start"} and value["pid"] > 0,
            "Malformed process identity")
    return identity(value["pid"]) == value


def pid_namespace():
    return os.readlink("/proc/self/ns/pid")


def require_namespace(manifest):
    require(pid_namespace() == manifest["pid_namespace"],
            "Different PID namespace: use trusted execution to authenticate the host workers")


def lock_busy(path):
    try:
        with locked(path):
            return False
    except BlockingIOError:
        return True


def fingerprint(view):
    """Ignore timestamps/events; include outcomes, attempts and blocked reasons."""
    packet = {"tasks": view["tasks"], "mission_sync_error": view.get("mission_sync_error")}
    return hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest()


def selection(view, grant, calls, attempted, *, external_uncertain=False, at=None):
    """Select existing executors independently; spent owners are never reopened."""
    at = at or datetime.now(timezone.utc)
    key = fingerprint(view)
    eligible = {name: row for name, row in view["tasks"].items()
                if row["status"] == "READY" and row["attempts_used"] < row["maximum_attempts"]}
    reasons = {name: "Original task attempt ceiling exhausted" for name, row in view["tasks"].items()
               if row["status"] == "READY" and name not in eligible}
    live_allowed = (not external_uncertain and grant.get("approved") is True
                    and at < datetime.fromisoformat(grant["deadline_utc"])
                    and calls < grant["maximum_calls"])
    for action, executor in (("run", "command"), ("live", "agent")):
        names = [name for name, row in eligible.items() if row["executor"] == executor]
        # Command recovery adopts receipts without spending an owner attempt.
        if action == "run":
            names += [name for name, row in view["tasks"].items()
                      if row["status"] == "RUNNING" and row["executor"] == "command"]
        if not names:
            continue
        if action == "live" and not live_allowed:
            reason = ("Unknown prior dispatch requires reconciliation" if external_uncertain else
                      "Original live grant expired" if at >= datetime.fromisoformat(grant["deadline_utc"]) else
                      "Original shared call ceiling exhausted" if calls >= grant["maximum_calls"] else
                      "Original live grant is not approved")
            reasons.update({name: reason for name in names})
            continue
        if [action, key] in attempted:
            reasons.update({name: "Executor already tried at this unchanged frontier" for name in names})
            continue
        return action, key, reasons
    return None, key, reasons


class Hook:
    def __init__(self, root=ROOT, work=WORK, *, poll=POLL_SECONDS):
        self.root, self.work = Path(root), Path(work)
        self.directory = self.root / self.work
        self.manifest_path = self.directory / "registration.json"
        self.journal_path = self.directory / "journal.json"
        self.poll = poll

    def manifest(self):
        value = read(self.manifest_path)
        require(value["profile"] == "integration-continuation-hook.v1", "Unknown hook registration")
        require(value["commands"] == COMMANDS, "Unreviewed hook command")
        for pointer in value["protected"]:
            verify(self.root, pointer)
        require(value["attempts_reset"] is False and value["calls_added"] == 0
                and value["deadline_extended"] is False, "Hook cannot grant new authority")
        return value

    def journal(self):
        if self.journal_path.exists():
            value = read(self.journal_path)
            require(value["registration"] == ref(self.root, self.manifest_path), "Changed hook registration")
            return value
        return {"registration": ref(self.root, self.manifest_path), "status": "REGISTERED",
                "steps": [], "attempted": [], "round": 0, "external_uncertain": False}

    def publish(self, journal, status, **fields):
        journal.update(status=status, updated_at_utc=now(), process=identity(os.getpid()), **fields)
        durable_save(self.journal_path, journal)

    def predecessor_busy(self, manifest):
        processes = list(manifest["predecessor_processes"])
        # A writer may have started a command/consumer since registration.
        state = read(self.root / STATE)
        for row in state["tasks"].values():
            if row["status"] != "RUNNING":
                continue
            processes.append(row.get("live_supervisor"))
            if row["attempts"]:
                processes += [row["attempts"][-1].get(k) for k in ("worker", "supervisor")]
        active = [p for p in processes if p and alive(p)]
        busy = [name for name in manifest["writer_locks"] if lock_busy(safe(self.root, name))]
        return {"processes": active, "locks": busy}

    def snapshot(self):
        from scripts.legal_integration_master import MasterExecution
        return MasterExecution(self.root, PROGRAM, STATE).summary()

    def start_step(self, journal, action):
        require(action in COMMANDS, "Unknown fixed action")
        index = len(journal["steps"])
        folder = self.directory / "steps" / f"{index:04d}-{action}"
        require(not folder.exists(), "Existing unjournaled step needs reconciliation")
        intent = {"action": action, "command": COMMANDS[action], "at_utc": now(),
                  "registration": ref(self.root, self.manifest_path), "index": index}
        durable_save(folder / "intent.json", intent)
        journal["steps"].append({"path": str(folder.relative_to(self.root)), "action": action})
        self.publish(journal, "EXECUTING", active_step=index)
        # The child writes its identity before it dispatches the master command.
        # A crash in the spawn gap leaves an uncertain intent, never a retry.
        with (folder / "wrapper.log").open("ab") as log:
            subprocess.Popen([str(self.root / ".venv-context/bin/python"), str(self.root / SCRIPT),
                              "_step", str(index)], cwd=self.root, stdout=log, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)

    def step_outcome(self, row):
        folder = safe(self.root, row["path"])
        intent = read(folder / "intent.json")
        require(intent["registration"] == ref(self.root, self.manifest_path)
                and intent["action"] == row["action"]
                and intent["command"] == COMMANDS[row["action"]], "Changed step intent")
        result_path = folder / "receipt.json"
        if result_path.exists():
            result = read(result_path)
            require(result["intent"] == ref(self.root, folder / "intent.json"), "Changed step receipt")
            for pointer in result["evidence"]:
                verify(self.root, pointer)
            return result
        for name in ("worker.json", "command.json"):
            if (folder / name).exists():
                record = read(folder / name)
                require(record["intent"] == ref(self.root, folder / "intent.json"), "Changed worker receipt")
                if alive(record["process"]):
                    return None
        if lock_busy(self.directory / "action.lock"):
            return None
        # Let a freshly exec'd receipt writer publish its PID before inspecting
        # an interrupted spawn. Older intents lacking evidence are uncertain.
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(intent["at_utc"])).total_seconds()
        if age < 30:
            return None
        return {"action": row["action"], "unknown_outcome": True, "exit_code": None,
                "reason": "No authenticated surviving worker, command or terminal receipt; never replayed",
                "intent": ref(self.root, folder / "intent.json"), "evidence": []}

    def action(self, journal, action):
        if "active_step" not in journal:
            self.start_step(journal, action)
        row = journal["steps"][journal["active_step"]]
        require(row["action"] == action, "Restart selected a different pending step")
        while True:
            result = self.step_outcome(row)
            if result is not None:
                row["result"] = result
                # Keep the receipt pending until the caller commits its cursor
                # in the same journal write. Otherwise a watcher crash between
                # receipt and cursor publication could duplicate this action.
                self.publish(journal, "ACTION_SETTLED")
                return result
            self.publish(journal, "WAITING_ACTION", action=action)
            time.sleep(self.poll)

    def gates(self, journal):
        # Cursor persistence avoids replaying completed checks on watcher death.
        cursor = journal.setdefault("gate_cursor", 0)
        failed = journal.setdefault("gate_failures", [])
        while cursor < len(GATES):
            action = GATES[cursor]
            result = self.action(journal, action)
            if result.get("unknown_outcome") or result.get("exit_code") != 0:
                failed.append({"action": action, "result": result})
            cursor += 1
            journal["gate_cursor"] = cursor
            journal.pop("active_step")
            self.publish(journal, "VALIDATING")
        return not failed

    def finish(self, journal, view, reason, *, blockers=None):
        path = self.directory / "result.json"
        if not path.exists():
            predecessor = self.root / PREDECESSOR / "worker-result.json"
            terminal = "SETTLED" if view and view["execution"] == "COMPLETE" else "BLOCKED"
            result = {"profile": "integration-continuation-result.v1", "status": terminal,
                      "reason": reason, "frontier": view, "additional_blockers": blockers or {},
                      "registration": ref(self.root, self.manifest_path), "steps": journal["steps"],
                      "predecessor_result": ref(self.root, predecessor) if predecessor.exists() else None,
                      "finished_at_utc": now(), "integration_complete": False, "legal_acceptance": False,
                      "local_engineering_packages": 1, "prior_detours": 54,
                      "attempts_reset": False, "calls_added": 0, "deadline_extended": False}
            durable_save(path, result)
        self.publish(journal, read(path)["status"], reason=reason, result=ref(self.root, path))
        return read(path)

    def watch(self):
        with locked(self.directory / "watch.lock"):
            manifest = self.manifest()
            require_namespace(manifest)
            journal = self.journal()
            self.publish(journal, journal["status"])
            if (self.directory / "result.json").exists():
                result = read(self.directory / "result.json")
                self.publish(journal, result["status"], result=ref(self.root, self.directory / "result.json"))
                return result
            if not journal.get("predecessor_settled"):
                while True:
                    self.manifest()
                    busy = self.predecessor_busy(manifest)
                    if not busy["processes"] and not busy["locks"]:
                        break
                    self.publish(journal, "WAITING_PREDECESSOR", waiting=busy)
                    time.sleep(self.poll)
                journal["predecessor_settled"] = now()
                # A dead live owner without a terminal result is NOT permission
                # to replay its last external dispatch, even at the same attempt.
                state = read(self.root / STATE)
                journal["external_uncertain"] = any(
                    row["status"] == "RUNNING" and row.get("master_live")
                    for row in state["tasks"].values())
                self.publish(journal, "PREDECESSOR_SETTLED", waiting={})
            while True:
                self.manifest()
                if not self.gates(journal):
                    return self.finish(journal, None, "Common validation gates failed; inspect exact receipts",
                                       blockers={"gates": journal["gate_failures"]})
                view = self.snapshot()
                durable_save(self.directory / f"frontier-{journal['round']:04d}.json", view)
                grant = read(self.root / BASE / "live-grant.json")
                calls = len(read(self.root / BASE / "live-calls.json")["calls"])
                # Restart must finish/adopt its pending drain before selecting.
                if journal.get("drain"):
                    action, key = journal["drain"]
                    blockers = {}
                else:
                    action, key, blockers = selection(view, grant, calls, journal["attempted"],
                        external_uncertain=journal["external_uncertain"])
                if action is None:
                    return self.finish(journal, view, "No untried authorized ready work remains", blockers=blockers)
                if journal["round"] >= manifest["maximum_drains"]:
                    return self.finish(journal, view, "Finite hook drain bound reached; review unchanged blockers")
                if not journal.get("drain"):
                    journal["drain"] = [action, key]
                    journal["attempted"].append([action, key])
                    self.publish(journal, "DISPATCH_SELECTED")
                result = self.action(journal, action)
                if result.get("unknown_outcome"):
                    if action == "live":
                        journal["external_uncertain"] = True
                    # Local orphan commands are reconciled only through the
                    # existing master recovery, not by replaying this step.
                journal.pop("drain")
                journal.pop("active_step")
                journal["round"] += 1
                journal["gate_cursor"] = 0
                journal["gate_failures"] = []
                self.publish(journal, "REFRESH_AFTER_OUTCOME")


def execute_step(hook, index):
    root = hook.root
    require_namespace(hook.manifest())
    journal = hook.journal()
    require(0 <= index < len(journal["steps"]), "Unknown hook step")
    row = journal["steps"][index]
    folder = safe(root, row["path"])
    intent_path = folder / "intent.json"
    intent = read(intent_path)
    require(intent["index"] == index and intent["action"] == row["action"]
            and intent["registration"] == ref(root, hook.manifest_path)
            and intent["command"] == COMMANDS[row["action"]], "Unreviewed step intent")
    with locked(hook.directory / "action.lock") as lock:
        require(not (folder / "worker.json").exists() and not (folder / "receipt.json").exists(),
                "Step already launched; never duplicate")
        pointer = ref(root, intent_path)
        durable_save(folder / "worker.json", {"process": identity(os.getpid()), "intent": pointer})
        began = time.monotonic()
        code, timed_out, error = None, False, None
        command = intent["command"]
        with (folder / "stdout").open("xb") as out, (folder / "stderr").open("xb") as err:
            try:
                # The command retains the action lock if this receipt writer is
                # killed in the spawn/identity publication window.
                child = subprocess.Popen(command, cwd=root, stdout=out, stderr=err,
                                         stdin=subprocess.DEVNULL, pass_fds=(lock.fileno(),))
                durable_save(folder / "command.json", {"process": identity(child.pid),
                                                       "intent": pointer, "command": command})
                try:
                    code = child.wait(timeout=CHECK_TIMEOUT if row["action"] in GATES else None)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    child.kill()
                    code = child.wait()
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
        durable_save(folder / "receipt.json", {"action": row["action"], "command": command,
                     "intent": pointer, "exit_code": code, "timed_out": timed_out, "error": error,
                     "wall_seconds": time.monotonic() - began, "finished_at_utc": now(),
                     "evidence": [ref(root, folder / name) for name in ("stdout", "stderr")]})


def register():
    hook = Hook()
    with locked(hook.directory / "registration.lock"):
        if hook.manifest_path.exists():
            hook.manifest()
            return {"registered": True, "registration": ref(ROOT, hook.manifest_path)}
        review = read(ROOT / REVIEW)
        require(review["verdict"] == "PASS" and review["provider_calls"] == 0, "Hook review must pass")
        require(review["pid_namespace"].startswith("pid:[") and review["pid_namespace"].endswith("]"),
                "Review must retain the actual host worker PID namespace")
        for pointer in review["evidence"]:
            verify(ROOT, pointer)
        start = read(ROOT / PREDECESSOR / "worker-start.json")
        protected = [start[key] for key in ("program", "binding", "grant", "source")]
        protected += [ref(ROOT, path) for path in (SCRIPT, TESTS, PLAN, REVIEW,
                       PREDECESSOR / "worker-start.json", PREDECESSOR / "worker-live-process.json")]
        for pointer in protected:
            verify(ROOT, pointer)
        binding = read(ROOT / BASE / "current-binding.json")
        protected_paths = {item["path"] for item in binding["bindings"]}
        require(not protected_paths.intersection(map(str, (SCRIPT, TESTS, PLAN, REVIEW))),
                "Hook installation would change an active bound file")
        from scripts.legal_integration_phased_live import LIVE, active_live
        program, state = read(ROOT / PROGRAM), read(ROOT / STATE)
        remaining = sum(max(0, t["maximum_attempts"] - len(state["tasks"][t["id"]]["attempts"]))
                        for t in program["tasks"])
        locks = [PREDECESSOR / "worker.lock", PREDECESSOR.parent.parent / "detached-worker.lock",
                 LIVE / "supervisor.lock", active_live(program) / "supervisor.lock",
                 STATE.with_suffix(".run.lock")]
        if binding.get("phase_service_scope"):
            locks.append(Path(binding["phase_service_scope"]["path"]).parent / "service-worker.lock")
        value = {"profile": "integration-continuation-hook.v1", "user_instruction": "do the automatic continuation hook",
                 "pid_namespace": review["pid_namespace"],
                 "master_program": str(PROGRAM), "commands": COMMANDS, "protected": protected,
                 "predecessor_processes": [start["process"], read(ROOT / PREDECESSOR / "worker-live-process.json")["process"]],
                 "writer_locks": list(dict.fromkeys(map(str, locks))), "maximum_drains": remaining + len(program["tasks"]) + 2,
                 "registered_at_utc": now(), "attempts_reset": False, "calls_added": 0,
                 "deadline_extended": False, "prior_detours": 54, "local_engineering_packages": 1,
                 "environment": str(ROOT / ".venv-context/bin/python"), "devices": "CPU only; CUDA_VISIBLE_DEVICES=-1",
                 "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()}
        durable_save(hook.manifest_path, value)
        return {"registered": True, "registration": ref(ROOT, hook.manifest_path)}


def status():
    hook = Hook()
    manifest = hook.manifest()
    journal = hook.journal()
    visible = pid_namespace() == manifest["pid_namespace"]
    return {key: journal.get(key) for key in ("status", "updated_at_utc", "process", "waiting", "round", "reason")} | {
        "alive": alive(journal.get("process")) if visible else None,
        "process_visibility": "host namespace verified" if visible else "different PID namespace; use trusted status",
        "registration": ref(ROOT, hook.manifest_path),
        "journal": str(WORK / "journal.json"), "integration_complete": False}


def arm():
    hook = Hook()
    require_namespace(hook.manifest())
    with locked(hook.directory / "launch.lock"):
        if (lock_busy(hook.directory / "lifecycle.lock")
                or lock_busy(hook.directory / "watch.lock")):
            return status()
        if (hook.directory / "finalization.json").exists():
            return status()
        with (hook.directory / "watch.log").open("ab") as output:
            child = subprocess.Popen([str(ROOT / ".venv-context/bin/python"), str(ROOT / SCRIPT), "watch"],
                                     cwd=ROOT, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                                     start_new_session=True)
        process = identity(child.pid)
        require(process is not None, "Watcher ended before its process identity was captured; inspect watch.log")
        for _ in range(100):
            if hook.journal_path.exists() and read(hook.journal_path).get("process") == process:
                receipt = {"profile": "integration-continuation-armed.v1", "process": process,
                           "registration": ref(ROOT, hook.manifest_path), "command": [str(ROOT / ".venv-context/bin/python"), str(SCRIPT), "arm"],
                           "at_utc": now(), "status_at_arm": read(hook.journal_path)["status"], "provider_calls": 0}
                path = hook.directory / f"armed-{child.pid}.json"
                durable_save(path, receipt)
                return status() | {"armed_receipt": ref(ROOT, path)}
            require(child.poll() is None, "Detached watcher exited; inspect watch.log")
            time.sleep(0.1)
        raise Refused("Watcher startup not confirmed; inspect PID/locks before retry")


def record_history(path, identifier, decision):
    from scripts import legal_mission_control as control
    with (ROOT / MISSION).with_suffix(".execution.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        mission = read(ROOT / MISSION)
        require(mission["current_task"] == "product-contribution", "Current admission changed")
        evidence = [ref(ROOT, path)]
        previous = [r for r in mission["history"] if r["id"] == identifier]
        reason = ("Use the installed same-master continuation hook. Continue original independent ready work; "
                  "retain exact spent-attempt, missing-repair, authority and service blockers. No allocation renewed.")
        if previous:
            require(len(previous) == 1 and previous[0]["result_evidence"] == evidence, "Changed hook history evidence")
        else:
            mission["history"].append({"id": identifier, "task_id": "product-contribution", "kind": "product_evaluation",
                "outcome": "no_advance", "decision": decision, "next_task": "product-contribution",
                "next_task_reason": reason, "recorded_at_utc": now(), "result_evidence": evidence})
            mission["next_task_reason"] = reason
            control.validate(mission, read(ROOT / "docs/implementation/legal-mission-control/tools.json"), ROOT)
            durable_save(ROOT / MISSION, mission)


def record():
    hook = Hook()
    require_namespace(hook.manifest())
    armed = sorted(hook.directory.glob("armed-*.json"), key=lambda p: read(p)["at_utc"])
    require(armed, "Hook not armed")
    receipt = read(armed[-1])
    require(receipt["registration"] == ref(ROOT, hook.manifest_path), "Changed armed registration")
    installation = hook.directory / "installation-result.json"
    if not installation.exists():
        active = alive(receipt["process"]) and lock_busy(hook.directory / "lifecycle.lock")
        settled = (hook.directory / "finalization.json").exists()
        if settled:
            require(read(hook.directory / "finalization.json")["result"]
                    == ref(ROOT, hook.directory / "result.json"), "Changed settled hook result")
        require(active or settled, "Hook is neither active nor retained as settled")
        durable_save(installation, {"profile": "integration-continuation-installation.v1", "installed": True,
            "armed": ref(ROOT, armed[-1]), "registration": ref(ROOT, hook.manifest_path), "review": ref(ROOT, REVIEW),
            "at_utc": now(), "local_engineering_packages": 1, "prior_detours": 54, "provider_calls": 0,
            "integration_complete": False, "legal_acceptance": False})
    record_history(installation, "continuation-hook-20261018-installed",
                   "One local engineering package: reviewed automatic continuation hook installed and armed. "
                   "Original allocations unchanged. This is delivery repair, not substantive legal progress.")
    with (hook.directory / "installation-refresh.stdout").open("w") as out, (hook.directory / "installation-refresh.stderr").open("w") as err:
        result = subprocess.run(COMMANDS["refresh"], cwd=ROOT, stdout=out, stderr=err, timeout=CHECK_TIMEOUT)
    durable_save(hook.directory / "installation-refresh.json", {"command": COMMANDS["refresh"], "exit_code": result.returncode,
                 "at_utc": now(), "evidence": [ref(ROOT, hook.directory / ("installation-refresh." + name)) for name in ("stdout", "stderr")]})
    require(result.returncode == 0, "Mission refresh failed; inspect retained installation-refresh files")
    return {"recorded": True, "refresh_exit_code": result.returncode, "result": ref(ROOT, installation)}


def finalize(hook):
    """Idempotent retention, protected by the production lifecycle lock."""
    result_path = hook.directory / "result.json"
    completion = hook.directory / "finalization.json"
    if completion.exists():
        receipt = read(completion)
        require(receipt["result"] == ref(hook.root, result_path), "Changed finalized result")
        for pointer in receipt["evidence"]:
            verify(hook.root, pointer)
        return
    record_history(result_path, "continuation-hook-20261018-settled",
                   "Automatic hook settled with retained original frontier and exact blockers; no legal closure claimed.")
    refresh_path = hook.directory / "final-refresh.json"
    if refresh_path.exists() and read(refresh_path)["exit_code"] == 0:
        for pointer in read(refresh_path)["evidence"]:
            verify(hook.root, pointer)
    else:
        with (hook.directory / "final-refresh.stdout").open("w") as out, (hook.directory / "final-refresh.stderr").open("w") as err:
            refreshed = subprocess.run(COMMANDS["refresh"], cwd=hook.root, stdout=out, stderr=err, timeout=CHECK_TIMEOUT)
        durable_save(refresh_path, {"exit_code": refreshed.returncode, "command": COMMANDS["refresh"],
            "at_utc": now(), "evidence": [ref(hook.root, hook.directory / ("final-refresh." + name))
                                           for name in ("stdout", "stderr")]})
        require(refreshed.returncode == 0, "Final mission refresh failed; retained result still valid")
    durable_save(completion, {"result": ref(hook.root, result_path), "finished_at_utc": now(),
        "evidence": [ref(hook.root, refresh_path)], "history_id": "continuation-hook-20261018-settled"})


def watch_and_retain(hook):
    # Keep the production writer exclusive until terminal history is retained.
    # A restart with a saved result only completes retention, never dispatches.
    with locked(hook.directory / "lifecycle.lock"):
        try:
            result = hook.watch()
            finalize(hook)
            return result
        except Exception as exc:
            error_path = hook.directory / f"error-{time.time_ns()}.json"
            durable_save(error_path, {"error": f"{type(exc).__name__}: {exc}", "at_utc": now(),
                "traceback": traceback.format_exc(), "process": identity(os.getpid()),
                "result_retained": (hook.directory / "result.json").exists()})
            if hook.journal_path.exists():
                journal = hook.journal()
                hook.publish(journal, "ERROR", error=ref(hook.root, error_path))
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("register", "arm", "status", "record", "watch", "_step"))
    parser.add_argument("index", nargs="?", type=int)
    args = parser.parse_args()
    require((args.action == "_step") == (args.index is not None), "Only internal step accepts an index")
    if args.action == "_step":
        execute_step(Hook(), args.index)
        return
    if args.action == "watch":
        result = watch_and_retain(Hook())
    else:
        result = {"register": register, "arm": arm, "status": status, "record": record}[args.action]()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
