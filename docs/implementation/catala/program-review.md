# Program review before execution

Verdict: **PASS FOR BOUNDED EXECUTION**, subject to the exact file hashes in
`program-review.json`. This is the implementing agent's skeptical code review,
supported by boundary tests and compiler/Java smoke checks. It is not independent
legal review or evidence that human reviewers prefer Catala.

The eight-phase program has real actions for baseline freezing, toolchain checks,
profile validation, Catala typechecking and Java generation, differential
comparison, package verification, reviewer-packet generation and an adoption
decision. A stage result identifies its evidence. A failed prerequisite prevents
dependent stages from running, while the decision is still recorded. Existing
output directories cannot be reused. Unit fault injection verifies this path.

## Findings and repairs

1. **Wrong or moving baseline.** The other worker continued changing main after
   the checkpoint. The worktree starts from the remotely verified `66d15b2`.
   Phase 1 verifies reference code, schemas, Java runtime and corpus against that
   commit before computing expectations. Local imports explicitly select this
   worktree, bypassing the main checkout's editable Python installation.
2. **Circular conformance.** The candidate adapter imports shared schema/type/time
   checks but never the reference evaluator. Catala owns threshold and ambiguity
   calculations. Baseline evaluation occurs only in the comparison program.
   Preflight version, scope and fact-conflict decisions are separately attributed.
3. **Default semantics mismatch.** The pinned upstream
   `tests/exception/good/two_exceptions_same_outcome.catala_en` accepts coalesced
   equal outcomes. RuleIR's corresponding fixture demands conflict. The authored
   Catala scope explicitly computes ambiguity. The runner observes native amount
   ten and ambiguity code two, then deliberately removes this check to test that
   the harness detects the incorrect candidate.
4. **Missing facts and monetary units.** Inputs retain a known/unknown flag. HKD
   cents use arbitrary-size integers. Boundary neighbours, missing/known/conflict
   combinations, validity and recording-time boundaries, and a changed masked
   amount test this contract. No amount placeholder is promoted to evidence.
5. **Environment contamination.** PATH isolation alone did not remove Conda
   compiler activation variables. A fresh OCaml switch uses a small explicit
   environment and system GCC. The preparation script rejects an OCaml config
   containing Conda settings. The compiler, dependency export and complete pinned
   source inventory are recorded. Runtime compilation rejects additional files.
6. **Unexpected native interfaces.** Catala prints integer JSON as `1.0` in the
   interpreter and as strings in Java. Exact Decimal parsing accepts integral
   representations and rejects fractional values, booleans and binary floats.
   Generated Java scopes have both calculation and output-copy constructors;
   the bridge selects the exact calculation signature and validates named inputs.
7. **Proxy promotion.** A passed finite corpus, successful HTML generation, source
   length or test count cannot promote the adapter. The program always records
   the uncompleted human study, full trace contract and existing transaction/release
   integration. The output projection is explicitly narrower than full RuleIR
   result-schema equivalence. No reference trace is attached to candidate results.
8. **Reproducibility and stop conditions.** Commands have bounded timeouts and
   captured output. The runner requires a reviewed code/plan/toolchain fingerprint.
   Packages require an external trusted manifest hash, reject altered bytes and
   rewritten manifests, and execute copied checked jar bytes. No network,
   installation, branch operation or release action occurs in the master runner.

## Pre-run evidence and limitations

Seventeen focused tests passed, including boundary rejection, temporal evidence,
conflict precedence, exact integer decoding, package integrity, stale review,
failed-phase propagation and existing-output protection. The real Catala compiler
typechecked both scopes with invariant checks, and generated Java compiled for
Java 17 and executed both the exact financial threshold and ambiguity examples.

The declared profiles cover the SPI financial subcondition and one synthetic
default with two equal-valued exceptions. Arithmetic, dates as computed values,
arbitrary nested rules, rule references, arbitrary exception priorities and the
remaining RuleIR operators are unsupported, and fixture instances outside the
profile must be rejected. Version/knowledge times are boundary semantics, not a
claim that Catala proves legal effectiveness. Scope and conflict preflight are
adapter behavior, not independent Catala validation.

The Java bridge is a typed calculation component behind the validated Python
entry point. It does not yet replace the current standalone Java policy, reproduce
the RuleIR trace or enter the release/transaction path. These are explicit
adoption vetoes, not concealed successful integration claims.

## Review of the first execution repair

Run 01 passed phases 1--4, then found one mismatch among 112 declared comparisons:
the version-error diagnostic omitted the standard message while retaining the
correct status, code and pointer. This invalidated that adapter's complete
diagnostic projection; it did not invalidate the baseline, harness or Catala
research direction. The shared stable `diagnostic` constructor now supplies the
complete error, its source is frozen with the baseline, and a focused regression
test fixes the expected message. The repair preserves the candidate/reference
separation because diagnostic formatting is a shared boundary, not a calculation.
Run 01 remains unchanged; the revised code is approved for a fresh run 02 after
the focused suite passes and the review fingerprint is renewed.

## Final review of identity, source map and host delivery

Run 02 completed the bounded comparison with zero mismatches. The final audit
identified useful delivery repairs before preserving the definitive run:
candidate result identity now commits to adapter, compiler/source or jar bytes,
and packaged calls also include the externally trusted manifest hash. Each new
run snapshots the reviewed code, profile and plan, so uncommitted candidate bytes
remain reconstructible. The source map resolves six named definitions to exact
expressions and lines. A separately compiled Java caller now exercises the same
library-host pattern as the existing project tests. The package retains generated
Java and runtime sources with their license. The reviewer packet uses concrete
examples and descriptive Catala identifiers, and the compiler's HTML is wrapped
as a standalone document. These changes require renewed review fingerprints and
a complete final run; the prior runs remain intact.
