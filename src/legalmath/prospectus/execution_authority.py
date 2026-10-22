"""Prospectus task admission and evidence transitions; no legal-truth oracle."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time

REL = "docs/implementation/prospectus-execution-authority"
CODE = ("src/legalmath/prospectus/execution_authority.py",
        "src/legalmath/prospectus/execution_workers.py", "scripts/prospectus_control.py",
        "src/legalmath/prospectus/execution_acceptance.py", "src/legalmath/prospectus/build_contract.py")
HANDLERS = {"native-cohort", "native-interfaces", "agent", "external"}


def read(path):
    return json.loads(Path(path).read_text())


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode()).hexdigest()


def file_hash(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write(path, value, *, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if exclusive:
        temporary = path.with_name(path.name + f".{os.getpid()}.{time.monotonic_ns()}.pending")
        with temporary.open("x") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        finally:
            temporary.unlink()
        return
    temporary = path.with_name(path.name + ".new")
    with temporary.open("w") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def process_identity(pid):
    try:
        fields = Path(f"/proc/{int(pid)}/stat").read_text().rsplit(")", 1)[1].split()
        if fields[0] == "Z":
            return None
        return {"pid": int(pid), "start_ticks": fields[19],
                "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                "pid_namespace": os.readlink(f"/proc/{int(pid)}/ns/pid")}
    except (OSError, ValueError, IndexError):
        return None


class Authority:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.base = self.root / REL

    def path(self, name):
        path = (self.root / name).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Path escapes worktree: " + str(name))
        return path

    @contextmanager
    def lock(self, *, blocking=False):
        self.base.mkdir(parents=True, exist_ok=True)
        with (self.base / "writer.lock").open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
            yield

    def events(self):
        events, previous = [], None
        for index, path in enumerate(sorted((self.base / "history").glob("*.json")), 1):
            row = read(path)
            value = {k: v for k, v in row.items() if k != "sha256"}
            if row["seq"] != index or row["previous"] != previous or digest(value) != row["sha256"]:
                raise ValueError("Invalid event history: " + str(path))
            events.append(row)
            previous = row["sha256"]
        return events

    def append(self, kind, **fields):
        events = self.events()
        row = {"seq": len(events) + 1, "previous": events[-1]["sha256"] if events else None,
               "kind": kind, "at": datetime.now(timezone.utc).isoformat(), **fields}
        row["sha256"] = digest(row)
        write(self.base / "history" / f'{row["seq"]:06d}.json', row, exclusive=True)
        return row

    def spec(self):
        program = read(self.base / "program.json")
        revisions = [e for e in self.events() if e["kind"] == "REVISION"]
        if not revisions or revisions[-1]["program_sha256"] != digest(program):
            raise ValueError("Program differs from reviewed active revision")
        for revision in revisions:
            if revision.get("review_sha256") and file_hash(self.path(revision["review"])) != revision["review_sha256"]:
                raise ValueError("Retained revision review changed")
        saved = read(self.base / "revisions" / f'{program["revision"]:04d}.json')
        if saved != program:
            raise ValueError("Reviewed revision changed")
        return self.validate_program(program)

    def validate_program(self, program):
        inventory = read(self.base / "baseline/inventory.json")
        if digest(inventory) != program["inventory_sha256"]:
            raise ValueError("Original obligation inventory changed")
        if program["version"] != "prospectus-authority.v1":
            raise ValueError("Unsupported program version")
        obligations = {r["id"]: r for r in program["obligations"]}
        tasks = {r["id"]: r for r in program["tasks"]}
        if len(tasks) != len(program["tasks"]) or len(obligations) != len(program["obligations"]):
            raise ValueError("Duplicate task/obligation")
        if set(obligations) != {r["id"] for r in inventory}:
            raise ValueError("Missing or invented migration obligation")
        for old in inventory:
            row = obligations[old["id"]]
            if row["origin"] != old["origin"] or row["scope"] != old["scope"]:
                raise ValueError("Obligation source or scope changed")
            if not row["tasks"] or not set(row["tasks"]) <= tasks.keys():
                raise ValueError("Unmapped obligation: " + row["id"])
        for name, expected in program["baseline_files"].items():
            if file_hash(self.path(name)) != expected:
                raise ValueError("Corrupt baseline: " + name)
        for task in tasks.values():
            required = {"id", "title", "handler", "depends_on", "obligations", "inputs",
                        "dossier", "acceptance", "budget_key", "timeout_seconds", "reason"}
            if not required <= task.keys() or task["handler"] not in HANDLERS:
                raise ValueError("Invalid task specification")
            from .execution_acceptance import check_task
            check_task(task)
            if not re.fullmatch(r"[a-z][a-z0-9-]{0,79}", task["id"]):
                raise ValueError("Invalid task identifier")
            if task.get("stream") not in {"engineering", "assisted", "automatic", "package_evaluation"}:
                raise ValueError("Task needs its completion stream")
            if task["budget_key"] not in program["budgets"] or not task["obligations"]:
                raise ValueError("Missing original budget lineage")
            for oid in task["obligations"]:
                if oid not in obligations or task["id"] not in obligations[oid]["tasks"]:
                    raise ValueError("Task/obligation mapping disagrees")
                if task["budget_key"] not in obligations[oid]["budget_keys"]:
                    raise ValueError("Task renaming cannot change its budget lineage")
            if any(dep not in tasks for dep in task["depends_on"]):
                raise ValueError("Unknown dependency")
            if task.get("repair_of") and task["repair_of"] not in tasks:
                raise ValueError("Unknown failed-task trigger")
            if task.get("repair_of"):
                original = tasks[task["repair_of"]]
                if task["acceptance"] != original["acceptance"] or not set(original["obligations"]) <= set(task["obligations"]):
                    raise ValueError("A repair must satisfy the original acceptance criterion and obligations")
            if not 0 < task["timeout_seconds"] <= 7200:
                raise ValueError("Invalid timeout")
            supplied = task.get("external_evidence", [])
            if not isinstance(supplied, list) or (supplied and task["handler"] != "external"):
                raise ValueError("Only external tasks may bind supplied external evidence")
            for item in supplied:
                if (not isinstance(item, dict) or set(item) != {"path", "sha256"}
                        or item["path"] not in task["inputs"]
                        or not isinstance(item["sha256"], str)
                        or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])):
                    raise ValueError("External evidence must be a hashed admitted input")
                self.path(item["path"])
            external_paths = {item["path"] for item in supplied}
            for name in task["inputs"] + [task["dossier"]]:
                if name in external_paths and name != task["dossier"]:
                    continue  # Unavailable supplied evidence waits without blocking other tasks.
                if not self.path(name).is_file():
                    raise ValueError("Missing retained task dossier/input: " + name)
        ordered, pending = [], dict(tasks)
        while pending:
            ready = [k for k, v in pending.items() if set(v["depends_on"]) <= set(ordered)]
            if not ready:
                raise ValueError("Task dependency cycle")
            for key in ready:
                ordered.append(key)
                del pending[key]
        from .build_contract import check
        check(program, self.root)
        return program, tasks, ordered

    def binding(self, task):
        names = list(CODE) + task["inputs"] + [task["dossier"]]
        for dependency in task["depends_on"]:
            accepted = next((e for e in reversed(self.events()) if e.get("task") == dependency and e["kind"] == "ACCEPT"), None)
            if accepted:
                names.append(accepted["attempt"] + "/outputs.json")
        return {name: file_hash(self.path(name)) for name in sorted(set(names))}

    def retained_evidence_valid(self, event):
        """Verify immutable output/admission identity even for partial work."""
        attempt = self.path(event["attempt"])
        admitted = next(e for e in self.events() if e["kind"] == "ADMIT" and e.get("attempt") == event["attempt"])
        if file_hash(attempt / "admission.json") != admitted["admission_sha256"]:
            return False
        manifest = read(attempt / "outputs.json")
        if "result.json" not in manifest or file_hash(attempt / "outputs.json") != event["outputs_sha256"]:
            return False
        return all(self.path(str(attempt.relative_to(self.root) / name)).is_relative_to(attempt)
                   and file_hash(attempt / name) == expected for name, expected in manifest.items())

    def attempt_valid(self, event, task):
        admission = read(self.path(event["attempt"]) / "admission.json")
        return (self.retained_evidence_valid(event) and admission["binding"] == self.binding(task)
                and admission["task_sha256"] == digest(task))

    def external_evidence_ready(self, task):
        supplied = task.get("external_evidence", [])
        try:
            return bool(supplied) and all(file_hash(self.path(item["path"])) == item["sha256"] for item in supplied)
        except OSError:
            return False

    def status(self):
        program, tasks, order = self.spec()
        events = self.events()
        latest, spent = {}, {k: 0 for k in program["budgets"]}
        for event in events:
            if event["kind"] == "ADMIT":
                spent[event["budget_key"]] += 1
            if event.get("task"):
                latest[event["task"]] = event
        accepted_repairs = {}
        for key, task in tasks.items():
            event = latest.get(key, {})
            if task.get("repair_of") and event.get("kind") == "ACCEPT":
                accepted_repairs[task["repair_of"]] = (task, event)
        rows = {}
        for key in order:
            task, event = tasks[key], latest.get(key)
            evidence_task = task
            if key in accepted_repairs:
                evidence_task, event = accepted_repairs[key]
            state, reason = "READY", task["reason"]
            if task["handler"] == "external":
                state, reason = "WAITING_EXTERNAL", task["external_input"]
                if self.external_evidence_ready(task):
                    state, reason = "READY", "Bound external files available for substantive review; authenticity/independence not inferred"
            if event:
                kind = event["kind"]
                state = {"ADMIT": "ADMITTED", "LAUNCH": "STARTING", "START": "RUNNING", "ACCEPT": "COMPLETE",
                         "REJECT": "REPAIR_REQUIRED", "INTERRUPT": "REPAIR_REQUIRED",
                         "RECORD": "RESULT_RECORDED"}.get(kind, "INVALIDATED")
                if kind == "ACCEPT":
                    try:
                        old = read(self.path(event["attempt"]) / "admission.json")
                        if not self.retained_evidence_valid(event):
                            state, reason = "REPAIR_REQUIRED", "Accepted evidence was corrupted; unchanged retry refused"
                        elif old["binding"] != self.binding(evidence_task) or old["task_sha256"] != digest(evidence_task):
                            state, reason = "READY", "Completed evidence is stale after changed method/input; historical result retained"
                    except (OSError, ValueError, KeyError):
                        state, reason = "REPAIR_REQUIRED", "Accepted evidence is missing or invalid"
                if kind in {"REJECT", "INTERRUPT"}:
                    old = read(self.path(event["attempt"]) / "admission.json")
                    if old["binding"] != self.binding(task) or old["task_sha256"] != digest(task):
                        state, reason = "READY", "Changed method/input after retained failed attempt"
                if kind == "RECORD":
                    try:
                        old = read(self.path(event["attempt"]) / "admission.json")
                        if not self.retained_evidence_valid(event):
                            state, reason = "REPAIR_REQUIRED", "Recorded partial evidence was corrupted; unchanged retry refused"
                        elif old["task_sha256"] != digest(task):
                            state, reason = "READY", "Reviewed task refinement continues retained partial work under its original budget"
                        else:
                            reason = "Partial work retained; acceptance or continuation requires a reviewed task refinement"
                    except (OSError, ValueError, KeyError):
                        state, reason = "REPAIR_REQUIRED", "Recorded partial evidence is missing or invalid"
                if kind in {"ADMIT", "LAUNCH", "START"}:
                    old = read(self.path(event["attempt"]) / "admission.json")
                    try:
                        unchanged = old["binding"] == self.binding(task) and old["task_sha256"] == digest(task)
                    except OSError:
                        unchanged = False
                    if not unchanged:
                        state, reason = "INVALIDATED", "Active task method/input changed"
            if task["handler"] == "external" and state == "READY" and not self.external_evidence_ready(task):
                state, reason = "WAITING_EXTERNAL", task["external_input"]
            if any(rows[d]["state"] != "COMPLETE" for d in task["depends_on"]):
                state, reason = "WAITING_DEPENDENCY", "Required substantive predecessor is incomplete"
            trigger = task.get("repair_of")
            if trigger and latest.get(trigger, {}).get("kind") not in {"REJECT", "INTERRUPT"}:
                state, reason = "WAITING_TRIGGER", "Repair requires its named failed attempt"
            if state == "READY" and spent[task["budget_key"]] >= program["budgets"][task["budget_key"]]["maximum_new_attempts"]:
                state, reason = "BUDGET_EXHAUSTED", "Original obligation admission bound reached"
            rows[key] = {"id": key, "title": task["title"], "handler": task["handler"],
                         "state": state, "reason": reason,
                         "attempt": event.get("attempt") if event else None,
                         "satisfied_by": evidence_task["id"] if state == "COMPLETE" else None}
        completed = {key for key, row in rows.items() if row["state"] == "COMPLETE"}
        obligations = [{"id": row["id"], "scope": row["scope"],
                        "complete": bool(row["tasks"]) and set(row["tasks"]) <= completed,
                        "remaining_tasks": [t for t in row["tasks"] if t not in completed]}
                       for row in program["obligations"]]
        current_tasks = set(program.get("build_contract", {}).get("required_tasks", tasks))
        available = [r for r in rows.values() if r["state"] in {"READY", "ADMITTED"}
                     and r["id"] in current_tasks]
        available.sort(key=lambda r: (r["state"] != "ADMITTED", tasks[r["id"]].get("priority", 100), r["id"]))
        active = [rows[key] for key, event in latest.items() if event["kind"] in {"LAUNCH", "START"}]
        decisions = {scope: all(t["id"] in completed for t in tasks.values() if t["stream"] == scope)
                     and any(t["stream"] == scope for t in tasks.values())
                     for scope in ("engineering", "assisted", "automatic", "package_evaluation")}
        from .build_contract import project
        from .criterion_evidence import conditional as current_conditional
        conditional = current_conditional(self, program, tasks, events, latest)
        return {"version": "prospectus-authority-state.v1", "revision": program["revision"],
                "program_sha256": digest(program), "event_head": events[-1]["sha256"],
                "tasks": list(rows.values()), "obligations": obligations, "budget_admissions": spent,
                "next_task": available[0]["id"] if available and not active else None,
                "running": [r["id"] for r in active], "completion": decisions,
                "current_build": project(program, completed, conditional),
                "program_complete": bool(obligations) and all(r["complete"] for r in obligations)}

    def refresh_locked(self):
        state = self.status()
        previous = read(self.base / "state.json") if (self.base / "state.json").exists() else None
        selection = lambda s: (s["next_task"], [(r["id"], r["state"], r["reason"]) for r in s["tasks"]])
        if previous is None or selection(previous) != selection(state):
            self.append("REFRESH", next_task=state["next_task"], running=state["running"],
                        reason=next((r["reason"] for r in state["tasks"] if r["id"] == state["next_task"]),
                                    "No ready task; inspect retained running, external and repair states"))
            state = self.status()
        if previous != state:
            write(self.base / "state.json", state)
        next_row = next((r for r in state["tasks"] if r["id"] == state["next_task"]), None)
        text = ("# Prospectus execution status\n\nGenerated from reviewed program revision "
                + str(state["revision"]) + "; program SHA-256 `" + state["program_sha256"] + "`.\n\n"
                + "Whole-program complete: **" + str(state["program_complete"]) + "**.\n\n"
                + ("Current general build complete: **" + str(state['current_build']['complete'])
                   + "**. Deferred historical tasks are not accepted.\n\n"
                   if state.get('current_build') else "")
                + ("Next task: **" + next_row["id"] + "** — " + next_row["title"] + ".\n\n"
                   + next_row["reason"] + "\n\n" if next_row else "No new task is dispatchable; inspect running/waiting states.\n\n")
                + "| Task | State | Reason |\n| --- | --- | --- |\n"
                + "".join(f'| {r["id"]} | {r["state"]} | {r["reason"].replace(chr(10), " ").replace("|", "/")} |\n' for r in state["tasks"]))
        for name in ("STATUS.md", "RESET.md", "NEXT-PROGRAM.md"):
            path = self.base / name
            if not path.exists() or path.read_text() != text:
                path.write_text(text)
        return state

    def refresh(self):
        with self.lock():
            return self.refresh_locked()

    def admit_locked(self, task_id=None):
        state = self.status()
        task_id = task_id or state["next_task"]
        if not task_id or task_id != state["next_task"]:
            raise ValueError("Task is not the next admitted/ready task")
        row = next(r for r in state["tasks"] if r["id"] == task_id)
        if row["state"] == "ADMITTED":
            path = self.path(row["attempt"]) / "admission.json"
            event = next(e for e in reversed(self.events()) if e.get("task") == task_id and e["kind"] == "ADMIT")
            if file_hash(path) != event["admission_sha256"]:
                raise ValueError("Admission changed after freeze")
            return read(path)
        program, tasks, _ = self.spec()
        task = tasks[task_id]
        events = self.events()
        n = 1 + sum(e["kind"] == "ADMIT" and e["task"] == task_id for e in events)
        attempt = self.base / "attempts" / task_id / f"attempt-{n:03d}"
        attempt.mkdir(parents=True, exist_ok=False)
        admission = {"task": task_id, "task_sha256": digest(task), "task_spec": task,
                     "program_sha256": digest(program), "revision": program["revision"],
                     "binding": self.binding(task), "attempt": str(attempt.relative_to(self.root)),
                     "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip(),
                     "cpu_gpu": "CPU only; GPU intentionally hidden for workers", "random_seeds": "N/A; deterministic local evidence",
                     "plan": program["plan"], "reason": row["reason"]}
        write(attempt / "admission.json", admission, exclusive=True)
        self.append("ADMIT", task=task_id, attempt=admission["attempt"],
                    budget_key=task["budget_key"], program_sha256=digest(program),
                    admission_sha256=file_hash(attempt / "admission.json"), reason=row["reason"])
        self.refresh_locked()
        return admission

    def admit(self, task_id=None):
        with self.lock():
            return self.admit_locked(task_id)

    def run(self, task_id=None):
        with self.lock():
            admission = self.admit_locked(task_id)
            task = admission["task_spec"]
            if task["handler"] in {"agent", "external"}:
                return {"execution": "AGENT_WORK_REQUIRED", **admission}
            attempt = self.path(admission["attempt"])
            argv = [str(self.root / ".venv/bin/python"), "-m", "scripts.prospectus_control",
                    "worker", "--attempt", admission["attempt"]]
            self.append("LAUNCH", task=task["id"], attempt=admission["attempt"], argv=argv)
            lease = (attempt / "worker.lock").open("a")
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            argv += ["--lease-fd", str(lease.fileno())]
            try:
                with (attempt / "execution.log").open("xb") as log:
                    child = subprocess.Popen(argv, cwd=self.root, stdin=subprocess.DEVNULL,
                                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                             pass_fds=(lease.fileno(),),
                                             env={**os.environ, "PYTHONPATH": str(self.root / "src"),
                                                  "CUDA_VISIBLE_DEVICES": "-1", "OMP_THREAD_LIMIT": "1"})
            except OSError as error:
                self.append("INTERRUPT", task=task["id"], attempt=admission["attempt"], reason=str(error))
                self.refresh_locked()
                raise
            finally:
                lease.close()
            self.worker_process = child
            identity = process_identity(child.pid)
            if identity is None:
                raise ValueError("Worker did not retain process identity")
            job = {"identity": identity, "argv": argv, "attempt": admission["attempt"],
                   "timeout_seconds": task["timeout_seconds"], "started_epoch": time.time()}
            write(attempt / "job.json", job, exclusive=True)
            self.append("START", task=task["id"], attempt=admission["attempt"], identity=identity)
            self.refresh_locked()
            return {"execution": "RUNNING", "task": task["id"], "attempt": admission["attempt"], "pid": child.pid}

    def wait_worker(self):
        """Keep the tool process/session alive; status calls remain independent."""
        child = self.worker_process
        try:
            child.wait(timeout=7300)
        except subprocess.TimeoutExpired:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        return self.resume()

    def worker_alive(self, attempt, identity):
        lease_path = attempt / "worker.lock"
        if lease_path.exists():
            with lease_path.open("a") as stream:
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    return True
        return bool(identity and process_identity(identity["pid"]) == identity)

    def record_locked(self, attempt_name):
        program, tasks, _ = self.spec()
        attempt = self.path(attempt_name)
        if not attempt.is_relative_to(self.base / "attempts"):
            raise ValueError("Only admitted attempt evidence can be recorded")
        admission = read(attempt / "admission.json")
        task = tasks[admission["task"]]
        events = [e for e in self.events() if e.get("task") == task["id"]]
        if not events or events[-1]["attempt"] != attempt_name:
            raise ValueError("Attempt is not active")
        if events[-1]["kind"] in {"ACCEPT", "REJECT", "INTERRUPT", "RECORD"}:
            return self.refresh_locked()
        build_acceptances = []
        build_evidence = {}
        try:
            admitted = next(e for e in self.events() if e.get("attempt") == attempt_name and e["kind"] == "ADMIT")
            if file_hash(attempt / "admission.json") != admitted["admission_sha256"]:
                raise ValueError("Admission changed after freeze")
            if admission["program_sha256"] != digest(program):
                raise ValueError("Program specification changed during task")
            if admission["binding"] != self.binding(task) or admission["task_sha256"] != digest(task):
                raise ValueError("Method/input changed during task")
            candidate = {"attempt": attempt_name, "outputs_sha256": file_hash(attempt / "outputs.json")}
            if not self.attempt_valid(candidate, task):
                raise ValueError("Output evidence changed")
            from .execution_workers import validate
            disposition = validate(self.root, attempt, task)
            from .build_contract import validate_submission
            build_acceptances = validate_submission(self.root, attempt, task, program)
            from .criterion_evidence import issue
            build_evidence = issue(self, admission, task, program, build_acceptances)
            kind, reason = ("ACCEPT", "Required evidence independently validated") if disposition else (
                "RECORD", "Work retained; task-specific substantive validator/review still required")
        except (ValueError, OSError, KeyError, TypeError) as error:
            kind, reason = "REJECT", str(error)
        fields = {"task": task["id"], "attempt": attempt_name, "reason": reason}
        if build_acceptances and kind in {'RECORD', 'ACCEPT'}:
            fields['build_acceptances'] = build_acceptances
            if build_evidence:
                fields['build_evidence'] = build_evidence
            fields['build_criteria_sha256'] = digest(program['build_contract']['criteria'][task['id']])
            if kind == 'RECORD':
                fields['reason'] = ('Conditional build criteria independently checked; '
                                    'original task acceptance remains incomplete')
        if (attempt / "outputs.json").exists():
            fields["outputs_sha256"] = file_hash(attempt / "outputs.json")
        self.append(kind, **fields)
        return self.refresh_locked()

    def record(self, attempt_name):
        with self.lock():
            return self.record_locked(attempt_name)

    def resume(self):
        with self.lock():
            events = self.events()
            revision = next(e for e in reversed(events) if e["kind"] == "REVISION")
            spec_file = self.base / "revisions" / f'{revision.get("revision", 1):04d}.json'
            specification = read(spec_file)
            if digest(specification) != revision["program_sha256"]:
                raise ValueError("Committed specification is corrupt")
            if read(self.base / "program.json") != specification:
                write(self.base / "program.json", specification)
            latest = {e["task"]: e for e in events if e.get("task")}
            for event in latest.values():
                if event["kind"] not in {"ADMIT", "LAUNCH", "START"}:
                    continue
                attempt = self.path(event["attempt"])
                if (attempt / "outputs.json").exists():
                    self.record_locked(event["attempt"])
                elif event["kind"] in {"LAUNCH", "START"}:
                    job = read(attempt / "job.json") if (attempt / "job.json").exists() else None
                    if not self.worker_alive(attempt, job["identity"] if job else None):
                        self.append("INTERRUPT", task=event["task"], attempt=event["attempt"],
                                    reason="Worker ended without complete retained evidence; unchanged retry refused")
                    elif event["kind"] == "LAUNCH" and job:
                        self.append("START", task=event["task"], attempt=event["attempt"], identity=job["identity"])
            return self.refresh_locked()

    def revise(self, proposal_name, review_name):
        with self.lock():
            old, _, _ = self.spec()
            new = read(self.path(proposal_name))
            review = read(self.path(review_name))
            required_review = {"baseline", "changes", "skeptical_audit", "evidence_contract", "scope_unchanged", "budget_unchanged"}
            if not required_review <= review.keys() or not all(review[k] for k in required_review - {"budget_unchanged"}):
                raise ValueError("Revision lacks substantive reviewed justification")
            if review["baseline"] != digest(old) or new["revision"] != old["revision"] + 1:
                raise ValueError("Revision uses the wrong active baseline")
            if new["inventory_sha256"] != old["inventory_sha256"]:
                raise ValueError("Scope/budget change requires separately authorized migration; ordinary revision cannot reset limits")
            from .build_contract import check_revision
            check_revision(old, new, review)
            if new["budgets"] != old["budgets"]:
                extension = review.get("budget_revision", {})
                required = {"budget_key", "previous_maximum", "new_maximum", "retained_attempts", "reason",
                            "next_discriminating_check", "stop_condition", "same_scope_authorization"}
                if not required <= extension.keys() or not all(extension[k] for k in required):
                    raise ValueError("Scope/budget extension requires an explicit cumulative review")
                key = extension["budget_key"]
                altered = [k for k in set(new["budgets"]) | set(old["budgets"]) if new["budgets"].get(k) != old["budgets"].get(k)]
                attempts = [e["attempt"] for e in self.events() if e["kind"] == "ADMIT" and e["budget_key"] == key]
                if altered != [key] or key not in old["budgets"] or extension["retained_attempts"] != attempts:
                    raise ValueError("Budget extension must retain the complete original admission history")
                before, after = old["budgets"][key]["maximum_new_attempts"], new["budgets"][key]["maximum_new_attempts"]
                if before != extension["previous_maximum"] or after != extension["new_maximum"] or after != before + 1:
                    raise ValueError("Only one explicitly reviewed additional admission is supported")
                if review["budget_unchanged"]:
                    raise ValueError("Review incorrectly claims an unchanged budget")
            old_tasks = {r["id"]: r for r in old["tasks"]}
            for task in new["tasks"]:
                ancestor = old_tasks.get(task["id"]) or old_tasks.get(task.get("repair_of"))
                if ancestor is None or task["budget_key"] != ancestor["budget_key"]:
                    raise ValueError("A new repair must inherit its named original task budget")
                if ancestor["handler"] == "external" and task["handler"] != "external":
                    raise ValueError("Human/source external acceptance cannot become an automatic task")
                if task["stream"] != ancestor["stream"]:
                    raise ValueError("Ordinary revision cannot reclassify acceptance scope")
            old_obligations = {r["id"]: r for r in old["obligations"]}
            for row in new["obligations"]:
                prior = old_obligations[row["id"]]
                if not set(prior["tasks"]) <= set(row["tasks"]) or row["budget_keys"] != prior["budget_keys"]:
                    raise ValueError("Revision cannot remove obligations or reset task lineage")
            self.validate_program(new)
            target = self.base / "revisions" / f'{new["revision"]:04d}.json'
            write(target, new, exclusive=True)
            self.append("REVISION", revision=new["revision"], program_sha256=digest(new),
                        review=review_name, review_sha256=file_hash(self.path(review_name)))
            write(self.base / "program.json", new)
            return self.refresh_locked()

    def worker(self, attempt_name, lease_fd=None):
        attempt = self.path(attempt_name)
        if lease_fd is None or os.fstat(lease_fd).st_ino != (attempt / "worker.lock").stat().st_ino:
            raise ValueError("Worker must inherit its registered attempt lease")
        with self.lock(blocking=True):
            admission = read(attempt / "admission.json")
            event = next(e for e in reversed(self.events()) if e.get("task") == admission["task"])
            if event["kind"] == "LAUNCH" and event["attempt"] == attempt_name:
                identity = process_identity(os.getpid())
                job = {"identity": identity, "argv": event["argv"], "attempt": attempt_name,
                       "timeout_seconds": admission["task_spec"]["timeout_seconds"], "started_epoch": time.time()}
                if not (attempt / "job.json").exists():
                    write(attempt / "job.json", job, exclusive=True)
                self.append("START", task=admission["task"], attempt=attempt_name, identity=identity)
                event = self.events()[-1]
            if event["kind"] != "START" or event["attempt"] != attempt_name:
                raise ValueError("Worker lacks active admission")
            admitted = next(e for e in self.events() if e["kind"] == "ADMIT" and e.get("attempt") == attempt_name)
            if file_hash(attempt / "admission.json") != admitted["admission_sha256"]:
                raise ValueError("Worker admission changed")
            if read(attempt / "job.json")["identity"] != process_identity(os.getpid()):
                raise ValueError("Worker process differs from registered job")
        started = time.monotonic()
        task = admission["task_spec"]
        stopped = threading.Event()
        def heartbeat():
            while True:
                write(attempt / "heartbeat.json", {"identity": process_identity(os.getpid()),
                      "task": task["id"], "elapsed_seconds": time.monotonic() - started})
                if stopped.wait(10):
                    return
        beat = threading.Thread(target=heartbeat, daemon=True)
        beat.start()
        def timed_out(signum, frame):
            raise TimeoutError("Reviewed worker time limit reached")
        signal.signal(signal.SIGALRM, timed_out)
        signal.alarm(task["timeout_seconds"])
        try:
            from .execution_workers import execute
            execute(self.root, attempt, task)
            result = {"status": "PASS"}
        except Exception as error:
            result = {"status": "FAIL", "error": type(error).__name__ + ": " + str(error)}
        finally:
            signal.alarm(0)
            stopped.set()
            beat.join(timeout=1)
        result.update(wall_seconds=time.monotonic() - started, task=task["id"])
        write(attempt / "result.json", result, exclusive=True)
        manifest = {str(p.relative_to(attempt)): file_hash(p) for p in sorted(attempt.rglob("*"))
                    if p.is_file() and p.name not in {"execution.log", "outputs.json", "heartbeat.json", "worker.lock"}
                    and not p.name.endswith((".new", ".pending"))}
        write(attempt / "outputs.json", manifest, exclusive=True)
        return self.record(attempt_name)
