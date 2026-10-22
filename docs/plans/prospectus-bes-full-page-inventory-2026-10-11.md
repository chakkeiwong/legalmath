# BES original-PDF page inventory, 11 October 2026

## Research intent and evidence contract

Question: which pages in the three retained English BES annual reports are plausible additional mixed-image or image-only text pages that native Poppler extraction could miss? This is a *candidate inventory*, not a proof that every page is complete. The exact comparator is the current product `source_graph.pdf_units` native PDF extraction and the six image-heavy audit pages already confirmed by rendered inspection (2008 PDF 245–248; 2009 PDF 174–175). The 2010 native audit opinion at PDF 190 is a control. The mechanism under test is page-image geometry combined with the product's native text layer.

Primary pass criterion: inspect every original PDF page under exact source SHA-256, agree with recorded page counts (286, 229, 256), retain per-page native-text and image-geometry measurements, and include all six confirmed image-heavy audit pages in the candidate set. Hard vetoes are a changed original, changed source extractor, unmatched page count, missing per-page record, failure of any known-six recall, or malformed image geometry. Runtime and number of candidates are explanatory only. A candidate threshold cannot establish text completeness, an absence of images cannot prove absence of vector-drawn text, and this run cannot authenticate an issuer source or promote a legal answer.

The 14 onward-source dependencies stay `UNRESOLVED`; no raw OCR, correction, publication date or legal interpretation is promoted. The output is `bes-original-acquisition/page-inventory/attempt-001/` with source/extractor/runtime identities, all page measurements, candidate list, checks and a hash manifest.

## Default and assumption audit

- The three PDF hashes and page counts come from the retained acquisition receipts and are required identities. Wrong bytes stop the run.
- Poppler `pdftotext -bbox-layout -enc UTF-8` is the actual native source-graph mode. Its executable hash is recorded. Native character count is an omission diagnostic, not a correctness metric.
- Existing PyMuPDF 1.27.2.2 in `/home/chakwong/miniconda3/envs/tfgpu/bin/python` reads visible image bounding boxes. It is a convenience detector, not a complete semantic image classifier. The known-six recall is the earliest check of utility.
- Nominate a page when its largest visible image covers at least one quarter of the page, when it has an image and fewer than 20 native nonspace characters, or when it has zero native characters even if the page contains no raster image. These thresholds are *screening hypotheses*, not reviewed defaults. Retain all continuous page measurements so a later visual review can revise them without losing evidence.
- `CUDA_VISIBLE_DEVICES=-1` is set before PyMuPDF import; this is CPU work. One bounded 180-second attempt is allowed. No random seed or stochastic ranking applies.

## Skeptical audit before execution

The baseline is the actual three originals and product extraction mode, rather than an artificial blank scan. A sparse-text page is not treated as a promotion criterion. Known false-negative pages would invalidate this screening method and trigger a changed method, not an unchanged repeat. The 2010 control prevents the inventory from being described as equivalent to OCR need; image geometry and blank-page nominations may be false positives, which are retained for visual disposition. The exact command writes source hashes, per-page measurements and known-six diagnostics, so its artifacts answer the candidate-inventory question. It does not answer whole-report coverage or legal authenticity. Runtime environment and page limits are explicit. Audit verdict: PASS for a bounded diagnostic, with all nominations explicitly unreviewed until image inspection.

## Execution and refresh

1. Verify original and prior extraction hashes; inspect the six known pages and the 2010 control with the same method. If the known-six recall fails, repair the screen before running full inventory.
2. Execute once with `timeout 180 /home/chakwong/miniconda3/envs/tfgpu/bin/python docs/implementation/prospectus-integration-closure/bes-original-acquisition/page_inventory.py` and `CUDA_VISIBLE_DEVICES=-1`.
3. Inspect candidate counts and page measurements; visually review additional likely legal/financial pages before adding any OCR profile. Record a result and refresh `NEXT-PROGRAM.md` without changing the current product phase receipts unless product code or a bound packet changes.
