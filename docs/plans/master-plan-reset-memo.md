# Master implementation plan and Claude review handoff

Date: 22 September 2026. User objective: decide whether development can start,
create a master implementation plan, review it thoroughly and write a handoff
for Claude. The user explicitly clarified “master implementation plan,” not
application code. No Claude review was launched or reported as completed.

## Delivered planning material

- `docs/implementation/master-plan.md`: product, current/target boundary, required
  Java deployment, technical resolutions, milestones, task specifications,
  adversarial acceptance, commands, budgets, owners and readiness.
- `docs/implementation/master-plan.tasks.json`: 25 tasks T00–T24, dependencies,
  required core, outputs, future commands and honest NOT_STARTED status.
- `docs/reviews/master-plan-review.md`: author audit, seventeen findings and
  dispositions, evidence/limits and separate readiness decisions.
- `docs/reviews/claude-review-handoff.md`: self-contained review brief, source
  and code paths, five bounded review passes, adversarial cases, read-only
  constraints and required findings/coverage/report format.
- `docs/reviews/master-plan-evidence/`: original/isolated Java evidence, probes,
  input manifest, spec check and plan check.
- `docs/plans/templates/`: the requested general experiment/result/reset
  templates for future serious runs; no human/model study was run here.

START-HERE, root README, work packages and the execution/storage/Java contracts
were synchronized with the plan. The manuscript PDF, original demo/code/fixtures,
schemas and SQL sketch were preserved. The workspace has no Git repository.

## Important repairs

Cross-backend semantic equality excludes real engine identity and its native
execution hash; every other result field must agree and both hashes must be
independently reconstructed. Actual engine identities are never forged to force
hash equality. The wrapper is explicit canonical `request` plus `result`.

BuildManifest -> VerificationReport -> JavaReleaseManifest -> ReleaseRecord
is an acyclic record sequence. Candidate build precedes approval; controlled
export follows approval. The JAR does not embed a manifest containing its own hash.
Assessment timestamps remain in result identity; incidental timing does not.

Corrections are interval-local. Source-span/interpretation IDs and their source
references need full validation. Consent and obligation completeness cannot
certify future observations. Missing persistence/API/event schemas must close in
T00, not be guessed during runtime coding. Full Java events follow Python event
implementation; the synthetic host race/idempotency protocol has mandatory T15.
T21 explicitly depends on solver-comparison T18.

The old three-week foundation estimate was stale; existing W00–W04 including
W03J totals 17–25 engineer-days. The plan uses provisional stage allocations and
re-estimation after M2, not a twelve-week completion claim.

## Verified starting state

`python3 scripts/check_spec_pack.py` passes its structural/source/SQL checks and
reports zero full-runtime decisions. Targeted probes show the current helper
accepts duplicate spans, duplicate interpretations and a missing interpretation
source. Those are recorded implementation limitations; the helper was not changed.

An isolated copy of the Java example was rebuilt with the project-local JDK 17.
It passes 32 decisions, eleven consent histories and three compiled mutation
checks, with separate host and reproducible build checks. All fifteen compared
input/source/generated/binary hashes match the original evidence. The temporary
workspace is recorded in the evidence directory; durable results are copied there.
No GPU, model call, bank connection or adjacent environment change was involved.

The plan checker validates the task graph, prose/JSON dependency agreement, all
core ancestors of T22, sixteen acceptance families, local links and file identity.
This is a planning consistency check, not a proof of the future application.
Its first run caught a multiline task-title parser error and missing extracted
acceptance text. Both extraction and checking were repaired; the failed report
is retained and all task metadata was regenerated from the correct sections.

## Decision and continuation

Ready to start T00–T03. The full runtime, engineering MVP, human/model pilot and
bank deployment remain separate unfinished stages. Next implementation work is
T00: freeze missing schema/error/storage/API contracts and independent negative
cases, then isolated package/storage/source intake. Independent Claude review
may require targeted changes; a handoff memo is not its verdict.

Strongest alternative explanation for demo agreement remains a shared source
interpretation mistake. Independent compliance adjudication is required for a
bank release. Optional research adapters and human business comparisons cannot
become prerequisites for useful independent source/runtime engineering.
