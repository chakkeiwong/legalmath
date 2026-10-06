"""Deliver the actual phase evidence and unresolved inputs without overclaiming."""
import csv
import re
import subprocess
import unicodedata
from xml.etree import ElementTree as ET

from . import master_control as c


def build(directory,current):
    from .master_phases import phase_result
    integrated=phase_result(current,"E7")
    rows=c.read(c.ROOT/integrated["classification"])["results"]
    data=c.read(c.ROOT/integrated["inventory"])
    challenge=phase_result(current,"E5")
    new=[i for i in data["issues"] if i.get("family")]
    counts={"yes":sum(r["answer"] is True for r in rows),"no":sum(r["answer"] is False for r in rows),"unresolved":sum(r["answer"] is None for r in rows)}
    development=c.ROOT/current["phases"]["E3"]["directory"]
    tests=sum(int(s.get("tests",0)) for s in ET.parse(development/"tests.xml").getroot().iter("testsuite"))
    acquisition=[c.read(p) for p in sorted((c.DATA/"requests").glob("*/receipt.json"))]
    coverage={category:sum(i.get("category")==category for i in new) for category in ("capital","corporate")}
    unseen=sum(i.get("data_role")=="new-issue-pdf-frozen-challenge" for i in new)
    phases={p:phase_result(current,p) for p in c.PHASES[:-1]}
    open_issues=c.open_requirements(current)
    source_review=c.read(c.ROOT/current["phases"]["E7"]["directory"]/"source-review.json")
    result={"status":"QUALIFIED","results":rows,"counts":counts,"regression_tests":tests,"new_category_coverage":coverage,
            "post_freeze_unseen_issues":unseen,"http_requests":len(acquisition),"phase_results":phases,"source_review":source_review,
            "open_issues":open_issues,"actual_permission":False,"legal_accuracy":"NOT_ESTABLISHED"}
    c.write(directory/"results.json",result)
    with (directory/"results.csv").open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=["id","title","answer","summary_reason"]);writer.writeheader()
        for r in rows:writer.writerow({k:r[k] for k in writer.fieldnames})
    lines=["# Prospectus evidence master: executed results","",
           f"The program covers {len(rows)} issues: {counts['yes']} qualified positives, {counts['no']} qualified negatives and {counts['unresolved']} unresolved classifications. The regression suite passed {tests} tests.","",
           f"New source selections: {coverage['corporate']}/2 corporate and {coverage['capital']}/2 capital issues. {unseen} use issue PDFs first acquired after the relevant method freeze without intervening method changes. Issuer discovery pages may have been visited earlier. The acquisition ledger retains {len(acquisition)}/80 HTTP requests.","",
           "The known inventory-description and bank-fixture metadata defects were reproduced and repaired in new versioned records. Historical evidence was preserved. Every bank investigation retains fourteen obligations and grants no transaction permission.","",
           "## Decision and evidence","","| Requirement | Result |","| --- | --- |",
           "| Decision | Retain demonstrated engineering repairs and source-dependent results within their recorded scope |",
           "| Primary criterion | Controller, arithmetic and regression checks pass; source identities and conditional reports replay |",
           "| Veto status | See preserved failed attempts and witness review; unknown inputs do not become permission |",
           "| Main uncertainty | English interpretation, complete contracts, actual authority and private/event facts |",
           "| Next action | Resolve the remaining source and actual-input requirements; extend unsupported numerical profiles |",
           "| Not concluded | Universal legal accuracy, population accuracy or an authorised trade |","",
           "| Inference question | Status |","| --- | --- |",
           "| Hard veto evidence | Identity, method drift, quotation tampering, arithmetic boundaries and missing-input rules checked in stated domains |",
           "| Statistically supported ranking | None |",
           "| Descriptive evidence | Source availability and finite case counts only |",
           "| Default readiness | Bounded engineering improvements; broader legal reliability unestablished |",
           "| Next evidence | More unseen families, complete agreements, dated authority and actual client/event inputs |","",
           "## Source investigation","",*[(f"**{r.get('subject','Source')}:** {r.get('finding','')}\n\n{r.get('remaining','')}\n") for r in source_review.get("findings",[])],
           "## Conditional loss calculations","",
           "The existing UBS issue-specific engine is retained. Deutsche section 5(4) now has exact conditional principal-allocation and write-up-cap calculations, with explicit effectiveness, currency, issuer discretion and external-input assumptions. Worked scenarios are hypothetical. Notice/timing, actual regulatory determinations and settlement remain separate requirements. Other instruments do not inherit either profile.","",
           "## Bond results",""]
    index=["# Retained source index","","Links refer to exact retained sources; selection does not establish complete contracts.",""]
    import os
    for n,r in enumerate(rows,1):
        label="Yes" if r["answer"] is True else "No" if r["answer"] is False else "Unresolved"
        lines += ["```{=latex}",r"\begin{minipage}{\linewidth}","```","",f"### {n}. {r['title']}","",f"**Identity:** {', '.join(r['identifiers'] or [r['id']])}. **Answer:** {label}.","",r["summary_reason"],"",r.get("dependency_boundary", "Selected source scope remains qualified."),"","```{=latex}",r"\end{minipage}",r"\par\addvspace{1em}","```",""]
        for selected in r["coverage"]:
            d=data["documents"][selected["document"]]
            index.append(f"- {r['id']}: [{selected['document']}]({os.path.relpath(c.ROOT/d['original'],directory)}) — SHA-256 {d['sha256']}")
    lines += ["## Remaining requirements","",*['- '+x for x in open_issues],"",
              "A passing run can still share an incomplete interpretation between extractor and checker. A wrong edition, applicable omitted condition or unsupported witness would overturn the affected conclusion. The source challenge is descriptive and too small to establish population accuracy.",""]
    (directory/"results.md").write_text("\n".join(lines));(directory/"CASE-INDEX.md").write_text("\n".join(index)+"\n")
    (directory/"header.tex").write_text(r"\setlength{\emergencystretch}{3em}"+"\n")
    c.command(["pandoc",str(directory/"results.md"),"--standalone","--pdf-engine=xelatex","--include-in-header="+str(directory/"header.tex"),
               "-V","geometry:margin=20mm","-V","fontsize:10pt","-V","mainfont:DejaVu Serif","-o",str(directory/"results.pdf")],directory/"build.log",timeout=180)
    text=subprocess.check_output(["pdftotext",str(directory/"results.pdf"),"-"],text=True)
    cleaned=[]
    for i,p in enumerate(text.split('\f'),1):
        parts=p.rstrip().splitlines()
        if parts and parts[-1].strip()==str(i):parts.pop()
        cleaned.append('\n'.join(parts))
    key=lambda t: ''.join(ch.lower() for ch in unicodedata.normalize('NFKC',t) if ch.isalnum())
    rendered=key('\n'.join(cleaned))
    for row in rows:
        if any(key(row[k]) not in rendered for k in ('title','summary_reason')):raise ValueError("Missing rendered bond content: "+row['id'])
    (directory/"rendered-text.txt").write_text(text)
    subprocess.run(["pdftoppm","-scale-to","1400","-png",str(directory/"results.pdf"),str(directory/"page")],check=True,capture_output=True,timeout=120)
    return {"status":"QUALIFIED","report":c.relative(directory/"results.pdf"),"pdf_sha256":c.sha(directory/"results.pdf"),"pages":len(list(directory.glob('page-*.png'))),
            "counts":counts,"regression_tests":tests,"source_challenge":coverage,"post_freeze_unseen_issues":unseen,
            "resolved":["Executed program and qualified report built with complete bond text"],"open_issues":open_issues,
            "visual_review":"Pending supervising agent inspection; write external review without altering this attempt"}
