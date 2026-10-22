# Missing-script source preparation

One genuine Arabic sukuk prospectus is retained from an observed official CMA
catalogue link: 6,204,334 bytes and 198 pages. All 198 pages received bounded
native-script inspection; 35 contained both right-to-left characters and ASCII
letters. Images of pages 5, 6 and 14 confirm mixed Arabic/Latin layouts. Exact
source and image identities are retained in `source-inspection.json` and
`IMAGE-REVIEW.md`.

All six allowed HTTP starts were consumed: one retained redirect response,
three catalogue/issuer pages, the Arabic catalogue and the Arabic PDF. No
automatic redirects or retries occurred. The 97 observed JPX issuer-document
links are discovery evidence only. No further HTTP call is authorized by this
package. Four render operations were used, including the first failed
inspection's render and the reviewed inspector's verification/render operations.

The first inspector failed because our JSON serializer did not handle native
image bytes. `inspection-first-failure.json`, the original script and invalid
empty output remain intact. The reviewed inspector preserves binary block hashes
and lengths and all text spans/word geometry; it also verifies the original PDF
and reused render. This is a repaired local serialization defect, not evidence
of a defective PDF or unsuitable PyMuPDF package. The first failed command's
wall time was not retained; its original script imposed a 120-second alarm.
The successful inspection took approximately 0.912 seconds.

The first seal command stopped before writing outputs because the original
redirect receipt records its command by a path-form note, whereas later receipts
store an explicit argument list. The original seal script and failure record are
retained. The corrected validator checks that exact first-receipt variant,
reconstructs only the documented relative output paths, and hashes the retained
headers/body. No acquisition or inspection was repeated.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Unsupported conclusion |
| --- | --- | --- | --- | --- | --- |
| Retain exposed mixed-script development material; broader task remains partial | Met: original source, provenance, native text and three visibly mixed-script images | Source/render identity and acquisition bounds checked; independent reading and actual consumer evidence still veto promotion | Exact Arabic reading order, transcription and consumer behavior are not evaluated | Run a reviewed local source-preservation diagnostic against these retained pages; obtain independent readings and a true vertical original separately | Automatic extraction quality, legal correctness, complete coverage or installed-package readiness |

The consumer/readings matrix is in `CONSUMER-MATRIX.md`. There were no OCR,
native product-worker, GPU, model or installation calls. This package does not
change the historical native-worker lower bound of 62. All four whole-delivery
completion flags remain false. The second original native-layout-cases admission
is consumed without increasing its allowance.

Post-run skeptical review: the principal alternative explanation for a useful
looking page is that the native text has a different order from the visible
page. Consequently the nomination counts and successful parse establish source
availability only. A mismatched source/render hash would invalidate this result;
a later failed text consumer would motivate a specific integration repair rather
than rejection of the source family or the package.
