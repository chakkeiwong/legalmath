"""Build the complete gap-campaign report from preserved execution receipts."""
import csv
import hashlib
import json
from pathlib import Path
import re
import os
import unicodedata
import subprocess
import time
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"docs/implementation/prospectus-gap-closure"
DATA = ROOT/"docs/prospectus/gap-closure"

def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value): path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n")
def newest(stage, filename):
    for p in sorted((OUT/stage).glob("attempt-*/"+filename), reverse=True):
        manifest = read(p.parents[len(Path(filename).parts)-1]/"run-manifest.json")
        if manifest.get("status") in ("PASS", "COMPLETE"): return p
    raise ValueError("No passing "+stage+" "+filename)

def build(target):
    started = time.monotonic()
    development = newest("corpus", "run/classification.json")
    rows = read(development)["results"]
    challenge_paths = []
    for path in sorted((OUT/"fresh").glob("attempt-*/run/classification.json")):
        if read(path.parent.parent/"run-manifest.json")["status"] == "PASS": challenge_paths.append(path)
    # Retain failed candidate challenges separately; final row is latest result per issue.
    fresh = {}
    for path in challenge_paths:
        for row in read(path)["results"]: fresh[row["id"]] = row
    rows += list(fresh.values())
    invs = [DATA/"development-inventory.json"]+sorted(DATA.glob("fresh*/issue-inventory.json"))
    docs = {}
    for path in invs: docs.update(read(path)["documents"])
    integration = newest("integration", "integration.json")
    bank = {r["id"]: r for r in read(integration)["results"]}
    regress = newest("regression", "tests.xml")
    suites = ET.parse(regress).getroot()
    test_count = sum(int(s.attrib.get("tests",0)) for s in suites.iter("testsuite"))
    retrievals = [read(p) for p in sorted((DATA/"acquisitions").glob("*/receipt.json"))]
    disposition = read(OUT/"gap-disposition.json")
    counts = {"yes": sum(r["answer"] is True for r in rows), "no": sum(r["answer"] is False for r in rows), "unresolved": sum(r["answer"] is None for r in rows)}
    write(target/"results.json", {"results": rows, "counts": counts, "gap_disposition": disposition,
        "development_result": str(development.relative_to(ROOT)), "fresh_results": [str(p.relative_to(ROOT)) for p in challenge_paths],
        "integration": str(integration.relative_to(ROOT)), "regression_tests": test_count,
        "acquisition_attempts": len(retrievals), "legal_accuracy": "NOT_ESTABLISHED"})
    columns = ["id","title","answer","summary_reason","qualification"]
    with (target/"results.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader()
        for r in rows: writer.writerow({k:r.get(k) for k in columns})
    lines = ["# Prospectus gap-closure results", "",
        f"The campaign covers {len(rows)} bonds: {counts['yes']} qualified positives, {counts['no']} qualified negatives and {counts['unresolved']} unresolved answers. "
        "A positive identifies a principal write-down or compulsory conversion into common shares in the selected terms. A negative is limited to the examined documents and supported constructions.", "",
        f"The full prospectus and bank regression suite passed {test_count} tests. All {len(bank)} integrated cases retained all 14 bank obligations per case. "
        "Actual customer eligibility and transaction permission remain unestablished.", "",
        "## Disposition of the seven gaps", "", "| Gap | Result | Remaining requirement |", "| --- | --- | --- |"]
    for row in disposition["gaps"]: lines.append("| "+" | ".join(row[k].replace("|","/") for k in ("gap","result","remaining"))+" |")
    lines += ["", "## Evidence and decision", "", "| Decision requirement | Finding |", "| --- | --- |",
        "| Decision | Retain the bounded reader repairs and conditional bank integration |",
        "| Primary criterion | Constructed obligations, source replay, regression and formal/native checks pass; all 14 bank obligations are retained |",
        "| Veto status | Invalid witnesses found in the first frozen challenge were removed; failed attempts remain archived |",
        "| Main uncertainty | English interpretation, omitted contracts, source authority and actual customer facts |",
        "| Next justified action | Obtain missing sources and conduct a further unseen-family challenge with the repaired method |",
        "| Not concluded | Universal legal accuracy, complete contract reconstruction or permission to trade |", "",
        "| Inference question | Status |", "| --- | --- |",
        "| Hard veto screen | Rejected forged amounts, conditions, source identities, scope shortcuts and stale facts; failed development attempts retained |",
        "| Statistically supported ranking | None; deterministic finite checks and a small source challenge |",
        "| Descriptive differences | Supported row counts and acquisition coverage only |",
        "| Default readiness | Bounded engineering repair; no claim of universal legal classification |",
        "| Next evidence needed | Referenced agreements and amendments, controlling-source review, more independently selected source families, actual bank/customer facts |", "",
        "## Source findings", "", *[part for paragraph in disposition["source_findings"] for part in (paragraph, "")],
        "## Bond results", ""]
    index = ["# Gap-campaign source index", "", "Every bond below links to its retained selected originals. Selection is a qualified source premise.", ""]
    for i, row in enumerate(rows, 1):
        answer = "Yes" if row["answer"] is True else "No" if row["answer"] is False else "Unresolved"
        lines += ["```{=latex}", r"\begin{minipage}{\linewidth}", "```", ""]
        lines += [f"### {i}. {row['title']}", "", "**Identity:** "+", ".join(row["identifiers"] or [row["id"]])+". **Answer:** "+answer+".", "", row["summary_reason"], ""]
        sources = []
        for c in row["coverage"]:
            d=docs[c["document"]]; sources.append("["+c["document"]+"]("+d["url"]+")")
            index += ["- "+row["id"]+": ["+c["document"]+"]("+os.path.relpath(ROOT/d["original"], target)+") — SHA-256 "+d["sha256"]]
        lines += ["**Selected sources:** "+"; ".join(sources)+".", ""]
        for field in ("dependency_boundary","source_language_qualification"):
            if row.get(field): lines += [row[field], ""]
        lines += ["```{=latex}", r"\end{minipage}", r"\par\addvspace{1em}", "```", ""]
    lines += ["## Limits and next evidence", "", disposition["conclusion"], "",
        "The strongest alternative explanation for a passing software run is that extractor and checker share an incomplete interpretation. "
        "The source challenge is too small to establish accuracy in an issuer population. An applicable omitted condition, wrong edition, or accepted forged witness would overturn the affected result.", ""]
    (target/"results.md").write_text("\n".join(lines))
    (target/"CASE-INDEX.md").write_text("\n".join(index)+"\n")
    header=target/"header.tex"
    header.write_text(r"\setlength{\emergencystretch}{3em}"+"\n")
    cmd=["pandoc",str(target/"results.md"),"--standalone","--pdf-engine=xelatex","--include-in-header="+str(header),"-V","geometry:margin=20mm","-V","fontsize:10pt","-V","mainfont:DejaVu Serif","-V","colorlinks:true","-o",str(target/"results.pdf")]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=150)
    (target/"pdf-build.log").write_text(p.stdout+p.stderr)
    if p.returncode: raise ValueError("PDF build failed")
    extracted=subprocess.check_output(["pdftotext",str(target/"results.pdf"),"-"],text=True)
    (target/"rendered-text.txt").write_text(extracted)
    # Strip only checked page-number footers for contiguous text validation.
    pages=extracted.split('\f')
    cleaned=[]
    for i,page in enumerate(pages,1):
        lines=page.rstrip().splitlines()
        if lines and lines[-1].strip()==str(i):lines.pop()
        cleaned.append('\n'.join(lines))
    extracted='\n'.join(cleaned)
    key=lambda s: ''.join(c.lower() for c in unicodedata.normalize('NFKC',s) if c.isalnum())
    for r in rows:
        for s in (r['title'],r['summary_reason']):
            if key(s) not in key(extracted): raise ValueError("Missing PDF result text: "+r['id'])
    subprocess.run(["pdftoppm","-scale-to","1400","-png",str(target/"results.pdf"),str(target/"page")],check=True,timeout=120,capture_output=True)
    write(target/"pdf-manifest.json", {"command":cmd,"source_sha256":sha(target/"results.md"),"pdf_sha256":sha(target/"results.pdf"),
        "all_bond_titles_and_reasons_preserved":True,"visual_inspection":"PENDING","wall_seconds":time.monotonic()-started})
    print(json.dumps({"rows":len(rows),"counts":counts,"regression_tests":test_count,"report":str(target/"results.pdf")}))
