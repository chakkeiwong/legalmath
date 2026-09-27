# Translator completion reset memo

Campaign status: **COMPLETE** for the reviewed bounded implementation and
deterministic validation, committed as `d01635dd` on 28 September 2026. All six
implementation stages in the plan are executed. The
[master-program summary](../master-program-summary.md) records the final outcome,
remaining research questions and main-integration handoff.

Work is isolated in `.worktrees/catala` on `feature/catala-adapter`, from
`507df9ac`. Main's unrelated changes and frozen earlier evidence are preserved.

Version 2 is implemented across `translation/model.py`, `expressions.py`,
`frontend.py`, `catala_structured.py`, `structured.py`, `observations.py`,
`pipeline.py` and `verification.py`. The closed library registry is
`operations.py`. `native_compat.py` and the native CLI support multiple generated
outputs and `--shared-version 2`; legacy single-output tasks still default to
version 1. `tests/translation/test_v2_*` hold independent references.

Do not merge `partial.v1` with `ruleir.v1`: the former follows evaluated field/item
dependencies; the latter retains the existing static fact-conflict veto. Exact
minor-unit scale errors on indivisibility. Separate rounding nodes use explicit
modes. Multiple true exception guards conflict even for equal consequences.
The compiler emits typed state records; Python is an observation codec, not a
third arithmetic evaluator. Native Catala calculates helper, scope, default,
calendar, numeric and collection operations. Rich partial results carry child
states and never expose placeholder payloads as values.

Pinned Catala 1.2.1, the existing native trace compiler and JDK 17 suffice. No
toolchain installation, provider calls or allowance usage occurred. All execution
remains draft-only; source criticism is not human adjudication or release approval.

The full trusted suite passed 792 tests in 966.75 seconds. Final review added a
version-1 large-coefficient compatibility test and record-output scope/default
tests, then repaired the coefficient limit and aggregate abstention status.
The 69-test translation suite passed in 209.22 seconds after those repairs.
Some synthetic metadata still inherited the old threshold example; corrected
fixtures passed the subsequent 35-test affected run in 129.00 seconds. Four sealed
builds and 91 exact checks are retained. Combined coverage accounts for 794
distinct test IDs. Consult `validation.json` and the results note rather than
scratch directories. Logs/XML and separate source hashes distinguish each
checkpoint; final source hashes match the final manifest.

`scripts/translator_completion_check.py baseline` replays frozen version-1 builds
without rewriting them: 44 paired cases, seven rich outputs, nine verified builds.
`retain` packages final compiled fixtures and compressed exact-check records.
`artifacts/catala/translator-completion/regression-work*` is scratch and ignored;
the selected builds and `checks.json.gz` are the portable evidence. Generated Java
has upstream trailing whitespace; retain its exact bytes and hashes.

Remaining limits are explicit: a closed operator/library set, acyclic helpers
and types, generated native type/depth/source limits, list/runtime resource
limits, and repeated evaluation when the native compatibility API returns every
output. No live conversion-quality study or production promotion is implied.
