# Continue until completion or a documented blocker

The user has authorized execution of the prospectus program. Routine checkpoints
are progress reports, not new authorization requests. The current authority is
program.json and its accepted history; the active-stage-queue.json file is only
a recoverable dispatch cursor for an already admitted package. It grants no task,
budget, host or external permission.

The checked local failure mode is premature turn termination: recording a small
package, seeing next_task:null for a partial result, and ending before reviewing
its justified continuation. Authority.refresh validates the recorded program;
it cannot invent legal analysis or keep an agent executing after a final reply.
Changing an allow-list does not repair this control-flow mistake. Existing
AGENTS.md already requires same-turn continuation.

For each admitted package: dispatch one bounded stage, retain its tool-session
identity, poll that session, inspect the actual result, then dispatch its ready
successor. One-second command yields and bounded output keep the conversation
responsive; a short tool wait must not shrink the authorized scope. Started
markers and missing results indicate unresolved execution, never permission to
launch a duplicate. After a reload, inspect the retained cursor and stage files,
resume the existing session where available, and resolve ambiguous process state
before dispatch. A stale cursor cannot override a newer started/result marker.

After the package: seal once, record, refresh, inspect status and continue ready
work. RESULT_RECORDED is partial evidence. If the automatic queue is empty,
review remaining source obligations, concrete repairs and independent tasks
under the original cumulative budgets. Revise through the existing authority
only when a concrete skeptical audit and evidence contract justify continuation.
Never reset history or extend a failed unchanged run merely to stay busy.

Use the active program's bound continuation map to make that review concrete:

    .venv/bin/python -m scripts.prospectus_continuation

This read-only inspector reports local review routes, specific missing inputs,
incomplete predecessors and spent admission allowances. REVIEW_REQUIRED means
the empty dispatch queue does not support a whole-program blocked handoff.
It grants no admission or retry. Its full map is referenced by program.json;
the reviewed design is docs/plans/prospectus-thorough-closure-2026-10-14.md.
It cannot keep an agent alive after a final reply or diagnose a stream failure.

The current staged interpretation demonstrates a bounded response to a real
timeout. Attempt003 retains six successful comparisons and exit124 on the final
omission. Attempt004 retains exact open-P3 equivalence, changed-argument rejection
controls and the successful omission consumer. The timeout remains a failure;
there is no evidence identifying a historical stream-disconnection cause.

End an execution turn only for completed requested scope, user stop, a real
platform limit, or a documented blocking condition covering every authorized
route. A final handoff must identify what is incomplete, why independent work
cannot continue, and the exact missing input or next action. A ready/admitted
task or a routine review checkpoint is not such a blocker.
