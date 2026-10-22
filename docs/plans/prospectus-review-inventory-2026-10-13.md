# Repair independent-review preparation's source inventory

The first independent-packet attempt skipped 22 source entries because the main
manifest uses file, while its reader accepts only original and path. It also
treats unmatched documents as unknown without propagating confirmed exposure
across duplicate bytes and explicitly reviewed source families. Use the second
original admission to repair that preparation.

Question: does the finite frozen manifest set now have complete document
accounting and conservative exposure propagation, without marking any document
unexposed? The baseline is attempt-001's 40 admitted rows and 22 omitted rows.
Keep exactly its manifest denominator; list other repository manifests as
outside scope rather than claiming a complete repository exposure history.

Primary criterion: every original manifest entry is represented with its actual
path, bytes/hash and source-field provenance or an explicit blocking issue.
Handle dictionary/list documents and file/original/path names; do not guess an
ambiguous relative location or silently skip malformed metadata. Reproduce the
22-row omission before repair. Retain all original development evidence. Exact
duplicate hashes and reviewed family assignments propagate exposure, while
unknown families and unmatched metadata remain ineligible. Existing original
files and sealed evidence must be unchanged.

Add a reusable inventory/preflight module and run its actual preparation consumer
on the retained manifests. A candidate selection from an exposed alias or an
unknown family must be blocked. Test missing files, hash mismatch, path escape,
conflicting path fields, duplicate IDs across manifests and byte aliases.
No test key, signature, person, invitation, prediction or independent label is
created. Existing signed-review checks remain unchanged. This preflight can
reject or prepare evidence; it cannot authenticate an independent cohort.

Audit PASS: denominator is frozen separately from implementation success; counts
are accounting checks, not independence criteria. Family assignments are explicit
development-review metadata, not automatic legal-entity identity. An exact-byte
alias proves shared content, not all historical exposure. Missing data remains
unknown and blocks selection. Confirmed exposure is never erased by a directory
called fresh or holdout. The strongest risk is overclaiming complete history;
the result must state the scope and retain false complete/eligible flags.

Execute: freeze baseline/input identities; implement checked inventory and
blocked cohort preflight; test and consume all retained rows; review attribution
and limitations; seal <=10MB, record/refresh, continue a justified route. Source
hash corruption vetoes inventory use; missing real administrators/readers block
cohort acceptance but not this repair. CPU only, worktree src pin, timeout120,
one-second yields. No network, installation, external communication, git write
or increase to original admission bounds.
