# Comparison archive: commit scope and portability

8 October 2026. The later user instruction to commit and push authorizes this
checkpoint separately from the finished program's execution budget. T0–T4 remain
complete with incomplete live evidence. This checkpoint preserves the finite
comparison implementation, plan, review records, and execution receipts.

The staged scope includes the previously omitted `scripts/legal_tool_recovery.py`
helper. Earlier unfinished interpretation, assurance, and prospectus changes
remain outside this checkpoint. Downloaded runtimes and packages under
`.localresources/legal-tool-comparison/` and ephemeral locks are excluded.

## Skeptical audit before commit

The original packaging assumption was wrong: retaining T3 receipts does not make
the terminal integration test portable. That test also validates downloaded
archives, licences, wheels, and earlier source receipts. A fresh checkout lacks
those inputs. The narrow repair is a collection guard in
`tests/tooling/conftest.py`: only the terminal archive test skips when either
external archive directory is absent. When both directories exist, the original
test runs and missing or changed referenced files still fail validation. No
reference checker, scientific result, or historical test file is changed.

The audit passes for this bounded checkpoint. The comparator remains the recorded
local baseline; no new tool comparison is being run. Test success establishes
packaging behavior only. It cannot promote legal accuracy or close obligations.
Historical hashes and unrelated work must remain intact; a mismatch or unexpected
staged path blocks the commit. Push must be a normal fast-forward, with remote
advancement checked before publication. No new provider call or program phase is
part of this task.

## Archive prerequisites

`status` can read the committed terminal state. Full `verify` and the terminal
integration test need the original local archive at the recorded paths:

- `.localresources/legal-tool-comparison/`, including the pinned archives,
  licence files, and wheels listed in T4 `audit-references.json`.
- `artifacts/legal-interpretation-program/`, including the P0 source packet,
  the two Gatecoin source responses, and the S4/follow-up baseline receipts.
- The earlier follow-up decision at
  `docs/implementation/legal-interpretation-program/follow-up/final-decision.md`.

The exact paths and hashes are preserved in T0 `result.json` and T4
`audit-references.json`. Restoring directories alone is insufficient: verification
checks their referenced bytes. Full re-execution additionally depends on the
earlier local interpretation implementation, including
`legalmath.interpretation.semantics.arguments`, which is outside this checkpoint.
The guarded editor mentioned in the execution notes is another existing local
operations dependency. This commit is an implementation and evidence archive;
standalone product execution has not been established.

Run focused checks directly with
`.venv/bin/python -m pytest -q -rs tests/tooling/test_legal_tool_program.py`.
Use `CUDA_VISIBLE_DEVICES=-1` for deliberate CPU-only checks. The original
runner's `check` action rewrites `checks/tests.log` and `checks/tests.json`, so it
must not be used to refresh the historical, hash-bound verification record.

Eight existing blank lines at EOF are retained: five method snapshots, the T4
report, the current component script, and the historical test file. The ordinary
`git diff --cached --check` reports these; they are accepted for byte preservation.
No other whitespace exception is authorized.

## Validation completed for this checkpoint

The current workspace run completed all ten focused checks in 0.40 seconds. It
did not invoke the runner's `check` action and did not rewrite the historical
`checks/tests.log` or `checks/tests.json`.

A temporary checkout containing only the staged files completed with nine passes
and one explicit skip. The skip named both missing archive directories. A second
run with empty archive directories caused the terminal test to
fail on its first missing referenced file, rather than skipping. This preserves
the distinction between unavailable prerequisites and incomplete or changed
prerequisites.

The staged review retains 221 files and excludes locks, bytecode, and local
downloads. The prior credential-pattern scan found no matches.
`git diff --cached --check` reports only the eight documented
historical EOF blank-line findings. The final commit and normal fast-forward push
are the remaining checkpoint actions.
