"""Audit the built proposal and retained papers; does not assess legal correctness."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

import fitz

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/proposal"
BASE = ROOT / ".localresources/proposal-v02-baseline"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sources = list(DOC.glob("*.tex"))
    text = "\n".join(p.read_text() for p in sources)
    bib = "\n".join(p.read_text() for p in DOC.glob("*.bib"))
    keys = re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib)
    citations = set()
    for group in re.findall(r"\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]+)\}", text):
        citations.update(k.strip() for k in group.split(","))
    labels = re.findall(r"\\label\{([^}]+)\}", text)
    refs = re.findall(r"\\(?:ref|eqref|autoref)\{([^}]+)\}", text)
    baseline_text = "\n".join(p.read_text() for p in BASE.glob("*.tex"))
    old_equations = set(re.findall(r"\\label\{(eq:[^}]+)\}", baseline_text))
    manifest = json.loads((ROOT / "docs/papers/manifest.json").read_text())
    paper_errors = []
    page_count = 0
    for record in manifest["papers"]:
        path = ROOT / "docs/papers" / record["filename"]
        try:
            assert path.read_bytes().startswith(b"%PDF-"), "not PDF bytes"
            assert digest(path) == record["sha256"], "digest mismatch"
            assert path.stat().st_size == record["bytes"], "size mismatch"
            with fitz.open(path) as paper:
                assert len(paper) == record["pages"], "page-count mismatch"
                assert len(paper) > 0 and not paper.needs_pass, "unreadable PDF"
                page_count += len(paper)
        except Exception as exc:
            paper_errors.append({"file": record["filename"], "error": str(exc)})
    baseline = json.loads((BASE / "baseline-manifest.json").read_text())
    baseline_errors = [name for name, sha in baseline["files"].items()
                       if digest(BASE / name) != sha]
    java_path = ROOT / "examples/java-dry-run/build/verification.json"
    java = json.loads(java_path.read_text())
    java_errors = [name for name, sha in java["sha256"].items()
                   if digest(ROOT / name) != sha]
    pdf = fitz.open(DOC / "proposal.pdf")
    outside = []
    for n, page in enumerate(pdf, 1):
        for word in page.get_text("words"):
            if not (page.rect + (-1, -1, 1, 1)).contains(fitz.Rect(word[:4])):
                outside.append({"page": n, "word": word[4]})
    log = (DOC / "proposal.log").read_text()
    warnings = [line for line in log.splitlines()
                if re.search(r"Warning|Overfull|Underfull|Missing character|^!|Infinite glue", line)]
    spec = json.loads(subprocess.check_output(
        [sys.executable, str(ROOT / "scripts/check_spec_pack.py")], text=True))
    required = {"catala2021", "arc2025", "slaw2024", "jurayj2026",
                "stipula2021", "stipulakey2025", "reachability2026"}
    record = {
        "checked_on": datetime.now(timezone.utc).date().isoformat(),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(), "proposal_version": "0.3",
        "proposal_pages": len(pdf), "proposal_sha256": digest(DOC / "proposal.pdf"),
        "bibliography_entries": len(keys), "distinct_cited_entries": len(citations),
        "missing_citation_keys": sorted(citations - set(keys)),
        "duplicate_bibliography_keys": [k for k, n in Counter(keys).items() if n > 1],
        "missing_reference_targets": sorted(set(refs) - set(labels)),
        "duplicate_labels": [k for k, n in Counter(labels).items() if n > 1],
        "protected_equation_labels_retained": sorted(old_equations & set(labels)),
        "protected_equation_labels_missing": sorted(old_equations - set(labels)),
        "protected_baseline_integrity_errors": baseline_errors,
        "latex_warning_or_overfull_underfull_lines": warnings,
        "words_outside_pdf_page": outside,
        "paper_PDFs_verified": len(manifest["papers"]) - len(paper_errors),
        "distinct_works": manifest["distinct_work_count"], "total_paper_pages": page_count,
        "paper_integrity_errors": paper_errors,
        "all_seven_requested_papers_present": required <= {p["id"] for p in manifest["papers"]},
        "specification_checks": spec,
        "java_demonstration": {k: v for k,v in java.items() if k != "sha256"},
        "java_artifact_integrity_errors": java_errors,
        "java_verification_record_sha256": digest(java_path),
        "source_files_sha256": {p.name: digest(p) for p in sorted(sources + list(DOC.glob("*.bib")))},
        "commands": ["latexmk -xelatex -interaction=nonstopmode -halt-on-error proposal.tex",
                     "python3 scripts/check_proposal.py", "python3 scripts/check_spec_pack.py"],
        "check_environment": {"python": sys.version.split()[0], "sqlite": sqlite3.sqlite_version,
                              "pymupdf": version("PyMuPDF"), "jsonschema": version("jsonschema"),
                              "accelerator_use": "none; document, schema and CPU Java checks only"},
        "render_review_directory": "/tmp/legalmath-proposal-v3-release-review",
        "render_review_record": "docs/proposal/review.md",
        "limits": ["32 decision cases and eleven consent histories executed for SPI-Demo1; complete RuleIR runtime remains unimplemented.",
                   "Java conformance and mutation tests are finite engineering checks, not legal approval or a compiler proof.",
                   "Published benchmarks and proofs were not reproduced.",
                   "Bounded literature coverage; unresolved leads are listed in docs/papers/coverage.md.",
                   "Author rendered-page review is separate from pending human acceptance and compliance adjudication."]}
    (DOC / "validation.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in record.items() if k != "source_files_sha256"}, indent=2))
    failure_keys = ["missing_citation_keys", "duplicate_bibliography_keys", "missing_reference_targets",
                    "duplicate_labels", "protected_equation_labels_missing", "protected_baseline_integrity_errors",
                    "paper_integrity_errors", "words_outside_pdf_page", "java_artifact_integrity_errors"]
    if any(record[k] for k in failure_keys) or not record["all_seven_requested_papers_present"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
