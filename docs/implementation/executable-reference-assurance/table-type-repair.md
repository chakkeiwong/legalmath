# Canonical identity repair discovered during frozen regression

A post-integration adversarial diagnostic changed the reference table's
`executable_available` value from JSON true to integer 1. Python dictionary
equality treats those values as equal, so the resolver accepted a table with a
changed canonical identity. The selected expression did not change, but this is
wrong relative to the declared exact-table integrity contract. The reproducer
is `artifacts/executable-reference-assurance/2026-09-29/table-type-reproducer.json`.

Repair: compare canonical request/schema/candidate/table bytes rather than
Python's coercive numeric equality. Challenge both the true-to-1 change and an
integer offset changed to a float. The latter must produce a stable schema
diagnostic before slicing, not an incidental Python exception. Keep source
quotation and semantic labels untouched. Add the cases to the affected suite,
execute the focused repair, then revalidate D2 and the full isolated regression
against the repaired source snapshot. Do not edit the earlier snapshot or hide
its missing challenge. The old successful finite checks did not establish this
stronger adversarial property.

The D3 audit and D4 source attachment concern unchanged calendar/source modules.
Their original snapshot identity remains explicit. They are not silently
rebound to the later executable-reference repair.

## Shared source-table boundary

The subsequent review found the same equality issue in
`source_references.verify_table`. The retained
`source-table-type-reproducer.json` substitutes Boolean false for start offset
0 and the old resolver accepts it. Although the quote bytes stay unchanged,
the altered table must be rejected under the same exact-identity contract.
Canonical comparison and two focused adversarial cases repair this boundary.
The earlier schema and valid reference IDs remain usable; no historical model
judgment changes. Verification attempt 02 keeps its original frozen source and
cannot qualify this later change. Focused repair, D2 revalidation and verification
attempt 03 must pass before delivery. The original attempt caps are retained.
