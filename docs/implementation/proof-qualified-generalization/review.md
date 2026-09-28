# Skeptical implementation review

28 September 2026. Codex self-review; no human quality judgment or independent
reviewer is claimed. The plan's pre-execution audit is retained in
`docs/plans/proof-qualified-generalization.md`.

The first focused run found an invalid new fixture: a rule reference pointed to a
conditional scope. The shared model correctly rejects that construct. The fixture
now references an unconditional result and tests scope on its dependent output.
The repaired focused run passed 39 tests. This was a fixture failure, not evidence
against the implementation or the research direction.

The review also identified and repaired two assurance weaknesses before the
retained campaign. The independent evaluator must evaluate all strict operands
and guards before applying error priority; an earlier conflict cannot hide a later
arithmetic error. Composite partial values outside the evaluator's domain must be
qualified rather than assigned the scalar error result. Also, a local hash chain
alone cannot detect complete rewriting or truncation: an optional externally
retained event-head commitment now supplies that check, and reports without it
state the limitation.

The formal proposition was reviewed against its actual Lean text. It establishes
constructor preservation for any interpretation and input context, not arithmetic
implementation correctness or natural-language legal meaning. Its independent
parser/encoder and declared constructor semantics remain premises. Actual backend
execution has separate finite evidence. The generated challenge seed is a
reproduction choice; no statistical ranking or future legal error rate follows.

The legacy source-investigation campaign is not replaced or given more model
calls. The new assurance command consumes shared models and independently reaches
native Catala. Existing source hashes, old trace derivatives and old deterministic
translation identities are preserved. Its reports remain qualified where that
campaign's uncertainty or unsupported operations persist.

The new feature enforces a machine-only evidence interface. It cannot retrospectively
prove that a pretrained model never encountered a text or that no human influenced
its training. Those are provenance limits, not permission to use human answers as
quality references. Likewise local publication metadata does not authenticate a
future source. Prospective claims remain NOT_ESTABLISHED until suitable evidence
exists, with further qualifications even after observations arrive.

The first generated campaign found a real target mismatch: shared-model signed
scale factors were advertised as RuleIR-compatible, but RuleIR's schema permits
only a nonnegative numerator. Lowering now rewrites a negative scale as zero
minus its positive magnitude. Fresh node identities avoid collisions, old
nonnegative lowering stays identical, and the denominator/exactness condition is
preserved. Two Lean integer lemmas establish sign reversal of every exact
quotient and equality of the exactness domains. A focused real-backend test
checks zero, positive/negative values, indivisibility, nested signs and a forty-
digit input with independently computed answers. All 17 repair/window checks
passed. The first campaign is retained as failed development evidence.

That attempt also exposed a result-manifest serialization error: repository
canonical JSON forbids floating-point values. Wall time is now recorded as an
integer number of milliseconds. Its results.json was already retained; the
incomplete manifest is not passed off as a completed run.
