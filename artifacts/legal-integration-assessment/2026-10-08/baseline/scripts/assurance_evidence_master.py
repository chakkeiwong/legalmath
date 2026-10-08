#!/usr/bin/env python3
"""Fixed-path, restartable evidence master. Model/source text cannot select commands."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

CODE = Path(__file__).resolve().parents[1]
ROOT = Path("/home/chakwong/python/legalmath")
sys.path[:0] = [str(CODE/"src"), str(CODE/"scripts")]
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from legalmath.canonical import canonical, digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import supplemental_repair as codec
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import CodexProvider
from legalmath.interpretation.search.schema import validate_output_schema
import assurance_evidence_core as c
import assurance_evidence_sources as sources
import assurance_evidence_phases as phases

ALLOWLIST = Path("docs/implementation/assurance-evidence-master/allowlist.json")
PHASES = phases.PHASES
TERMINAL = {"COMPLETED", "COMPLETED_WITH_OPEN_EVIDENCE"}
TESTS = ["tests/assurance/test_assurance_evidence_master.py",
         "tests/assurance/test_supplemental_repair.py", "tests/assurance/test_challenge_contract.py",
         "tests/assurance/test_readable_challenges.py", "tests/assurance/test_official_archive.py"]

def output(value):
    print(json.dumps(value, sort_keys=True), flush=True)

def files_in(directory, root, exclude=()):
    return [c.receipt(p, root) for p in sorted(directory.rglob("*"))
            if p.is_file() and p.name not in exclude and ".tmp." not in p.name and "__pycache__" not in p.parts]

def check_command(policy, argv):
    if argv not in policy["commands"]:
        c.fail("E_AUTHORITY", "Master command does not exactly match reviewed allowlist")
    if policy["requested_prefix"] != [".venv/bin/python", "scripts/assurance_evidence_master.py"]:
        c.fail("E_AUTHORITY", "Unexpected approval prefix")
    return True

def predecessors(root):
    names = ["final-result.json", "context.json", "authority-context.json", "remaining-obligations.json",
             "formal-evidence.json", "followup-premise-checks.json", "assessment-evidence.json",
             "allowance.json", "authorization.json"]
    refs = [c.receipt(root/c.OLD/n, root) for n in names]
    refs.append(c.receipt(root/c.BASE/"additional-100-call-authorization.json", root))
    # Historical grants remain byte-identical, including their prior reservations.
    for name in ("artifacts/assurance-new-grant/2026-09-29/live-allowance.json",
                 "artifacts/assurance-new-grant/2026-09-29/gap-closure-allowance.json"):
        p = root/name
        if p.exists():
            refs.append(c.receipt(p, root))
    return refs

def prepare(root):
    base = root/c.BASE
    manifest_path = base/"master-manifest.json"
    if manifest_path.exists():
        verify_manifest(root)
        return c.read(manifest_path)
    policy = c.read(root/ALLOWLIST)
    check_command(policy, [".venv/bin/python", "scripts/assurance_evidence_master.py", "run"])
    auth = {"profile": c.PROFILE, "authorization_id": "user.2026-10-02.assurance-evidence-closure",
        "authorization": "100 more calls; create, review and execute the master with bounded repairs and refreshed next-phase plans.",
        "maximum": 100, "window_hours": 48, "maximum_attempts_per_issue": 2,
        "phase_limits": c.LIMITS, "repair_reserve": 16, "allowed_issues": phases.issue_registry(root),
        "predecessors": predecessors(root), "legal_correctness": "NOT_ESTABLISHED"}
    if (base/"authorization.json").exists() and c.read(base/"authorization.json") != auth:
        c.fail("E_INTEGRITY", "Existing authorization differs; no silent reset")
    c.save(base/"authorization.json", auth)
    hashes = c.code_material(root)
    frozen = base/"frozen"
    for name, sha in hashes.items():
        target = frozen/name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and raw_digest(target.read_bytes()) != sha:
            c.fail("E_INTEGRITY", "Partial snapshot changed; inspect before resuming")
        if not target.exists():
            shutil.copyfile(root/name, target)
    for name in ("pyproject.toml",):
        if (root/name).exists():
            shutil.copyfile(root/name, frozen/name)
            hashes[name] = raw_digest((root/name).read_bytes())
    tools = {}
    for name in (".venv/bin/python", ".localresources/java-toolchain/jdk-17.0.20.1+1/bin/java",
                 ".localresources/java-toolchain/jdk-17.0.20.1+1/bin/javac",
                 ".localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala",
                 "docs/implementation/catala/toolchain-lock.json"):
        if (root/name).exists():
            tools[name] = raw_digest((root/name).read_bytes())
    # Source extraction and review remain bound to retained publisher bytes.
    authority = c.read(root/c.OLD/"authority-context.json")
    source_refs = authority["source_receipts"]
    for ref in source_refs:
        c.checked(ref, root)
    manifest = {"profile": c.PROFILE, "created_at": c.now(), "authorization": c.receipt(base/"authorization.json", root),
        "predecessors": auth["predecessors"], "source_receipts": source_refs, "code_hashes": hashes,
        "tool_hashes": tools, "plan": c.receipt(root/c.PLAN, root),
        "allowlist": c.receipt(root/ALLOWLIST, root), "cpu_only": True,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "command": [".venv/bin/python", "scripts/assurance_evidence_master.py", "run"],
        "environment": str(root/".venv"), "seeds": "N/A: remote generation uncontrolled; local checks deterministic",
        "baseline_version": "2026-10-01 final-result.json", "frozen_root": str(frozen.relative_to(root)),
        "publication": False}
    c.save(manifest_path, manifest)
    c.EvidenceAllowance(root).verify()
    return manifest

def active_frozen(root):
    base = root/c.BASE
    active = base/"active-revision.json"
    if not active.exists():
        return base/"frozen"
    report = c.read(c.checked(c.read(active)["receipt"], root))
    if report["status"] != "REPAIR_VALIDATED" or report["test_exit_code"] != 0:
        c.fail("E_INTEGRITY", "Unvalidated engineering revision")
    c.checked(report["prior_manifest"], root)
    for ref in report["checks"]:
        c.checked(ref, root)
    directory = (root/report["frozen_root"]).resolve()
    if not directory.is_relative_to(base.resolve()):
        c.fail("E_INTEGRITY", "Revision outside fixed campaign")
    for name, sha in report["code_hashes"].items():
        if raw_digest((directory/name).read_bytes()) != sha:
            c.fail("E_INTEGRITY", "Repaired snapshot changed")
    return directory

def activate_repair(root):
    verify_manifest(root)
    base = root/c.BASE
    if not (base/"last-stop.json").exists():
        c.fail("E_REFERENCE", "Engineering repair requires a recorded execution failure")
    versions = base/"engineering-repairs"
    versions.mkdir(exist_ok=True)
    directory = versions/f"{len(list(versions.glob('revision-*')))+1:02}"
    directory = versions/("revision-"+directory.name)
    directory.mkdir(exist_ok=False)
    hashes = c.code_material(root)
    frozen = directory/"frozen"
    for name, sha in hashes.items():
        target = frozen/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root/name, target)
    shutil.copyfile(root/"pyproject.toml", frozen/"pyproject.toml")
    hashes["pyproject.toml"] = raw_digest((frozen/"pyproject.toml").read_bytes())
    argv = [str(root/".venv/bin/python"), "-m", "pytest", "-q", *TESTS]
    with (directory/"tests.log").open("w") as stream:
        process = subprocess.run(argv, cwd=frozen, env={**os.environ, "CUDA_VISIBLE_DEVICES": "-1",
            "PYTHONPATH": str(frozen/"src")+os.pathsep+str(frozen/"scripts"), "PYTHONDONTWRITEBYTECODE": "1"},
            stdout=stream, stderr=subprocess.STDOUT, timeout=300)
    checks = [c.receipt(directory/"tests.log", root)]
    # Preflight actual acquired-source packets in the new frozen interpreter.
    probe = ("from pathlib import Path; import assurance_evidence_core as c; "
             "import assurance_evidence_phases as p; import assurance_evidence_master as m; "
             "r=Path('/home/chakwong/python/legalmath'); "
             "a=c.read(r/c.BASE/'P0/authority-context.json'); "
             "v=c.read(r/c.BASE/'P1/source-acquisition.json')['public_requests']; "
             "print([(t['id'],m.preflight_task(t)[2]) for t in p.authority_tasks(r,a,v)+p.propagation_tasks(r,a,p.review_digest(m.all_task_rows(r)))])")
    with (directory/"actual-preflight.log").open("w") as stream:
        probe_result = subprocess.run([str(root/".venv/bin/python"), "-c", probe], cwd=frozen,
            env={**os.environ, "PYTHONPATH": str(frozen/"src")+os.pathsep+str(frozen/"scripts"),
                 "PYTHONDONTWRITEBYTECODE": "1", "CUDA_VISIBLE_DEVICES": "-1"},
            stdout=stream, stderr=subprocess.STDOUT, timeout=120)
    checks.append(c.receipt(directory/"actual-preflight.log", root))
    failure_source = c.checked(c.read(base/"current-stop.json")["receipt"], root) if (base/"current-stop.json").exists() else base/"last-stop.json"
    shutil.copyfile(failure_source, directory/"diagnosed-failure.json")
    report = {"status": "REPAIR_VALIDATED" if process.returncode == probe_result.returncode == 0 else "REPAIR_REJECTED",
        "created_at": c.now(), "test_exit_code": process.returncode, "probe_exit_code": probe_result.returncode,
        "prior_manifest": c.receipt(base/"master-manifest.json", root),
        "previous_revision": c.read(base/"active-revision.json") if (base/"active-revision.json").exists() else None,
        "failure": c.receipt(directory/"diagnosed-failure.json", root), "checks": checks, "test_argv": argv,
        "frozen_root": str(frozen.relative_to(root)), "code_hashes": hashes,
        "allowance_unchanged": c.EvidenceAllowance(root).verify(), "source_edits": False}
    c.save(directory/"repair-result.json", report)
    if report["status"] != "REPAIR_VALIDATED":
        c.fail("E_INTEGRITY", "Engineering revision failed executed tests/preflight")
    c.save(base/"active-revision.json", {"receipt": c.receipt(directory/"repair-result.json", root)})
    refresh(root, "Executed engineering repair tests passed; resume uses new immutable snapshot")
    return {"status": report["status"], "revision": str(directory.relative_to(root)),
            "calls_used": c.EvidenceAllowance(root).verify()["used"]}


def verify_manifest(root):
    base = root/c.BASE
    manifest = c.read(base/"master-manifest.json")
    for ref in [manifest["authorization"], manifest["plan"], manifest["allowlist"],
                *manifest["predecessors"], *manifest["source_receipts"]]:
        c.checked(ref, root)
    for name, sha in manifest["code_hashes"].items():
        if raw_digest((base/"frozen"/name).read_bytes()) != sha:
            c.fail("E_INTEGRITY", "Frozen code changed: "+name)
    for name, sha in manifest["tool_hashes"].items():
        if raw_digest((root/name).read_bytes()) != sha:
            c.fail("E_INTEGRITY", "Execution tool changed: "+name)
    active_frozen(root)
    return manifest

def schema_for(request):
    typ = codec.AssessmentResponse if request["kind"] == "formal_repair" else c.GroupedPropagationResponse if request["kind"] == "propagation_grouped" else c.PropagationResponse if request["kind"] == "propagation" else c.ReviewResponse
    schema = typ.model_json_schema()
    schema["properties"]["binding_hash"]["enum"] = [request["binding_hash"]]
    if request["kind"].startswith("propagation"):
        schema["properties"]["reading_updates"].update(minItems=len(request["selected"]), maxItems=len(request["selected"]))
        n = len(request["question_inventory"])
        if request["kind"] == "propagation":
            schema["properties"]["question_updates"].update(minItems=n, maxItems=n)
        schema["properties"]["obligation_updates"].update(minItems=len(request["obligations"]), maxItems=len(request["obligations"]))
    elif request["kind"] == "formal_repair":
        schema["properties"]["assessments"].update(minItems=len(request["selected"]), maxItems=len(request["selected"]))
        schema["properties"]["newly_proposed_readings"]["maxItems"] = 0
    else:
        schema["properties"]["findings"].update(minItems=len(request["questions"]), maxItems=len(request["questions"]))
    validate_output_schema(schema)
    return schema

def preflight_task(task):
    request = task["request"]
    c.verify_packet(request["source_packet"])
    schema = schema_for(request)
    wire = codec.encode(request)
    if codec.decode(wire, digest(request)) != request:
        c.fail("E_INTEGRITY", "Round trip changed request")
    size = len(canonical(wire))
    if size > 200000:
        c.fail("E_RESOURCE_LIMIT", f"Complete request has {size} bytes; no source truncation allowed")
    return wire, schema, size

def preflight(root):
    authority = c.read(root/c.OLD/"authority-context.json")
    tasks = (phases.authority_tasks(root, authority) + phases.dispute_tasks(root, authority)
             + phases.propagation_tasks(root, authority))
    rows = []
    for task in tasks:
        _, _, size = preflight_task(task)
        rows.append({"task": task["id"], "bytes": size})
    value = {"status": "PASS", "tasks": len(rows), "maximum_bytes": max(r["bytes"] for r in rows),
             "rows": rows, "provider_calls": 0}
    c.save(root/c.BASE/"preflight.json", value)
    return {k: v for k, v in value.items() if k != "rows"}

def verify_provider(root, reservation, wire, schema):
    folder = root/c.BASE/"provider-evidence"/f'{reservation["slot"]:04}-{reservation["request_hash"][:16]}'
    if not (folder/"manifest.json").exists():
        return None
    manifest = c.read(folder/"manifest.json")
    if manifest["allowance_slot"] != reservation["slot"] or manifest["request_hash"] != digest(wire):
        c.fail("E_INTEGRITY", "Detached provider manifest")
    for name, ref in manifest["files"].items():
        if Path(name).name != name or raw_digest((folder/name).read_bytes()) != ref["retained_sha256"]:
            c.fail("E_INTEGRITY", "Provider bytes changed")
    if c.read(folder/"request.json") != wire or c.read(folder/"schema.json") != schema:
        c.fail("E_INTEGRITY", "Model received another request/schema")
    events = folder/"events.jsonl"
    if events.exists():
        forbidden = {"command_execution", "mcp_tool_call", "web_search", "file_change"}
        for line in events.read_text().splitlines():
            if line.strip() and json.loads(line).get("item", {}).get("type") in forbidden:
                c.fail("E_AUTHORITY", "Provider attempted tool use")
    return folder

def reservations_for(root, task_id, wire_hash):
    ledger = c.EvidenceAllowance(root)._load()
    return [r for r in ledger["calls"] if r["task"] == task_id and r["request_hash"] == wire_hash]

def check_attempt(root, directory):
    row = c.read(directory/"result.json")
    receipt_path = directory/"receipt.json"
    if not receipt_path.exists():
        c.fail("E_INTEGRITY", "Attempt lacks completion receipt")
    for ref in c.read(receipt_path)["files"]:
        c.checked(ref, root)
    request, wire, schema = (c.read(directory/n) for n in ("request.json", "wire.json", "schema.json"))
    if digest(request) != row["request_hash"] or digest(wire) != row["wire_hash"]:
        c.fail("E_INTEGRITY", "Request changed after dispatch")
    codec.decode(wire, digest(request))
    reservations = reservations_for(root, row["task"], digest(wire))
    if len(reservations) > 1:
        c.fail("E_INTEGRITY", "Ambiguous reservation")
    if reservations:
        provider = verify_provider(root, reservations[0], wire, schema)
        if row["status"] == "VALIDATED":
            if provider is None or c.validate_response(c.read(provider/"result.json"), request) != row["value"]:
                c.fail("E_INTEGRITY", "Accepted response detached from provider")
        row["allowance_slot"] = reservations[0]["slot"]
    elif row["status"] == "VALIDATED":
        c.fail("E_INTEGRITY", "Accepted result without counted call")
    row["receipt"] = c.receipt(directory/"receipt.json", root)
    return row

def finish_attempt(root, directory, row):
    c.save(directory/"result.json", row)
    c.save(directory/"receipt.json", {"files": files_in(directory, root, ("receipt.json",))})
    return check_attempt(root, directory)

def attempt(root, task, number, correction=None, provider_factory=CodexProvider):
    directory = root/c.BASE/"tasks"/task["id"]/f"attempt-{number:02}"
    request = deepcopy(task["request"])
    if correction:
        request["repair"] = {"prior_error": correction.get("error"), "details": correction.get("details"),
            "prior_response": correction.get("rejected_value"),
            "instruction": "Correct exactly the recorded schema/quotation/identity defect. Preserve legal uncertainty. This is the second and final attempt for these canonical issues."}
        request["binding_hash"] = digest({k: v for k, v in request.items() if k != "binding_hash"})
    current = {**task, "request": request}
    wire, schema, size = preflight_task(current)
    directory.mkdir(parents=True, exist_ok=True)
    if (directory/"result.json").exists():
        # Complete the receipt after a crash between result and receipt writes.
        if not (directory/"receipt.json").exists():
            c.save(directory/"receipt.json", {"files": files_in(directory, root, ("receipt.json",))})
        row = check_attempt(root, directory)
        if row["request_hash"] != digest(request):
            c.fail("E_INTEGRITY", "Resume generated a different task")
        return row
    for name, value in (("request.json", request), ("wire.json", wire), ("schema.json", schema)):
        path = directory/name
        if path.exists() and c.read(path) != value:
            c.fail("E_INTEGRITY", "Unfinished request changed")
        c.save(path, value)
    row = {"task": task["id"], "phase": task["phase"], "role": task["role"], "issues": task["issues"],
           "request_hash": digest(request), "wire_hash": digest(wire), "request_bytes": size,
           "attempt": number, "started_at": c.now(), "status": "RUNNING"}
    reservations = reservations_for(root, task["id"], digest(wire))
    try:
        if reservations:
            if len(reservations) != 1:
                c.fail("E_INTEGRITY", "Multiple reservations for one attempt")
            directory_provider = verify_provider(root, reservations[0], wire, schema)
            if directory_provider is None or not (directory_provider/"result.json").exists():
                row.update(status="INTERRUPTED", error="E_INTERRUPTED",
                    details="Counted call has no recoverable complete output; preserved and not blindly repeated.")
                return finish_attempt(root, directory, row)
            raw = c.read(directory_provider/"result.json")
            row["provenance"] = {"allowance_slot": reservations[0]["slot"], "offline_recovery": True}
        else:
            allowance = c.EvidenceAllowance(root, task=task["id"], phase=task["phase"],
                issues=task["issues"], correction=correction is not None)
            result = provider_factory(allowance=allowance).complete(wire, schema,
                Settings(timeout_seconds=300, max_input_bytes=200000, max_output_bytes=200000))
            raw = result.value
            row["provenance"] = {k: v for k, v in result.provenance.items() if k != "events_jsonl"}
        row["rejected_value"] = raw
        row["value"] = c.validate_response(raw, request)
        row.pop("rejected_value")
        row.update(status="VALIDATED", ended_at=c.now())
    except LegalMathError as exc:
        if exc.code in ("E_INTEGRITY", "E_AUTHORITY"):
            raise
        row.update(status="FAILED", error=exc.code, details=exc.details, ended_at=c.now())
    except (ValueError, KeyError) as exc:
        row.update(status="FAILED", error="E_SCHEMA", details=str(exc)[:2000], ended_at=c.now())
    return finish_attempt(root, directory, row)

def all_task_rows(root):
    rows = []
    for folder in sorted((root/c.BASE/"tasks").glob("*")):
        attempts = sorted(folder.glob("attempt-*/result.json"))
        if attempts:
            rows.append(check_attempt(root, attempts[-1].parent))
    return rows

def phase_directory(root, phase):
    relative = state(root).get("phase_directories", {}).get(phase, phase)
    path = (root/c.BASE/relative).resolve()
    if not path.is_relative_to((root/c.BASE).resolve()):
        c.fail("E_INTEGRITY", "Phase directory outside fixed campaign")
    return path


def state(root):
    path = root/c.BASE/"state.json"
    return c.read(path) if path.exists() else {"phases": {}, "dependency_failure_streak": 0}

def refresh(root, reason):
    current = state(root)
    next_phase = next((p for p in PHASES if current["phases"].get(p, {}).get("status") not in TERMINAL), None)
    allowance = c.EvidenceAllowance(root).verify()
    rows = all_task_rows(root)
    failed = [{"task": r["task"], "status": r["status"], "error": r.get("error"), "receipt": r["receipt"]}
              for r in rows if r["status"] != "VALIDATED"]
    halted = current["dependency_failure_streak"] >= 2 or (
        allowance["ends_at"] is not None and c.now() >= allowance["ends_at"])
    actions = {
        "P0": "Verify baseline, execute source locator repair, inventory every retained question, preflight and run focused tests.",
        "P1": "Acquire bounded official sources; review dated authority and repaired historical statutory quotations.",
        "P2": "Review contrary hypothetical cases and full responsibility-predicate definitions using acquired authority evidence.",
        "P3": "Propagate source answers to all 35 readings and all original obligations; execute bridge, finite and runtime checks.",
        "P4": "Review actual changes and every proposed original-obligation closure, verify receipts and write recovery/result notes.",
        None: "Review final result and precise unresolved source, interpretation and case-fact frontier."}
    report = {"profile": c.PROFILE, "refreshed_at": c.now(), "reason": reason,
        "phases": current["phases"], "next_phase": next_phase, "allowance": allowance,
        "remaining_model_calls": 100-allowance["used"], "failed_tasks": failed,
        "action": "STOP provider breadth: two consecutive dependency failures or expired window." if halted else actions[next_phase],
        "continuation_veto": halted, "legal_correctness": "NOT_ESTABLISHED",
        "pending_substantive_work": ([
            "All 70 role/reading propagation reviews remain unaccepted after provider deadlines.",
            "Four historical scope corrections remain pending; source dates/families must not be conflated.",
            "Applicable 2023/2026 authority chain, legal standards and actual provider facts remain unresolved.",
            "First two readings exhausted two calls per role; unused total quota cannot authorize another attempt.",
            "Premature final reviews are superseded; no new original obligation is closed."] if halted else []),
        "source_of_plan": c.receipt(root/c.PLAN, root)}
    c.save(root/c.BASE/"next-phase-plan.json", report)
    lines = ["# Refreshed next-phase plan", "", reason, "", report["action"], "",
             f"Calls used: {allowance['used']}/100; repair reserve used: {allowance['repair_calls']}/16.",
             f"Next phase: {next_phase or 'complete'}. Continuation veto: {halted}.", "",
             "Completed engineering steps do not close legal applicability, interpretation or actual-case facts.", ""]
    for p in PHASES:
        r = current["phases"].get(p, {})
        lines.append(f"- {p}: {r.get('status', 'PENDING')}; result: {r.get('result', {}).get('path', 'none')}")
    if halted:
        lines += ["", "Remaining work:"]+[("- "+x) for x in report["pending_substantive_work"]]
    if failed:
        lines += ["", "Failed tasks retained:"]
        lines += [f"- {r['task']}: {r['status']} / {r['error']}" for r in failed]
    c.write_text(root/c.BASE/"next-phase-plan.md", "\n".join(lines)+"\n")
    # Immutable refresh history lets a resumed agent see the decision between phases.
    history = root/c.BASE/"plan-history"
    history.mkdir(exist_ok=True)
    c.save(history/f"{len(list(history.glob('*.json')))+1:04}.json", report)
    return report

def dependency_failure(row):
    return (row.get("error") in ("E_DEPENDENCY", "E_INTERRUPTED") or
            (row.get("error") == "E_RESOURCE_LIMIT" and
             any(x in str(row.get("details", "")) for x in ("Codex call deadline", "Codex output byte cap"))))

def resume_task_protocol(root, tasks):
    result = []
    for task in tasks:
        previous = root/c.BASE/"tasks"/task["id"]/"attempt-01"/"result.json"
        if not previous.exists():
            result.append(task)
            continue
        old = check_attempt(root, previous.parent)
        if old["status"] == "VALIDATED":
            # Reuse the exact previously accepted request rather than regenerate.
            task["request"] = c.read(previous.with_name("request.json"))
            result.append(task)
            continue
        task["id"] += ".grouped-repair"
        task["correction_trigger"] = {
            "error": old.get("error"), "details": {
                "prior": old.get("details"),
                "causal_change": "Short grouped question dispositions replace repeated per-question prose. Exact original IDs, full source/readings and complete question coverage remain mandatory. This is the final canonical attempt."},
            "rejected_value": None}
        result.append(task)
    return result


def charged_failure_streak(root):
    """Count every charged attempt in reservation order, including repairs."""
    by_slot = {}
    for path in (root/c.BASE/'tasks').glob('*/attempt-*/result.json'):
        row = check_attempt(root, path.parent)
        if row.get('allowance_slot'):
            if row['allowance_slot'] in by_slot:
                c.fail('E_INTEGRITY', 'Duplicate charged master result')
            by_slot[row['allowance_slot']] = row
    streak = 0
    for call in c.EvidenceAllowance(root)._load()['calls']:
        row = by_slot.get(call['slot'])
        streak = streak+1 if row is None or dependency_failure(row) else 0
    return streak


def record_failure_streak(root):
    current = state(root)
    current['dependency_failure_streak'] = charged_failure_streak(root)
    c.save(root/c.BASE/'state.json', current)
    return current


def run_tasks(root, phase, tasks):
    progress = []
    current = state(root)
    for offset in range(0, len(tasks), 2):
        current = record_failure_streak(root)
        if current["dependency_failure_streak"] >= 2:
            break
        batch = tasks[offset:offset+2]
        # All actual payloads preflight before either member of a two-role batch can spend.
        accepted = []
        for task in batch:
            try:
                preflight_task(task)
                accepted.append(task)
            except LegalMathError as exc:
                c.save(phase_directory(root, phase)/"frontier"/(task["id"]+".json"),
                    {"status": "PREFLIGHT_BLOCKED", "task": task["id"], "issues": task["issues"],
                     "error": exc.code, "details": exc.details})
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt, root, task, 1, correction=task.get("correction_trigger")) for task in accepted]
            pairs = [(task, future.result()) for task, future in zip(accepted, futures)]
        for task, row in pairs:
            current = record_failure_streak(root)
            if current["dependency_failure_streak"] < 2 and row["status"] == "FAILED" and row.get("error") in ("E_REFERENCE", "E_SCHEMA", "E_UNSUPPORTED_PROFILE"):
                # A precise validator diagnostic is the causal repair trigger, never generic repeated prompting.
                c.save(root/c.BASE/"repairs"/(task["id"]+".json"), {
                    "trigger": row["receipt"], "diagnostic": row.get("details"),
                    "action": "Second counted call with exact prior error and rejected response.",
                    "same_issues": task["issues"], "maximum_new_attempts": 2})
                refresh(root, "Repair triggered for "+task["id"])
                try:
                    row = attempt(root, task, 2, correction=row)
                    current = record_failure_streak(root)
                except LegalMathError as exc:
                    if exc.code != "E_RESOURCE_LIMIT":
                        raise
                    progress.append({"task": task["id"], "status": "REPAIR_BLOCKED", "error": exc.details})
            if current["dependency_failure_streak"] < 2 and phase == "P3" and row["status"] == "VALIDATED" and "reading_updates" in row["value"]:
                repair_task = phases.formal_repair_task(root, task, row)
                if repair_task:
                    trigger = {"error": "CONCRETE_PROGRAM_REPAIR", "details": repair_task["request"]["concrete_repairs"],
                               "rejected_value": None}
                    try:
                        repaired = attempt(root, repair_task, 1, correction=trigger)
                        current = record_failure_streak(root)
                        c.save(root/c.BASE/"repairs"/(repair_task["id"]+".json"),
                               {"trigger": row["receipt"], "result": repaired["receipt"], "issues": repair_task["issues"]})
                    except LegalMathError as exc:
                        if exc.code != "E_RESOURCE_LIMIT":
                            raise
                        c.save(phase_directory(root, phase)/"frontier"/(repair_task["id"]+".json"),
                               {"status": "PROGRAM_REPAIR_BUDGET_BLOCKED", "issues": repair_task["issues"], "details": exc.details})
            progress.append({"task": task["id"], "status": row["status"], "receipt": row["receipt"]})
        current = state(root)
        c.save(phase_directory(root, phase)/"task-progress.json", progress)
        refresh(root, phase+" batch checkpoint; saved responses will be validated before any retry")
        output({"phase": phase, "completed_tasks": len(progress), "scheduled": len(tasks),
                "calls_used": c.EvidenceAllowance(root).verify()["used"]})
    current = state(root)
    pending = [t["id"] for t in tasks if t["id"] not in {r["task"] for r in progress}]
    return {"scheduled": len(tasks), "statuses": dict(Counter(r["status"] for r in progress)),
            "pending_tasks": [t["id"] for t in tasks if t["id"] not in {r["task"] for r in progress}],
            "status": "HALTED" if current["dependency_failure_streak"] >= 2 else "BLOCKED_PHASE_INPUT" if pending else "COMPLETED_WITH_OPEN_EVIDENCE"}

def execute_tests(root, work):
    frozen = active_frozen(root)
    argv = [str(root/".venv/bin/python"), "-m", "pytest", "-q", *TESTS]
    started = c.now()
    with (work/"tests.log").open("w") as stream:
        result = subprocess.run(argv, cwd=frozen, env={**os.environ,
            "CUDA_VISIBLE_DEVICES": "-1", "PYTHONPATH": str(frozen/"src")+os.pathsep+str(frozen/"scripts"),
            "PYTHONDONTWRITEBYTECODE": "1"}, stdout=stream, stderr=subprocess.STDOUT, timeout=300)
    c.save(work/"test-command.json", {"argv": argv, "cwd": str(frozen), "started_at": started,
        "ended_at": c.now(), "exit_code": result.returncode, "cpu_only": True,
        "log": c.receipt(work/"tests.log", root)})
    if result.returncode:
        c.fail("E_INTEGRITY", "Frozen focused tests failed; inspect P0/tests.log")
    return {"status": "PASS", "command": c.receipt(work/"test-command.json", root)}

def summarize(root):
    rows = all_task_rows(root)
    outcomes = [r for row in rows if row["phase"] == "P3" and row["status"] == "VALIDATED"
                for r in [{**v, "role": row["role"]} for v in row["value"].get("obligation_updates", [])]]
    old = c.read(root/c.OLD/"remaining-obligations.json")
    dispositions, proposed = [], []
    for item in old:
        oid = item["obligation"]["obligation_id"]
        findings = {r["role"]: r for r in outcomes if r["question_id"] == oid}
        closes = all(role in findings and findings[role]["original_question_answered"]
                     and findings[role]["status"] == "SUPPORTED_UNDER_STATED_SCOPE" for role in c.ROLES)
        row = {"obligation": item["obligation"], "role_findings": findings,
               "status": "PROPOSED_CLOSED_REQUIRES_FINAL_REVIEW" if closes else "OPEN"}
        dispositions.append(row)
        if closes:
            proposed.append(row)
    runtime_path = phase_directory(root, "P3")/"runtime-summary.json"
    runtime = c.read(runtime_path) if runtime_path.exists() else []
    qpath = phase_directory(root, "P3")/"question-dispositions.json"
    qs = c.read(qpath) if qpath.exists() else []
    ledger = c.EvidenceAllowance(root)._load()
    accounted = set()
    history = []
    for path in sorted((root/c.BASE/"tasks").glob("*/attempt-*/result.json")):
        row = check_attempt(root, path.parent)
        if "allowance_slot" in row:
            if row["allowance_slot"] in accounted:
                c.fail("E_INTEGRITY", "Reservation accounted more than once")
            accounted.add(row["allowance_slot"])
        history.append({"task": row["task"], "attempt": row["attempt"], "status": row["status"], "receipt": row["receipt"]})
    result = {"profile": c.PROFILE, "allowance": c.EvidenceAllowance(root).verify(),
        "baseline_unresolved_original_obligations": 46, "proposed_closures": proposed,
        "remaining_original_obligations_before_final_review": 46-len(proposed),
        "original_obligation_dispositions": dispositions,
        "question_dispositions": dict(Counter(r["status"] for r in qs)),
        "reading_records": 35, "all_original_records_retained": True,
        "task_statuses": dict(Counter(r["status"] for r in rows)), "attempt_history": history,
        "unaccounted_slots": [r["slot"] for r in ledger["calls"] if r["slot"] not in accounted],
        "runtime": {"programs": len(runtime),
            "native_java_probe_cases": sum(r.get("expression", {}).get("cases", 0) for r in runtime),
            "executed_target_cases": sum(r["executed_target_cases"] for r in runtime),
            "qualification_statuses": dict(Counter(r["qualification_status"] for r in runtime))},
        "legal_correctness": "NOT_ESTABLISHED", "release_eligible": False,
        "ranking": "No statistical ranking; roles share the configured model family.",
        "state": state(root)}
    c.save(root/c.BASE/"progress-result.json", result)
    return result

def final_review_packet(summary):
    # All proposed closures retained in full; open obligations identified individually.
    return {k: v for k, v in summary.items() if k not in ("original_obligation_dispositions", "attempt_history", "state")} | {
        "open_obligations": [{"id": r["obligation"]["obligation_id"], "dimension": r["obligation"]["dimension"],
                             "statuses": {k: v["status"] for k, v in r["role_findings"].items()}}
                            for r in summary["original_obligation_dispositions"] if r["status"] == "OPEN"],
        "evidence_limits": ["Finite Boolean checks require explicit meanings and complete fact classifications.",
                            "Production lowering retains all unresolved original questions/dependencies.",
                            "Current source retrieval does not establish point-in-time applicability.",
                            "Availability updates do not close a compound interpretation question."]}

def supervisor_repairs(root):
    path = root/c.BASE/"supervisor-scope-review.json"
    if not path.exists():
        return []
    queue = c.read(path)
    results = []
    for item in queue["issues"]:
        original_path = root/item["result"]
        original = check_attempt(root, original_path.parent)
        request = c.read(original_path.with_name("request.json"))
        request["instructions"] += (
            " SCOPE CORRECTION: This is the historical source family identified in the selected questions. "
            "The 20 April 2026 date belongs only to the active 26EC22 circular, not these historical questions. "
            "Use a historical assessment/event date only if actually established by the original source; "
            "otherwise state it is unknown. A source publication or blackout date does not by itself supply "
            "the assessed submission date. Mixed-gift questions concern gifts only, not schema/signature "
            "or resubmission issues. Do not close a previously open legal question in this scope-only correction.")
        request["binding_hash"] = digest({k: v for k, v in request.items() if k != "binding_hash"})
        task = {"id": original["task"], "phase": original["phase"], "role": original["role"],
                "issues": original["issues"], "request": request}
        trigger = {"error": "SUBSTANTIVE_SCOPE_MISMATCH", "details": item["diagnosis"]+" "+item["repair"],
                   "rejected_value": original["value"]}
        try:
            result = attempt(root, task, 2, correction=trigger)
            results.append({"task": task["id"], "status": result["status"], "receipt": result["receipt"]})
        except LegalMathError as exc:
            if exc.code != "E_RESOURCE_LIMIT":
                raise
            results.append({"task": task["id"], "status": "REPAIR_BUDGET_BLOCKED", "details": exc.details})
        c.save(root/c.BASE/"supervisor-scope-repair-results.json", results)
        refresh(root, "Executed a counted scope correction under unchanged historical issue identities")
        output({"stage": "supervisor-scope-repair", "completed": len(results),
                "calls_used": c.EvidenceAllowance(root).verify()["used"]})
    return results


def finalize(root):
    result = summarize(root)
    if result["unaccounted_slots"]:
        c.fail("E_INTEGRITY", "A reserved call has no final disposition")
    rows = all_task_rows(root)
    final_dispositions = [r for r in rows if r["phase"] == "P4" and r["status"] == "VALIDATED"
                          and (not state(root).get("final_reassessment") or r["task"].endswith(".after-propagation"))
                          and any(f["question_id"] == "final-dispositions" for f in r["value"]["findings"])]
    final_ok = len(final_dispositions) == 2 and all(
        f["status"] == "SUPPORTED_UNDER_STATED_SCOPE" and f["original_question_answered"]
        for r in final_dispositions for f in r["value"]["findings"])
    result["closed_original_obligations"] = len(result["proposed_closures"]) if final_ok else 0
    result["remaining_original_obligations"] = 46-result["closed_original_obligations"]
    result["status"] = "EXECUTED_WITH_OPEN_EVIDENCE"
    result["completed_at"] = c.now()
    scope_results = root/c.BASE/"supervisor-scope-repair-results.json"
    result["supervisor_scope_repairs"] = c.read(scope_results) if scope_results.exists() else []
    result["pending_supervisor_scope_repairs"] = [r for r in result["supervisor_scope_repairs"] if r["status"] != "VALIDATED"]
    c.save(root/c.BASE/"final-result.json", result)
    note = [
        "# Evidence master execution result", "",
        f"New calls used: {result['allowance']['used']}/100; unaccounted reservations: {len(result['unaccounted_slots'])}.",
        f"Original obligations still open: {result['remaining_original_obligations']}/46. All 35 readings retained.",
        f"Question dispositions: {result['question_dispositions']}.",
        f"Executed native/Java probe cases: {result['runtime']['native_java_probe_cases']}; production target cases: {result['runtime']['executed_target_cases']}.", "",
        "| Decision | Primary criterion | Veto | Main uncertainty | Next justified action | Not concluded |",
        "|---|---|---|---|---|---|",
        "| Retain conditional evidence | Source quotes and reservations replayed | Open/failed work retained | Applicability, interpretation and actual facts | Follow exact unresolved dispositions | Legal correctness or production release |", "",
        "| Inference status | Finding |", "|---|---|",
        "| Hard veto screen | Invalid/missing responses excluded; unresolved lowering stays blocked |",
        "| Statistically supported ranking | None; no ranking designed |",
        "| Descriptive-only differences | Counts of agreement, questions and passes |",
        "| Default readiness | No default or release policy change |",
        "| Next evidence needed | Dated authority chain, authoritative interpretation and actual case records as specified in dispositions |", "",
        "Post-run red-team: the strongest alternative explanation for apparent progress is source availability without semantic closure. "
        "A correct applicable authority or case record can overturn a conditional interpretation. The weakest evidence remains the externally unresolved legal standards and dates.", "",
        "Resume with the same approved master command. Completed task receipts are validated and reused. "
        "Do not rerun an old campaign or reset any allowance. No manuscript or prospectus was changed.", ""]
    text = "\n".join(note)
    c.write_text(root/c.BASE/"execution-result.md", text)
    c.write_text(root/"docs/implementation/assurance-evidence-master/execution-result.md", text)
    c.write_text(root/"docs/implementation/assurance-evidence-master/reset-memo.md",
                 "# Recovery memo\n\nUse artifacts/assurance-gap-continuation/2026-10-02/final-result.json and next-phase-plan.md. "
                 "The frozen master, counted attempts, automatic repair triggers and unresolved dispositions are retained there. "
                 "The 2026-10-01 baseline and unrelated prospectus work are protected.\n")
    return {"status": result["status"], "calls_used": result["allowance"]["used"],
            "remaining_original_obligations": result["remaining_original_obligations"], "runtime": result["runtime"]}

def blocked_report(root):
    """Finish independent offline work while respecting a live continuation veto."""
    verify_manifest(root)
    work = root/c.BASE/"offline-after-live-halt"
    receipt_path = work/"completion-receipt.json"
    if receipt_path.exists():
        for ref in c.read(receipt_path)["files"]:
            c.checked(ref, root)
        offline = c.read(work/"offline-result.json")
    else:
        offline = phases.offline_after_halt(root, work)
        c.save(receipt_path, {"files": files_in(work, root, ("completion-receipt.json",))})
    result = summarize(root)
    if result["unaccounted_slots"]:
        c.fail("E_INTEGRITY", "Reserved calls missing disposition")
    result.update(status="HALTED_PROVIDER_PROPAGATION", completed_at=c.now(), offline_replay=offline,
        closed_original_obligations=0, remaining_original_obligations=46,
        accepted_new_reading_reviews=0, pending_new_reading_reviews=70,
        final_review_status="SUPERSEDED_PRE_PROPAGATION_REVIEWS_ONLY",
        active_final_report="No new original-obligation closure accepted.",
        pending_supervisor_scope_repairs=c.read(root/c.BASE/"supervisor-scope-review.json")["issues"],
        required_next_decision="A materially smaller/faster reviewed provider protocol is required. The first two readings have exhausted two attempts per role. No reset or third attempt is authorized by unused global calls.",
        execution_scope_completed="Master implemented, approved, executed, repaired, replayed and checkpointed; legal gap-closure campaign incomplete.")
    c.save(root/c.BASE/"final-result.json", result)
    note = [
        "# Evidence master execution result", "",
        "The executable master was reviewed, approved and run. Live propagation is blocked by six provider deadlines, including the two-call compact-output repair pilot.",
        f"Calls used: {result['allowance']['used']}/100. All reservations are accounted for. Unused calls do not reset per-issue limits.",
        "P0 source-locator repairs, P1 authority review and P2 interpretation cases executed. P3 accepted zero new reviews; all 70 role/reading updates remain pending. Premature P4 reviews are retained as superseded and cannot approve new conclusions.", "",
        f"Independent offline replay recomputed {offline['assessment_replays']} predecessor assessments. It executed {offline['runtime']['native_java_probe_cases']} native/Java probes, explicit unknown/conflict replays, and eight conditional vocabulary-bridge checks.",
        f"Production target cases: {offline['runtime']['executed_target_cases']}. Original obligations still open: 46. Release eligibility: false.",
        f"Mechanical source availability: {offline['named_source_matches']} of {offline['mechanical_source_availability_records']} retained questions explicitly name acquired sources. These are availability links, not accepted interpretations.", "",
        "Four historical authority responses also require scope corrections: they borrowed the active circular's 2026 date or irrelevant source-family requirements. Their exact quotes were valid; their scope was not fully acceptable. Those correction calls remain unexecuted under the live continuation veto.", "",
        "| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |",
        "|---|---|---|---|---|---|",
        "| Retain executed engineering repairs | Tests, exact source locators and receipts replay | Passed within declared scope | Long provider calls | Use frozen reviewed master and retained evidence | Legal closure |",
        "| Halt live propagation | Complete accepted per-reading outputs required | Six 300-second deadlines; latest pilot both failed | Provider latency/output protocol | Design a materially smaller protocol and review issue-level budget | Lack of legal merit or exhausted 100-call grant |",
        "| Retain unchanged conditional runtime evidence | Fresh finite/native/Java checks | Production source questions unresolved | Date, meaning and actual case facts | Resolve applicable source/fact questions before release | Production readiness |", "",
        "| Inference status | Finding |", "|---|---|",
        "| Hard veto | Provider deadlines and unresolved production prerequisites |",
        "| Statistically supported ranking | None |",
        "| Descriptive-only evidence | Call counts, source downloads and finite/runtime pass counts |",
        "| Default readiness | No default or release change |",
        "| Next evidence | Working bounded propagation protocol, dated authority chain, authoritative interpretation and case records |", "",
        "Post-run red-team: code and finite checks cannot substitute for the missing reading reviews. The deadline failures establish a failure of this execution protocol, not rejection of the legal research direction. The strongest alternative explanation is excessive structured-output work or provider latency; no unsupported root cause is asserted.", "",
        "The approved command is .venv/bin/python scripts/assurance_evidence_master.py run. A resume verifies and reuses this checkpoint and does not dispatch while the two-failure veto remains active.", ""]
    text = "\n".join(note)
    c.write_text(root/c.BASE/"execution-result.md", text)
    c.write_text(root/"docs/implementation/assurance-evidence-master/execution-result.md", text)
    c.write_text(root/"docs/implementation/assurance-evidence-master/reset-memo.md",
        "# Recovery memo\n\nActive run: artifacts/assurance-gap-continuation/2026-10-02. "
        "Read final-result.json, execution-result.md and next-phase-plan.md. "
        "Live state is HALTED_PROVIDER_PROPAGATION at 40/100 calls; all calls accounted, "
        "zero new reading reviews accepted, 46 original obligations remain. "
        "P1/P2 and offline conditional repairs/replays are retained. Four historical "
        "scope repairs and all 70 propagation reviews remain pending. "
        "Do not use the superseded early final report or reset exhausted issue attempts.\n")
    refresh(root, "Live continuation veto retained; independent offline replay and honest blocked-result report completed")
    return {"status": result["status"], "calls_used": result["allowance"]["used"],
            "remaining_original_obligations": 46, "offline": offline}


def run(root):
    verify_manifest(root)
    current = state(root)
    refresh(root, "Resume after integrity verification")
    for phase in PHASES:
        current = state(root)
        if current["phases"].get(phase, {}).get("status") in TERMINAL:
            ref = current["phases"][phase]["result"]
            record = c.read(c.checked(ref, root))
            for entry in record["files"]:
                c.checked(entry, root)
            continue
        if current["dependency_failure_streak"] >= 2:
            return blocked_report(root)
        verify_manifest(root)
        work = phase_directory(root, phase)
        work.mkdir(parents=True, exist_ok=True)
        current["phases"][phase] = {"status": "RUNNING", "started_at": c.now()}
        c.save(root/c.BASE/"state.json", current)
        refresh(root, phase+" started after prior phase results")
        if phase == "P0":
            result = phases.p0(root, work)
            result["preflight"] = preflight(root)
            result["tests"] = execute_tests(root, work)
        else:
            authority = c.read(root/c.BASE/"P0"/"authority-context.json")
            if phase == "P1":
                acquisitions, archive = sources.acquire(root, work, authority)
                tasks = phases.authority_tasks(root, authority, acquisitions)
            elif phase == "P2":
                tasks = phases.dispute_tasks(root, authority)
            elif phase == "P3":
                tasks = resume_task_protocol(root, phases.propagation_tasks(root, authority, phases.review_digest(all_task_rows(root))))
            else:
                tasks = phases.final_tasks(root, authority, final_review_packet(summarize(root)))
                if current.get("final_reassessment"):
                    spending = c.EvidenceAllowance(root).verify()["issue_spending"]
                    available, exhausted = [], []
                    for task in tasks:
                        if any(spending.get(issue, 0) >= 2 for issue in task["issues"]):
                            exhausted.append({"task": task["id"], "issues": task["issues"],
                                "status": "FINAL_REVIEW_ATTEMPTS_EXHAUSTED",
                                "effect": "Prior review predates repaired propagation and cannot accept new closures."})
                            continue
                        task["id"] += ".after-propagation"
                        task["request"]["reassessment_reason"] = "Previously blocked propagation now executed; assess this new evidence, not the superseded premature final report."
                        task["request"]["binding_hash"] = digest({k:v for k,v in task["request"].items() if k!="binding_hash"})
                        available.append(task)
                    c.save(work/"final-review-frontier.json", exhausted)
                    tasks = available
            definitions = work/"task-definitions.json"
            if definitions.exists():
                tasks = c.read(definitions)
            else:
                c.save(definitions, tasks)
            c.save(work/"scheduled-tasks.json", [{"task": t["id"], "issues": t["issues"],
                "request_hash": digest(t["request"])} for t in tasks])
            result = run_tasks(root, phase, tasks)
            if phase == "P3" and result["status"] in TERMINAL:
                evidence, detail = phases.propagate_and_check(root, work, all_task_rows(root))
                result["propagation"] = detail
                result["runtime"] = phases.runtime_checks(root, work, evidence)
        record = {"phase": phase, "result": result, "ended_at": c.now(),
                  "files": files_in(work, root, ("phase-result.json",))}
        c.save(work/"phase-result.json", record)
        current = state(root)
        current["phases"][phase] = {"status": result["status"], "result": c.receipt(work/"phase-result.json", root)}
        c.save(root/c.BASE/"state.json", current)
        refresh(root, phase+" completed; dependent next phase rebuilt from retained evidence")
        output({"phase": phase, "status": result["status"], "calls_used": c.EvidenceAllowance(root).verify()["used"]})
        if result["status"] not in TERMINAL:
            return {"status": result["status"], "result": summarize(root)["task_statuses"],
                    "next_plan": str(c.BASE/"next-phase-plan.md")}
    supervisor_repairs(root)
    value = finalize(root)
    refresh(root, "Final replay and result note completed")
    return value

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["preflight", "run", "status", "repair"])
    args = parser.parse_args()
    check_command(c.read(ROOT/("docs/implementation/assurance-evidence-master/repair-allowlist.json" if args.action == "repair" else ALLOWLIST)),
                  [".venv/bin/python", "scripts/assurance_evidence_master.py", args.action])
    if args.action == "status":
        manifest = ROOT/c.BASE/"master-manifest.json"
        value = {"status": "NOT_STARTED", "calls_used": 0} if not manifest.exists() else {
            "state": state(ROOT), "allowance": c.EvidenceAllowance(ROOT).verify()}
        output(value)
        return
    base = ROOT/c.BASE
    base.mkdir(parents=True, exist_ok=True)
    with (base/".master.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            c.fail("E_RESOURCE_LIMIT", "Another master owns the execution lock")
        if args.action == "preflight":
            output(preflight(ROOT))
            return
        if args.action == "repair":
            output(activate_repair(ROOT))
            return
        manifest = prepare(ROOT)
        frozen = active_frozen(ROOT).resolve()
        if CODE != frozen:
            # Freeze before provider dispatch; child inherits the whole-master lock.
            os.set_inheritable(lock.fileno(), True)
            env = {**os.environ, "PYTHONPATH": str(frozen/"src")+os.pathsep+str(frozen/"scripts"),
                   "PYTHONDONTWRITEBYTECODE": "1", "LEGALMATH_MASTER_LOCK_FD": str(lock.fileno())}
            os.execve(ROOT/".venv/bin/python", [str(ROOT/".venv/bin/python"),
                str(frozen/"scripts/assurance_evidence_master.py"), "run"], env)
        output(run(ROOT))

if __name__ == "__main__" and len(sys.argv) == 2 and sys.argv[1].startswith("ops-"):
    import assurance_evidence_operations as operations
    try:
        operations.entry(ROOT, CODE, sys.argv[1])
    except Exception as exc:
        output({"status": "STOPPED", "error": getattr(exc, "code", type(exc).__name__),
                "details": str(getattr(exc, "details", exc))[:2500]})
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__" and len(sys.argv) == 2 and sys.argv[1] in ("extend-preflight", "extend", "extend-status", "extend-repair", "extend-diagnostic"):
    import assurance_evidence_extension as extension
    try:
        extension.entry(ROOT, CODE, sys.argv[1])
    except Exception as exc:
        output({"status": "STOPPED", "error": getattr(exc, "code", type(exc).__name__), "details": str(getattr(exc, "details", exc))[:2500]})
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__" and len(sys.argv) == 2 and sys.argv[1] in ("continue-report", "continue-repair"):
    import assurance_evidence_maintenance as maintenance
    try:
        check_command(c.read(ROOT/"docs/implementation/assurance-evidence-master/maintenance-allowlist.json"),
                      [".venv/bin/python", "scripts/assurance_evidence_master.py", sys.argv[1]])
        with (ROOT/c.BASE/".master.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
            output(maintenance.report(ROOT) if sys.argv[1] == "continue-report" else maintenance.repair(ROOT))
    except Exception as exc:
        output({"status": "STOPPED", "error": getattr(exc, "code", type(exc).__name__),
                "details": str(getattr(exc, "details", exc))[:2000]})
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__" and len(sys.argv) == 2 and sys.argv[1] in ("continue", "continue-preflight", "continue-status"):
    import assurance_evidence_continuation as continuation
    try:
        continuation.entry(ROOT, CODE, sys.argv[1])
    except Exception as exc:
        output({"status": "STOPPED", "error": getattr(exc, "code", type(exc).__name__),
                "details": str(getattr(exc, "details", exc))[:2000]})
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    try:
        # Reuse the inherited lock instead of acquiring it on a second file description.
        inherited = os.environ.pop("LEGALMATH_MASTER_LOCK_FD", None)
        if inherited is not None:
            fd = int(inherited)
            if CODE != active_frozen(ROOT).resolve():
                c.fail("E_AUTHORITY", "Inherited execution lock outside frozen snapshot")
            os.fstat(fd)
            output(run(ROOT))
            os.close(fd)
        else:
            main()
    except Exception as exc:
        error = {"status": "STOPPED", "error": getattr(exc, "code", type(exc).__name__),
                 "details": str(getattr(exc, "details", exc))[:2000]}
        try:
            history = ROOT/c.BASE/"stop-history"
            history.mkdir(exist_ok=True)
            stop = history/f"{len(list(history.glob('*.json')))+1:04}.json"
            c.save(stop, {**error, "at": c.now()})
            c.save(ROOT/c.BASE/"current-stop.json", {"receipt": c.receipt(stop, ROOT)})
            if not (ROOT/c.BASE/"last-stop.json").exists():
                shutil.copyfile(stop, ROOT/c.BASE/"last-stop.json")
            if (ROOT/c.BASE/"authorization.json").exists():
                refresh(ROOT, "Execution stopped: "+str(error["error"])+"; inspect last-stop.json before resuming")
        except Exception:
            pass
        output(error)
        sys.exit(1)
