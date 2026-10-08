# P0–P6 root-cause and solution study — 6 October 2026

User request: commit the current checkpoint; trace P0–P6, survey existing
solutions, propose concrete repairs and establish what can be proved.

## Pre-execution skeptical audit

PASS for checkpoint preservation, code tracing and bounded deterministic probes.
Baseline is the unmodified successor executed at da2c7a4, then its checkpoint
commit recorded after creation. Preserve prior receipts and separate main.
Do not substitute passing tests or phase exit status for legal interpretation.
The generated run tree is 1.6 GB; inspect untracked sizes before committing.
Pack large generated files losslessly, keep originals available locally, and
verify exact restored bytes so evidence fits ordinary Git hosting.
Compression threshold is a storage convenience, not an evidentiary cutoff.

Research question: which failures arise from missing data/review versus
incorrect interfaces or semantics, and which repairs have a demonstrable
correctness argument under explicit assumptions?
Primary evidence: source-level control/data-flow trace, minimal reproducer,
and a reference specification with soundness properties.
The comparator is the current code for the same versioned question and input.
Engineering proofs cover explicitly formalized behavior; they cannot prove
that a disputed natural-language contract or authority was interpreted correctly.

Expected failures: disconnected phase outputs; globally blocked references;
template-specific string deletion; insufficient clause typing; unvalidated
time/fact/financial inputs; inventory checks mistaken for full integration.
Diagnostic roles: counterexamples veto the affected correctness claim and
trigger a repair proposal; counts/runtime are explanatory only; missing
independent labels veto release, not this investigation.
Continuation vetoes: wrong checkout/import, corrupted source, mislabeled
comparison, missing probe outputs. Repair these before interpretation.
No stochastic model training or ranking is proposed.

## Execution

1. Preserve/commit the previous manuscript, code and receipts, including a
   losslessly restorable archive for oversized generated records.
2. Trace controller -> jobs P0–P6 -> service -> source, assembly, clause, law,
   finance and bank modules; inspect actual current receipts and tests.
3. Run small adversarial checks against current behavior; record commands,
   current code hashes, outputs and each violated invariant.
4. Inspect retained technical literature plus focused official sources for
   uncovered needs (document structure, incremental builds, partial
   information, time, numerical conventions and independent evaluation).
   Use existing ResearchAssistant extraction when feasible; keep local copies,
   URLs, hashes and section anchors. Do not train/adopt models from abstracts.
5. Propose repairs as explicit algorithms/contracts. Prove their narrower
   properties mathematically and exercise finite reference models. Separate
   those proofs from independent legal/real-document validation still required.
6. Write the full diagnosis and reviewed implementation program under
   docs/implementation/prospectus-phase-roots-2026-10-06 and a concise response.
   Commit this requested investigation separately when complete.

Default/assumption audit: development fixtures are not independent legal labels;
a source hash proves identity only; a reason string is not authoritative
semantics; missing facts are not false; identical execution labels do not prove
same premises; dates require valid-time and knowledge-time distinctions.
Use CPU only and CUDA_VISIBLE_DEVICES=-1. Any literature retrieval is bounded
and recorded; do not consume a hidden API budget or call external models.

## Reference repair audit (before execution)

PASS for isolated, deterministic specifications; production remains unchanged.
Reuse prospectus.semantics.possible_decision rather than invent a second solver.
Compare finite completions with an independently coded truth-table oracle.
Test duplicate and multi-unit source occurrences, every partition of a short
sentence, unresolved/selected contract choices, time interval endpoints,
explicit false additional legal premises, exact holder allocations, dependency
mutations, context changes, and evaluation/signoff scope changes. These are
engineering regression criteria; no count or passing toy case establishes
real-prospectus accuracy. Document remaining unimplemented reference checks.

Assumptions: paragraph membership and choice identities are supplied correctly;
source intervals and question definitions are explicit; law predicates are
reviewed and finite; registered-holder identity is supplied by the applicable
contract; tasks are deterministic over all declared inputs, including code and
tool configuration. Missing or contradicted assumptions yield UNKNOWN, CONFLICT
or a structured rejection, never an invented fact. SHA-256 identity relies on
collision resistance. Snapshot consistency requires immutable bytes, not merely
a start/end timestamp. No adoption of Docling or QuantLib defaults is authorized
by a literature example. Their inspected code is a design/comparator source.

The reference checks will save reference-results.json and reference-manifest.json
in the investigation folder, including source hashes, runtime and exact command.
The finite domains are debugging/exhaustive small-model checks, not sampling or
statistical evidence. Mathematical proofs must state their assumptions and may
establish only algorithmic invariants, never completeness of the legal premises.
