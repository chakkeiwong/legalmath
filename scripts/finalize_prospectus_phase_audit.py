"""Verify phase-study evidence bindings and render the revised manuscript pages."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
import fitz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/implementation/prospectus-phase-roots-2026-10-06"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    start = time.monotonic()
    probe = json.loads((OUT / "probe-manifest.json").read_text())
    bindings = dict(probe["code_bindings"])
    bindings.update(probe["output_bindings"])
    bindings["scripts/audit_prospectus_phase_roots.py"] = probe["script_sha256"]
    reference = json.loads((OUT / "reference-manifest.json").read_text())
    bindings.update(reference["files"])
    bindings[reference["result"]] = reference["result_sha256"]
    sources = json.loads((OUT / "literature/new-source-manifest.json").read_text())
    for row in sources["sources"]:
        bindings[row["path"]] = row["sha256"]
        if row.get("text_path"):
            bindings[row["text_path"]] = row["text_sha256"]
        for excerpt in row.get("inspected_excerpts", []):
            bindings[excerpt["path"]] = excerpt["sha256"]
    changed = [name for name, expected in bindings.items() if sha(ROOT / name) != expected]
    if changed:
        raise ValueError("Changed evidence binding: " + ", ".join(changed))
    production = subprocess.check_output(["git", "diff", "7fd9c4e864c22da1e8a5df8ed7bc5c59331eb25f",
                                         "--", "src", "tests/prospectus_successor",
                                         "scripts/prospectus_delivery.py"], cwd=ROOT, text=True)
    if production:
        raise ValueError("Production implementation changed during study")

    documents = list(OUT.glob("*.md")) + [ROOT / "docs/plans/prospectus-phase-repair-2026-10-06.md"]
    links = 0
    for document in documents:
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            target = re.sub(r":\d+$", "", target.split("#")[0])
            if not (document.parent / target).resolve().exists():
                raise ValueError("Broken local link: " + str(document) + " -> " + target)
            links += 1

    pdf_path = ROOT / "docs/monograph/monograph.pdf"
    pages = []
    with fitz.open(pdf_path) as book:
        candidates = set()
        for i, page in enumerate(book):
            if ("What the executed service establishes" in page.get_text()
                    or "a subsequent code" in page.get_text()
                    or "Occurrence-specific source intervals" in page.get_text()):
                # Exclude a possible table-of-contents hit.
                if "43,626" in page.get_text() or i > 80:
                    candidates.update(range(max(0, i-1), min(len(book), i+2)))
        if not candidates:
            raise ValueError("Revised manuscript passage not found")
        image_dir = OUT / "rendered"
        image_dir.mkdir(exist_ok=True)
        for i in sorted(candidates):
            path = image_dir / ("monograph-%03d.png" % (i + 1))
            book[i].get_pixmap(dpi=120).save(path)
            pages.append({"page": i + 1, "path": str(path.relative_to(ROOT)), "sha256": sha(path)})
        page_count = len(book)
    doc_check = json.loads((ROOT / "docs/monograph/review/reader-facing/document-check.json").read_text())
    if doc_check.get("status") != "PASS":
        raise ValueError("Document build/check did not pass")
    paths = documents + [ROOT / name for name in [
        "scripts/audit_prospectus_phase_roots.py", "scripts/prepare_prospectus_phase_literature.py",
        "scripts/prospectus_phase_reference.py", "scripts/check_prospectus_phase_reference.py",
        "scripts/finalize_prospectus_phase_audit.py", "docs/plans/prospectus-phase-roots-2026-10-06.md",
        "docs/monograph/chapters/02f-prospectus-execution.tex", "docs/monograph/chapters/02f-prospectus-delivery.tex",
        "docs/monograph/monograph.pdf",
        "docs/monograph/technical-companion.pdf", "docs/monograph/process-guide.pdf"]]
    record = {"status": "PASS", "baseline_commit": "7fd9c4e864c22da1e8a5df8ed7bc5c59331eb25f",
              "commands": ["python3 -m scripts.build_reader_facing_monograph",
                           "python3 -m scripts.finalize_prospectus_phase_audit"],
              "interpreter": sys.executable, "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1",
              "seeds": "N/A: deterministic document and evidence validation",
              "plan": "docs/plans/prospectus-phase-roots-2026-10-06.md",
              "result": str((OUT / "final-verification.json").relative_to(ROOT)),
              "data": "probe/reference/literature manifests and rebuilt manuscript",
              "wall_seconds_verification": time.monotonic() - start,
              "verified_evidence_bindings": len(bindings), "local_links_checked": links,
              "production_unchanged": True, "monograph_pages": page_count,
              "rendered_pages": pages,
              "files": {str(path.relative_to(ROOT)): sha(path) for path in paths},
              "legal_acceptance": "NOT_ESTABLISHED",
              "visual_review": "See MANUSCRIPT-REVIEW.md; image generation alone is not visual acceptance"}
    (OUT / "final-verification.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({key: record[key] for key in
                      ("status", "verified_evidence_bindings", "local_links_checked", "production_unchanged", "monograph_pages")}))
    print(json.dumps({"rendered_pages": [r["page"] for r in pages]}))


if __name__ == "__main__":
    main()
