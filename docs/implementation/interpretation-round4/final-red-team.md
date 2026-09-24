# Final integration red-team findings

24 September 2026, during the final B5 regression. The current acceptance inputs
are frozen until that command returns. Do not silently patch a running attempt.

1. With the new example registry enabled, exhausting the final query call leaves
   an explicit finding but the older `execution_complete` condition only checks
   inventories, fidelity and criticism. The monitor could cache that incomplete
   investigation as completed. Required repair: include requested example-query
   completion and exhausted argument evaluation in the execution predicate;
   verify a failed query is retried within the existing budget.
2. A scheduler snapshot pins registry/source bytes, but settings and replay input
   paths still reference mutable external files. Required repair: copy and hash
   these run inputs before dispatch and use the copied paths; include the retained
   configuration in its event record.
3. A scheduling wrapper may return normally after a child reports a failed or
   exhausted monitoring result. Retain the nested status, but add an explicit
   top-level attention state so an operator cannot mistake process exit zero for
   successful investigation. Correlated interpretation uncertainty is separate
   from process completion and must remain visible in the result evidence.
4. Required question partitions may be deferred by a replay limit. Preserve the
   detailed file and propagate the incomplete execution to the top-level finding
   and execution flag. Incompatible meanings are legitimate uncertainty; a
   resource-exhausted or failed requested check is incomplete execution.
5. A registry-supplied publication date and individual quotation are not
   independently authenticated legal judgments. Preserve this distinction in
   the documentation. No software change can make the existing one-family
   scripted evaluation a heldout legal-accuracy study.

These are implementation repair triggers, not evidence against multiple-reader
interpretation. All earlier accepted artifacts must remain intact. Execute a
successor integration-repair phase with focused regressions and a final suite;
do not reset acceptance counters or relabel B5 historical output. No additional
model calls or institution access are required for these repairs.

## Executed repair

B5 completed 498 tests and its Java-host acceptance before inputs changed. B6
then repaired the execution predicate for requested example queries, cyclic or
limited argument evaluation and resource-deferred question partitions. Monitor
rows now expose unresolved findings on both completed and unchanged results and
check retained evidence integrity before reuse. Scheduler settings and replay
bytes are copied into immutable dispatch-input snapshots; its summary has explicit
failure and attention states. Substantive unresolved meaning is preserved without
retrying a completed investigation merely to obtain agreement.

Focused repair checks initially found a misplaced test assertion while extending
the authority dependency regression. The assertion was moved back to its intended
test; the failed preflight was retained in the execution note. This was a test
editing failure, not evidence against the implementation target. The final B6
runner must still pass the complete suite before closure.
