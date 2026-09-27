# Catala branch reset memo

## Campaign completion, 28 September 2026

The authorized Catala implementation campaign is complete through `d01635dd`
on `feature/catala-adapter`. The final stage implements shared model version 2:
rich scope/defaults, exact scaling, explicit rounding, typed libraries/helpers,
multiple outputs and partial field/item observations. The common frontend feeds
deterministic RuleIR and Catala translators; richer expressions can reach Catala
without passing through RuleIR. Version-1 commitments remain reproducible.

Read the [final master-program summary](master-program-summary.md), the current
[translator reset memo](translator-completion/reset-memo.md), and the
[results](translator-completion/results.md). Validation comprises a 792-test full
regression, a 69-test repair run and a 35-test final fixture run: 794 distinct
test IDs across checkpoints, not one final 794-test invocation. Retained evidence
includes 91 exact checks, four sealed builds, 44 paired legacy cases, seven rich
outputs and nine verified legacy builds.

The bounded engineering campaign is complete. Independent legal adjudication,
representative conversion-quality comparisons and human reviewer measurements
remain open; no default-backend change or production promotion follows. Preserve
the distinct `partial.v1` and `ruleir.v1` evidence policies and the documented
operator, type, source-size and runtime bounds.

Completion documents are committed as `cbfc0a03`; main contains the complete
campaign through merge `5417af67`. The fetched `origin/main` at `9160ce72` is
already an ancestor. Thirty focused integration tests passed, the merge tree
matches the tested branch, and unrelated main edits were preserved. The
[integration results](integration-results.md) record validation, preservation
and the closing push/synchronization commands. The user authorized publishing
main and bringing this branch to the same commit. Main's unrelated uncommitted
assurance and monograph work remains outside these commits. Earlier
synchronization statements below describe historical checkpoints only.

## Earlier backend checkpoint (historical)

Worktree: `/home/chakwong/python/legalmath/.worktrees/catala`.
Branch: `feature/catala-adapter`.
Committed main baseline: `9160ce72a17a255242299cc8ab33046f2501f42b`.
Synchronization merge: `5c47153f712b34dbd69fb344b74c87931c4e0b92`.
Reviewed implementation checkpoint: `4a7ce12d`.

At this earlier checkpoint the user requested synchronization of new main work,
planning and execution of repairs for the Catala implementation gaps. Committed
main was merged. The remote main reference then agreed. Its new work
adds interpretation-assurance workflows without changing RuleIR or Java/release
contracts. Preserve the separate main worktree's ongoing uncommitted assurance,
monograph and research work; the synchronization snapshot is `main-sync.json`.

The new backend is implemented. It generates Catala expression and selection
scopes from validated RuleIR, supports the current operators and scalar types,
and connects actual returned values to the existing Java trace and raw-snapshot
APIs. Explicit optional backend selection reaches the release, portable-package,
and CLI build paths. Defaults, event replay, source authoring and institutional
release approvals retain their existing roles. The compiler is a build-time
tool; the generated JAR contains all runtime dependencies and source identities.

Read `gap-remediation-review.md` and `docs/plans/catala-gap-remediation.md` for
the design and pre-execution audit. The narrow first draft was rejected because
it would have deferred the very trace/host gaps the user requested to repair.
The replacement implements those gaps. Shared Java validation/provenance means
this is not an independent whole-engine verifier. Human reviewer benefit and
institution-specific acceptance remain unestablished; they do not block
implementation or deterministic engineering tests.

The retained program is `scripts/catala_remediation_program.py`, with exact input
hashes in `gap-remediation-review.json`. It checks all current fixture bundles,
277 deterministic interactions, full traces/hashes, real Catala transaction and
release integration, regression compatibility and deterministic builds. The
completed retained run is `artifacts/catala/remediation-01/`: all eight phases
passed, with 344 complete decision comparisons, eight shared event cases and
202 regression tests (no failures/errors/skips). Distinct build paths produced
identical JAR bytes/manifests. Final interpretation is in
`gap-remediation-results.md`; no default change or production approval occurred.

Original pilot evidence remains in runs 01–03, the original adapter/master and
`execution-report.md`. Those records describe four exact bundle hashes and two
handwritten scopes; they are historical and must not be confused with the new
generic backend. Do not overwrite them or refresh their fingerprints to pretend
that the revised backend was tested by an old run.

Toolchain: `.localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala`.
Upstream: `.localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa`.
JDK: ignored symlink to the parent checkout's
`.localresources/java-toolchain/jdk-17.0.20.1+1`.
Python: `/home/chakwong/python/legalmath/.venv/bin/python`, `PYTHONPATH=src`.
No global environment changes, network downloads, GPU calls, or model workers
are needed. The original compiler preparation isolated Conda flags as well as
PATH; do not rebuild it inside the inherited Conda compiler environment.

## Direct native converter continuation, 25 September 2026

A separate direct source-to-native-Catala development route has now been
implemented and exercised. Read `native-converter/reset-memo.md` and
`native-converter/results.md` for its seven-task generated-program evidence,
exact I/O, source-domain hardening, real scope-output observations and distinct
host/CLI profile. It does not supersede the RuleIR backend evidence above.
Unlike the earlier offline backend work, this extension used 22 counted model
calls from the existing shared allowance, ending at 175/500. The default
pipeline and production approval state have not been changed.
