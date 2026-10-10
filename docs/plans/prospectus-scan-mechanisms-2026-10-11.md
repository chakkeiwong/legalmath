# Separate OCR recognition from supplied-region selection

Status: bounded local diagnostic admitted while the real-scan regression runs.
Write only this new plan and `docs/implementation/prospectus-integration-closure/scan-mechanisms/`.
No active source, test, real-scan plan, script, oracle or phase binding may change.

## Question and evidence contract

Why does the current English OCR route miss seven critical supplied regions
of the BES final terms: word recognition, page segmentation, or our word-centre
selection rule? Compare two mechanisms against the retained current-worker
output and the same 23-target image oracle. First compare centre selection with
positive-area box intersection on the original words. Then run the supported
installed PyMuPDF OCR API on the exact already rendered supplied crops, keeping
the same English model and 300-DPI profile. There is no Tesseract command-line
executable in the current environment. Installed `Pixmap.pdfocr_tobytes`
supports language/tessdata but does not expose page-segmentation mode. Do not
invent an option or install a runtime for this comparison.

The first comparison changes word selection only. The second changes image
context and tests supplied segmentation jointly with crop boundaries; it is
not an automatic layout detector. The source remains the six-page BES PDF
and pre-OCR `real-scan/oracle.json`, with protected hashes and all 23 targets.
Neither path may use authored correction text as OCR input. Retain inspected
installed API source and wrapper code with hashes for invocation provenance.

| Role | Criterion |
|---|---|
| Primary diagnostic validity | Reproduce all 23 baseline centre selections and their 16 exact matches; verify all crop/page/model/runtime/active-method identities; retain every target and raw output. |
| Candidate screen | Exact whitespace-normalized equality per target; further-study viability requires losing none of the baseline passing targets. All 23 must pass for complete critical-text recovery, still under assisted segmentation. |
| Promotion veto | Critical text lost/changed, clipped crop, changed model/profile, hidden correction, borrowed geometry, guessed relationship or unlabelled manual boundary. |
| Continuation veto | Corrupt source/crop/oracle, different runtime, active-method drift, missing diagnostic, unexpected native structure or exceeded resource bound. |
| Repair trigger | A reproduced wrapper error or a valid failure with a specific next hypothesis; retain the attempt and review any changed retry. |
| Explanatory only | Text lengths, word counts, changed targets and elapsed time; concurrency precludes runtime comparison. |

No package ranking, unseen accuracy, Portuguese-language support, new default,
semantic reading or eligibility follows. English-model Portuguese errors are
profile-specific observations, not fundamental package limitations. Automatic
relations remain absent: region boundaries and intended links are supplied.

## Assumptions and smallest diagnostics

| Choice | Provenance/status | Risk | Earliest check |
|---|---|---|---|
| English model, PyMuPDF 1.27.2.2 and pinned interpreter | Existing baseline, not multilingual recommendation | Profile failure blamed on package | Model and distribution hashes |
| Existing 300-DPI PNG crops | Inspected regions; supplied segmentation hypothesis | Lost context or signature interference | All crop hashes/dimensions and prior review freeze |
| Positive-area intersection | Explicit geometry hypothesis without tuned threshold | Oversized boxes admit neighbours/noise | Reproduce centre baseline; inspect new spans |
| OCR on unchanged crop pixels | Supported API; diagnostic candidate | Supplied cells mistaken for automatic structure | Retain boundaries and every raw output |
| Whitespace normalization only | Pre-OCR rule | Permissive matching hides punctuation/diacritic errors | Exact strings and failure rows |

## Execution and reviewed bounds

1. Retain inspected API source slices and executable/model inventory. Read the
   actual installed implementation before finalizing the worker.
2. Run `geometry.py` within 60 seconds, reading the complete original graph and
   frozen regions. Record both rules, all raw spans and added/removed words.
3. Run `crop-ocr.py` with a 600-second outer bound and 300-second native bound.
   Use the pinned interpreter, `CUDA_VISIBLE_DEVICES=-1`, `OMP_THREAD_LIMIT=1`,
   all 23 exact crops and pinned English model. Retain crop dimensions/resolution
   and output page dimensions; crop-local boxes cannot represent original
   geometry. Produce no correction map or semantic admission from these boxes.
4. Review all changed targets, failures, crop-context explanations and actual
   invocation. Valid analysis may pass while a candidate fails. Retain a decision
   table and next discriminating action. Production integration requires a
   separately reviewed design after the active regression is committed.

```text
timeout 60 .venv/bin/python docs/implementation/prospectus-integration-closure/scan-mechanisms/geometry.py
timeout 600 .venv/bin/python docs/implementation/prospectus-integration-closure/scan-mechanisms/crop-ocr.py
```

Allow 20 MB of evidence with 1 MB reserved for metadata. Each attempt records
command, git commit, uncommitted active-method identity, interpreter/environment,
source/model versions, time, plan and result. Seeds are N/A. Verify the active
real-scan method before/after; valid checkpoint progress is allowed. Native
concurrency is only a bounded recognition diagnostic, with no runtime claim.
No network, installation, live model, GPU or new reviewer is used.

Skeptical audit: PASS for these diagnostics. Baseline replay precedes geometry
comparison. Cropped text comes from original pixels, not the correction oracle.
The model and supported API stay fixed. Expected failures motivate the next
hypothesis; changed source/runtime or missing diagnostics invalidate the run.
Thresholds are hypotheses, package/default promotion is prohibited, and work
stays outside every active binding.

Pre-mortem: cropping can succeed because a reviewer supplied the right cell;
that assistance is part of the candidate. Intersection can include signature
noise; inspect every added span. Both routes can share OCR mistakes; the
independently reviewed printed oracle remains the comparator. A corrected
identifier cannot stand in for a complete qualification or legal conclusion.
