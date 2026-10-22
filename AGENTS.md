# Planning and continuation for this repository

For every new or materially revised execution plan, follow
`docs/plans/standing-continuation-policy.md` and use
`docs/plans/templates/execution-plan-template.md` or an equivalent explicit
dependency map. Record which items need success, which only need completion,
which are independent, and which bounded recovery runs after failure. After each
checkpoint, persist the result, refresh the ready set and continue authorized
independent work; a failed branch does not end the plan. Distinguish branch
blockers from global authority, deadline or budget vetoes. End only on verified
completion or when no authorized ready work remains and exact blockers are
reported. This rule applies to the separate prospectus work too; its substantive
program and permissions remain separate. It does not authorize subagents or
additional external calls.

# Legal interpretation mission

For work on the legal-interpretation product, use
`docs/plans/legal-interpretation-mission-control.md` as the current work-selection
program and `docs/implementation/legal-mission-control/mission.json` as the
current task register. These instructions do not govern the separate prospectus
project or unrelated maintenance.

The current integration graph is mission.json's `integration_master`, governed
by `docs/plans/legal-integration-master-2026-10-13.md`. The older
`execution_program` is historical evidence. Use
`.venv-context/bin/python scripts/legal_integration_master.py status`
to find ready work and `run` to drain independent registered commands. Use its
fixed `live` action only with the existing checked grant and current bindings. Execute
ready agent items in the same work session. A completed package is a checkpoint,
not a reason to end the turn. A failed item blocks only its success dependants;
continue independent items and declared recovery. Inspect the master frontier before ending:
`WORK_REMAINS` means continue, while `BLOCKED` needs exact unresolved prerequisites.
An expired global deadline or invalid global authority remains a real stop.
Keep attempts and old results across reloads; never silently redispatch a running
worker. The runner adopts a verified completed orphan result or records an
interruption when both recorded processes are dead. Agent work resumes from its
retained notes and current reservation.

Before nontrivial implementation, experiments or continued legal-interpretation
execution, run these exact local commands from the repository root:

```text
.venv/bin/python scripts/legal_mission_control.py check
.venv/bin/python scripts/legal_mission_control.py status
.venv/bin/python scripts/legal_mission_control.py admit
```

Read the admitted task and its retained substantive dossier before acting. If a
check refuses admission, resolve the named problem or record a reviewed program
revision. Do not choose an easier historical runner merely because it can run.
Existing historical programs remain evidence/verification contexts; never rewrite
their sealed sources, grants or results to pass a current check.

After each work package or repair, retain its actual result, update the mission
history and next-task reason, and run `legal_mission_control.py refresh` with the
same interpreter prefix. The refresh validates the recorded transition; it does
not invent the next plan. No new phase, renamed task or new directory resets the
cumulative detour bound or historical call/repair/deadline limits.

Task completion, test totals and tool invocation counts are not legal progress.
An engineering detour needs a reproduced blocker of an admitted substantive task,
one bounded attempt and an explicit return to that task. An unsuccessful repair
does not authorize an endless series of new repair programs. A justified change
to that work-selection bound needs an explicit reviewed revision.

Keep the four original questions, 46 original obligations and 35 original
readings visible. Fulfillment cannot be replaced by duty activation. Missing
client facts do not stop conditional source analysis. A tool is fully evaluated
only when its real product use, downstream consideration, failure cases and
matched effect on the answer are evidenced. Deferred and conceptual tools remain
explicitly separate from integrated tools.

These checks enforce process constraints, not legal truth or host security. They
grant no new live-call allowance, external permission or completion verdict.

# Prospectus execution authority

For prospectus work in this worktree, the sole work-selection authority is
`docs/implementation/prospectus-execution-authority/program.json` and its
accepted history, operated by `scripts/prospectus_control.py`. Its reviewed
design is `docs/plans/prospectus-execution-authority-2026-10-12.md`.

Before nontrivial prospectus implementation or continuation, run from this
worktree root:

```text
.venv/bin/python -m scripts.prospectus_control check
.venv/bin/python -m scripts.prospectus_control status
.venv/bin/python -m scripts.prospectus_control admit
```

Read the admitted dossier and its retained source evidence before acting.
Use `run` for the admitted registered worker. For agent work, retain the actual
result in its admitted attempt and use `record --attempt <retained-path>`;
recording alone does not imply acceptance. Add a reviewed task-specific
validator before closing a task that has no automatic acceptance rule. Use
`revise --proposal <file> --review <file>` for reviewed task refinement;
ordinary revisions cannot drop obligations or reset the original budget.
Run `refresh` after recording each work package. Continue the next independent
ready task when there is no true blocker. A checkpoint is not a stop condition.

Before ending an execution turn, inspect current authority status. A ready or
admitted task requires continuation in the same turn, not a final message that
only names the next task. `AGENT_WORK_REQUIRED` hands execution to the current
agent; it is not a blocker. Use commentary for package summaries and keep tool
calls short without shortening the authorized work. If a task is blocked,
retain its actual blocker and continue independent ready work. Partial results
need the reviewed continuation described below; absence of an automatic
handler alone does not justify stopping. End execution only when the requested
scope is complete, the user requests a stop, a real platform limit intervenes,
or every authorized route is blocked by a documented condition. Before a
blocked handoff, record why no independent work remains and the exact next
action/input required. This instruction governs the agent's turn; the local
Python dispatcher does not keep an agent running after its final reply.

Partial `RESULT_RECORDED` work resumes through a reviewed refinement of the
same task, retaining its budget and immutable evidence. Supplied external
files may be bound by a reviewed `external_evidence` path/hash list, with each
path also in the task inputs; admission permits review, never automatic human
acceptance. See the authority's `OPERATIONS.md` for these transitions.

After an interruption, use `resume` before dispatching another job. Full worker
logs and results stay in the admitted attempt; use one-second tool yields and
small status outputs. Never start a duplicate merely because the stream ended.

The older closure/controller programs are delegated verification tools and
historical evidence. Their PASS receipts do not select substantive work or
close missing source, automatic-capability or independent-review requirements.
Preserve all sealed attempts. Generated current views are under the execution
authority directory; older reset/next-program documents are historical inputs.

This authority is specific to prospectuses. It does not replace the separate
legal-interpretation mission, grant new host/network permissions, authorize
external messages or turn supplied development readings into independent
legal acceptance. Preserve unrelated work in the main worktree.
