# Compact response-alias correction

The first alias attempt was invalid as a transport remedy: it wrapped the
entire 40,754-byte request inside the model prompt and increased the wire to
48,778 bytes. It timed out and remains a failed attempt. The v5 review caught
the design defect before treating it as evidence.

The corrected codec keeps source text, claims, candidates, questions and tool
context in their original locations. It removes only the repeated long
`required_pairs` and span identifier spellings from the model-facing schema,
replacing them with request-local p/s/e keys and index tables. It adds no
duplicate original request. The retained request shrinks to 40,488 bytes.
The caller-held full request and maps are expanded before the unchanged
source-reference, executable-reference and fidelity validators run.

Fresh focused controls pass exact judgment round trips, unavailable/blocked/
encoded states, foreign and duplicate alias rejection, detached table and
question rejection, and protection against manufacturing an executable
comparison. A fresh wrapper test must pass before dispatch. The final retry
uses the same request, route, 180-second cap and both perspectives. It is
limited to the failed baseline batch and consumes at most two repair calls.
If it times out or returns an invalid/incomplete response, no further live
retry is authorized by this continuation. Bulk execution then remains blocked
because the 12-pair batch is not demonstrated feasible under the declared cap.

The response alias mechanism is a transport optimization only. It cannot
establish semantic support, legal accuracy, service reliability, tool ranking,
or full-matrix capacity. All prior attempts, raw transport logs and repair
entries remain immutable.
