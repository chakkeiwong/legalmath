"""Fixed local difficulty study; diagnostic outputs never admit legal sources."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import signal
import sys
import tempfile
import time
import zipfile

from legalmath.prospectus import master_control as c, evidence_closure as ec
from legalmath.prospectus import closure_phases as phases, closure_recovery as recovery
from legalmath.prospectus.closure_sources import require
from legalmath.prospectus.loss_absorption_reader import analyze_issue, load_document

DATA = c.ROOT / "docs/prospectus/difficulty-2026-10-04"
OUT = c.ROOT / "docs/implementation/prospectus-difficulty-2026-10-04"
PLAN = c.ROOT / "docs/plans/prospectus-difficulty-study-2026-10-04.md"
MAX_REQUESTS = 45


def method():
    result = ec.method()
    for path in (Path(__file__).resolve(), PLAN):
        result[c.relative(path)] = c.sha(path)
    return result


def validate_frozen(expected, actual):
    require(expected == actual, "Frozen study method changed; do not retune this cohort")


def frozen():
    record = c.read(DATA / "freeze.json")
    validate_frozen(record["method"], method())
    require(c.sha(DATA / "method.zip") == record["archive_sha256"], "Frozen archive changed")
    return record


def freeze():
    if (DATA / "freeze.json").exists():
        return {"status": "FROZEN", **frozen()}
    require(not (DATA / "sources.json").exists(), "Cannot freeze after sources were opened")
    ec.preserve()
    DATA.mkdir(parents=True, exist_ok=True)
    files = method()
    with zipfile.ZipFile(DATA / "method.zip", "x", zipfile.ZIP_DEFLATED) as stream:
        for path in files:
            stream.write(c.ROOT / path, path)
    # All previously retained originals are exposed, including unused sources.
    exposed = {}
    for path in (c.ROOT / "docs/prospectus").rglob("*"):
        if path.is_file() and not path.is_relative_to(DATA) and (
                path.suffix.lower() == ".pdf" or path.name in {"response.bin", "response.body"}):
            exposed[c.relative(path)] = c.sha(path)
    value = {"at": c.now(), "method": files, "archive_sha256": c.sha(DATA / "method.zip"),
             "requests_at_start": len(phases.all_requests()), "max_additional_requests": MAX_REQUESTS,
             "exposed_sources": exposed, "scope": "Diagnostic development study, not independent S6 validation"}
    c.write(DATA / "freeze.json", value, exclusive=True)
    return {"status": "FROZEN", "at": value["at"], "requests_at_start": value["requests_at_start"],
            "exposed_sources": len(exposed), "files": len(files)}


def fetch():
    record = frozen()
    queue = c.read(DATA / "public-queue.json")
    require(isinstance(queue, list) and len(queue) <= MAX_REQUESTS, "Study request cap")
    require(len({r["key"] for r in queue}) == len(queue), "Duplicate study request key")
    results = []
    for row in queue:
        require(set(row) == {"key", "url", "gap", "review"} and row["key"].startswith("hard-") and row["review"],
                "Invalid reviewed study request")
        prior = [p for p in phases.all_requests() if c.read(p).get("key") == row["key"]]
        if prior:
            path = prior[-1]
            require(c.read(path)["url"] == row["url"], "Queue URL changed for retained key")
        else:
            require(len(phases.all_requests()) - record["requests_at_start"] < MAX_REQUESTS, "Study budget exhausted")
            path = phases.acquire(row)
        results.append(recovery.prepare(path))
    c.write(DATA / "sources.json", results)
    return {"status": "RETAINED", "records": len(results),
            "pdfs": sum(r.get("kind") == "pdf" and "document" in r for r in results),
            "requests_total": len(phases.all_requests()),
            "remaining_global": ec.policy()["max_http_requests_including_continuation"] - len(phases.all_requests())}


def inspect(subject=None, pages=None):
    frozen()
    records = c.read(DATA / "sources.json")
    if subject:
        record = next(r for r in records if r["key"] == subject)
        doc = load_document(record["document"], c.ROOT)
        numbers = [int(p) for p in (pages or "1").split(",")]
        require(1 <= len(numbers) <= 6 and all(1 <= p <= len(doc["pages"]) for p in numbers), "One to six valid pages")
        return {"key": subject, "pages": [doc["pages"][p-1] for p in numbers]}
    result = []
    for row in records:
        if row.get("kind") != "pdf" or "document" not in row:
            continue
        doc = load_document(row["document"], c.ROOT)
        selected = []
        for page in doc["pages"]:
            match = re.search(r"(?i)(?:terms and conditions|conditions of the|loss absorption|write[ -]?down|conversion upon|trigger event|interest deferral|non.viability)", page["text"])
            if match and len(selected) < 14:
                selected.append({"page": page["page"], "excerpt": page["text"][max(0, match.start()-60):match.end()+250]})
        result.append({"key": row["key"], "pages": row["document"]["pages"],
                       "source_sha256": row["document"]["sha256"], "title_excerpt": doc["pages"][0]["text"][:5000],
                       "candidate_pages": selected})
    c.write(OUT / "source-inspection.json", result)
    return result


def checked_cases(cases):
    require(isinstance(cases, list) and 20 <= len(cases) <= 30, "Study needs 20-30 selected cases")
    require(len({x["id"] for x in cases}) == len(cases), "Duplicate case identity")
    require(all(x.get("review") and x.get("difficulty") and x.get("issuer") for x in cases), "Missing source review")
    return cases


def summarize(rows):
    return {"selected": len(rows), "statuses": dict(Counter(r["status"] for r in rows)),
            "answers": dict(Counter(str(r.get("answer")) for r in rows)),
            "unresolved_clauses": sum(r.get("unresolved_clauses", 0) for r in rows)}


def analyze():
    record = frozen()
    bundle = c.read(DATA / "cases.json")
    cases = checked_cases(bundle["cases"])
    sources = {r["key"]: r for r in c.read(DATA / "sources.json")}
    binding = c.digest({"cases": bundle, "sources": sources, "method": record["method"]})
    target = OUT / "run-001"
    if target.exists():
        manifest = c.read(target / "manifest.json")
        require(manifest["binding"] == binding, "Frozen case/source selection changed")
        for path, value in manifest["outputs"].items():
            require(c.sha(target / path) == value, "Retained result changed")
        return c.read(target / "summary.json")
    OUT.mkdir(parents=True, exist_ok=True)
    selection = DATA / "selection-freeze.json"
    if selection.exists():
        require(c.read(selection)["binding"] == binding, "Selected cohort changed after freeze")
    else:
        c.write(selection, {"binding": binding, "at": c.now(), "case_ids": [x["id"] for x in cases]}, exclusive=True)
    started, began = time.monotonic(), c.now()
    rows, hashes = [], set()
    with tempfile.TemporaryDirectory(prefix=".study-", dir=OUT) as folder:
        staging = Path(folder)
        for case in cases:
            row = {"id": case["id"], "issuer": case["issuer"], "difficulty": case["difficulty"],
                   "source_complete": False, "independent_adjudication": False, "issue_answer": None}
            source = sources.get(case.get("source_key"))
            if not source or "document" not in source or source.get("kind") != "pdf":
                rows.append({**row, "status": "UNAVAILABLE", "reason": "Selected PDF unavailable"})
                continue
            meta = source["document"]
            require(meta["sha256"] == case["source_sha256"], "Case source changed")
            require(meta["sha256"] not in hashes, "Duplicate source cannot count as another case")
            require(meta["sha256"] not in record["exposed_sources"].values(), "Previously exposed PDF")
            hashes.add(meta["sha256"])
            document = load_document(meta, c.ROOT)
            require(all(anchor["quote"] in document["pages"][anchor["page"]-1]["text"]
                        for anchor in case["review"]["anchors"]), "Review anchor absent")
            require(case["review"]["anchors"], "Identity/source anchors required")
            selection_row = {"id": meta["id"], "operative_pages": case.get("operative_pages", [[1, meta["pages"]]]),
                             "scope_basis": case.get("scope_basis", "Whole-document diagnostic stress input; legal applicability not established")}
            if case.get("shelf_pages"):
                selection_row["shelf_pages"] = case["shelf_pages"]
            issue = {k: case[k] for k in ("id", "issuer", "title", "identifiers") if k in case}
            issue.update(security_type=case.get("security_type", "debt"), documents=[selection_row])
            try:
                def expired(*unused):
                    raise TimeoutError("Case exceeded 60-second diagnostic limit")
                prior = signal.signal(signal.SIGALRM, expired)
                signal.alarm(60)
                try:
                    result = analyze_issue(issue, {meta["id"]: meta}, c.ROOT)
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, prior)
                c.write(staging / (case["id"] + ".json"), result)
                unresolved = [e for e in result["evidence"] if e["disposition"].startswith("unresolved")]
                supporting = [e for e in result["evidence"] if e["id"] in result["derivation"]["evidence_ids"]]
                row.update(status="ABSTAIN" if result["answer"] is None else "CONDITIONAL_READING",
                           answer=result["answer"], facts=result["facts"], unresolved_clauses=len(unresolved),
                           unresolved_dispositions=dict(Counter(e["disposition"] for e in unresolved)),
                           open_issues=result["open_issues"], evidence=[{"page": e["page"], "kind": e["kind"],
                           "quote": e["quote"], "origin": e.get("origin")} for e in supporting[:3]])
            except Exception as exc:
                row.update(status="ENGINE_ERROR", reason=type(exc).__name__ + ": " + str(exc))
            rows.append(row)
        summary = {**summarize(rows), "cases": rows, "population_accuracy": "NOT_ESTABLISHED",
                   "may_execute_transaction": False, "method_changed": False}
        c.write(staging / "summary.json", summary)
        outputs = {p.name: c.sha(p) for p in staging.iterdir() if p.is_file()}
        c.write(staging / "manifest.json", {"binding": binding, "started_at": began, "finished_at": c.now(),
            "wall_seconds": time.monotonic()-started, "command": " ".join(sys.argv), "python": sys.version,
            "cpu_only": True, "gpu": "intentionally hidden", "seeds": "N/A deterministic",
            "plan": c.relative(PLAN), "outputs": outputs, "source_admissions": 0})
        staging.rename(target)
    return {**summarize(rows), "directory": c.relative(target)}


def verify():
    record = frozen()
    ec.preserve()
    for item in c.read(DATA / "sources.json"):
        for path, value in item["files"].items():
            require(c.sha(c.ROOT / path) == value, "Recovered evidence changed")
        if "receipt" in item:
            receipt = c.read(c.ROOT / item["receipt"])
            require(c.sha(c.ROOT / item["receipt"]) == item["binding"]["receipt_sha256"], "Receipt changed")
            if receipt.get("original"):
                require(c.sha(c.ROOT / receipt["original"]) == receipt["sha256"], "Source changed")
    result = analyze()
    return {"status": "PASS", "result": {k: v for k,v in result.items() if k != "cases"},
            "additional_requests": len(phases.all_requests())-record["requests_at_start"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "fetch", "inspect", "analyze", "verify", "check"))
    parser.add_argument("subject", nargs="?")
    parser.add_argument("pages", nargs="?")
    args = parser.parse_args(argv)
    require(args.action == "inspect" or (args.subject is None and args.pages is None), "No extra arguments")
    OUT.mkdir(parents=True, exist_ok=True)
    with ec.locked():
        if args.action == "check":
            value = ec.command([sys.executable, "-m", "pytest", "tests/prospectus/test_difficulty_study.py", "-q"],
                               OUT / "tests.log", timeout=60)
        elif args.action == "inspect":
            value = inspect(args.subject, args.pages)
        else:
            value = globals()[args.action]()
        return c.emit(value)
