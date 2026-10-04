# Required Java backend

Java is the bank deployment target. Python is an authoring/reference implementation.
This addendum is a required W03J/W04 contract, not an optional language adapter.
The proposal explains the same design and its running case in the manuscript.

## Delivered subset and required product

`examples/java-dry-run` implements SPI-Demo1: ten Boolean rules, 32 source-derived
synthetic decision cases, eleven consent histories, exact integers, known/unknown/
conflict facts, scope and source-linked rule traces. It generates real Java,
builds a dependency-free Java 17 JAR and executes a separately compiled host.
Its `DEMONSTRATION_ONLY` authority is immutable output, not a configurable approval.

The full product must implement every accepted RuleIR 0.1 operator and the complete
EvaluationResult/node-trace contract. The demo does not supply full defaults,
date operations, obligations, reviewers, release authority or private bank mapping.
Do not claim the 35 general-language cases have run merely because SPI-Demo1 passes.

## Compiler and library

`compile_java(bundle, target_release=17) -> JavaSourceTree`:

1. Validate structure, identifiers, references, types, cycles, source links and
   operator support. Reject unknown operators; no automatic engine fallback.
2. Emit immutable fact declarations and stable rule/node/source identifiers.
   Generate internal method names from validated identifiers. Treat all source
   prose/labels as escaped data, never executable Java fragments.
3. Emit one method per rule. Preserve scope status, reference memoization, full
   static conflict closure, evaluation order and skipped branch trace roots.
4. Bind the bundle hash and backend/version identifier into the generated class.
5. Return exact UTF-8 source bytes and a manifest; the compiler does not approve
   legal interpretation or select an effective release.

Mappings:

| IR | Java implementation requirement |
| --- | --- |
| bool/integer/money/date literal | Boolean, BigInteger, BigInteger HK cents, validated LocalDate with year 1–9999; no floating-point conversion |
| fact | Immutable tagged fact with evidence/validity/recording time; unknown and conflict never cast to false |
| rule | Memoized reference to an unconditional definition; shared traces emitted once |
| all/any/not | Eager ordered evaluation using specified T/F/U tables; runtime error precedes conflict, then logical value |
| compare | Exact same-type ordering; BigInteger.compareTo or LocalDate comparison; no Boolean comparison/casts |
| add/sub | BigInteger operations with retained integer/money type |
| scale | Multiply by numerator and divideAndRemainder by positive denominator; nonzero remainder -> E_INEXACT_SCALE |
| if | Evaluate condition, choose one branch, trace skipped root; unknown condition returns unknown without evaluating either branch |
| default | Evaluate all guards; multiple true -> conflict; otherwise any unknown -> unknown; sole true selects exception, all false selects base; explicit nesting only |
| scope | False -> OUT_OF_SCOPE; unknown -> UNKNOWN/SCOPE_UNKNOWN; otherwise body |
| errors/trace/hashes | Exact result schema, deterministic code/pointer/message, full source/node/evidence trace and canonical_v1 identity |

Proposed full Java API:

```java
public interface CompiledRuleSet {
    String bundleHash();
    String backendVersion();
    EvaluationResult evaluate(FactSnapshot facts, RuleId rule,
                              AssessmentContext context);
}
// AssessmentContext: validAt, knownAt, draft/production/replay mode.
// The release service/host checks authority; passing a mode is not approval.
```

Generate immutable, typed records from the declarations for the bank adapter where
practical; keep a strict schema-validation boundary for any JSON/Map transport.
The runtime must work without Python, LLMs, solvers, source fetching or MCP calls.
Event projection is a separately versioned Java component with the same pure
replay semantics and a reference comparator. A completeness watermark cannot
cover a time later than the recording instant of its assertion. It supplies decision facts and duty
assessments; real observations are not removed because advice would prohibit them.

## Release and integration

`build_java(tree, toolchain) -> JavaBuildManifest` records: schema/profile/IR
versions; bundle and source digests; generated-source and runtime-source digests;
backend/compiler/runtime identity; Java target; dependency versions/licenses;
JAR digest and build command. It contains no report or approval hash. A later
VerificationReport names this build manifest and exact JAR. A JavaReleaseManifest
then names both build and report, effective interval and applicability references.
Release approval binds the bundle and that final manifest. These external records
must not form a hash cycle or be embedded in the JAR whose digest they contain.
Candidate building precedes approval; controlled export follows approval.
An independently checked signature authenticates the authority in bank deployment;
hashes alone identify bytes. The build must compile with the declared `--release`.

Do not put wall-clock build durations or volatile request IDs into semantic
result hashes. Explicit assessment times remain in the canonical request. Build
in a clean directory with fixed archive-entry timestamps. Recompile in a separate
directory and compare emitted source and binary hashes under the same toolchain.
Record any reproducibility exception rather than reporting a pass.

The bank adapter resolves legal subject/category identities, evidence, currency,
calendar/valuation policies and imported assessments. It accepts the active release
only after digest/authority/effective-time validation. It maps all errors, unknowns,
conflicts and unsupported profiles to explicit host dispositions. Only TRUE for
this narrow condition allows the host to proceed to its other controls.

Read consent generation, positions and reservations at consistent versions;
evaluate exposure including the proposed order; atomically validate versions and
reserve exposure with the decision record. On concurrent change, reread and
reevaluate under a bounded retry policy. A repeated order ID/payload is idempotent;
a different payload under the same ID conflicts. Persist actual observations even
if the control would have rejected them. Retain historical JARs and snapshots.
Rollback may repair implementation of a current rule; it cannot revive superseded
law merely by restoring old software.

## Acceptance evidence

Run all 35 full-language cases in both backends plus the SPI source cases. Compare
complete semantic results, including source traces and missing/blocking inputs,
not just final Boolean values. Use actual backend-specific `engine_version`
identities. Compare all response fields except that identity and `result_hash`,
then independently recompute each execution hash under its own identity, as
specified in `contracts.md`. Equal meanings need not produce equal execution
hashes across different engines. Exercise malformed inputs, operator rejection,
time boundaries, scale exactness, dates, hash determinism and errors. Mutation
detection must change an expected outcome or required trace property. Compile a
caller separately against the exact tested JAR, and test host version races,
idempotency, stale release and replay using a synthetic adapter.

Finite conformance testing is engineering evidence, not a compiler-correctness
theorem or legal-fidelity result. A KeY/Lean proof may later establish a named
property of this backend with explicit domain/clock assumptions; it must bind to
the actual semantics and code version, not merely to a structurally similar model.
