"""Fixed pre-edit preservation and bounded projections for the S2 investigation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__" and Path(sys.prefix) != ROOT / ".venv":
    os.execv(str(ROOT / ".venv/bin/python"), [str(ROOT / ".venv/bin/python"), "-m",
        "scripts.legal_interpretation_s2_prepare", *sys.argv[1:]])
from scripts.legal_interpretation_s2_sources import Page
DOC = ROOT / "docs/implementation/legal-interpretation-program"
BASE = ROOT / "artifacts/legal-interpretation-program/successor-s2"
P0 = ROOT / "artifacts/legal-interpretation-program/2026-10-06-offline-v1/P0/attempt-2"
S1 = ROOT / "artifacts/legal-interpretation-program/successor-s1/attempt-2/result.json"
COMPLETION = ROOT / "artifacts/legal-interpretation-program/2026-10-06-offline-v1/completion-2.json"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def ref(p): return {"path": str(p.relative_to(ROOT)), "sha256": sha(p)}
def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("x") as f: json.dump(value, f, indent=2, ensure_ascii=False); f.write("\n")
def files():
    return {str(p.relative_to(ROOT)):sha(p) for directory in ("src/legalmath", "tests")
        for p in sorted((ROOT/directory).rglob("*")) if p.is_file() and
        p.suffix in (".py", ".json", ".java", ".lean")}
def inputs():
    return [ref(p) for p in (COMPLETION, S1, P0/"packet.json", P0/"overlay.json", P0/"obligation-map.json")]
def prepare():
    expected = ((COMPLETION, "00787202085da9ee4942a34bf87252a9be5192fe1333075b843edede74bb788d"),
                (S1, "75b6cfd2f361b7e28ebdac0cd742876831a2b5d5314ba82dc5328432b8993cdd"))
    for p, h in expected:
        if sha(p) != h: raise ValueError("Wrong baseline: " + str(p))
    archive = DOC/"revisions/revision-2"
    manifest = read(DOC/"revision-2-manifest.json")
    archived = []
    for row in manifest["files"] + [ref(DOC/"revision-2-manifest.json"), ref(DOC/"revision-2-validation.json")]:
        path = row["path"]; target = archive/path
        if target.exists():
            if sha(target) != row["sha256"]: raise ValueError("Corrupt archive: " + path)
        else:
            source = ROOT/path
            if sha(source) != row["sha256"]: raise ValueError("Cannot archive changed revision-2 file: " + path)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as f: f.write(source.read_bytes())
        archived.append({"path":path,"retained_path":str(target.relative_to(ROOT)),"sha256":row["sha256"]})
    record = DOC/"revision-2-archive.json"
    if not record.exists():
        save(record, {"schema_version":1,"files":archived,"purpose":"Exact revision-2 bytes before master revision 3"})
    elif read(record)["files"] != archived: raise ValueError("Archive index changed")
    baseline = BASE/"baseline.json"
    if not baseline.exists():
        save(baseline, {"at":datetime.now(timezone.utc).isoformat(), "inputs":inputs(), "files":files(),
            "git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "git_status":subprocess.check_output(["git","status","--short"],cwd=ROOT,text=True),
            "plan":ref(ROOT/"docs/plans/legal-interpretation-program/S2-authority-and-standards.md"),
            "archive":ref(record)})
    elif read(baseline)["inputs"] != inputs(): raise ValueError("S2 baseline changed")
    print(json.dumps({"archive":ref(record),"archived_files":len(archived),"baseline":ref(baseline),
        "source_test_files":len(read(baseline)["files"])}))
def project():
    rows=read(BASE/"inspection/obligations.json")
    output=[]
    for i,row in enumerate(rows,1):
        o=row["obligation"]; responses=[]
        for value in row["responses"]:
            r=value["response"]
            entry={k:r[k] for k in ("answer","needed_evidence","evidence") if k in r}
            if entry not in responses: responses.append(entry)
        output += [f'{i}. {o["obligation_id"]} | {o["dimension"]} | {o["candidate_id"]}',
            json.dumps(responses,ensure_ascii=False)]
    p=BASE/"inspection/obligations-unique.txt"
    if not p.exists():
        with p.open("x") as f:f.write("\n".join(output)+"\n")
    q=BASE/"inspection/questions-unique.json"
    unique=[]
    for row in read(BASE/"inspection/questions.json"):
        for value in row["question_texts"]:
            if value not in unique: unique.append(value)
    if not q.exists(): save(q,unique)
    print(json.dumps({"obligations":ref(p),"questions":ref(q),"question_count":len(unique)}))
def discovery():
    for identity in ("cfa-cases","cfa-decided","sfc-codes"):
        folder=BASE/"acquisition"/identity
        result=read(folder/"result.json")
        page=Page();page.feed((folder/"response.bin").read_text(errors="replace"))
        links=[{"url":urljoin(result["final_url"],r["url"]),"text":" ".join(r["text"].split())}
            for r in page.links]
        terms=("search","hkl","unit trusts","code on unit","fund managers","token","archive","court")
        picked=[r for r in links if any(t in (r["url"]+" "+r["text"]).lower() for t in terms)]
        print(json.dumps({"id":identity,"links":picked[:55]},ensure_ascii=False))
    print(json.dumps({"requests_used":len(list((BASE/"acquisition").glob("*/request-*.json")))}))
def navigation():
    import re
    raw=(BASE/"acquisition/hklii-app/response.bin").read_text()
    for term in ("baseURL","/api/","searchCases","getCase","casePath","backend","https://","/search"):
        positions=[m.start() for m in re.finditer(re.escape(term),raw)]
        print(json.dumps({"term":term,"count":len(positions),"contexts":[raw[max(0,i-120):i+280] for i in positions[:4]]}))
    raw=(BASE/"acquisition/judiciary-home-corrected/response.bin").read_text()
    print(json.dumps({"judiciary_scripts":re.findall(r'<script[^>]*src=["\\\']([^"\\\']+)',raw)}))
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("prepare","project","discovery","navigation"))
    args=parser.parse_args()
    {"prepare":prepare,"project":project,"discovery":discovery,"navigation":navigation}[args.action]()
