# Bounded repair review before actual verification

The first focused stage passed all14 tests in0.281seconds. Post-test code
review found that the test runner prohibited subprocesses but the real wrapper
did not enforce its retained-evidence-only scope. Although the expected stale
method refusal happens before any product consumer, future named checks must
not acquire an implicit fresh-extraction allowance from this wrapper.

Retain both stage-one methods under `pre-guard-method` with their exact recorded
hashes. Add a scoped subprocess refusal around named verification and ensure
the original Popen function is restored after success or failure. A real
attempt to call Popen in the focused test must produce a retained failure
before launching. This is the one permitted implementation correction and
second/final test start; there is no third test start or repeated real check.

The guard controls ordinary subprocess creation within this single-threaded
wrapper; it is not a hostile-code sandbox or authority to change host policy.
Cooperative SIGTERM is converted to a recorded timeout, and KeyboardInterrupt
is retained separately. Hard kills or an unwritable evidence directory remain
outside the finalization guarantee. Native validation criteria are unchanged.
