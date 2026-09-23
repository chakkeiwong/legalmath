# Live comparison audit — retained 23EC46 alternatives

Before the diagnostic: the ongoing P5 case generated a direct-product-link
reading and a direct-or-contextual-link reading with identical fact definitions.
The finite probe comparator reported no difference in its tested points. This
is not a false equivalence claim, but it may leave a simple actionable
counterexample undiscovered.

The engineering question is whether the 128-probe convenience limit misses a
known distinguishing combination. The comparator is the unchanged finite probe
path. The candidate mechanism is the existing SMT encoder over the complete
declared Boolean domain `{T,F,U}` for each fact, with no empirical numeric
bounds. It does not establish which English interpretation is legally correct.

The generated bodies are `G AND NOT D AND L_direct` and
`G AND NOT D AND (L_direct OR L_context)`. With scope true, `G=true`,
`D=false`, `L_direct=false` and `L_context=true`, these evaluate to false and
true respectively. That substitution is the primary diagnostic target.
Confirm it in Python and both generated Java classes, then ask the solver for
its own replayable witness on the same pair.

Veto the result for changed source/candidate hashes, different fact bindings,
solver timeout or unsupported fragment, or disagreement between Java and Python.
The number and distribution of old probe points are explanatory diagnostics.
A counterexample is evidence of different encoded behavior only. A solver
no-counterexample result would concern the declared Boolean domain and checked
encoding, not English fidelity, empirical feasibility of every assignment, or
production readiness.

Preserve the selected candidate IDs and hashes, packet hash, explicit snapshot,
old comparison status, solver result and Java replay under
`artifacts/interpretation/round2/live-comparison-audit/`. If the hypothesis is
confirmed, propose an explicit complete Boolean domain policy and a regression
for interacting exception/link facts before changing the implementation.

## Executed result

The diagnostic confirmed the missed witness. Python and both generated Java
classes returned different decisions for the explicit assignment above. The
existing solver independently found a distinguishing assignment. The old
128-probe result was accurate about its finite probes, but those probes were
insufficient to expose this interaction. Calling their agreement equivalence
would have been wrong; the stored result made no such claim.

The comparator now uses the complete declared Boolean domain when both readings
have identical Boolean fact definitions and the caller has not supplied a
domain. A caller's narrower or inconsistent domain is retained. Solver
`UNKNOWN` remains visible and cannot become equivalence through a finite-probe
fallback. Numerical ranges and business-feasibility constraints are not
invented. Equivalence within the declared domain still depends on the checked
encoding and solver; no independently checked proof certificate is claimed.

P7 attempt 02 passed all **280 tests** (including **48 search tests**) and
replayed every previously recorded pair from P5 attempt 05. For 24EC50, all
three pairs remained incomparable because the fact definitions differed. For
23EC46, three of 24 pairs had replayable differences; the other 21 had
incompatible fact definitions. The specifically missed direct/contextual-link
pair now produced a difference. Replay used zero model calls and did not modify
either old investigation. These counts describe this fixed development case;
they do not estimate legal accuracy.

The accepted manifest is
`artifacts/interpretation/round2/P7/attempt-02/run-manifest.json`.
Its full test run took 165.407 seconds under the supervisor, and frozen replay
took 8.895 seconds. The first P7 attempt had already passed the full tests but
failed when the replay harness parsed fractional manifest timings with the
strict rule-data parser. `p7-repair-01.json` records the narrow parser repair.
Source and investigation bytes still use strict parsing and exact hash checks.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | What is not established |
|---|---|---|---|---|---|
| Accept this comparison repair | The frozen missed witness is found and replayed in both Java classes | No changed input hashes or Python/Java mismatch; full suite passes | Solver/encoding trust and real-world feasibility of synthetic facts | Run P8 on both retained circulars using the repaired comparator | Which reading correctly interprets the circular |

The strongest alternative explanation for a newly found difference is that the
encoded fact assignment cannot occur in practice. A domain specialist must
assess that question. It does not undo the demonstrated weakness of the old
probe coverage, and it must not be used to silently delete a candidate or a
counterexample.
