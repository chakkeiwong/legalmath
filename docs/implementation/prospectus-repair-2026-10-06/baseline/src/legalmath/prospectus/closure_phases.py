"""Concrete closure work, preserving unmet source and human requirements."""
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urlparse
from xml.etree import ElementTree

from . import evidence_closure as ec
from . import master_control as c
from . import evidence_continuation as old
from . import closure_sources as sources


def inventory():
    baseline = c.read(old.BASE / "inventory.json")
    return sources.candidate_inventory(baseline, optional("source-inputs.json", {}),
                                       optional("admissions.json", []), c.ROOT, dates())


def baseline_rows():
    result = c.read(old.OUT / "phases/C1/attempt-005/result.json")
    return c.read(c.ROOT / result["classification"])["results"]


def rows(data=None):
    from .loss_absorption_reader import analyze_issue
    data = inventory() if data is None else data
    return [analyze_issue(issue, data["documents"], c.ROOT) for issue in data["issues"]]


def optional(name, default):
    path = ec.DATA / name
    return c.read(path) if path.exists() else default


def dates():
    return sources.assessment(**c.read(ec.DATA / "assessment.json"))


def checks(folder):
    result = ec.command([sys.executable, "-m", "pytest", "tests/prospectus", "tests/compliance", "-q",
                         "--junitxml=" + str(folder / "tests.xml")], folder / "tests.log")
    tree = ElementTree.parse(folder / "tests.xml")
    suites = tree.getroot().findall("testsuite")
    result["tests"] = sum(int(x.get("tests", "0")) for x in suites)
    result["failures"] = sum(int(x.get("failures", "0")) + int(x.get("errors", "0")) for x in suites)
    return result


def check():
    folder = ec.OUT / "checks" / f"attempt-{len(list((ec.OUT / 'checks').glob('attempt-*'))) + 1:03d}"
    folder.mkdir(parents=True)
    try:
        result = {"status": "PASS", "check": checks(folder)}
    except Exception as exc:
        result = {"status": "FAILED", "reason": str(exc)}
    c.write(folder / "result.json", {**result, "method": ec.method(), "at": c.now()})
    return {**result, "directory": c.relative(folder)}


def inspected_document(subject):
    data = inventory()
    if subject in data["documents"]:
        return data["documents"][subject]
    if subject == "hkma-ic1":
        receipt = next(c.read(p) for p in old.OUT.glob("phases/C3/attempt-*/requests/*/receipt.json")
                       if c.read(p).get("key") == "hkma-ic1-pdf")
        folder = ec.OUT / "inspection" / subject
        folder.mkdir(parents=True, exist_ok=True)
        source = c.ROOT / receipt["body"]
        if not (folder / "pages.json").exists():
            subprocess.run(["pdftotext", "-layout", str(source), str(folder / "text.txt")], check=True, timeout=30)
            parts = (folder / "text.txt").read_text().split("\f")
            if not parts[-1].strip():
                parts.pop()
            c.write(folder / "pages.json", {"source_sha256": receipt["sha256"],
                    "pages": [{"page": i + 1, "text": v} for i, v in enumerate(parts)]})
        return {"id": subject, "pages": len(c.read(folder / "pages.json")["pages"]),
                "original": c.relative(source), "sha256": receipt["sha256"], "text": c.relative(folder / "pages.json"),
                "text_sha256": c.sha(folder / "pages.json"), "url": receipt["url"], "preliminary": False}
    matches = [p for p in all_requests() if c.read(p)["key"] == subject]
    if matches:
        from .closure_recovery import prepare
        result = prepare(matches[-1])
        if "document" not in result:
            raise ValueError("No inspectable source: " + result["status"])
        return result["document"]
    raise ValueError("Unknown retained source: " + str(subject))


def inspect_source(action, subject, requested):
    if action == "rules":
        forms = [c.PREFIX + ["close", v] for v in ("run", "check", "verify", "status", "rules")]
        forms += [c.PREFIX + ["close", "phase", p] for p in ec.PHASES]
        forms += [c.PREFIX + ["close", "inspect", "inventory"], c.PREFIX + ["close", "render", "deutsche-at1-2025", "52,53,54"],
                  [".venv/bin/python", "scripts/edit_workspace_files.py", "/tmp/edits.json"]]
        results = []
        for argv in forms:
            output = subprocess.check_output(["codex", "execpolicy", "check", "--rules", "/home/chakwong/.codex/rules/default.rules", "--", *argv],
                                             text=True, timeout=30)
            check = json.loads(output)
            if check.get("decision") != "allow":
                raise ValueError("Saved approval does not cover " + " ".join(argv))
            results.append({"argv": argv, "decision": check["decision"]})
        c.write(ec.OUT / "approval-checks.json", {"forms": results, "at": c.now()})
        return {"status": "PASS", "approved_forms": len(results)}
    if subject == "inventory":
        return {"documents": inventory()["documents"], "issues": [{"id": i["id"], "documents": i["documents"]} for i in inventory()["issues"]]}
    if subject == "clauses":
        groups = defaultdict(list)
        for row in rows():
            for clause in row["evidence"]:
                if clause["disposition"].startswith("unresolved"):
                    groups[(clause["document"], clause["source_sha256"], clause["start"], clause["end"], clause["quote"])].append(row["id"])
        ordered = sorted(groups.items(), key=lambda item: (-len(item[1]), item[0][0], item[0][2]))
        return {"records": sum(len(v) for v in groups.values()), "unique_source_spans": len(groups),
                "largest_groups": [{"document": k[0], "start": k[2], "quote": k[4], "issues": v} for k, v in ordered[:15]]}
    meta = inspected_document(subject)
    from .loss_absorption_reader import load_document
    pages = load_document(meta, c.ROOT)["pages"]
    numbers = [int(p) for p in requested.split(",")] if requested else [1]
    if not 1 <= len(numbers) <= 6 or any(not 1 <= p <= len(pages) for p in numbers) or len(set(numbers)) != len(numbers):
        raise ValueError("One to six unique valid page numbers required")
    if action == "render":
        folder = ec.OUT / "inspection" / subject
        folder.mkdir(parents=True, exist_ok=True)
        rendered = []
        for page in numbers:
            stem = folder / f"page-{page:04d}"
            subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-scale-to", "1600", "-singlefile", "-png",
                            str(c.ROOT / meta["original"]), str(stem)], check=True, capture_output=True, timeout=45)
            rendered.append({"page": page, "path": c.relative(stem.with_suffix(".png")), "sha256": c.sha(stem.with_suffix(".png"))})
        return {"status": "RENDERED", "pages": rendered}
    return {"document": subject, "metadata": meta, "page_count": len(pages), "pages": [pages[p - 1] for p in numbers]}


def previous(current, phase):
    return c.read(c.ROOT / current["phases"][phase]["directory"] / "result.json")


def all_requests():
    return list(old.OUT.glob("phases/C3/attempt-*/requests/*/receipt.json")) + list((ec.DATA / "requests").glob("*/receipt.json"))


def acquire(row):
    policy = ec.policy()
    parsed = urlparse(row["url"])
    if (parsed.scheme != "https" or parsed.hostname not in policy["public_hosts"] or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError("URL outside reviewed public policy")
    if not re.fullmatch(r"[a-z0-9-]{1,70}", row["key"]):
        raise ValueError("Invalid queue key")
    receipts = [c.read(p) for p in all_requests()]
    if len(receipts) >= policy["max_http_requests_including_continuation"]:
        raise ValueError("Cumulative HTTP budget exhausted")
    if sum(r["url"] == row["url"] for r in receipts) >= policy["max_requests_per_url"]:
        raise ValueError("Per-URL HTTP budget exhausted")
    folder = ec.DATA / "requests" / f"{len(receipts) + 1:03d}-{row['key']}"
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / "receipt.json"
    result = {**row, "sequence": len(receipts) + 1, "at": c.now(), "status": "RESERVED"}
    c.write(path, result)
    try:
        # Public Apollo GET queries require explicit preflight intent (request 025).
        headers = ["--header", "Apollo-Require-Preflight: true"] if parsed.hostname == "graphqlaz.luxse.com" else []
        run = subprocess.run(["curl", "--silent", "--show-error", *headers, "--max-time", str(policy["max_http_seconds"]),
            "--max-filesize", str(policy["max_response_bytes"]), "--proto", "=https", "--dump-header", str(folder / "headers.txt"),
            "--output", str(folder / "response.bin"), "--write-out", "%{http_code}", row["url"]],
            capture_output=True, text=True, timeout=policy["max_http_seconds"] + 5)
        result.update(http_status=run.stdout[-3:], exit_code=run.returncode, error=run.stderr,
                      status="RETAINED" if run.returncode == 0 and run.stdout == "200" else "UNAVAILABLE")
        if (folder / "response.bin").exists():
            result.update(original=c.relative(folder / "response.bin"), sha256=c.sha(folder / "response.bin"),
                          bytes=(folder / "response.bin").stat().st_size)
    except subprocess.TimeoutExpired:
        result.update(status="TIMEOUT")
    for name in ("response.bin", "headers.txt"):
        artifact = folder / name
        if artifact.exists():
            result.setdefault("files", {})[c.relative(artifact)] = c.sha(artifact)
    c.write(path, result)
    return path


def source_work_orders(data):
    prefixes = {"G12": ("basf-",), "G13": ("enel-",), "G14": ("unilever-",), "G15": ("lloyds-",),
                "G16": ("seb-",), "G17": ("lvmh-", "bbva-")}
    return [{"gap": gap, "issuer": issuer, "needed": needed, "status": "OPEN",
             "issue_ids": sorted(i["id"] for i in data["issues"] if i["id"].startswith(prefixes[gap]))}
            for gap, issuer, needed in (
        ("G12", "BASF", "9 September 2022 base; 27 February 2023 supplement; selected German Option I"),
        ("G13", "Enel", "Authoritative executed agency/guarantee/covenant; amendment coverage"),
        ("G14", "Unilever", "Separate operative agreements and amendments"),
        ("G15", "Lloyds", "Authenticated primary SEC filing/exhibit"),
        ("G16", "SEB", "July 2023 fiscal agency agreement and relevant 2024 supplements"),
        ("G17", "LVMH/BBVA", "Complete applicable agreements, incorporation and amendments"))]


def execute(phase, folder, current):
    data = inventory()
    if phase == "S0":
        baseline = ec.preserve()
        tests = checks(folder)
        rule_checks = inspect_source("rules", None, None)
        return {"status": "PASS", "baseline": baseline, "checks": tests, "approvals": rule_checks,
                "repairs": ["Implemented independent closure executor with result-bound refresh and inherited request accounting"], "remaining": []}
    if phase == "S1":
        from . import source_obligations
        reports = []
        classified = rows(data)
        by_id = {r["id"]: r for r in classified}
        baseline = {r["id"]: r for r in baseline_rows()}
        c.write(folder / "inventory.json", data)
        c.write(folder / "classification.json", {"results": classified})
        c.write(folder / "classification-changes.json", [
            {"id": key, "before": baseline[key]["answer"], "after": row["answer"],
             "before_sha256": c.digest(baseline[key]), "after_sha256": c.digest(row)}
            for key, row in by_id.items() if baseline[key]["answer"] != row["answer"]])
        for issue in data["issues"]:
            packet = source_obligations.build(by_id[issue["id"]], issue, data["documents"], c.ROOT,
                                               as_of=dates()["effective_at"])
            result = sources.resolve(packet, issue, data["documents"], c.ROOT, dates(),
                                     optional("admissions.json", []), optional("decisions.json", []))
            c.write(folder / "issues" / (issue["id"] + ".json"), result)
            reports.append({"id": issue["id"], "open_references": result["open_references"],
                            "admitted_documents": len(result["admissions"]), "problems": result["admission_problems"]})
        c.write(folder / "summary.json", reports)
        return {"status": "QUALIFIED", "assessment": dates(), "issues": len(reports), "open_references": sum(r["open_references"] for r in reports),
                "repairs": ["Executed issue-bound admission/dependency resolver on every retained issue"],
                "remaining": ["G10/G11/G18: page, edition, applicability and amendment reviews must discharge actual references"]}
    if phase == "S2":
        receipts = []
        queue = optional("public-queue.json", [])
        sources.require(isinstance(queue, list) and len({r["key"] for r in queue}) == len(queue), "Duplicate public queue key")
        for row in queue:
            sources.require(set(row) == {"key", "url", "gap", "review"} and row["review"], "Incomplete public URL review")
            prior = [p for p in all_requests() if c.read(p).get("key") == row["key"] and c.read(p)["url"] == row["url"]]
            receipts.append(c.relative(prior[-1] if prior else acquire(row)))
        from .closure_reviews import source_work_review
        orders = source_work_review(source_work_orders(data), optional("source-work-reviews.json", []), data, current)
        c.write(folder / "source-work-orders.json", orders)
        c.write(folder / "requests.json", [{"path": p, "sha256": c.sha(c.ROOT / p), "receipt": c.read(c.ROOT / p)} for p in receipts])
        external = {p: c.sha(c.ROOT / p) for p in receipts}
        for p in receipts:
            receipt = c.read(c.ROOT / p)
            external.update(receipt.get("files", {}))
            if receipt.get("original"):
                external[receipt["original"]] = receipt["sha256"]
        from .closure_recovery import prepare
        recovered = [prepare(c.ROOT / path) for path in receipts]
        for record in recovered:
            external.update(record["files"])
        c.write(folder / "recovery-inspection.json", recovered)
        return {"status": "WAITING_EVIDENCE", "external_outputs": external, "requests_total": len(all_requests()),
                "recovered_pdf_candidates": [r["key"] for r in recovered if r.get("kind") == "pdf" and r["status"] == "EXTRACTED_UNREVIEWED"],
                "requests_remaining": ec.policy()["max_http_requests_including_continuation"] - len(all_requests()),
                "remaining": [r["gap"] + " " + r["issuer"] + ": " + r["needed"] for r in orders if r["status"] == "OPEN"],
                "retrieval_implies_admission": False}
    if phase == "S3":
        return integration(folder, data)
    if phase == "S4":
        from .closure_reviews import clause_audit
        return clause_audit(folder, data, rows(data), baseline_rows(), optional("clause-reviews.json", []))
    if phase == "S5":
        from .closure_mechanisms import execute_profiles
        return execute_profiles(folder, data, current)
    if phase == "S6":
        from .closure_reviews import challenge
        return challenge(folder, current, data)
    if phase == "S7":
        from .closure_reviews import human_review
        return human_review(folder, current, optional("human-review.json", None))
    raise ValueError("Unimplemented phase")


def integration(folder, data):
    from ..transaction import intake
    from ..transaction.evidence import Registry
    from . import feature_investigation, master_mechanisms, instrument_sources, instrument_investigation
    bank, store = intake.bootstrap(c.ROOT, folder / "bank", at=dates()["known_at"])
    bank["context"]["effective_at"] = dates()["effective_at"]
    registry = store.json(bank["registry_sha256"])
    # Preserve the predecessor's authority sources with their original observation dates.
    for entry in c.read(c.ROOT / "docs/prospectus/legal/manifest.json")["sources"]:
        if entry.get("use_for_applicable_law") is False:
            continue
        at = entry["retrieved_on"]
        if "T" not in at:
            at += "T00:00:00Z"
        raw, key = entry["key"] + ".legal-original", Path(entry["text_path"]).stem
        registry[raw] = intake.record(store.put((c.ROOT / entry["path"]).read_bytes()), "law", entry["source_url"], at,
                                      media_type="application/octet-stream")
        registry[key] = intake.record(store.put((c.ROOT / entry["text_path"]).read_bytes()), "law", entry["source_url"], at,
                                      dependencies=[raw])
    meta = inspected_document("hkma-ic1")
    receipt = next(c.read(p) for p in old.OUT.glob("phases/C3/attempt-*/requests/*/receipt.json") if c.read(p).get("key") == "hkma-ic1-pdf")
    observed = receipt.get("at") or receipt.get("started_at")
    registry["hkma-ic1-2017.original"] = sources.intake_record(store, (c.ROOT / meta["original"]).read_bytes(),
        kind="law", origin=meta["url"], observed_at=observed, provenance="official_retrieval")
    registry["hkma-ic1-2017"] = sources.intake_record(store, "\n\n".join(p["text"] for p in c.read(c.ROOT / meta["text"])["pages"]).encode(),
        kind="law", origin=meta["url"], observed_at=observed, provenance="official_retrieval", dependencies=["hkma-ic1-2017.original"])
    bank["registry_sha256"] = store.put(registry)
    authority = Registry(store, registry).check(["hkma-ic1-2017"], **dates())
    c.write(folder / "authority-registration.json", {"registry_sha256": bank["registry_sha256"], "check": authority,
                                                   "applicability": "NOT_ESTABLISHED", "retrieval_receipt": receipt})
    by_id = {r["id"]: r for r in rows(data)}
    reports, request_packet = [], []
    facts = optional("facts.json", {})
    sources.require(isinstance(facts, dict) and isinstance(facts.get("issues", {}), dict) and
                    set(facts.get("issues", {})) <= set(by_id), "Unknown issue in factual intake")
    for issue in data["issues"]:
        request = master_mechanisms.issue_context(bank, issue)
        request, assertions = sources.apply_fact_intake(request, store, c.ROOT, facts, issue["id"])
        specific = None
        if issue["id"] == "ubs-sgd-at1-2024":
            specific = {"profile": instrument_investigation.PROFILE,
                        "dossier_sha256": store.put(instrument_sources.dossier(c.ROOT)), "scenario_sha256": None}
        result = feature_investigation.investigate(by_id[issue["id"]], issue, data["documents"], c.ROOT, request, store,
                                                   product_assertions_sha256=assertions, instrument_request=specific)
        if specific is not None and result["instrument_investigation"] is None:
            raise ValueError("Existing UBS profile was not retained")
        expected = c.read(old.OUT / "phases/C2/attempt-005/receipts" / (issue["id"] + ".json"))
        if old.obligations(result) != old.obligations(expected) or result["may_execute_transaction"]:
            raise ValueError("Bank duty identity or permission regression")
        c.write(folder / "receipts" / (issue["id"] + ".json"), result)
        reports.append({"id": issue["id"], "obligations": old.obligations(result), "may_execute_transaction": False})
        request_packet.append({"id": issue["id"], "missing_product_facts": result["required_product_evidence"],
                               "requirements": master_mechanisms.input_requirements(issue, result["source_obligations"]["mechanisms"]),
                               "fields": ["source bytes", "origin", "observed_at", "effective_from/until", "fresh_until", "assertion pointer"]})
    c.write(folder / "summary.json", reports)
    c.write(folder / "fact-request-packet.json", request_packet)
    return {"status": "WAITING_EVIDENCE", "cases": len(reports), "authority_registered": "IC-1 V.3 2017",
            "bank_store": c.relative(folder / "bank/store"), "repairs": ["Registered recovered IC-1 with observed retrieval provenance; rebuilt exact bank duties"],
            "remaining": ["G19/G20: IC-1 related circulars and date-specific applicability; actual authority and event effectiveness",
                          "G24/G25/G26: independently evidenced times and actual product, event, client and bank facts absent"]}
