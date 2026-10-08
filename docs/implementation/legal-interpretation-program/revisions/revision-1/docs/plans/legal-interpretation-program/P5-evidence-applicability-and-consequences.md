# P5: Derive scoped facts from evidence

Status: PLANNED_NOT_EXECUTED. The [master program](../legal-interpretation-master-program.md)
controls evidence, default assumptions, resource limits and source-fidelity claims.
Dependencies: P2, P3, P4.

## Question and inputs

Which observations justify a factual predicate, over which actor, activity and time, and which legal consequences remain unproved?

P1 support states and time model; P2 duty branches; P3 warrants; P4 precedent premises or explicit gaps. Existing event projections and retained record evidence are starting implementations, not general semantic guarantees.

## Implementation

1. Implement semantics/evidence.py to bind observations to entity, provider, component, activity, event time, knowledge time and validity interval. Distinguish raw records, derived observations and legally evaluative predicates.

2. For the pilot, derive only narrow predicates warranted by declared rules: a recorded appointment, a supervision event within an interval, a record discrepancy or an unresolved ownership assertion. Retained responsibility, adequacy and proper records remain separate evaluative claims unless a sufficient rule and evidence are stated.

3. Represent exceptions and evidence of absence with their required completeness premises. An absent incident record does not prove no incident. Preserve conflicting title assertions and competing record priority rules.

4. Cover commencement, replacement, termination, retention, backdated correction and migration across providers. Do not backfill an assessment date from publication.

5. Separate modality, duty satisfaction, breach, remediation and sanction/liability rules. A remediation event does not erase the historical incident; token possession does not itself establish legal or beneficial title.

## Files and validation commands

Proposed semantics/evidence.py; pilot evidence derivation graph, typed observations and actor/time bindings. Reuse existing event machinery through versioned adapters.

The following test files are planned deliverables, not existing executed tests.
After implementing them, run these exact forms from the repository root:

```text
.venv/bin/python -m pytest tests/interpretation/semantics/test_evidence.py -q
.venv/bin/python -m pytest tests/interpretation/semantics/test_applicability.py -q
```

Add the relevant existing regression paths discovered from actual touched imports.
Record those exact paths in the phase revision before executing; do not invent a
successful regression result or invoke a broad suite unrelated to the change.

## Discriminating challenges

Right event/wrong provider; event learned after cutoff; unknown effective date; conflicting title and token records; good operations without retained authority; incident followed by remediation; no observation mistaken for false.

## Acceptance and failure decisions

Every settled formal predicate has a reproducible derivation under explicit assumptions, and every missing/conflicting input preserves its status through actual serialization. No broader legal classification or consequence is inferred from a narrow observation alone.

A missing classifier warrant produces unresolved classification, not an invented threshold. A wrong identity/time join triggers code repair and invalidates dependent results. Missing private case facts do not stop interpreter development on declared inputs.

## Result and next-phase refresh

P6 receives exactly supported predicates, their evidence dependencies, unresolved evaluative standards and the supported temporal fragment. Narrow lowering to that fragment and preserve all unsupported alternatives.

Save the executed plan version, input/output hashes, commands, results,
uncertainties, decision and refreshed successor plan under the immutable attempt
directory specified by the master. A planned test command is not run evidence.

Resource boundary: Offline retained or synthetic declared evidence. No model training, personal-data acquisition or replacement of legal standards by numerical confidence.
