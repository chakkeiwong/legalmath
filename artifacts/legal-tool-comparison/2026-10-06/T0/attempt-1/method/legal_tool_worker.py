"""Isolated external-package worker; fixed operations, JSON data, no shell."""
import json
import os
from pathlib import Path
import re
import sys
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
ROOT=Path(__file__).resolve().parents[1]
RES=ROOT/".localresources/legal-tool-comparison"

def pyarg(data):
    pin=json.loads((RES/"pyarg.json").read_text())
    sys.path.insert(0,str(ROOT/pin["source"]/"src"))
    from py_arg.abstract_argumentation_classes.argument import Argument
    from py_arg.abstract_argumentation_classes.defeat import Defeat
    from py_arg.abstract_argumentation_classes.abstract_argumentation_framework import AbstractArgumentationFramework
    from py_arg.algorithms.semantics.get_grounded_extension import get_grounded_extension
    from py_arg.algorithms.semantics.get_preferred_extensions import get_preferred_extensions
    rows=[]
    for case in data["cases"]:
        if len(case["ids"])>12:raise ValueError("Argument limit")
        args={x:Argument(x) for x in case["ids"]}
        af=AbstractArgumentationFramework(case["id"],list(args.values()),
                    [Defeat(args[a],args[b]) for a,b in case["attacks"]])
        grounded=sorted(a.name for a in get_grounded_extension(af))
        preferred=sorted(sorted(a.name for a in e) for e in get_preferred_extensions(af))
        rows.append({"id":case["id"],"grounded":[grounded],"preferred":preferred})
    return {"status":"EXECUTED","tool":"PyArg","commit":pin["commit"],"cases":rows,
            "scope":"Supplied abstract defeat graph only; no ASPIC construction or legal priority imported"}

def citations(data):
    import eyecite
    from importlib.metadata import version
    rows=[]
    for text in data["texts"]:
        found=eyecite.get_citations(text)
        rows.append({"text":text,"citations":[{"matched":c.matched_text(),
            "class":type(c).__name__,"span":list(c.span())} for c in found]})
    return {"status":"EXECUTED","tool":"eyecite","version":version("eyecite"),"cases":rows,
            "scope":"Syntax extraction only, no external case resolution or citator"}

def retrieve(data):
    from rank_bm25 import BM25Okapi
    from importlib.metadata import version
    units=data["corpus"]["units"]
    tokens=lambda s:re.findall(r"[a-z0-9]+",s.lower())
    ranker=BM25Okapi([tokens(u["text"]) for u in units],k1=1.5,b=0.75,epsilon=0.25)
    rows=[]
    for q in data["questions"]:
        scores=ranker.get_scores(tokens(q["question"]))
        ids=sorted(range(len(units)),key=lambda i:(-float(scores[i]),units[i]["id"]))[:8]
        rows.append({"question_id":q["id"],"passages":[{"unit_id":units[i]["id"],
            "score":float(scores[i]),"text":units[i]["text"],"role":units[i]["role"],
            "source":units[i]["source"]} for i in ids]})
    return {"status":"EXECUTED","tool":"rank-bm25","version":version("rank-bm25"),"results":rows,
        "parameters":{"k1":1.5,"b":0.75,"epsilon":0.25,"top_k":8},
        "scope":"Lexical baseline inspired by retrieval literature; not CLERC software or corpus",
        "parameter_status":"Package defaults and top-8 convenience hypothesis; descriptive ranking only"}

def main():
    if len(sys.argv)!=4 or sys.argv[1] not in ("pyarg","citations","retrieve"):
        raise SystemExit("Fixed worker arguments required")
    inp,out=(Path(p).resolve() for p in sys.argv[2:])
    if not inp.is_relative_to(ROOT) or not out.is_relative_to(ROOT):
        raise ValueError("Path outside worktree")
    data=json.loads(inp.read_text())
    result={"pyarg":pyarg,"citations":citations,"retrieve":retrieve}[sys.argv[1]](data)
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
if __name__=="__main__":main()
