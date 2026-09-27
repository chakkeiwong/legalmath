# Closing native Catala gaps

Date: 26 September 2026. User instruction: create, thoroughly review and execute
the proposed gap-closure plan. Baseline: Catala branch `71633380`; preserve the
prior native and RuleIR evidence. This successor is authorized implementation
and bounded investigation, not a default change or production deployment.

## Research intent and evidence contract

Main question: which remaining limitations can we remove without silently
changing legal meaning, and what evidence distinguishes native capability from
better source conversion? Mechanism: native Catala types/scopes with explicit
semantics, exact boundaries, compiler-location execution records, and approved
immutable packages. The comparator is current RuleIR on its representable
fragment, plus independently written exact reference cases; native-only features
are recorded as unsupported by RuleIR, never scored as RuleIR errors.

Primary engineering criterion: declared semantics and exact behavior match the
specified references, instrumentation preserves outputs, and package/host
integrity tests pass. Primary conversion criterion: all declared behaviors plus
source review and mandatory uncertainty pass per task. Compilation, model
agreement, test-row counts, elapsed time and token counts are explanatory only.
Wrong meaning, lost uncertainty, precision loss, incorrect trace attribution,
authorization bypass or an undetected corrupted package veto acceptance.
Leaked hidden answers, invalid references, changed frozen inputs, unavailable
required tools or exhaustion of the bounded grant stop the affected experiment.
Candidate failures trigger repairs within the frozen limit. They do not reject
the research direction. Human legal adjudication and human reviewer measurements
cannot be supplied by self-review or model votes.

Engineering, behavioral and legal-source conclusions remain separate. Even all
checks passing cannot establish general legal correctness, generalization,
production authorization or superiority. Artifacts:
`artifacts/catala/gap-closure/`; interpretation and continuation notes:
`docs/implementation/catala/gap-closure/`.

## Execution sequence and acceptance

1. **Explicit semantics.** Add a versioned, hash-bound native semantics record:
   exact arithmetic, units, rounding points, date convention, required-input
   abstention, native exception ties and scope of compatibility. Add executable
   shared-fragment comparisons and intentional-divergence witnesses for unknowns,
   conflicts, identical versus different exceptions, rounding and dates. Do not
   claim equivalence for partial inputs or retrofit RuleIR policy silently.
2. **Retained sources and adjudication.** Retain a small multi-source corpus with
   exact bytes/quotes, scope, primitive interface, source lineage, qualifications,
   references and clause dispositions. References are provisional until a
   reviewer independent of the generator adjudicates them. Build validation for
   those records, preserve alternative readings and distinguishing witnesses,
   and produce an actionable legal-review packet. Do not self-sign legal review.
3. **Language coverage.** Implement optional values (known absence versus unknown),
   enum payloads and controlled imports from a declared pinned standard-library
   subset. Keep acyclic types and resource limits. Use real compiler/Java/interpreter
   feature probes before claiming support. Reject undeclared imports and preserve
   exact dependency hashes. Recursion is not a deployment requirement merely
   because the gap list mentioned it: retain explicit rejection until a source
   case requires it and its resource behavior can be bounded.
4. **Executed decisions with source locations.** Prepare an isolated derivative of
   the pinned Java emitter; never overwrite the original compiler or lock. Emit
   original-source coordinates with executed native decisions/branches. Store
   patch, binary digest and runtime identity. Compare patched instrumented Java,
   uninstrumented original Java and exact interpreter values. Exercise both sides,
   short-circuit/lazy cases, enums/options, nested scopes and exceptions; reject
   altered locations/events through replay. Document exactly which control-flow
   constructs are observed; do not invent a complete legal derivation.
5. **Host and package integration.** Install verified immutable native packages,
   retain raw source bytes, bind legal and engineering review to source/interface/
   semantics/build/corpus, use the project's host identity model or a token-hash
   authenticator at a distinct native adapter, and persist activation/rollback/
   revocation audit records. Recheck approvals, release and subject state at commit.
   Test package export/import, corruption/path traversal, expired or revoked
   credentials, stale review, replacement, rollback, concurrent changes, replay
   and idempotency. Keep authorization external to model proposals. Production
   institutions still supply real identities, reviewers and operational policy.
6. **Paired conversion experiment.** Build and execute three declared arms on a
   frozen shared factual interface: current source-to-RuleIR generation component,
   minimal direct Catala and source-reviewed direct Catala. Use existing actual
   RuleIR request/response validation and Java execution, not handwritten RuleIR
   candidates. Name the measured component precisely: a bounded component study
   is not a comparison with the entire assurance algorithm. Source-family hashes
   determine splits; no renamed threshold counts as a new family. Source-adjudication
   pending is explicit; run a development comparison now and produce a separate
   heldout-study admission check that refuses unadjudicated or overlapping sources.
   Hidden reference cases never enter prompts or repairs. Count failed/abstaining
   tasks and all attempts, aggregate at task/source-family level, show paired
   uncertainty under stated sampling assumptions, and withhold superiority when
   the design or interval cannot support it.
7. **Reviewer experiment.** Prepare counterbalanced anonymous assignments, matched
   source/program material and seeded defects, capture accuracy/omissions/time/
   assistance, and validate submissions. Exercise the collection and analysis
   code with explicitly synthetic responses; do not count those as human evidence.
8. **Final audit.** Run focused and relevant regression tests, verify portable
   artifacts and all commitments, write decisions/default-readiness/nonconclusions
   and reset memo, then commit the isolated branch checkpoint.

## Resource/default audit and pre-mortem

| Choice | Provenance and status | Failure mode / early diagnostic |
| --- | --- | --- |
| Pinned Catala 1.2.1 | Existing working baseline | Java/options/stdlib mismatch; isolated feature probes first |
| Derivative compiler | Required because stock Java lacks trace support; hypothesis | Instrumentation changes evaluation or locations; compare with untouched compiler and exact references |
| Complete required inputs | Explicit existing native policy | Inflated abstention; paired missing-input witness and coverage reporting |
| Optional absence | Native option type, distinct from missing evidence | Treating an absent value as unavailable; mixed nested-list tests |
| Imports | Allowlisted pinned library profile | Unpinned transitive dependency or path escape; closure hashes and hostile directive tests |
| Exact independent references | Hand arithmetic / separate Python implementation | Shared author mistakes; explicit calculations and seeded mutants, external review pending |
| Small multi-source study | Development convenience sample | False population claims; uncertainty and human-adjudication state remain explicit |
| Same configured model route | Existing user-authorized access | Correlated critics and memorization; fresh contexts, full provenance, no independence claim |
| Bounded source study | User asks execution; existing global grant ceiling retained | Other work or retries consume budget; use shared ledger and fixed task cap |
| Host authority | Trusted identity config, hashed tokens, two roles | Caller spoofing/stale authority; rejection and concurrent-revocation tests |

Compiler preparation may run up to 10 minutes, in an isolated source/build folder,
using the existing opam switch with no dependency installation. Individual compiles
remain 120 seconds, executions 15 seconds, model calls 180 seconds. Freeze a
concrete study after offline calibration, at most 24 new model calls from the
remaining shared 500-call ledger (two attempts per arm across four tasks). The
old task's 177 ceiling is not
reset: this is the user's newly requested successor. No global ceiling increases.
Actual consumed balance is checked at freeze. No GPU runtime is used. Python and
JDK paths remain those recorded in the native reset memo. Commands and wall times
are retained per phase.

A misleading pass could be a trace recording a wrapper instead of the branch,
a package verifying its own rewritten hashes without a trusted commitment,
optional absence hiding missing observations, copied compiler internals presented
as independent evidence, or a paired study leaking its gold program. Early
checks specifically target these. Default promotion requires representative,
adjudicated heldout sources and supported paired differences; this execution
can close implementation gaps while leaving that empirical decision open.

## Skeptical plan review before implementation

Root Codex audit, not an independent reviewer. Initial verdict REVISE: the prior
suggestion conflated production authentication with a trusted in-process caller,
left the library dependency profile undefined, and risked implying the full
RuleIR assurance algorithm could be compared under a one-call budget. The revised
sequence above uses immutable packages, an explicit authentication adapter,
allowlisted dependencies, and honestly named component arms. It also separates
human prerequisites from work that can execute now. Wrong baseline/proxy metrics,
stop versus repair rules, latent domain assumptions, stale inputs, environment
mismatches and non-discriminating artifacts are addressed. Verdict PASS for the
bounded implementation and development comparison; population/legal/human claims
remain conditional on evidence that has not yet been obtained.

## Corrective audit before execution

The implementation was re-audited after the first draft artifacts were produced.
Four material defects were found and corrected before any live comparison was
accepted: the old semantic script compared prose and Python literals instead of
running both engines; the old study used handwritten controls rather than source
conversion; the first reviewer packet leaked its labels and had no compiled
paired programs; and the first host design counted credentials rather than named
reviewers. Those artifacts remain under `*-invalid-draft/` with explicit
invalidation records. The current scripts execute the pinned compiler, native
interpreter/Java, RuleIR Python/Java, and compiled seeded defects. Approval rows
bind named identities, credential hashes, review commitments and expiry, and
commit-time checks re-read them in the same transaction.

The current execution is frozen to four retained tasks from three source-lineage
families, with 44 fixed factual cases. The source readings and reference cases
remain `PENDING_HUMAN`; source authorship and model review do not count as
independent adjudication. The live study's only permitted model calls are the
four-task, three-arm, two-attempt ceiling recorded in the shared allowance. If
the allowance changes or the frozen packet or source code changes,
the run is invalid and must be restarted rather than silently resumed.

Corrective audit verdict: PASS for executing the bounded engineering and
development study; FAIL for any superiority, legal-correctness, held-out or
human-review conclusion until its stated external evidence exists.
