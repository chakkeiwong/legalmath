# Recovery of an already completed request revision

G3 attempt 3 stopped before any new provider call. A scored retrieval request
had originally failed before reservation; its reviewed rank-only replacement
then succeeded in an immutable revision directory. On reuse, the guard looked
for any counted reservation with that arm name before looking up the existing
exact replacement. It therefore rejected a cached success as a proposed retry.

Repair: first find the immutable directory determined by the full current
request/schema/route/timeout binding. If it contains a completed row, reuse it
through the ordinary binding and response-reference checks. Otherwise preserve
the existing prohibition on changed requests with counted reservations. Never
redispatch an interrupted reservation or create a new revision for a billed
request automatically. The failed attempt and all original responses stay intact.

Audit: this is a replay bookkeeping defect, not a changed experimental request.
The smallest regression check constructs the failed ancestor and its successful
counted replacement, and proves reuse cannot call the provider. The repair uses
one recorded method revision and zero model calls. Continue G3 only after it
passes; the prior source-scope, product and coverage reviews remain applicable.
