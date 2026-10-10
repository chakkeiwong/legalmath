# BES source review before current OCR

On 11 October 2026 (Hong Kong), the executing agent inspected all six retained
review images and all 23 enlarged critical-region crops. The crops were rendered
from the original PDF, independently of OCR. The current PyMuPDF renderer
reproduced the historical full-page image bytes exactly on every page. The
inventory attempt passed in 0.985 seconds and preserved the active R6 method.

`oracle.json` contains the printed text, supplied image regions and eight
relationships fixed before the next OCR trial. Every crop contains the intended
text without clipping a critical character or including a neighbouring cell.
The contact sheets in `region-review/` were actually viewed; they are viewing
aids, not additional source authorities. The individual crops and full-page
hashes are sealed in `inventory/attempt-001/`.

The first three pages establish the printed issue description, annual coupon,
payment dates, Actual/Actual (ICMA) wording, Interbolsa book-entry form and
Portuguese governing-law statement. The responsibility sentence on page 4 is
legible despite a signature stroke across its last word; no signature identity
or authority is authenticated. Page 5's ratings are accompanied by the complete
printed qualification on regulatory use and registration. That text is retained
as a document statement; its legal accuracy and actual registration facts are
outside this extraction test.

Page 6 prints ISIN `PTBEQBOM0010` and common code `064529170`. The clearing
system's Portuguese name belongs in the right-hand cell, opposite the question
about systems other than Euroclear and Clearstream. Delivery is against payment,
and additional paying agents are marked `Not Applicable`. The final `Yes`
answers the intended holding-arrangement question. The entire following
paragraph states that the designation does not necessarily establish recognized
eligible collateral and that recognition depends on Eurosystem criteria.
These are separate printed statements with a required qualification link.

The book-entry Interbolsa form on page 3 and the generic ICSD/common-safekeeper
language on page 6 both survive. This review does not reconcile their legal
application. The original base prospectus and supplements mentioned on page 1
remain onward sources, and these six final-terms pages cannot establish the
complete governing contract.

This is agent-authored development review, not an independent first reading,
qualified legal adjudication or acceptance evidence. The document is already
exposed development data. Supplied cells, text corrections and relationships
will be reported separately from automatic OCR output. The current worker has
not yet been run on this input under this plan.

## Source-to-service audit

`extraction.scan` runs the current bounded worker. `retained_ocr_units` groups
its raw words into source occurrences; it does not consume the reviewed
historical transcription. `corrections.admit` binds an original interval and
page-image hash and accounts for every input character. Corrected output has
no inherited geometry. `annotation_bridge.bound_evidence` and
`admissions.annotation_clauses` recover raw source spans from admitted display
text, rejecting inserted/uncertain spans and ambiguous partial replacements.

`admissions.governing_dependencies` checks the selected governed targets.
Its `from` field may be a non-operative construction instruction, as the
existing margin test explicitly demonstrates. Requiring every `from` span to
be an operative clause would therefore be an unjustified repair. For the BES
qualification, the reviewed required targets must include the complete
qualification and the affected answer, so an omission cannot pass solely
because the `Yes` survives. A row association in this extraction slice is not
a new legal eligibility question; Q1 continues to mean contractual principal
loss, and the other five product questions keep their existing meanings.
