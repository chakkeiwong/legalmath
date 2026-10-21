# Review of the existing request-format diagnostic

This amends the runner of the existing six-call diagnostic; it grants no new
calls, task attempts, repairs, deadline or acquisition continuation. The
checkpointed plan, original result note, original preflight and both earlier
authorizations remain unchanged. The proposed deadline paragraph was retained
separately, and the exact checkpointed plan bytes have been restored. Mission
check passes and `product-contribution` is admitted.

The first two invocations were stopped before reservation. The first waited on
the shared provider lock. The second waited for P10 settlement, but its one-hour
batch clock incorrectly included P10's authorized two-hour service cooldown.
Neither invocation tested P14 or Gatecoin. A subsequent unfinished edit also
left invalid Python indentation. These are local diagnostic defects, not
provider responses. Fix them before dispatch.

Dependency review: authenticate the fixtures and all six unchanged-content arms
first. Wait for the existing master owners and both recorded P10 processes to
settle. Then hold the existing master supervisor/run locks while sending the
bounded diagnostic, so another owner cannot start between its calls. The
service lock and closed circuit remain mandatory. An open circuit, unknown
lock holder, changed binding, altered inputs, exhausted ceiling or deadline
vetoes dispatch. A branch's invalid request does not block the other branch;
an explicit safety refusal stops only subsequent variants of that branch.
Service failures stop both branches under the existing shared policy.

The owner wait ends at the original grant deadline minus 305 seconds. The
one-hour batch starts only after owner settlement. Every reservation must still
have at least 305 seconds under the original grant, and every provider process
is bounded to 300 seconds with no retries. Count reservations across the two
retained predecessor authorities and this revision together; a new source hash
cannot reset the six-call ceiling. Refuse any restart after any reservation.
Reconcile a previous worker by its PID and Linux start identity, including the
existing top-level identity format. Archive the two stopped attempts.

Evidence contract remains unchanged: compare authenticated terminal outcomes
on the actual rejected requests, using the same model, route, legal content and
original schemas. Only exact schema expansion or JSON whitespace may change.
An output file or exit zero alone cannot pass; require a completed turn and
validation against both schemas. Keep successful output outside production
checkpoints. One observation per form cannot distinguish a format effect from
intermittent service behavior, establish legal correctness or rank models.

Skeptical audit: **PASS subject to offline verification before launch**. The
baseline is the actual failure receipt, not different neighboring requests or
ten historical owner attempts. The scheduling corrections preserve the outage
stop and active P10 work. No experiment artifact can establish unobserved HTTP
framing or identify an undocumented provider parameter. The earliest checks
are Python compilation, authentication of all six prepared inputs, the fourteen
positive/adverse schema controls, zero reservations under every authority,
dead identities for both stopped diagnostic attempts, and lock/deadline checks
without provider calls. A failed check blocks launch rather than being relabeled
as a provider result. Actual provider outcomes and the mission refresh will be
retained after this diagnostic settles.
