"""Bounded local inspection/build helper; no retrieval or model calls."""
import argparse
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("command",choices=["basf","environment","brackets","queues"])
    args=parser.parse_args()
    if args.command=="brackets":
        import json
        out=ROOT/"docs/implementation/prospectus-successor-2026-10-06"
        state=json.loads((out/"state.json").read_text())
        data=json.loads((ROOT/state["P2"]["directory"]/"basf-assembly.json").read_text())
        for r in data["remaining_brackets"]:
            if r["depth"]<=1:print(r["start"],r["end"],r["depth"],r["preview"])
        return
    if args.command=="queues":
        import json
        p=ROOT/"docs/implementation/prospectus-evidence-closure/phases/S4/attempt-004/clause-groups.json"
        data=json.loads(p.read_text())
        print("groups",len(data),"records",sum(len(r["bindings"]) for r in data),"sample",json.dumps(data[0],ensure_ascii=False)[:2000])
        for p in (ROOT/"docs").glob("**/*"):
            if p.is_file() and "review" in str(p).lower() and "form" in str(p).lower() and p.suffix in {".json",".md"}:
                if "candidate" not in str(p) and "baseline" not in str(p):print(p.relative_to(ROOT))
        return
    if args.command=="environment":
        import importlib.util
        import shutil
        print(json.dumps({"python":sys.executable,"version":sys.version,
            "fitz":bool(importlib.util.find_spec("fitz")),"pytest":bool(importlib.util.find_spec("pytest")),
            "legalmath":str(importlib.util.find_spec("legalmath")),
            "xelatex":shutil.which("xelatex"),"latexmk":shutil.which("latexmk")},indent=2))
        return
    sys.path.insert(0,str(ROOT/"src"))
    from legalmath.prospectus.successor.contracts import read,write
    from legalmath.prospectus.successor.basf import construct
    from legalmath.prospectus.successor.jobs import BASF
    out=ROOT/"docs/implementation/prospectus-successor-2026-10-06"
    state=read(out/"state.json")
    graph=read(ROOT/state["P1"]["directory"]/"source-graph.json")
    result=construct(graph,read(ROOT/BASF))
    write(out/"basf-construction-preview.json",result)
    (out/"basf-construction-preview.txt").write_text(result["candidate_text"])
    print(json.dumps({"rules":result["rules"],"operations":len(result["operations"]),
        "remaining_brackets":len(result["remaining_brackets"]),"unbalanced":result["unbalanced_offsets"],
        "top_level":[r for r in result["remaining_brackets"] if r["depth"]==0]},indent=2,ensure_ascii=False))


if __name__=="__main__":main()
