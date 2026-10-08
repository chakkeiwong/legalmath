"""Verify preserved sources, reader results, historical campaigns and document builds.

This local integrity check does not rerun the reader, acquire sources or adjudicate law.
"""
from collections import Counter
from pathlib import Path
import difflib
import fcntl
import json
import re
import sys
import time

from scripts import prospectus_corner_cases as c
from scripts import run_prospectus_corner_tests as reader

ROOT, DATA, OUT = c.ROOT, c.DATA, c.OUT
sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus import evidence_closure as closure


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bound(path, expected):
    path = Path(path)
    require(path.is_file(), "Missing file: " + str(path))
    require(c.j.sha(path) == expected, "Hash changed: " + str(path))


def bindings(base, mapping):
    require(bool(mapping), "Empty hash binding")
    for name, digest in mapping.items():
        bound(base / name, digest)
    return len(mapping)


def verify():
    started = c.j.now()
    tick = time.monotonic()
    result = {"status": "PASS", "started": started,
              "scope": "Local preservation and engineering checks; no legal accuracy claim"}
    result["reader"] = reader.verify()

    # Existing historical manifest must exist; do not create a replacement baseline.
    require((closure.OUT / "baseline.json").is_file(), "Historical baseline missing")
    result["historical_campaign"] = closure.preserve()

    prior = c.j.read(ROOT / "docs/prospectus/jurisdiction-2026-10-04/prior-24-pdf-index.json")
    require(len(prior["files"]) == 24, "Prior PDF count changed")
    for row in prior["files"]:
        bound(ROOT / row["pdf"], row["sha256"])
        bound(ROOT / row["original"], row["sha256"])
    result["prior_pdfs_unchanged"] = len(prior["files"])

    prior_run = ROOT / "docs/implementation/prospectus-difficulty-2026-10-04/run-001"
    prior_manifest = c.j.read(prior_run / "manifest.json")
    selection = c.j.read(ROOT / "docs/prospectus/difficulty-2026-10-04/selection-freeze.json")
    require(prior_manifest["binding"] == selection["binding"], "Prior run binding changed")
    result["prior_output_files_unchanged"] = bindings(prior_run, prior_manifest["outputs"])
    for name in ["docs/implementation/prospectus-jurisdiction-2026-10-04/document-baseline/manifest.json",
                 str((OUT / "baseline/manifest.json").relative_to(ROOT))]:
        for row in c.j.read(ROOT / name)["files"]:
            bound(ROOT / row["copy"], row["sha256"])

    source_index = c.j.read(DATA / "source-index.json")["sources"]
    queue = c.j.read(DATA / "public-queue.json")
    require(len({r["key"] for r in queue}) == len(queue), "Duplicate acquisition key")
    queued = {r["key"]: r for r in queue}
    all_receipts = [c.j.read(p) for p in c.j.receipts()]
    policy = c.j.read(DATA / "acquisition-policy.json")
    require(len(all_receipts) <= policy["global_ceiling"], "Request ceiling exceeded")
    require(policy["start_count"] == 112 and policy["global_ceiling"] == 212,
            "Unexpected request budget")
    sequences, receipt_file_count, policy_versions = [], 0, set()
    for row in source_index:
        bound(ROOT / row["original"], row["sha256"])
        bound(ROOT / row["receipt"], row["receipt_sha256"])
        if "text" in row:
            bound(ROOT / row["text"], row["text_sha256"])
        receipt = c.j.read(ROOT / row["receipt"])
        require(row["key"] == receipt["key"] and row["url"] == receipt["url"],
                "Source/receipt identity mismatch")
        require(row["url"] == queued[row["key"]]["url"], "Source/queue URL mismatch")
        require(row["sha256"] == receipt["sha256"], "Original/receipt digest mismatch")
        for name, digest in receipt.get("files", {}).items():
            bound(ROOT / name, digest)
            receipt_file_count += 1
        digest = receipt["acquisition_policy_sha256"]
        snapshot = DATA / "policy-snapshots" / (digest + ".json")
        bound(snapshot, digest)
        version = c.j.read(snapshot)
        require(version["global_ceiling"] == 212 and version["start_count"] == 112,
                "Unexpected receipt policy")
        policy_versions.add(digest)
        sequences.append(receipt["sequence"])
    require(sorted(sequences) == list(range(113, 113 + len(source_index))),
            "Extension request sequence has gaps")
    catalogue = c.j.read(OUT / "reviewed-catalogue.json")["sources"]
    require(len(catalogue) == len({r["sha256"] for r in catalogue}) == 30,
            "Substantive source count or uniqueness changed")
    require(not {r["sha256"] for r in catalogue} & {r["sha256"] for r in prior["files"]},
            "A substantive source duplicates the original study")
    result["sources"] = {
        "response_records": len(source_index), "substantive_documents": len(catalogue),
        "pdfs": sum(r["media"] == "pdf" for r in catalogue),
        "official_judgments_html": sum(r["media"] == "html" and r["role"] == "judgment"
                                       for r in catalogue),
        "roles": dict(Counter(r["role"] for r in catalogue)),
        "receipt_files_verified": receipt_file_count, "policy_versions": len(policy_versions)}
    result["requests"] = {
        "cumulative": len(all_receipts), "extension_used": len(all_receipts) - 112,
        "remaining": 212 - len(all_receipts), "ceiling": 212}

    # Compare source-bearing LaTeX tokens and preserve the full diff for human review.
    manuscript_rows, diff_parts, local_links = [], [], 0
    token_pattern = (
        r"\\(?:label|(?:[A-Za-z]*cite[A-Za-z]*))(?:\[[^\]]*\])?\{[^}]+\}"
        r"|\\href\{[^}]+\}"
        r"|\\begin\{(?:equation|align|gather|multline|displaymath)\*?\}"
        r".*?\\end\{(?:equation|align|gather|multline|displaymath)\*?\}"
        r"|\\\[.*?\\\]|\\\(.*?\\\)|(?<!\\)\$\$.*?(?<!\\)\$\$"
        r"|(?<!\\)\$(?!\$).*?(?<!\\)\$")
    for rel in ["docs/monograph/chapters/02e-prospectus-difficulty.tex",
                "docs/monograph/appendices/prospectus-difficulty.tex"]:
        old = (OUT / "baseline" / rel).read_text()
        new = (ROOT / rel).read_text()
        old_tokens = Counter(re.findall(token_pattern, old, re.S))
        new_tokens = Counter(re.findall(token_pattern, new, re.S))
        missing = old_tokens - new_tokens
        require(not missing, "Removed source/math tokens: " + repr(missing))
        diff_parts.extend(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                              fromfile="baseline/" + rel, tofile=rel))
        for target in re.findall(r"\\href\{([^}]+)\}", new):
            if target.startswith("../"):
                for folder in ["docs/monograph", "docs/proposal"]:
                    require((ROOT / folder / target).resolve().is_file(), "Broken link: " + target)
                local_links += 1
        manuscript_rows.append({"path": rel, "baseline_sha256": c.j.sha(OUT / "baseline" / rel),
                                "current_sha256": c.j.sha(ROOT / rel),
                                "removed_source_or_math_tokens": [], "baseline_tokens": sum(old_tokens.values()),
                                "current_tokens": sum(new_tokens.values())})
    diff_path = OUT / "manuscript-changes.diff"
    diff_path.write_text("".join(diff_parts))
    result["manuscript"] = {"files": manuscript_rows, "local_links_checked": local_links,
                            "diff": c.j.rel(diff_path), "diff_sha256": c.j.sha(diff_path),
                            "semantic_preservation": "See rendered-review.json; token check is not semantic adjudication"}

    build = c.j.read(OUT / "build-manifest.json")
    require(build["status"] == "PASS" and build["exit_code"] == 0, "Failed build")
    result["build_inputs_verified"] = bindings(ROOT, build["inputs"])
    result["build_outputs_verified"] = bindings(ROOT, build["outputs"])
    for source, alias in [("monograph", "monograph"), ("monograph", "proposal"),
                          ("technical-companion", "technical-companion")]:
        bound(ROOT / "docs/proposal" / (alias + ".pdf"),
              c.j.sha(ROOT / "docs/monograph" / (source + ".pdf")))
    rendered = c.j.read(OUT / "rendered-pages.json")
    review = c.j.read(OUT / "rendered-review.json")
    require(review["layout_status"] == "PASS" and review["human_prose_acceptance"] == "PENDING",
            "Unexpected rendered review status")
    result["rendered_documents"] = {}
    for name, record in rendered.items():
        bound(ROOT / "docs/monograph" / (name + ".pdf"), record["pdf_sha256"])
        require(record["pdf_sha256"] == review["documents"][name]["pdf_sha256"],
                "Review refers to a different PDF")
        require({p["page"] for p in record["pages"]} == set(review["documents"][name]["inspected_pages"]),
                "Unreviewed rendered page")
        images = {p["image"]: c.j.sha(ROOT / p["image"]) for p in record["pages"]}
        result["rendered_documents"][name] = {
            "pdf_sha256": record["pdf_sha256"], "page_count": record["page_count"],
            "pages_inspected": [p["page"] for p in record["pages"]], "images": images}

    findings = c.j.read(OUT / "regression-findings.json")
    require(findings["status"] == "GAPS_REPRODUCED" and findings["checked"] == findings["failed"] == 3,
            "Unexpected preserved regression result")
    require(all(r["status"] == "FAIL" and r["final_answer"] is None
                for r in findings["findings"]), "Unexpected clause or issue-level verdict")
    result["classification_screen"] = {"checked": 3, "failed": 3,
                                       "status": "GAPS_REPRODUCED", "engine_fix_applied": False}
    result["record_hashes"] = {}
    for path in [OUT / "REPORT.md", OUT / "RESET-MEMO.md", OUT / "rendered-review.json",
                 OUT / "regression-findings.json", OUT / "build-manifest.json",
                 OUT / "run-001/manifest.json", DATA / "source-index.json",
                 DATA / "acquisition-policy.json", Path(__file__),
                 ROOT / "docs/plans/prospectus-corner-repair-2026-10-04.md"]:
        require(path.is_file(), "Missing completion record: " + str(path))
        result["record_hashes"][c.j.rel(path)] = c.j.sha(path)
    result["finished"] = c.j.now()
    result["wall_seconds"] = round(time.monotonic() - tick, 3)
    result["command"] = "python3 -m scripts.verify_prospectus_corner_archive"
    result["python_executable"] = sys.executable
    result["legal_adjudication"] = "PENDING"
    return result


def main():
    with (ROOT / "docs/implementation/prospectus-evidence-closure/.lock").open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            result = verify()
        except Exception as exc:
            result = {"status": "FAIL", "at": c.j.now(), "error": type(exc).__name__ + ": " + str(exc)}
            c.j.write(OUT / "archive-verification.json", result)
            print(json.dumps(result, indent=2))
            raise SystemExit(1)
        c.j.write(OUT / "archive-verification.json", result)
        summary = {k: v for k, v in result.items()
                   if k not in {"rendered_documents", "record_hashes", "manuscript"}}
        summary["rendered_pages_inspected"] = sum(
            len(v["pages_inspected"]) for v in result["rendered_documents"].values())
        summary["local_links_checked"] = result["manuscript"]["local_links_checked"]
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
