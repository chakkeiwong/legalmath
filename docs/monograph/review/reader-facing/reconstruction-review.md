> Historical review of the 235-page monograph and 69-page companion. The
> subsequent [round-four integration review](../round4/integration-review.md)
> and [delivery manifest](../round4/delivery-manifest.json) describe the current
> 244/76-page pair. Page numbers and appendix letters below belong to this
> protected earlier edition.

# Whole-volume reconstruction review

24 September 2026. Author/executor review; target-reader acceptance pending.

The reconstructed edition contains a 235-page main monograph and a 69-page
technical companion. The repair covers the front matter and all ten chapters.
The user's criticism was substantive: the earlier book led with engineering
records, asked tables to carry explanations, repeated definitions without
enough development and often sounded like an internal audit. The earlier
checklist and build results did not establish compliance with the writing policy.

The main question now connects the chapters: when a bank turns a circular into
a decision, how can it show that the decision preserves the intended meaning?
The SPI client and marketing incentive cases introduce the distinctions before
the formal representation or implementation detail needs them. A return to a
case must add a new difficulty: alternative financial routes, attachment of an
exception, missing facts, changed knowledge, disagreement, execution or review
responsibility.

## What changed throughout the book

Page numbers below are physical PDF pages. They identify rendered review
locations, not a claim that each whole chapter received independent acceptance.

| Part | Repair and teaching purpose | Rendered locations |
|---|---|---|
| Front | Two-page executive summary states the completed prototype, contribution, evidence and management decision. Task IDs, digests and build chronology no longer lead the book. | 1–3 |
| 1 | Starts with a fee discount and voucher assessed on Monday. Scope, subject and source version become consequences of that decision. Separates the business concern from any unmeasured claim about manual incident rates. Defines SPI before the main text uses it. | 9, 11 |
| 2 | Explains why a Monday decision needs the edition actually read. Replaces field-heavy inventories with prose and three short comparisons. Ms Lee's result is explained in ordinary language; source duties and proposed bank choices remain separate. Defines Boolean notation before the first condition. | 22, 28, 30, 32 |
| 3 | Explains the difference between a justified reading and preservation by a program. Introduces the entities, assumptions and comparison before the preservation equation. Explains grammar symbols and typed expressions before their use. Retains the equations and derivations. | 47, 48, 55 |
| 4 | Begins with the different questions posed by gifts, consent and payment. A numerical escrow case precedes the transition table. A short comparison explains four language families; the full software inventory is a reference in the companion. The earlier Catala/Stipula repetition repairs remain. | 70, 85, 97 |
| 5 | Rival readings must change a possible decision. Removes references to the author's conversation and replaces adjacent-repository detail with an account of what can transfer. Adds a numerical search-priority example, including why the score is not a probability. | 112, 120–121 |
| 6 | Begins with five readers sharing a missing annex. Recasts issue tracking, resolution, budgets and interrupted requests around the questions being investigated. A six-step explanation replaces controller pseudocode in the reading sequence. Short role and resolution tables follow prose. | 125, 129, 136, 143, 146–147 |
| 7 | Starts from behaviour at thresholds, missing evidence and later withdrawals. Explains the monetary rule before its representation. Replaces API and build recitals with what the bank receives and supplies. The Tuesday-approval/Wednesday-change example explains release identity. | 157–158, 171, 177 |
| 8 | Reconstructs the chapter around compliance, operations, engineering, the reviewer's decision and one change from source to release. The complete old workbench record is preserved separately. | 181 |
| 9 | Leads with material omissions and reviewer decisions. Groups cases by the contrast they teach, explains evaluation decisions in ordinary language and gives numerical conformal examples after introducing the symbols and assumptions. Detailed acceptance and reporting matrices remain available separately. | 184, 189, 192, 198 |
| 10 | Begins with a correct formula applied to the wrong entity or stale data. Relates responsibility, amendment, incidents and readiness to bank decisions. Replaces the dense readiness list with five questions and the evidence each owner needs. | 204, 222 |

The short main-volume tables use body-size type, increased row spacing and
placement beside their explanation. Most of the formerly dense comparisons now
have two columns. The role, boundary-case, experimental-arm and escrow tables
retain additional columns because the side-by-side relationship is their
purpose. The escrow table follows definitions and a numerical example; its
formal transitions are part of the argument.

The rendered pass found and repaired a one-word executive-summary continuation,
tables floating into the next discussion, remaining cramped summary tables,
an early unexplained RuleIR reference, a repeated Chapter 7 opening and two
diagrams still phrased in implementation terminology. Source searches helped
find these passages; matches were inspected rather than treated as style verdicts.

## Disposition of the technical and scientific content

The first reconstruction kept the engineering record as appendices in a
290-page PDF. That arrangement still asked the reader to carry an implementation
report inside the monograph. The final arrangement puts optional reproduction
detail in the companion. It does not move necessary mathematics out of the
argument or ask a reader to fetch an appendix to understand a derivation.

| Material | Final disposition and reason |
|---|---|
| Executive production history | Replaced by the management account; detailed historical task and test records remain in companion Appendix B. |
| Full SPI provisions, input fields and case records | Companion Appendix A; the main chapter explains their legal and operational significance before short comparisons. |
| Full workbench chapter and its executed/proposed increments | Companion Appendix B; the new Chapter 8 explains ownership, decisions and operation. Historical evidence is not represented as a new run. |
| Full software, role, resolution, acceptance, evaluation and readiness matrices | Companion Appendix C; main summaries preserve the distinct questions and point to the full lookup records. |
| Compiler APIs, exact serialization, controller pseudocode, blocked-report JSON and worker recovery record | Companion Appendix D; main text explains the rule, sequence, unresolved decision and recovery consequences. |
| Literature collection procedure, local-repository inventory and source-archive mechanics | Companion Appendix D; the main argument retains source findings, limits and relevant citations. |
| Build manifests, digests and reproducible-build details | Companion section D.9; the main chapter teaches why approval belongs to the program actually tested. |
| Equations and mathematical arguments | All 35 original display groups and all 37 equation labels remain in the main volume. Added text introduces quantities and explains examples; display formulas were not changed. |
| Original listings | All 21 retained: four in the main text where they illustrate the formal language, seventeen in the companion. |
| Source findings and qualifications | Unfavourable Stipula–KeY compilation findings, the maintenance-duty inconsistency, conditional mathematical results, source/reviewer limits and the adverse production-readiness verdict remain. |

Four teaching figures were reworded: `teach-P-01b-complete-dry-run-05` now follows
the tested rule into approval; `-06` shows a timed consent withdrawal;
`teach-M06-17` explains an interrupted request and a late answer; and
`teach-M07-12` ties approval to the program examined. Their labels and conceptual
jobs survive. The original figure text is in the protected source checkpoint.
The bank workflow in the new Chapter 8 is an additional figure.

The automated check verifies 243 protected checkpoint files and accounts for all
207 original source-unit labels. This is not a sentence-by-sentence semantic
equivalence certificate. Rewritten prose has an author disposition in this
review; raw inventories and technical records have an explicit destination.
Source units can now be taught differently or split between explanation and
reference. The historical exact-transform checker is not claimed to validate
the reconstruction. Page reduction alone is not evidence of better teaching.

## Evidence attached to this edition

`python3 scripts/build_reader_facing_monograph.py` builds both documents and
their cross-references, runs the current checker and updates the proposal PDF
alias. The final checks pass: no missing original display, listing, source label,
citation key or reference target; no duplicate label; no unresolved or overfull
LaTeX diagnostic; and no clipped or empty page under the recorded geometry check.
The alias PDFs match the delivered PDFs byte for byte.

The citation set still contains 81 archived documents and 211 occurrences across
the pair. For 204 occurrences the citation key and entire paragraph/row context
match the earlier scoped author judgment exactly. Seven changed occurrences in
two paragraphs have explicit judgments: the HYPO passage and the six-source
mapping of the Chapter 9 cases. The current binder checks source and reading-note
identities too; changed meanings cannot receive support through fuzzy matching.
This editorial binding does not claim a fresh current-law or retraction search.

The added UCT illustration evaluates to 1.672983 and 1.229193, agreeing with the
rounded text. The conformal examples use ranks 18 for nineteen calibration
observations and 5 for four observations at the stated error level; the latter
selects the infinite-threshold branch. Those are deterministic arithmetic checks,
not evidence for legal calibration. See `worked-example-checks.json`.

The rendered review inspected 36 selected pages spanning the title, executive
summary, contents, every chapter, rewritten tables, mathematical introductions,
examples and changed diagrams. Five companion pages cover its opening and all
four appendices. All 304 pages received automated geometry/text checks. This
does not claim that all 304 pages were reread sequentially or that a target human
reader has accepted the voice. The selected images and page identities are under
`.localresources/monograph-reader-facing/rendered-final/`; the delivery manifest
binds that selection to the PDFs.

## Remaining gaps

Human comprehension and naturalness remain unvalidated. The earlier user review
was negative and is not superseded by an author checklist. The present work is a
concrete repaired candidate for a new reading. In particular, the recurring
diagrams and transitions still need to earn their place with unfamiliar readers;
figure density does not establish understanding.

Independent legal judgment is still missing for an adopted bank scope. The
source collection does not establish a complete authority perimeter, and the
demonstrations do not establish the correct interpretation for every client,
product or event. Literature retrieval gaps and untested backend comparisons
remain recorded in the retained literature review and beside the relevant
sources. Whole-compiler correctness and transfer of published guarantees to the
bank's setting remain limited to the stated arguments and checks.

The proposed evaluation has not established live-model legal accuracy, useful
omission detection, calibrated legal uncertainty or measured reviewer benefit on
representative independent cases. Scripted examples and old test counts cannot
supply that evidence. Production identity, case-level confidentiality,
independently controlled audit integrity, real host concurrency/revocation and
incident procedures still require implementation and deployment-specific checks.
The separate product-risk review gives the repair and acceptance conditions.

The decision is to deliver the reconstructed documents for reader review.
Successful compilation and preservation allow that review to proceed; they do
not promote the prose to human acceptance or the prototype to legal or bank use.
