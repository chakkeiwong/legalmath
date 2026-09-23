# Interpretation automation: reviewed execution contract

Date: 23 September 2026. Implements the A1–A6 priorities in
`docs/implementation/interpretation-round2/automation-next-phase-plan.md`.

## Skeptical review and corrections before implementation

The previous plan is directionally sound but was not executable. It lacked exact
contracts, an operational entry point, independent source-check sequencing,
change-trigger definitions, and acceptance commands. Those are material defects,
repaired here before implementation. P12 is the engineering baseline; neither
310 tests nor model agreement measures English accuracy. Old evidence and the
actual dirty working-tree inputs will be frozen before changes.

The incremental product is a source-assurance orchestrator around the existing
interpretation tree and Java verifier. It must run from the CLI, persist requests,
responses and issue histories, and consume the existing counted model allowance.
It must not be a collection of disconnected demonstration utilities. Existing
release authority is preserved. A clean diagnostic means no detected issue in a
declared profile, never universal legal correctness.

## Question and evidence contract

Question: can complementary source, argument, repair and change checks detect
specified interpretation defects, including unanimous omissions, without sending
every clean control to a person? Comparator: frozen P12 source packet, candidates
and checks, plus explicit single-reading/no-search/search ablations on a common
controlled challenge set. Shared source access is mandatory. No independent
accuracy ranking or financial saving will be inferred from this engineering run.

Primary pass criteria: each phase's mandatory cases below passes; the integrated
entry point executes these checks and exposes unresolved evidence; original Java
replays agree with their explicitly normalized counterpart; previous regressions
pass. Missed mandatory defects, false clean results on missing context, invalid
source anchors, lost history, or silent budget overrun veto acceptance and trigger
repair. Missing legal labels do not veto continued engineering. Unavailable model
service stops dependent live runs, not unrelated implementation. Costs, issue
counts and model judgments are descriptive diagnostics, not correctness scores.

Predetermined engineering challenges include unanimous exception omission,
authentic quotation supporting an unrelated assertion, remote exception, may/must
change, wrong threshold, missing annex, stale incorporated definition, false case
authority, attack-type confusion, reversed output convention, split facts,
UNKNOWN/conflict, event-date change, and harmless whitespace/identifier changes.
Each expected relation is recorded in a fixture before the corresponding test.
These are development challenges; no held-out legal-accuracy claim is made.

## Concrete supported profile

* A1: versioned source documents and references, two extraction inventories,
  independently checked packet coverage, bounded official-host acquisition,
  visited-set closure, explicit missing/stale/cycle/limit findings. HTML and PDF
  second extraction uses a separate implementation where available; unavailable
  second extraction stays visible. Unsupported references are retained.
* A2: two blind source-only atomic-claim inventories before any candidate is
  exposed; actor/action/modality/conditions/exceptions/time/evidence fields;
  per-unit disposition and quote validation; independent candidate-versus-source
  entailment with three-way labels and exact evidence. Candidate claims cannot
  define their own coverage denominator. Deterministic cue checks are warnings,
  not a substitute for entailment or a completeness proof.
* A3: a bounded structured-argument profile with ordinary premises, assumptions,
  exceptions, strict/defeasible inference, premise/conclusion/inference attacks,
  supported explicit preferences, critical questions, and case operators whose
  preconditions and provenance are checked. This is an adaptation of ASPIC+,
  Carneades and case-theory construction, not their full combined semantics.
* A4: stage-tagged issues and repair actions; changed upstream inputs invalidate
  downstream checks; explicit compliance/prohibition output normalization;
  conditional derived Boolean fact mappings; separate original Java evaluation
  on mapped snapshots. No implicit fact equivalence or changed UNKNOWN semantics.
* A5: source challenges and controls, dependency/method/fact-schema fingerprints,
  bounded one-shot monitor ticks suitable for scheduling, affected-control replay,
  immutable successor results, retry and cadence settings. No background daemon
  or deployment is assumed. Missed/overdue monitoring remains observable.
* A6: deterministic evidence-action priorities with documented cost units,
  per-issue and total limits, no repeat of identical failed evidence actions,
  source/scope/assumption/version-bound answer reuse, deduplicated discriminating
  questions, retained uncertainty on exhaustion. Estimates are scheduling
  heuristics, not learned correctness probabilities.

## Default and assumption audit

| Choice | Provenance/status | Rationale | Failure mode and early diagnostic |
|---|---|---|---|
| Current Codex route, fresh contexts | Existing authorization; baseline | No new provider cost or private data | Correlated omissions; unanimous-defect challenge |
| Two inventories plus candidate check | Monograph; hypothesis | Separate denominator from candidate | Shared model bias; lexical cues and independent extraction, retained disagreement |
| Bounded structured profile | Local engineering adaptation | Inspectable inference and attacks | Paper semantics overstated; explicit unsupported profiles and reference examples |
| Max 2 semantic repairs per issue | Convenience, tested bound | Prevent infinite repeated reading | Premature exhaustion; report residual evidence and test exact counting |
| 20 documents / 3 reference levels | Convenience, configurable bound | Bounded acquisition | Missing deeper context remains a finding, not a clean result |
| Daily monitoring, 2 attempts per revision | Illustrative local policy | Testable scheduler interface | Missed update; overdue status, fake-clock tests; bank SLA not established |
| Common Boolean mapping domain | Existing type/UNKNOWN semantics | Exhaustive small finite comparisons | Domain explosion; resource limit, no finite-sample equivalence claim |
| Live increment at most 36 calls | Remaining 59/100 authorization | Bounded engineering pilot with repairs | Service/schema failure; count before dispatch, retain response, no refund |

## Phases, commands, stop and repair rules

The fixed runner is `.venv/bin/python scripts/run_interpretation_assurance_plan.py`.
Its `refresh PHASE`, `review PHASE --note FILE`, `run PHASE`, `repair PHASE --note
FILE` and `status` operations preserve exact input hashes and append-only attempts.
Every accepted phase refreshes its successor. A failed phase requires an executed
repair note and fresh review; initially four failed attempts, then explicit plan
revision. Review is author review, not represented as independent adjudication.

The A7 four-attempt stop fired on structured-criticism target encoding. The
explicit revision `docs/implementation/interpretation-round3/a7-attack-repair-plan.md`
permits two further attempts (six total failed attempts maximum), with precise
attack diagnostics and mandatory exact prior-response replay. The 77-reservation
increment ceiling and all semantic acceptance criteria are unchanged.

After attempt 06, the six-attempt stop fired on source-fidelity output schema
errors. The user's continuation and explicit `a7-schema-repair-plan.md` revision
allow one additional attempt (seven total), with field-level validation feedback
and an explicit response schema. The increment ceiling is now 93 reservations
(52 since the original 41); the authorized total remains 100. Semantic and
challenge acceptance criteria remain unchanged. Earlier limits above describe
the initial plan and its first revision, not permission to reset failed attempts.

Attempt 07 completed the 90-row matrix but its final criticism stream disconnected.
An earlier valid response matches that exact request and schema. The explicit
`a7-retained-completion-plan.md` revision permits one further attempt (eight total)
with zero live dispatch for 23EC46 and only the missing independent 24EC16 and
challenge work. The 93/100 ceiling is unchanged. Independent checks continue after
a source failure; final acceptance still requires all of them to pass.

| Phase | Acceptance command within runner | Required result |
|---|---|---|
| A0 | pytest tests/assurance/test_master.py | Frozen baseline and stale-review/repair protections |
| A1 | pytest tests/assurance/test_sources.py | Missing units/annexes, parser disagreement, bounded closure, official acquisition |
| A2 | pytest tests/assurance/test_semantics.py | Blind inventories, three-way evidence validation, shared omission, clean controls |
| A3 | pytest tests/assurance/test_arguments.py | Typed attacks, critical questions, provenance, preferences, cycles and case moves |
| A4 | pytest tests/assurance/test_repair.py | Stage invalidation, bounded repairs and normalized original Java witnesses |
| A5 | pytest tests/assurance/test_monitor.py tests/assurance/test_challenges.py | Future-change replay, immutable history, challenges and harmless controls |
| A6 | pytest tests/assurance | Integrated CLI, budgets, evidence reuse, actionable uncertainty and all component tests |
| A7 | pytest tests; scripts/interpretation_assurance_pilot.py | Full regression, retained-source/live engineering pilot and manifests |

Artifacts: `artifacts/interpretation/round3/PHASE/attempt-NN/`; baseline under
`.localresources/interpretation-round3/`. Every manifest records commit and actual
inputs, Python/JDK, CPU-only operation, commands, elapsed time, data hashes,
applicable seed (deterministic tests; provider seed unavailable), and result paths.
Live reads use public retained documents only, no bank records. No consultancy,
external messages, new provider, funding commitment or deployment is authorized.

Pre-mortem: testing only implementation-shaped fixtures could miss real omissions;
therefore retain a live source-first pilot and public-source challenges, while
explicitly withholding natural-error-rate claims. Escalating every case can look
safe; clean controls and unresolved-question counts prevent that being called
useful automation. A new input class or unsupported semantic construct must remain
unresolved. Model retry success does not erase the failed attempt.

Review verdict: PASS WITH LIMITS for implementing and evaluating this bounded
profile. No material unrecorded default remains for starting A0/A1; later phase
reviews must bind actual implementation and refine these contracts if needed.
