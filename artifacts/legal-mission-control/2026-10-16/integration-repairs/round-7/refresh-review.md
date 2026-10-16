# Reconcile full refresh after the wrapper timeout

The inherited child timeout is 300 seconds. Historical evidence validation now
exceeds that duration. Saved owner results and mission history remain durable;
the timeout sets `mission_sync_error`. Do not reinterpret a timeout as a passed
validation or weaken the validation itself.

Reuse the reviewed round-six bookkeeping recovery. After all writers exit,
record exact mission, program, binding, state and ledger hashes under existing
locks. Run the exact mission `refresh` and master `verify` commands, retaining
their full output, return codes and elapsed times. Read-only checks may run in
parallel. After both pass, reacquire locks, require identical input hashes,
matching cumulative calls and attempt allocations, no running owner and the
exact observed timeout. Require the current binding and applicable completion
review to have succeeded. Clear only the pending timeout and append a recovery
event with those receipts. Any other error or changed input vetoes recovery.

This is completion of the already-required refresh, not a new repair, attempt,
service grant, source edit or success result. The helper's `finish` action only
runs the existing master `run` command to drain eligible command work; it does
not manufacture a completion review. It must precede snapshot capture.

Skeptical audit: PASS for this narrow reconciliation. The evidence is successful
full validation of unchanged inputs, not process liveness or an elapsed timeout.
The script neither changes production code nor removes historical failures.
The original product and tool acceptance criteria remain open.
