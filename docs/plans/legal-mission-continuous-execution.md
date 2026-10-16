# Continuous execution of the legal mission

11 October 2026. This reviewed revision implements the user's instruction to
replace repeated start/stop execution with dependency-aware continuation. It
supersedes the work-selection policy of the consumed one-off repair packages;
their sources, grants, results and spent attempts remain unchanged. The parent
mission is still `product-contribution`, with four original questions, 46
obligations, 35 readings and six selected tools whose answer contribution is open.

## Question and evidence contract

The execution question is whether a failed, interrupted or unavailable item
blocks only work that depends on its successful result, while independent work
continues and completed work survives a restart. The baseline is the current
single-task mission validator and nine spent enabling detours. The candidate is
a persisted acyclic task graph with explicit success, completion and recovery
dependencies, task receipts, bounded attempts and a supervisor that drains ready
work. Engineering acceptance requires adversarial graph tests and an actual
multi-branch run. An empty runnable list alone cannot establish completion.

The substantive question remains whether source-supported answers preserve P10
fulfillment, P14 attachment, evidential sufficiency and Gatecoin's case-specific
limits, and what each selected tool contributes to those answers. Scheduler,
test and invocation counts cannot answer that question. Source acceptance sheets
are executor-reviewed conditional analyses, not independent legal adjudication.

Corrupt global authority, an invalid/cyclic graph, changed protected evidence or
the original overall deadline can veto all dependent execution. A model failure,
missing source authority, exhausted task reserve, invalid task output or failed
candidate is a branch blocker. It cannot veto unrelated tasks. Promotion and
execution are separate: failure to establish legal correctness leaves a question
open but allows conditional analysis, failure evaluation and planned recovery.

## Reviewed work graph

The machine register is `docs/implementation/legal-mission-control/execution.json`.
Every task names success dependencies, optional completion dependencies, any
failure-triggered recovery, execution mode, output, verification requirement,
write-resource locks, priority and a finite attempt limit. Codex performs the
registered reasoning/editing tasks; the runner executes registered local commands.
An `AGENT_WORK_REQUIRED` result is a handoff to the active supervisor within the
same work session, never mission completion or a request for another user prompt.

| Item | Needs successful result from | Other condition | Deliverable |
|---|---|---|---|
| Program implementation/review | None | This pre-execution review | Tested persistent dependency supervisor and compatibility check |
| P10/evidence answer contract | None | Retained exact sources | Conditional answer, contrary readings, acceptance counterexamples |
| P14 answer contract | None | Retained exact sources | Attachment alternatives and request/no-request controls |
| Gatecoin answer contract | None | Retained exact sources | Scoped propositions, scenario-seven conflict and transfer controls |
| Source-repair restart | None | Preserved question-first stop evidence | Fresh complete investigation after a bound concern; no stale reviews/search |
| Resource/qualification design | None | Original ledger and deadline | Prospective ceilings, finite qualification reservation and live eligibility decision |
| Source contract verification | All three source contracts | None | Exact original identities, cited retained support and failure cases checked |
| Product regression | Source-repair restart | None | Focused original-question and full-restart regression results |
| Response qualification | Resource design and source contract verification | Valid live authority and enough time | Actual response evidence or concrete branch blocker |
| Qualification recovery | Resource design and source contract verification | Response qualification fails | One reviewed corrective attempt using retained failure, or external blocker |
| Matched product assessment | Product regression, source contract verification, accepted qualification or recovery | Complete route resources must fit | Matched answers and per-tool findings, or exact unmet prerequisites |
| Consolidated result | All leaves have a result or blocker | Completion dependencies, not success dependencies | Remaining work and all blockers, without declaring product completion |

Independent source tasks, source-repair work and resource design may run in
parallel when their write resources differ. Model calls sharing one allowance
must reserve atomically. Agent editing tasks remain under the active supervisor;
the program will not launch unreviewed agents or arbitrary shell commands.

## Execution and refresh rules

1. Validate the graph, original evidence and authority before dispatch. Preserve
   the old ledger and snapshot the current dirty source baseline. Register this
   revision once. The user's current instruction authorizes its listed local
   repairs and continuation, not unlimited calls or a renewed deadline.
2. Select every ready node whose prerequisites are successful. Schedule
   independent command nodes together, honoring declared resource conflicts.
   On failure, persist the failure, activate its declared recovery if any, and
   immediately select other ready nodes. A task waits only for its own inputs.
3. Persist a start reservation before work and a hashed result receipt after it.
   Never rerun a completed node implicitly. An interrupted started node becomes
   `INTERRUPTED`; an explicit reviewed retry consumes its next existing attempt.
   Restarting a process or renaming a task cannot reset attempts or history.
4. After each package, record the actual result and mission history, refresh the
   ready set, and continue. Source repairs invalidate dependent reviews/search
   and answers; unrelated source-analysis receipts remain usable. Invalid
   output is a task failure even when a command returns zero.
5. End execution only when all task deliverables have verified results, the
   overall deadline applies, or every remaining branch has an evidenced blocker
   and no ready agent/command/recovery action exists. Report `BLOCKED` separately
   from `COMPLETE`. A planned review is work to do, never an automatic stop.

## Resources and authority

The historical grant remains 400 provider calls, 13 spent at this revision's
admission, and expires 12 October 2026 04:28:01 UTC. Nine prior enabling detours
remain counted. This graph admits two named engineering packages (supervisor and
source restart), each with at most two implementation/verification attempts;
actual attempts are retained. This replaces the arbitrary one-package-per-user-
turn selection rule only for this explicit finite program. Further retries
require evidence-based revision inside the remaining original bounds, not a
silent reset. No new research direction or external communication is included.

The old 23-call baseline-core balance is a constraint on that sealed method.
The resource task must determine a successor allocation within the remaining
global allowance; it cannot rewrite the old grant or infer that all 387 unused
calls fit the clock. A small response qualification can be planned before a
complete future inventory exists, using prospective ceilings. Full matched
execution must separately pass actual population, source, output, tool-action
and time checks. Live use needs a bound method and aggregate allowance; a caller
boolean is insufficient. If qualification cannot yet be admitted, the task
records the exact missing implementation/evidence and other branches continue.

Local commands use `.venv/bin/python scripts/legal_mission_execution.py` with
fixed subcommands. Commands contain no shell substitution or arbitrary shell
payload. Existing sandboxed file permission covers local changes. If a concrete
live command needs host/network approval, request its narrow reusable command
prefix once after its exact payload and call cap are reviewable. No broad Python
or shell approval is requested.

## Default audit and pre-mortem

| Choice | Provenance/status | Failure risk | Earliest check |
|---|---|---|---|
| Explicit success versus completion edges | User's dependency requirement | Review skipped after failure, or dependent consumes invalid result | Failed-parent/independent-child/recovery tests |
| Two command workers | Convenience ceiling, no performance claim | Conflicting writes or duplicate reservations | Resource-lock and simultaneous-start tests |
| Two attempts for the two named engineering items | Finite reviewed local bound | Retry loop disguised by new directory | Persisted counters and interrupted-resume test |
| Existing source dossiers | Retained baseline, legally conditional | Old prose silently treated as settled law | Inspect exact excerpts and retain contrary/unknown conditions |
| Existing 400-call grant and clock | Explicit user authorization | Stage reserve mistaken for total shortage or renewed grant | Frozen ledger plus aggregate successor arithmetic |
| Full claim/candidate matrix | Inherited method, unqualified at full population | Multiplicative cost prevents any complete answer | Resource design before live full-route dispatch |

The worst false success is a drained command queue with unfinished reasoning
tasks labelled complete. Tests must reject that state. Another is reusing a
successful receipt after its prerequisite changes; input/output hashes and
dependency receipts must invalidate that branch. A third is repeating tests and
reports while no source answer or qualification advances; the graph includes
specific substantive outputs and its final report lists unperformed work.

Review records are kept separately from legal acceptance. The post-repair audit
must exercise a failed branch, an independent successful branch, a successful
recovery, interrupted execution, changed evidence, expired authority, concurrent
resource conflict, and restart without duplicate work. After that audit the
active agent must execute the graph, not merely announce it.
