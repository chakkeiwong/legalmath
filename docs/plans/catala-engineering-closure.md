# Catala engineering closure

28 September 2026. Baseline `aa20a84b`, `feature/catala-adapter`.
The user requested a plan, thorough review and execution for the remaining gaps
whose repairs are known. Implementation uses the clean Catala worktree; unrelated
main-worktree manuscript and assurance changes are preserved.

## Question and evidence contract

Can the existing shared frontend and Catala execution path evaluate all outputs
in one invocation, retain exact results and evidence, and produce decision traces
without bypassing compiler invariants? Can users discover the supported resource
envelope before compiling, and can the final source checkpoint pass one complete
regression run?

The comparator is the committed translator at `aa20a84b`, its frozen version-1
and version-2 builds, the original RuleIR evaluator on their common semantics,
and hand-calculated references for structured semantics. A batch must equal
individual results in status, value, partial values, reasons, provenance, times
and build identity. One native JVM invocation for all selected outputs is an
engineering acceptance criterion. Elapsed time and memory are descriptive only;
they cannot establish a general speed ranking between Catala and RuleIR.

Trace acceptance requires the original and instrumented compilers to run with
`--check-invariants`, exact instrumented/plain Java agreement, pinned-interpreter
agreement, lazy branch observations, and rejection of altered trace/build data.
Compiler success alone is insufficient. Existing sealed builds must still verify
without rewriting their identities. Resource checks must identify the actual
limiting dimension and reject overflow before compiler execution.

Wrong results, altered uncertainty or precedence, missing evidence, duplicate
native execution, skipped invariants on new traced builds, or accepted tampering
veto promotion and trigger repair. A corrupt baseline, invalid independent
reference, missing pinned compiler, or changing source during the final suite
vetoes continuation of the affected run until repaired. A candidate failure does
not reject Catala or end a phase intended to repair that failure.

No live interpretation calls or new legal judgments are made. Passing cannot
establish source fidelity on unfamiliar laws, statistical superiority, full
Catala coverage, human readability acceptance or institutional deployment.
Artifacts go under `artifacts/catala/engineering-closure/`, with a manifest and
results under `docs/implementation/catala/engineering-closure/`.

## Execution sequence

1. Add verified multi-output execution to the shared pipeline. Verify and prepare
   one build/snapshot, freeze executable bytes, run a native program once, and
   project each output with the same result contract as individual execution.
   For scalar targets send requests through one JVM. Expose explicit `--all`
   execution and route the native compatibility command through it. Preserve the
   existing single-output API. Add batch verification and integrity tests.
2. Build a separately pinned second trace-toolchain derivative. Disable upstream
   AST trace rewriting during semantic passes and enable observation only when
   emitting Java. Keep ordinary compiler checks enabled on both outputs. Test
   nested scope/helper calls, exceptions, lazy branches, options, variants and
   libraries against independent expected values and the original interpreter.
   Describe trace coverage precisely: emitted source choices and outputs;
   externally implemented standard-library internals remain an opaque boundary.
   Keep the old toolchain and historical records intact.
3. Provide a separate, deterministic resource preflight report so historical
   translation hashes do not change. Report input/output counts, generated type
   count, nesting and candidate bytes with limits and structured overflow reasons.
   Exercise small-to-boundary multi-output programs and generated-type/source
   overflow; do not lift safety caps without evidence. Add interaction cases
   combining helpers, strict defaults, partial observations, collections and
   explicit rounding. Retain representative checked builds/results.
4. Run focused tests and repair failures, then frozen version-1/version-2 replay
   and one full regression on the final implementation checkpoint. Use explicit
   process deadlines and retain logs, test IDs, exact source hashes, commands,
   tool identities, CPU status, wall times and artifact hashes. Do not aggregate
   older checkpoints into the final suite count. Record any environmental block
   separately from implementation failures.
5. Update the implementation guide, master summary and reset memo with changes,
   evidence and the remaining limits. Commit only this work on the Catala branch.
   Integrate with main only after checking concurrent work and compatibility;
   retain unrelated uncommitted files and never rewrite historical artifacts.

## Defaults and assumptions

| Choice | Provenance / status | Failure mode | Earliest diagnostic |
| --- | --- | --- | --- |
| Same shared model and evidence policy | Committed baseline | Batching changes lazy dependencies or static conflict policy | Exact per-output comparison on unknown/conflicting inputs |
| One whole native program per snapshot | Existing runtime already returns all outputs | Per-output Python loop launches the JVM repeatedly | Count actual runtime calls and compare complete records |
| Emitter-only tracing | Repair hypothesis | Optimizer removes a semantic observation or source positions drift | Lazy/nested/exception trace probes and forged-position rejection |
| Retain old trace lock and compiler | Compatibility requirement | Old build identity silently changes | Frozen build replay |
| 40 inputs/outputs, 30 native types, depth 12, 64,000 source bytes | Existing defensive profile, not scalability evidence | Generated encoding exceeds user-visible type count | Deterministic preflight and first unsupported boundary |
| Pinned Catala 1.2.1, JDK 17, Python 3.11 | Existing environment | Conda tools contaminate compiler rebuild | Lock checks and isolated OCaml build environment |
| Deterministic semantic checks | Engineering scope | Passing fixtures mistaken for legal/source quality | Explicit separate evidence and non-claims |

Research intent: improve execution and assurance without changing the shared
interpretation. Expected failures are trace attribution, state/provenance drift,
resource expansion and stale build verification. Exact agreement and final-suite
success are promotion criteria; invalid harness/tool identities are continuation
vetoes; runtime/memory observations explain costs only. There are no stochastic
rankings or default-backend changes.

Pre-mortem: two new paths could share a bug and agree; independent values and the
untouched interpreter address this. A batch could silently mix build revisions;
one verified manifest and frozen JAR bytes must bind all outputs. Disabling trace
rewriting could weaken observations; explicit branch/enum/option and default
tests must state which source decisions remain visible. Larger limit numbers
could merely defer a compiler crash; the plan retains limits and measures the
supported envelope instead. A full suite could include unrelated concurrent
changes; the clean worktree and source manifest prevent that ambiguity.

## Skeptical review before execution

Root Codex review; no independent reviewer is claimed. First draft REVISE:
changing existing capability payloads would invalidate deterministic translation
commitments; overwriting the first trace compiler would destroy reproducibility;
counting old tests would not answer the final-checkpoint question; and a faster
small batch would not demonstrate general backend superiority. The reviewed
plan uses a separate resource report, a versioned trace derivative, frozen replay,
and a single final suite with descriptive timings only.

Second review PASS for execution. Baselines share the frontend and retain their
explicit evidence-policy differences. No unexamined numerical defaults or model
budget is introduced. Compiler/toolchain assumptions have early exact probes;
resource caps remain reviewed defensive limits. Each planned artifact answers
the stated engineering question, with repair triggers and continuation vetoes.
Arbitrary imports/recursive programs need a new reviewed language and dependency
profile; unfamiliar-source quality needs independent adjudication; institutional
identity/transport needs deployment requirements. Those gaps are not claimed
closed by engineering tests.

Commands use `PYTHONPATH=src:.` and `.venv/bin/python`; the toolchain rebuild uses
`/usr/bin/python3 scripts/prepare_catala_trace.py` with its isolated OCaml
environment. TestClient checks run in the trusted environment as required by the
previously reproduced sandbox hang. All work is CPU-only and uses no GPU library.

The bounded envelope ladder uses 1, 8, 20 and 40 integer outputs with independently
specified `7 + index` answers. Every batch must launch one native JVM and match
each separate output byte for byte; plain Java and the interpreter must agree.
`/usr/bin/time` records each execution JVM's peak resident memory, excluding host
validation and compilation. Those measurements and wall times are descriptive.
Collection interaction checks use complete/partial evidence with exact rational
references. Static overflow probes include 41 manually declared inputs, 32
generated types, encoded nesting over 12 and source expansion over 64,000 bytes.
These probes test rejection/diagnostics; they are not supported language examples.
