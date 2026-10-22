# Pension preparation: distinguish appended plans from changed source evidence

The original component-217 preparation passed 121 tests, then refused a changed
non-code input: docs/plans/prospectus-general-build-2026-10-17.md. Its failure
and frozen preparation remain untouched. No pension candidate was admitted or
run. The full failed preparation cost is 3.5985871427692473 seconds, including
the tests, rather than adding the overlapping 3.014003350865096 seconds again.

Inspection proves that the first 14,302 bytes of the current master narrative
hash exactly to the original pension009 binding,
0f02502b097e0f6c5c8faa184c204b4eba3066c124ca3d2ff2ec8fa081e8ecaa.
The extra 3,197 bytes document the already retained BES cash-flow continuations
208–210. They do not alter the original pension argument, sources or decisions.
The current full hash is
99f654430cf4c3bc78fd0686eebe37b9e654f74c8a3b1dc5c97012d4dd7c976b.

Accept this exact append-only documentation change for the new admission.
The current runner, installed evaluator, package, tests and original comparator
remain unchanged; use the passing tests and failed preparation rather than
rerunning them. All other historical document/source identities must still
match. The named code differences remain subject to complete current/installed
consumer equality and original independent controls. No general exemption for
documents, missing originals or altered sources follows.

Audit verdict: PASS for this changed preparation. The guard correctly revealed
an inherited plan update; the broad category assumption was too strict for this
one proven append. Preserve the original failure and cumulative cost, retain
the explicit prefix proof, freeze a new review and use the original proposed
tenth BASF-reference admission. No new production edits, test reruns, wheel
builds, dependency installs or native calls are needed.
