# Source route refused before product comparison

The optional source API and three native call-site changes are implemented but
not yet validated on the full source. Preparation passed. The traced pdftotext
child exited zero, but the driver rejected one captured stream at its20MiB
limit before saving either stream. The trace retains85 records and the actual
child identity. The exact stdout/stderr size is not retained; it is wrong to
claim an exact size or XML equality from this attempt. This is a driver
diagnostic-retention defect as well as an inherited-limit mismatch. The limit
was selected for small OCR output without measuring full-document bbox XML.

The focused checks then ran independently:11 passed and1 failed. The failed
test expected an undeclared-executable error but its executable lived under
the deliberately reserved /tmp namespace. The earlier path rejection is
correct; the fixture does not reach its stated target. No host fallback ran.
Repair the fixture to use a permitted, undeclared executable path and retain
a separate reserved-path test. Do not weaken the expected rejection.

Two supervised reservations were used: strace and pytest. The trace records
one internal pdftotext child, bringing the previous visible lower bound27 to30.
Stage-driver commands are separately retained, not counted as worker starts.
No repair, source-product, construction or answer stage was run. The original
20MiB bound is unchanged and the failed result must stay failed.

| Decision | Primary criterion | Veto status | Uncertainty | Next action | Limit |
| --- | --- | --- | --- | --- | --- |
| Reject this candidate execution | Complete source and answer comparison absent | Output bound and one fixture failure | Exact stream size lost | Review explicit per-call64MiB ceiling with old20MiB default, bounded draining, evidence retention and fixture correction | No package rejection or correctness claim |
| Preserve trace for inventory nomination |85 records retained; successful native child exit | One unresolved stdout pipe metadata record | Enumeration is not dependency closure | Validate extended inventory by sealed XML equality against attempt004 | No universal runtime or legal conclusion |

The failing result invalidates this run's completion claim; it does not show a
fundamental defect in Poppler, PyMuPDF, Tesseract or Bubblewrap. The strongest
alternative explanation for future equality remains a shared error on exposed
development data. All four delivery flags remain false. See invocations,
process-ledger.json and the final method snapshots for reproducibility.
