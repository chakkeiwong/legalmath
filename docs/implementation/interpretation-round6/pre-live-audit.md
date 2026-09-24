# D1 audit before live dispatch

D0 passed 25 tests in 22.47 seconds. The real source partitions into 16, 6 and
7 units, with 1,951, 1,782 and 1,170 source characters. Compact inventory
requests occupy 5,681, 4,371 and 3,868 bytes, excluding the unchanged response
schema. This is a transport measurement, not evidence of better interpretation.

Two gaps require repair before dispatch. The probe loop must retry only a
recognizable transient service error, not authentication, schema, authority or
input-cap failures. Also, retained replay currently matches the original request
hash against the allowance ledger; compact transport reserves the wire request
hash. Replay must recompute that transformation, verify its provenance, and find
the original counted reservation without spending a new call. A forged mapping
must fail. Preserve the original D0 attempt and test these repairs separately
before D1; D2 will cover the final tree.

The 200-byte availability probe deliberately contains no legal reading. Its
success cannot substitute for an inventory piece. Two probes at most plus an
18-call investigation fit the unchanged 20-call remainder. A permanent error or
two failed transient probes stop live dispatch. Independent deterministic work
continues. Input omission, incomplete readers, source changes and unverified
cross-piece context remain acceptance vetoes.
