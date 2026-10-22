# Source-stage refusal and bounded recovery

The source stage refused the manual transcript with `Wrong company label` before
any production mutation. A read-only mismatch localization found exactly two
directory-label differences, both on page 63: row 19 (zero based) was typed
`Espírito Santo Investimentos, Ltda`, while the retained source prints/extracts
`Espirito Santo Investimentos, Ltda`; row 45 was typed `Espírito Santo International
Asset Management`, while the source omits that accent too. Spaces inserted by the
native text extractor are already handled by the original whitespace rule.
The row attributes, movement values and clause-anchor localization found no other
differences. Localization alone is not a complete source validation.

This is a manual transcription mismatch caught by the existing validator. It is
not evidence of a package's unsuitability, and does not justify globally stripping
accents or relaxing entity matching. The original-resolution page-63 image was
read during recovery and the two source spellings rechecked. A changed attempt
will correct only those two characters in the transcript, keep all original raw
quotations and association checks, and add row context to mismatch error messages.
Before admission, the full corrected source check and full-graph preflight must
pass, with deliberate wrong-label/value/context controls still refused.

The independent coverage stage is retained. Implementation and its success
dependants did not run. Attempt 040, its manual transcript and failure evidence
remain immutable after sealing. Attempt 039 remains the successful comparator.
The next review must retain cumulative costs and all 40 admissions; no unchanged
retry is authorized. No global continuation veto occurred.

|Decision|Primary criterion|Veto status|Uncertainty|Next justified action|Not concluded|
|---|---|---|---|---|---|
|Reject this transcript|Failed exact company-label agreement|Source promotion veto fired; authority and original evidence intact|Corrected full check pending|Correct two accent characters in a new reviewed attempt, preflight, then source and product checks|Package rejection, legal truth, whole-build completion|
