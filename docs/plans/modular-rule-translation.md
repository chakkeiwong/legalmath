# Shared interpretation and replaceable rule targets

27 September 2026. Baseline: `4020f999` on `feature/catala-adapter`.
User authorization: plan, thoroughly review and execute the modular front-end,
translation and target-language refactor. Preserve main's unrelated work and
all frozen earlier evidence.

## Question and evidence contract

Engineering question: can one committed interpretation be translated to RuleIR
and Catala without a second legal reading or a target-selected evidence policy?
The baseline is the existing search formalizer and RuleIR Python/Java semantics,
plus the already tested RuleIR-to-Catala backend. Native-only constructs have
separate exact references; unsupported RuleIR constructs are not scored as errors.

Pass criteria: existing search formalizations retain their exact RuleIR bundles;
both targets bind the same model/interpretation/uncertainty and policy hashes;
translators make zero provider calls; shared cases preserve status and exact value;
rich constructs execute in native Catala and receive explicit unsupported reports
from RuleIR. Unknown/conflict/stale inputs, ambiguous interpretations, source
dependencies, altered commitments, exception ties and lazy errors must be tested.
Compiler success and case counts are explanatory only. Meaning/status changes,
target-specific reinterpretation, dropped uncertainty or approval bypass veto the
implementation and trigger repair. Missing pinned tools or invalid reference
artifacts stop the affected execution. Candidate failures do not reject modularity.

This is a deterministic engineering refactor, not another stochastic comparison.
No live model calls, new dependency installation, legal adjudication, production
activation, default backend change or superiority claim is needed. Recorded and
fixture provider responses test orchestration; they are not conversion-quality
evidence. A later paired conversion study must freeze a common interpretation
before selecting either target.

## Architecture and execution

1. Introduce a versioned typed `LegalRuleModel` between interpretation and target
   generation. It retains source spans, selected reading, assumptions, questions,
   coverage, validity and an explicit evidence/semantic profile. Its operators
   include the full current RuleIR fragment and a bounded richer fragment with
   records, lists, collection operations, exact decimals and optional/payload
   values. No raw target-language program belongs in this model. Validate types,
   references, depth, size and source commitments before translation.
2. Extract the existing formal-expression parsing and bundle construction behind
   adapters to the common model. Existing search/assurance callers continue to
   use `formal.bundle`, which delegates to the RuleIR translator. Preserve their
   serialized bundles and hashes. Existing RuleIR bundles can enter the common
   interface without losing any rules or semantics.
3. Add deterministic target translators and capability reports. The RuleIR target
   handles its actual supported fragment. Catala reuses the verified compatibility
   lowering for that fragment, and directly emits native code for supported rich
   models. Reusing a compiler pass must not make RuleIR a required representation
   of rich models. Unsupported constructs/policy combinations report exact reasons;
   no target silently invents a new interpretation or coerces types.
4. Add one target-independent generation/review workflow using the existing source
   packet, interpretation dimensions, coverage and uncertainty discipline. Freeze
   all proposed readings; selecting one is explicit, and unresolved questions
   block executable promotion for both targets. Criticism examines the common
   interpretation, not a target-specific code response. Retain bounded provider
   dispatches/responses and interruption-safe resume. Reuse completed front-end
   work when selecting another target.
5. Wire a public modular CLI/API for interpret, translate, build and draft execute.
   Route native CLI generation through the shared workflow. Preserve historical
   free-form native generation only as an explicit legacy compatibility path;
   handwritten native build/replay remains available. Bind model/translation and
   underlying build hashes. Draft execution does not grant release authority.
6. Share policy selection and normalized semantic results above execution. Imported
   RuleIR uses its existing partial-information semantics. Rich native models
   explicitly choose complete-input semantics; the same policy is applied if
   their scalar subset is sent to RuleIR. This is a model contract, never inferred
   from the chosen target. Existing authenticated release hosts continue to require
   their approvals; the new workflow cannot self-approve or activate a release.
7. Execute exact paired tests, a retained-source replay through one frozen model
   per task, richer native feature probes, CLI/resume/uncertainty/tamper tests and
   relevant existing regressions. Write the capability table, run manifests,
   result/decision note and reset memo. Commit the isolated branch checkpoint.

## Defaults, limits and pre-mortem

| Choice | Provenance/status | Failure mode | Early diagnostic |
| --- | --- | --- | --- |
| Existing scalar semantics | Preserved RuleIR baseline | Redefining unknown/conflict or rounding | Compare shared status/value and legacy bundle bytes |
| Catala compatibility lowering | Existing verified compiler pass | Pretending native-only support uses that restricted pass | A rich collection model must execute without conversion to RuleIR |
| Explicit complete-input rich profile | Existing native policy, optional | Target changes the evidence decision | Same scalar model and missing-input snapshot sent to both targets |
| Bounded richer model | Task-scoped implementation | New representation becomes an undocumented bottleneck | Capability reports and direct list/option probes |
| Shared generation schema | Existing interpretation metadata, extended types | Model emits raw target code or drops rival questions | Strict parsing, explicit selection and unresolved-source veto |
| No live calls | Engineering evidence only | Fixture success called model improvement | No conversion-quality or statistical ranking in result note |
| Pinned Python/JDK/Catala | Existing environment | Wrong executable or rewritten compiler lock | Small compile/import probes; preserve toolchain hashes |

Use the existing `/home/chakwong/python/legalmath/.venv/bin/python` with
`PYTHONPATH=src:.`, JDK 17 and the pinned Catala toolchain. Compiles/executions
retain existing time/memory limits. Focused tests precede regression. Runs longer
than five minutes are bounded and logged under
`artifacts/catala/modular-translation/`; results under
`docs/implementation/catala/modular-translation/`.

A misleading pass could compare independently generated readings, erase questions
when a reading is selected, use a Python evaluator to supply Catala answers,
silently restrict every target to RuleIR, or count a compile as source fidelity.
Tests must make those shortcuts visible. Existing release approvals must never
be transferred merely because two translations share a model hash.

## Skeptical plan audit before implementation

Root Codex review (not an independent reviewer): initial design REVISE. Merely
sharing the source packet repeats the previous confound. Putting current RuleIR
at the common boundary prevents richer native constructs. Replacing every
runtime with the native complete-input adapter regresses existing partial-input
behavior. A generic new evaluator would introduce an unnecessary third execution
oracle. The revised design instead uses a typed shared model, deterministic
lowering, the existing verified scalar backend, explicit optional rich semantics,
and independent hand references for rich probes.

Audit PASS for the revised implementation. The comparator is the actual existing
formalizer/runtime, not prior model pass rates. Case success is engineering
evidence only. Stop/repair rules, source/provenance commitments, legacy schemas,
environment and the distinction between interpretation review and release
approval are explicit. A bounded initial rich capability set is acceptable only
if unsupported cases are reported and no existing native build/replay is removed.

## Execution and final audit

Implemented the shared typed model, legacy formalizer adapter, deterministic
RuleIR/native translators, common generation/criticism, explicit evidence policy,
CLI integration, and build/result commitments. The target translators have no
provider dependency. No live calls or production operations were needed.

Targeted checks passed on the compiled engines: 44 retained-source cases per
target, seven richer native outputs with original-interpreter and plain-Java
comparators, 16 byte-identical legacy bundle checks, and focused tests for
uncertainty, resume, evidence, policies, malformed inputs and altered commitments.
The full regression was interrupted at the first API TestClient check after 494
passing progress records. That exact test passed in 0.81 seconds in the trusted
environment. All 266 remaining tests passed there with a 600-second bound and
60-second stack diagnostics. Combined coverage accounts for all 759 collected
tests. This changed the execution environment, not the test oracle.

Final audit repaired the result wrapper/inner-trace binding and deterministic
evidence alias verification. A synthetic rich fixture initially inherited source
wording from the scalar example; it was replaced with a coherent synthetic source
and factual meanings. Its earlier bytes are inventoried under
`artifacts/catala/modular-translation/superseded-probe.json`; the replacement was
compiled and checked again. These repairs preserve the main question and do not
turn development fixtures into legal or model-quality evidence.

The accepted report and complete regression accounting are under
`docs/implementation/catala/modular-translation/`. Remaining feature limitations
are in its README and capability reports. No claim of universal target superiority
follows from these deterministic checks.
