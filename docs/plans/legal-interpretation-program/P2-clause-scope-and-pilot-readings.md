# P2: Make the disputed duties explicit

Status: PLANNED_NOT_EXECUTED. The [master program](../legal-interpretation-master-program.md)
controls evidence, default assumptions, resource limits and source-fidelity claims.
Dependencies: P1.

## Question and inputs

Which different executable consequences follow from the retained paragraph-10 and paragraph-14/footnote-5 readings?

P1 records; full frozen source units and their referenced definitions/footnotes; P0 operative corrections. Read complete relevant clauses and dependencies rather than selected snippets alone.

## Implementation

1. Implement semantics/clauses.py to express actors, activities, objects, quantifiers, modality, conditions, exceptions and cross-reference attachment. Treat a source extraction as a proposed interpretation with warrants and objections. Implement a proposed `clauses.propose(packet, question, retained_proposals, policy)` interface that consumes actual retained investigator proposals and source relations; record unrepresented concerns rather than relying only on hand-entered settled examples. Fresh model generation, if later justified, remains separately budgeted and supplies proposals only.

2. Decompose paragraph 10 into responsibility allocation, supervisory conduct and operational adequacy. Construct the retained rival readings and any newly exposed unsupported combination without assuming the decomposition exhausts the law.

3. Separate paragraph 14's confirmation and demonstration from paragraph 15's third-party verification and paragraph 16's legal opinion. Preserve the competing placements of request conditions and footnote-5 implications. No document-order, typography or footnote default decides priority.

4. Create source-linked scope diagrams and controlled-English renderings of each branch. Mark constitutive classifications separately from duties; preserve SHOULD without importing a sanction or civil-liability rule.

5. Generate distinguishing assignments from the declared formal alternatives, including retained authority with failed operations and no regulator request. Record the differences as conditional consequences, not legal answer keys.

## Files and validation commands

Proposed semantics/clauses.py; pilot-reading specification and source-to-premise map in the phase output. Store all alternatives and unresolved source relations.

The following test files are planned deliverables, not existing executed tests.
After implementing them, run these exact forms from the repository root:

```text
.venv/bin/python -m pytest tests/interpretation/semantics/test_clauses.py -q
.venv/bin/python -m pytest tests/interpretation/semantics/test_pilot_readings.py -q
```

Add the relevant existing regression paths discovered from actual touched imports.
Record those exact paths in the phase revision before executing; do not invent a
successful regression result or invoke a broad suite unrelated to the change.

## Discriminating challenges

Condition attaches to the wrong duty; a footnote is ignored; responsibility is equated with good outcomes; SHOULD becomes MUST; a provider's act is attributed to an intermediary; every branch is out of scope.

## Acceptance and failure decisions

Each proposed duty has a recoverable actor/action/modality/scope representation, rivals remain separate, and at least one generated distinguishing input shows the meaningful differences or proves equality within an explicitly bounded formal domain.

If the schema cannot express a plausible reading, preserve it as unsupported and repair P1. If authority cannot choose between readings, keep both. A source quotation alone cannot mark a semantic relation proved.

## Result and next-phase refresh

P3 receives the branch inventory, supporting and opposing warrants, unrepresented concerns, and generated inputs distinguishing the branches. Revise its argument vocabulary to those actual disputes.

Save the executed plan version, input/output hashes, commands, results,
uncertainties, decision and refreshed successor plan under the immutable attempt
directory specified by the master. A planned test command is not run evidence.

Resource boundary: Offline development first. A future proposal generator may nominate readings only under a separately recorded provider route; it cannot supply acceptance labels.
