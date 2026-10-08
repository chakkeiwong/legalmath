"""Freeze verified S3 dependencies before S4 changes; never overwrite history."""
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if __name__=="__main__" and Path(sys.prefix)!=ROOT/".venv":
    os.execv(str(ROOT/".venv/bin/python"),[str(ROOT/".venv/bin/python"),"-m","scripts.legal_interpretation_s4_prepare",*sys.argv[1:]])
os.environ["CUDA_VISIBLE_DEVICES"]="-1"


def prepare():
    import json
    import subprocess
    from datetime import datetime, timezone
    from scripts import run_legal_interpretation_master as master
    from scripts.legal_interpretation_s3_execute import verify_attempt
    base=ROOT/"artifacts/legal-interpretation-program/successor-s4"
    target=base/"baseline.json"
    if target.exists():raise ValueError("S4 already frozen; never rerun changed S3")
    current=master.selected()
    if current["completed_phase"]!="S3":raise ValueError("Expected S3 predecessor")
    selected=master.checked(current["result"])
    verification=verify_attempt(selected.parent)
    result=master.read(selected)
    paths={**result["method"]["source_and_tests"],**result["method"]["drivers"]}
    paths.update({str(master.POINTER.relative_to(ROOT)):master.sha(master.POINTER)})
    rows=[]
    for name,expected in sorted(paths.items()):
        source=ROOT/name
        if master.sha(source)!=expected:raise ValueError("Changed S3 dependency: "+name)
        dest=base/"s3-snapshot"/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open("xb") as f:f.write(source.read_bytes())
        rows.append({"original_path":name,**master.ref(dest)})
    master.save(target,{"at":datetime.now(timezone.utc).isoformat(),"s3_pointer":current,
        "s3_verification_before_edits":verification,"files":rows,
        "source_and_tests":result["method"]["source_and_tests"],
        "git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "git_status":subprocess.check_output(["git","status","--short"],cwd=ROOT,text=True),
        "scope":"Historical bytes and pre-edit verification; not current-method execution"})
    print(json.dumps({"status":"FROZEN","baseline":master.ref(target),"files":len(rows)}))


if __name__=="__main__":prepare()
