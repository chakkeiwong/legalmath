# Repair invalid OCR word geometry without losing source text

## Reproduced problem and intended result

The actual Portuguese 2009 P1 consumer fails on one out-of-page `:` word in
PDF page 177. Original width 640.63 pt; generated word extends to 1037.02 pt.
The rest of the five-page worker output survives its preliminary checks. The
same generated PDF reproduces the defect with both default and accurate-bbox
word extraction. This is not floating-point tolerance. Source images and the
worker are retained under `bes-original-acquisition/portuguese-2009-reports/`.

Question: can the product preserve all recognized text and image provenance,
isolate unusable geometry, and continue conditional report analysis without
presenting false spatial precision? The comparator is the rejected raw worker
and unchanged original PDF, plus the four passing source-report cases. The
primary criterion is exact text/identity preservation with explicit unknown
geometry and tested downstream behavior, not merely a successful import.

## Skeptical review before implementation

The strict current rejection is correct under its existing all-boxes-in-page
contract. Calling it a faulty validator would be wrong. A new optional
degraded-geometry mode changes the contract and must remain explicit. The
producer may have a native recognition/PDF-placement defect; provenance checks
cannot repair it. Missing CLI means direct Tesseract comparison has not run.
Use available authoritative source/code and an isolated sidecar for a direct
engine probe if needed, preserving versions. Do not install into `tfgpu` or
assume another OCR wrapper provides identical geometry semantics.

No source implementation changes until the current report-scope controller
finishes, so its running method remains fixed. Do not rerun the failed P1 or
geometry probe unchanged. The candidate below is a reviewed hypothesis, not an
automatic default change. Any installed-component request must use a narrow
approval if the actual sandbox requires it; local edits need no new approval.

## Refreshed admission and skeptical audit, 12 October 2026

The source-report ladder finished: R0–R8 are current engineering PASS, including
428 R4 checks. Its sealed evidence remains the comparator. The saved official
MuPDF writer trace has completed step 1 below: the oversized advance is already
encoded in the generated PDF. Recognition versus grouping/placement remains
unresolved; another identical OCR call would not distinguish them.

Audit verdict: execute the bounded local contract repair. The earlier suggestion
to pass `bbox=None` was incomplete: both layout adapters unpack every word box.
They must explicitly refuse spatial projection on an affected page. Text anchors
may retain exact offsets and page identity with unknown geometry; corrections
already withhold boxes and must retain their image requirement. Freeze and test
these downstream obligations before the actual Portuguese consumer. No engine
installation or default profile change is necessary for this hypothesis.

The research intent is lossless conditional text use in the presence of one
unusable spatial observation. The mechanism is a separately selected
`pymupdf-hybrid.v2` profile with
`geometry_policy=preserve-text-without-invalid-box.v1`. Its scope is finite,
ordered boxes outside the original page. Non-finite, inverted, malformed and
unbound inputs remain errors. The v1 profile stays strict. The inherited 1e-3
rounding tolerance is a compatibility baseline, not evidence of OCR accuracy;
both profiles receive boundary controls. Original-page dimensions and image
identity are independently rerendered for retained inputs.

Promotion criteria: retain every native unit and OCR word, exact text offsets,
raw invalid coordinates, source/image identity and a typed geometry issue;
preserve existing valid-case consumer answers; consume the eleven frozen legal
passages or explicitly retain any recognition miss for a separate correction.
False spatial mapping, qualifier loss or silently promoted source/date facts
veto promotion. Corrupted source evidence or a changed method during a run veto
continuation. A recognition miss triggers an image-bound correction, not a
whole-package rejection. Timing and unit counts are explanatory only.
Successful local checks establish neither automatic layout, correct recognition
geometry, complete source coverage nor independent legal acceptance.

New evidence goes in `ocr-geometry-repair-2026-10-12/` beside the sealed
source-report package. The executable `scripts/prospectus_geometry_program.py`
will retain its control freeze, exact commands, code/input hashes, CPU-only
runtime, results, bounded attempts and refreshed next action. It will execute
focused controls, the retained Portuguese worker through real P1 and report
consumers, and matched previous consumers. It must not retry a failed stage
unchanged. After reviewed attribution, the existing closure controller performs
one finite pass over stale receipts and refreshes between phases. No old receipt
or sealed source is rewritten. Seed policy: N/A, deterministic engineering
replay; no statistical ranking is claimed.

## Ordered program

1. Inspect the generated OCR PDF content/text transforms and installed upstream
   PyMuPDF/MuPDF source or official code. Identify whether the oversized box is
   already in recognition output, introduced by invisible-text placement, or
   introduced by word extraction. The preserved default/accurate outputs are
   evidence; a CLI call is not currently available.
2. Freeze controls for valid boxes, small render rounding, non-finite/inverted
   boxes, genuinely outside-page words, missing source images and wrong PDF
   identity. Freeze expected unknown-geometry behavior separately from normal
   known geometry. Include a critical legal word with invalid geometry, not
   only this punctuation token, so the policy cannot hide substantive loss.
3. If supported, add a versioned optional admission that preserves the original
   box in raw evidence and records `bbox=None` plus a typed geometry issue in
   the product. Retain exact text/source offsets and the full-page image hash.
   The strict profile must continue rejecting the original input. Layout and
   image correction must refuse spatial claims for the affected word unless
   an independent image-bound geometry review supplies them. Page/source
   completeness remains unresolved. No clipping or token deletion.
4. Run the actual Portuguese P1 and new report-scope consumer against the
   independently frozen eleven passages. A missed critical span triggers a
   separate reviewed correction; a false mapped location, hidden omission,
   changed input or lost qualifier vetoes promotion. Compare unchanged normal
   inputs with the four prior consumer answers and raw source maps.
5. Classify the result: our all-or-nothing integration contract, OCR-PDF
   geometry defect, recognition error, or unresolved mechanism. A usable
   degraded path is not evidence the producer geometry is correct. A failed
   candidate does not establish package unsuitability. Retain source-code,
   exact commands, runtime versions, source/image hashes, limits and matched
   output maps; then refresh affected closure phases and documentation.

The saved PDF inspection is complete. The next executable action is freezing
the controls and current source evidence before implementing the repair. Stop the candidate for
corrupt evidence or untested downstream spatial claims. Missing independent
legal review blocks legal acceptance, not this explicitly conditional repair.
