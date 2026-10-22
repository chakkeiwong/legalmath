# Hybrid PDF page intake repair, 11 October 2026

## Reproduced problem and question

The retained BES 2008 and 2009 annual reports contain six audit pages whose
body is an image but whose headers or footers contain native text.
`source_graph.pdf_units` emits those native lines and flags only a page with
zero lines. It therefore omits the audit body without a page-level coverage
warning. `extraction.scan` and `ocr_worker.main` support only whole-document
OCR with a maximum of twenty pages; the original reports have 286 and 229
pages. Raising that limit or treating nonempty text as completeness would not
repair the underlying selection and coverage problem.

The engineering question is whether an explicitly reviewed subset of original
PDF pages can acquire additional OCR evidence with correct source identity,
original page numbers, native-text preservation, image provenance and explicit
coverage limits. The comparator is the actual source-graph intake retained in
`bes-original-acquisition/attempt-001/intake-diagnostic/`, not an empty-text
synthetic scan. The 256-page 2010 report supplies a native-text control.

## Evidence contract and research intent

| Role | Criterion |
|---|---|
| Primary engineering criterion | Exact source hashes and page counts; OCR exactly the declared original pages; retain native units byte-for-byte; bind model, worker, image and runtime identities; reject missing, duplicate, out-of-range and wrong-source evidence. |
| Content promotion criterion | Every predeclared critical span on a selected page must be checked against its image. An OCR phrase or word count alone cannot certify a page or report. Raw mismatches stay visible; corrections need separate image-bound review. |
| Promotion veto | Missing selected-page result, changed source/model, incorrect original pagination, incomplete critical span or lost native evidence. |
| Continuation veto | Changed protected comparator, corrupted original, method drift during a run, absent required model/runtime, or exhausted bounded attempt with no reviewed changed method. |
| Repair trigger | Correctly located OCR with text errors calls for the existing separate correction workflow; it does not establish fundamental package failure. |
| Explanatory only | Runtime, extracted characters, word totals, file size and test totals. |
| Nonconclusions | No complete-report extraction, package ranking, automatic legal interpretation, independent authenticity, historical availability, entitlement or collateral eligibility. |
| Artifacts | Frozen page oracle, original-page OCR results, per-page critical-span comparisons, controls, method/environment manifest and a result note. |

## Defaults and skeptical audit

The six pages come from inspected source images, not a text-length heuristic:
2008 PDF 245–248; 2009 PDF 174–175 (printed 173–174). Selection is supplied
review, not an automatic detector. It may miss other image pages, so unselected
page coverage remains unreviewed. English at 300 dpi and one CPU thread reuse
the existing reviewed OCR profile; they are a baseline, not an optimal setting.
The pinned English model is
`docs/prospectus/closure-2026-10-05/tools/eng.traineddata`, SHA-256
`7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`.
The previously validated `/home/chakwong/miniconda3/envs/tfgpu/bin/python`
supplies PyMuPDF 1.27.2.2 for CPU OCR.
No install, live model call or GPU use is needed.

Before OCR, freeze critical text from all six rendered pages: translation
qualification, reporting period, consolidated versus individual scope, complete
opinion paragraph, opinion date, and the individual-account NCA exception
paragraph. Exact whitespace-normalized comparison is a diagnostic; no fuzzy
match silently passes a material OCR substitution. These reviewed spans are
assisted reference evidence, not independent legal adjudication.

The most misleading success would be finding one date while omitting an
accounting exception, or silently renumbering a six-page extract to 1–6. The
earliest diagnostic checks original-page identities and all frozen spans.
Wrong-hash, omitted-page, repeated-page, wrong-count and wrong-model controls
must reject before any consumer promotion. CPU is deliberately selected with
`CUDA_VISIBLE_DEVICES=-1`. The baseline bound is 300 seconds for six pages,
one attempt; a failed candidate can motivate a documented repair but cannot
authorize an unchanged retry. No stochastic ranking is planned.

Audit verdict: PASS for the bounded diagnostic and design. Core integration
requires its own admission after the active R4–R8 evidence seals. Do not edit
the active controller, its imported source/tests, source packets or declared
root plan while R4 runs. The separate acquisition directory is outside that
method binding.

## Ordered execution and refresh

1. Seal the three candidate identity reviews and retain the acquisition/search
   manifest. Preserve all fourteen historical unresolved dependencies.
2. Freeze the image-reviewed critical spans; implement and run a standalone
   page-selection prototype in the acquisition directory. Preserve the original
   source files and original page numbers. Retain full native and OCR layers.
3. Record exact matched/mismatched spans and controls. Refresh this plan from
   the result before integration. If OCR is inaccurate, distinguish a local
   selection/consumer gap from package recognition errors.
4. Complete the current controller R4–R8 sequence. Then admit a versioned
   optional hybrid profile in the product, keeping the existing whole-document
   profile compatible. Bind selected page identities and model provenance.
   Surface native-only coverage as unreviewed; do not auto-promote mixed pages.
5. Exercise the actual source graph and onward-source consumer with omission,
   date, issuer, page-identity and correction controls. Account for duplicate
   native/OCR text explicitly; never erase native evidence or silently merge
   different readings. Refresh affected validation only after code is frozen.
6. Update reset/result/master/next-program notes with actual outcomes. Keep
   source acquisition, extraction coverage, consumer admission and independent
   legal acceptance as separate decisions.

Exact prototype command after its oracle and inputs are frozen:
`timeout 300 /home/chakwong/miniconda3/envs/tfgpu/bin/python docs/implementation/prospectus-integration-closure/bes-original-acquisition/hybrid_probe.py`.

## Admission correction

The first invocation with `/tmp/prospectus-adoption-tools/bin/python` failed
at `import fitz` before creating an attempt or running OCR. That environment
contains other adoption tools but not PyMuPDF. The summary's interpreter
assumption was wrong. The retained worker-recovery baseline identifies
`/home/chakwong/miniconda3/envs/tfgpu/bin/python` and PyMuPDF 1.27.2.2; use
that existing interpreter with GPU deliberately hidden before imports. This is
an environment correction, not an OCR/package result or a repeated unchanged
candidate. Preserve the failed invocation in `hybrid-preflight-001.json`.

## Probe result and implementation admission

The corrected runtime completed the six selected original pages in 23.755
seconds, retained 69,179 native units without modification and rejected twelve
mutated source/count/page/model records. Fifteen of eighteen critical spans
match raw OCR after correcting one faulty reference transcription; three
opinion paragraphs differ only in the missing accent in Espírito. The enlarged
original image establishes that the initial accounting-exception transcription
was wrong. Preserve oracle v1 and the first result; the separate review retains
oracle v2 and its reason. Existing image-bound correction maps are appropriate
for the accent repairs. This is evidence of useful bounded extraction with
specific errors, not evidence of package unsuitability or general accuracy.

During the frozen controller run, stage copies of the three changed modules
under `bes-original-acquisition/candidate/`; import those explicitly in a
separate focused harness. Do not edit the product copies until R4–R8 seal.
The optional `hybrid_profile` requires exact source page count, an ordered
unique selection of at most twenty original pages, pinned language models and
300-dpi CPU extraction. Preserve legacy whole-document scan behavior. Fresh
and retained hybrid results require the exact selected-page sequence, original
source hash/count, model identity and per-page image geometry. Keep native
units unchanged and OCR units separately identified; duplicates require
explicit disposition rather than silent deduplication. Native-only and OCR
coverage remain unreviewed unless separately admitted.

Focused controls must cover long native PDFs with image pages, invalid
selection before worker launch, omitted/repeated/renumbered pages, wrong
source/model/count, missing image, invalid geometry, native preservation and
actual service consumption with image-bound corrections. Then run the actual
BES originals through the staged source graph. New evidence must name staged
module paths/hashes and cannot be described as product integration. The
implementation audit passes: the earliest checks distinguish adapter faults
from OCR errors, and core edits remain outside the active method.

The first staged consumer attempt failed before service intake: the standalone
probe retained its runtime identity in `started.json`, not in each raw page
record. Preserve `candidate-consumer-001/started.json`; a changed adapter
constructs the runtime field with the frozen probe-method identity and writes
`candidate-consumer-002/`. It does not relabel the raw probe or claim that a
normalized field was supplied by the original worker. The primary source/page
hash and model controls remain mandatory.

Staged attempt 002 passed the real source-product interface on all three
reports (104,996 units; six original audit pages had OCR layers), but review
identified a further gap: a retained OCR record could assert an arbitrary
image hash without rerendering the selected source page. That is a provenance
defect in the staged adapter, not a package recognition failure. A changed
method now rerenders retained selected pages with the pinned CPU worker and
compares image hashes, dimensions and original page numbers. The focused fake
fixture isolates schema controls; separate real-worker checks exercise both
fresh OCR and retained-image verification. Preserve attempt 002 as staged
evidence and use attempt 003 for this stronger method.

## Product admission after the phase ladder sealed

The final staged candidate passed 24 focused controls and a source-product
execution on all three originals. The retained 2008/2009 OCR pages were
rerendered from their bound original PDFs; the wrong-source control rejected.
R0–R8 then sealed at the v3 controller method, with one R6 fixture failure
repaired and one stale R8 review binding revised. These receipts describe the
pre-hybrid product method, so they cannot be reused as post-integration
validation. No live OCR run by itself establishes complete document coverage.

Copy the exact staged extraction, worker and graph implementations into the
product, add focused product-source controls to the already R3-bound scan test
file, and run the new controls plus backward compatibility checks before
starting a refreshed R0–R8 ladder. R4's 4,500-second ceiling remains; an
unrelated failed phase stops its descendants pending a reviewed repair. After
the ladder, update the R8 attribution review for new source/controller hashes
and rerun only the affected R8 phase, not the historical receipts. This is a
new product method and warrants revalidation; the 24 staged controls and
104,996-unit candidate graph are comparison evidence, not substitutes.

Skeptical audit: the exact baseline is the sealed pre-hybrid v3 method, the
primary engineering criterion is the actual product consumer with retained
original-page identity and unmodified native text, the vetoes are source,
image, page and run-manifest drift, and no test count or OCR word total is a
promotion metric. The controller will refresh the next phase after each run.
The strongest residual risk is unseen mixed-image pages in the rest of the
reports; explicit page selection does not discover them. Audit verdict: PASS
for optional intake integration, with general source-completeness still open.
