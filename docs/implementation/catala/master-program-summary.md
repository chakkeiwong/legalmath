# Catala campaign: final summary for the master program

28 September 2026. Implementation checkpoint: `d01635dd` on
`feature/catala-adapter`. Status: **COMPLETE for the authorized bounded
engineering campaign**. The work is ready for the user-authorized main merge.

The project now has one source interpretation frontend and a typed shared model,
followed by deterministic translators and executable target languages. RuleIR
and Catala consume the same retained reading and explicit evidence policy.
Catala can execute richer shared programs directly. The original RuleIR backend,
serialized version-1 models and existing release authority remain compatible.

## Delivered work

| Stage | Result | Evidence |
| --- | --- | --- |
| Generic RuleIR-to-Catala backend | Current scalar operators, full Java result/trace contract, optional transaction/release backend | [Remediation results](gap-remediation-results.md): 344 decision comparisons, eight event cases, 202 regression tests |
| Direct native conversion | Typed native interfaces, exact I/O and interpreter verification | [Native converter results](native-converter/results.md) |
| Native semantic and host extensions | Options, payload variants, pinned libraries, executed source-position traces and verified portable packages | [Gap-closure results](gap-closure/results.md) |
| Shared frontend and deterministic lowering | One frozen interpretation with explicit target capability reports; rich expressions bypass RuleIR | [Modular translation results](modular-translation/results.md): 44 paired cases and seven rich outputs |
| Shared model version 2 | Rich scopes, strict exceptions, exact scale, explicit rounding, typed libraries, pure helpers, multiple outputs and nested partial observations | [Completion results](translator-completion/results.md), [interface guide](translator-completion/README.md) and [review](translator-completion/review.md) |

In version 2 the compiler computes arithmetic, selection and state propagation;
Python validates observations and decodes results. Multiple active exceptions
conflict even when their consequences are equal. Scaling integer or monetary
minor units must divide exactly; rounding is a separate declared operation.
Partially observed records, lists, options and variants retain uncertainty and
field/item evidence. Known optional absence and missing evidence remain distinct.

The optional `partial.v1` policy follows evaluated dependencies. It differs from
RuleIR's static whole-fact conflict veto and is explicitly unsupported by that
target. Comparing the two policies as if they were the same would be wrong.

## Final validation accounting

The [validation manifest](translator-completion/validation.json) binds commands,
source hashes, logs, test identities and compiled records. The full trusted
regression passed **792 tests in 966.75 seconds**. Final compatibility repairs
passed **69 translation tests in 209.22 seconds**. Corrected fixture metadata
then passed **35 affected tests in 129.00 seconds**. These checkpoints cover
**794 distinct test IDs**, with no skipped tests. They are not one full-suite run
against the final source checkpoint.

Four sealed version-2 builds preserve **91 exact checks** against handwritten
references, instrumented Java, plain Java and the original Catala interpreter.
Frozen version-1 replay passed **44 paired cases and seven rich outputs**, and
verified **nine existing builds** without regenerating their commitments.
Evidence is retained under `artifacts/catala/translator-completion/`; its final
source hashes match the implementation checkpoint. Pinned Catala 1.2.1 and JDK
17 were sufficient. The completion stage used no live model calls or new tools.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Complete the implementation campaign | Planned feature families execute with exact references and preserved legacy commitments | No unresolved value/status/provenance or compatibility failure in retained checks | Finite coverage and resource bounds | Merge the reviewed work and maintain its regression checks | Complete Catala language coverage |
| Retain both targets | Common-model cases agree; richer Catala features have explicit RuleIR capability failures | Different evidence policies are never represented as equivalent | Broader workloads and nesting combinations | Select a target and policy explicitly | Universal Catala superiority |
| Keep quality and deployment questions open | Engineering evidence is available; source/human study requirements remain distinct | No legal or human evidence sufficient for promotion | Independent adjudication and representative heldout sources | Plan those studies separately when required | Legal correctness, human benefit or production readiness |

Remaining implementation bounds are the closed operation/library vocabulary,
acyclic helpers and types, generated type/depth/source budgets and bounded
collection/runtime resources. The compatibility API evaluates the sealed program
once per returned output; batching remains a possible optimization. Prior live
conversion studies were small and conditional; the shared-frontend completion
does not provide a new statistical ranking of conversion quality.

The strongest alternative explanation for passing checks is incomplete coverage
of nesting and resource interactions. An independent counterexample to declared
semantics or provenance requires repair. Compiler success and test counts alone
do not establish source fidelity or a better default backend.

The [current reset memo](reset-memo.md) and
[integration plan](../../plans/catala-main-integration.md) provide the handoff.
Historical run manifests and pilot reports retain their original scope and are
not rewritten to claim validation of later implementations.
