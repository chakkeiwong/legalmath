# Complete bond report: PDF conversion and correctness review

## Scope and decision

The user requests a PDF of the complete 26-bond report and asks whether its
classifications are correct. The target reader should see every outcome,
reason, source location and material qualification. Preserve the original
Markdown, JSON and CSV in a temporary baseline before editing. Produce
`docs/implementation/bond-loss-absorption-classification/results.pdf` from the
current report with a reproducible conversion script. Only this report and its
publisher are in scope; the frozen reader and prior execution records remain
evidence of what actually ran.

## Evidence contract and skeptical audit

The question is whether the reported reasons support the selected securities
under the user's definition: explicit principal write-down or compulsory
conversion to common shares, including prospectus-disclosed statutory bail-in.
The comparator is the retained issue-specific source text and its definitions,
not a human answer or another model's label. A successful test suite proves
neither source completeness nor the correctness of English interpretation.

Pass criteria for the PDF are preservation of all 26 rows and all substantive
qualifications, working source links, successful compilation and readable
rendered pages without clipped text. For the correctness review, examine the
selected witnesses, series identity, definition links and known omissions.
Wrong-security or non-operative witnesses require repair; missing evidence
requires qualification or abstention. Formal test counts are explanatory for
this source review, not promotion criteria for legal truth. No accuracy score
or universal legal correctness will be claimed.

The initial skeptical audit found concrete citation problems: Standard
Chartered's summary selected a Newco reorganisation clause rather than the
conversion trigger; Duke's 2054 senior notes selected the 2034 redemption
clause. Correct these through a generic, evidence-based presentation rule or
explicitly preserved source correction, not an issuer-indexed answer table.
Retain the original engine explanations and frozen results. Investigate any
counterexample to the actual classification before changing its answer.

Assumptions: dated offering documents remain the analysis scope; complete
current SFC eligibility/sanctions clearance is a separate question. Ordinary
creditor restructuring is excluded under the previously stated feature
definition. Cash repayment alone is insufficient to prove absence of a
write-down clause. A missing recognised mechanism is only a qualified negative.

The revised plan passes review for a bounded source/presentation audit. Its
remaining unproved premises are English interpretation, supplied document
scope and incorporation completeness. No external model or human quality
assessment is required. Preserve a source-hash-bound review note, build
manifest and rendered-page checks; record any remaining defects explicitly.

## Execution

1. Read all selected supporting witnesses and targeted linked definitions;
   check corporate negative reasons and senior-bank statutory-bail-in clauses.
2. Correct misleading presentation with a focused regression check; preserve
   the original reports and avoid changes to the frozen classification model.
3. Generate the PDF using installed Pandoc/XeLaTeX. Use one readable entry per
   bond instead of compressing the complete table onto narrow pages. Preserve
   all text and provide portable issuer/source hyperlinks.
4. Inspect extracted text and every rendered page. Record source/PDF hashes,
   conversion command, content checks, bounded correctness findings and limits.

No scientific ranking is involved. Stop only if the source/PDF is invalid or
the requested conclusion lacks support; repair the affected part or publish
the specific unresolved limit rather than implying unconditional correctness.

## Executed result

The complete six-page PDF was built and every page inspected. The source table
was expanded into numbered bond entries, preserving every field and all
surrounding prose. The requested negative examples remain qualified negatives;
all 26 classifications are unchanged. Two incorrect explanation witnesses
were replaced through the generic summary filter. Four focused regression
tests passed; the existing delivery verifier passed again without modifying
the frozen reader or prior run artifacts.

The first build exposed unavailable optional `fancyhdr`/`titlesec` packages;
the renderer now uses standard LaTeX layout without additional installation.
Pandoc's raw-LaTeX block handling required fenced raw blocks for the bond
entries. PDF extraction checks explicitly remove only the expected page-number
footer so that paragraphs spanning pages can be compared without dropping text.

| Review area | Result and limit |
| --- | --- |
| Reader comprehension | Every bond has a visible identity, result, reason and source; the final page explains the correctness limits. This is author inspection, not a human quality score. |
| Formal integrity | Decisions are unchanged; archived finite/SMT/native results retain their original conditional scope. |
| Source fidelity | All selected witnesses were read; linked common-share/amount definitions and the two defective citations were checked. Source selection and unrestricted interpretation remain unproved. |
| Typography | All six pages inspected at readable resolution; no clipping, split bond entries, missing characters or overfull boxes found. |

The next semantic repair is recorded in the reset memo. PDF creation and
source inspection do not close the reader's interpretation/generalization gap.
