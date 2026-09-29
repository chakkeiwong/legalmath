# Bounded review of a concurrent source-helper change

After E4/attempt-002 passed all 277 tests and built the documents, the shared
`source_references.verify_table` changed from Python dictionary equality to
canonical-byte equality. The change is preserved as concurrent work. Its exact
diff is one comparison expression. The accepted baseline archive contains the
previous helper bytes and reproduces the tested method identity.

Question: does this stricter representation check change any prepared request
or source-table behavior used by this increment? Comparator: the 32 retained
E3 requests and their exact hashes. Pass criteria: all newly prepared requests
are identical, lossless decoding passes, and the focused source-reference,
readable-table and transport-continuation tests pass. A changed request,
unexpected method diff, validation failure or input mutation vetoes acceptance.
This check uses no live calls and cannot establish model comprehension.

The arithmetic, native compilers, instrument calculations, bank engine and
selected financial regression did not change. Repeating their full runs would
not distinguish the effect of this source-table comparison. Inspect the exact
diff, exercise the changed helper, preserve both method versions and record
the result as a supplemental qualification. Do not reset phase counters or
rewrite the old PASS manifests. The master correctly requires reassessment
when its broad input inventory changes; use the immutable tested snapshot
for reproduction rather than silently treating the mutable workspace as it.

This revised bounded check passes the skeptical audit: it targets the only
new dependency behavior, uses byte equality as an integrity criterion, and
does not promote it to legal interpretation quality. The current live study
remains unexecuted and awaits the previously requested 32-call allowance.

The first inventory check also detected a concurrent addition of ten lines to
`06k-executable-dates.tex`, explaining this same canonical-value distinction.
No executable code or instrument mathematics changed there. Its tested bytes
are recoverable from the protected baseline; the compiled PDFs still match E4.
Freeze those PDFs and the tested chapter. The focused source-helper check binds
the E3 method inventory, which deliberately excludes manuscript prose. The new
chapter prose is concurrent work, outside this document-build acceptance; no
claim is made that the old PDFs contain it. Preserve the initial inventory
failure as a diagnostic rather than erasing it or rerunning unrelated phases.
