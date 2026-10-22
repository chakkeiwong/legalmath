# Portuguese assurance OCR and actual source consumer

The acquired Portuguese 2010 PDF validates as 256 pages. Native contents at
PDF 7 point to the limited-assurance report at printed 88; source-image review
confirms it at PDF 88–89. Those pages have only 65 and 43 native nonspace
characters. The four retained crops support thirteen prospectively transcribed
critical spans in `portuguese-2010/critical-spans.json`.

Question: can the existing selected-page OCR/P1 interface recover these exact
Portuguese qualifications while preserving native evidence? The exact baseline
is P1 from this PDF with native extraction only. The candidate uses the existing
300-dpi selected-page profile with Portuguese alone, pinned to the retained
official fast-model SHA `c4932b937207a9514b7514d518b931a99938c02a28a5a5a553f8599ed58b7deb`.
This is an optional source-specific configuration hypothesis, not a default.

Engineering pass requires unchanged native units, OCR on exactly pages 88–89,
matching original-page image hashes, all raw OCR units retained by P1, and
retained model/source/worker/environment bindings. Thirteen exact image-span
matches are a separate recognition screen: missing accents, negation, date,
criteria or complete qualification prevents a claim of complete critical-span
recovery. Raw counts/runtime are explanatory. A recognition miss calls for
diagnosis (recognition, reading order, or oracle), not a change to the frozen
oracle or another automatic OCR run. Source/model/image mismatch invalidates
this branch. Never promote the internal March 2011 date to publication evidence.

Run once with `.venv/bin/python` through a new coordinator that pins worktree
imports and the existing tfgpu CPU OCR interpreter. Set CUDA_VISIBLE_DEVICES=-1
before imports. The two-page call is below the twenty-page cap; existing worker
timeouts apply. Save raw worker output, exact span matches/misses, request,
compressed P1 product, native preservation check, start/result/manifest under
`portuguese-2010/ocr-consumer-001`. No new packages or external calls.

Dependencies: valid acquired bytes and image/oracle bindings precede OCR;
source-product consumption depends on valid worker output. Interpretation of
the source images and documentation can proceed even if recognition fails.
This branch is independent of the running R4 test ladder. After the bounded
run, retain actual results and refresh source-scope next work; no legal query
promotion or onward-dependency resolution follows from a P1-only result.

Skeptical audit PASS: the comparator is the same new document, native and OCR
layers remain distinct, page identity is observed rather than transferred from
English, and the pre-OCR image oracle preserves a full negative conclusion and
third-party qualification. Portuguese fast-model adequacy and default 300 dpi
remain hypotheses tested by the exact span screen. A screen pass cannot
establish independent legal acceptance, translation certification, authenticity,
publication dates or whole-report extraction coverage.
