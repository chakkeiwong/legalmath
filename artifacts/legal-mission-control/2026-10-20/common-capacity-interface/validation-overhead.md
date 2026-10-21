# Local validation overhead observed during adoption

At 18:32 UTC on 20 October 2026 the old live supervisor was safely handed over.
The unchanged predecessor wrapper then ran its registered local commands. Its
`run` command required approximately 14 minutes before returning WORK_REMAINS
with no running owners and no synchronization error. Mission refresh then took
approximately five minutes. The final verify command was still running after
seven minutes. These timings are descriptive process observations; they are not
a profiled allocation of time to individual functions.

Inspected code shows `Execution.locked()` calls revision-specific
`validate_state_history()` on each lock entry. `Execution.__init__()` and
`start()` also call `validate_program()`. The current revisions recursively
verify historical projections and protected evidence. `sync_mission()` runs
full mission validation in process and then launches a separate full refresh.
This repeated work is a credible explanation for CPU-bound local delay, but a
scoped profile is required before attributing exact fractions of runtime.

No new provider charge was recorded during this interval; the total stayed at
3485. The existing live deadline expired at 18:55:16 UTC while local validation
was still completing. This is distinct from provider capacity or service errors.
It does not invalidate the deterministic capacity tests or permit skipping
evidence checks.

The smallest follow-up is a no-provider profile of one current validation, with
the same frozen evidence and pass/fail outputs. Any optimization must retain
content identity, mutation detection, transaction checks and cross-process
freshness. Caching merely by filename or trusting a previous successful check
would be unsafe. This follow-up is recorded separately and does not alter the
sealed capacity implementation, its historical baselines or its deployment.
