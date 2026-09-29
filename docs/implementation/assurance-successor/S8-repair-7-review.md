# Native reviewed allowance slices must survive resume

The three peer tasks were first created after the reviewed arm ceiling became
120. Their slices therefore have maximum=120 and no migration receipt. Resume
incorrectly required a prior 60 migration for every 120 slice, raising E_INTEGRITY
before the task body could report its failure. The executor then waited for its
active pilot while the main thread unwound, concealing the initialization error.
This is reproduced against all three actual peer single-arm files.

Accept a directly created reviewed slice only after verifying its grant identity,
current reviewed amendment, every original globally reserved slot/request and
absence of a prior 60 archive for that same slice. Preserve its original bytes
and bind a CREATED_WITH_REVIEWED_LIMIT origin receipt; every reservation prefix
and the 120 maximum remain unchanged. A migrated slice whose old receipt was
removed must reject, as must detached or duplicate reservations. Existing
migrated slices retain their original checks. This is provenance reconciliation
under the already authorized 120 ceiling, not extra quota or a refund.

Preflight all slice amendments before starting any thread, so initialization
errors surface before an independent model call. Test initial reviewed creation,
resume, unchanged bytes on repeated resume, lost migration proof, wrong slots
and duplicate slots. Then apply the same checker to all eight actual slices
and replay cached proposal providers without dispatch.

The eighth S8 attempt retains seven predecessors and all calls, original
source/reference freezes, per-issue bounds, the 48-hour campaign and 500-call
grant. Correcting this bookkeeping defect does not change a reading, make a
failed source question correct, or justify study promotion. Current regression
needs a final run after this repair; earlier overlapping runs remain historical.
