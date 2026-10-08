"""Local page rendering and bounded OCR for the documented prospectus additions."""
from pathlib import Path
import argparse, base64, hashlib, json, shutil, subprocess
import fitz
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/implementation/prospectus-jurisdiction-2026-10-04"
def main():
    p=argparse.ArgumentParser();p.add_argument("action",choices=("scan","anchors","pages","image"));p.add_argument("subject",nargs="?");a=p.parse_args()
    if a.action=="image":
        image=(OUT/a.subject).resolve()
        assert image.is_relative_to(OUT.resolve()) and image.suffix==".png" and image.stat().st_size<4000000
        print(base64.b64encode(image.read_bytes()).decode());return
    if a.action=="anchors":
        result={}
        for key,pages in [("jur-hellenic-2008-candidate",[1,7,10,17,18,25]),
                          ("jur-nlb-2011-candidate",[1,18,24,48])]:
            source=ROOT/"docs/prospectus/jurisdiction-2026-10-04/sources"/key/"source.pdf"
            pdf=fitz.open(source)
            dest=OUT/"source-render"/key;dest.mkdir(parents=True,exist_ok=True)
            for number in pages:
                pdf[number-1].get_pixmap(dpi=120).save(dest/f"page-{number:02d}.png")
            result[key]={"sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"pages":pages}
        (OUT/"source-render"/"anchor-manifest.json").write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps(result,indent=2));return
    if a.action=="scan":
        key="jur-bes-2014-ptbeqkom0019"
        folder=ROOT/"docs/prospectus/jurisdiction-2026-10-04/sources"/key
        pdf=fitz.open(folder/"source.pdf")
        render=OUT/"source-render"/key;render.mkdir(parents=True,exist_ok=True)
        texts=[];images=[]
        for i,page in enumerate(pdf):
            image=render/f"page-{i+1:02d}.png";page.get_pixmap(dpi=150).save(image);images.append(str(image.relative_to(ROOT)))
            if shutil.which("tesseract"):
                r=subprocess.run(["tesseract",str(image),"stdout","-l","eng"],capture_output=True,text=True,timeout=45,check=True)
                texts.append({"page":i+1,"text":r.stdout})
        record={"method":"Tesseract eng,150dpi" if texts else "No OCR tool available; rendered images only",
                "status":"OCR_DERIVATIVE_REQUIRES_REVIEW" if texts else "OCR_REQUIRED",
                "pages":texts,"images":images}
        (folder/"ocr-pages.json").write_text(json.dumps(record,indent=2)+"\n")
        print(json.dumps({"images":images,"ocr_available":bool(texts)},indent=2));return
    result={}
    for name,needle in [("monograph","New prospectuses: payment"),("technical-companion","Additional prospectuses and")]:
        doc=fitz.open(ROOT/"docs/monograph"/(name+".pdf"));rows=[]
        toc=doc.get_toc()
        matches=[i for i,item in enumerate(toc) if needle in item[1]]
        assert len(matches)==1, (name,matches)
        position=matches[0];level,title,first=toc[position]
        following=[item[2] for item in toc[position+1:] if item[0]<=level]
        last=following[0] if following else len(doc)
        assert 0<first<=last<=len(doc) and last-first<20, (first,last)
        dest=OUT/"render"/name;dest.mkdir(parents=True,exist_ok=True)
        for i in range(first-1,last):
            page=doc[i];rows.append({"page":i+1,"text":page.get_text()})
            page.get_pixmap(dpi=110).save(dest/f"page-{i+1:03d}.png")
        result[name]=rows
    (OUT/"rendered-pages.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:[p["page"] for p in v] for k,v in result.items()},indent=2))
if __name__=="__main__":main()
