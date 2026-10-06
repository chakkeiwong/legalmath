"""Read-only inspection of retained evidence for the ordered repair."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
def main():
    p=argparse.ArgumentParser();p.add_argument("kind",choices=["sources","basf","forms"]);a=p.parse_args()
    if a.kind=="forms":
        for f in ROOT.glob("docs/implementation/**/review*.json"):
            if "baseline" not in f.parts and "candidate" not in f.parts:
                v=json.loads(f.read_text())
                if isinstance(v,list): print(str(f.relative_to(ROOT)),len(v),str(v[:1])[:700])
        return
    if a.kind=="sources":
        for folder in ("jurisdiction-2026-10-04","corner-cases-2026-10-04","corner-repair-2026-10-04"):
            for s in read("docs/prospectus/"+folder+"/source-index.json")["sources"]:
                if any(k in s["key"] for k in ("annex","heta","dana","lloyds","ukraine","popular","snoras","italy")) and not any(k in s["key"] for k in ("bing","ddg","search","index")):
                    print(s["key"],s.get("media"),s.get("pages"),s.get("text"),s.get("sha256"))
        return
    packet=read("docs/implementation/prospectus-basf-continuation-2026-10-05/phases/012-construct/basf-selection-admission.json")
    print("DECISIONS",[(d["id"],d["selected"]) for d in packet["decisions"]])
    print("FIELDS",[{k:v for k,v in x.items() if k!="source"} for x in packet["issue_context"]])
    for key in ("basf-supplement-february-2023-exchange","basf-annual-2022-exchange"):
        pages=read(packet["sources"][key]["text"])["pages"]
        print(key,"FIRST PAGE",str(pages[0])[:2500])
    old=read("docs/implementation/prospectus-repair-2026-10-06/state.json")
    data=read(old["P2"]["directory"]+"/basf-assembly.json")
    print("CURRENT",old["P2"]["directory"])
    for at in data["unbalanced_offsets"]:
        print("UNBALANCED",at,data["raw_body"][at-250:at+1600])
        print("PAGES",[s for s in data["source_map"] if abs(s["start"]-at)<250])
    print("BRANCHES")
    for b in data["remaining_brackets"]:
        if b["depth"]<=1:print(b)
if __name__=="__main__":main()
