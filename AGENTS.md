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
