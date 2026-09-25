# Catala remediation plan review

Reviewed against merge `5c47153f` before substantive implementation. The initial
narrow plan is superseded: reporting trace and host gaps as unavailable would
leave the user's requested implementation repair unfinished.

Verdict: **PASS for implementation of the revised plan** at
`docs/plans/catala-gap-remediation.md`. Default promotion and human reviewer
benefit remain unestablished, separate from engineering completion.

The audit checked wrong baselines, proxy metrics, hidden defaults, stale context,
unfair comparisons, environment assumptions, stop conditions, and whether the
planned commands actually exercise Catala. Required controls are:

- Merge committed main and preserve its unrelated active work.
- Generate from arbitrary validated bundles, rather than four recognized hashes.
- Preserve RuleIR's explicit multiplicity conflict; native Catala defaults compute
  a different result for equal consequences.
- Compare full traces, reasons, provenance and hashes, including lazy traversal.
- Bind real compiled Catala scopes into the Java host and fail missing dispatch.
- Use real Catala builds for transaction/release tests; merely rerunning existing
  tests with the original Java builder would not answer the question.
- Pin all compiler/runtime inputs and preserve deterministic deployment bytes.
- Record the shared Java boundary as correlated evidence, not independent proof.
- Continue to repairs for expected candidate failures; never call human feedback
  absent only after treating that absence as a reason to abandon implementation.

This is the executing agent's skeptical review, not an independent human review.
Post-implementation findings and the exact reviewed source fingerprint will be
recorded with the remediation result.

## Implementation audit before the retained run

The generated scope uses a list of typed operand records rather than one Java
constructor argument per child, avoiding the JVM argument-count limit for
large defaults. Integer payloads remain exact; the upstream CatalaInteger
implementation uses BigInteger and integer conversion truncates a rational
quotient, so scale checks the multiplication identity before accepting it.
Only nonnegative scale numerators are legal in the current RuleIR schema;
a negative operand tests signed division without broadening that schema.

The Java host hook does not invoke the reference evaluator. A compiled literal
fault appeared in both result and trace and was rejected by full conformance.
Missing generated dispatch throws; the NDJSON Runner refuses dynamic plain-Java
evaluation from a Catala JAR. Distinct engine identity is checked during release
verification. Catala release idempotency includes the build manifest; existing
plain-Java idempotency envelopes are preserved for compatibility.

The standalone JAR contains the pinned Catala runtime, Apache license, generated
source, source map, canonical bundle and host sources. Relative compiler inputs
avoid embedding temporary paths. Upstream runtime compilation is separate from
project/compiled code, which retains javac lint warnings as errors. Catala 1.2.1
warns about its built-in sum syntax and unused uniform literal operands; those
warnings are retained. Using the pinned built-in aggregation avoids introducing
uncompiled standard-library modules. A compiler upgrade needs a fresh review.

Focused checks passed before this retained run: finite fixtures and SPI cases,
277 deterministic interactions, source mutation sensitivity, honest trace fault
injection, draft/production/replay calls, independent host, transaction races,
synthetic release/export/history/corruption/overlap, and portable host meaning.
One diagnostic fixture initially used a forbidden negative scale numerator and
was corrected to a negative operand. One negative assertion matched the wrong
English error wording and was corrected to check the stable error code. Neither
was treated as evidence against the language or as a passing check.

Remaining limits are finite test coverage, shared host infrastructure, bounded
compiler/JVM resources, institution-specific validation, and absent human
reviewer evidence. These limits prevent stronger adoption claims; they do not
leave the originally missing lowering, trace or host implementation deferred.
The source fingerprint records this self-review, not an independent review.
