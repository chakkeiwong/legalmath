# P1: Represent source meaning and evidence without losing uncertainty

Status: PLANNED_NOT_EXECUTED. The [master program](../legal-interpretation-master-program.md)
controls evidence, default assumptions, resource limits and source-fidelity claims.
Dependencies: P0.

## Question and inputs

Can one record preserve quotation identity, proposed meaning, applicability, factual support and formal consequences without conflating them?

P0's frozen baseline and gap map; existing Packet/Proposal/Reading contracts, source_references.py and translation model types. Treat old evidence as historical input, not already validated new records.

## Implementation

1. Define versioned immutable records in semantics/records.py for source editions, scoped propositions, clause relations, readings, evidence support, assumptions and unresolved dependencies. Use strict validation and canonical identity rather than free-form JSON dictionaries.

2. Bind each quotation to the existing request-bound Unicode span contract. Retain role and speaker separately: allegation, party submission, finding, reasoning, majority, concurrence, dissent or unknown. Do not infer a role merely from document membership.

3. Keep positive and negative support independent; retain missing and conflicting support through serialization. Separate fact support, argument status, applicability and branch execution status. Explicitly prohibit implicit truth conversion.

4. Represent partial intervals and the distinction among publication, effective, event and knowledge dates. Unknown bounds remain unknown; no fallback year or silently completed date.

5. Write lossless adapters for legacy Packet/Reading records. Unavailable new fields become unresolved, never backfilled as established. Validate namespace/import direction before integrating with translation.

## Files and validation commands

Proposed semantics/records.py and versioned schema resources; adapters at the interpretation boundary. Existing strict contracts retain their old behavior.

The following test files are planned deliverables, not existing executed tests.
After implementing them, run these exact forms from the repository root:

```text
.venv/bin/python -m pytest tests/interpretation/semantics/test_records.py -q
.venv/bin/python -m pytest tests/interpretation/semantics/test_legacy_adapter.py -q
```

Add the relevant existing regression paths discovered from actual touched imports.
Record those exact paths in the phase revision before executing; do not invent a
successful regression result or invoke a broad suite unrelated to the change.

## Discriminating challenges

A verified quote supports a disputed proposition; dissent is mistaken for majority; absent data is cast to false; two records conflict; a partial date crosses an applicability boundary; a old record lacks actor identity.

## Acceptance and failure decisions

All five evidence axes remain distinct after serialization and migration; invalid identities and unsupported coercions are rejected; legacy histories retain hashes and unresolved fields. An unknown value cannot become a settled decision through a default.

Schema rejection of valid partial evidence triggers a representational repair. A circular import or a lossy migration vetoes promotion of the adapter. Missing legal meaning does not block implementing the record structure.

## Result and next-phase refresh

P2 receives the exact grammar, record version, actor/time vocabulary, migration limitations and the smallest examples the representation cannot express.

Save the executed plan version, input/output hashes, commands, results,
uncertainties, decision and refreshed successor plan under the immutable attempt
directory specified by the master. A planned test command is not run evidence.

Resource boundary: Offline; proposed finite collection sizes inherit no legal significance. Set measured resource bounds before accepting untrusted records.
