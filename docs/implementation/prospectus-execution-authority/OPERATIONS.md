# Operating the prospectus authority

Run commands from `/home/chakwong/python/legalmath/.worktrees/bond-gap-closure`.
The command module pins imports to this worktree. The editable interpreter
alone can otherwise resolve the main worktree's package.

```text
.venv/bin/python -m scripts.prospectus_control check
.venv/bin/python -m scripts.prospectus_control status
.venv/bin/python -m scripts.prospectus_control admit
```

Read the selected dossier and retained evidence. For a registered worker, run:

```text
.venv/bin/python -m scripts.prospectus_control run
```

Use a one-second tool yield, retain its tool-session ID, then poll that session
with bounded output. The command intentionally stays alive with its child;
there is no detached background job that can be killed when the tool returns.
Complete logs live in the attempt. Use `resume` after an interruption before
starting any other worker. A zero command exit is not sufficient evidence of
task acceptance: read current state and the retained result.

Agent work uses the admitted attempt for its reviewed work plan, actual
commands, input/method/environment identities, source evidence, positive and
adverse controls, result note and `outputs.json`. The output manifest must
include `result.json`. Record and refresh with:

```text
.venv/bin/python -m scripts.prospectus_control record --attempt <admitted-relative-path>
.venv/bin/python -m scripts.prospectus_control refresh
```

`RESULT_RECORDED` is partial work, not completion. To continue it, retain a
reviewed next-work dossier and a new immutable program proposal that refines
the same task. Preserve the original task ID, obligations, acceptance
requirements and budget lineage. Supply the active program hash, skeptical
audit and evidence contract in the review, then run:

```text
.venv/bin/python -m scripts.prospectus_control revise --proposal <proposal.json> --review <review.json>
```

Changed task specifications become ready under the original remaining
admission budget. An unchanged partial result does not automatically loop;
editing controller code alone does not authorize another partial package.
Corrupted retained evidence requires repair and cannot be made retryable by
renaming a task. A task-specific acceptance validator remains necessary to
complete an agent task.

When genuine external files are available, keep the external task's handler
and independence requirements. A reviewed revision may add
`external_evidence: [{"path": "...", "sha256": "..."}]`; each path must also
appear in that task's `inputs`. Missing or changed files remain waiting. Bound
files make the task ready for substantive review, not accepted. Do not put
credentials or invented reviewer attestations in the register.

`STATUS.md`, `RESET.md` and `NEXT-PROGRAM.md` are generated views, so edit the
program through reviewed revision rather than hand-editing those views. The
older closure programs are validation evidence and delegated workers. Current
R0–R8 PASS receipts do not select or close outstanding substantive tasks.

The authority grants no host permissions. Ordinary authorized worktree and
temporary-file edits use the sandbox. Network, installation, protected-path
and external-message restrictions continue to apply. No global allow-list or
sandbox change was needed for this implementation.

When dispatch is empty, run the bound read-only continuation inspector:

    .venv/bin/python -m scripts.prospectus_continuation

REVIEW_REQUIRED identifies local continuation design or preparation, including
tasks whose admission allowance is spent. Follow the listed substantive action
and the existing revise/admit rules; the report creates no new allowance.
Use --full for the per-task acceptance, missing-input and dependency map.
An optional --output must name a new JSON file inside the authority's
continuation-reviews directory. The report is a projection, not another program.
