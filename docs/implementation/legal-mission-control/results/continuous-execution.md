# Dependency-aware execution: repair and actual result

12 October 2026, Hong Kong time (11 October UTC). The user's requested execution
repair has been implemented, reviewed and exercised against the actual work graph.
The master plan is `docs/plans/legal-mission-continuous-execution.md`; its reviewed
v2 and v3 corrections are retained separately. The machine definition currently
registered in `mission.json` is `execution-v3.json`. Earlier definitions, task
attempts, failures and reports remain available.

The principal cause of the earlier start/stop pattern was work selection:
completion of a small engineering package ended the session even when source
analysis, resource review or recovery could proceed. The replacement represents
success prerequisites (`requires`), completion prerequisites (`after`), successful
alternatives (`any_success`) and failure-triggered work (`when_failed`) explicitly.
The local runner drains ready commands with up to two independent workers and
declared write locks. Reasoning tasks are explicit supervisor work; an empty
command queue with ready reasoning tasks is WORK_REMAINS, not completion.

Attempts are persisted before work, results are hashed, and changed inputs or
prerequisites invalidate only affected results. A failed worker cannot cancel an
independent worker. Setup failures, missing command results, an unexpected worker
exception and a failed mission refresh have separate retained outcomes. A valid
committed task result is not overwritten because refresh failed. Settlement
remains unavailable while a task or synchronization is active. Reload does not
reset attempts or repeat completed tasks: a finished orphan's valid receipt can
be adopted, a live process retains its reservation, and an ended process without
a valid result needs a reviewed retry.

This is durable resumption and correct dependency scheduling, not a promise
that an IDE crash leaves an AI reasoning process running. The active supervisor
must resume ready agent tasks. Commands use fixed argv without a shell, and
protected evidence and the original absolute deadline remain global controls.

## Actual execution

Nine of the thirteen final graph items succeeded. Three qualification items
retain failed outcomes, and the matched-assessment item is dependency-blocked.
No ready or running task remains. The consolidated report is
`artifacts/legal-mission-control/2026-10-11/continuous-execution/execution-report/attempt-2/execution-report.md`.

| Work | Result | Evidence and limit |
|---|---|---|
| Controller repair/review | Succeeded, two bounded attempts | 66 scheduler/mission tests; independent failures, recovery, reload, stale results, active invalid work, process identity and synchronization exercised |
| P10/evidence, P14, Gatecoin source contracts | Succeeded | Four original questions, 23 exact excerpts and 16 conditional counterexamples; executor source analysis, not legal closure |
| Full source restart | Succeeded, one bounded attempt | Both readers and downstream stages rebuild in a new revision; immutable predecessor, source/target identity and finite restart count tested |
| Product regression | Succeeded independently during live work | 52 focused tests; actual scripted complete restart, not live legal validation |
| Resource design | Succeeded with recorded setup correction | Exact source and finite four-call response qualification; validated setting is 300 seconds per call |
| First qualification | Failed before dispatch | Unsupported 600-second setting; zero calls; declared recovery proceeded |
| First real proposal/review | Failed answer acceptance | Two calls; missing P14 footnote rival and relevant 23EC52 incorporation reasoning |
| Bounded corrected proposal/review | Failed answer acceptance | Two further calls; targeted omissions fixed but confidence-scope rival and the case's P11 applicability premise still missing |
| Matched product/tool assessment | Blocked by failed prerequisite | No accepted answer method, complete formal populations or qualified live whole-route reserve |
| Consolidated report | Succeeded using completion dependencies | Report ran despite failed qualification; all unfinished work remains explicit |

The initially unplanned setup failure would have consumed the only semantic
repair slot. The reviewed v3 correction explicitly preserved the failures and
used the two previously unspent qualification calls for one substantive repair.
This was not a renewed allowance or a repeated unchanged request. The correction
also fails its source screen, so no further call is admitted under this finite
program. This exhausted qualification scope is distinct from the still-unused
global call balance.

The review results and source-grounded corrections are in
`results/continuous-response-qualification.md` and
`results/answer-correction-failure.md`. The latter explains why source quotation
checks and correct case IDs did not catch loss of a cross-question rival or an
unstated applicability premise. These failures reject the current candidate,
not the legal target, harness or research direction. No unsupported pass was
substituted to unblock the dependent tool trial.

## What remains and how to resume

The live whole-route guard is still deliberately local-only. Complete candidate
and claim populations, a coherent response method preserving the identified
rivals and case premises, equal-arm stage/restart resources and actual
source-reviewed tool effects remain unestablished. The original P10, P14,
evidence and Gatecoin questions, 46 obligations and 35 readings remain open.
All six selected tools still lack full answer-level evaluation. BM25 produced
two actual source-bound retrievals; neither was supplied to the recorded model
answers, so their effect is unmeasured. Five structural tools lack validated
formal candidates or an effective argument graph for these prose answers.
Historical fixture integration does not supply those missing inputs.

The narrow next substantive question is how to preserve cross-question
source obligations and conditional case-premise mappings in the actual answer
review, including footnote 5's confidence-scope rivals and the distinction between
an unspecified records requirement and P11. A future coherent method needs
review and a finite allocation inside the original authority. It must not simply
replay the exhausted qualification, add administrative phases, silently reset
attempts or remove the live guard. This report itself adds no new live stage.

Resume with the exact repository-root commands required by AGENTS.md, followed
by the dependency status:

```text
.venv/bin/python scripts/legal_mission_control.py check
.venv/bin/python scripts/legal_mission_control.py status
.venv/bin/python scripts/legal_mission_control.py admit
.venv/bin/python scripts/legal_mission_execution.py status
```

`run` drains ready registered commands; ready agent tasks belong to the active
supervisor in that same session. `settle` is the final check. The expected saved
state here is BLOCKED, with no ready/running work and no pending mission sync.
Neither BLOCKED nor completed reporting closes the legal mission.

## Resources and approvals

Aggregate usage is **17/400**: thirteen sealed historical reservations plus four
new calls. The original thirteen-call ledger has not changed; the final successor
ledger retains all seventeen entries. The deadline is **12 October 2026 at
04:28:01 UTC (12:28:01 Hong Kong time)**. The nine prior engineering detours
remain counted, with three engineering attempts in this graph. No runtime,
phase rename or directory resets those totals. Test suites overlap and are not
added into a legal progress score.

Three narrow live command prefixes were approved during execution. The extra
prompts resulted from separate versioned entrypoints introduced to preserve
the failed executors. That was avoidable workflow friction. The final fixed
dispatcher prefix is `.venv/bin/python scripts/legal_mission_live_action.py execute`,
currently accepting only the sealed `answer-correction` action. A saved prefix
is not permission for arbitrary new actions or a guarantee that host review
will never be required. Local reads, edits and tests needed no new approval.

The strongest remaining implementation risk is that reasoning-task continuation
still relies on the active agent honoring the graph; the command runner does not
perform open-ended legal reasoning. The most important substantive limitation
is the absence of a qualified actual answer and matched tool effect. Both are
explicit, so neither can silently become a successful completion verdict.
