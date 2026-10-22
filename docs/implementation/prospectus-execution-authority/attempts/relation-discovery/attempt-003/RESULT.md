# All exposed BES suggestions accounted for

The optional relation-review API now retains and validates an authored judgment
for every one of the24 BES v2 suggestions: eight protected targets and sixteen
extras. Eighteen preserve the inspected printed relation; three cross printed
rows; three need explicit transcription review. The sixteen extras are therefore
not sixteen false positives. All six original pages are retained as renders;
each judgment binds the PDF hash, page-render hash, complete candidate identity,
exact endpoints and any disputed units.

Three scope failures have concrete local causes. On page1, the issue-date
suggestion includes p1:ocr68, the maturity date from Arabic item8. On page3,
New Global Note includes p3:ocr24, the answer to Arabic item26. The Roman-only
stop condition ignores these boundaries. The page2 status suggestion instead
misses an OCR-corrupted Roman marker: p2:ocr24 is `Gii)` although the page shows
item13(iii). Its following board-approval label and date enter the status row.
The code's independent label/value extent checks do not restore the missing
row boundary. These are failures in our candidate construction, not demonstrated
fundamental failures of the extraction package.

The determination-date value includes p2:ocr55 `t` at the scan's far-right edge.
Its x-coordinate is593.76; the intended value begins at279.84. Selection admits
all text to the right of the inferred split without a finite horizontal limit.
The raw source remains intact. The ISIN and Portuguese clearing-system name
also contain unresolved transcription discrepancies despite matching protected
endpoint targets. Neither protected-target success nor reviewable row scope
certifies the exact identifier or every glyph.

Forty focused tests pass. Ten altered actual-data controls refuse missing,
duplicate and foreign candidates; changed graph/candidate identities; forged
anchors; empty reasons; changed renders; and unsupported independence/legal
scope. The earlier36-test run remains retained; four added cases strengthened
the requirement to preserve complete endpoint/marker evidence and file scope.

The actual service reconsumes the retained full P1–P5 products. The replay is
stored as `reconsumed-answer.json.gz`. Its mode truthfully remains `frozen`.
Comparison with the historical `fresh` answer normalizes only that declared
assessment-mode metadata and the derived report checksum, as the earlier
retained comparison did. Every remaining field agrees exactly, including the
source map, clause/dependency data, all questions and product identities.
Accepted relations remain empty and inferred legal scope false. This is
retained-product replay, not fresh extraction or current installed validation.

| Decision | Primary criterion | Veto diagnostics | Main uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Record finite review package | Complete24/eight/sixteen coverage and unchanged full answer pass | No altered admission input, missing page, forged anchor or answer drift | Agent exposed to development data; review judgments are not independently adjudicated | Review optional boundary repair against these exact failures and synthetic adversarial layouts | General relation accuracy, independent legal acceptance, whole delivery |

Post-run review: image-linked evidence makes these judgments inspectable, but
the validator checks their provenance and structure rather than their truth.
A mistaken visual reading or shared OCR error remains possible. Independent
source readings could overturn individual judgments. A predictor repair must
preserve the eighteen reviewed relations, all eight protected endpoints and
full qualifications; it must not silently repair raw OCR or gain credit by
dropping every suggestion. No stochastic ranking is made.

No new OCR/native worker, model call, installation or network request ran.
The remaining automatic relation and independent-review requirements stay open.
