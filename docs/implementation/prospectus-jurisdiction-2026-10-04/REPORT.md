# Prospectus documentation and jurisdiction sources — 4 October 2026

The 24-document difficulty study is now incorporated in the LaTeX monograph and technical companion. All 24 source PDFs are retained as convenient named files with SHA-256 and receipt references. Three additional historical offering documents were downloaded and reviewed as candidates or controls. They do **not** establish three new cases of an adverse legal override: no readable primary court judgment was obtained in this acquisition stage.

## Reader documents and stored sources

- [Monograph](../../monograph/monograph.pdf): section 2.5, printed pages 48–51 (physical PDF pages 81–84).
- [Technical companion](../../monograph/technical-companion.pdf): appendix B, printed pages 8–13 (physical PDF pages 12–17).
- LaTeX additions: `docs/monograph/chapters/02e-prospectus-difficulty.tex` and `docs/monograph/appendices/prospectus-difficulty.tex`.
- [Original 24 PDF index](../../prospectus/jurisdiction-2026-10-04/prior-24-pdf-index.json); named copies under `docs/prospectus/difficulty-2026-10-04/pdfs/`.
- [New source index](../../prospectus/jurisdiction-2026-10-04/source-index.json), [reviewed catalogue](reviewed-catalogue.json), and [seven test specifications](test-specifications.json).
- The existing build also refreshed the `docs/proposal/` PDF copies and the process guide.

The manuscript preserves the actual old results: 24 distinct PDFs from 16 issuer families, 21 abstentions, three conditional positives, no runtime errors and 256 unresolved clause records. Mizuho's paid-amortization witnesses are recorded as a confirmed clause error. HPB's authority write-down wording, instrument/asset scope, incorporated documents and dates of proposed or future laws remain separate issues. No abstention rate is presented as an accuracy or legal error rate.

## New source findings

| Retained original | Verified source proposition | Use in further testing | Remaining evidence |
| --- | --- | --- | --- |
| [BES, 6 May 2014 final terms](../../prospectus/jurisdiction-2026-10-04/sources/jur-bes-2014-ptbeqkom0019/source.pdf), PTBEQKOM0019 | Senior status and 100% redemption fields, subject to stated prior-redemption qualifications; p. 4 confirms ISIN and Common Code. | Match a repayment promise to dated resolution measures and exact liability schedules; distinguish actual Eurosystem eligibility from stated intention. | Base of 17 July 2013 and four named supplements; exact measures, liability list and relevant judgments. No later transfer, retransfer, loss or recovery outcome established. |
| [Hellenic Republic, 28 March 2008 circular](../../prospectus/jurisdiction-2026-10-04/sources/jur-hellenic-2008-candidate/source.pdf), XS0292467775 | Principal floor, English governing law, and an immunity waiver expressly qualified by international conventions and Greek execution/attachment law (pp. 10, 17–18). | Separate entitlement, jurisdiction and enforceability; prevent automatic application of a domestic-law sovereign restructuring rule based on country alone. | Applicable enforcement law and exact proceeding/assets; series-specific restructuring record. Empty-text pages 27–28 are flagged for review. |
| [SID Bank, 9 March 2011 memorandum](../../prospectus/jurisdiction-2026-10-04/sources/jur-nlb-2011-candidate/source.pdf), XS0504013912 | State guarantee description refers to Article 13, transactions under Articles 11–12 and written creditor request; Notes use English law. | Bind statutory guarantees to their scope and conditions; distinguish SID issuer from NLB co-manager. | Authentic historical statute and any applicable judicial interpretation. No guarantee override or principal loss established. |

The Slovenian acquisition key retains the initial NLB search hypothesis for provenance. The catalogue corrects the issuer to SID. A prospectus assertion about non-retrospective constitutional protection is recorded as that document's assertion, not an independently checked constitutional rule. A judgment about a different bank, loan or security cannot supply missing facts about these issues.

BES is a five-page scan with no extracted text. All five pages were visually inspected; selected normalized fields are retained in [manual-review.json](../../prospectus/jurisdiction-2026-10-04/sources/jur-bes-2014-ptbeqkom0019/manual-review.json). The extraction manifest now says `OCR_REQUIRED`; neither the empty extraction nor this partial manual transcription is treated as complete text.

## Acquisition and resource status

This stage used the remaining ten authorised HTTP requests, taking the shared cumulative ledger from 102 to 112:

- Four EUR-Lex responses were HTTP 202 with empty bodies.
- The old CURIA index returned one retained HTTP 301 redirect; it was not followed automatically.
- Two LuxSE metadata queries and three PDF downloads succeeded.

Failed responses and their receipts remain stored. No failed response has been labelled a court judgment. The source hashes are distinct from the prior 24 PDFs. Documentation/source-metadata searches in the worktree and main checkout found no corresponding exact ISIN cases; this is not an exhaustive OCR search of every PDF in the repository.

An asynchronous request for up to 20 additional public requests remains pending. The existing ceiling is recorded at `docs/implementation/prospectus-evidence-closure/allowlist.json`, key `max_http_requests_including_continuation: 112`, and in the separate new acquisition policy. No extension has been assumed or installed. There were no paid model calls, installations or GPU work.

## Validation and review

The final recorded build used:

```text
python3 -m scripts.prospectus_jurisdiction_study build
```

It invoked `python3 -m scripts.build_reader_facing_monograph` in the worktree, passed in 11.237 seconds, and produced a 363-page monograph and 85-page companion. Document checks reported no errors, 136 citation documents, 301 citation occurrences and all 207 original source-unit labels retained. The exact commit, environment, inputs and PDF hashes are in [run-manifest.json](run-manifest.json); output is in [build.log](build.log).

```text
python3 -m scripts.prospectus_jurisdiction_study verify
```

The focused verifier passed: 24 original and three new PDFs; nine literal text anchors; seven test specifications; 39 local source links resolving from both PDF distribution directories; four protected document-baseline copies; and all 293 frozen engine-method files unchanged. See [verification.json](verification.json). This phase did not rerun or retune the engine. The old study's three harness checks and 909 prospectus checks remain historical validation of that study, not new legal evidence.

Rendered review covered monograph PDF pages 81–84 and companion pages 12–17. Two long appendix headings were shortened and the affected final pages rechecked. Tables, repeated table headers, accents, footnotes and source paths were legible with no observed clipping. The build and source-link checks establish document integrity, not human acceptance or independent legal adjudication. Rendered sources checked in this work: BES pp. 1–5, Greek pp. 10, 17, 18, 25, and SID pp. 1, 18, 24, 48. Other source assertions rely on inspected extracted text and retain the review limitations in the catalogue.

## Decision and next phase

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain LaTeX additions and 27 PDFs | Source-linked narrative/catalogue, storage hashes and build pass | No integrity/build veto | Human reading and independent legal review pending | Read the new section and appendix; keep provisional legal classifications | Production readiness or legal accuracy from a PDF build |
| Retain BES as an intervention candidate | Exact promise and ISIN visually established | Event admission veto: missing measures and dependencies | Instrument-specific intervention history | Obtain official measure and exact liability schedule, then incorporated documents and forum-specific decisions | A demonstrated loss, retransfer or recovery amount |
| Retain Greek and SID controls | Governing law, enforcement/guarantee clauses and issuer identity checked | Adverse-event labels withheld | Applicable external law and actual events | Test claim scope and obtain authentic legislation before assigning event labels | Country-wide application of Greek or NLB/Kotnik history |
| Stop network acquisition at existing cap | All ten remaining requests accounted for | Network continuation veto: 112/112 requests | Whether further allowance is authorised | Record a separate extension only after response, then fetch bounded exact-host sources | Rejection of the research direction or completion of event-source acquisition |

The next phase must bind each legal rule to issuer, ISIN or claim, governing law, forum, date and source edition. Prioritise the BES liability list and measures, its missing base/supplements and relevant judgments before expanding to another jurisdiction. Court holdings about jurisdiction or recognition must remain separate from substantive entitlement and payment outcomes.

Post-run red team: three successful PDF downloads could misleadingly look like three successful regulatory-event admissions. They are not. The strongest alternative explanation for a catalogue match is a manager name or country reference, as the SID correction demonstrates. Missing primary legal sources are the weakest evidence. Exact dated measures naming the security, plus the incorporated offering documents and relevant holdings, could change the current provisional classification.
