# One diagnosed comparator repair

The first candidate failed before writing its fixture or package. The source
checks, geometry and arithmetic completed; building the primary-statement
comparator raised IndexError on a valid unlabelled subtotal row. This is a local
assumption bug, not evidence against the source tables or an external package.

The failed checks/program and measured command receipt are retained in
failed-candidate. The original candidate-preparation receipt stays unchanged.
The changed implementation considers labelled rows for named comparisons and
still requires exactly one match for each of nine expected statement labels.
It uses a list rather than a dictionary so duplicate named rows cannot collapse
silently. Missing, duplicate or numerically different comparators must fail.

Audit PASS: this directly repairs the reproduced cause without weakening any
required tie-out. Add adverse checks for missing and duplicate named comparators.
The changed run uses candidate-recovery.json, keeps cumulative time/storage and
consumes the one permitted changed recovery. No further retry is authorised
under this candidate plan if it fails; preserve that failure and review an
independent source route instead. No production change has occurred for444.
