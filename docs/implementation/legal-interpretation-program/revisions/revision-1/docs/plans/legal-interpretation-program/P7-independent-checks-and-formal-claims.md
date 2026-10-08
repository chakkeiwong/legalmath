# P7: Verify scoped invariants and expose silent failures

Status: PLANNED_NOT_EXECUTED. The [master program](../legal-interpretation-master-program.md)
controls evidence, default assumptions, resource limits and source-fidelity claims.
Dependencies: P6.

## Question and inputs

Which exact properties of the implemented interpretation layer can be independently established?

P6 implementation and actual outputs; phase-specific counterexamples; existing independent Boolean and Lean mechanisms. Freeze the declared formal domain before generating challenges.

## Implementation

1. Write precise propositions for branch accounting, preservation of unresolved premises, dependency invalidation and the relation between the reference evaluator and supported lowering. For small finite declared domains, construct a materializing subset-enumeration oracle that differs from the production evaluator and compare the full branch outcomes, not just aggregate success flags. State which properties are proved versus exhaustively checked versus sampled.

2. Implement small Lean statements where the actual theorem is useful; keep parser/serializer/runtime correspondence as separate obligations unless actually proved. Do not claim that a set-theoretic theorem verifies the Python parser.

3. Generate exhaustive cases only within a declared finite domain. Derive expected results from an independently implemented specification. A literal duplicate of the production algorithm is not an independent checker.

4. Inject targeted faults: omit a footnote, substitute actor identity, swap opinion role, invert a condition, erase a branch, change a source hash, coerce unknown to false, and carry a stale receipt after amendment. Require detection where the invariant actually covers the fault.

5. Keep source-meaning hypotheses visible beside formal results. Do not manufacture legal oracle labels for faults that depend on disputed natural-language interpretation.

6. Record command, git state plus dirty-file hashes, environment, CPU mode, source versions, seeds (N/A for exhaustive deterministic runs), wall time, actual outputs and all unsuccessful checks.

## Files and validation commands

Proposed finite reference/fault checks and, where justified, InterpretationSemantics.lean with real kernel receipts; independent result/claim map.

The following test files are planned deliverables, not existing executed tests.
After implementing them, run these exact forms from the repository root:

```text
.venv/bin/python -m pytest tests/interpretation/semantics/test_invariants.py -q
.venv/bin/python -m pytest tests/interpretation/semantics/test_faults.py -q
```

Add the relevant existing regression paths discovered from actual touched imports.
Record those exact paths in the phase revision before executing; do not invent a
successful regression result or invoke a broad suite unrelated to the change.

## Discriminating challenges

A tautological theorem is sold as English correctness; only selected successful cases are counted; a shared implementation bug escapes both checks; a semantic mutation is detected only because the answer was manually labelled.

## Acceptance and failure decisions

Every claimed invariant has its exact observed or kernel-checked evidence and domain; declared detectable faults are caught; missing checks and unproved correspondence remain explicit. The suite distinguishes engineering correctness from legal source interpretation.

An invalid checker is a continuation veto for its evidence. A candidate counterexample triggers the owning phase's repair. If a theorem proves a different target, correct the claim and plan before rerunning.

## Result and next-phase refresh

P8 receives the actual proved/checked domains, source assumptions, unresolved obligations, fault coverage limits and the code/method version to freeze for later observation.

Save the executed plan version, input/output hashes, commands, results,
uncertainties, decision and refreshed successor plan under the immutable attempt
directory specified by the master. A planned test command is not run evidence.

Resource boundary: Deterministic finite checks first; no stochastic ranking or unbudgeted sweep. Each long formal/benchmark run needs its concrete evidence contract and resource cap.
