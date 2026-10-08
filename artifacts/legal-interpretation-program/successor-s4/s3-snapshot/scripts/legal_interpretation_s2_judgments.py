"""Create retained text projections and conservative judgment identity records."""
import json, html, re, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if __name__=="__main__" and Path(sys.prefix)!=ROOT/".venv":
    os.execv(str(ROOT/".venv/bin/python"),[str(ROOT/".venv/bin/python"),"-m","scripts.legal_interpretation_s2_judgments",*sys.argv[1:]])
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
from legalmath.canonical import digest
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"artifacts/legal-interpretation-program/successor-s2"
def text_projection(identity):
    packet=json.loads((BASE/"acquisition"/identity/"response.bin").read_bytes())
    raw=html.unescape(packet["content"])
    raw=re.sub(r"<script.*?</script>"," ",raw,flags=re.S|re.I)
    raw=re.sub(r"<style.*?</style>"," ",raw,flags=re.S|re.I)
    raw=re.sub(r"<[^>]+>"," ",raw)
    raw=re.sub(r"\s+"," ",raw).strip()
    path=BASE/"acquisition"/identity/"judgment-text.txt"
    if not path.exists():path.write_text(raw+"\n")
    return path
def main():
    rows=[]
    for identity in ("cheung-2009","gatecoin-2023","gatecoin-2025"):
        packet=json.loads((BASE/"acquisition"/identity/"response.bin").read_bytes())
        text=text_projection(identity)
        rows.append({"id":identity,"neutral":packet["neutral"],"date":packet["date"],"court":packet["db"],
            "document_url":packet["doc"],"response_hash":digest(packet),"content_text":str(text.relative_to(ROOT)),
            "content_hash":digest(text.read_text()),"admission":"IDENTITY_AND_TEXT_RETAINED; issue, holding, treatment and transfer not yet admitted"})
    p=BASE/"judgments.json"
    if not p.exists():p.write_text(json.dumps({"schema_version":1,"judgments":rows},indent=2)+"\n")
    print(json.dumps({"judgments":len(rows),"path":str(p.relative_to(ROOT)),"sha256":digest(p.read_text())}))
if __name__=="__main__":main()
