# Real scanned final terms: extraction, rows and qualifications

Status: source preparation, raw extraction, analysis and packet authoring are
retained. R6 completed with exact coverage of 663 tests and current passing
receipts, and is committed as `c6ad78f76`. The image-identity repair is admitted
for integration below. Historical attempts and their frozen inputs stay intact.

## Question and protected comparator

Can the current OCR intake and reviewed correction/annotation adapters preserve
the designated text, table relationships and qualifications in an actual scanned
prospectus, with every accepted reading traceable to its original occurrence?
The document is the six-page Banco Espirito Santo final terms dated 14 July
2011, series 23, ISIN PTBEQBOM0010. Its retained PDF is
`docs/prospectus/corner-cases-2026-10-04/sources/jur-more-bes-1315263/source.pdf`,
SHA256 `17184c68cb8637c8943e47ceef6ba723a51ae7dc242fb0204e9196d2f5683e79`.

The baseline is the current, unmodified `extraction.scan` and `ocr_worker.py`
at the completed worker-recovery method. Historical OCR is evidence of earlier
failures, not the current extractor's expected output. The expected printed
text and cells are fixed by inspecting all six retained page images before a
new OCR trial. Agent transcription is development evidence; independent legal
acceptance remains absent. Source authenticity and the referenced base
prospectus/supplements are separate unresolved questions.

The intended correction boundary binds an original occurrence, its page-image
hash and a complete sequence of raw-to-display operations. The later reproduced
method-name defect and reviewed repair below distinguish intended enforcement
from the previous implementation.
Corrected display has no inherited bounding box. Annotation admission then
maps supplied reading spans back to selected raw occurrences; inserted or
uncertain text cannot become semantic evidence. Layout admission consumes
reviewed governing targets, but does not infer their legal meaning. The
existing Docling sidecar disables OCR and table structure for born-digital
pages. Running that configuration on this image-only document would test an
inappropriate profile and cannot support rejection of Docling.

## Research intent and evidence contract

The proposed mechanism is explicit page/cell review plus the existing
correction and annotation consumers. Expected failures are identifier errors,
crossed table columns, Portuguese diacritics and a lost negative qualification.
In particular, page 6's `Yes` describes an intended holding arrangement. Its
following paragraph says recognition as Eurosystem collateral depends on
eligibility criteria. The two statements must survive together. Neither an
isolated `Yes` nor complete text extraction establishes actual eligibility.

| Role | Predeclared requirement |
|---|---|
| Primary engineering criterion | All six pages and all frozen critical cells are retained; every assisted critical reading has exact raw/image correspondence and the complete qualification reaches the real service. |
| Primary adverse criterion | Wrong source/image, stale correction, ambiguous partial replacement, missing governed text and wrong table occurrence are rejected or leave the relevant dependency unresolved. |
| Automatic criterion | Report exact character/order success on the frozen targets separately from supplied cell selection and correction. Do not call reviewed region selection or supplied meanings automatic discovery. |
| Promotion veto | Lost critical text, borrowed geometry, guessed relation, unlabelled assistance, a qualification omitted from a claimed complete reading, or a wrong source accepted. |
| Continuation veto | Changed protected PDF/oracle/method, unknown runtime, corrupted evidence, missing required diagnostic, unexplained output change or the stated resource bound. |
| Repair trigger | An actual adapter/consumer failure on the retained real input. Preserve that attempt, review one bounded repair, and continue if the comparator and harness remain valid. |
| Explanatory only | Word counts, test totals, text coverage outside the fixed targets and elapsed time. |

No ranking of packages, unseen-document accuracy, complete multilingual family
coverage, independent legal truth, real collateral eligibility, real coupon
entitlement or production native confinement follows from passing this case.
The service's six existing questions are preserved; an eligibility question
must not be silently substituted for Q1's contractual principal-loss question.
Raw and assisted results, unknown source meanings and missing incorporated
sources remain explicit in the report.

## Ordered execution

1. Freeze `oracle.json` with the six-page inventory, historical review-image
   identities, critical expected text and image regions. Inspect images 1–6,
   including signatures without authenticating them. Re-render the original PDF
   with the current pinned PyMuPDF runtime and bind each full-page image hash.
   Region coordinates are manually reviewed image coordinates, not OCR boxes.
2. After the R6 validation has completed and its work is committed, admit a
   single fresh current-worker extraction. Pin the interpreter, imported
   distribution, worker, English model, PDF and this plan. Retain complete raw
   output, geometry and a full service report. Validate the exact page sequence
   and image identities before interpreting any text result.
3. Score the raw critical occurrences without consulting corrected historical
   text. Measure page-order text separately from text inside supplied regions.
   Inspect actual failure locations. Do not retry unchanged OCR to seek a pass.
4. Prepare explicit assisted maps from the failed and passing cells. Preserve
   every raw character; use only image-supported character corrections. Record
   any row reordering with source spans, retaining the original raw order.
   Missing/unreadable content remains inserted or uncertain, which vetoes a
   semantic reading. Verify the complete page-6 qualification and its attachment
   to the intended-arrangement answer. Preserve page-3 form and Portuguese-law
   facts without resolving their legal relationship to the ICSD wording.
5. Pass the admitted maps through the actual service and annotation adapter.
   Compare with the same source without assistance, and with one critical
   occurrence/qualification omitted at a time. Preserve all six questions and
   the rest of the raw graph. Do not declare the whole instrument complete
   merely because a designated interval has been interpreted.
6. If a local source repair is reproduced, retain the failure and revise this
   plan before editing. Run focused meaningful regressions, an actual consumer,
   and the required current phase checks. If no source repair is needed, retain
   the new actual consumer as data/usage evidence; do not rerun unrelated passing
   code checks. Record attribution, remaining families and the next executable
   package in RESULT, RESET and NEXT-PROGRAM, then commit the completed work.

## Defaults, budgets and environment

| Choice and provenance | Justification and status | Failure mode and earliest check |
|---|---|---|
| Existing 300-DPI English PyMuPDF/Tesseract profile | Protected recovery baseline; not a recommended multilingual default | Portuguese words may fail; retain exact per-cell misses rather than infer package unsuitability. |
| Existing tfgpu interpreter, PyMuPDF 1.27.2.2 | Known installed OCR runtime; CPU intentionally selected | `.venv` lacks PyMuPDF and may import main; verify imports, hashes and checkout explicitly. |
| Six pages, fixed critical cells | Source-specific reviewed denominator | A convenient subset might conceal omissions; retain all pages and identify unreviewed meanings outside the critical set. |
| Manually selected image regions | Supplied layout hypothesis, never automatic output | Wrong row or clipped text; inspect all regions before OCR and require wrong-occurrence controls. |
| Whitespace normalization only | Harmless layout comparison baseline | Accent/identifier errors must remain errors; no case folding, punctuation removal or edit-distance pass threshold. |
| Existing conservative native reuse veto | Reviewed safety boundary | A successful OCR run is not immutable dependency closure; retain the veto. |

Use only local retained files. No installation, network, live model or GPU work
is authorized by this plan. `CUDA_VISIBLE_DEVICES=-1` must precede optional
imports. Allow 60 seconds for inventory/rendering, 300 seconds per actual OCR
launch, 900 seconds for the first complete scan/service trial and 100 MB of new
evidence including a 1-MB metadata reserve. Review the measured first extraction
before scheduling repeated service calls. Do not run a long comparison in
parallel with R6 or interpret concurrent elapsed time as package performance.
Every attempt is immutable and records commit, command, imports, CPU mode,
source/model/method hashes, timing, plan and output paths; random seeds are N/A
for this deterministic input. Source/plan/script changes require a new attempt.

## Skeptical audit before preparation

PASS for image/oracle preparation only. The protected source and actual runtime
are named; old OCR is not used as a current oracle; text coverage and test totals
cannot promote meaning or eligibility. Automatic and assisted work have separate
criteria. The current sidecar's born-digital settings are not silently transferred
to a scan. Stop conditions and repair triggers are distinct. Preparation changes
none of the running R6 bindings, and final scan admission awaits its committed
result. The smallest next action is binding and inspecting the six page images.

The admitted preparation command is:

```text
timeout 60 .venv/bin/python docs/implementation/prospectus-integration-closure/real-scan/source-inventory.py
```

The runner verifies protected image dimensions and hashes, the pinned renderer
and the active R6 method before/after rendering. It retains one immutable
`inventory/attempt-001` with full page identities and the 23 supplied crops.
The eight relationships are supplied review targets, not discovered output.
All crop contents must be inspected before freezing the scan trial admission.

Pre-mortem: a corrected display can trivially repeat a supplied answer while
mapping the wrong raw word. Exact original occurrences, image regions and
wrong-occurrence controls must therefore accompany display equality. Two
identically broken workers can agree; the predeclared page images and printed
targets supply a separate source check. A character pass can still lose the
relationship between `Yes` and its qualification; the downstream omission
control, not character count, answers that question.

## Additional admission: image-binding branch probe

Source review found a specific mismatch before the BES worker trial:
`corrections.admit` requires an image hash only when `'ocr'` occurs in the
unit's method. Actual `retained_ocr_units` emits
`retained-pymupdf-tesseract`, which lacks that substring. This is a hypothesis
about our adapter, not a reproduced package failure. No existing closure test
mentions this image-identity requirement.

A bounded, in-process admission probe may run during the R6 regression because
it only reads its already sealed English baseline and writes a new evidence
directory. It launches no OCR worker and edits no bound method. Use the actual
retained service source graph, with a complete source interval and a copy-only
display operation. A matching page image should pass; an absent or wrong image
must reject. A literal `ocr` method control must reject a wrong image, and a
plain-text control may omit an image. Preserve any surprising admission as a
reproduced local defect. No broader text or legal conclusion follows.

```text
timeout 30 .venv/bin/python docs/implementation/prospectus-integration-closure/real-scan/image-binding-probe.py
```

Allow 30 seconds and 1 MB of evidence. The real retained unit is the baseline;
the two modified method labels are discriminating controls only. Check the
active R6 method and input manifest before/after. The primary criterion is the
exact admission/error for each case; counts and timings are explanatory. Changed
evidence, unexpected errors or method drift veto continuation. Actual adverse
admission triggers a reviewed narrow correction after R6 completion; it does
not authorize editing the active run. The earlier source-review note describes
the intended adapter boundary; this probe tests whether the implementation
enforces it for the real producer's output.

Skeptical probe audit: PASS. This uses actual producer output and a deliberately
literal method-name control to distinguish a local dispatch error from OCR
quality. It preserves both the active validation and the protected six-page
oracle. No new native call, mutable runtime dependency or proxy promotion is
introduced. BES raw extraction still waits for the committed R6 comparator.

## Reproduced correction defect and isolated repair design

`image-binding/attempt-001` reproduced both adverse admissions in 0.0068 seconds
on a real worker-produced source occurrence. Matching-image and plain-text
controls passed; the literal `ocr` control rejected the wrong image. The root
cause is the local string-based producer classification, not a failing OCR
package. The previous source-review description is therefore the intended
boundary, not a correct account of its enforcement before this repair.

Recognize the actual `retained-pymupdf-tesseract` producer and its
`retained-original-text-or-blank` fallback, while preserving the historical
`ocr` check. Any unit carrying an image identity also requires it. A required
identity must be a valid SHA256 string and the supplied value must match;
missing or malformed provenance cannot waive the requirement. Plain text
without an image remains supported. Do not change rendering, word grouping,
OCR settings, source quotations or corrected-text geometry.

Preparation may write an isolated candidate under `real-scan/candidate/` and
test copies under `/tmp`. The current worktree source and its active R6 method
stay fixed. Use actual `retained_ocr_units` output from the protected English
raw-worker baseline, plus its explicit no-word fallback control. Exercise
matching/missing/wrong image values, missing/malformed source identity, an
image-bearing unfamiliar method, ordinary plain text, and the actual service
intake. These are deterministic engineering controls, not another OCR run.
Retain old and candidate results separately; a candidate failure triggers one
reviewed bounded correction. Integration still awaits R6 completion and commit.

Skeptical repair-design audit: PASS for isolation only. The test uses the
real producer and actual service instead of reproducing the same method-name
heuristic. It distinguishes required provenance from optional plain text,
preserves existing geometry and raw text, and cannot modify the active method.
Allow 60 seconds per isolated test invocation and 5 MB of evidence. Exact
candidate source, tests and commands must be retained before running. No new
package/model, network call, runtime change or default OCR policy is involved.

The isolated commands, in dependency order, are:

```text
timeout 60 .venv/bin/python docs/implementation/prospectus-integration-closure/real-scan/check-candidate.py baseline
timeout 60 .venv/bin/python docs/implementation/prospectus-integration-closure/real-scan/check-candidate.py candidate
```

The runner copies the recorded source, actual worker data and PDF into a fresh
temporary root, explicitly verifies the imported correction module, then runs
the same 20 controls. Baseline must exhibit exactly 16 `DID NOT RAISE`
failures with its four valid controls passing; candidate must pass all 20.
Any other failure is a harness/implementation problem requiring inspection.
The baseline result's `PASS` means reproduction succeeded, not that adverse
admissions are acceptable. Neither command changes the active worktree source.

The first baseline test attempt exposed a local fixture error: the isolated
adapter result lacked the `visible` flag normally added by `source_graph.build`.
Sixteen adapter cases therefore failed earlier with `Source occurrence
unavailable`. The complete service controls did reach the boundary and
reproduced both missing/wrong-image admissions. This result invalidates the
minimal fixture, not the candidate (which has not run) or the OCR package.
The original test bytes are preserved in `candidate/versions/` with their
recorded hash. Mark the known retained fixture visible as the builder does;
the separate full-service controls continue to check the actual builder path.
The revised runner uses new numbered attempts and refuses an unchanged method.
Run baseline 002, inspect its exact failures, then candidate 001 only if the
baseline is discriminating. Skeptical repair review: PASS for this one fixture
repair; the actual case data, candidate patch and expected image behavior stay
the same. No active R6 file changes.

## Reviewed scheduling revision for the raw scan

The initial plan unnecessarily made a new read-only worker trial depend on
committing R6. The new trial can bind the exact already frozen source snapshot
without editing it, and no timing ranking or promotion depends on its result.
Waiting for a commit would add no evidence about OCR characters or page order.
Permit the raw baseline while R6 is `RUNNING`, with R0–R3 current and passing,
provided every file in its frozen method still matches. A failed/interrupted
R6 state refuses this admission. If R6 has finished, require its sealed PASS.
Record the commit and all uncommitted method hashes; never label this a clean
committed-method trial. Production source integration still follows the R6
checkpoint and commit. This revision supersedes only the earlier raw-trial
scheduling prerequisite; the source/oracle and scientific criteria stay fixed.

```text
timeout 900 .venv/bin/python docs/implementation/prospectus-integration-closure/real-scan/run-baseline.py
```

Use the existing one-thread CPU OCR worker for at most two six-page launches.
Check the first measured run before the service launch; above 120 seconds,
retain it and review scheduling instead of proceeding. Concurrent runtimes are
explanatory only. The actual source graph and both fresh complete outputs must
match, all six image identities must equal the independently inspected pages,
and all 23 original target identities must remain in the denominator. Missing
relationships or text are candidate failures that trigger assisted analysis;
method/input corruption or unknown output drift is a continuation veto.

Skeptical scheduling and command audit: PASS. Source preparation and isolated
tests already verified that none of these new files belongs to R6's bindings.
The baseline runner explicitly inserts the worktree source, pins the separate
OCR interpreter/model, binds the frozen review, checks page inventories and
retains automatic text presence separately from supplied cell projection.
It performs no mutation of source/test/phase inputs and claims no concurrent
performance comparison. Wrong baselines, method drift and surrogate promotion
are explicitly vetoed. No source repair is admitted by this scheduling change.

## Observed raw trial and analysis repair

The first BES trial retained two equal fresh raw/service extractions and every
independently rendered page identity. It then stopped because the supplied
responsibility region had no word centres. Inspection of the retained output
shows the text is present, with `FinalC)` and merged words, but the signature
inflated its word boxes from y=237.60 to y=283.01 PDF points. Their centres lie
below the narrow printed-text region fixed before OCR. The exact raw line and
boxes remain available. Other targets include the old ISIN error and Portuguese
character substitutions. All six product questions retain unresolved/partial
status. No baseline extraction needs repeating.

The empty-region condition was incorrectly treated as a continuation veto in
the runner. It is a failure of this geometry-selection candidate, and should
remain a failed target under the frozen 23-target denominator. Repair analysis
with a separate script reading the immutable attempt; do not rewrite its
result, source images, oracle, method or execution evidence. Verify its exact
failure reason, complete raw/service identity, page hashes and source snapshot,
then retain every target, including the unmapped one, in `analysis/attempt-001`.
An invalid source or unequal outputs still vetoes analysis. No OCR is launched.

```text
timeout 60 .venv/bin/python docs/implementation/prospectus-integration-closure/real-scan/analyze-baseline.py
```

Allow 60 seconds and 5 MB of analysis evidence. The script records the exact
critical occurrence rows and text misses; automatic relationships remain absent.
Skeptical review: PASS for analysis repair. The candidate failure is not being
removed or relabelled as success, and the denominator and comparison rule stay
fixed. Explicit manual selection of the responsibility line is a later assisted
intervention, not an improvement to the automatic geometry score. The adapter
image-binding defect remains separate and its isolated repair is still pending
integration. Fundamental package unsuitability is not established by this case.

## Assisted source packet admission

Analysis 001 retains all 23 targets: 14 have exact normalized page-text
presence; 16 are exact within supplied regions. Seven supplied-region targets
fail: responsibility, ratings, ratings qualification, ISIN, clearing label,
clearing value and intended-arrangement label. No automatic relationships are
proposed. These are descriptive fixed-case counts, not accuracy estimates.

Author a separate supplied packet using those exact raw intervals. Select
the actual page-4 responsibility line explicitly by its identity and quotation;
record the failed centre rule without changing its score. Apply eight exact
image-reviewed replacements: the responsibility line; `S&P:` spacing; `usinga`;
the extra ISIN character; `S.A/` punctuation; `Liquidacdoe`; `Mobilidrios`;
and `ina`. All other intervals copy their original bytes. Each replacement
accounts for the whole admitted raw interval and carries the retained page
image hash. No corrected text receives a raw bounding box. Full-source words,
including signature noise and unreviewed text, remain in the source graph.

The source packet authoring command is:

```text
timeout 60 .venv/bin/python docs/implementation/prospectus-integration-closure/real-scan/author-review.py
```

It must validate all 23 joined displays against the pre-OCR oracle, retain each
segment's original occurrence, record the explicitly supplied eight
relationships and source-bind the whole packet. It does not make an actual
service result. The subsequent consumer must use the repaired image guard,
run corrections and annotation through P1/P2/P3 and all six questions, and
demonstrate matching raw sources and rejected stale image/quote/correction
inputs. Each relationship's required target set includes both endpoints; for
a qualification, it includes the full qualification and its affected value.
Removing one target must expose an unresolved dependency. Omitting one supplied
meaning must restore unknown interpretation on its original occurrences.

This is a supplied source-preservation reading. `effect=none` means the
designated identifier, row or collateral/ratings statement is not itself an
admitted principal-write-down or compulsory-conversion instruction; coupon
wording is `coupon`, and responsibility remains `unknown`. The rest of the
document and all missing incorporated sources remain unknown. No eligibility
answer is introduced, no scope is marked complete and no actual rate/eligibility
event is inferred. An uncertain correction cannot support semantic evidence.

Skeptical authoring audit: PASS. The complete source images and exact raw
misses were inspected. Manual selection, text replacement and relationship
provision are explicitly assisted. The geometry miss remains a failure and
all original critical targets stay in the denominator. Exact quote/image
binding and omission tests distinguish preservation from copying a desired
answer. The authoring uses no native worker or active-source mutation; allow
60 seconds and 5 MB of new evidence. Consumer admission follows packet review
and integration of the already tested image guard.

## Integration and consumer admission after R6

R6's final verification passed: all nine manifests, 663 unique collected test
identities, every current phase receipt, unchanged method and final attribution
equality. Its completed work is committed as `c6ad78f76`. Verify the isolated
candidate archive and before/after diagnostic manifests, then copy only its
`corrections.py` and `test_closure_correction_images.py` to the matching source
and test locations. Record the exact predecessor and integrated hashes before
testing. The predecessor correction source must still equal the candidate's
recorded baseline. No new OCR execution is needed.

Run the 20 actual-producer/image controls through the closure dispatcher with
a retained JUnit result, under a 60-second bound. Then run:

```text
timeout 300 .venv/bin/python docs/implementation/prospectus-integration-closure/real-scan/consumer.py
```

The consumer must preserve the complete raw graph and all six question statuses,
recover exactly every supplied original occurrence through the annotation
bridge, and retain 23 meanings, eight dependencies and the full qualifications.
It tests 23 single-meaning omissions, eight required-endpoint omissions and
seven adverse admissions: wrong image, missing image, wrong raw occurrence,
stale graph, uncertain replacement, partial replacement and wrong table value.
The wrong-occurrence control chooses a distinct sufficiently long unit so that
it reaches exact quote validation rather than failing only on interval length.
All target unit sets were inspected and are disjoint, so a single omission is
a valid matched control. Each dependency requires both complete endpoints.
No node or relation is attributed to automatic discovery or actual eligibility.

Skeptical integration/consumer review: PASS after tightening the wrong-occurrence
control. The previous unexecuted control selected a 12-character unit for a
78-character interval; its expected quote error was therefore wrong. The revised
control reaches the intended validator. The comparator remains the retained
current-worker output, not corrected historical text. Supplied meanings are
explicit premises, unreviewed meanings remain unknown, and no scope is declared
complete. Source corruption and unexplained changes still veto continuation;
an expected OCR miss or a reproduced local consumer defect triggers analysis
or a separately reviewed repair. Exact artifacts, CPU-only environment and
resource bounds are retained. No package ranking or default-policy promotion
follows from this deterministic case.

## Consumer result and current-method refresh admission

Consumer 001 passed in 9.029 seconds with 52,338,485 evidence bytes. All 23
source readings, eight relationships, 23 meaning omissions, eight endpoint
omissions and seven adverse admissions pass. The complete original graph and
the six question statuses remain equal to the unassisted comparator. This
supports the assisted preservation criterion on this one document. The raw
OCR/region candidate still fails its declared critical-target criterion.

Bind the retained analysis, authoring and consumer results into R3, together
with the oracle, source-review freeze, baseline manifest and this plan/scripts.
Add the twenty image regressions to R3's actual test selection. Add two focused
real-BES regressions: original raw/image identity plus complete source readings,
and omission of the full eligibility qualification while `Yes` survives.
The latter must make its explicit dependency unresolved in both questions.
They use the retained current-worker input and actual current service, without
launching OCR or changing the frozen oracle. These tests preserve meaningful
downstream behavior; they do not assert an eligibility answer.

Refresh with:

```text
timeout 6300 .venv/bin/python docs/implementation/prospectus-integration-closure/real-scan/run-validation.py
```

The runner collects exact identities (expected 685 after 22 added tests),
executes R0–R7 serially, then only the otherwise uncovered nodes, writes exact
coverage, updates the reviewed attribution and runs R8 and final refresh.
Each phase requires a current valid passing receipt; all collected identities
must be covered without failure, error or skip. Test totals explain coverage
only. Bind the source, tests, this plan, scripts and supplied packet before
starting, and reject drift. R4 keeps its reviewed 4,500-second internal bound
(preceding actual run 3,144.351 seconds); the outer command allows 6,300 seconds.
The new source/test/controller changes invalidate the previous all-source
phase bindings, so this is required current-method regression. Do not repeat
the OCR trial, installed package exercises or an additional aggregate suite.
Retain at most 100 MB for this real-scan package, with metadata reserve.

Skeptical refresh review: PASS. The new real-case tests run the actual service;
sealed consumer evidence remains explicitly at its recorded method. Raw OCR
failure is recorded separately from valid subsequent analysis and assisted
success. Attribution identifies the local guard defect and the earlier probe
errors without blaming the OCR package or silently changing its defaults.
The full current-method phase evidence is necessary under the existing
controller contract; no weaker historical receipt is relabelled as current.
After passing results, update the reset/result notes and commit. New substantive
preparation may proceed while R4 runs only in separate files that are outside
these frozen bindings, with no native performance comparison or source edit.
