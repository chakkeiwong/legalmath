# Final controller audit and bounded correction

11 October 2026 UTC. The post-repair execution exposed no cancellation of an
independent branch: the 52 product regressions finished while model qualification
was running. A further skeptical code audit found two settlement risks worth
correcting within the controller's already reserved second attempt.

First, changed input can classify a task INVALID while its recorded process is
still running. It must remain in the running list, hold its resource lock and
prevent a completion-edge report from settling. Second, a mission-refresh error
is retained after a valid task result, but must not disappear behind a COMPLETE
execution label. A subsequent run/settle retries that synchronization without
rerunning the completed task; unresolved synchronization is explicit remaining
work. Preserve the old code under controller-attempt-2/before and retain attempt
one's result. No new node, allowance, deadline or unbounded repair is introduced.

Additional checks verify adoption of a valid completed orphan without dispatch,
preservation of a live orphan, and branch isolation even if the worker handler
raises an unexpected exception. These are execution criteria only. The current
model response and legal claims remain subject to their separate source review.

Pre-run audit passes: these corrections address concrete state transitions,
use the same dependency model and source identities, preserve reservations, and
have discriminating behavioral tests. They do not promote proxy metrics or
weaken the conditions for accepting a legal or model result.
