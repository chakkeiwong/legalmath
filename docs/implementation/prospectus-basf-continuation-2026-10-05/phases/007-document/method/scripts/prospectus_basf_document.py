"""Write the BASF continuation result and retain programme-wide work orders."""
import json
import re
import xml.etree.ElementTree as ET
from scripts import prospectus_basf as m

def test_result(path):
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    counts = {k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ("tests","failures","errors","skipped")}
    m.require(counts["tests"] > 0 and not any(counts[k] for k in ("failures","errors","skipped")),
              "Focused checks not clean")
    return counts

def run(folder):
    packet = m.read(m.latest("construct").parent/"basf-selection-admission.json")
    comparison = m.read(m.latest("construct").parent/"comparison.json")
    tests = test_result(m.latest("checks").parent/"tests.xml")
    gaps = m.read(m.prior.OUT/"remaining-gaps.json")
    for gap in gaps:
        gap.pop("command",None)
        gap["implementation_status"] = "FURTHER_IMPLEMENTATION_OR_EVIDENCE_REQUIRED"
    gaps[0].update(status="EXPLICIT_SELECTIONS_AND_DETAILED_REPORT_RANGES_CHECKED",
        closed="63 explicit choices (55 checkboxes and 8 bilingual response pairs); German clause locators and 92 expressly listed annual-report pages",
        next_action="Construct continuous controlling German text with nested alternatives/placeholders and cross-references; resolve incorporation-range discrepancy, earlier/interim reports and applicable agreements/amendments",
        dependency="Source construction, applicable documents and independent German adjudication")
    gaps += [
        {"gap":"General clause semantics", "status":"OPEN",
         "next_action":"Repair actor, modality, antecedents, exceptions, scope, negation, conversion alternatives and creditor-amendment/redemption distinctions using source-derived cases",
         "dependency":"Validated extraction and independent labels; 1467 records / 1307 unique spans remain unadjudicated",
         "implementation_status":"FURTHER_IMPLEMENTATION_REQUIRED"},
        {"gap":"Successor integration and delivery", "status":"OPEN",
         "next_action":"Integrate fully constructed issues and qualified bilingual pages into an isolated successor reader; end-to-end regression, scoped acceptance, commit and synchronization",
         "dependency":"Current consumer exposes selection facts only; original engine unchanged; OCR/refresh/continuation work uncommitted",
         "implementation_status":"FURTHER_IMPLEMENTATION_REQUIRED"},
    ]
    work = {
        "schema":"prospectus-next-work-orders.v1",
        "implemented_commands":{
            "verify_current_phase":"python3 -m scripts.prospectus_basf status",
            "replay_if_stale":"python3 -m scripts.prospectus_basf run",
            "inspect_current_admission":".venv/bin/python scripts/run_prospectus_closure_next.py inspect " +
                m.relative(m.latest("construct").parent/"basf-selection-admission.json") + " --outline"},
        "next_development_phase":{
            "task":"Continuous BASF German Option I construction",
            "implementation_exists":False,
            "inputs":[m.relative(m.latest("construct").parent/"basf-selection-admission.json"),
                      "docs/implementation/prospectus-evidence-closure/phases/S2/attempt-017/source-work-orders.json"],
            "first_actions":["Separate base margin instructions from body while preserving every word and continuation.",
                "Inventory every nested branch and placeholder in German Option I pages 108–133.",
                "Bind each deletion or substitution to final terms and test retained section 10 successor guarantee.",
                "Preserve issuer-specific tax, default, notice and amendment qualifications.",
                "Evaluate source completeness before end-to-end reader integration."]},
        "remaining_gaps":gaps, "http_requests":{"used":188,"limit":212,"remaining":24},
        "promotion_criteria_pending":["Independent adjudication","Unexposed cohort","Actual applicable facts","Intended-use acceptance"],
        "complete_autonomous_programme":False,
    }
    m.write(folder/"remaining-gaps.json",gaps)
    m.write(folder/"next-work-orders.json",work)
    report = f"""# BASF selection and report-scope continuation

The new optional BASF consumer accounts for all 55 checkboxes and eight bilingual
Yes/No provisions on Part I pages 3–7 of the 6 March 2023 final terms for
XS2595418596. The previous packet covered 21 choices. Every decision has a source
location and either a German clause locator or an explicit excluded-parent
explanation. These are selection facts; continuous operative German terms still
need construction and the full dossier remains UNRESOLVED.

## Findings that matter to interpretation

The issue is BASF SE's EUR500 million 4.250% notes due 8 March 2032. German
controls. It selects annual ICMA interest without a stub, the dated issuer call,
the make-whole call, and the 75% clean-up call. The distinct interest-date call,
scheduled holder put, renminbi call and transaction-trigger call are not selected.
The change-of-control holder right remains selected and requires the rating
condition and exercise procedure; it must not disappear merely because the
separate scheduled put is marked No.

The clean-up clause requires both acquisition of at least 75% of original
principal and the corresponding reduction in the global note. It concerns the
whole residual issue, with 30–60 days' notice, par and accrued interest. The
Finance-only initial guarantee is excluded for this BASF SE issue, while
section 10(d)'s guarantee condition for a later issuer substitution remains.
Majority creditor amendment under SchVG remains distinct from issuer redemption.
These conditions were inspected in the German original; no actual exercise or
enforceability conclusion is established.

The February 2023 supplement expressly lists the auditor report (197–202),
income statement (203), balance sheet (205–206), cash flows (207), and notes
(209–290) of the retained English BASF Report 2022. Their 92 physical/printed
page bindings are checked. Its broader heading instead says 195–209. Both
statements remain in the packet; full incorporation scope is unresolved.
The English auditor report says its German original is authoritative. Report
admission establishes identity and detailed page scope; column order, financial
values and the German auditor original have not been qualified here.

## Engineering evidence and decision

{tests['tests']} focused tests passed with zero failures, errors or skips.
They cover changed checkboxes, bilingual conflicts and flips, unknown/duplicate
choices, additional responses, source identity changes, altered source review,
forged/reserialized packets, changed report labels, lost language qualifications,
and stale prerequisite/method/input bindings. The earlier 123 OCR/refresh tests
are included in this total. This is deterministic development evidence, without
independent labels or an unseen evaluation cohort.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain optional selection consumer | Exhaustive explicit choices and exact replay pass | Full clause construction and independent review pending | Nested alternatives and filled fields | Construct continuous German clauses | Complete contract or general parser |
| Admit detailed report page scope | Original, edition, header and range checks pass | Broad-range discrepancy and text layout remain | Full incorporated scope and controlling auditor original | Resolve scope; qualify required text | Financial interpretation |
| Continue development | Protected baseline and focused checks pass | No source-integrity continuation veto | Complete dossiers, rules and actual facts | Execute next work orders | Programme closure or production readiness |

The strongest alternative explanation is that the new coverage count merely
enumerates a template without resolving operative meaning. The consumer therefore
exposes locators and selected/deleted facts and refuses a complete contract or
legal answer. Every nested branch and field still needs separate construction.
A contrary original-page reading, new applicable amendment or independent
interpretation would require repair. This is an implementation continuation,
not a legal accuracy result or a rejection of the research direction.

## Execution and repair record

The protected entry baseline binds 8,923 files. Git baseline is
5bff0065dcc73268aab78cba3e9522b7455825ac on
feature/prospectus-evidence-master in .worktrees/bond-gap-closure.
Original engine code and prior evidence remain unchanged. No downloads,
installations, paid model calls, external messages or GPU initialization occurred.
The HTTP ledger remains 188/212, leaving 24 requests.

The first source diagnostic found a marginal-table interruption in the report
heading anchor; the shorter exact range anchor fixed it. Preparation initially
failed because Pillow was absent from the project virtual environment. The
existing tfgpu Pillow installation rendered contact sheets with GPU hidden.
The failed receipt remains preserved. Source images were also inspected through
compressed copies because large base64 transfers truncated; the originals remain
bound and unchanged. All 37 prepared pages were inspected for this bounded review.

Numbered receipts preserve each attempt, commands, environment, method/input
snapshots and elapsed time. Changed inputs, methodology, source review or upstream
receipts invalidate dependent phases. The source reviewer is the executing agent,
not an independent adjudicator. Human manuscript acceptance remains pending.

## Remaining programme and next step

remaining-gaps.json lists the dossier, bilingual extraction, semantic, BES,
jurisdiction, regulatory/financial, independent/unseen validation and integration
work. The next development phase is continuous BASF German clause construction,
then complete source scope and isolated reader integration. It is specified in
next-work-orders.json but is not yet implemented as an autonomous closing phase.
The current runner's executable repair loop covers this bounded continuation.

OCR, refresh and continuation files remain uncommitted. No commit, merge or push
was performed in this continuation.
"""
    (folder/"REPORT.md").write_text(report)
    m.write(folder/"test-summary.json",tests)
    tex = r"""\documentclass[11pt]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[a4paper,margin=25mm]{geometry}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{booktabs}
\usepackage{hyperref}
\setlength{\parindent}{0pt}
\setlength{\parskip}{7pt}
\title{BASF 2032 notes: selections and incorporated report scope}
\author{Prospectus engine development addendum}
\date{5 October 2026}
\begin{document}
\maketitle
The final terms dated 6 March 2023 for BASF SE's EUR500 million
4.250\% notes due 8 March 2032 (ISIN XS2595418596) contain 55 checkboxes
and eight bilingual Yes/No provisions in Part I, pages3--7. The new
optional consumer accounts for all63 decisions, compared with21 in the
previous packet, and binds them to source locations and German clause
locators. German controls. Continuous operative German terms and the
complete issue dossier remain unfinished.

The distinctions among redemption provisions are consequential. The
dated issuer call and make-whole call are selected, as is the clean-up
call. The separate interest-date call, scheduled holder put, renminbi
call and transaction-trigger call are not selected. The
change-of-control holder right is selected: its rating condition and
exercise procedure survive the deletion of the separate scheduled put.
The clean-up clause on base-prospectus page122 requires acquisition of
at least75\% of the original principal \emph{and} reduction of that
principal in the global note. It permits redemption of the whole
residual issue, with30--60 days' notice, at par plus accrued interest.

Issuer identity also changes which branches apply. The initial
Finance-only guarantee in section2(3), pages110--111, is excluded for
this BASF SE issue. Section10(d), page129, nevertheless retains a
guarantee condition for a later issuer substitution. Removing every
guarantee reference would lose that condition. Section11 separately
addresses majority creditor amendment under the SchVG.

The supplement dated27 February2023 lists the following parts of the
retained English BASF Report2022 on its page12:
\begin{center}
\begin{tabular}{lr}
\toprule
Incorporated item & Printed and physical pages\\
\midrule
Auditor's report &197--202\\
Income statement &203\\
Balance sheet &205--206\\
Cash flows &207\\
Notes &209--290\\
\bottomrule
\end{tabular}
\end{center}
The92 detailed page bindings pass identity checks. The same table's
broader heading says195--209, which does not encompass the listed notes.
Both descriptions remain recorded. Full incorporation scope therefore
requires resolution; the broader heading was not silently corrected.
The auditor's report on page197 also states that its German original
is authoritative. Admission here establishes source identity and
detailed page scope, with financial values and column reading order
still unqualified.

\newpage
\textbf{Validation and remaining work.}
TESTCOUNT focused engineering tests passed, including changed
selections, bilingual conflicts, unknown options, altered source
identity, forged packets, stale review and prerequisite bindings,
report-page changes and a lost language qualification. They include
the123 earlier OCR and refresh tests. These exposed development cases
have no independent legal labels or unseen evaluation result.

The loader reconstructs each accepted packet from the protected
sources and the reviewed specification. Its successor view supplies
selected/deleted facts and clause locations while retaining an
unresolved dossier and no legal answer. The counts measure coverage;
they do not establish legal accuracy or production readiness.

The next local task is to construct continuous German Option I terms,
including nested alternatives, filled fields, cross-references and
issuer-specific conditions. Earlier and interim reports, applicable
agreements, amendment coverage and the report-range discrepancy also
remain. Beyond BASF, the programme still needs broader bilingual
extraction, general semantic repair, the other issuer dossiers, BES
dependencies and precedence, jurisdiction primary sources and actual
regulatory and financial facts.

Independent adjudication of the original1,467 records (1,307 unique
spans), assignment of the25 review forms, an unexposed evaluation cohort
and intended-use acceptance remain prerequisites for promotion.
The executable repair loop covers this continuation; the next
contract-construction phase still requires implementation.

The entry baseline protects8,923 files. No network request was made;
24 of212 authorised requests remain. The original engine and previous
evidence are preserved. This addendum records provisional development
review, with human manuscript acceptance pending.
\end{document}
"""
    # Insert readable spaces around numeric facts without changing their meaning.
    tex = tex.replace("TESTCOUNT",str(tests["tests"]))
    for old,new in [("pages3","pages 3"),("all63","all 63"),("with21","with 21"),("least75","least 75"),
                    ("with30","with 30"),("page122","page 122"),("section2","section 2"),("pages110","pages 110"),
                    ("Section10","Section 10"),("page129","page 129"),("Section11","Section 11"),
                    ("dated27","dated 27"),("February2023","February 2023"),("Report2022","Report 2022"),
                    ("page12","page 12"),("The92","The 92"),("says195","says 195"),("page197","page 197"),
                    ("the123","the 123"),("original1,467","original 1,467"),("the25","the 25"),
                    ("of212","of 212"),("protects8,923","protects 8,923")]:
        tex = tex.replace(old,new)
    (folder/"addendum.tex").write_text(tex)
    m.command(["latexmk","-pdf","-interaction=nonstopmode","-halt-on-error","-outdir="+str(folder),
               str(folder/"addendum.tex")],folder,"latex",timeout=120)
    info = m.command(["pdfinfo",str(folder/"addendum.pdf")],folder,"pdfinfo")
    page_count = int(re.search(r"Pages:\s+(\d+)",info).group(1))
    m.require(1 <= page_count <= 4,"Unexpected addendum length")
    for page in range(1,page_count+1):
        m.command(["pdftoppm","-f",str(page),"-l",str(page),"-singlefile","-scale-to","1350",
                   "-png",str(folder/"addendum.pdf"),str(folder/f"addendum-{page}")],folder,f"render-{page}",45)
    m.write(folder/"rendered-pages.json",{"pdf":m.relative(folder/"addendum.pdf"),
        "pdf_sha256":m.sha(folder/"addendum.pdf"),
        "images":{m.relative(folder/f"addendum-{p}.png"):m.sha(folder/f"addendum-{p}.png") for p in range(1,page_count+1)}})
    for name in ("REPORT.md","remaining-gaps.json","next-work-orders.json"):
        (m.OUT/name).write_bytes((folder/name).read_bytes())
    (m.OUT/"RESET-MEMO.md").write_text(
        "# BASF continuation reset memo\n\nRun python3 -m scripts.prospectus_basf status for current, hash-derived state.\n"
        "Authoritative reports are in numbered phase folders. Review of all 37 source pages is provisional development review.\n"
        "Coverage: 55 checkboxes, 8 bilingual responses, 92 detailed report pages. Full German contract and dossier unresolved.\n"
        "Read next-work-orders.json before further implementation; next contract-construction phase is specified but unimplemented.\n"
        "Preserve prior receipts, OCR data and 25 existing independent-review forms. No new HTTP requests or git delivery.\n")

def verify(folder):
    doc = m.latest("document").parent
    render = m.read(doc/"rendered-pages.json")
    review = m.read(m.OUT/"rendered-review.json")
    m.require(review["pdf"] == render["pdf"] and review["pdf_sha256"] == render["pdf_sha256"],
              "Stale rendered review")
    m.require(review["images"] == render["images"] and review["status"] == "VISUALLY_INSPECTED",
              "Rendered image review incomplete")
    m.require(review["human_acceptance"] is False and review["independent_legal_adjudication"] is False,
              "Rendered review scope overstated")
    m.prior.verify_bindings({render["pdf"]:render["pdf_sha256"],**render["images"]})
    test_result(m.latest("checks").parent/"tests.xml")
    for name in ("REPORT.md","remaining-gaps.json","next-work-orders.json"):
        m.require(m.sha(m.OUT/name) == m.sha(doc/name),"Current result differs from numbered result")
