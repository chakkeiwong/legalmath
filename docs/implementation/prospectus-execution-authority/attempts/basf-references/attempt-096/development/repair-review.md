# Changed development repair before formal method freeze

Diagnostic001 exposed two different problems. No formal stage has run. Retain
the original frozen preparation unchanged.

The arbitrary two-alias fixture's expected Nord token at4:8 identifies the
unquoted entity, not the quoted naming token at14:18. This is a harness error.
The independently inspectable literal source fixes that one interval. Preserve
both the old expectation and this additive correction.

The original BASF template raw line is
(["BASF"]["BASF Finance"] oder die "Emittentin") wird in [festgelegte Währung].
The selected source labels308:314 as SUPPLIED_OR_TRANSFORMED. BASF309:313
therefore has no exact raw projection. Emittentin325:335 is itself raw-bound,
but its complete coordinated naming syntax307:337 includes the supplied name.
The detector correctly refuses to promote either full naming expression as
wholly raw-bound. The verifier was wrong to demand DECLARATION_SYNTAX for every
token while also prohibiting transformed text from becoming raw evidence.

Repair: retain a separate observed_syntax field for grammar in the selected
text; independently expect UNRESOLVED_SOURCE and no source-qualified syntax for
these two tokens. Every other original token must retain its exact expected
syntax and source-qualified outcome. No source identity, raw offset, definition
reading,612-use disposition or remaining premise changes. This is a source
qualification, not proof that the issuer has no definition.

This does not lower the source requirement or turn failure into legal success.
The finite declaration-syntax package can account for all47 tokens, but only45
are wholly raw-bound under the retained request. Unbound naming expressions
remain explicit. The main work still requires governing-use/source integration.

Skeptical audit: PASS for this changed development repair. The discrepancy is
reproduced in independent raw-piece metadata and the literal arbitrary fixture;
neither correction is inferred from a desired legal answer. Verify transformed
cue/quote/name and cross-context refusal controls before formal freeze. No
additional admission, cumulative-limit reset or unchanged formal retry occurs.
