# Portuguese 2009 reading: original pages found, P1 blocked by geometry

The original Portuguese PDF is available and matches its 11 October receipt.
Image review independently located the statutory audit on PDF pages 174–176
and the Audit Committee report on 177–178. Eleven passages were transcribed
from source-bound crops before OCR. The financial opinion and committee
concurrence are distinct; their internal dates are 4 and 9 March 2010.

The five-page Portuguese OCR worker completed. The actual P1 consumer rejected
one generated word box on page 177: `:` at approximately x=530.64–1037.02 pt,
outside the original 640.63 pt page width. This is not a small raster-rounding
error. The failed request, worker and source images are retained in
`ocr-consumer-001/`; there is no successful P1 or downstream scope result for
this new case.

The bounded `geometry-probe-001` reproduced the same out-of-page box from the
retained image. PyMuPDF's accurate-bounding-box flag preserves all 266 tokens
but leaves that box outside the page. The diagnostic then failed because the
Tesseract CLI is absent; it had already retained the generated OCR PDF and both
word outputs. Direct engine-versus-PDF geometry therefore remains untested.
The installed `tfgpu` environment supplies PyMuPDF's embedded OCR route, which
does not imply a standalone `tesseract` command is present. The failed probe
is retained without rerunning or relabeling it PASS.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Withhold this case's P1 promotion | Actual source intake failed | One invalid geometry veto | Recognition box versus OCR-PDF text placement | Trace generated-PDF geometry and evaluate an explicit degraded-geometry contract under a reviewed plan | No fundamental package unsuitability |
| Retain local original and image reading | Source/image hashes verified | No source-byte failure | Independent authenticity and historical publication | Continue conditional source analysis and external evidence | No incorporation or issue-date availability claim |
| Preserve running source-report ladder | Its four admitted cases passed | New case not part of that cohort | Generality beyond exposed cohort | Finish that method's validation, then admit any geometry repair separately | No claim all Portuguese reports pass |

A repair must retain the raw text and invalid box as evidence and distinguish
unusable word geometry from unread text. Simply clipping the box to the page,
deleting the token, weakening the bound, or certifying a manually changed
worker result would hide the failure. An optional route with explicitly unknown
word geometry may allow further conditional reading, but its downstream
anchor/correction/layout behavior needs tests before adoption. Production
code was not changed during the active R4 run.
