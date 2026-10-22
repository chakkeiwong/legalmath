# Portuguese page-89 reading-order repair

The frozen Portuguese source screen recovered 12/13 spans. Raw OCR contains
the complete negative-assurance words in order, interrupted by right-margin
characters (`ê`, `$`, `5`, `E`). The inspected original separates that margin
from the report body. This is a reproduced reading-order failure, not missing
Portuguese recognition or evidence against the package as a whole.

Use the existing supplied-layout/P1 interface and retained raw OCR once. The
candidate is two source-reviewed regions separated at 90% of page width, a
geometry hypothesis checked on this original image and character partition.
The comparator is the sealed no-layout Portuguese P1 with identical PDF,
model and OCR bytes. Use existing reviewed helper functions from the English
page-89 package but bind their source bytes; do not run or edit that old method.

Primary pass: actual P1 consumes both regions, every nonspace raw word
character maps exactly once, no raw unit/sidebar disappears, all six frozen
page-89 checks match the body, and the seven page-88 raw checks remain matched.
Changed text, overlapping region ownership and a stale graph must reject.
Any source/image/model drift vetoes. A failed region is retained without an
automatic crop sweep. No Docling model, general region detector, P2 selection,
legal scope inference or new OCR default is implied.

Audit PASS: source words and supplied reading are separate, the qualification
is compared in full, geometry is an image-specific reviewed hypothesis, and
sidebar preservation prevents success by dropping difficult evidence.
Prerequisites are the sealed Portuguese P1 and frozen image/oracle records.
The region run is independent of R4, uses the CPU worker only for verification,
and writes a new `portuguese-2010/region-consumer-001` result and manifest. After
completion, update the conditional bilingual source review and ready set.
