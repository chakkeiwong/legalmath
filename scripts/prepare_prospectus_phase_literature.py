"""Retain bounded literature extractions and exact source identities for the phase audit."""
from pathlib import Path
import hashlib
import json
import os
import sys
import tarfile
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/implementation/prospectus-phase-roots-2026-10-06/literature"
RA = Path("/home/chakwong/python/ResearchAssistant")
sys.path.insert(0, str(RA / "src"))
from research_assistant.ingest.pdf_extract import extract_pdf_text
from research_assistant.ingest.parser_command import ParserExecutionPolicy

SOURCES = [
    ("docling", "https://arxiv.org/pdf/2408.09869", "docling.pdf"),
    ("build-systems", "https://www.microsoft.com/en-us/research/wp-content/uploads/2018/03/build-systems.pdf", "build-systems.pdf"),
    ("quantlib-schedule", "https://raw.githubusercontent.com/lballabio/QuantLib/v1.38/ql/time/schedule.cpp", "quantlib-schedule.cpp"),
    ("build-models", "https://hackage.haskell.org/package/build-1.0/build-1.0.tar.gz", "build-1.0.tar.gz"),
    ("docling-readingorder", "https://raw.githubusercontent.com/docling-project/docling/570f956792fcfe8e51bde0f4a79a2ddabc1a061a/docling/models/stages/reading_order/readingorder_model.py", "docling-readingorder.py"),
]


def main():
    rows = []
    for key, url, file in SOURCES:
        path = OUT / file
        raw = path.read_bytes()
        row = {"id": key, "url": url, "path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "retrieval_method": "curl HTTPS public source; retained exact bytes",
            "retrieval_date": "2026-10-06", "authenticity": "HTTPS endpoint only"}
        if path.suffix == ".pdf":
            if not raw.startswith(b"%PDF-"):
                raise ValueError("Not a PDF: " + key)
            text = extract_pdf_text(path, policy=ParserExecutionPolicy(timeout_seconds=60))
            target = OUT / (key + ".txt")
            target.write_text(text)
            row.update(text_path=str(target.relative_to(ROOT)),
                text_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                extraction="ResearchAssistant.extract_pdf_text -> pdftotext")
        if file == "build-1.0.tar.gz":
            # Read named regular members only; never unpack paths from the archive.
            names = ("src/Build/Trace.hs", "src/Build/Rebuilder.hs",
                     "src/Build/Task.hs", "src/Build/Scheduler.hs",
                     "test/Main.hs", "test/Spreadsheet.hs", "LICENSE")
            excerpts = []
            with tarfile.open(path, "r:gz") as archive:
                for name in names:
                    member = archive.getmember("build-1.0/" + name)
                    if not member.isfile() or member.size > 1000000:
                        raise ValueError("Unexpected archive member")
                    data = archive.extractfile(member).read()
                    target = OUT / "build-models" / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    excerpts.append({"path": str(target.relative_to(ROOT)),
                                     "sha256": hashlib.sha256(data).hexdigest()})
            row["inspected_excerpts"] = excerpts
        rows.append(row)
    (OUT / "new-source-manifest.json").write_text(json.dumps({
        "sources": rows, "new_public_retrievals": len(rows),
        "prospectus_retrieval_ledger": "Unmodified 188/212; this literature survey recorded separately",
        "models_executed": False, "gpu": "hidden; CPU only",
        "research_assistant_parser": str(RA / "src/research_assistant/ingest/pdf_extract.py")
    }, indent=2) + "\n")
    print(json.dumps({"sources": len(rows), "pdfs_extracted": 2, "output": str(OUT)}))


if __name__ == "__main__":
    main()
