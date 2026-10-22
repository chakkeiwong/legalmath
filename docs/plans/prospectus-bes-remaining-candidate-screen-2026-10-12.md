# BES remaining image-candidate screen, 12 October 2026

## Research intent and evidence contract

Question: among the 31 inventory pages previously triaged only through contact
sheets, which are worth full-page image review because source-bound English OCR
finds substantial words absent from the native layer? The exact baseline is the
771-page inventory's native Poppler extraction and the ten visually confirmed
and already selected audit/committee/sustainability pages (2008 PDF 245–248;
2009 PDF 174–177; 2010 PDF 88–89). The 31 remaining candidates are the target
of this diagnostic. Do not reclassify them as legal sources merely because OCR
returns text.

Primary engineering pass: verify all three original PDF hashes and page
counts, exact inventory/visual-review manifests, process exactly the 31
remaining original PDF page numbers with the existing pinned CPU worker, bind
image/model/runtime identities, retain every raw word and text stream, and
produce native-vs-OCR measurements per page. An image whose OCR has at least
100 alphabetic characters and either fewer than 50 native nonspace characters
or more than four times the native nonspace count, is nominated for enlarged
visual review. Those thresholds are
screening hypotheses only. All 31 remain in the output even if no threshold
fires. Source/image mismatch, missing page, model/runtime drift or changed
inventory invalidates the screen. A zero nomination count is not completeness.

OCR character counts, ratios, keyword hits, runtime, and contact-sheet
appearance are explanatory, not promotion criteria. A candidate must be read
in its enlarged original image and supplied with a source-bound oracle before
joining selected-page product evidence. English raw OCR may miss Portuguese
diacritics and tables. Logos, maps and advertising text may be visible but not
relevant to the prospectus question; financial/legal text outside this screen
may still exist in smaller images or vector paths. No source authenticity,
historical date, whole-report coverage, legal interpretation or package ranking
follows from this diagnostic.

## Default/assumption audit and skeptical review

The source hashes/page counts come from the retained original acquisition
receipts; mismatches veto. The 41-page inventory passed known-six recall and
stored all 771 measurements, but its 25% image-size and low-native thresholds
were hypothesis screens; they do not justify a negative completeness claim.
The ten prior selected pages are removed by exact `(year, PDF page)` identity;
the remaining count must be 31. The 300-dpi English model and CPU PyMuPDF
worker are the actual current product comparator, not preferred settings.
Small or low-confidence text could be missed; each page's raw output and image
identity remain available for later review. The `100/50/4×` thresholds trade
inspection time for false negatives and cannot promote a page or reject one.

The anticipated failure modes are an off-by-one printed/PDF page, an image
hash generated from different bytes, a large photo with OCR junk, an ad with
small genuine words, a missed multi-column qualifier, and overinterpretation
of raw OCR. The cheapest diagnostics are original PDF SHA/page count, exact
selected-page list, retained inventory native counts, rendered 300-dpi image
hashes, raw text snapshots and manual inspection of nominated/near-threshold
pages. The command's artifacts answer the candidate-screen question and no
broader one. Audit verdict: PASS for a bounded exploratory screen. A failed
candidate screen triggers method review, not a repeated unchanged run.

## Execution and refresh

Run once from the prospectus worktree:

```text
timeout 600 .venv/bin/python docs/implementation/prospectus-integration-closure/bes-original-acquisition/screen_remaining_pages.py
```

The script sets `CUDA_VISIBLE_DEVICES=-1` before imports and uses the existing
CPU OCR interpreter with one worker thread. It makes three bounded per-year
calls of 9, 12 and 10 pages, all below the product's 20-page profile cap.
It retains source/inventory/model/method fingerprints, baseline commit,
command/environment, deterministic seed status, start/finish/wall time, raw
OCR JSON/text per page, all 31 measurements, nomination reasons, progress after
each year, and a manifest under
`bes-original-acquisition/page-inventory/exploratory-ocr-001/`. Detailed text
goes to files; stdout prints only a compact per-year count. After the three
years, inspect every nominated and near-threshold page in an enlarged original
render, record which new omissions are substantively distinct, and only then
write a source-specific integration plan. Preserve the 31-page exploratory
output even if no additional page is admitted.
