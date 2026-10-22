# Concrete archival follow-up

Four metadata requests are retained. Wayback CDX returned HTTP 503; its
availability API returned no snapshot for the queried URL/date. Neither is
evidence of historical absence. Two Arquivo.pt version-history pages return
twenty indexed records for the 2010 Portuguese URL, with the earliest returned
PDF capture at 2015-04-24 13:29:17. One other indexed record is HTML despite
the .pdf URL and must not be treated as a PDF capture.

The metadata response limit of 2 MiB cannot hold the known 8,125,384-byte PDF.
Admit one additional content retrieval from the exact archived-original link
in that earliest record, limited to 10 MiB and 45 seconds. This is a concrete
content verification step within the same source-authority package, not more
search queries or an unchanged retry. Retain failure if the capture cannot be
retrieved. Compare complete archived bytes to the retained current PDF; do not
infer equivalence from filename, year or the archive's uninspected digest
format. Source mismatch vetoes exact-byte corroboration.

If equal, the bounded conclusion is that the independent archive supplies a
2015-dated capture of the same bytes. This establishes neither original
publication nor presence in 2011, and the current product has no typed
observed-by capture field. Keep report_scope's external facts unknown. Strong
authentication or independent legal-review acceptance is not established by
this retrieval. The local receipt-bound consumer runs without assigning any
metadata date to document_date or known_from.
