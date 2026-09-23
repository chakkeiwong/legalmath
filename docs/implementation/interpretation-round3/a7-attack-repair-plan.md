# Explicit revision after the four-attempt stop

The original four failed-attempt limit has fired. Acceptance remains blocked;
this note explicitly revises the plan before any retry. Attempt 04 passed 381
tests and replayed the successful source checks, but both fresh criticism outputs
used the literal `conclusion` where the REBUT wire contract requires the target
argument's ID. The error reported only a generic mismatch. The intended rebuttal
may be semantically meaningful, but the validator must not infer or silently
rewrite a malformed proposal.

Repair the specific interface: describe `target_component` in its JSON schema,
give a concrete identifier example in the prompt, and report each failed attack's
field, actual value, expected target ID, source conclusion and target proposition.
Pass structured validation details to the bounded repair alongside the short log
message. Test that the original malformed attacks remain rejected, that a
well-formed attack with the wrong proposition still fails, and that the correct
named target passes. Do not relax argument semantics or remove attacks to pass.

The revised supervisor permits at most six failed attempts, providing two further
attempts for this diagnosed interface repair and any final integrated defect.
The 77-total live increment ceiling is unchanged: 55 calls are consumed, leaving
22. Exact replay of successful 23EC46 responses remains mandatory; only changed
criticism may be newly dispatched for it. 24EC16 and the omission/clean challenge
must still execute. The original accepted source and challenge targets remain
unchanged. No extra provider, external communication or consultancy is involved.

Skeptical audit: the four-attempt stop invalidated proceeding under the old plan,
not the retained test results or the research direction. This is an explicit
plan/contract revision with a narrower repair diagnosis. Required evidence is
targeted rejection/acceptance tests, full regression, exact retained replay and
successful remaining live checks. A clean diagnostic cannot substitute for a
missing check. If the revised cap is reached, preserve uncertainty and report
incomplete acceptance; do not silently increase it again.
