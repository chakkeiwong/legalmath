"""Build the reader-facing monograph and its linked reproduction companion."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "docs/monograph"
REVIEW = BOOK / "review/reader-facing"


def document_python():
    """Choose a Python that can run the PDF checker, and record that choice.

    The application environment intentionally does not require PyMuPDF.  The
    document-review environment does.  An explicit override keeps this script
    portable while avoiding a silent fallback to an unrelated interpreter.
    """
    candidates = []
    override = os.environ.get("LEGALMATH_DOC_PY")
    if override:
        candidates.append(Path(override))
    candidates.append(Path(sys.executable))
    for candidate in candidates:
        probe = subprocess.run([str(candidate), "-c", "import fitz"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               check=False)
        if probe.returncode == 0:
            return str(candidate)
    raise RuntimeError("document checker requires PyMuPDF; set LEGALMATH_DOC_PY")


def main():
    REVIEW.mkdir(parents=True, exist_ok=True)
    doc_python = document_python()
    # Each document imports the other's labels. The second pair settles both
    # directions after a fresh build or a changed split between documents.
    for document in ("technical-companion", "monograph") * 2:
        with (REVIEW / f"{document}-build.log").open("w") as log:
            subprocess.run(
                ["latexmk", "-xelatex", "-interaction=nonstopmode",
                 "-halt-on-error", "-cd", f"docs/monograph/{document}.tex"],
                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True,
            )
        print(f"Built {document}.pdf", flush=True)
    subprocess.run(
        [doc_python, "scripts/check_reader_facing_monograph.py"],
        cwd=ROOT, check=True,
    )
    shutil.copyfile(BOOK / "monograph.pdf", ROOT / "docs/proposal/proposal.pdf")
    shutil.copyfile(BOOK / "technical-companion.pdf", ROOT / "docs/proposal/technical-companion.pdf")
    # The companion's return links target monograph.pdf. Keep that target beside
    # the historical proposal alias as well.
    shutil.copyfile(BOOK / "monograph.pdf", ROOT / "docs/proposal/monograph.pdf")
    subprocess.run(
        [doc_python, "scripts/export_monograph_process_guide.py"],
        cwd=ROOT, check=True,
    )


if __name__ == "__main__":
    main()
