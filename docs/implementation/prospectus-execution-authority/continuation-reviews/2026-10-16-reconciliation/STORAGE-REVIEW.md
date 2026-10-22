# Retain equal results by exact reference

The first 2009-default preflight passed in 20.1 seconds and retained about
15 MiB of complete products. Repeating those byte-identical JSON objects for
all five routes would exceed the declared 30 MiB cap. The first script and
all its results remain unchanged.

Before the remaining routes, use a separate compact wrapper. It executes the
same current constructors and full equality comparisons. For an equal product,
retain its existing file reference and digest instead of another byte copy.
For a changed product, retain the full newly computed object. Check all referenced
source hashes before and after the run. This changes storage only: a digest
comparison is not substituted for the full object equality criterion, and a
changed result cannot be labelled equal to avoid storing it. Keep the same
120-second case and 30 MiB combined evidence limits. A mismatch stops further
dependent preflights if its retained bytes would exhaust that cap.

Review verdict: justified storage correction. The source products already
exist in immutable attempts and are explicitly hashed by started.json. Exact
references preserve reconstructability without rewriting historical evidence
or expanding the budget. New wrapper and base-script hashes are recorded.
