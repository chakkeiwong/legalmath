# Exact-quantity repair accepted within its stated scope

Revision 214 retained finance-conventions/attempt-004 through an actual RECORD
event, `4aeafaf7eaf488259eeebb011260a4a5a032af5864eea94c9cc19dd8f962273c`.
The authority independently replayed and accepted `exact-quantity-refusal`.
Original finance acceptance and the general build remain incomplete.

The reproduced defect was our parser's exception contract: `Fraction('1/0')`
raised ZeroDivisionError outside consumers that declare ValueError refusals.
The shared parser now translates only that construction failure. Every
successfully parsed value still returns the same Fraction; arithmetic,
entitlement, dates and rounding conventions are unchanged.

All fourteen valid retained comparisons were equal, including complete Danske
and Shell direct/selected consumer records and the two explicitly hypothetical
v2 results. Twenty-two malformed-input checks refused for the precise
zero-denominator reason, including excluded holders and selected numeric terms.
The focused supporting suite passed 397 tests. Preparation took
7.3881493248045444 seconds, candidate execution 40.250338928774 seconds, and
the record command including the independent replay 57.3837411319837 seconds.
The retained receipt and manifest preserve the actual commands and identities.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Limit |
| --- | --- | --- | --- | --- | --- |
| Accept finite parser repair | Valid full comparisons equal; invalid inputs refused | No changed valid result or wrong refusal | Remaining financial and source coverage | Validate current methods and installed package after this shared-code batch | No actual entitlement, legal truth or whole-build claim |

This is an implementation defect in our input boundary, not evidence of a
fundamental package problem. The next phase must validate the wheel's actual
contents and isolated imports, including the new comparative JSON specification.
Historical checks remain immutable; their stale current bindings require
explicit current validation rather than relabelling their old results.
