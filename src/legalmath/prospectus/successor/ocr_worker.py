"""Fixed CPU PyMuPDF OCR worker; stdin contains a bounded validated profile."""
import hashlib
import json
import os
from pathlib import Path
import sys
import importlib.metadata

if __package__:
    from .native_inputs import loaded_inputs
else:
    from native_inputs import loaded_inputs

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["OMP_THREAD_LIMIT"] = "1"


def main():
    import fitz
    distribution = importlib.metadata.distribution('PyMuPDF')
    bindings = {str(p): hashlib.sha256(distribution.locate_file(p).read_bytes()).hexdigest()
                for p in distribution.files if str(p).endswith(('.py', '.so', 'METADATA'))}
    spec = json.load(sys.stdin)
    document = fitz.open(spec["source"])
    selected = spec.get("selected_pages")
    if selected is None:
        if not 0 < len(document) <= spec["max_pages"]:
            raise ValueError("Scan page count exceeds declared profile")
        selected = list(range(1, len(document) + 1))
    else:
        if (len(document) != spec["page_count"] or not isinstance(selected, list) or
                not 1 <= len(selected) <= spec["max_pages"] <= 20 or
                any(type(p) is not int or not 1 <= p <= len(document) for p in selected) or
                selected != sorted(set(selected))):
            raise ValueError("Invalid original-page OCR selection")
        if hashlib.sha256(Path(spec["source"]).read_bytes()).hexdigest() != spec["source_sha256"]:
            raise ValueError("Original PDF bytes changed before OCR")
    rows = []
    for number in selected:
        page = document[number - 1]
        pix = page.get_pixmap(dpi=spec["dpi"], colorspace=fitz.csRGB)
        raw_image = pix.tobytes("png")
        row = {"page": number, "image_sha256": hashlib.sha256(raw_image).hexdigest(),
                     "image_width": pix.width, "image_height": pix.height}
        if not spec.get('verify_images_only'):
            scanned = fitz.open(stream=pix.pdfocr_tobytes(language=spec["language"],
                                tessdata=spec["tessdata"], compress=True), filetype="pdf")
            text = scanned[0].get_text(sort=True)
            row.update(text=text, words=scanned[0].get_text("words"),
                       disposition="OCR_TEXT_REQUIRES_REVIEW" if text.strip() else "BLANK_OR_UNREAD_REQUIRES_REVIEW")
            scanned.close()
        rows.append(row)
        if 'selected_pages' in spec:
            rows[-1].update(width_points=page.rect.width, height_points=page.rect.height)
    result = {"source_sha256": hashlib.sha256(Path(spec["source"]).read_bytes()).hexdigest(),
        "page_count": len(document), "pages": rows,
        "runtime": {"dpi": spec["dpi"], "language": spec["language"], "pymupdf": fitz.VersionBind,
                    "mupdf": fitz.VersionFitz, "distribution_files": bindings,
                    "gpu": "intentionally hidden", "native_inputs": loaded_inputs()}}
    if 'selected_pages' in spec:
        result.update(version='hybrid-ocr.v1', selected_pages=selected)
    if spec.get('verify_images_only'):
        result['verification_only']=True
    document.close()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
