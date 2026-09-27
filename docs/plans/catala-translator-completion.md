# Complete the shared Catala translator

28 September 2026. Baseline: `507df9ac`, `feature/catala-adapter`.
Authorization: create, review and execute the plan for the previously identified
implementation limits. Work stays in the Catala worktree.

## Question and evidence contract

Can one source-grounded, target-independent model express and execute scoped rich
rules, exceptions, exact scaling, explicit rounding, typed library operations,
reusable calculations, multiple outputs and partially observed structures?

The engineering baseline is the version-1 shared translator at `507df9ac`, its
44 paired source cases, seven rich outputs and original RuleIR evaluator. New
features use independent, hand-calculated references. Instrumented Java, plain
Java and the pinned Catala interpreter must agree exactly. Compiler success is
an explanatory diagnostic, not the acceptance criterion.

Acceptance requires all listed feature families to be available through the
shared generation schema/parser, validation, source criticism, deterministic
lowering, execution and capability reporting. Tests must check values, statuses,
provenance and deliberately adverse cases. Existing version-1 model/build
commitments and scalar results must remain reproducible. Unsupported target
features must receive explicit reasons before compilation.

Wrong values/statuses, silently changed exception or rounding policy, lost
uncertainty, unbound evidence, or runtime work done by a hidden Python arithmetic
evaluator veto acceptance and trigger implementation repair. Corrupted baseline
artifacts, missing pinned tools or an invalid independent reference stop the
affected check until repaired. A failed candidate is not evidence against Catala
or modular interpretation. There are no live provider calls or statistical
rankings. These checks cannot establish legal fidelity, production readiness,
universal language coverage or Catala superiority.

## Reviewed implementation sequence

1. Introduce model/interpretation version 2 while preserving version 1 byte for
   byte. Add explicit typed helper definitions and named outputs. Extend the
   prefix grammar with rule/helper calls, record construction, defaults,
   scaling, rounding and a closed typed library-operation registry. Reject
   recursive helpers, undeclared operations and type mismatches. Bind retained
   readings to every executable output/helper, including exception citations.
2. Compile version-2 expressions to typed Catala result records. Arithmetic,
   conditions, exception selection and state propagation execute in Catala.
   Result records carry state, typed payload, evidence-path references and an
   error code. Inaccessible payload placeholders are never returned as values.
   Scope evaluates before its body. Exceptions evaluate all guards, reject
   multiple true guards even with equal consequences, propagate unknown guards,
   and evaluate only the selected consequence. Exact integer/minor-unit scaling
   returns an error when indivisible; explicit rounding is a distinct node.
3. Provide typed min/max, date addition with explicit month-end clamping,
   month-end and collection length/sequence operations. Round exact decimal
   minor units to integer or money minor units using named toward-zero, floor,
   ceiling or nearest-ties-away modes. Helpers compile to typed Catala scopes;
   named outputs use one shared interpretation. Keep native type/source/resource
   limits; capability reporting must explain any generated-interface overflow.
4. Add an opt-in `partial.v1` evidence profile for version 2. It permits observed
   structures with separately known/unknown/conflicting fields and list items.
   Known optional absence differs from unknown optional evidence. Incomplete
   membership makes a collection unavailable to aggregates, never an empty or
   complete observed subset. Projection can use known fields independently.
   This profile uses dependencies actually evaluated; it does not silently
   replace RuleIR's static whole-fact conflict veto. Existing `ruleir.v1` and
   `complete.v1` policies remain unchanged. RuleIR must reject the new profile
   when its policy cannot represent it. Structured partial output is explicit.
5. Bind encoded evidence and decoded status/value to the existing verified native
   build and trace. Verification replays the input encoding, instrumented and
   plain Java, and exact interpreter assertions. Add frontend/critic guidance,
   strict schemas, CLI tests, provenance/tamper tests and a documented example.
6. Run focused tests first, then retained paired replay and relevant regressions.
   Record the actual commands, environment, hashes, exact references, decisions,
   remaining limits and a reset memo. Commit a reviewed checkpoint.

## Defaults and assumption audit

| Choice | Provenance / status | Failure mode | Earliest diagnostic |
| --- | --- | --- | --- |
| Version-1 lowering unchanged | Frozen baseline | Regenerating an old build changes its hash | Verify an existing scalar and rich build |
| Version-2 result records | Implementation hypothesis | Placeholder evaluated or returned as evidence | False/unknown scope with invalid arithmetic body |
| Strict exception overlap | Existing shared RuleIR policy | Native Catala coalesces equal consequences | Equal and unequal overlapping exceptions |
| Explicit rounding modes | Task-scoped reviewed API | Native money rounding changes exact scale | Positive/negative halves and indivisible scale |
| Partial dependencies | Explicit optional new policy | Mistaken claim of RuleIR semantic equivalence | Lazy branch conflicts plus unchanged legacy conflict case |
| List completeness | Existing complete-input principle, refined | Missing membership treated as zero | Empty complete vs empty incomplete list |
| Helpers and outputs | Explicit source-reading declarations | Hidden facts or helper cycles | Pure parameter boundary and cycle tests |
| Closed library registry | Pinned upstream code | Documentation and implementation disagree | Hand reference, Java and interpreter for each operation |
| Existing toolchains and limits | Reviewed project baseline | Wrong compiler or unbounded expansion | Lock verification and smallest compiled probes |

## Research intent and stop conditions

Main question: remove implementation restrictions without changing committed
meaning. Candidate: a versioned shared model and typed Catala state lowering.
Expected failures: generated syntax/type errors, incorrect state precedence,
rounding/unit errors and missing provenance. Exact semantic agreement and
legacy preservation are promotion criteria. Semantic/provenance failures veto
promotion and trigger repair. Invalid harness/reference/toolchain identity is a
continuation veto for the affected run. Compile size, runtime and case counts
are explanatory only. A passing fixture does not measure model interpretation
quality or warrant changing the default backend.

Pre-mortem: a run could pass by comparing two copies of the same faulty emitter,
checking only complete data, deriving the expected result from generated code,
or letting the host calculate the answer. Hand references and original Catala
interpreter checks prevent those shortcuts; adversarial scope/exception/partial
cases probe lazy execution and uncertainty. A compiler/type failure weakens the
implementation, not the source-language direction.

Commands use `PYTHONPATH=src:.` and
`/home/chakwong/python/legalmath/.venv/bin/python`, the existing JDK 17 and pinned
Catala 1.2.1/trace toolchains. Tests involving API TestClient use the trusted
environment because the baseline recorded sandbox hangs there. Logs and retained
checks go under `artifacts/catala/translator-completion/`; result notes, manifest
and reset memo under `docs/implementation/catala/translator-completion/`.
Long checks use explicit timeouts and logs. No new compiler installation needed.

## Skeptical review before implementation

Root Codex review, not an independent review: initial approach REVISE. Direct
native defaults and money multiplication change shared overlap/exactness policy.
Treating missing nested values as option absence loses meaning. Reusing version-1
serialization invalidates prior build commitments. Calling the new partial
profile equivalent to RuleIR ignores its static conflict veto. The revised plan
uses versioned models, explicit state lowering, separate rounding, typed nested
observations and an explicitly distinct optional policy.

Revised plan PASS for execution. The actual comparator, non-claims, bounded
resource assumptions, stop/repair conditions and independent references are
specified. Every material convenience remains a tested implementation hypothesis;
none promotes Catala to a new default. Work may repair compiler/adapter defects
within this plan, but must report remaining resource/expressiveness limits.

## Review before retained regression

The focused compiled checks passed after two repairs: an empty exception set
needed a concrete zero metadata record (an empty generic fold was ambiguous to
Catala), and a conflict test had contradictory root evidence IDs. The latter was
a fixture error; strict evidence validation was retained. Inspection of pinned
`stdlib/java/list_internal.java` showed machine-integer narrowing of sequence
length; the lowering now handles reversed ranges and caps positive lengths before
the library call. Date offsets are similarly guarded before native duration
conversion. Expanded type construction/validation is bounded before compilation.

The native compatibility CLI now supports multiple shared outputs, including
camel-case native names, without returning to free-form target generation. The
same interface can explicitly choose version 2 for one output. Version-1 defaults
and all frozen build regeneration remain preserved.

Root review PASS to the retained regression: independent references cover both
signs and half-way rounding, lazy scope/body, equal/distinct exception overlaps,
error/unknown/conflict precedence, records/options/variants, incomplete collections,
stale nested evidence, helper calls, rule references, library domains, CLI and
forged results. The final run uses a fresh artifact scratch directory with a
1,200-second deadline and 90-second stack diagnostics. Trusted execution avoids
the previously confirmed API TestClient sandbox hang. Failures trigger repair;
passing tests will still not establish source-interpretation quality.

## Completion

All six implementation phases are complete. The trusted full regression passed
792 tests. Two final review checks led to a version-1 scale-bound repair and
explicit aggregate abstention for the multi-output adapter; the 69-test
translation suite passed afterward. Correcting inherited synthetic task metadata
then triggered a fresh affected run: 35 tests passed, retaining 91 exact
version-2 checks and four sealed builds. Combined test coverage is 794 unique
IDs. Frozen version-1 replay passed 44 paired cases and seven rich outputs while
verifying all nine original builds without regeneration.

The result note, review, reset memo, schemas, examples and source-hashed run
manifest are under `docs/implementation/catala/translator-completion/`.
Logs, checkpoint source hashes, compressed exact checks and portable builds are
under `artifacts/catala/translator-completion/`. The failure that reproduced the
large-coefficient regression is also retained. No live provider call, dependency
installation, backend-default change or production operation occurred.
