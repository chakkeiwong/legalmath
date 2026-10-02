"""Recorded deterministic actions and bounded acquisition for the gap campaign."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urljoin
from html.parser import HTMLParser

class HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.parts=[]; self.current=None; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ("script","style"): self.skip+=1
        if tag=="a": self.current={"url":dict(attrs).get("href",""),"text":""}
    def handle_endtag(self, tag):
        if tag in ("script","style"): self.skip=max(0,self.skip-1)
        if tag=="a" and self.current is not None:
            self.links.append(self.current); self.current=None
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)
        if self.current is not None: self.current["text"]+=data


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from legalmath.prospectus.common import digest
from legalmath.prospectus.loss_absorption_reader import analyze_issue

OUT = ROOT/"docs/implementation/prospectus-gap-closure"
DATA = ROOT/"docs/prospectus/gap-closure"

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+"\n")

def now(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def preview(out, inventory):
    data = json.loads(inventory.read_text())
    rows = [analyze_issue(issue, data["documents"], ROOT) for issue in data["issues"]]
    write(out/"classification.json", {"results": rows})
    prior = {r["id"]: r for r in json.loads((OUT/"baseline/results.json").read_text())["results"]}
    changes = [{"id": r["id"], "before": prior[r["id"]]["answer"], "after": r["answer"],
                "open_issues": r["open_issues"],
                "unresolved": [{"document": e["document"], "page": e["page"], "quote": e["quote"], "disposition": e["disposition"]}
                               for e in r["evidence"] if e["disposition"].startswith("unresolved")]}
               for r in rows if r["id"] in prior and r["answer"] != prior[r["id"]]["answer"]]
    result = {"counts": {str(a): sum(r["answer"] is a for r in rows) for a in (True, False, None)}, "changes": changes}
    write(out/"comparison.json", result)
    print(json.dumps({"counts": result["counts"], "changed": [r["id"] for r in changes]}))
    return data, rows

def integration(out, inventory):
    from legalmath.transaction import intake
    from legalmath.prospectus import feature_investigation, instrument_sources, instrument_investigation, eligibility_checks
    data, rows = preview(out, inventory)
    bank, store = intake.bootstrap(ROOT, out/"bank", at=now())
    registry = store.json(bank["registry_sha256"])
    for entry in json.loads((ROOT/"docs/prospectus/legal/manifest.json").read_text())["sources"]:
        if entry.get("use_for_applicable_law") is False: continue
        key = Path(entry["text_path"]).stem
        recorded = entry["retrieved_on"]
        if "T" not in recorded: recorded += "T00:00:00Z"
        raw = entry["key"]+".legal-original"
        registry[raw] = intake.record(store.put((ROOT/entry["path"]).read_bytes()), "law", entry["source_url"], recorded, media_type="application/octet-stream")
        registry[key] = intake.record(store.put((ROOT/entry["text_path"]).read_bytes()), "law", entry["source_url"], recorded, dependencies=[raw])
    bank["registry_sha256"] = store.put(registry)
    summaries = []
    for issue, row in zip(data["issues"], rows):
        bank["context"]["instrument_id"] = issue["id"]
        specific = None
        if [s["id"] for s in issue["documents"]] == [instrument_sources.KEY]:
            packet = instrument_sources.dossier(ROOT)
            specific = {"profile": instrument_investigation.PROFILE, "dossier_sha256": store.put(packet), "scenario_sha256": None}
        r = feature_investigation.investigate(row, issue, data["documents"], ROOT, bank, store, instrument_request=specific)
        write(out/"receipts"/(issue["id"]+".json"), r)
        summaries.append({"id": issue["id"], "feature": row["answer"], "obligations": len(r["bank_investigation"]["inventory"]),
            "references": len(r["source_obligations"]["references"]), "mechanisms": len(r["source_obligations"]["mechanisms"]),
            "scope": r["bank_investigation"]["calculations"]["scope"]["in_scope_product"],
            "may_execute_transaction": r["may_execute_transaction"], "instrument_connected": specific is not None})
    write(out/"integration.json", {"results": summaries, "formal_scope_checks": eligibility_checks.prove(out/"formal-scope")})
    print(json.dumps({"integrated": len(summaries), "may_execute": sum(r["may_execute_transaction"] for r in summaries)}))

def acquire(key, url, purpose):
    import re
    if not re.fullmatch(r"[a-z0-9-]+", key): raise ValueError("Safe acquisition key required")
    folder = DATA/"acquisitions"; folder.mkdir(parents=True, exist_ok=True)
    previous = sorted(folder.glob("*/receipt.json"))
    if len(previous) >= 40: raise ValueError("Predeclared 40 retrieval attempts exhausted")
    if sum(json.loads(p.read_text())["url"] == url for p in previous) >= 3:
        raise ValueError("Predeclared two retries per URL exhausted")
    if sum(json.loads(p.read_text()).get("retained", False) for p in previous) >= 32:
        raise ValueError("Predeclared 32 retained-document budget exhausted")
    attempt = folder/(str(len(list(folder.iterdir()))+1).zfill(3)+"-"+key); attempt.mkdir()
    dest = attempt/"response.body"
    command = ["curl", "-L", "--max-time", "60", "--connect-timeout", "15", "-A", "LegalMath research contact public-source inspection", "-sS", "-D", str(attempt/"headers.txt"), "-w", "%{http_code}\n%{url_effective}", "-o", str(dest), url]
    start = time.monotonic()
    p = subprocess.run(command, capture_output=True, text=True, timeout=65)
    (attempt/"stderr.log").write_text(p.stderr)
    lines = p.stdout.splitlines()
    status = int(lines[-2]) if len(lines) >= 2 and lines[-2].isdigit() else 0
    raw = dest.read_bytes() if dest.exists() else b""
    success = p.returncode == 0 and status == 200 and bool(raw)
    r = {"key": key, "url": url, "effective_url": lines[-1] if len(lines) >= 2 else None,
         "purpose": purpose, "recorded_at": now(), "command": command, "http_status": status,
         "exit_code": p.returncode, "wall_seconds": time.monotonic()-start,
         "retained": success, "sha256": hashlib.sha256(raw).hexdigest(), "path": str(dest.relative_to(ROOT)),
         "plan": "docs/plans/prospectus-gap-closure.md", "content_kind": "pdf" if raw.startswith(b"%PDF") else "html_or_other"}
    write(attempt/"receipt.json", r)
    if success and not raw.startswith(b"%PDF"):
        parser = HTMLText(); parser.feed(raw.decode("utf-8", errors="replace"))
        links = [{"text": " ".join(a["text"].split()), "url": urljoin(r["effective_url"], a["url"])} for a in parser.links if a["url"]]
        write(attempt/"links.json", links)
        (attempt/"text.txt").write_text(" ".join(parser.parts))
    print(json.dumps(r, indent=2))
    return r

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["preview", "integration"])
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--inventory", type=Path, required=True)
    args = ap.parse_args()
    globals()[args.stage](args.output, args.inventory)
