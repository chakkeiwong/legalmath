"""Bounded local inspection of repair sources, receipts and rendered addendum."""
from pathlib import Path
import argparse, base64, json
from scripts import run_prospectus_corner_repair as m
def main():
    p=argparse.ArgumentParser()
    p.add_argument("action", choices=("sources","image","status","acquisition"))
    p.add_argument("key", nargs="?")
    a=p.parse_args()
    if a.action=="image":
        path=(m.ROOT/a.key).resolve()
        assert path.is_relative_to(m.ROOT/"docs/implementation") and path.suffix==".png"
        assert path.stat().st_size<6000000
        import fitz
        with fitz.open(path) as doc:
            scale=min(1,1000/doc[0].rect.width)
            raw=doc[0].get_pixmap(matrix=fitz.Matrix(scale,scale)).tobytes("png")
        print(base64.b64encode(raw).decode());return
    if a.action=="status":
        print(json.dumps(m.read(m.OUT/"state.json"),indent=2));return
    if a.action=="acquisition":
        from scripts import prospectus_jurisdiction_study as j
        from html.parser import HTMLParser
        from urllib.parse import urljoin
        class Links(HTMLParser):
            def __init__(self):super().__init__();self.values=[]
            def handle_starttag(self,tag,attrs):
                self.values.extend(v for k,v in attrs if tag=="a" and k=="href" and v)
        rows=[]
        for pth in j.receipts():
            r=m.read(pth)
            if a.key and r["key"]!=a.key:continue
            if not a.key and not any(x in r["url"].lower() for x in ("bportugal","fma.gv","danagas","duckduckgo","google","bing","lloyd","ukraine","normattiva")):continue
            row={k:r.get(k) for k in ("key","url","status","http_status")}
            if r.get("original") and a.key==r["key"]:
                raw=(m.ROOT/r["original"]).read_bytes()
                parser=Links();parser.feed(raw.decode("utf8",errors="replace"))
                row["links"]=[urljoin(r["url"],v) for v in parser.values][:150]
                text=j.Text();text.feed(raw.decode("utf8",errors="replace"))
                row["text"]="\\n".join(text.parts)[:25000]
            rows.append(row)
        print(json.dumps(rows,ensure_ascii=False,indent=2));return
    rows=[]
    for code in ("1221003","1272291","1260978","1286398","1297141","1347380"):
        path=m.DATA/"sources"/("jur-more-bes-"+code)/"pages.json"
        rows.append({"key":code,"text":m.read(path)["pages"][0]["text"]})
    old=m.read(m.ROOT/"docs/implementation/prospectus-difficulty-2026-10-04/run-001/case-105635287.json")
    witnesses=[e for e in old["evidence"] if e["kind"]=="principal_write_down"]
    print(json.dumps({"covers":rows,"mizuho":witnesses},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
