# P0: Bind the baseline and repair contradictory operative wording

Status: PLANNED_NOT_EXECUTED. The [master program](../legal-interpretation-master-program.md)
controls evidence, default assumptions, resource limits and source-fidelity claims.
Dependencies: documentation and review package.

## Question and inputs

Which current statements are demonstrably stale, and which remain legally unresolved?

Read the product gap audit, current-post-review-repairs.json, selected dispositions.json, original obligation map, active code revision and existing grant records. Recompute identities; do not assume the saved pointer or counts remain current.

## Implementation

1. Freeze the exact selected packet, questions, 35 reading identities, both role records and all 46 original obligations. Preserve the source inventory, acquired editions, code hashes and all failed attempts. If counts differ, reconcile the difference before using a denominator.

2. Build an immutable candidate overlay for the identified operative fields. Replace acquired-source-unavailable assertions with the actual availability/applicability distinction. Express the paragraph-14/footnote-5 uncertainty in the relevant reading field itself, not only in a global disclaimer.

3. Preserve original text, field path, reason, supporting acquisition/source record and predecessor hash for every edit. Do not change formulas, declare an issue answered or consume provider budget to make these textual corrections.

4. Implement a small deterministic operative overlay helper, preferably reusing the existing post-review repair mechanism through a new revision. Map every current gap to its original obligation IDs before adding derived tasks.

## Files and validation commands

Candidate overlay and baseline manifest under the future run's P0 directory; proposed semantics/operative.py only if existing repair code cannot represent the scoped overlay. Do not overwrite the historical post-review package.

The following test files are planned deliverables, not existing executed tests.
After implementing them, run these exact forms from the repository root:

```text
.venv/bin/python -m pytest tests/interpretation/semantics/test_operative.py -q
```

Add the relevant existing regression paths discovered from actual touched imports.
Record those exact paths in the phase revision before executing; do not invent a
successful regression result or invoke a broad suite unrelated to the change.

## Discriminating challenges

The acquired source is present but applicability is unknown; an unavailable authority really is missing; a reading claims request-trigger-only while a linked footnote remains unresolved; the active pointer changes after freezing.

## Acceptance and failure decisions

Each targeted operative field has the scoped correction, originals and all obligations survive, changed-source detection works, and no substantive closure or formula change is fabricated. Inventory arithmetic must distinguish role records, readings and obligations.

An identity mismatch is a continuation veto until reconciled. An uncertain legal meaning is a qualified result. A missed operative field triggers a causal overlay repair, not another general disclaimer.

## Result and next-phase refresh

P1 receives the exact source/question identities, corrected candidate fields, unresolved premises and a reconciled gap map. Record which texts are acquired versus applicable versus missing.

Save the executed plan version, input/output hashes, commands, results,
uncertainties, decision and refreshed successor plan under the immutable attempt
directory specified by the master. A planned test command is not run evidence.

Resource boundary: Offline; no provider calls. Stop on any attempt to modify historical evidence or grant counters.
