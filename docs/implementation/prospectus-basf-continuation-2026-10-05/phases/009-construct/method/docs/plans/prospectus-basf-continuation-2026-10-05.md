# BASF selection and incorporated-source continuation — 5 October 2026

## Decision and baseline

Continue the verified closure refresh in the existing feature/prospectus-evidence-master
worktree, at git 5bff0065dcc73268aab78cba3e9522b7455825ac. Preserve the original
engine, OCR round, refresh round, their source material, methods and receipts.
This phase closes a source-selection coverage gap; it does not produce a complete
German contract or an independently adjudicated legal answer.

Code and tests live in new prospectus_basf modules and tests/closure_basf.
Results live in docs/implementation/prospectus-basf-continuation-2026-10-05.
No downloads, installations, paid models, GPU use or external messages are planned.
The request allowance stays at 188/212. Local file edits are already authorised.

## Skeptical audit before implementation

| Risk found | Required correction |
| --- | --- |
| Prior 21 checked selections are an incomplete inventory | Account for every checkbox on final terms Part I pages 3–7 and all eight bilingual Yes/No provisions, including unselected Option II fields |
| Matching a label anywhere can confuse repeated TARGET or call labels | Match exact page, label, occurrence and bilingual response; require exhaustive, nonoverlapping source positions |
| Mapping final-term choices could be presented as a composed contract | Output a selection-to-clause map and explicitly scoped consumer; full nested substitutions and continuous operative German text remain open |
| BASF SE could incorrectly eliminate all guarantee references | Separate the initial Finance-only guarantee from the conditional BASF SE successor guarantee in section 10(d) |
| A 2022 annual-report filename might stand in for incorporated scope | Bind original and extraction identity, printed-page labels and each expressly listed range; retain the inconsistent overall 195–209 heading alongside notes 209–290 |
| Clean text could conceal marginal annotations or financial column mixing | Retain original text and label clause excerpts as locators; report admission establishes document/page identity, not corrected financial text or numeric interpretation |
| Historical passes may become stale when new code changes | Record current method/input hashes, numbered attempts and exact prerequisite receipt hashes; recalculate the next executable phase after changes |
| Successful tests could be called legal validation | Tests establish source coverage, deterministic reconstruction and fail-closed behaviour; adjudication and real legal outcomes remain unvalidated |
| Missing human labels could stop useful engineering | Independent review blocks promotion, while local source mapping and adverse controls continue |

Audit verdict: PASS for the revised bounded programme, with the above limits.
No baseline or original cohort result will be overwritten. Default engine promotion
is excluded. The first diagnostic is selector coverage and exact-source replay.

## Intent and evidence contract

Question: can every explicit Part I choice be accounted for and linked to the
appropriate controlling German provision (or excluded parent option), with the
retained 2022 report admitted only to its explicitly incorporated page ranges?

Comparator: the refresh phase 013 BASF packet (21 selections, report admission
pending) and the same original final terms, 2022 base and February 2023 supplement.

Primary engineering criteria:
- all Part I checkbox positions and all eight bilingual response pairs have exactly
  one source-bound decision; unrecognised, duplicated or contradictory choices fail;
- selected/excluded decisions have replayable German clause locators or an explicit
  excluded-parent explanation; no bare template becomes operative;
- issuer/currency conditions retain the distinction between an initial guarantee
  and a guarantee conditional on a later issuer substitution;
- report page numbers and explicit subranges match the retained English report;
  conflicting range descriptions remain visible, without silently changing either;
- a scoped successor consumer reconstructs results from sources/review/specification,
  rejects forged or stale packets and retains UNRESOLVED dossier/unknown legal outcome;
- focused adverse tests and final source/method/history verification pass.

Promotion vetoes: incomplete nested clause construction, missing agreements and
earlier/interim reports, incomplete extraction, independent adjudication, actual
event facts, unseen evaluation and intended-use acceptance.
Continuation vetoes: corrupted source/history, wrong edition, or missing source
needed for a specific assertion. Repair triggers: uncovered selector, ambiguous
anchor, wrong option/language, dropped qualification, stale method or review.
Counts and runtime are explanatory only. No legal accuracy rate or production
readiness follows from a passing run. This is deterministic; statistical ranking
and random seeds are not applicable.

## Assumptions and defaults

| Choice | Provenance/status | Reason | Failure mode / earliest check |
| --- | --- | --- | --- |
| Work on BASF first | Prior report priority; reviewed | Required sources are already retained | Wrong issue; bind ISIN, issuer and base/supplement links |
| English checkbox label plus German response | Bilingual original; development parsing choice | Existing extraction exposes glyphs and bilingual values | Repeated/contradictory labels; coverage and mutation controls |
| German clause locators | Final terms language selection; reviewed | German controls this issue | Locator mistaken for fully constructed text; consumer exposes no full contract or positive legal conclusion |
| Agent source review | Provisional | Permits local engineering | Not independent; record reviewer role and promotion veto |
| Physical equals printed annual-report page | Hypothesis | Sampled report labels agree | Verify every admitted page label plus rendered boundary pages |
| Exact reviewed source scope | Development convenience | Prevents unsupported generalisation | Another issue/rewording enters; reject changed identity and unknown choice |
| Existing Python/Poppler/LaTeX | Existing CPU environment | No installation needed | Missing tool/incorrect page geometry; record versions and render samples |

## Execution, repair and refresh

Entry point: python3 -m scripts.prospectus_basf PHASE

1. baseline: verify protected prior records and bind sources/method environment.
2. prepare: render new final-term, relevant German clause and report-boundary pages;
   create a source-review packet for actual agent inspection.
3. checks: implement selection coverage, clause locators, report admission and
   scoped consumer; run adverse source/packet/prerequisite tests.
4. construct: execute the validated consumer and save a before/after coverage
   comparison; preserve unresolved dependencies and financial-text limitations.
5. document: record findings, decision table, complete remaining-gap programme,
   reset memo and a short LaTeX addendum.
6. verify: check current inputs/method, test result, all bound outputs and rendered
   review; seal a manifest and refresh the next-phase work orders.

The driver derives next action from current method, input and prerequisite hashes.
Failures remain as numbered receipts; repair triggers the affected phase again.
Source or rendered review is an agent task, not a new user approval. Any repair
changing methodology invalidates checks and downstream output. Post-completion
work orders must distinguish implemented commands from still-unimplemented work.

## Programme beyond this bounded phase

BASF: finish continuous German clause construction, nested suboptions/placeholders,
applicable agreements/amendments and earlier/interim report scope. Then integrate
the complete dossier into an isolated successor reader.
Deutsche: qualify remaining bilingual operative pages, then evaluate full-issue
semantic handling; the existing three-page annotation is source-specific.
General engine: develop actor/modal/negation/scope/exception and conversion-alternative
handling against source-derived cases; independently adjudicate the 1467 records
(1307 unique spans). Counts are not accuracy.
Other dossiers: execute retained G13–G17 Enel/Unilever/Lloyds/SEB/LVMH/BBVA work orders.
BES: resolve 29 incorporated dependencies and content-based precedence of duplicated
risk factor 1.17.
Jurisdictions: admit exact Portuguese Annex 2B, HETA, Dana, Lloyds, Ukraine,
Popular/Snoras and historical Italian primary sources using genuinely new routes.
Regulation and finance: date-specific rules, issuer/event/client/bank facts,
nominals, calendars, rounding and settlement inputs.
Validation: assign the 25 review forms, obtain independent labels and an unexposed
cohort, run paired frozen evaluation, and obtain intended-use/manuscript acceptance.
Delivery: OCR/refresh/this round are uncommitted; integration and git delivery remain
separate from engineering acceptance.

## Pre-mortem and final review

The strongest misleading success would be exhaustive checkbox accounting with
wrong clause interpretation. Check full surrounding source passages and rendered
marginal conditions; retain German review as a promotion requirement. Another is
admitting financial pages while their extracted columns remain interleaved: admit
identity/scope only. Review generated output against the old packet and record what
actually closed, what failed, and the next smallest executable repair. A candidate
failure is not a rejection of the research direction.

