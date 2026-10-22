# BES p89 reviewed-region consumer result, 12 October 2026

The existing product layout adapter now has a retained consumer result for the
newly recovered 2010 sustainability report page. It consumes two supplied,
image-reviewed regions, maps all retained page-word characters exactly once,
preserves all original native/OCR units and keeps the sidebar as a separate
projection. The body projection matches all seven frozen critical spans. The
unchanged raw source stream matches six of seven because sidebar letters split
“nothing has come to our attention”.

The preceding diagnostic reproduced the current English worker text and words
exactly. `get_text(sort=True)`, `get_text(sort=False)` and both word-sort options
all left the phrase interrupted. A supplied body corridor ending at 90% of
page width reconstructed it while accounting separately for fifteen sidebar
words. Recognition of the phrase was already correct; source-region ordering
was the failure. The 90% boundary is an inspected-page choice, not a generic
cropping or column-detection rule.

Code tracing found a usable integration path in `admissions.structure` and
`layout_adapter.project_layout`. The actual `service.source_product` now
consumes this region packet. No new OCR was substituted into the corrected
eleven-document legal consumer. The product's field named `docling` contains
a supplied layout representation; **the Docling model did not run**. No automatic
region detection or legal scope inference is established.

| Decision | Primary criterion | Veto evidence | Main uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Accept this supplied page projection | Actual P1 consumer; 7/7 body spans; two non-overlapping regions | Exact source/image binding and complete nonspace word-character partition pass | Generality to other pages | Broaden reviewed region cases before automatic detection | Full-report reading order |
| Preserve raw evidence | All-page raw units identical to no-layout comparator; sidebar retained | No character ownership loss or overlap | Raw sidebar OCR remains imperfect | Keep raw and projected views distinct | OCR is corrected automatically |
| Reuse existing layout interface | Real layout admission with zero mapping failures | Changed candidate, widened body, overlapping ownership and stale graph controls reject | Downstream supplied legal annotation/scoping | Bind reviewed projections into a separate source-scoping package when justified | Docling inference or legal interpretation complete |

The diagnostic ran in 2.067 seconds and the actual product consumer in 17.336
seconds using `.venv/bin/python`, with the existing CPU OCR subprocess,
`CUDA_VISIBLE_DEVICES=-1` and `OMP_THREAD_LIMIT=1`. Exact commands, baseline
commit, dirty method hashes, original/model/image identity, environment,
deterministic seed status, full products, word coordinates, span checks,
negative controls, wall times and manifests are retained in `attempt-001/`
and `consumer-001/`. The plans are
`docs/plans/prospectus-bes-p89-reading-order-2026-10-12.md` and
`docs/plans/prospectus-bes-p89-region-consumer-2026-10-12.md`.

The strongest alternative explanation is that manual page geometry makes a
known example easy while multi-column or marginal legal qualifications would
still fail. The exact character partition shows nothing was discarded here;
it does not resolve that generality risk. A frozen set containing body text in
the right margin, notes, multi-column tables and rotated text is needed before
a detector or default change. The accepted result is a source-specific use of
the existing adapter with explicit supplied review, preserving uncertainty.
