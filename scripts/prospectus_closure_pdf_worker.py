"""Page-preserving CPU OCR worker; uses the existing PyMuPDF installation."""
from pathlib import Path
import argparse, hashlib, json, os, sys, time
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
os.environ["OMP_THREAD_LIMIT"]="1"
import fitz
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/implementation/prospectus-closure-2026-10-05"
DATA=ROOT/"docs/prospectus/closure-2026-10-05"
OLD=ROOT/"docs/implementation/prospectus-corner-repair-2026-10-04/phases/016-intake"
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n")
def run(key,numbers,mode):
    sources=json.loads((OLD/"bes-bundles.json").read_text())["documents"]
    source=sources[key];original=ROOT/source["original"]
    assert sha(original)==source["sha256"]
    doc=fitz.open(original)
    target=DATA/("smoke" if mode=="smoke" else "derivatives")/key
    target.mkdir(parents=True,exist_ok=True)
    language=DATA/"tools/eng.traineddata"
    pages=[];merged=fitz.open()
    for index,page in enumerate(doc,1):
        raw=page.get_text(sort=True)
        row={"page":index,"text":raw,"method":"original_text"}
        if index in numbers:
            image=target/f"page-{index:03d}.png"
            pix=page.get_pixmap(dpi=300,colorspace=fitz.csRGB)
            pix.save(image)
            preview=target/f"page-{index:03d}-review.png"
            page.get_pixmap(dpi=130).save(preview)
            row.update(image=str(image.relative_to(ROOT)),image_sha256=sha(image),
                       review_image=str(preview.relative_to(ROOT)),review_image_sha256=sha(preview),
                       original_text=raw)
            if mode!="render":
                start=time.monotonic()
                data=pix.pdfocr_tobytes(language="eng",tessdata=str(language.parent),compress=True)
                scanned=fitz.open(stream=data,filetype="pdf")
                row.update(text=scanned[0].get_text(sort=True),method="pymupdf_tesseract_full_page",
                           words=scanned[0].get_text("words"),wall_seconds=round(time.monotonic()-start,3))
                merged.insert_pdf(scanned)
                (target/f"page-{index:03d}.txt").write_text(row["text"])
            print(json.dumps({"key":key,"page":index,"characters":len(row["text"]),"mode":mode}),flush=True)
        pages.append(row)
    if len(merged):
        merged.save(target/"ocr-selected-pages.pdf")
    record={"source":source["original"],"source_sha256":source["sha256"],"page_count":len(doc),
        "pages":pages,"ocr_pages":numbers if mode!="render" else [],
        "rendered_pages":numbers,"mode":mode,"review_status":"PENDING",
        "runtime":{"python":sys.executable,"pymupdf":fitz.VersionBind,"mupdf":fitz.VersionFitz,
                   "gpu":"intentionally hidden","dpi":300,"language":"eng",
                   "language_sha256":sha(language) if language.exists() else None,
                   "confidence_scores":"not exposed by PyMuPDF; no confidence-based acceptance",
                   "worker_sha256":sha(__file__)}}
    write(target/"pages.json",record)
    return {"key":key,"pages_json":str((target/"pages.json").relative_to(ROOT)),
            "sha256":sha(target/"pages.json"),"page_count":len(doc),"processed_pages":numbers}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("key");p.add_argument("pages");p.add_argument("mode",choices=("smoke","ocr","render"))
    a=p.parse_args();numbers=[int(x) for x in a.pages.split(",")]
    assert len(numbers)<=20 and len(set(numbers))==len(numbers) and min(numbers)>0
    print(json.dumps(run(a.key,numbers,a.mode),ensure_ascii=False))
