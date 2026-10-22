# Supplied statement cells

The prospectus service accepts an optional `source_statement_cells` request
field for a reviewed reading of the BES 9M2010 statement pages. The initial
profile is specific to the original release, page occurrences and the
corrected 203-cell reading retained in source-bes-dep-01 attempt004. It is
an assisted input; it does not extract arbitrary financial tables.

Supply `version: source-statement-cells.v1`,
`profile: bes-9m10-statement-cells.v1`, `document: bes-release-9m10`,
the complete source graph's ordinary product digest as `graph_sha256`,
an explicit `review` record and the complete corrected map as `reading`.
The map must match the protected finite profile. Whole original page content
and geometry are checked as well. A different source edition or altered map
requires a separately reviewed profile; changing a request hash is insufficient.

P2 retains the admitted reading, P3 binds its identity and the final consumer
revalidates both. The answer's `source_statement_cells` field contains all
rows, exact source anchors, period/unit headers, memorandum roles and source
qualifications. It preserves 23 unknown dashes and the non-additive ECB
subset magnitudes. Questions, source dependencies and transaction authority
are not resolved by attaching this reading.

Requests without the field preserve existing behavior. Missing, altered or
unsupplied intermediate statement evidence is rejected even when the ordinary
phase hashes are recomputed. The field is supported through normal request
construction and final consumption; supplied interpretation overrides cannot
replace the statement input.

The current evidence is the original retained-P1 downstream comparison in
source-bes-dep-01 attempt005, sixteen focused tests and ninety-seven selected
regression tests. It establishes consumption for this finite supplied input.
Independent financial/legal review, historical authenticity, general parsing,
fresh native extraction and whole prospectus completeness remain unresolved.
