# Catala engineering closure results

Implementation checkpoint `09a81a31`, 28 September 2026. The bounded engineering
follow-up implements single-invocation batch execution, invariant-checked tracing
and explicit resource preflight. The final complete regression passed **807 tests
with zero skips in 1,038.44 seconds**. The implementation source stayed unchanged
throughout that run.

## Execution and preservation of meaning

`execute_all` verifies one build, prepares one snapshot and invokes the native
program once. It returns the same individual result records as `execute`,
including partial values, missing/conflicting evidence, reasons, validity times
and build identity. Scalar RuleIR and Catala compatibility targets send all
requests through one JVM. The native compatibility CLI uses this path; the shared
CLI exposes `rules execute --all`. A supplied build hash is checked again at the
native execution boundary, and the verified JAR bytes are frozen before use.

Batch verification checks every external expected result, replays the complete
batch and compares native values with plain Java and the original Catala
interpreter. Altering a value, removing an output, changing a time or substituting
a different build fails verification. The combined semantic control uses a typed
helper to filter a collection with conflicting unused fields, sum exact rational
amounts, apply an exception and explicitly round a selected output.

The bounded envelope check used independent `7 + index` integer answers. Every
batch and individual result agreed exactly; interpreter and plain-Java checks
passed. The recorded observations were:

| Outputs | Batch JVM calls | Individual JVM calls | Batch wall seconds | Individual wall seconds | Batch JVM peak RSS (KiB) | Candidate bytes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 1 | 0.092592 | 0.090456 | 40,080 | 1,232 |
| 8 | 1 | 8 | 0.158720 | 1.270220 | 40,800 | 10,045 |
| 20 | 1 | 20 | 0.460707 | 8.502588 | 41,760 | 25,797 |
| 40 | 1 | 40 | 1.259240 | 44.087918 | 45,600 | 52,257 |

Wall time includes host execution work but excludes compilation. Peak RSS covers
the execution JVM only. These are single local observations made while frozen
replay was also running. They are descriptive, without uncertainty estimates;
they establish neither a general speed ratio nor superiority over RuleIR. The
hard engineering result is removal of repeated native execution for a batch.

Frozen replay passed **186 exact checks over 13 existing builds**: 44 paired
scalar cases (88 executions), seven richer version-1 outputs and 91 version-2
checks. Complete result records remained equal, and no old build was regenerated
or given a new identity. The old trace derivative remains retained.

## Compiler assurance and resource diagnostics

The second trace derivative suppresses upstream AST trace rewriting during
semantic passes, then observes Java emission. Both original and instrumented
compilers now execute `--check-invariants`, including nested helper/scope calls.
New manifests record `trace_invariant_check=original_and_instrumented`. Ten
existing native tracing tests passed, including lazy choices, nested scopes,
exceptions, options, variants, dates, collections and library calls. The retained
compiler patch and lock identify the derivative exactly.

Tracing observes emitted branches, option/variant decisions and scope outputs.
It does not enumerate optimized-away source choices or steps inside external
standard-library code. Successful compiler invariants validate the ordinary
compiler passes; the Java observation hooks still require the independent value,
lazy-execution and tamper checks. This is stronger assurance for the declared
trace, not a proof of the whole implementation.

`rules resources` reports actual input/output counts, generated types and depth,
expanded fields and candidate UTF-8 bytes. It is separate from translation
records, preserving their commitments. Tests reject 41 manually declared inputs,
32 generated types, excessive encoded depth and source expansion beyond 64,000
bytes. Fourteen one-field record types use exactly 30 native types after state
encoding; fifteen require 32. The parser and original safety caps remain in force.
A static pass does not promise that every combination inside the caps will fit
runtime, trace or compiler budgets.

## Validation and decisions

The complete suite passed against `09a81a31`, with source hashes captured
before and after and Hypothesis seed `20260928`. All 807 test IDs passed in one
invocation; this count is not an aggregation of earlier runs. Two dependency
deprecation warnings were reported, with no test failures or skips. Its JUnit report, log and manifest
are retained under `artifacts/catala/engineering-closure/`. The two initial focused
failures were malformed new test fixtures: a copied scalar rule still claimed
an unchanged retained reading, and a helper expression used the wrong binder
syntax. Correcting the manual-fixture declaration and expression resolved them;
the repaired checks passed. A resource probe also crossed the frontend's own
40-fact limit before reaching its intended native-boundary check; it now declares
the oversized model explicitly as a manual rejection fixture.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Use batch execution for requested output sets | One JVM and exact individual-result equality at 1/8/20/40 outputs | No value, status, evidence or identity mismatch | Other workload costs | Keep single-output and batch regression checks | General speed ranking |
| Use the second trace derivative for new builds | Both invariant checks and three-way exact value agreement | No failure in the native probes | Finite coverage; external library internals unobserved | Preserve trace tamper/laziness tests and old locks | Formal correctness proof |
| Retain defensive resource limits | Precise static expansion/rejection checks | Oversized programs rejected | Combined compiler/runtime envelopes | Add requirements-driven profiles separately | Arbitrary-size programs |
| Complete the engineering follow-up | 807 tests pass in one final-checkpoint invocation | No failures or skips; source hashes unchanged | Finite regression coverage | Integrate the reviewed checkpoint and retain the evidence | Source or production promotion |

The strongest alternative explanation is fixture coverage concentrated on familiar
operators and small source programs. A counterexample that changes a declared
value, state, evidence path or build identity triggers repair. The weakest evidence
is performance generality: the ladder uses simple integer outputs, one observation
per size, and excludes compiler and host peak memory. Source-quality trials still
need independent adjudication of unfamiliar legal sources; institutional release
integration needs an identified deployment and authority protocol. Recursion and
arbitrary imports need a separately reviewed language/dependency profile. None of
those limitations is closed by this engineering run.

See the [reviewed plan](../../../plans/catala-engineering-closure.md), the retained
[envelope](../../../../artifacts/catala/engineering-closure/envelope.json) and
[frozen replay](../../../../artifacts/catala/engineering-closure/replay.json).

The [validation manifest](validation.json) contains the exact test IDs, command,
environment and source hashes. The [evidence index](evidence-index.json) binds
the retained builds, batch records, frozen replay and regression reports.
