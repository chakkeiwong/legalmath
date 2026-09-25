# Catala backend remediation

## Question and synchronized baseline

Can generated Catala calculations implement the accepted RuleIR 0.1 operators
through the existing raw-snapshot Java, trace, transaction, and release APIs?
RuleIR stays the authored rule source. This is an optional backend, not a change
to the default engine or a claim that a finite test proves compiler correctness.

Committed main `9160ce72` was merged without conflict in `5c47153f`. Its changes
add interpretation-assurance workflows; they do not alter RuleIR, Java runtime,
or release semantics. The main worktree also contains active uncommitted work.
`docs/implementation/catala/main-sync.json` records those paths. They are not a
stable baseline and must not be imported or overwritten by this task.

## Scope and implementation decisions

The earlier pilot supported four exact bundle hashes, two handwritten examples,
projected results, and a typed draft-only host. Those are implementation limits,
not evidence that Catala is intrinsically inferior to RuleIR. A generator for
only those same examples would not close the requested gaps.

Generate one Catala calculation scope per expression from any validated RuleIR
0.1 bundle, with a source map back to rule, expression, and source span. Support
literal, fact, rule reference, all, any, not, compare, add, sub, exact scale, if,
and default; bool, arbitrary-precision integer, HKD minor units, and date types.
There is no whitelist of bundle identities. Unknown operators or invalid types
fail before compilation. Dates use an order-preserving epoch-day encoding at
the bridge; money stays in exact integer minor units. Status values are explicit.

The existing Java policy runtime will accept an optional calculation engine.
Catala computes literals, boolean and numeric operators, and branch selection.
Java retains raw JSON validation, fact admissibility/time rules, static conflict
checking, lazy traversal, rule memoization, provenance, and result hashing.
Trace nodes record the actual returned Catala values/statuses during traversal.
They are never populated from a Python/reference evaluation. The common Java
machinery is a correlated component, so this backend is not an independent
whole-engine checker. Metadata and malformed-input cases test the shared host.

Lower default selection explicitly: two true guards conflict even if their
consequences agree; error/conflict guards precede multiplicity; unknown guards
block a unique selection. Do not rely on native Catala exception coalescing to
implement RuleIR's different target. Preserve lazy branches and exact-scale
errors. An absent dispatch entry must fail, never fall back to the Java evaluator.

Compile an ordinary generated Java policy class with the same String and Map
APIs, a distinct engine identity, and the pinned Catala Java runtime included.
Build manifests bind generated sources, bridge, runtime, compiler, and JAR. Use
relative source names and deterministic JAR metadata. Compiler installation is
not required on the deployment host. Expose explicit backend selection in
build/release and CLI entry points; default Java behavior stays available.

## Execution phases and stop conditions

1. Record synchronization and this reviewed plan. Inspect the real upstream
   compiler/runtime and run a small compiled calculation smoke test.
2. Implement general lowering, source mapping, and Java injection. First verify
   real Catala execution, exact arithmetic and branch selection, then full
   status/reason/evidence/trace/hash agreement. Use the reference only in tests.
3. Implement the reproducible build and explicit backend selection. Verify
   pinned toolchain inputs, no decision fallback, deterministic package bytes,
   and rejection of malformed bundles and tampered output.
4. Run the full language fixtures and SPI control corpus with a compiled Catala
   class for each distinct bundle. Add focused interaction tests for nested
   defaults, unknown/error precedence, skipped inexact branches, shared rules,
   dates, large integers, and arbitrary fact/exception identifiers. Test semantic
   bundle mutations and a faulty calculation backend to expose fabricated traces.
5. Exercise the Catala-built JAR through the existing transaction/concurrency,
   independent Java caller, mode, event, release, export, restore, corruption,
   and stale-evidence tests. Test the plain backend after the shared hook change.
6. Preserve commands, checks, hashes, result report, plan, and reviewed-source
   fingerprint in a new remediation run. Document reviewer source navigation
   and the separate pending human study. Update the reset memo and commit the
   completed branch work. Do not merge into main or promote the default engine.

A compile/type/semantic/integrity failure blocks the dependent phase and triggers
repair. It does not reject Catala as a direction. Stop continuation only if the
required semantics cannot be represented, trusted pinned tooling cannot execute,
or the evidence cannot be preserved. A missing human reviewer study blocks a
claim of reviewer benefit and final adoption, not implementation or testing.

## Evidence contract and research intent

| Field | Predeclared contract |
| --- | --- |
| Main question | Does the generated backend satisfy the existing executable RuleIR and Java integration contracts? |
| Candidate | Catala expression/selector kernels with explicitly shared Java boundary and provenance machinery |
| Exact comparators | Current Python evaluator, existing Java backend, versioned RuleIR fixtures, and integration invariants from merged main |
| Primary pass criterion | Exact equality of complete results, including ordered traces and diagnostics, except distinct engine/result identities; each result hash independently verified; all applicable integration assertions pass using actual Catala JARs |
| Promotion veto | Any semantic/trace mismatch, unbound compiler/runtime/source identity, ignored malformed input, tampered artifact acceptance, or required integration failure |
| Continuation veto | Invalid harness/reference assumptions, unavailable trusted tools, corrupt/missing evidence, or unrepresentable required semantics after investigation |
| Repair trigger | Compile errors, mismatches, lazy-evaluation mistakes, metadata drift, nondeterministic builds, or missing test coverage |
| Explanatory only | Source length, compile time, package size, and execution-layer counts; no speed/readability ranking |
| Expected failure | Native default coalescing differs; explicit lowering must repair that mismatch |
| Non-conclusions | No legal correctness, formal compiler equivalence, independent validation of shared infrastructure, performance superiority, human readability benefit, or production approval |
| Artifacts | `artifacts/catala/remediation-01/`, this plan, implementation review/result/reset notes |

## Defaults, assumptions, and pre-mortem

| Choice / provenance | Justification and status | Failure mode / earliest check |
| --- | --- | --- |
| RuleIR canonical / existing authoring and release model | Reviewed project baseline | Bundle threshold mutation must change source and execution |
| Catala 1.2.1 / existing pinned local toolchain | Reviewed compatibility starting point | Verify binary and Java runtime hashes, compile actual fenced Catala, invoke output |
| Shared Java envelope / existing raw-host contract | Engineering reuse, explicitly correlated evidence | Fault-inject Catala results and observe trace; compare full reference result |
| Explicit status and selector integers / target semantics | New hypothesis checked by truth tables | Unknown/error/multiple-true and lazy-branch counterexamples |
| Integer dates and money / canonical typed scalars | Exact representation, not approximation | Date endpoints/order, negative and very large integers, inexact scale rejection |
| JDK 17 and deterministic ZIP / current deployment contract | Reviewed baseline | Two builds in different paths must have identical JAR/manifests |
| Existing finite fixtures plus focused interactions | Regression evidence, not exhaustive proof | Avoid dynamic plain-Java Runner fallback; require Catala identity and class dispatch |
| Human review deferred / no human data supplied | Pending external acceptance | Never report reviewer superiority or fabricated study completion |

A run could pass misleadingly if it invokes the plain Java fallback, compares
only root values, synthesizes traces using the oracle, silently truncates values,
or tests releases using a non-Catala build. The checks above target each risk
before broader testing. No stochastic ranking is planned; all acceptance checks
are deterministic engineering invariants.

## Pre-execution skeptical audit

The first narrow draft was rejected: it deferred the trace and host gaps the
user asked to repair. This replacement closes all automatable implementation
work and retains only external human/adoption decisions. It uses the committed
main baseline, explicit shared-component limits, correct default semantics,
complete-result comparison, strict fail-closed dispatch, and repair-oriented
stop conditions. PASS for implementation under this contract. Final acceptance
requires the recorded tests and post-implementation review, not this plan alone.

## Exact execution

Working directory: `.worktrees/catala`; Python:
`/home/chakwong/python/legalmath/.venv/bin/python`; JDK and pinned Catala paths
are explicit in `tests/catala/backend_support.py`. The master validates those
paths against the retained toolchain lock. No downloads or model calls occur.

```bash
PYTHONPATH=src /home/chakwong/python/legalmath/.venv/bin/python scripts/catala_remediation_program.py --out artifacts/catala/remediation-01
```

Before this command, inspect the implementation and write the fingerprint to
`docs/implementation/catala/gap-remediation-review.json`. The program rejects
changed inputs. It records every exact build command plus the full pytest
command and test selection. The master has eight bounded phases. The corpus
and interaction tests execute directly into retained comparison directories;
pytest excludes only those two already-executed tests and runs all remaining
Catala tests, unit/conformance tests, Java host/transaction/release tests, and
changed main assurance workflows. Timeout is 120 seconds per build subprocess,
60 seconds per Java comparison, and 600 seconds for the final regression group.
Any failure preserves evidence and stops dependent phases; a repair requires a
new reviewed fingerprint and a fresh output directory.
