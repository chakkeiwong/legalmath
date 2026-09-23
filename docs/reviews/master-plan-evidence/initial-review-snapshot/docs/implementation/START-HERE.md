# Implement LegalMath with Java delivery

This is the entry point for an implementing agent. The proposal explains the
product and research; this directory and `docs/specs/v0.1` define the prototype.
The v0.1 and v0.2 proposals are preserved under `.localresources/`. The user
rejected both. Version 0.3 adds a language lesson, a complete selected circular
profile and actual Java generation/execution. Human acceptance remains pending.

## First action

Start with the [master implementation plan](master-plan.md), its
[task graph](master-plan.tasks.json) and the [audit](../reviews/master-plan-review.md).
Begin T00 contract closure, then T01–T03 foundations and source import. No full
application implementation is claimed by the existing demonstration.

For the explanatory background, read the language lesson, complete 23EC35 dry run and Java delivery chapters
in the [proposal](../proposal/proposal.pdf). Rebuild the
[Java example](../../examples/java-dry-run/README.md) and inspect its limits.
Then read the [required Java contract](../specs/v0.1/java-backend.md) and, in order:

1. [Semantics](../specs/v0.1/semantics.md): the normative language and evaluation rules.
2. [Contracts](../specs/v0.1/contracts.md): source, storage, lifecycle and API contracts.
3. [Work packages](work-packages.md): implement W00, then follow dependencies.
4. [Decisions](decisions.md): settled choices and reasons.
5. [Decision cases](../specs/v0.1/fixtures/decision-cases.json): 35 complete inputs
   with exact expected result projections; the same directory contains negative,
   event and release examples.

Run the specification check before creating application code:

```bash
python3 scripts/check_spec_pack.py
```

This checks the supplied contract material. It does not mean that the application,
SFC translator or proof adapters have already been implemented. Commands in the
work packages are future acceptance commands unless recorded in
[the proposal validation record](../proposal/validation.json).

## Deliver the first vertical slice

Implement source import, validation and deterministic evaluation of
`spi.financial`, using the supplied source extract and synthetic input cases.
The command must return a named financial subcondition, its trace and the exact
source references. It must never label that result a complete SPI qualification,
suitability decision or trade authorization. Complete W00--W03 before adding an
LLM, a web interface or a general workflow engine. Then complete W03J, the
mandatory Java backend, before producing a production-shaped release package.
The supplied SPI-Demo1 emitter is a working subset, not complete RuleIR support.

Use Python 3.11 for authoring/reference evaluation, Java 17 for the required
library, and the SQLite driver and dependencies fixed in W00. Public-source, local-only operation is the first target. Keep all adjacent
repositories read-only. Do not import their whole environments or copy their code
without resolving the stated licensing and interface conditions.

## Completion and release are different

Engineering completion means the documented tests, replay and rejection behavior
work. The supplied cases are design/conformance examples, not a bank-approved
legal oracle. A release to bank use additionally needs the entity/activity scope,
definitions, data mappings and interpretations approved by the designated owners.
Store those decisions as review records; do not fabricate them to make a test pass.

No production bank connection, client-data ingestion, autonomous regulatory
publication or automatic policy deployment is in this implementation scope.
