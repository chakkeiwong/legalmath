# Operating the processing continuation

This increment implements the [reviewed C0–C7 plan](../../plans/assurance-continuation-execution.md).
The [controlling product requirement](../proof-qualified-generalization/product.md)
requires machine-checked propositions or explicit qualifications. A passing
execution receipt does not establish English legal correctness. The original
S8 failure, its source freeze, all four tasks and all consumed calls remain
historical evidence.

## Inspect the retained execution

The authorized live continuation has finished at 500/500 reservations. C0–C5
passed against their recorded snapshot; both C6 receipts remain failed, and C7
has no executed receipt. Use the separate [execution result](execution-result.md)
and [final-assessment repair record](assessment-isolation-repair.md). The final
regression runs on an archived isolated snapshot because another product is
being developed concurrently. Its results apply to that exact version.

Do not run the old master again to bypass completed phase-attempt limits or its
failed predecessor. The [next phase plan](next-phase-plan.md) preserves the actual
unfinished work and original issue histories. The command below inspects the
executed program; `status` is read-only.

From the repository root, using the existing application environment:

```sh
.venv/bin/python scripts/run_assurance_continuation.py status
```

The runner accepts `phase C0` through `phase C7`. It verifies current predecessor
receipts before executing a phase. C6 uses the configured Codex provider and
requires network access; its reviewed wrapper has a narrowly approved command
prefix. The local model grant remains the original 500-reservation grant. The
continuation has no code path that replenishes it.

The root is `artifacts/assurance-continuation/2026-09-29/`. Inspect
`state.json`, `next-phase-plan.json` and each phase's `attempt-XX/manifest.json`.
A manifest binds the source hashes, base commit, interpreter, exact commands,
CPU-only setting, elapsed time, outputs and retry evidence. `PASSED` means that
the phase's stated engineering checks executed. Read its `result` before making
a broader claim. In the original plan, C6 could pass its accounting checks while
reporting missing perspectives, disputed judgments or a resource stop.

`engineering_execution_complete` requires all eight current phase receipts.
`historical_study_complete` and natural-language correctness remain separate.
Do not rename the historical failure, count a partial circular as a completed
investigation, or treat an unassessed dimension as an agreement.

The application environment supplies `pypdf` and the existing HTML extractor.
Document work uses the separately recorded PyMuPDF environment and the existing
XeLaTeX builder. Set `LEGALMATH_DOC_PY` only to a document interpreter with
PyMuPDF installed; otherwise the runner probes the resolved `python3`.

## Recovery without resetting history

A failed phase retains its manifest and refreshes the next action. Before a
retry, record an actual implementation change and execute its focused
reproducer. `docs/implementation/assurance-continuation/C5-repair-1.json` is an
executed example: it names the exact predecessor receipt, the change, actual
commands and a hash-bound passing result. A description of an intended test is
insufficient. The first C5 failure and its dependency repair are explained in
[environment-repair.md](environment-repair.md).

If an intact successful phase predates a source edit, the runner records
`SOURCE_REVALIDATION` and reruns its checks. It preserves the old successful
receipt instead of fabricating a failure. Failed, missing or corrupted output
requires investigation; it cannot use the revalidation exemption. Both kinds
of retry consume the original maximum of three phase attempts.

Do not delete a directory, change a partition or change a schema to obtain fresh
issue limits. Scoped live continuation uses `ResumingCodex` to reconstruct
reservations and the oldest issue deadline from the retained provider evidence.
The grant, task arm, pair/perspective, deadline and local action limits all
apply. An exhausted limit produces a qualified incomplete result.

## Source references and complete context

`legalmath.interpretation.assurance.source_references` implements
`legalmath.source-spans.v1`. The model receives the complete unchanged packet
plus a closed table of full-unit and adjoining-span identifiers. It returns
`{"span_ids": ["span.…"]}` where the wire schema asks for source evidence.
It never supplies authoritative replacement text or computes offsets. The
resolver retrieves half-open Unicode-codepoint slices and applies the original
quotation contract, including uniqueness within the source unit.

Each table belongs to one packet and one request. Its receipt retains the
original request and schema, reference table, wire request and schema, raw model
response, resolved response and validation. This makes a location reproducible;
source support, question relation, executable correspondence and authority are
still assessed separately. Unsupported or unresolved labels survive resolution.
Executable-expression quotations are not source-span selections.

The existing complete investigation supports these opt-in settings:

```python
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
from legalmath.interpretation.assurance.source_references import PROTOCOL

investigation = CompleteInvestigation(
    root, directory, provider, jdk, assessment_time,
    settings=reviewed_settings, catala=locked_catala_toolchain,
    scoped_schedule="round-first", reference_protocol=PROTOCOL,
    machine_qualification=True,
)
dossier = investigation.run(roots, selected_slice, retained=retained_sources)
```

Here `roots` and `retained_sources` use the existing exact-byte source records;
`provider` must carry its existing authorization and issue history. This is an
API configuration example, not an authorization to construct a fresh grant.
The integrated test exercises the actual constructor and dossier verifier with
simulated model responses. The C6 run separately measures the real provider.

## Interpret, account for every unit, then reconcile

`single_reader.run` is the optional `legalmath.single-reader.coverage.v1`
protocol. It asks for one proposed reading and its declared questions, divides
the coverage table into bounded responses, and then performs a whole-source
consistency check. Every request still carries the full source. The deterministic
merge requires every source unit exactly once, retains cross-piece concerns and
binds every piece to the exact interpretation. A final response accounts for
every concern and question. A revised interpretation invalidates all earlier
coverage and must be rechecked.

Select `transport_profile="compact-locators.v2"` for the lossless locator
compaction used by the optional study entry point. Every original unit's text,
identifier and normative flag remains present; document locators are recorded
once rather than repeated. `output_identity_contract` provides the original
packet/interpretation/coverage hashes. The source-reference table's separate
packet hash belongs to the compact transport and cannot replace an output
identity. The actual 263-unit initial request now fits the 200,000-byte limit;
later reconciliation context must still pass the size check.
The executed actual-source synthetic diagnostic reached all 263 coverage units
and retained 263 concerns, then stopped at a 382,396-byte final consistency
request. Its result is `split-capacity/result.json`. This is an explicit current
capacity limitation, not a completed live authentication investigation.

For a live call, supply an explicit `IssueLimits` history bound to
`{"packet": digest(packet), "role": "single-reader"}`. Existing work must
first be imported with its spent attempts, oldest timestamps and evidence
identities; an empty new file is appropriate only for genuinely unattempted
issues. The continuation does not migrate the old authentication attempt into
a new live split run. Its 263-unit source is preserved and partitioned in C0,
and the split protocol is exercised by integrated deterministic challenges.
That is not evidence that the live 263-unit task has completed.

The output distinguishes accounted proposals from legal entailment. An
executable subquestion cannot discharge a different question with the same
Boolean output type. Even complete accounting of the declared questions does
not prove that the initial reader discovered every possible legal question.

## Arithmetic, domains and machine qualification

Addition accepts two or more operands subject to the existing expanded node
and depth limits. It preserves order and multiplicity by an explicit binary
fold. Binary expression bytes are unchanged; other operators keep their old
arity. Exact integer and tagged-missing addition have a separately recorded
Lean theorem. The proof does not cover legal applicability, conflict handling,
time selection or an arbitrary production compiler.

`qualification_adapter.run` binds a packet, reading, exact question, assignment,
method version and selected mathematical cases to the shared qualification
route. `qualification_adapter.verify` checks that binding and the underlying
machine evidence. Unencoded readings receive an `UNENCODED` qualification.
Formalized readings may have checked mathematical properties while source
dependencies still prevent translation. Supplying no runtime cases creates no
runtime evidence.

`comparison_domains.compare` requires a versioned domain naming every common
fact's type, unit, listed values and provenance. A mathematical probe set is
distinguished from a declared finite domain. A difference is replayed through
the original programs; matching values establish only the recorded comparison.
The system does not infer admissible financial values from desired answers or
silently regard quoted text as proof that a finite set is exhaustive.

The actual retained four-operand proposal is reproduced in C4. Its unresolved
premises remain in the product output. Separate hypothetical Java and Catala
execution tests that unchanged expression under explicit mathematical inputs.
The dropped-operand mutation must produce a separating witness.
