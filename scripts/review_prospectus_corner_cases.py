"""Bounded local review of retained corner-case sources and rendered documents."""
from pathlib import Path
import argparse, base64, json, os, shutil, subprocess
import fitz
from scripts import prospectus_corner_cases as c
def main():
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=("ocr","pages","image","render","excerpt","results"))
    p.add_argument("key",nargs="?")
    p.add_argument("--numbers")
    a=p.parse_args()
    if a.action=="results":
        result=c.j.read(c.OUT/"run-001"/(a.key+".json"))
        pages=[int(v) for v in a.numbers.split(",")] if a.numbers else []
        rows=[{k:e.get(k) for k in ("id","page","kind","disposition","quote","semantic_witness")} for e in result["evidence"] if not pages or e["page"] in pages]
        print(json.dumps({"facts":result["facts"],"open":result["open_issues"],"evidence":rows[:40]},ensure_ascii=False));return
    if a.action=="excerpt":
        pages=c.j.read(c.DATA/"sources"/a.key/"pages.json")["pages"]
        numbers=[int(v) for v in a.numbers.split(",")] if a.numbers else [1]
        assert 1<=len(numbers)<=8 and all(1<=v<=len(pages) for v in numbers)
        print(json.dumps({"page_count":len(pages),"pages":[{"page":n,"text":pages[n-1]["text"][:12000]} for n in numbers]},ensure_ascii=False));return
    if a.action=="image":
        path=(c.OUT/a.key).resolve()
        assert path.is_relative_to(c.OUT.resolve()) and path.suffix==".png" and path.stat().st_size<4000000
        print(base64.b64encode(path.read_bytes()).decode());return
    if a.action=="render":
        result={}
        for name,needle in [("monograph","New prospectuses: payment"),("technical-companion","Additional prospectuses and")]:
            path=c.ROOT/"docs/monograph"/(name+".pdf")
            doc=fitz.open(path);toc=doc.get_toc()
            positions=[i for i,item in enumerate(toc) if needle in item[1]]
            assert len(positions)==1,(name,positions)
            pos=positions[0];level,title,first=toc[pos]
            following=[item[2] for item in toc[pos+1:] if item[0]<=level]
            last=following[0] if following else len(doc)
            assert 0<first<=last<=len(doc) and last-first<30
            folder=c.OUT/"render"/name;folder.mkdir(parents=True,exist_ok=True)
            rows=[]
            for i in range(first-1,last):
                target=folder/f"page-{i+1:03d}.png"
                doc[i].get_pixmap(dpi=100).save(target)
                rows.append({"page":i+1,"text":doc[i].get_text(),"image":c.j.rel(target)})
            result[name]={"pdf_sha256":c.j.sha(path),"page_count":len(doc),"pages":rows}
        c.j.write(c.OUT/"rendered-pages.json",result)
        print(json.dumps({k:[p["page"] for p in v["pages"]] for k,v in result.items()}));return
    source=next(r for r in c.j.read(c.DATA/"source-index.json")["sources"] if r["key"]==a.key)
    assert source["media"]=="pdf" and source["status"]=="RETAINED"
    assert c.j.sha(c.ROOT/source["original"])==source["sha256"]
    doc=fitz.open(c.ROOT/source["original"])
    numbers=[int(v) for v in a.numbers.split(",")] if a.numbers else list(range(1,len(doc)+1))
    assert 1<=len(numbers)<=8 and all(1<=v<=len(doc) for v in numbers)
    folder=c.OUT/"source-render"/a.key;folder.mkdir(parents=True,exist_ok=True)
    rows=[]
    for n in numbers:
        path=folder/f"page-{n:03d}.png"
        doc[n-1].get_pixmap(dpi=140).save(path)
        row={"page":n,"image":c.j.rel(path),"text":doc[n-1].get_text()}
        if a.action=="ocr":
            assert shutil.which("tesseract")
            env=os.environ.copy();env["CUDA_VISIBLE_DEVICES"]="-1";env["OMP_THREAD_LIMIT"]="1"
            run=subprocess.run(["tesseract",str(path),"stdout","-l","eng"],capture_output=True,text=True,check=True,timeout=45,env=env)
            row["text"]=run.stdout
        rows.append(row)
    target=c.DATA/"sources"/a.key/("ocr-pages.json" if a.action=="ocr" else "review-pages.json")
    c.j.write(target,{"source_sha256":source["sha256"],"method":"Tesseract eng 140dpi" if a.action=="ocr" else "PyMuPDF text/render",
        "status":"DERIVATIVE_REQUIRES_REVIEW","pages":rows})
    print(json.dumps({"file":c.j.rel(target),"pages":numbers}))
if __name__=="__main__":main()
