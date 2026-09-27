# Modular translation reset memo

Work is isolated on `feature/catala-adapter`, from `4020f999`. The main worktree's
unrelated changes and all frozen earlier studies are preserved.

The implementation lives in `src/legalmath/translation/`. Start with
`frontend.interpret`, `model.validate`, `pipeline.translate/build/execute`, and
`verification.verify_execution`. Existing `formal.bundle` delegates to the
shared parser/model and RuleIR lowering. `catala-convert generate` defaults to
the shared workflow; `--legacy-code-generation` and the old Python converter API
retain historical free-form generation.

The paired replay has 44 passing cases on each target and seven exact richer
native outputs. The model and interpretation commitments match across each pair.
The schema/CLI/resume/evidence/tamper tests use fixture providers and make no live
calls. The source packet is
`artifacts/catala/gap-closure/source-review-successor/packet.json`; source
adjudication is still pending. The shared allowance was not used.

Regression accounting covers all 759 collected tests across runs, including 34
new translation checks. A sandbox API TestClient hang interrupted the initial
run after 494 passing progress records. That exact test and the complete remaining
266 tests passed in the trusted environment. `regression.json` retains the test
IDs, command descriptions and log hashes; do not describe this as one completed
full-suite invocation. Final source hashes match the retained paired replay.

Reproduction uses the existing `.venv`, `PYTHONPATH=src:.`, JDK 17 and the pinned
Catala/trace toolchains. `scripts/modular_translation_check.py` verifies and reuses
matching builds, then reruns the exact references. Read
`docs/plans/modular-rule-translation.md` and the result note before interpreting
the run. This is compiler/runtime evidence, not converter superiority.

Remaining architectural limits: one result per generated reading; rich native
models require complete-input semantics and unconditional outer scope; shared
operators do not yet cover native library calls, rounding, helper scopes, or
rich default/scale nodes. Unsupported combinations receive capability reports.
Neither this API nor a source critic authorizes a production release.
