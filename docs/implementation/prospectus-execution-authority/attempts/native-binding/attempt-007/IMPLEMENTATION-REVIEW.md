# Pre-run parent-binding clarification

The protected 2009 request contains correction_admission and
source_report_readings. Both bind the old graph hash. The selected runtime
changes execution metadata, and removing hybrid_ocr for fresh extraction changes
the bundle hash. Passing the unchanged parent hashes would correctly refuse;
dropping the corrections or report readings would test a different question.

The existing plan already requires checking each product against its own parent.
Implement that requirement with the existing product and admission APIs: run
service.source_product on the original request with only correction_admission
temporarily removed; retain that raw P1; rebind the exact original correction
packet's graph_sha256 to the actual raw graph; apply corrections.admit; rebind
the exact original report-reading packet's graph_sha256 to the corrected graph;
seal the complete P1 through service.seal. The fresh request alone removes the
retained hybrid_ocr input. No production method, quotation, correction operation,
image binding, reading order or interpretation is changed. The actual P2–P5 and
answer consumers then run normally.

The validator reconstructs this sequence from raw P1 and the protected request,
checks correction entries and complete source units, and checks report readings
through their real admission API. Semantic comparison removes only explicitly
checked parent hashes from assembly, clauses, corrections and report readings;
runtime metadata and fresh/retained input identity are verified separately.
Missing raw P1 or any changed original instruction refuses acceptance.

Audit: PASS with this clarification. It repairs a stale-parent assumption before
native execution and leaves all admission, process, time, storage and promotion
bounds intact. Default native subprocess timeouts are capped at 60 seconds by
the recording driver; command arguments and returned bytes remain unchanged.
All Popen calls remain observed by the common 12-start ledger. The driver is
instrumentation and composition of real APIs, never a replacement extractor.

The prefreeze unit run retained 18 passes and one fixture failure: changing the
answer in memory also changed P3 through a shared Python dictionary reference.
The consumer correctly rejected that corrupted product before reaching the
intended independent forged-answer check. Deep-copying the test answer isolates
the intended mutation. This changes no production behavior or experiment budget.
The failed XML remains retained; the subsequent frozen suite verifies the fix.
