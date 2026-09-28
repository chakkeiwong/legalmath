# Plan and implementation review

28 September 2026. Root Codex review; this is not an independent reviewer verdict.

The pre-execution plan was revised to protect committed translation identities,
retain the original trace derivative and separate exact engineering criteria from
descriptive timing. Its skeptical review and assumption ledger are retained in
`docs/plans/catala-engineering-closure.md`.

The implementation review checked the following potential failure paths:

- A whole native program already returns every output. The batch path must call
  that runtime once, then decode each projection; the call-count probes confirm
  this behavior. Scalar targets pass multiple requests through one Java process.
- A batch must not mix snapshots or builds. Snapshot preparation occurs once,
  the enclosing native build hash is passed into execution, and the selected
  verified JAR is copied before launch. Reference tests cover tampered aggregates,
  missing outputs, altered times and wrong expected build hashes.
- Changing the trace compiler must not invalidate old evidence. New builds select
  a second pinned derivative; existing build verification uses each sealed
  manifest. Frozen replay reproduced all 186 old records across 13 builds exactly.
- Invariant checking must be real, rather than a renamed manifest flag. Retained
  command logs for all four envelope builds show six Java compiler invocations
  each, including library units and the traced program; every invocation supplies
  `--check-invariants`. The instrumented compiler performs unchanged semantic
  passes before enabling Java observations. Its preparation-script hash matches
  the retained lock.
- The revised trace has a narrower, explicit meaning: emitted Java decisions and
  scope outputs. It does not promise one event per source condition or visibility
  inside external libraries. Lazy-branch, nested-scope, option, enum, exception and
  forged-position tests assess the implemented meaning. The invariant checker
  does not itself verify the Java hooks.
- Resource reports must not change deterministic translation commitments or lift
  safety limits. The separate report measures generated state encoding and names
  rejected dimensions. Overflow fixtures remain explicitly synthetic. The 40-output
  execution probe is evidence for that program, not arbitrary compositions within
  every cap.
- Test expectations must not be copied from the implementation under test. The
  interaction control has exact rational expectations; the ladder uses the
  independent expression `7 + index`; original Catala interpreter and plain Java
  provide execution checks. Full per-output equality tests assess compatibility,
  not independent legal validity.

Focused checks, frozen replay and the final 807-test regression support these
engineering changes. The final run had no failures or skips and preserved the
source hashes captured before execution; see `results.md` and `validation.json`.
No source-quality, human-review, default-backend or institutional-release
promotion follows. A result counterexample triggers repair; poor source
interpretation would require a different experiment and cannot be inferred from
these tests. The main remaining empirical weakness is workload coverage and the
single-observation timing ladder.
