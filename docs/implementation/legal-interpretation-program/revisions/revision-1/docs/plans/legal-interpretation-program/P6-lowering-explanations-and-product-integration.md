# P6: Run the same meaning through explanation and execution

Status: PLANNED_NOT_EXECUTED. The [master program](../legal-interpretation-master-program.md)
controls evidence, default assumptions, resource limits and source-fidelity claims.
Dependencies: P3, P4, P5.

## Question and inputs

Does the actual product preserve the declared branches and qualifications when producing explanations and executable results?

P2–P5 structures and supported fragments; existing translation.model.from_reading, qualification_adapter.run/verify, complete investigator and existing target-specific checks.

## Implementation

1. Implement semantics/lower.py and render.py from the same immutable semantic records. Serialize the branch, assumptions, scope and evidence identity alongside the executable expression and explanation.

2. Map only supported constructs to existing RuleIR/Catala targets. Reject unrepresentable modalities, quantities, partial intervals or conflicting inputs with named reasons; never silently choose a Boolean or erase a branch.

3. Implement semantics/integration.py as an optional route in the complete investigator. Preserve the old default/replay behavior and historical contracts. Verify the actual new stage's outputs rather than accepting a standalone helper's success. Offline integration uses explicitly retained or synthetic provider responses, recorded as such; do not silently invoke a live provider or label a replay as fresh source evidence.

4. Compute decision sets across every retained branch and declared semantic setting; include unknown, conflict, unsupported and unfinished outcomes. Do not report unanimity from an empty or partial set.

5. Carry uncertainty into the operative field, detailed report and summary. Keep legal correctness and unrestricted future generalization NOT_ESTABLISHED unless an exactly scoped independent result supports something stronger.

6. Execute the existing qualification route on compatible models and actual selected runtime targets. A target not installed or not supporting a branch produces a qualified target result; never substitute a Python-only replay for claimed Java/Catala execution. This permits dependent development but leaves that target's acceptance obligation pending. At least one actual supported downstream target must execute before P6 can claim its execution capability complete.

## Files and validation commands

Proposed semantics/lower.py, render.py and integration.py; narrowly scoped changes to complete_investigation.py and versioned adapters; no new autonomous provider scheduler.

The following test files are planned deliverables, not existing executed tests.
After implementing them, run these exact forms from the repository root:

```text
.venv/bin/python -m pytest tests/interpretation/semantics/test_lowering.py -q
.venv/bin/python -m pytest tests/interpretation/semantics/test_rendering.py -q
.venv/bin/python -m pytest tests/interpretation/semantics/test_integration.py -q
```

Add the relevant existing regression paths discovered from actual touched imports.
Record those exact paths in the phase revision before executing; do not invent a
successful regression result or invoke a broad suite unrelated to the change.

## Discriminating challenges

Summary drops footnote uncertainty; branch fails lowering and disappears; all branches out of scope; explanation condition differs from code; shared source error passes two compilers; claimed stage was never called.

## Acceptance and failure decisions

The actual complete-investigator route preserves all declared branch outcomes, source/evidence identity and qualifications. Supported compiled executions match the independent declared-semantics reference. Unsupported targets/branches remain in the denominator.

A lowering counterexample blocks that target and triggers repair. A complete investigator bypassing the new route is an implementation failure. Agreement between targets never closes the source-fidelity gap.

## Result and next-phase refresh

P7 receives actual integrated outputs, the exact supported domain, rejected constructs, runtime identities, counterexamples and the formal propositions worth proving. Remove proof ambitions that the implementation does not express.

Save the executed plan version, input/output hashes, commands, results,
uncertainties, decision and refreshed successor plan under the immutable attempt
directory specified by the master. A planned test command is not run evidence.

Resource boundary: Local CPU/runtime checks; deliberately hide GPU before any optional ML import. Provider dispatch remains separate and requires valid explicit allowance.
