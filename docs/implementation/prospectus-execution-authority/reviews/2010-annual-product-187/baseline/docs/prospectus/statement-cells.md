# Supplied statement cells

The prospectus service accepts an optional `source_statement_cells` request
field for supplied readings of three BES releases. Each profile binds the
original release, complete page occurrences and a retained development
reading. This is an assisted input for these specific documents.

| Release | Profile | Document | PDF pages | Rows / cells | Unknown dashes |
| --- | --- | --- | --- | --- | --- |
| 9M2010 | `bes-9m10-statement-cells.v1` | `bes-release-9m10` | 37–38 | 77 / 203 | 23 |
| Q1 2011 | `bes-q111-statement-cells.v1` | `bes-release-q111` | 36–37 | 78 / 206 | 22 |
| FY2010 | `bes-fy2010-statement-cells.v1` | `bes-release-fy10` | 41–42 | 76 / 200 | 23 |

Supply `version: source-statement-cells.v1`, the matching `profile` and `document`,
the complete source graph's ordinary product digest as `graph_sha256`,
an explicit `review` record and the complete corrected map as `reading`.
The map must match the protected finite profile. Whole original page content
and geometry are checked as well. A different source edition or altered map
requires a separately reviewed profile; changing a request hash is insufficient.

P2 retains the admitted reading, P3 binds its identity and the final consumer
revalidates both. The answer's `source_statement_cells` field contains all
rows, exact source anchors, period/unit headers, memorandum roles and source
qualifications. It preserves unknown dashes and the non-additive ECB
subset magnitudes. The 9M reading retains its `headers` field; Q1 retains its
`tables` field, stock and quarter-flow periods, and the distinct parent rows
of its two ECB memoranda. Questions, source dependencies and transaction authority
are not resolved by attaching this reading.

FY2010 retains annual income flows for2009/2010 and balance dates31December2009,
30June2010 and31December2010. Its discontinued-operations row is a signed,
non-additive part of Net income. The retained map preserves the source's
printed expense signs, unknown dashes, EUR-thousands units and unaudited
qualification. Cover-page context does not enlarge the incorporated41/42
statement selection. The source map's historical production_consumed flag
remains false; actual use is reported separately by the consumer's consumed field.

Requests without the field preserve existing behavior. Missing, altered or
unsupplied intermediate statement evidence is rejected even when the ordinary
phase hashes are recomputed. The field is supported through normal request
construction and final consumption; supplied interpretation overrides cannot
replace the statement input.

The 9M evidence is the original retained-P1 comparison in source-bes-dep-01
attempt005, with 18 actual adverse controls and 97 selected regression tests.
Q1 attempt004 consumes the original PDF P1 from attempt001, with 17 actual
adverse controls and complete protected-answer comparisons. The shared focused
suite at that point had 22 tests. The Q1 run also reproduces the complete retained 9M
answer. These checks establish consumption of the two finite supplied inputs.

Earlier Q1 attempt002 and attempt003 downstream checks used selected extracted
text. Their source maps remain evidence, but those downstream checks did not
establish original-PDF consumption. Attempt004 retains the initial historical
comparison failure: current code reports page 287 of the base prospectus as
having no retained native text. A documented comparator repair adds only that
source-backed diagnostic to the historical answer before comparing the full
answer. It does not establish that the page is blank. All 14 original source
dependencies remain unresolved and Q3 remains PARTIAL.

Independent financial/legal review, historical authenticity, general parsing,
fresh native extraction and whole prospectus completeness remain unresolved.

The FY2010 map and corrected whole-source description are retained in
source-bes-dep-08 attempt005. Product evaluation uses attempt006's exact
original-source comparator and actual public consumers. Its recorded result
determines the integration verdict; adding the profile alone does not establish
that verdict. Existing installed-wheel evidence predates this profile and
requires a separate current installed evaluation.
