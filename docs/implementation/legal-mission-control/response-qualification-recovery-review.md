# Review of the declared qualification recovery

11 October 2026 UTC. The primary branch did not dispatch: construction of
`Settings(timeout_seconds=600)` failed because the validated model permits at
most 300 seconds. The ledger remains at thirteen historical calls. The omission
of a settings-construction check in the original qualification tests was a plan
error. This is an implementation failure, not a rejected legal answer or a
provider failure.

Keep the original plan, protocol, script and failed execution evidence unchanged.
Use the already declared recovery branch with a versioned executor that constructs
the supported 300-second setting before reserving any call. This narrower ceiling
stays within the original four-call allocation and deadline. It can fail for
latency; a 300-second timeout cannot show that the legal question is insoluble.
The recovery keeps the exact source, questions, schema, cases and model route.
The only changes are early validated setting construction and the supported cap.
The original expected-answer-free proposal and fresh review remain paired stages.

Skeptical review: no source or success criterion is weakened, no unused primary
reservation becomes a new allowance, no call is refunded, and the original
400-call global limit remains enforced by the same aggregate successor ledger.
The recovery code and this review are hashed before dispatch. The old executor
cannot be retried as if it had succeeded; the primary result is FAILED and the
declared alternative dependency must supply any usable result. This correction
does not qualify the separate complete product route or its live guard.
