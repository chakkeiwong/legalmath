"""Versioned source-based results and rendered addendum."""
import os, re, shutil, subprocess, sys
import xml.etree.ElementTree as ET
from scripts import prospectus_refresh as m
from scripts.prospectus_refresh_admission import review, load_column_document, walk_anchors
from scripts.prospectus_refresh_work import sources, BASF

def tests():
    path=m.latest("checks",current=True)/"tests.xml"
    root=ET.parse(path).getroot()
    suites=[root] if root.tag=="testsuite" else list(root.iter("testsuite"))
    result={k:sum(int(s.get(k,0)) for s in suites) for k in ("tests","failures","errors","skipped")}
    m.require(result["tests"]>0 and not any(result[k] for k in ("failures","errors","skipped")),
              "Tests failed, missing, or skipped")
    result.update(path=m.relative(path),sha256=m.sha(path))
    return result

def run(folder):
    admission=m.latest("admit",current=True)
    result=m.read(admission/"admission-summary.json")
    test=tests()
    baseline=m.read(m.latest("baseline")/"baseline.json")
    gaps=m.read(admission/"remaining-gaps.json")
    text=f"""# Prospectus closure refresh — 5 October 2026

BASF's retained 2022 base prospectus and February 2023 supplement now have a
source-bound admission record for the March 2032 issue. It checks
{result['basf_selected_options']} explicit selections and preserves German as the
controlling language. The full issue dossier remains unresolved.

An optional loader repairs the interleaved German and English extraction on
Deutsche Bank PDF pages 36–38. All {result['words_preserved']} extracted words
remain in language or footer regions, with coordinates and original-page bindings.
Changed pages must reconstruct from the reviewed geometry; all other pages must
remain exactly equal to the baseline. No OCR or translation was used.

## Source findings

BASF's final terms page 2 links the 9 September 2022 base and 27 February 2023
supplement. Page 3 selects Option I and deletes unselected, incomplete or struck-out
alternatives. Page 7 makes German controlling. A programme template is therefore
not an operative clause selection.

The admission distinguishes the dated call selected on page 6 from a separately
worded interest-date call marked No. It preserves the annual ICMA no-stub choice,
unselected long-stub/Actual365 alternatives, clearing systems and global-note form.
The German status, ICMA, payment-delay and governing-law passages retain their
qualifications. Quotes and offsets are in basf-admission.json.

Historical Option I A–I conditions are distinguished from current Option I.
The 2022 financial report is retained but its incorporated pages await admission.
Earlier/interim statements, applicable agreements, amendment coverage and complete
German suboption mapping remain open. The admission is bounded to recorded facts.

Deutsche section 2(7), page 37, permits statutory write-down to zero and conversion
into ordinary shares of the issuer, a group entity or a bridge bank, OR other
ownership instruments qualifying as Common Equity Tier 1. The repaired English
column retains those alternatives, the no-event-of-default text and the agreement
qualifier. It does not establish common-share-only conversion. Both languages
remain in regions.json.

The post-extraction review added a source-specific disclosure annotation for this
complete section. It records the statutory principal write-down possibility and
both conversion alternatives. Current legal applicability, actual action and
mandatory common-share-only conversion stay unknown. This is an exact reviewed
construction; unreviewed rewordings and added exceptions abstain. It has not
become a general semantic rule or changed the frozen whole-issue answer.

## Validation and decision

{test['tests']} tests passed with no failures, errors or skips, including ambiguous
checkboxes, bilingual conflicts, changed originals/images/geometry, lost negation,
rehashed forged derivatives, page/scope controls and retained OCR/finance checks.

The frozen reader produced {result['reader_before']['records']} records
({result['reader_before']['unresolved']} unresolved) on the original three pages
and {result['reader_after']['records']} records
({result['reader_after']['unresolved']} unresolved) after repair. Counts describe
segmentation/classification; they are not accuracy measures. Every output quote
was checked against the corresponding original or admitted derivative.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain bounded BASF admission | Edition/issue anchors and explicit choices pass | Dossier and independent German review incomplete | Unmapped suboptions and missing applicable material | Complete clause mapping and incorporation | Complete legal opinion or absence of loss powers |
| Retain optional column adapter | Word preservation, reconstruction and adverse controls pass | Only three reviewed pages; no independent labels | Other layouts, continuations and semantics | Qualify more pages and repair source-derived meanings | Whole-document accuracy or general reliability |
| Preserve programme qualification | Historical evidence remains intact | Independent/unseen/intended-use work pending | Generalisation and actual facts | Qualified adjudication and factual admission | Programme closure or production readiness |

Deterministic engineering evidence; statistical ranking is N/A. The strongest
alternative explanation is that classifier changes reflect sentence boundaries
while the legal difficulty remains. Word and qualifier preservation is therefore
the criterion, not the count. A contrary image reading, wrong selector, missing
continuation or independent interpretation would require repair.

## Execution and remaining work

Baseline: 5bff0065dcc73268aab78cba3e9522b7455825ac; branch:
feature/prospectus-evidence-master; worktree: .worktrees/bond-gap-closure.
The original engine, 4 October candidate, OCR round and existing review forms
remain preserved. Entry verification covered {baseline['verified_count']} bound
files; final verification rechecks them.

The driver retains numbered attempts, source/method bindings, commands, environment,
wall times and failure logs. Review inputs are snapshotted. A method or current
review change invalidates affected checks/admission. Next commands refresh after
each phase. No package installation, paid model call, external message or HTTP
request occurred; the ledger remains 188/212, leaving 24 requests.

remaining-gaps.json carries G13–G17 source work, BES dependencies and precedence,
missing jurisdiction primary sources, unadjudicated spans, actual regulatory and
financial facts, independent/unseen validation and intended-use acceptance.
The original 25 independent-review forms remain untouched.

Next local priority: complete BASF's German suboption mapping and qualify further
Deutsche operative pages before broader semantic repair. Human manuscript
acceptance and production promotion remain pending.

## Reset memo

Run python3 -m scripts.prospectus_refresh status for the current receipt and next
command. Authoritative results are in numbered phase directories. Read the
refreshed plan and source-review.json before changing scope. Preserve completed
OCR data and independent-review forms. These are exposed development cases.
"""
    (folder/"REPORT.md").write_text(text)
    m.write(folder/"remaining-gaps.json",gaps)
    (folder/"RESET-MEMO.md").write_text(text.split("## Reset memo\n\n",1)[1])
    docs=sources()
    tex=r"""\documentclass[11pt]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[a4paper,margin=25mm]{geometry}
\usepackage{lmodern,microtype,hyperref}
\hypersetup{colorlinks=true,urlcolor=blue}
\title{Prospectus closure: language and option selection}
\author{LegalMath development note}
\date{5 October 2026}
\begin{document}
\maketitle
BASF's March 2032 notes illustrate a problem that downloading a prospectus alone
cannot solve. The final terms select fixed-rate Option I from the September 2022
programme, specify German as the controlling language, and delete alternatives
that are unselected, incomplete or struck out. A reader must apply those choices
before interpreting the template's clauses.\footnote{BASF final terms,
6 March 2023, pp.~2--3 and 7; \href{FTPATH}{retained original}.}

The new source record binds the final terms to the base prospectus of
9 September 2022 and its first supplement of 27 February 2023. It checks
NCHOICES explicit selections. Page~6 selects an issuer call during
8 December 2031--7 March 2032 but marks a separately worded call tied to interest
payment dates as unavailable. A search for issuer calls cannot distinguish those
provisions. Likewise, the annual ICMA choice excludes short or long coupons,
although other day-count alternatives remain printed in the programme.

The controlling German text preserves further qualifications. The ranking clause
recognises priority created by mandatory law. The payment-day clause denies
additional interest for the specified delay. Section~15 expressly states that
the English translation is nonbinding.\footnote{BASF base prospectus,
pp.~110, 112, 114 and 133; \href{BASEPATH}{retained original}.}
These passages support bounded source decisions. Other optional clauses,
incorporated financial statements and applicable agreements still require review.

\newpage
Deutsche Bank's 2025 AT1 prospectus presents a different obstacle. On pages~36--38,
German occupies the left column and English the right. The earlier extraction
preserved visual rows, causing the reader to join fragments from both languages.
The reviewed derivative separates the columns using word coordinates and retains
every word in its language or page-number region.\footnote{Deutsche Bank,
AT1 Notes Prospectus, ISIN DE000A460DG7, PDF pp.~36--38;
\href{DBPATH}{retained original}.}

The distinction matters in section~2(7). The resolution authority may write
claims down to zero, or convert them into ordinary shares of the issuer, a group
entity or a bridge bank, or into other ownership instruments qualifying as
Common Equity Tier~1. The last alternative prevents a conclusion that conversion
must be exclusively into common shares. The paragraph also preserves the
no-event-of-default qualification. Those words are now available as a contiguous
English passage, alongside the retained German column.

\medskip
NTESTS engineering tests passed. The source-admission tests reject lost negation,
ambiguous selections, inconsistent bilingual fields, changed originals or images,
overlapping geometry and derivatives that no longer reconstruct from the reviewed
words. The earlier OCR and conditional financial checks also pass.

The frozen reader generated BEFORE records, including BEFOREUN unresolved,
on the original three pages and AFTER records, including AFTERUN unresolved,
after column separation. These figures describe changed segmentation and
classification on known development examples. They do not measure legal accuracy.
The engineering result is narrower: the reviewed words and material qualifiers
survive the optional extraction path, and provenance checks reject alteration.
A source-specific annotation now records the disclosed write-down power and both
conversion alternatives. It abstains on unreviewed rewording or added exceptions;
actual legal applicability and mandatory common-share-only conversion remain
unknown. This exact reviewed construction is not a general semantic rule.

Independent legal adjudication, further page qualification, complete operative
documents and actual issuer or investor facts remain necessary. No production
default changed, and this round made no new network request. Historical evidence
and existing independent-review forms remain intact. The next source task is to
finish BASF's German clause selection; the next extraction task is to qualify
the remaining Deutsche pages before widening semantic repair.
\end{document}
"""
    replacements={"FTPATH":os.path.relpath(m.ROOT/docs["basf-2032-final"]["original"],folder),
                  "BASEPATH":os.path.relpath(m.ROOT/docs[BASF]["original"],folder),
                  "DBPATH":os.path.relpath(m.ROOT/docs["deutsche-at1-2025"]["original"],folder),
                  "NCHOICES":str(result["basf_selected_options"]),"NTESTS":str(test["tests"]),
                  "BEFOREUN":str(result["reader_before"]["unresolved"]),"AFTERUN":str(result["reader_after"]["unresolved"]),
                  "BEFORE":str(result["reader_before"]["records"]),"AFTER":str(result["reader_after"]["records"])}
    for key,value in replacements.items():tex=tex.replace(key,value)
    (folder/"addendum.tex").write_text(tex)
    m.run_command(["latexmk","-pdf","-interaction=nonstopmode","-halt-on-error",
                   "-outdir="+str(folder),str(folder/"addendum.tex")],folder,"latex",timeout=180)
    m.run_command(["pdftoppm","-png","-scale-to","1500",str(folder/"addendum.pdf"),
                   str(folder/"addendum")],folder,"render",timeout=60)
    images=sorted(folder.glob("addendum-*.png"))
    m.require(bool(images),"No rendered pages")
    m.write(folder/"document.json",{"pdf":m.relative(folder/"addendum.pdf"),
             "pdf_sha256":m.sha(folder/"addendum.pdf"),"tex":m.relative(folder/"addendum.tex"),
             "tex_sha256":m.sha(folder/"addendum.tex"),"pages":[{"page":i+1,"image":m.relative(p),
             "sha256":m.sha(p)} for i,p in enumerate(images)],"tests":test,"admission":m.relative(admission),
             "human_acceptance":"PENDING"})
    for name in ("REPORT.md","remaining-gaps.json","RESET-MEMO.md"):
        shutil.copyfile(folder/name,m.OUT/name)

def verify_result(folder):
    checked=tests()
    admission=m.latest("admit",current=True);document=m.latest("document",current=True)
    review()
    walk_anchors(m.read(admission/"basf-admission.json"))
    load_column_document(m.read(admission/"column-admission.json"),m.ROOT)
    from scripts.prospectus_refresh_sources import norm
    from scripts.prospectus_refresh_semantics import recognize
    p=m.read(admission/"reviewed-passage.json")
    m.require(m.sha(m.ROOT/p["column_binding"])==p["column_sha256"],"Passage column binding changed")
    regions=m.read(m.ROOT/p["column_binding"])
    column=next(r for r in regions if r["page"]==p["page"])["columns"][p["language"]]["text"]
    m.require(norm(column)[p["start"]:p["end"]]==p["quote"],"Passage offsets fail replay")
    expected=recognize(p["quote"])
    m.require(expected is not None,"Source-specific annotation no longer recognized")
    expected["source_passage"]=p
    m.require(m.read(admission/"semantic-annotation.json")==expected,"Semantic annotation changed")
    manifest=m.read(document/"document.json")
    m.verify_bindings({manifest["pdf"]:manifest["pdf_sha256"],manifest["tex"]:manifest["tex_sha256"]})
    rendered=m.read(m.OUT/"rendered-review.json")
    m.require(rendered["document"]==m.relative(document/"document.json") and
              rendered["pdf_sha256"]==manifest["pdf_sha256"] and
              rendered["inspected_pages"]==[p["page"] for p in manifest["pages"]] and
              rendered["status"]=="PASS" and rendered["human_acceptance"]=="PENDING",
              "Rendered review missing/stale/misrepresented")
    m.verify_bindings({p["image"]:p["sha256"] for p in manifest["pages"]})
    for target in re.findall(r"\\href\{([^}]+)\}",(document/"addendum.tex").read_text()):
        m.require((document/target).resolve().is_file(),"Broken source link")
    for name in ("REPORT.md","remaining-gaps.json","RESET-MEMO.md"):
        m.require(m.sha(m.OUT/name)==m.sha(document/name),"Stale public result "+name)
    baseline=m.read(m.latest("baseline")/"baseline.json")
    count=m.verify_bindings(baseline["files"]);prior=m.history()
    result={"status":"PASS","protected_files":count,"prior_phase_receipts":len(prior),
            "tests":checked,"source_review":m.sha(m.OUT/"source-review.json"),
            "admission":m.relative(admission),"document":m.relative(document),
            "rendered_pages_inspected":len(manifest["pages"]),"requests":{"used":188,"limit":212,"remaining":24,"new":0},
            "independent_adjudications":0,"production_promotion":False}
    m.write(folder/"verification.json",result)
    run={"schema":"prospectus-closure-refresh.v1",
         "git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=m.ROOT,text=True).strip(),
         "command":"python3 -m scripts.prospectus_refresh verify","python":sys.executable,
         "python_version":sys.version,"compute":"CPU only; CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden",
         "seeds":"N/A deterministic","environment":baseline["tools"],"plan":m.relative(m.PLAN),
         "plan_sha256":m.sha(m.PLAN),"result":m.relative(document/"REPORT.md"),
         "method":m.method(),"data":m.read(admission/"receipt.json")["inputs"],
         "phase_receipts":{m.relative(p):m.sha(p) for p,_ in prior},
         "wall_seconds_by_phase":{m.relative(p):r["wall_seconds"] for p,r in prior},
         "verification":m.relative(folder/"verification.json"),"verification_sha256":m.sha(folder/"verification.json"),
         "protected_baseline":m.relative(m.latest("baseline")/"baseline.json"),
         "protected_baseline_sha256":m.sha(m.latest("baseline")/"baseline.json"),
         "human_acceptance":"PENDING","independent_legal_adjudication":False,"production_promotion":False}
    m.write(folder/"run-manifest.json",run)
    shutil.copyfile(folder/"verification.json",m.OUT/"verification.json")
    shutil.copyfile(folder/"run-manifest.json",m.OUT/"run-manifest.json")
    print(__import__("json").dumps(result,indent=2))
