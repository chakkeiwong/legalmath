# Solver corpus preparation findings

The first bounded synthetic product smoke failed with ValueError: Unbound
clause in interpretation_product. The harness built clause anchors before
adding the construction AST, which changes operative unit identities. This
is a test-harness ordering error, not a production or Z3 failure. Construct
the final assembly first, then bind the supplied clause to its actual units.
No admitted candidate ran and no production method changed.

A static review also found that current/frozen consumer records intentionally
differ in assessment_mode and the resulting report checksum. Retain both
complete records, verify their checksums, and compare every substantive field
after removing only those two declared metadata fields. This avoids both a
false mismatch and an overly narrow selected-field comparator.
