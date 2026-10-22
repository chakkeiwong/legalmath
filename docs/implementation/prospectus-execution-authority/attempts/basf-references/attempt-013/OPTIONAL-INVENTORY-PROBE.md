# Failed ancillary inventory inspection

After the frozen candidate and omission consumers passed, an additional
read-only Python inspection tried to join all47historical marker lines and
13additional findings to current source spans. It assumed each entry in
`source_pieces` or `sources` had a top-level `unit`. That assumption is wrong
for the heterogeneous historical ledger. The comprehension raised
`KeyError: 'unit'` before any crosswalk file was written.

No crosswalk result, count or closure claim is retained from that inspection.
It was not a stage of the frozen two-reference verification protocol, and none
of that protocol's checks depends on it. Do not rerun this failed inspection
under the current package. Any future full-inventory program must review the
original record shapes explicitly. The earlier two-entry reconciliation uses
the directly inspected source rows19and21 and remains separate.

The failed command used the same worktree interpreter with `src` and `.`
prepended to `sys.path`, loaded `candidate-answer` and the original001reference
ledger, then attempted `{a['unit'] for a in anchors}`. Its exact elapsed time
was not emitted and remains UNKNOWN. This is an inspection-script assumption
failure, not evidence against a package or the prospectus interpretation.
