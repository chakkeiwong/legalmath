"""Bounded read-only inspection of retained closure files."""
import argparse,json
from scripts import run_prospectus_closure_next as m
def main(args):
    parser=argparse.ArgumentParser()
    parser.add_argument("path");parser.add_argument("--lines",nargs=2,type=int)
    parser.add_argument("--pages",nargs="+",type=int);parser.add_argument("--keys",nargs="+")
    a=parser.parse_args(args);path=(m.ROOT/a.path).resolve()
    if not path.is_relative_to(m.ROOT):raise ValueError("Outside worktree")
    text=path.read_text()
    if a.lines:
        start,stop=a.lines
        print("\n".join(f"{i+1}: {v}" for i,v in enumerate(text.split("\n")) if start<=i+1<=stop))
    elif a.pages:
        doc=json.loads(text) if path.suffix==".json" else None
        pages=doc["pages"] if isinstance(doc,dict) and "pages" in doc else text.split("\f")
        for p in a.pages:
            value=pages[p-1]
            print(f"PAGE {p}:\n"+(value["text"] if isinstance(value,dict) else value))
    else:
        value=json.loads(text)
        if a.keys:
            for key in a.keys:
                selected=value
                for part in key.split("."):
                    selected=selected[int(part)] if isinstance(selected,list) else selected[part]
                print(key+": "+json.dumps(selected,ensure_ascii=False,indent=2))
        else:print(json.dumps(value,ensure_ascii=False,indent=2))
