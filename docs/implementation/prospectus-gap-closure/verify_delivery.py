"""Verify the preserved gap-campaign delivery; no retrievals or native reruns."""
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
DATA = ROOT / "docs/prospectus/gap-closure"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus.common import digest
from legalmath.prospectus import source_obligations


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    started = time.monotonic()
    artifact_checks = 0
    manifests = {}
    for path in sorted(OUT.glob("**/run-manifest.json")):
        manifest = read(path)
        for relative, expected in manifest.get("artifacts", {}).items():
            require(sha(path.parent / relative) == expected,
                    f"Changed execution artifact: {path.parent / relative}")
            artifact_checks += 1
        manifests[str(path.relative_to(OUT))] = {
            "sha256": sha(path), "status": manifest["status"]}

    final_stages = ["focused/attempt-008", "regression/attempt-003",
                    "corpus/attempt-003", "fresh/attempt-003",
                    "integration/attempt-003", "delivery/attempt-003"]
    method_differences = {}
    for relative in final_stages:
        manifest = read(OUT / relative / "run-manifest.json")
        require(manifest["status"] == "PASS", f"Final stage did not pass: {relative}")
        differences = [p for p, expected in manifest["source_hashes"].items()
                       if sha(ROOT / p) != expected]
        allowed = [] if relative.startswith("delivery/") else ["scripts/prospectus_gap_report.py"]
        require(differences == allowed, f"Unexpected method drift: {relative}: {differences}")
        method_differences[relative] = differences

    test_counts = {}
    for stage, expected in [("focused/attempt-008", 498), ("regression/attempt-003", 734)]:
        suites = list(ET.parse(OUT / stage / "tests.xml").getroot().iter("testsuite"))
        require(sum(int(s.get("tests", 0)) for s in suites) == expected, stage)
        require(all(int(s.get(k, 0)) == 0 for s in suites for k in ("errors", "failures", "skipped")), stage)
        test_counts[stage] = expected

    baseline = OUT / "baseline"
    for name, expected in read(baseline / "manifest.json")["files"].items():
        require(sha(baseline / name) == expected, f"Changed protected baseline: {name}")
        if name.startswith("results."):
            require(sha(ROOT / "docs/implementation/bond-loss-absorption-classification" / name) == expected,
                    f"Changed prior published report: {name}")

    freeze_checks = {}
    for folder in sorted((OUT / "freezes").glob("candidate-*")):
        freeze = read(folder / "freeze.json")
        with ZipFile(folder / "method.zip") as archive:
            require(set(archive.namelist()) == set(freeze["files"]), f"Freeze members: {folder}")
            for name, expected in freeze["files"].items():
                require(hashlib.sha256(archive.read(name)).hexdigest() == expected, f"Freeze bytes: {name}")
                if folder.name == "candidate-002":
                    require(sha(ROOT / name) == expected, f"Final candidate changed: {name}")
        freeze_checks[folder.name] = {"files": len(freeze["files"]), "manifest_sha256": sha(folder / "freeze.json"),
                                     "archive_sha256": sha(folder / "method.zip")}

    inventory = read(DATA / "final-inventory.json")
    documents = inventory["documents"]
    require(len(documents) == 42 and len(inventory["issues"]) == 32, "Final inventory size")
    for key, doc in documents.items():
        require(sha(ROOT / doc["original"]) == doc["sha256"], f"Original source changed: {key}")
        require(sha(ROOT / doc["text"]) == doc["text_sha256"], f"Extracted source changed: {key}")
    require(sum(d["pages"] for d in documents.values()) == 3780, "Selected page count")

    delivery = OUT / "delivery/attempt-003"
    report = read(delivery / "results.json")
    rows = report["results"]
    current_by_id = {r["id"]: r for r in rows}
    require(len(current_by_id) == 32, "Missing or duplicate report row")
    require(report["counts"] == {"yes": 16, "no": 16, "unresolved": 0}, "Reported counts")
    require(sum(r["answer"] is True for r in rows) == 16 and sum(r["answer"] is False for r in rows) == 16,
            "Actual row counts")
    require(report["legal_accuracy"] == "NOT_ESTABLISHED", "Lost legal-accuracy qualification")
    final_rows = read(OUT / "corpus/attempt-003/run/classification.json")["results"]
    final_rows += read(OUT / "fresh/attempt-003/run/classification.json")["results"]
    require(rows == final_rows, "Delivery differs from final corpus and exposed replay")
    require(rows == read(OUT / "integration/attempt-003/classification.json")["results"],
            "Delivery and bank integration classify different rows")
    old = read(baseline / "results.json")["results"]
    changes = [{"id": r["id"], "before": r["answer"], "after": current_by_id[r["id"]]["answer"]}
               for r in old if r["answer"] != current_by_id[r["id"]]["answer"]]
    require(changes == [{"id": "enel-senior-2028", "before": None, "after": False}], "Unexplained baseline change")
    with (delivery / "results.csv").open(newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    require([r["id"] for r in csv_rows] == [r["id"] for r in rows], "CSV row identities")
    for row, csv_row in zip(rows, csv_rows):
        require(csv_row["answer"] == str(row["answer"]) and csv_row["summary_reason"] == row["summary_reason"],
                f"CSV differs: {row['id']}")

    receipt_checks = []
    for issue in inventory["issues"]:
        row = current_by_id[issue["id"]]
        current = source_obligations.replay(row, issue, documents, ROOT)
        receipt_path = OUT / "integration/attempt-003/receipts" / (issue["id"] + ".json")
        receipt = read(receipt_path)
        hashed = dict(receipt)
        expected = hashed.pop("receipt_hash")
        require(digest(hashed) == expected, f"Bank receipt hash: {issue['id']}")
        require(receipt["feature"]["report_sha256"] == digest(current), f"Bank report identity: {issue['id']}")
        packet = source_obligations.build(current, issue, documents, ROOT,
                                          as_of=receipt["source_obligations"]["as_of"])
        require(packet == receipt["source_obligations"], f"Source/condition record changed: {issue['id']}")
        bank = receipt["bank_investigation"]
        require(len(bank["inventory"]) == 14 and not bank["may_execute_transaction"], f"Bank obligations: {issue['id']}")
        require(receipt["may_execute_transaction"] is False and
                receipt["feature_to_regulatory_scope"] == "NO_AUTOMATIC_IMPLICATION", f"Unauthorized inference: {issue['id']}")
        require((receipt["instrument_investigation"] is not None) == (issue["id"] == "ubs-sgd-at1-2024"),
                f"Transferred instrument calculation: {issue['id']}")
        receipt_checks.append({"id": issue["id"], "sha256": sha(receipt_path), "obligations": 14})

    native_cases = 0
    for rel, n, yes, no in [("corpus/attempt-003/run", 30, 14, 16), ("fresh/attempt-003/run", 2, 2, 0)]:
        summary = read(OUT / rel / "summary.json")
        require((summary["bonds"], summary["yes"], summary["no"], summary["unresolved"]) == (n, yes, no, 0), rel)
        require(summary["native"]["formal_lowering"] == "KERNEL_CHECKED", rel)
        require(summary["formal"]["finite_partial_conflict_states"] == 256, rel)
        require(len(summary["formal"]["detected_mutants"]) == 4, rel)
        require(all(o["result"] == "UNSAT" for o in summary["formal"]["formal_obligations"]), rel)
        native_cases += summary["native"]["executed_target_cases"]
    require(native_cases == 160, "Native execution count")

    acquisition = read(DATA / "acquisition-ledger.json")
    require(acquisition["requests"] == len(acquisition["receipts"]) == 40, "Retrieval denominator")
    require(acquisition["registered_new_cases"] == {"capital": 2, "corporate": 0}, "Challenge coverage")
    for relative in acquisition["receipts"]:
        receipt = read(ROOT / relative)
        path = ROOT / receipt["path"]
        actual = sha(path) if path.exists() else hashlib.sha256(b"").hexdigest()
        require(actual == receipt["sha256"], f"Changed acquisition response: {relative}")
    source_links = re.findall(r"\]\(([^)]+)\)", (delivery / "CASE-INDEX.md").read_text())
    require(all((delivery / link).is_file() for link in source_links), "Broken retained-source link")
    pdf = read(delivery / "pdf-manifest.json")
    require(sha(delivery / "results.pdf") == pdf["pdf_sha256"] and
            sha(delivery / "results.md") == pdf["source_sha256"], "PDF source binding")
    require(pdf["all_bond_titles_and_reasons_preserved"], "Missing PDF content")
    require(len(list(delivery.glob("page-*.png"))) == 8, "Rendered page count")

    result = {
        "status": "PASS", "at": datetime.now(timezone.utc).isoformat(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "command": [sys.executable, str(Path(__file__).relative_to(ROOT))],
        "environment": sys.executable, "cpu_gpu": "CPU only; CUDA_VISIBLE_DEVICES=-1; no GPU framework imported",
        "seeds": "N/A deterministic", "plan": "docs/plans/prospectus-gap-closure.md",
        "verifier_sha256": sha(Path(__file__)), "inventory_sha256": sha(DATA / "final-inventory.json"),
        "verified_artifact_hashes": artifact_checks, "historical_manifests": manifests,
        "final_stage_method_differences": method_differences,
        "method_difference_explanation": "Only report presentation changed after the final scientific checks; final delivery and candidate-002 bind it.",
        "test_counts": test_counts, "freezes": freeze_checks,
        "selected_originals": 42, "selected_pages_or_text_units": 3780,
        "rows_replayed": 32, "counts": report["counts"], "baseline_changes": changes,
        "bank_receipts": receipt_checks, "native_target_executions": native_cases,
        "acquisition_attempts": 40, "registered_new_cases": acquisition["registered_new_cases"],
        "post_repair_unseen_observations": 0,
        "pdf_sha256": pdf["pdf_sha256"], "pdf_pages": 8,
        "visual_review": "See G7-final-review.md; model inspection of all eight rendered pages, not human voice approval.",
        "wall_seconds": time.monotonic() - started,
        "limitations": ["Source/legal completeness is not established.", "No actual client, current authority or trade permission.",
                        "Fixture instrument labels are not evidence of product type.",
                        "Final inventory scope prose inherits the original 30-case description; its 32 per-issue records include two exposed replays."]}
    path = OUT / "delivery-verification.json"
    with path.open("x") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "artifact_hashes": artifact_checks, "rows_replayed": 32,
                      "verification": str(path.relative_to(ROOT)), "wall_seconds": result["wall_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
