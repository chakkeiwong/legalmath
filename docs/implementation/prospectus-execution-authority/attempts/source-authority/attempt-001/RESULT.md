# Edition and historical-source evidence

All six retained English/Portuguese 2008–2010 editions match their acquisition
receipts, every receipt-bound file, and their respective retained issuer-index
links. This verifies the local acquisition chains and distinguishes editions.
It does not independently authenticate original publication or execution.

A new Arquivo.pt capture supplies a narrower historical finding. The archived
Portuguese 2010 PDF is exactly the same 8,125,384 bytes as the retained issuer
copy, with SHA-256
`981fa3f96ed65da0d42f3de9c35797f1dfbd676c6f6c11fbcf394b54adff3058`.
The replay supplies a Memento-Datetime of 24 April 2015 at 13:29:17 GMT,
matching the version-history entry. This supports an archive-recorded capture
of these bytes by that date. It does not establish publication in 2011 or
historical availability when the 2011 prospectus was issued. The archived
server's Last-Modified is 23 April 2015, whereas today's server gives 31 December
2021 for the same bytes: a concrete reason not to use that header as original
publication date. The PDF creation date is another distinct observation.

The two Arquivo.pt index pages contain twenty records, nineteen labelled PDF
and one HTML response at a .pdf URL. The earliest returned PDF is the capture
retained here. The Wayback CDX request returned 503, and its availability
endpoint returned no snapshot for the queried URL/date. These outcomes are
neither an exhaustive search nor evidence of historical absence.

The Portuguese 2010 acquisition receipt now also reaches actual P1 and the
report consumer in this attempt. Nine checks pass and five adverse controls
reject. The final report answers and instrument questions match the retained
baseline exactly. Publication, historical availability and authenticity stay
unknown; the receipt's acquisition date is not assigned as a document date or
earliest knowledge date. No independent legal acceptance is asserted.

Code tracing finds a concrete remaining integration boundary:
`report_scope.admit` rejects any supplied publication, historical-availability
or authenticity field, and `explain` always withholds historical availability.
`source_graph.build` binds acquisition bytes and marks authenticity as requiring
review. It has no typed archive-capture or observed-by predicate. Therefore the
2015 capture is retained evidence for further source analysis, not a newly
integrated historical fact. A future reviewed extension must distinguish exact
publication from an observed-by upper bound and validate source/edition,
archive metadata, content and query date. It must reject a 2015 capture as proof
of 2011 availability. Missing external evidence and this implementation boundary
are separate gaps.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain six acquisition chains | Hash and link comparisons pass | No integrity mismatch | Independent authentication absent | Use exact editions for onward-source tasks | Issuer route alone proves authenticity |
| Retain 2015 capture corroboration | Full archived bytes and Memento date match | Capture is later than the 2011 query | Original publication date | Seek contemporaneous filing or exact earlier capture in reviewed continuation | Historical availability in 2011 |
| Keep task partial | Actual receipt consumer passes nine checks and five adverse cases | Historical acceptance still withheld | No typed archive-evidence consumer or reviewed task acceptance validator | Continue source-bes-dep-01 now | Program completion |

The local run took 27.77 seconds. `started.json` and `edition-inventory.json`
retain the exact command, worktree-pinned modules, methods, inputs, environment,
CPU setting and deterministic seed status. Network requests and content identity
are retained in `archive-result.json` with original response files.

Post-run review: the strongest alternative explanation is a later replacement
file that matches today's bytes but differs from what readers saw in 2011.
This evidence cannot exclude it. An earlier authenticated filing with differing
bytes would change the edition analysis. The least supported inference remains
original publication and contemporaneous legal availability. No OCR-package
limitation or legal reliance conclusion follows.
