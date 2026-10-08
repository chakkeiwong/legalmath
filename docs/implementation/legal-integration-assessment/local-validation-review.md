# Review of the retained regression failure

8 October 2026. The sequential suite returned 263 passes and one failure in
`test_scoped_investigation_no_live_dispatch_and_persistent_action_budget`.
The failing assertion expected one provider call when maximum_actions=1. The
previous integration repair introduced a minimum-capacity preflight: one pair
requires two perspectives and therefore at least two actions. Zero dispatches
is the correct behavior under that reviewed policy. The test predated it.

Verdict: the assertion is stale; the production admission behavior is correct.
Update it to require zero calls, the explicit capacity-block reason, minimum
actions of two, zero consumed journal actions, and unchanged pending pairs
across restart. Preserve the original failed log/XML and all 263 passes.
Run the corrected test once in a separate folder and aggregate its result with
the original suite. No broader rerun is needed because no production source
changed after that suite.

The runner needs one explicit sealed successor review to cover the changed
test and retain the initial review. Its allowed command forms, planned phases,
route and resource ceilings are unchanged. Preserve every initially reviewed
runner/test file under `local-validation-baseline/`, and record the successor
review in mutable execution state. The original repair entry remains the one
implementation batch; this correction consumes no extra repair entry or call.
The completed A1 result references both initial and focused checks before A2
can run. A started phase without a reviewed result remains blocked.

Skeptical audit: **PASS**. This is an assertion correction to an already tested
prerequisite rule, not a changed target, hidden retry, ignored test failure or
new program phase. The initial failure remains reportable. The local program
continues only if the corrected assertion passes and source identity checks
accept the explicit successor review. All live and legal nonconclusions remain.
