# BES 2010 p89 sidebar reading-order diagnostic, 12 October 2026

Question: is the remaining broken negative-assurance phrase caused by OCR
recognition or by extraction order mixing the body with the page sidebar?
The exact comparator is the current worker's 300-dpi English `get_text(sort=True)`
and `get_text('words')` output, retained in the corrected eleven-document
consumer. The source is the original 2010 English PDF, page 89, and the
image-reviewed retrospective oracle contains seven critical spans on that
page. The failure is the source phrase “nothing has come to our attention”:
the current text has sidebar tokens between “our” and “attention”.

Test four extraction views from **the same** freshly rendered and OCRed page:
`get_text(sort=True)`, `get_text(sort=False)`, word order from
`get_text('words', sort=False)`, and `get_text('words', sort=True)`.
Also test a human-supplied body corridor ending at 90% of page width,
explicitly an image-specific hypothesis, not a generic column detector.
The primary diagnostic is whether the exact body phrase becomes contiguous
while retaining the other six strict page-89 spans. A method is only nominated
for further development if both hold and the rendered page/image/model/source
identities agree. No raw words may be invented or deleted without an explicit
body-versus-sidebar disposition; retain the excluded sidebar words separately.

Wrong source, changed image hash, changed model, failure to reproduce the
current baseline's raw text/words, missing exact phrase in the OCR words,
or missing page geometry invalidates the diagnostic. A failed extraction view
does not stop testing the others. Counts and runtime are explanatory. This
single page cannot justify automatic layout repair, general column detection,
a default change, source authenticity or a legal conclusion. The existing
assisted ordered source anchors remain the current handling.

Default audit: 300 dpi and pinned English model are comparator settings; they
are not claimed optimal. A 90% body corridor comes from the visible page
geometry, may cut legitimate right-column text on another page, and therefore
cannot be promoted by one success. Baseline reproduction is the earliest
validity check; matched lost-spans distinguish a useful order change from a
seemingly successful phrase that drops another qualification. The command's
retained text and word coordinates answer order versus recognition, not general
production readiness. Skeptical audit verdict: PASS for a bounded diagnostic.

Run once, CPU-only, from the prospectus worktree:

```text
timeout 120 .venv/bin/python docs/implementation/prospectus-integration-closure/bes-original-acquisition/probe_p89_reading_order.py
```

The result goes to `reading-order/attempt-001/`, with exact source/model and
method hashes, command/environment, baseline commit, page-image identity,
all variant texts, word boxes, per-span matches, excluded-sidebar evidence,
timing and manifest. A failed run remains retained for review. The next plan
may use a supervised body-region input if this diagnostic works; a generic
automatic ordering change requires broader pages and negative controls.
