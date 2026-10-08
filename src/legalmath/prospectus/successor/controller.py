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

REL = "docs/implementation/prospectus-repair-2026-10-06"
DAG = {"P0": [], "P1": ["P0"], "P2": ["P1"], "P3": ["P1", "P2"], "P4": ["P1", "P3"],
       "P5": ["P1", "P2", "P3"], "P6": ["P1", "P2", "P3", "P4", "P5"], "P7": ["P0", "P6"], "P8": ["P6", "P7"]}
PROGRAM = "repair"
PLAN = "docs/plans/prospectus-phase-repair-execution-2026-10-06.md"
REPAIR_DAG = DAG.copy()


def configure(program):
    """Select a namespace in this controller; historical attempts stay immutable."""
    global REL, DAG, PROGRAM, PLAN
    if program not in {"repair", "adoption"}:
        raise ValueError("Unknown phase program")
    PROGRAM = program
    REL = "docs/implementation/prospectus-" + ("adoption" if program == "adoption" else "repair-2026-10-06")
    DAG = ({"A0": [], "A1": ["A0"], "A2": ["A0", "A1"], "A3": ["A0"], "A4": ["A0"],
            "A5": ["A0", "A1", "A2", "A3", "A4"], "A6": ["A0", "A1", "A2", "A3", "A4", "A5"]}
           if program == "adoption" else REPAIR_DAG.copy())
    PLAN = "docs/plans/prospectus-" + ("adoption-execution-2026-10-07.md" if program == "adoption" else "phase-repair-execution-2026-10-06.md")


def command(*arguments):
    return ["python3", "-m", "scripts.prospectus_delivery", "--program", PROGRAM, *arguments]


def handler(phase):
    if PROGRAM == "adoption":
        from . import adoption_jobs
        return getattr(adoption_jobs, phase.lower(), None)
    from . import jobs
    return getattr(jobs, phase.lower(), None)


def publish_products(root, folder):
    """Content addressed copies make published products verifiable after a crash."""
    path=folder/"product.json"
    if not path.exists():
        return {}
    raw=path.read_bytes();sha=digest(raw);target=root/REL/"blobs"/(sha+".json")
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if target.read_bytes()!=raw:
            raise ValueError("Corrupted content addressed product")
    else:
        temporary=target.with_suffix(".tmp")
        with temporary.open("wb") as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,target)
        descriptor=os.open(target.parent,os.O_RDONLY | os.O_DIRECTORY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)
    return {str(target.relative_to(root)):sha}


def bindings(root, phase=None):
    """Conservative declared bindings; observed reads are recorded separately."""
    if phase is None:
        return {p: bindings(root, p) for p in DAG}
    if PROGRAM == "adoption":
        from .adoption_jobs import bindings as adoption_bindings
        return adoption_bindings(root, phase)
    paths = list((root / "src/legalmath/prospectus/successor").glob("*.py"))
    paths += [root / "scripts/prospectus_delivery.py", root / "pyproject.toml"]
    paths += list((root / REL / "inputs" / phase).glob("*.json"))
    if phase in {"P3", "P4", "P5", "P6", "P7"}:
        paths += list((root / "tests/prospectus_successor").glob("*.py"))
        # Imported engines and packaged specification resources, not just wrappers.
        paths += [p for p in (root / "src/legalmath").rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    packet = root / "docs/implementation/prospectus-basf-continuation-2026-10-05/phases/012-construct/basf-selection-admission.json"
    if phase in {"P0", "P1", "P2"}:
        paths.append(packet)
        for row in read(packet)["sources"].values():
            paths += [root / row[k] for k in ("original", "text", "acquisition_receipt")]
    if phase in {"P0", "P4", "P5"}:
        for name in ("docs/prospectus/legal/manifest.json", "docs/prospectus/corner-cases/manifest.json"):
            manifest = root / name
            if manifest.exists():
                paths.append(manifest)
                # Every retained manifest referenced path is included recursively.
                def references(value):
                    if isinstance(value, dict):
                        for k,v in value.items():
                            if isinstance(v, str) and k in {"path", "text_path", "original", "text"} and (root/v).is_file():
                                paths.append(root/v)
                            else:
                                references(v)
                    elif isinstance(value, list):
                        for v in value:
                            references(v)
                references(read(manifest))
        from .jobs import LEGAL, INVENTORY, GROUPS, FORMS
        if phase == "P0":
            paths.append(root / GROUPS)
            paths += list((root/FORMS).glob("*.json"))
        if phase == "P4":
            paths += [root/LEGAL/"rule-scenarios.json", root/LEGAL/"source-registry.json"]
            for row in read(root/LEGAL/"source-registry.json").values():
                paths += [root/row[k] for k in ("original", "text") if row.get(k)]
        if phase == "P5":
            paths += [root/INVENTORY, root/"docs/prospectus/evidence-closure/scenarios.json"]
            from ..closure_mechanisms import PROFILES
            for profile in PROFILES.values():
                row=read(root/INVENTORY)["documents"][profile["document"]]
                paths += [root/row[k] for k in ("original", "text")]
    # Admissions may name additional source files/stores. Bind them before dispatch.
    def admitted_paths(value):
        if isinstance(value, dict):
            for k,v in value.items():
                if isinstance(v,str) and k in {"path","store","admission_path"}:
                    from .contracts import bound_path
                    path=bound_path(root,v)
                    if path.is_dir():
                        paths.extend(p for p in path.rglob("*") if p.is_file())
                    elif path.is_file():
                        paths.append(path)
                else:
                    admitted_paths(v)
        elif isinstance(value,list):
            for v in value:
                admitted_paths(v)
    for path in (root/REL/"inputs"/phase).glob("*.json"):
        admitted_paths(read(path))
    if phase == "P6":
        old = root / "docs/implementation/prospectus-evidence-closure/phases/S3/attempt-004/bank"
        paths += [p for p in old.rglob("*") if p.is_file()]
    if phase == "P1":
        meta=root/"docs/prospectus/closure-2026-10-05/reviewed-extractions.json"
        paths.append(meta)
        for row in read(meta).values():
            paths += [root/row[k] for k in ("original", "raw", "text", "review", "language_model")]
        from .jobs import INVENTORY
        from ..closure_mechanisms import PROFILES
        paths.append(root/INVENTORY)
        for profile in PROFILES.values():
            row=read(root/INVENTORY)["documents"][profile["document"]]
            paths += [root/row[k] for k in ("original", "text")]
    result = {str(p.relative_to(root)): digest(p.read_bytes()) for p in sorted(set(paths))}
    import importlib.metadata
    result["environment"] = {"python": sys.version, "packages": sorted((d.metadata["Name"], d.version)
                                      for d in importlib.metadata.distributions() if d.metadata["Name"])}
    if phase in {"P1", "P6"}:
        tool = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True, check=True)
        result["pdftotext"] = tool.stdout + tool.stderr
    return result


def current(root, state):
    valid = {}
    for phase, deps in DAG.items():
        row = state.get(phase)
        valid[phase] = bool(row and row.get("method") == digest(bindings(root, phase)) and row.get("artifact_ready")
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
        if valid[phase]:
            from .read_context import current as reads_current
            observed = root / row["directory"] / "read-context.json"
            if observed.exists() and not reads_current(root, read(observed)):
                valid[phase] = False
        if valid[phase]:
            for relative, expected in row.get("blobs",{}).items():
                path=root/relative
                if not path.is_file() or digest(path.read_bytes())!=expected:
                    valid[phase]=False
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
            "command": command("phase", "--phase", phase),
            "invalidation_set": [p for p in DAG if phase in ancestors(p)],
            "limits": {"attempts_per_identical_input": 3, "changed_inputs": "new bounded attempt group", "timeout_seconds": 1800}})
        if PROGRAM == "adoption":
            from .adoption_jobs import phase_plan
            rows[-1]["reviewed_next_plan"] = phase_plan(phase, state)
    repairs = []
    for phase in DAG:
        for diagnostic in state.get(phase, {}).get("remaining", []):
            implementation = any(term in diagnostic.lower() for term in (
                "bracket", "renumber", "incorporated", "construct remaining", "grammar", "rounding", "row/column", "margin"))
            if PROGRAM == "adoption":
                implementation = phase not in {"A4", "A6"} or "Full settlement" in diagnostic
            repairs.append({"id":phase+":"+digest(diagnostic)[:12], "target_phase":phase,
                "diagnostic":diagnostic, "input_identity":state.get(phase,{}).get("input_identity"),
                "kind":"IMPLEMENTATION_AND_SOURCE_REVIEW" if implementation else "EVIDENCE_ADMISSION",
                "handler":None if implementation else "admit_record",
                "acceptance_check":"Rerun target and re-evaluate this obligation against its source and regression",
                "command":None if implementation else command("repair","--record","<reviewed-record.json>"),
                "required_code_or_source_change":diagnostic if implementation else None,
                "required_external_record":None if implementation else diagnostic,
                "attempt":state.get(phase,{}).get("attempt",0), "outcome":"OPEN; unchanged input is not a repair"})
    result = {"program": PROGRAM, "phases": rows, "repair_obligations": repairs, "automatic_release": False,
              "next_dispatch": next((r["command"] for r in rows if not r["current"] and r["can_dispatch"]), None),
              "refresh_review": "Partial evidence permits independent phases; failed artifacts block dependent phases. Criteria unchanged."}
    write(root / REL / "repair-worklist.json", repairs)
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
        return _refresh(root, recover(root))


def recover(root):
    """A complete receipt is the commit point; a pointer update can be replayed."""
    state = {}
    for phase in DAG:
        for folder in sorted((root / REL / "phases" / phase).glob("attempt-*")):
            path = folder / "receipt.json"
            if not path.exists():
                continue
            try:
                receipt = read(path)
                if not all((folder/p).is_file() and digest((folder/p).read_bytes()) == sha for p,sha in receipt["outputs"].items()):
                    continue
                row = receipt["state"]
                state[phase] = {**row, "directory": str(folder.relative_to(root)), "receipt_sha256": digest(path.read_bytes())}
            except (KeyError, ValueError, OSError):
                continue
    write(root / REL / "state.json", state)
    return state


def admit_record(root, record):
    """Ingest a changed, reviewable input; no script/eval execution is accepted."""
    from .anchors import fields
    fields(record, {"obligation_id", "phase", "name", "before_sha256", "content", "reason"},
           {"obligation_id", "phase", "name", "before_sha256", "content", "reason"})
    phase, name = record["phase"], record["name"]
    allowed = {"P0": {"review.json"}, "P1": {"request.json"}, "P2": {"assembly.json"},
               "P3": {"interpretation.json"}, "P4": {"cases.json", "law.json"}, "P5": {"scenarios.json", "scenario.json"},
               "P6": {"bank.json"}, "P7": {"labels.json", "predictions.json"}, "P8": {"support.json", "signoffs.json"}}
    if PROGRAM == "adoption":
        # Only advertise admissions actually consumed by registered jobs.
        # A0–A3/A5 repairs currently change reviewed source/code, not inert files.
        allowed = {"A4": {"coupon.json"}, "A6": {"review.json", "facts.json"}}
    if name not in allowed.get(phase, set()) or not record["reason"]:
        raise ValueError("Unknown phase admission or missing repair reason")
    out = root / REL
    out.mkdir(parents=True, exist_ok=True)
    with (out / "controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        target = out / "inputs" / phase / name
        prior = digest(target.read_bytes()) if target.exists() else None
        if prior != record["before_sha256"] or (target.exists() and read(target) == record["content"]):
            raise ValueError("Stale or unchanged admission is not a repair")
        write(target, record["content"])
        receipt = {**record, "after_sha256": digest(target.read_bytes()), "outcome": "ADMITTED; REEXECUTION_REQUIRED"}
        write(out / "repairs" / (digest(receipt) + ".json"), receipt)
        _refresh(root, recover(root))
        return receipt


def execute(root, phase):
    root = Path(root)
    out = root / REL
    out.mkdir(parents=True, exist_ok=True)
    with (out / "controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = recover(root)
        fn = handler(phase)
        if not callable(fn):
            return {"phase": phase, "execution": "NOT_IMPLEMENTED"}
        valid = current(root, state)
        if valid[phase]:
            return {"phase": phase, "execution": "REUSED", "engineering": state[phase]["engineering"],
                    "remaining": state[phase]["remaining"], "release": "NOT_ACCEPTED"}
        if not all(valid[d] for d in DAG[phase]):
            _refresh(root, state)
            return {"phase": phase, "execution": "DEPENDENCY_NOT_CURRENT"}
        method_bindings = bindings(root, phase)
        method = digest(method_bindings)
        dependencies = {d: state[d]["receipt_sha256"] for d in DAG[phase]}
        identity = digest({"method": method, "dependencies": dependencies})
        parent = out / "phases" / phase
        parent.mkdir(parents=True, exist_ok=True)
        attempts = sorted(parent.glob("attempt-*"))
        existing = [read(p / "started.json") for p in attempts if (p / "started.json").exists()]
        same = sum(r["input_identity"] == identity for r in existing)
        if same >= 3:
            return {"phase": phase, "execution": "REPAIR_REQUIRED", "reason": "Bounded attempt/repair cap"}
        folder = parent / f"attempt-{len(attempts)+1:03d}"
        folder.mkdir()
        if PROGRAM == "adoption":
            from .adoption_jobs import phase_plan
            write(folder / "plan.json", phase_plan(phase, state))
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
            from .read_context import ReadContext, current as reads_current
            context = ReadContext(root, out / "snapshots")
            if "context" in inspect.signature(fn).parameters:
                result = fn(root, folder, state, context=context)
            else:
                result = fn(root, folder, state)
            write(folder / "read-context.json", context.manifest())
            if not reads_current(root, context.manifest()):
                raise ValueError("Observed input changed during execution")
            parents_current = current(root, state)
            if bindings(root, phase) != method_bindings or not all(parents_current[d] for d in DAG[phase]):
                raise ValueError("Input changed during execution; receipt cannot be published as current")
            if not isinstance(result, dict) or "engineering" not in result or "remaining" not in result:
                raise ValueError("Phase omitted acceptance disposition")
            result = {**result, "execution": "EXECUTED", "release": "NOT_ACCEPTED"}
        except Exception as exc:
            import traceback
            write(folder / "failure.json", {"error": str(exc), "traceback": traceback.format_exc()})
            result = {"execution": "FAILED", "engineering": "REPAIR_REQUIRED", "evidence": "PENDING",
                      "artifact_ready": False, "remaining": [str(exc)]}
            if "context" in locals():
                write(folder / "read-context.json", context.manifest())
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_alarm)
        write(folder / "result.json", result)
        manifest = {"phase": phase, "command": command("phase", "--phase", phase),
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "environment": sys.executable, "python": sys.version, "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1",
            "random_seeds": "N/A deterministic engineering", "wall_seconds": time.monotonic()-started,
            "plan": PLAN,
            "result_file": str((folder / "result.json").relative_to(root)), "input_bindings": method_bindings,
            "dependencies": dependencies, "data_version": identity}
        write(folder / "manifest.json", manifest)
        (folder / "RESULT.md").write_text("# " + phase + " execution\n\n" + result["engineering"] + "\n\n"
            + "Release: NOT_ACCEPTED.\n\n" + "\n".join("- " + r for r in result["remaining"]) + "\n\n"
            + "See result.json and manifest.json for criteria, commands and preserved evidence.\n")
        outputs = {str(p.relative_to(folder)): digest(p.read_bytes()) for p in sorted(folder.rglob("*"))
                   if p.is_file() and p.name != "receipt.json"}
        blobs=publish_products(root,folder) if result.get("artifact_ready") else {}
        record = {**result, "method": method, "dependencies": dependencies, "input_identity": identity, "attempt": same + 1, "blobs":blobs}
        write(folder / "receipt.json", {"outputs": outputs, "result": result, "input_identity": identity, "state": record})
        state[phase] = {**record,
            "directory": str(folder.relative_to(root)), "receipt_sha256": digest((folder / "receipt.json").read_bytes())}
        write(out / "state.json", state)
        _refresh(root, state)
        return {"phase": phase, **result, "directory": state[phase]["directory"]}
