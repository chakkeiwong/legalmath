"""Fixed CPU PyMuPDF OCR worker; stdin contains a bounded validated profile."""
import hashlib
import json
import os
from pathlib import Path
import sys
import importlib.metadata

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["OMP_THREAD_LIMIT"] = "1"


def main():
    import fitz
    distribution = importlib.metadata.distribution('PyMuPDF')
    bindings = {str(p): hashlib.sha256(distribution.locate_file(p).read_bytes()).hexdigest()
                for p in distribution.files if str(p).endswith(('.py', '.so', 'METADATA'))}
    spec = json.load(sys.stdin)
    document = fitz.open(spec["source"])
    if not 0 < len(document) <= spec["max_pages"]:
        raise ValueError("Scan page count exceeds declared profile")
    rows = []
    for number, page in enumerate(document, 1):
        pix = page.get_pixmap(dpi=spec["dpi"], colorspace=fitz.csRGB)
        raw_image = pix.tobytes("png")
        scanned = fitz.open(stream=pix.pdfocr_tobytes(language=spec["language"],
                            tessdata=spec["tessdata"], compress=True), filetype="pdf")
        text = scanned[0].get_text(sort=True)
        rows.append({"page": number, "text": text, "words": scanned[0].get_text("words"),
                     "image_sha256": hashlib.sha256(raw_image).hexdigest(),
                     "image_width": pix.width, "image_height": pix.height,
                     "disposition": "OCR_TEXT_REQUIRES_REVIEW" if text.strip() else "BLANK_OR_UNREAD_REQUIRES_REVIEW"})
    print(json.dumps({"source_sha256": hashlib.sha256(Path(spec["source"]).read_bytes()).hexdigest(),
        "page_count": len(document), "pages": rows,
        "runtime": {"dpi": spec["dpi"], "language": spec["language"], "pymupdf": fitz.VersionBind,
                    "mupdf": fitz.VersionFitz, "distribution_files": bindings,
                    "gpu": "intentionally hidden"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
