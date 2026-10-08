"""Independent, bounded successor to the completed prospectus evidence master."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from contextlib import contextmanager
import fcntl
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urljoin
from xml.etree import ElementTree as ET
import zipfile

from . import master_control as c
from . import master_sources as sources

ROOT = c.ROOT
OUT = ROOT / "docs/implementation/prospectus-evidence-continuation"
DATA = ROOT / "docs/prospectus/evidence-continuation"
PLAN = ROOT / "docs/plans/prospectus-evidence-continuation.md"
BASE = c.OUT / "phases/E7/attempt-002"
PHASES = ("C0", "C1", "C2", "C3", "C4")
DEPENDENCIES = {"C0": (), "C1": ("C0",), "C2": ("C1",), "C3": ("C0",),
                "C4": ("C1", "C2", "C3")}
PREFIX = c.PREFIX + ["continue"]
MAX_SECONDS = 14400
MAX_FAILURES = 3
OK = {"PASS", "QUALIFIED"}
MECHANISMS = {"principal_write_down", "mandatory_common_conversion", "cash_repayment"}


def artifacts(directory):
    return {str(p.relative_to(directory)): c.sha(p) for p in sorted(directory.rglob("*"))
            if p.is_file() and p != directory / "receipt.json" and "__pycache__" not in p.parts}


def method():
    return {**c.method_files(), c.relative(PLAN): c.sha(PLAN)}


def state():
    path = OUT / "state.json"
    return c.read(path) if path.exists() else {"version": "prospectus-continuation.v1", "wall_seconds": 0,
                                            "phases": {}, "attempts": []}


@contextmanager
def locked():
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / ".lock").open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def parent_files():
    # Include receipts themselves, source bytes, the old state and both budgets.
    return {c.relative(p): c.sha(p) for base in (c.OUT, c.DATA) for p in sorted(base.rglob("*"))
            if p.is_file() and not p.name.startswith(".") and "__pycache__" not in p.parts}


def verify_parent():
    pinned = OUT / "parent-snapshot.json"
    actual = parent_files()
    if pinned.exists() and c.read(pinned)["files"] != actual:
        raise ValueError("Protected parent campaign changed")
    for receipt in sorted((c.OUT / "phases").glob("*/attempt-*/receipt.json")):
        if c.read(receipt)["outputs"] != c.hashes(receipt.parent):
            raise ValueError("Parent phase artifact changed: " + c.relative(receipt))
    checks = sources.verify_sources()
    for path in sorted((c.OUT / "freezes").glob("candidate-*/freeze.json")):
        with zipfile.ZipFile(path.parent / "method.zip") as archive:
            for name, expected in c.read(path)["files"].items():
                if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                    raise ValueError("Parent method archive changed")
    from .loss_absorption_reader import load_document
    data = c.read(BASE / "inventory.json")
    for doc in data["documents"].values():
        load_document(doc, ROOT)
    if not pinned.exists():
        c.write(pinned, {"parent_commit": "119f3d0d", "at": c.now(), "files": actual}, exclusive=True)
    return {"files": len(actual), "sources": checks, "sha256": c.sha(pinned)}


def fingerprint(phase, current):
    files = {c.relative(OUT / "parent-snapshot.json"): c.sha(OUT / "parent-snapshot.json")}
    if phase in {"C2", "C4"}:
        p = DATA / "reader-review.json"
        files[c.relative(p)] = c.sha(p) if p.exists() else None
    if phase in {"C3", "C4"}:
        files[c.relative(DATA / "public-queue.json")] = c.sha(DATA / "public-queue.json")
    if phase == "C4":
        p = DATA / "source-review.json"
        files[c.relative(p)] = c.sha(p) if p.exists() else None
    return c.digest({"method": method(), "files": files,
                     "upstream": {p: current["phases"].get(p, {}).get("receipt_sha256")
                                  for p in DEPENDENCIES[phase]}})


def current_phase(phase, current):
    item = current["phases"].get(phase)
    if not item or item["status"] not in OK:
        return False
    directory = ROOT / item["directory"]
    receipt = directory / "receipt.json"
    return (receipt.exists() and c.sha(receipt) == item["receipt_sha256"]
            and c.read(receipt)["outputs"] == artifacts(directory)
            and item["inputs"] == fingerprint(phase, current))


def previous(current, phase):
    return c.read(ROOT / current["phases"][phase]["directory"] / "result.json")


def counts(rows):
    return {"yes": sum(r["answer"] is True for r in rows), "no": sum(r["answer"] is False for r in rows),
            "unresolved": sum(r["answer"] is None for r in rows)}


def clause_inventory(rows):
    return [{"id": r["id"], "answer": r["answer"], "open_issues": r["open_issues"],
             "unresolved": [e for e in r["evidence"] if e["disposition"].startswith("unresolved")],
             "dispositions": dict(Counter(e["disposition"] for e in r["evidence"]))} for r in rows]


def obligations(receipt):
    inventory = receipt["bank_investigation"]["inventory"]
    keys = [r["rule_id"] for r in inventory]
    if len(keys) != 14 or len(set(keys)) != 14:
        raise ValueError("Missing or duplicate bank obligations")
    return sorted(keys)


def command(argv, log, timeout=900):
    return c.command(argv, log, timeout=timeout)


def validate_reader_review(review, replay):
    path = ROOT / replay["classification"]
    if review["classification_sha256"] != c.sha(path) or review["answer_changes"] != replay["answer_changes"]:
        raise ValueError("Reader review is stale or omits changed answers")
    expected = {e["id"]: e for e in replay["new_witnesses"]}
    actual = {e["id"]: e for e in review["new_witnesses"]}
    if len(actual) != len(review["new_witnesses"]) or set(actual) != set(expected):
        raise ValueError("Every changed supporting witness needs review")
    for key, entry in actual.items():
        if (entry["quote_sha256"] != c.digest(expected[key]["quote"]) or not entry.get("reason")
                or entry.get("verdict") != "SUPPORTED_WITHIN_SELECTED_SOURCE"):
            raise ValueError("Unsupported changed witness")
    old = next(r for r in c.read(BASE / "classification.json")["results"] if r["id"] == "lvmh-senior-2029")
    new = next(r for r in c.read(path)["results"] if r["id"] == old["id"])
    unresolved = {e["id"]: e for e in old["evidence"] if e["disposition"].startswith("unresolved")}
    inspected = {e["old_id"]: e for e in review["lvmh_passages"]}
    if len(inspected) != len(review["lvmh_passages"]) or set(inspected) != set(unresolved):
        raise ValueError("All five LVMH passages need contextual review")
    for key, entry in inspected.items():
        old_e = unresolved[key]
        matches = [e for e in new["evidence"] if e["document"] == old_e["document"]
                   and e["start"] == old_e["start"] and e["end"] == old_e["end"]
                   and e["quote"] == old_e["quote"] and e["disposition"] == entry["new_disposition"]]
        if (not matches or entry["quote_sha256"] != c.digest(old_e["quote"]) or not entry.get("reason")
                or entry["new_disposition"].startswith("unresolved")):
            raise ValueError("Unresolved or unbound LVMH exclusion")
    if not review.get("remaining"):
        raise ValueError("Review must retain its source and human-adjudication limits")


def all_requests():
    return sorted((OUT / "phases/C3").glob("attempt-*/requests/*/receipt.json"))


def acquire(row, directory, policy):
    sources.valid_url(row["url"], policy)
    prior = all_requests()
    if len(prior) >= policy["max_http_requests"]:
        raise ValueError("Successor HTTP budget exhausted")
    if sum(c.read(p)["url"] == row["url"] for p in prior) >= policy["max_requests_per_url"]:
        raise ValueError("Successor per-URL retry limit exhausted")
    if not re.fullmatch(r"[a-z0-9-]{1,80}", row["key"]):
        raise ValueError("Invalid public source key")
    target = directory / "requests" / f"{len(prior)+1:03d}-{row['key']}"
    target.mkdir(parents=True, exist_ok=False)
    receipt = {**row, "status": "DISPATCH_RESERVED", "at": c.now(), "budget_sequence": len(prior)+1}
    c.write(target / "receipt.json", receipt)
    argv = ["curl", "--max-time", str(policy["max_http_seconds"]), "--connect-timeout", "15",
            "--max-filesize", str(policy["max_response_bytes"]), "--proto", "=https", "-A",
            "LegalMath public-source research", "-sS", "-D", str(target / "headers.txt"), "-o",
            str(target / "response.body"), "-w", "%{http_code}", row["url"]]
    started = time.monotonic()
    try:
        run = subprocess.run(argv, capture_output=True, timeout=policy["max_http_seconds"]+5)
        (target / "stderr.log").write_bytes(run.stderr)
        status = int(run.stdout.strip()) if run.stdout.strip().isdigit() else 0
        receipt.update(exit_code=run.returncode, http_status=status,
                       status="RETAINED" if status == 200 and run.returncode == 0 else "UNAVAILABLE_OR_REDIRECT")
    except subprocess.TimeoutExpired as exc:
        (target / "stderr.log").write_bytes(exc.stderr or b"")
        receipt.update(status="TIMEOUT", http_status=0, exit_code=124)
    body = target / "response.body"
    if not body.exists():
        body.write_bytes(b"")
    receipt.update(command=argv, body=c.relative(body), sha256=c.sha(body), bytes=body.stat().st_size,
                   wall_seconds=time.monotonic()-started)
    headers = (target / "headers.txt").read_text(errors="replace") if (target / "headers.txt").exists() else ""
    redirects = re.findall(r"(?im)^location:\s*(.*?)\s*$", headers)
    if redirects:
        receipt["redirect"] = urljoin(row["url"], redirects[-1])
    receipt["kind"] = "pdf" if body.read_bytes().startswith(b"%PDF") else "html_or_other"
    if receipt["status"] == "RETAINED":
        if receipt["kind"] == "pdf":
            from pypdf import PdfReader
            pages = [{"page": i+1, "text": p.extract_text() or ""} for i, p in enumerate(PdfReader(body).pages)]
            c.write(target / "pages.json", {"source_sha256": receipt["sha256"], "pages": pages,
                    "source_stage": "REQUIRES_REVIEW", "blank_pages": [p["page"] for p in pages if not p["text"].strip()]})
        else:
            parser = sources.Links()
            parser.feed(body.read_text(errors="replace"))
            (target / "text.txt").write_text("\n".join(parser.parts))
            c.write(target / "links.json", [{"url": urljoin(row["url"], r["href"]), "text": r["text"]} for r in parser.links])
    c.write(target / "receipt.json", receipt)
    return target / "receipt.json"


def execute(phase, directory, current):
    data = c.read(BASE / "inventory.json")
    baseline = c.read(BASE / "classification.json")["results"]
    if phase == "C0":
        preserved = verify_parent()
        rows = clause_inventory(baseline)
        for row in rows:
            receipt = c.read(BASE / "receipts" / (row["id"] + ".json"))
            row.update(source_references=receipt["source_obligations"]["references"],
                       obligation_keys=obligations(receipt), missing_product_facts=receipt["required_product_evidence"])
        c.write(directory / "gap-inventory.json", rows)
        return {"status": "PASS", "parent": preserved, "counts": counts(baseline),
                "unresolved_clauses": sum(len(r["unresolved"]) for r in rows),
                "source_references": sum(len(r["source_references"]) for r in rows),
                "repairs": ["Created independent continuation; protected historical evidence and exhausted budgets"],
                "remaining": ["G03–G32: see code ledger and exhaustive gap-inventory.json"]}
    if phase == "C1":
        tests = command([sys.executable, "-m", "pytest", "tests/prospectus", "tests/compliance", "-q",
                         "--junitxml=" + str(directory / "tests.xml")], directory / "tests.log")
        replay = command([sys.executable, "scripts/run_bond_loss_absorption_classification.py", "--inventory",
                          str(BASE / "inventory.json"), "--output", str(directory / "run"), "--checks", "--plan", str(PLAN)],
                         directory / "replay.log")
        rows = c.read(directory / "run/classification.json")["results"]
        from .master_phases import validate_rows
        validate_rows(data, rows)
        old = {r["id"]: r for r in baseline}
        changes = [{"id": r["id"], "before": old[r["id"]]["answer"], "after": r["answer"]}
                   for r in rows if r["answer"] is not old[r["id"]]["answer"]]
        old_ids = {e["id"] for r in baseline for e in r["evidence"] if e["kind"] in MECHANISMS and e["disposition"] == "applicable"}
        witnesses = [e for r in rows for e in r["evidence"] if e["kind"] in MECHANISMS and e["disposition"] == "applicable" and e["id"] not in old_ids]
        c.write(directory / "clause-inventory.json", clause_inventory(rows))
        return {"status": "QUALIFIED", "classification": c.relative(directory / "run/classification.json"),
                "classification_sha256": c.sha(directory / "run/classification.json"), "counts": counts(rows),
                "regression": tests, "replay": replay, "answer_changes": changes, "new_witnesses": witnesses,
                "repairs": ["Executed counterexample-covered reader repairs; replayed all 36 exposed issues"],
                "remaining": ["Review changed answers, supporting witnesses and all five LVMH passages before C2"]}
    if phase == "C2":
        review_path = DATA / "reader-review.json"
        if not review_path.exists():
            return {"status": "WAITING_REVIEW", "remaining": ["Record source-bound reader-review.json against C1 result"], "repairs": []}
        replay = previous(current, "C1")
        review = c.read(review_path)
        validate_reader_review(review, replay)
        rows = c.read(ROOT / replay["classification"])["results"]
        from .master_phases import integration, requirements
        integration(directory, data, rows)
        queue = requirements(data, rows)
        for row in queue:
            receipt = c.read(directory / "receipts" / (row["issue_id"] + ".json"))
            old = c.read(BASE / "receipts" / (row["issue_id"] + ".json"))
            if obligations(receipt) != obligations(old):
                raise ValueError("Bank obligation identities changed")
            row.update(obligation_keys=obligations(receipt), missing_product_facts=receipt["required_product_evidence"],
                       source_references=receipt["source_obligations"]["references"],
                       joined_calculation="UBS_EXISTING" if receipt["instrument_investigation"] else "NOT_ATTACHED")
        c.write(directory / "evidence-requirements.json", queue)
        c.write(directory / "accepted-reader-review.json", review)
        return {"status": "QUALIFIED", "cases": len(queue), "obligations_per_case": 14, "permission": False,
                "repairs": ["Rebuilt all bank investigations; checked exact obligation identities and retained all missing facts"],
                "remaining": ["G10–G26, G30–G32: full source, authority, calculation and actual-fact requirements remain"]}
    if phase == "C3":
        policy = c.read(DATA / "public-queue.json")
        receipts = []
        for row in policy["requests"]:
            existing = [p for p in all_requests() if c.read(p)["url"] == row["url"]]
            path = existing[-1] if existing and c.read(existing[-1])["status"] != "DISPATCH_RESERVED" else acquire(row, directory, policy)
            receipts.append(c.relative(path))
            response = c.read(path)
            if response.get("redirect"):
                try:
                    sources.valid_url(response["redirect"], policy)
                    prior = [p for p in all_requests() if c.read(p)["url"] == response["redirect"]]
                    follow = prior[-1] if prior else acquire({**row, "key": row["key"]+"-redirect", "url": response["redirect"]}, directory, policy)
                    receipts.append(c.relative(follow))
                except ValueError as exc:
                    c.write(directory / (row["key"] + "-redirect-blocked.json"), {"reason": str(exc), "redirect": response["redirect"]})
        return {"status": "QUALIFIED", "requests": len(all_requests()), "receipts": list(dict.fromkeys(receipts)),
                "repairs": ["Executed bounded public recovery including the reviewed official HKMA redirect host"],
                "remaining": ["Inspect each retained response; retrieval alone closes no legal dependency"]}
    if phase == "C4":
        path = DATA / "source-review.json"
        if not path.exists():
            return {"status": "WAITING_REVIEW", "remaining": ["Inspect C3 responses and record source-review.json"], "repairs": []}
        expected = set(previous(current, "C3")["receipts"])
        review = c.read(path)
        reviewed = {r["receipt"]: r for r in review["findings"]}
        if set(reviewed) != expected or len(reviewed) != len(review["findings"]):
            raise ValueError("Every public response needs review")
        for name, finding in reviewed.items():
            receipt = c.read(ROOT / name)
            if (finding["receipt_sha256"] != c.sha(ROOT / name) or not finding.get("finding") or not finding.get("remaining")
                    or receipt.get("sha256") != c.sha(ROOT / receipt["body"])):
                raise ValueError("Unbound source response review")
        c.write(directory / "source-review.json", review)
        replay = previous(current, "C1")
        rows = c.read(ROOT / replay["classification"])["results"]
        inventory = clause_inventory(rows)
        tests_path = ROOT / current["phases"]["C1"]["directory"] / "tests.xml"
        total = sum(int(s.get("tests", 0)) for s in ET.parse(tests_path).getroot().iter("testsuite"))
        result = {"status": "QUALIFIED", "counts": counts(rows), "regression_tests": total,
                  "answer_changes": replay["answer_changes"], "unresolved_clauses": sum(len(r["unresolved"]) for r in inventory),
                  "post_repair_unseen_cases": 0, "actual_permission": False, "source_review": review,
                  "repairs": [previous(current, p).get("repairs", []) for p in PHASES[:-1]],
                  "remaining": ["Complete source contracts/editions/languages, current authority, source-specific calculations, actual client/event facts, independent fresh validation and human legal review"]}
        c.write(directory / "results.json", {**result, "issues": inventory})
        lines = ["# Executed prospectus continuation", "", f"{len(rows)} exposed issues: {counts(rows)}. {total} regression tests passed.", "",
                 "All 36 joined bank investigations retain the exact fourteen obligations and grant no transaction permission.", "",
                 "| Issue | Before | After | Unresolved clauses |", "| --- | --- | --- | --- |"]
        old = {r["id"]: r for r in baseline}
        for r in inventory:
            label = lambda value: "Yes" if value is True else "No" if value is False else "Unresolved"
            lines.append(f"| {r['id']} | {label(old[r['id']]['answer'])} | {label(r['answer'])} | {len(r['unresolved'])} |")
        lines += ["", "| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |",
                  "| --- | --- | --- | --- | --- | --- |",
                  "| Retain bounded repairs | Counterexamples, regression, source replay and bank identities checked | See retained failures and source reviews | Shared interpretation and missing evidence | Resolve the code-traced gap ledger | Complete legal correctness, population accuracy or trade clearance |", "",
                  "All cases are exposed. There is no statistically supported ranking or post-repair unseen accuracy estimate.", "",
                  "The strongest alternative explanation is a shared omission between the reader and replay. An applicable omitted clause or wrong source edition would overturn the affected result.", "",
                  "See gaps.md, the C2 evidence-requirements.json and the source findings below for the remaining work.", ""]
        for finding in review["findings"]:
            lines += [finding["finding"], "", finding["remaining"], ""]
        (directory / "results.md").write_text("\n".join(lines))
        return result
    raise ValueError("Unknown successor phase")


def next_plan(phase, result, directory, current):
    ready = {p: result["status"] in OK if p == phase else current_phase(p, current)
             for p in PHASES}
    next_phase = next((p for p in PHASES if not ready[p]
                       and all(ready[q] for q in DEPENDENCIES[p])), None)
    return {"after": phase, "result": c.relative(directory / "result.json"), "result_sha256": c.sha(directory / "result.json"),
            "next_phase": next_phase, "next_command": " ".join(PREFIX + (["run"] if next_phase else ["status"])),
            "repairs_executed": result.get("repairs", []), "remaining": result.get("remaining", []),
            "action": "Repair or supply the named review before retrying" if result["status"] not in OK else "Continue with explicit qualifications",
            "gap_ledger": c.relative(OUT / "gaps.md"), "actual_permission": False}


def run_phase(phase, current):
    if any(not current_phase(p, current) for p in DEPENDENCIES[phase]):
        raise ValueError("Stale predecessor; run from first stale phase")
    if current_phase(phase, current):
        return current["phases"][phase]
    if current["wall_seconds"] >= MAX_SECONDS:
        raise ValueError("Successor execution budget exhausted")
    before = fingerprint(phase, current)
    if sum(r["phase"] == phase and r["inputs"] == before and r["status"] == "FAILED" for r in current["attempts"]) >= MAX_FAILURES:
        raise ValueError("Repeated identical failure budget exhausted")
    folder = OUT / "phases" / phase
    directory = folder / f"attempt-{len(list(folder.glob('attempt-*')))+1:03d}"
    directory.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    started_at = c.now()
    current["phases"][phase] = {"status": "RUNNING", "directory": c.relative(directory), "inputs": before,
                                "started_at": started_at}
    c.write(OUT / "state.json", current)
    print(json.dumps({"phase": phase, "status": "RUNNING", "directory": c.relative(directory)}), flush=True)
    try:
        result = execute(phase, directory, current)
        if before != fingerprint(phase, current):
            raise ValueError("Inputs/method changed during phase")
        if current["wall_seconds"] + time.monotonic()-started > MAX_SECONDS:
            raise ValueError("Successor execution budget exceeded during phase")
    except Exception as exc:
        result = {"status": "FAILED", "error": type(exc).__name__, "remaining": [str(exc)], "repairs": [], "research_direction_rejected": False}
    c.write(directory / "result.json", result, exclusive=True)
    plan = next_plan(phase, result, directory, current)
    c.write(directory / "next-phase-plan.json", plan, exclusive=True)
    receipt = {"phase": phase, "status": result["status"], "inputs": before, "outputs": artifacts(directory),
               "method": method(), "command": PREFIX + ["phase", phase], "invocation": sys.argv,
               "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "environment": sys.executable, "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1", "seeds": "N/A deterministic",
               "plan": c.relative(PLAN), "started_at": started_at, "finished_at": c.now(), "wall_seconds": time.monotonic()-started}
    c.write(directory / "receipt.json", receipt, exclusive=True)
    item = {"status": result["status"], "directory": c.relative(directory), "inputs": before, "receipt_sha256": c.sha(directory / "receipt.json")}
    current["phases"][phase] = item
    current["attempts"].append({"phase": phase, **item})
    current["wall_seconds"] += receipt["wall_seconds"]
    c.write(OUT / "state.json", current)
    refresh(current)
    print(json.dumps({"phase": phase, **item}), flush=True)
    return item


def recover_interruption(current):
    for phase, item in current["phases"].items():
        if item["status"] == "RUNNING":
            directory = ROOT / item["directory"]
            path = directory / "receipt.json"
            if path.exists():
                receipt = c.read(path)
                if receipt["outputs"] != artifacts(directory):
                    raise ValueError("Interrupted completion receipt is corrupt")
            else:
                elapsed = max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(item["started_at"])).total_seconds())
                receipt = {"phase": phase, "status": "INTERRUPTED", "inputs": item["inputs"],
                           "started_at": item["started_at"], "finished_at": c.now(),
                           "wall_seconds": min(MAX_SECONDS, elapsed), "command": PREFIX + ["run"],
                           "plan": c.relative(PLAN), "reason": "Interrupted process; preserve and retry in a new attempt"}
                c.write(directory / "interruption.json", receipt, exclusive=True)
                receipt["outputs"] = artifacts(directory)
                c.write(path, receipt, exclusive=True)
            item.update(status=receipt["status"], receipt_sha256=c.sha(path))
            current["attempts"].append({"phase": phase, **item})
            current["wall_seconds"] += receipt["wall_seconds"]
            c.write(OUT / "state.json", current)


def verify(current):
    parent = verify_parent()
    verified = 0
    for item in current["attempts"]:
        directory = ROOT / item["directory"]
        if c.sha(directory / "receipt.json") != item["receipt_sha256"] or c.read(directory / "receipt.json")["outputs"] != artifacts(directory):
            raise ValueError("Successor receipt/artifact changed")
        verified += len(artifacts(directory))
    stale = [p for p in PHASES if not current_phase(p, current)]
    return {"status": "INCOMPLETE" if stale else "PASS", "parent": parent, "successor_artifacts": verified,
            "stale": stale, "actual_permission": False}


def refresh(current):
    stale = [p for p in PHASES if not current_phase(p, current)]
    next_phase = next((p for p in stale if all(current_phase(q, current) for q in DEPENDENCIES[p])), None)
    result = {"next_phase": next_phase, "next_command": " ".join(PREFIX + (["run"] if stale else ["status"])),
              "stale": stale, "required_results": [], "remaining": [], "actual_permission": False,
              "gap_ledger": c.relative(OUT / "gaps.md")}
    for phase in PHASES:
        item = current["phases"].get(phase)
        if not item:
            continue
        path = ROOT / item["directory"] / "result.json"
        if path.exists():
            result["required_results"].append({"phase": phase, "path": c.relative(path), "sha256": c.sha(path)})
            if phase in stale or (not stale and phase == "C4"):
                result["remaining"].extend(c.read(path).get("remaining", []))
    result["remaining"] = list(dict.fromkeys(result["remaining"]))
    c.write(OUT / "next-phase-plan.json", result)
    return result


def review_template(current):
    if not current_phase("C1", current):
        raise ValueError("Current replay required before preparing source review")
    replay = previous(current, "C1")
    old = next(r for r in c.read(BASE / "classification.json")["results"] if r["id"] == "lvmh-senior-2029")
    rows = c.read(ROOT / replay["classification"])["results"]
    new = next(r for r in rows if r["id"] == old["id"])
    reader = {"classification_sha256": replay["classification_sha256"], "answer_changes": replay["answer_changes"],
              "new_witnesses": [{"id": e["id"], "quote_sha256": c.digest(e["quote"]), "reason": "",
                                  "verdict": "PENDING"} for e in replay["new_witnesses"]],
              "lvmh_passages": [], "remaining": ""}
    for e in old["evidence"]:
        if e["disposition"].startswith("unresolved"):
            matches = [x for x in new["evidence"] if (x["document"], x["start"], x["end"], x["quote"]) ==
                       (e["document"], e["start"], e["end"], e["quote"])]
            reader["lvmh_passages"].append({"old_id": e["id"], "quote_sha256": c.digest(e["quote"]),
                "new_disposition": matches[0]["disposition"] if len(matches) == 1 else "PENDING", "reason": ""})
    source_review = {"findings": []}
    if current_phase("C3", current):
        source_review["findings"] = [{"receipt": path, "receipt_sha256": c.sha(ROOT / path),
                                      "finding": "", "remaining": ""} for path in previous(current, "C3")["receipts"]]
    result = {"reader": reader, "sources": source_review, "notice": "Blank templates are not accepted reviews"}
    c.write(OUT / "review-template.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "run", "phase", "status", "verify", "review-template"))
    parser.add_argument("phase", nargs="?", choices=PHASES)
    args = parser.parse_args(argv)
    if (args.action == "phase") != (args.phase is not None):
        parser.error("Only phase accepts exactly one declared phase")
    if args.action == "status":
        current = state()
        return c.emit({"phases": {p: "CURRENT" if (OUT / "parent-snapshot.json").exists() and current_phase(p, current)
                                 else "STALE" if current["phases"].get(p, {}).get("status") in OK
                                 else current["phases"].get(p, {}).get("status", "PENDING") for p in PHASES},
                       "directories": {p: r["directory"] for p, r in current["phases"].items()},
                       "wall_seconds": current["wall_seconds"], "next": c.read(OUT / "next-phase-plan.json") if (OUT / "next-phase-plan.json").exists() else None})
    with locked():
        current = state()
        recover_interruption(current)
        if args.action == "check":
            folder = OUT / "checks" / f"attempt-{len(list((OUT/'checks').glob('attempt-*')))+1:03d}"
            folder.mkdir(parents=True, exist_ok=False)
            try:
                run = command([sys.executable, "-m", "pytest", "tests/prospectus/test_evidence_continuation.py", "-q",
                               "tests/prospectus/test_continuation_control.py",
                               "tests/prospectus/test_loss_absorption_repair.py",
                               "--junitxml="+str(folder / "tests.xml")], folder / "tests.log", timeout=180)
                result = {"status": "PASS", "command": run}
            except Exception as exc:
                result = {"status": "FAILED", "reason": str(exc)}
            c.write(folder / "result.json", {**result, "method": method(), "at": c.now()})
            return c.emit({**result, "directory": c.relative(folder)})
        verify_parent()
        if args.action == "review-template":
            return c.emit(review_template(current))
        if args.action == "verify":
            return c.emit(verify(current))
        for phase in PHASES if args.action == "run" else (args.phase,):
            if args.action == "run" and any(not current_phase(p, current) for p in DEPENDENCIES[phase]):
                continue
            item = run_phase(phase, current)
            if item["status"] not in OK and args.action == "phase":
                break
        complete = all(current_phase(p, current) for p in PHASES)
        return c.emit({"status": "COMPLETE_WITH_QUALIFICATIONS" if complete else "ACTION_REQUIRED",
                       "next": refresh(current)})
