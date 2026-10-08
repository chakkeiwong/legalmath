"""Fixed-checkpoint continuation with immutable spending and phase evidence."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from legalmath.canonical import canonical, digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import CodexProvider
import assurance_evidence_core as c
import assurance_evidence_master as master
import assurance_evidence_phases as phases
import assurance_evidence_protocol as protocol

PREVIOUS_RUN = c.BASE/"protocol-continuation"
RUN = c.BASE/"protocol-continuation-revision-02"
PLAN = Path("docs/plans/assurance-evidence-protocol-continuation-revision-02.md")
POLICY = Path("docs/implementation/assurance-evidence-master/continuation-allowlist.json")
PHASES = ("pilot", "scope", "propagation", "checks", "final")
LIMITS = {"propagation": 36, "scope": 4, "final": 4}
TESTS = master.TESTS+["tests/assurance/test_assurance_evidence_continuation.py"]
PREFIX = [".venv/bin/python", "scripts/assurance_evidence_master.py"]

def provider_settings():
    return Settings(timeout_seconds=300, max_input_bytes=200000, max_output_bytes=80000)



class Allowance:
    maximum = 100

    def __init__(self, root, task=None, correction=False):
        self.root, self.task, self.correction = Path(root), task, correction
        self.grant_path = self.root/RUN/"amendment.json"
        self.path = self.root/RUN/"allowance.json"
        self.grant = c.read(self.grant_path)
        self.verify()

    def ledger(self):
        grant = self.grant
        previous, calls = raw_digest(self.grant_path.read_bytes()), []
        for slot, path in enumerate(sorted((self.root/RUN/"reservations").glob("*.json")), grant["baseline_used"]+1):
            row = c.read(path)
            if path.name != f"{slot:04}.json" or row["previous_hash"] != previous or row["call"]["slot"] != slot:
                c.fail("E_INTEGRITY", "Continuation reservation chain changed")
            calls.append(row["call"])
            previous = digest(row)
        if self.path.exists():
            saved = c.read(self.path)
            if saved["amendment_hash"] != raw_digest(self.grant_path.read_bytes()) or saved["calls"] != calls[:len(saved["calls"])]:
                c.fail("E_INTEGRITY", "Continuation journal/projection mismatch")
        return calls

    def verify(self):
        g = self.grant
        if (c.read(self.grant_path) != g or g["maximum"] != 100 or g["additional_maximum"] != 60
                or g["baseline_used"] != 40 or g["additional_attempts_per_issue"] != 2
                or g["phase_limits"] != LIMITS or g["repair_maximum"] != 16):
            c.fail("E_AUTHORITY", "Unexpected continuation amendment")
        for ref in g["protected_checkpoint"]:
            c.checked(ref, self.root)
        calls = self.ledger()
        counts, spending, repairs = Counter(), Counter(), 0
        for row in calls:
            if (row["phase"] not in LIMITS or not row["issues"] or len(set(row["issues"])) != len(row["issues"])
                    or not set(row["issues"]) <= set(g["allowed_issues"])
                    or not re.fullmatch("[0-9a-f]{64}", row["request_hash"])
                    or type(row["repair"]) is not bool
                    or not g["starts_at"] <= row["issued_at"] < g["ends_at"]):
                c.fail("E_INTEGRITY", "Invalid continuation reservation")
            counts.update(row["issues"])
            if row["repair"]:
                repairs += 1
            else:
                spending[row["phase"]] += 1
        if len(calls) > 60 or repairs > 16 or any(n > 2 for n in counts.values()) or any(n > LIMITS[p] for p, n in spending.items()):
            c.fail("E_INTEGRITY", "Continuation quota exceeded")
        combined = Counter(g["baseline_issue_spending"])
        combined.update(counts)
        return {"used": 40+len(calls), "baseline_used": 40, "continuation_used": len(calls),
                "remaining": 60-len(calls), "maximum": 100, "repair_calls": repairs,
                "phase_spending": dict(spending), "new_issue_spending": dict(counts),
                "combined_issue_spending": dict(combined), "ends_at": g["ends_at"]}

    def reserve(self, request_hash):
        task = self.task
        if not task or task["phase"] not in LIMITS or not task["issues"] or len(task["issues"]) != len(set(task["issues"])) or not set(task["issues"]) <= set(self.grant["allowed_issues"]):
            c.fail("E_AUTHORITY", "Undeclared continuation issue")
        if not re.fullmatch("[0-9a-f]{64}", request_hash):
            c.fail("E_AUTHORITY", "Invalid request hash")
        with self.path.with_suffix(".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            status = self.verify()
            if not self.grant["starts_at"] <= c.now() < self.grant["ends_at"] or status["used"] >= 100:
                c.fail("E_RESOURCE_LIMIT", "Combined budget or original live window exhausted")
            if any(status["new_issue_spending"].get(i, 0) >= 2 for i in task["issues"]):
                c.fail("E_RESOURCE_LIMIT", "Two additional attempts exhausted for same canonical issue")
            if self.correction:
                if status["repair_calls"] >= 16:
                    c.fail("E_RESOURCE_LIMIT", "Continuation repair reserve exhausted")
            elif status["phase_spending"].get(task["phase"], 0) >= LIMITS[task["phase"]]:
                c.fail("E_RESOURCE_LIMIT", "Continuation phase budget exhausted")
            journal = self.root/RUN/"reservations"
            journal.mkdir(exist_ok=True)
            slot = status["used"]+1
            previous = digest(c.read(journal/f"{slot-1:04}.json")) if slot > 41 else raw_digest(self.grant_path.read_bytes())
            call = {"slot": slot, "task": task["id"], "phase": task["phase"], "issues": task["issues"],
                    "repair": self.correction, "request_hash": request_hash, "issued_at": c.now()}
            c.save(journal/f"{slot:04}.json", {"previous_hash": previous, "call": call})
            c.save(self.path, {"amendment_hash": raw_digest(self.grant_path.read_bytes()), "calls": self.ledger()})
            return slot


def protected_checkpoint(root):
    names = ["authorization.json", "allowance.json", "state.json", "final-result.json",
             "master-manifest.json", "active-revision.json", "supervisor-scope-review.json"]
    refs = [c.receipt(root/c.BASE/n, root) for n in names]
    refs += [c.receipt(p, root) for p in sorted((root/c.BASE/"reservations").glob("*.json"))]
    previous = root/PREVIOUS_RUN
    if previous.exists():
        if list((previous/"reservations").glob("*.json")):
            c.fail("E_AUTHORITY", "A spent continuation cannot be replaced by this zero-call engineering revision")
        refs += [c.receipt(previous/n, root) for n in ("manifest.json", "amendment.json", "state.json", "final-result.json")]
    return refs


def freeze(root):
    master.verify_manifest(root)
    provider_settings()
    work = root/RUN
    if (work/"manifest.json").exists():
        return verify(root)
    previous = c.EvidenceAllowance(root).verify()
    if previous["used"] != 40:
        c.fail("E_AUTHORITY", "Continuation is bound to the disclosed 40-call checkpoint")
    work.mkdir(parents=True, exist_ok=True)
    amendment = {
        "authorization": "Renewed user instruction to create, review and execute a repaired master after disclosed provider halt.",
        "created_at": c.now(), "baseline_used": 40, "maximum": 100, "additional_maximum": 60,
        "additional_attempts_per_issue": 2, "phase_limits": LIMITS, "repair_maximum": 16,
        "baseline_issue_spending": previous["issue_spending"], "starts_at": previous["starts_at"],
        "ends_at": previous["ends_at"], "allowed_issues": c.read(root/c.BASE/"authorization.json")["allowed_issues"],
        "protected_checkpoint": protected_checkpoint(root),
        "rule": "Append-only supplement on same canonical issues; original authority and spending are unchanged."}
    if (work/"amendment.json").exists():
        amendment = c.read(work/"amendment.json")
    else:
        c.save(work/"amendment.json", amendment)
    Allowance(root).verify()
    hashes = c.code_material(root)
    hashes["pyproject.toml"] = raw_digest((root/"pyproject.toml").read_bytes())
    frozen = work/"frozen"
    for name, sha in hashes.items():
        p = frozen/name
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and raw_digest(p.read_bytes()) != sha:
            c.fail("E_INTEGRITY", "Partial continuation snapshot differs; inspect before repair")
        if not p.exists():
            shutil.copyfile(root/name, p)
    tasks = protocol.propagation_tasks(root)+protocol.scope_tasks(root)
    report = {"status": "PASS", "provider_calls": 0, "tasks": []}
    for t in tasks:
        wire, schema, reverse = protocol.transport(t)
        report["tasks"].append({"task": t["id"], "bytes": len(canonical(wire)), "request_hash": digest(wire)})
    report["maximum_bytes"] = max(x["bytes"] for x in report["tasks"])
    c.save(work/"preflight.json", report)
    c.save(work/"initial-tasks.json", tasks)
    argv = [str(root/".venv/bin/python"), "-m", "pytest", "-q", *TESTS]
    with (work/"tests.log").open("w") as stream:
        result = subprocess.run(argv, cwd=frozen, env={**os.environ, "CUDA_VISIBLE_DEVICES": "-1",
            "PYTHONPATH": str(frozen/"src")+os.pathsep+str(frozen/"scripts"), "PYTHONDONTWRITEBYTECODE": "1"},
            stdout=stream, stderr=subprocess.STDOUT, timeout=300)
    if result.returncode:
        c.fail("E_INTEGRITY", "Continuation tests failed; no live dispatch authorized")
    manifest = {"status": "REVIEWED_AND_FROZEN", "created_at": c.now(), "frozen_root": str(frozen.relative_to(root)),
        "code_hashes": hashes, "references": [c.receipt(work/n, root) for n in
            ("amendment.json", "preflight.json", "initial-tasks.json", "tests.log")]+[c.receipt(root/PLAN, root), c.receipt(root/POLICY, root)],
        "command": PREFIX+["continue"], "test_command": argv, "environment": str(root/".venv"),
        "cpu_only": True, "gpu_hidden": True, "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "seeds": "N/A: deterministic local checks; remote generation uncontrolled", "data_version": "Original checkpoint/source receipts",
        "plan": str(PLAN), "result": str(RUN/"final-result.json"), "allowance_baseline": 40,
        "review": "Skeptical plan audit plus executed identity, spending, restart, coverage and phase-gate tests."}
    c.save(work/"manifest.json", manifest)
    refresh(root, "Frozen tests and actual packet preflight passed; two-role pilot is next")
    return verify(root)


def verify(root):
    master.verify_manifest(root)
    manifest = c.read(root/RUN/"manifest.json")
    for ref in manifest["references"]:
        c.checked(ref, root)
    for name, sha in manifest["code_hashes"].items():
        if raw_digest((root/manifest["frozen_root"]/name).read_bytes()) != sha:
            c.fail("E_INTEGRITY", "Frozen continuation code changed: "+name)
    Allowance(root).verify()
    for row in task_rows(root):
        folder = root/RUN/"tasks"/row["task"]/f"attempt-{row['attempt']:02}"
        task = c.read(folder/"task.json")
        wire, schema, reverse = protocol.transport(task)
        calls = [r for r in Allowance(root).ledger() if r["slot"] == row.get("allowance_slot")]
        if calls:
            provider = provider_folder(root, calls[0], wire, schema)
            if row["status"] == "VALIDATED" and (provider is None or protocol.validate(c.read(provider/"result.json"), task, reverse) != row["value"]):
                c.fail("E_INTEGRITY", "Accepted continuation result detached from provider")
        elif row["status"] == "VALIDATED":
            c.fail("E_INTEGRITY", "Uncounted accepted continuation result")
    for phase in state(root)["phases"].values():
        saved = c.read(c.checked(phase["result"], root))
        for ref in saved.get("files", []):
            c.checked(ref, root)
    active = root/RUN/"active-revision.json"
    if active.exists():
        revision = c.read(c.checked(c.read(active)["receipt"], root))
        if revision["status"] != "REPAIR_VALIDATED":
            c.fail("E_INTEGRITY", "Unvalidated continuation repair")
        for ref in revision["references"]:
            c.checked(ref, root)
        for name, sha in revision["code_hashes"].items():
            if raw_digest((root/revision["frozen_root"]/name).read_bytes()) != sha:
                c.fail("E_INTEGRITY", "Active repaired snapshot changed")
        manifest = {**manifest, "frozen_root": revision["frozen_root"]}
    return manifest


def state(root):
    path = root/RUN/"state.json"
    return c.read(path) if path.exists() else {"phases": {}, "halt": None}


def task_rows(root):
    rows = []
    for path in sorted((root/RUN/"tasks").glob("*/attempt-*/result.json")):
        if not path.with_name("receipt.json").exists():
            saved = c.read(path.with_name("task.json"))
            attempt(root, saved, number=int(path.parent.name.split('-')[-1]),
                provider_factory=lambda **kw: c.fail('E_AUTHORITY', 'Receipt recovery cannot dispatch'))
        row = c.read(path)
        for ref in c.read(path.with_name("receipt.json"))["files"]:
            c.checked(ref, root)
        row["receipt"] = c.receipt(path.with_name("receipt.json"), root)
        override = root/RUN/"offline-revalidations"/row["task"]/f"attempt-{row['attempt']:02}.json"
        if override.exists():
            saved = c.read(override)
            c.checked(saved["original_receipt"], root)
            row = {**saved["row"], "receipt": c.receipt(override, root)}
        rows.append(row)
    return rows


def refresh(root, reason):
    status, allowance = state(root), Allowance(root).verify()
    next_phase = next((p for p in PHASES if status["phases"].get(p, {}).get("status") not in ("COMPLETED", "COMPLETED_WITH_OPEN_TASKS")), None)
    rows = task_rows(root)
    accepted = [r for r in rows if r["status"] == "VALIDATED" and r["phase"] == "propagation" and "reading_updates" in r["value"]]
    reviewed = {(r["role"], u["reading_id"]) for r in accepted for u in r["value"]["reading_updates"]}
    action = {
        "pilot": "Validate both role outputs on the real initial workload; no breadth unless both pass.",
        "scope": "Correct four historical scope responses using only their own source family and unknown assessment dates.",
        "propagation": "Review remaining readings; use exact validator or program-defect repairs only.",
        "checks": "Rebuild all dispositions and execute formal/finite/native/Java/unknown/conflict checks on retained programs.",
        "final": "Review the completed new evidence and every changed availability assertion; previous final reviews cannot approve it.",
        None: "Continue only from the saved evidence frontier; original applicability, definition, time and factual obligations remain open."}[next_phase]
    report = {"refreshed_at": c.now(), "reason": reason, "next_phase": next_phase,
        "action": status["halt"] or action, "halt": status["halt"], "allowance": allowance,
        "accepted_reading_reviews": len(reviewed), "pending_reading_reviews": 70-len(reviewed),
        "remaining_original_obligations": 46, "closure_authorized": False, "state": status,
        "failed_attempts": [{"task": r["task"], "error": r.get("error"), "receipt": r["receipt"]} for r in rows if r["status"] != "VALIDATED"],
        "remaining_evidence": ["Complete 2023-11-02 and 2026-04-20 legislative and UT Code applicability chains.",
          "Authoritative distinctions among retained responsibility, supervision and achieved adequacy; request/footnote relation.",
          "Provider, scheme, ownership/control and appointment/termination facts and complete responsibility intervals.",
          "Historical JFIU schema/certificate/resubmission instructions, mixed-gift treatment, applicable structured-product provisions."],
        "legal_correctness": "NOT_ESTABLISHED", "release_eligible": False}
    history = root/RUN/"plan-history"
    history.mkdir(exist_ok=True)
    c.save(history/f"{len(list(history.glob('*.json')))+1:04}.json", report)
    c.save(root/RUN/"next-phase-plan.json", report)
    c.write_text(root/RUN/"next-phase-plan.md", "# Refreshed continuation plan\n\n"+reason+"\n\n"+report["action"]+
        f"\n\nCalls {allowance['used']}/100; accepted reading reviews {len(reviewed)}/70; original obligations open 46/46.\n\n"+
        "\n".join("- "+x for x in report["remaining_evidence"])+"\n")
    return report


def provider_folder(root, call, wire, schema):
    folder = root/RUN/"provider-evidence"/f'{call["slot"]:04}-{call["request_hash"][:16]}'
    if not (folder/"manifest.json").exists():
        return None
    manifest = c.read(folder/"manifest.json")
    if manifest["allowance_slot"] != call["slot"] or manifest["request_hash"] != digest(wire):
        c.fail("E_INTEGRITY", "Detached continuation provider evidence")
    for name, ref in manifest["files"].items():
        if Path(name).name != name or raw_digest((folder/name).read_bytes()) != ref["retained_sha256"]:
            c.fail("E_INTEGRITY", "Changed provider evidence")
    if c.read(folder/"request.json") != wire or c.read(folder/"schema.json") != schema:
        c.fail("E_INTEGRITY", "Provider request/schema changed")
    events = folder/"events.jsonl"
    if events.exists():
        for line in events.read_text().splitlines():
            if line.strip() and json.loads(line).get("item", {}).get("type") in {"command_execution", "mcp_tool_call", "web_search", "file_change"}:
                c.fail("E_AUTHORITY", "Provider attempted tool use")
    return folder


def canonical_prior_output(task, value):
    if value is None:
        return None
    _, _, aliases = protocol.transport(task)
    mapping = {**aliases["tokens"], **{k: q["question_id"] for k, q in aliases["questions"].items()}}
    return protocol.translate(value, mapping)


def attempt(root, task, number=1, correction=None, provider_factory=CodexProvider):
    task = deepcopy(task)
    if correction:
        task["request"]["correction"] = {"error": correction.get("error"), "details": correction.get("details"),
            "prior_output": canonical_prior_output(task, correction.get("rejected_value")),
            "instruction": "Correct this exact validator defect; preserve every original identity and substantive uncertainty."}
        task["request"].pop("binding_hash")
        task["request"]["binding_hash"] = digest(task["request"])
    wire, schema, reverse = protocol.transport(task)
    directory = root/RUN/"tasks"/task["id"]/f"attempt-{number:02}"
    directory.mkdir(parents=True, exist_ok=True)
    for name, value in (("task.json", task), ("request.json", wire), ("schema.json", schema), ("aliases.json", reverse)):
        path = directory/name
        if path.exists() and c.read(path) != value:
            c.fail("E_INTEGRITY", "Restart changed an existing continuation request")
        if not path.exists():
            c.save(path, value)
    calls = [r for r in Allowance(root).ledger() if r["task"] == task["id"] and r["request_hash"] == digest(wire)]
    if len(calls) > 1:
        c.fail("E_INTEGRITY", "Duplicate dispatch for same request")
    if (directory/"result.json").exists():
        row = c.read(directory/"result.json")
        expected = {"task": task["id"], "phase": task["phase"], "role": task["role"],
            "issues": task["issues"], "attempt": number, "request_hash": digest(wire),
            "allowance_slot": calls[0]["slot"] if calls else None}
        if any(row.get(k) != v for k, v in expected.items()):
            c.fail("E_INTEGRITY", "Saved continuation result detached from request or reservation")
        if not (directory/"receipt.json").exists():
            if row["status"] == "VALIDATED":
                provider = provider_folder(root, calls[0], wire, schema) if calls else None
                if provider is None or protocol.validate(c.read(provider/"result.json"), task, reverse) != row["value"]:
                    c.fail("E_INTEGRITY", "Cannot recover receipt for detached accepted result")
            c.save(directory/"receipt.json", {"files": master.files_in(directory, root, ("receipt.json",))})
        for ref in c.read(directory/"receipt.json")["files"]:
            c.checked(ref, root)
        if row["status"] == "FAILED" and row.get("rejected_value") and row.get("error") in ("E_REFERENCE", "E_SCHEMA"):
            # Replay actual saved provider bytes under the conservative validator.
            folder = provider_folder(root, calls[0], wire, schema) if calls else None
            if folder is not None:
                try:
                    validated = protocol.validate(c.read(folder/"result.json"), task, reverse)
                except LegalMathError:
                    validated = None
                if validated is not None:
                    row = {**row, "status": "VALIDATED", "value": validated,
                           "offline_revalidation": "Conservative disposition; no new call or changed original receipt"}
                    override = root/RUN/"offline-revalidations"/row["task"]/f"attempt-{number:02}.json"
                    c.save(override, {"original_receipt": c.receipt(directory/"receipt.json", root), "row": row})
                    return {**row, "receipt": c.receipt(override, root)}
        if row["status"] == "VALIDATED":
            if not calls:
                c.fail("E_INTEGRITY", "Accepted output has no reservation")
            folder = provider_folder(root, calls[0], wire, schema)
            if folder is None or protocol.validate(c.read(folder/"result.json"), task, reverse) != row["value"]:
                c.fail("E_INTEGRITY", "Accepted output changed or detached")
        return {**row, "receipt": c.receipt(directory/"receipt.json", root)}
    row = {"task": task["id"], "phase": task["phase"], "role": task["role"], "issues": task["issues"],
        "attempt": number, "request_hash": digest(wire), "request_bytes": len(canonical(wire)), "started_at": c.now()}
    try:
        if calls:
            folder = provider_folder(root, calls[0], wire, schema)
            if folder is None or not (folder/"result.json").exists():
                c.fail("E_DEPENDENCY", "Interrupted counted request lacks recoverable output; no blind replay")
            raw = c.read(folder/"result.json")
            row["offline_recovery"] = True
        else:
            master.output({"task_started": task["id"], "attempt": number, "input_bytes": len(canonical(wire))})
            allowance = Allowance(root, task, correction=bool(correction) or task.get("program_repair", False) or task.get("counted_repair", False))
            result = provider_factory(allowance=allowance).complete(wire, schema,
                provider_settings())
            raw = result.value
            row["provenance"] = {k: v for k, v in result.provenance.items() if k != "events_jsonl"}
        row["rejected_value"] = raw
        row["value"] = protocol.validate(raw, task, reverse)
        row.pop("rejected_value")
        row["status"] = "VALIDATED"
    except LegalMathError as exc:
        if exc.code in ("E_INTEGRITY", "E_AUTHORITY"):
            raise
        row.update(status="FAILED", error=exc.code, details=str(exc.details)[:2500])
    except (ValueError, KeyError) as exc:
        row.update(status="FAILED", error="E_SCHEMA", details=str(exc)[:2500])
    calls = [r for r in Allowance(root).ledger() if r["task"] == task["id"] and r["request_hash"] == digest(wire)]
    row.update(ended_at=c.now(), allowance_slot=calls[0]["slot"] if calls else None)
    c.save(directory/"result.json", row)
    c.save(directory/"receipt.json", {"files": master.files_in(directory, root, ("receipt.json",))})
    return {**row, "receipt": c.receipt(directory/"receipt.json", root)}


def consecutive_failures(root):
    rows = sorted((r for r in task_rows(root) if r.get("allowance_slot")), key=lambda r: r["allowance_slot"])
    streak = 0
    for r in rows:
        streak = streak+1 if master.dependency_failure(r) else 0
    return streak


def halt(root, reason):
    current = state(root)
    current["halt"] = reason
    c.save(root/RUN/"state.json", current)
    refresh(root, reason)
    return False


def split_timeout_task(task):
    request = task["request"]
    if task["phase"] != "propagation" or request["kind"] != "propagation" or len(request["selected"]) != 2:
        c.fail("E_AUTHORITY", "Single-reading timeout repair requires a paired propagation request")
    result = []
    for cid in request["selected"]:
        child = deepcopy(task)
        child["id"] = task["id"]+".single."+digest(cid)[:12]
        child["issues"] = ["reading."+cid+"."+task["role"]]
        if not set(child["issues"]) <= set(task["issues"]):
            c.fail("E_AUTHORITY", "Split repair changed canonical issue")
        child["counted_repair"] = True
        r = child["request"]
        r["selected"] = [cid]
        for name in ("readings", "questions", "reading_hashes", "prior_assessments"):
            r[name] = {cid: r[name][cid]}
        r["question_inventory"] = [q for q in r["question_inventory"] if q["reading_id"] == cid]
        r["obligations"] = [o for o in r["obligations"] if cid in o["candidate_ids"]]
        r["timeout_repair"] = {"original_task": task["id"],
            "cause_under_test": "Reduce two complete reading dispositions to one; original timeout cause remains unproved.",
            "instruction": "Review this one selected reading and every supplied original question. Complete sources and prior assessment are retained. This is the final permitted attempt on this canonical issue."}
        r.pop("binding_hash")
        r["binding_hash"] = digest(r)
        protocol.transport(child)
        result.append(child)
    expected = {(q["reading_id"], q["question_id"]) for q in request["question_inventory"]}
    actual = [(q["reading_id"], q["question_id"]) for child in result for q in child["request"]["question_inventory"]]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        c.fail("E_INTEGRITY", "Single-reading repair lost or duplicated an original question")
    return result


def recover_timeout(root, task, row):
    if not (row.get("error") == "E_RESOURCE_LIMIT" and "Codex call deadline" in str(row.get("details"))
            and task["phase"] == "propagation" and task["request"]["kind"] == "propagation"
            and len(task["request"]["selected"]) == 2):
        return [row]
    children = split_timeout_task(task)
    definitions = root/RUN/"timeout-repairs"/(task["id"]+".json")
    if definitions.exists():
        if c.read(definitions) != children:
            c.fail("E_INTEGRITY", "Saved split timeout repair changed")
    else:
        c.save(definitions, children)
    # Each child owns the same canonical issue and its remaining counted attempt.
    # Completed child outputs recover normally; no attempt or journal is reset.
    refresh(root, "Split timed-out paired task into complete single-reading repair attempts")
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt, root, child) for child in children]
        return [future.result() for future in futures]


def unresolved_task_ids(root, tasks):
    rows = accepted_rows(root)
    identities = {(row["role"], update["reading_id"]) for row in rows
                  for update in row["value"].get("reading_updates", [])}
    ids = {row["task"] for row in rows}
    return [task["id"] for task in tasks if not (
        all((task["role"], cid) in identities for cid in task["request"]["selected"])
        if task["phase"] == "propagation" and task["request"]["kind"] == "propagation" else task["id"] in ids)]


def run_tasks(root, tasks, pilot=False):
    for offset in range(0, len(tasks), 2):
        if state(root)["halt"]:
            return False
        batch = tasks[offset:offset+2]
        for task in batch:
            protocol.transport(task)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt, root, t) for t in batch]
            pairs = [(task, f.result()) for task, f in zip(batch, futures)]
        if consecutive_failures(root) >= 2:
            return halt(root, "Two consecutive provider failures; no corrective dispatch before route recovery.")
        final_rows = []
        for task, row in pairs:
            if row["status"] != "VALIDATED" and row.get("allowance_slot") is not None and row.get("error") in ("E_REFERENCE", "E_SCHEMA", "E_UNSUPPORTED_PROFILE"):
                spending = Allowance(root).verify()["new_issue_spending"]
                if (root/RUN/"tasks"/task["id"]/"attempt-02/result.json").exists() or all(spending.get(issue, 0) < 2 for issue in task["issues"]):
                    refresh(root, "Exact response-validation repair triggered for "+task["id"])
                    row = attempt(root, task, number=2, correction=row)
            final_rows.extend(recover_timeout(root, task, row))
        refresh(root, "Executed task batch; accepted coverage, failures and remaining calls recomputed")
        master.output({"completed_batch": offset//2+1, "tasks": len(tasks),
            "statuses": [r["status"] for r in final_rows], "calls_used": Allowance(root).verify()["used"]})
        if consecutive_failures(root) >= 2:
            return halt(root, "Two consecutive provider failures; causal protocol repair required before further dispatch.")
        failures = [r for r in final_rows if r["status"] != "VALIDATED"]
        if failures and not all(t["phase"] == "scope" for t in batch):
            by_id = {t["id"]: t for t in batch}
            spending = Allowance(root).verify()["new_issue_spending"]
            independent_exhausted = not pilot and all(
                r["task"] in by_id and by_id[r["task"]]["phase"] == "propagation" and
                all(spending.get(issue, 0) >= 2 for issue in by_id[r["task"]]["issues"])
                for r in failures)
            if not independent_exhausted:
                return halt(root, "Unaccepted response blocks dependent work; no issue limit is reset.")
            c.save(root/RUN/"exhausted-reading-frontier.json", [
                {"task": r["task"], "status": "UNACCEPTED_ATTEMPTS_EXHAUSTED", "receipt": r.get("receipt")}
                for r in failures])
            refresh(root, "Exhausted reading reviews stay unaccepted; independent undispatched reviews may continue")
    return True


def accepted_rows(root):
    latest = {}
    for row in task_rows(root):
        if row["status"] != "VALIDATED":
            continue
        if row["task"] not in latest or row["attempt"] > latest[row["task"]]["attempt"]:
            latest[row["task"]] = row
    return [r for r in latest.values() if r["status"] == "VALIDATED"]


def execute_program_repairs(root):
    originals = {t["id"]: t for t in c.read(root/RUN/"initial-tasks.json")}
    for path in (root/RUN/"timeout-repairs").glob("*.json"):
        originals.update({t["id"]: t for t in c.read(path)})
    frontier = []
    for row in accepted_rows(root):
        if row["phase"] != "propagation" or "reading_updates" not in row["value"]:
            continue
        task = originals[row["task"]]
        adapted = deepcopy(task)
        adapted["phase"] = "P3"
        repaired = phases.formal_repair_task(root, adapted, row)
        if repaired is None:
            continue
        repaired["id"] = task["id"]+".program-repair"
        repaired["phase"] = "propagation"
        repaired["issues"] = ["reading."+cid+"."+task["role"] for cid in repaired["request"]["selected"]]
        repaired["program_repair"] = True
        path = root/RUN/"program-repairs"/(repaired["id"]+".json")
        if path.exists():
            repaired = c.read(path)
        else:
            c.save(path, repaired)
        saved = root/RUN/'tasks'/repaired['id']/'attempt-01/result.json'
        if saved.exists():
            outcome = attempt(root, repaired,
                provider_factory=lambda **kw: c.fail('E_AUTHORITY', 'Saved repair replay cannot dispatch'))
            frontier.append({'task': repaired['id'], 'status': outcome['status'], 'receipt': outcome['receipt']})
            continue
        spending = Allowance(root).verify()["new_issue_spending"]
        if any(spending.get(i, 0) >= 2 for i in repaired["issues"]):
            frontier.append({"task": repaired["id"], "status": "SAME_ISSUE_REPAIR_BUDGET_EXHAUSTED",
                             "issues": repaired["issues"], "effect": "Program stays challenged and excluded from accepted runtime evidence."})
            continue
        outcome = attempt(root, repaired)
        frontier.append({"task": repaired["id"], "status": outcome["status"], "receipt": outcome["receipt"]})
        refresh(root, "Concrete program repair executed or explicitly budget-blocked")
        if consecutive_failures(root) >= 2:
            halt(root, "Two consecutive provider failures during formal repair")
            break
    c.save(root/RUN/"program-repair-frontier.json", frontier)
    return not state(root)["halt"]


def check_coverage(root):
    rows = [r for r in accepted_rows(root) if r["phase"] == "propagation" and "reading_updates" in r["value"]]
    actual = [(r["role"], u["reading_id"]) for r in rows for u in r["value"]["reading_updates"]]
    expected = {(role, cid) for role in c.ROLES for cid in phases.context(root)["candidates"]}
    if len(actual) != len(set(actual)) or set(actual) != expected:
        c.fail("E_REFERENCE", "Incomplete reading coverage blocks checks/final phase")
    return rows


def checks(root):
    check_coverage(root)
    if not execute_program_repairs(root):
        return False
    rows = [{**r, "phase": "P3" if r["phase"] == "propagation" else r["phase"]} for r in accepted_rows(root)]
    work = root/RUN/"checks"
    work.mkdir(exist_ok=True)
    evidence, detail = phases.propagate_and_check(root, work, rows)
    runtime = phases.runtime_checks(root, work, evidence)
    c.save(work/"result.json", {"propagation": detail, "runtime": runtime,
        "production_release": False, "original_obligations_open": 46})
    if detail["missing_reading_dispositions"]:
        c.fail("E_REFERENCE", "Propagation lost an accepted reading")
    return True


def final_tasks(root):
    rows = accepted_rows(root)
    propagation = check_coverage(root)
    value = c.read(root/RUN/"checks/result.json")
    tasks = []
    authority = c.read(root/c.BASE/"P0/authority-context.json")
    for subject in ("engineering", "dispositions"):
        for role in c.ROLES:
            if subject == "engineering":
                evidence = {"allowance": Allowance(root).verify(), "checks": value,
                    "calls": [{"task": r["task"], "slot": r.get("allowance_slot"), "status": r["status"], "error": r.get("error")} for r in task_rows(root)],
                    "tests": (root/RUN/"tests.log").read_text(), "manifest": c.read(root/RUN/"manifest.json")["review"],
                    "controller": Path(__file__).read_text()}
                packet = {"units": [{"unit_id": "engineering.executed", "text": json.dumps(evidence, ensure_ascii=False)}]}
                question = "Audit the supplied executable controller, actual tests, counted calls and executed checks. Identify material unhandled defects. Quote executed evidence. No source or production readiness claim follows from these checks."
            else:
                packet = protocol.compact_packet(phases.sources.current_packet(root, authority))
                # Each reviewer audits the other role's new findings. All 70 reading
                # dispositions are covered across the pair, with all changed question
                # assertions literal; unchanged open questions remain in exact receipts.
                reviewed_role = next(r for r in c.ROLES if r != role)
                evidence = []
                for r in propagation:
                    if r["role"] != reviewed_role:
                        continue
                    v = r["value"]
                    evidence.append({"readings": v["reading_updates"],
                        "changed_questions": [q for q in v["question_updates"] if q["status"] != "REMAINS_OPEN"],
                        "open_question_ids": [q["question_id"] for q in v["question_updates"] if q["status"] == "REMAINS_OPEN"],
                        "obligations": v["obligation_updates"]})
                question = "Audit the other role's complete reading dispositions and all changed question assertions. Are source availability, dates, meaning, conditional programs or case facts overstated? Identify exact reading/question IDs for corrections. All 46 original obligations remain open; production release is false. Unchanged open question texts remain in the archived task evidence, outside this final packet."
            tasks.append(protocol.make_task("final", role, ["final."+subject+"."+role], {
                "kind": "review", "source_packet": packet, "result_under_review": evidence,
                "questions": [{"id": "final-"+subject, "missing": question}],
                "instructions": "State concrete material defects and next repairs. Supported scope means only that this engineering/disposition audit has no identified blocker, never legal correctness. Keep answer under 1500 characters."}))
    return tasks


def phase_done(root, phase, data):
    work = root/RUN/phase
    work.mkdir(exist_ok=True)
    c.save(work/"phase-result.json", {"phase": phase, "status": "COMPLETED", "completed_at": c.now(), "files": master.files_in(work, root, ("phase-result.json",)), **data})
    current = state(root)
    current["phases"][phase] = {"status": data.get("status", "COMPLETED"), "result": c.receipt(work/"phase-result.json", root)}
    c.save(root/RUN/"state.json", current)
    refresh(root, phase+" completed; next phase refreshed from saved results")


def result(root):
    rows, status = accepted_rows(root), state(root)
    checkpath = root/RUN/"checks/result.json"
    report = {"status": "HALTED_CONTINUATION" if status["halt"] else "EXECUTED_WITH_OPEN_EVIDENCE",
        "completed_at": c.now(), "allowance": Allowance(root).verify(), "state": status,
        "accepted_reading_reviews": sum(len(r["value"]["reading_updates"]) for r in rows if "reading_updates" in r["value"]),
        "scope_corrections": sum(r["phase"] == "scope" for r in rows),
        "final_reviews": sum(r["phase"] == "final" for r in rows),
        "checks": c.read(checkpath) if checkpath.exists() else None,
        "closed_original_obligations": 0, "remaining_original_obligations": 46,
        "legal_correctness": "NOT_ESTABLISHED", "release_eligible": False,
        "question_dispositions": dict(Counter(q["status"] for r in rows for q in r["value"].get("question_updates", [])))}
    slots = [r.get("allowance_slot") for r in task_rows(root) if r.get("allowance_slot")]
    charged = [r["slot"] for r in Allowance(root).ledger()]
    if len(slots) != len(set(slots)) or set(slots) != set(charged):
        c.fail("E_INTEGRITY", "Continuation calls are not fully accounted")
    report["unaccounted_slots"] = []
    report["final_review_findings"] = [{"role": r["role"], **f} for r in rows if r["phase"] == "final" for f in r["value"]["findings"]]
    report["final_review_acceptance"] = "ACCEPTED_WITHIN_SCOPE" if len(report["final_review_findings"]) == 4 and all(f["status"] == "SUPPORTED_UNDER_STATED_SCOPE" and f["original_question_answered"] for f in report["final_review_findings"]) else "OPEN_OR_UNACCEPTED"
    report["unrepaired_challenges"] = [{"role": r["role"], **u} for r in rows for u in r["value"].get("reading_updates", []) if u["disposition"] == "CHALLENGED"]
    c.save(root/RUN/"final-result.json", report)
    note = ("# Continuation execution result\n\n"
        f"Status: {report['status']}. Combined spending: {report['allowance']['used']}/100. "
        f"Accepted reading reviews: {report['accepted_reading_reviews']}/70; scope corrections: {report['scope_corrections']}/4; final reviews: {report['final_reviews']}/4.\n\n"
        "All 46 original obligations remain open. Legal correctness is not established and release eligibility is false.\n\n"
        "| Decision | Primary criterion | Veto | Main uncertainty | Next action | Not concluded |\n"
        "|---|---|---|---|---|---|\n"
        f"| Retain validated evidence | Exact identities, quotations and complete dispositions | {status['halt'] or 'No controller halt'} | Authority dates, legal standards and actual facts | Follow next-phase-plan.json | Legal or production correctness |\n\n"
        "| Inference status | Finding |\n|---|---|\n"
        "| Hard veto | Failed responses excluded; original legal and production prerequisites preserved |\n"
        "| Statistically supported ranking | None |\n"
        "| Descriptive only | Counts, durations and conditional finite/runtime passes |\n"
        "| Default readiness | No default or release change |\n"
        "| Next evidence | Dated authority chain, source interpretations and actual case facts |\n\n"
        "Post-run red-team: exact quotations and complete responses do not prove the interpretations. "
        "Source availability may look like closure while applicability and meaning remain unresolved. "
        "An applicable contrary authority or actual case record could overturn conditional findings.\n\n"
        "Resume with .venv/bin/python scripts/assurance_evidence_master.py continue. "
        "Completed phases and calls are reused after receipt verification; original campaign evidence is immutable.\n")
    c.write_text(root/RUN/"execution-result.md", note)
    c.write_text(root/"docs/implementation/assurance-evidence-master/continuation-result.md", note)
    c.write_text(root/"docs/implementation/assurance-evidence-master/reset-memo.md",
        "# Recovery memo\n\nActive continuation: "+str(RUN)+". Read final-result.json and next-phase-plan.md. "
        f"Combined calls: {report['allowance']['used']}/100; status {report['status']}. "
        "The original 40-call checkpoint remains intact. Resume only the continuation command; do not reset old allowances.\n")
    refresh(root, "Execution result and precise remaining-evidence frontier recorded")
    return report


def run(root):
    verify(root)
    current = state(root)
    if current["halt"]:
        return result(root)
    tasks = c.read(root/RUN/"initial-tasks.json")
    overrides = root/RUN/"explicit-response-contracts.json"
    if overrides.exists():
        replacements = c.read(overrides)
        updated = []
        for task in tasks:
            entry = replacements.get(task["id"])
            if entry:
                if digest(task) != entry["original_task_hash"]:
                    c.fail("E_INTEGRITY", "Explicit response contract detached from original task")
                task = entry["task"]
            updated.append(task)
        tasks = updated
    propagation = [t for t in tasks if t["phase"] == "propagation"]
    for phase in PHASES:
        current = state(root)
        if current["phases"].get(phase, {}).get("status") in ("COMPLETED", "COMPLETED_WITH_OPEN_TASKS"):
            c.checked(current["phases"][phase]["result"], root)
            continue
        refresh(root, phase+" starting after predecessor validation")
        if phase == "checks":
            ok = checks(root)
            data = {"checks": c.receipt(root/RUN/"checks/result.json", root)} if ok else {}
        else:
            if phase == "pilot":
                scheduled = propagation[:2]
            elif phase == "scope":
                scheduled = [t for t in tasks if t["phase"] == "scope"]
            elif phase == "propagation":
                scheduled = propagation[2:]
            else:
                definitions = root/RUN/"final/task-definitions.json"
                if definitions.exists():
                    scheduled = c.read(definitions)
                else:
                    scheduled = final_tasks(root)
                    for task in scheduled:
                        protocol.transport(task)
                    c.save(definitions, scheduled)
            ok = run_tasks(root, scheduled, pilot=phase == "pilot")
            unaccepted = unresolved_task_ids(root, scheduled)
            data = {"tasks": [t["id"] for t in scheduled], "unaccepted_tasks": unaccepted,
                    "status": "COMPLETED_WITH_OPEN_TASKS" if phase == "scope" and unaccepted else "COMPLETED"}
        if not ok:
            return result(root)
        if phase == "propagation" and data.get("unaccepted_tasks"):
            data["status"] = "BLOCKED_INCOMPLETE_REVIEWS"
            phase_done(root, phase, data)
            halt(root, "Independent propagation finished with unaccepted exhausted reviews; complete coverage still blocks checks and final review.")
            return result(root)
        phase_done(root, phase, data)
    return result(root)


def entry(root, code, action):
    master.check_command(c.read(root/POLICY), PREFIX+[action])
    work = root/RUN
    if action == "continue-status":
        master.output({"state": state(root), "allowance": Allowance(root).verify()} if (work/"amendment.json").exists() else {"status": "NOT_STARTED"})
        return
    (root/c.BASE).mkdir(parents=True, exist_ok=True)
    with (root/c.BASE/".master.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            c.fail("E_RESOURCE_LIMIT", "Another master holds the campaign lock")
        manifest = freeze(root)
        if action == "continue-preflight":
            master.output({"status": "REVIEWED_AND_FROZEN", "calls_used": Allowance(root).verify()["used"],
                "maximum_bytes": c.read(work/"preflight.json")["maximum_bytes"], "manifest": str(RUN/"manifest.json")})
            return
        frozen = root/manifest["frozen_root"]
        os.set_inheritable(lock.fileno(), True)
        env = {**os.environ, "PYTHONPATH": str(frozen/"src")+os.pathsep+str(frozen/"scripts"),
            "PYTHONDONTWRITEBYTECODE": "1", "CUDA_VISIBLE_DEVICES": "-1", "LEGALMATH_CONTINUATION_LOCK": str(lock.fileno())}
        os.execve(root/".venv/bin/python", [str(root/".venv/bin/python"), str(frozen/"scripts/assurance_evidence_continuation.py")], env)


if __name__ == "__main__":
    root = Path("/home/chakwong/python/legalmath")
    try:
        fd = int(os.environ.pop("LEGALMATH_CONTINUATION_LOCK"))
        os.fstat(fd)
        manifest = verify(root)
        if Path(__file__).resolve().parents[1] != (root/manifest["frozen_root"]).resolve():
            c.fail("E_AUTHORITY", "Continuation execution must use its frozen snapshot")
        value = run(root)
        master.output({k: value[k] for k in ("status", "accepted_reading_reviews", "scope_corrections", "final_reviews", "remaining_original_obligations")} |
            {"calls_used": value["allowance"]["used"], "remaining_calls": value["allowance"]["remaining"]})
    except Exception as exc:
        error = {"status": "STOPPED", "error": getattr(exc, "code", type(exc).__name__),
                 "details": str(getattr(exc, "details", exc))[:2500], "at": c.now()}
        c.save(root/RUN/"current-stop.json", error)
        master.output(error)
        sys.exit(1)
