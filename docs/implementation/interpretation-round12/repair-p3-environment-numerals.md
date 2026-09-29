# Executed repair for P3

P3 attempt 01 stopped before comparison because the independent solver
environment lacks pytest. Its fixture loader imported a test module through the
Catala support module. Export the retained corpus with the application Python
and load only JSON in the solver Python. No package is silently installed and
the compared corpus is retained and hashed.

The focused rerun then exposed a separate exact-integer defect: cvc5's
`getIntegerValue` uses Python's limited decimal conversion and rejected the
retained 6,000-digit case. Read the solver numeral through LegalMath's exact
integer parser instead. The corrected diagnostic compared all 344 cases and
replayed a separating boundary witness against actual Java; it passed.

The actual-runtime mutation diagnostic killed all four required targeted faults
(29 boundary detections, 1 future-evidence detection, 67 multiple-exception
detections and 2 version-end detections). PIT baseline JUnit passed, but its
worker socket was denied in the sandbox. The approved trusted master command
must rerun PIT and the full combined phase. The sandbox failure is not evidence
that PIT or the machine is unavailable.

Other pre-live review repairs: bind the fixture/PIT/evaluation helper code in
phase inputs; share regional PDF action dispatch between retained and live
sources; retain live jobs outside immutable attempt snapshots so reruns reuse
completed evidence; update the SFC content endpoint and freeze two transfer
sources. No live calls were consumed before these changes. Focused repair checks
and the full phase must both pass before promotion.
