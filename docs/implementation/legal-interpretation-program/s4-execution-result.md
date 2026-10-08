# S4 result and separate verification

The reviewed S4 program executed successfully on 6 October 2026.
The selected result is
[attempt-1/result.json](../../../artifacts/legal-interpretation-program/successor-s4/attempt-1/result.json);
its SHA256 is
798907115d69822755d7d417c50a95aeb37faec41b89a2fae1bc503bbb522ce6.

The exact commands were:
```text
python3 -m scripts.run_legal_interpretation_master resume
python3 -m scripts.run_legal_interpretation_master verify
```

Both returned success. The second command independently rebuilt the Java
executions and Lean certificates, recomputed source lowering and checked the
whole actual investigation. The required suite passed 296 tests in 484.46 seconds.

The review repaired an invalid monotonicity assumption by separating fixed
four-state evidence from positive recursive heads. The actual v4 investigation
now computes 20 declared standards in Java, proves its returned ten-head set
sound and closed under the encoded theory, and binds that result to 108 records
across six branches. Eight separately retained synthetic recursive scenarios
also have kernel-checked results.

The [result note](../../../artifacts/legal-interpretation-program/successor-s4/attempt-1/result-note.md)
records the decision table, proof scope and remaining trust boundaries.
The [refreshed S5 plan](../../../artifacts/legal-interpretation-program/successor-s4/attempt-1/next-phase-plan.md)
requires specific source-to-rule prerequisite work before a fresh prospective
whole-method window.

All 35 readings, 70 role records and 46 open legal obligations remain preserved.
32 readings still lack formalization. English fidelity and legal correctness
remain NOT_ESTABLISHED. No substantive legal closure, future-source observation,
live provider call, network retrieval or GPU action is claimed.
