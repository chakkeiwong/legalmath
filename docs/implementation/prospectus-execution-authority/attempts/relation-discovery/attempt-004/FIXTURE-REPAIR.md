# One bounded synthetic-fixture repair

The first focused run passed61 tests and failed one fixture precondition:
the synthetic disconnected value removed v2's repeated-column support, so no
baseline candidate existed to limit. This is a test-design failure, not evidence
that the limiter accepted disconnected text. Retain the failed XML, invocation
and three pre-repair method files. Add a third ordinary row so two clean rows
support the value column, matching the actual BES page's repeated support.
The algorithm remains unchanged. Rerun the suite once using a distinct retained
stage. This consumes the plan's one local repair allowance; no automatic retry
is authorized if the next discriminating run fails.
