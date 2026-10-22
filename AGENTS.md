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
