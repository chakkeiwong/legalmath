# Fixed execution commands for the legal interpretation program

Use these direct commands from `/home/chakwong/python/legalmath`.
The tool invocation should set `login: false`; keep the interpreter and script
spelling exactly as shown. Do not prepend environment assignments, `cd`,
`timeout`, `bash -c`, pipes or redirections. The runner sets CPU mode,
subprocess limits and output paths internally.

| Purpose | Exact command |
|---|---|
| Status and recent attempts | `.venv/bin/python scripts/legal_interpretation_ops.py status` |
| Verify frozen review inputs | `.venv/bin/python scripts/legal_interpretation_ops.py verify-handoff` |
| Check proposed rules | `.venv/bin/python scripts/legal_interpretation_ops.py policy-check` |
| Check installed rules | `.venv/bin/python scripts/legal_interpretation_ops.py policy-check --installed` |
| Test execution tools | `.venv/bin/python scripts/legal_interpretation_ops.py self-test` |
| Phase tests after implementation | `.venv/bin/python scripts/legal_interpretation_ops.py phase-tests P0` (P0–P8) |
| Narrow existing regressions | `.venv/bin/python scripts/legal_interpretation_ops.py regression contracts` (contracts, sources, integration, translation) |
| Rebuild canonical documents | `.venv/bin/python scripts/legal_interpretation_ops.py build-docs` |
| List files | `.venv/bin/python scripts/legal_interpretation_ops.py files src/legalmath/interpretation` |
| Read a bounded range | `.venv/bin/python scripts/legal_interpretation_ops.py read docs/plans/legal-interpretation-master-program.md 1 80` |
| Literal search | `.venv/bin/python scripts/legal_interpretation_ops.py search request docs/plans/legal-interpretation-program` |
| Inspect JSON field | `.venv/bin/python scripts/legal_interpretation_ops.py json docs/implementation/legal-interpretation-program/phase-manifest.json status` |

These are local operations, not a dispatcher that implements P0–P8.
A missing test returns NOT_IMPLEMENTED and a nonzero exit code. A passed test
does not mark a phase complete. Read each phase, implement its substantive
repair, run its declared tests and the relevant regression group, record its
evidence, and rewrite/review the successor plan before proceeding. The guarded
editor supports those authorized local changes without modifying protected
agent/Git metadata:

```text
.venv/bin/python scripts/edit_workspace_files.py /tmp/edits.json
```

For agent execution, prefer `.venv/bin/python scripts/legal_interpretation_ops.py edit`
with a persistent stdin session. After READY_FOR_GUARDED_EDIT_JSON, send one JSON
line through the session input tool. The runner disables terminal echo and the
short terminal line limit, then passes the parsed data to the guarded editor.
Large file content therefore never enters the shell command or its prefix matcher.
The original editor also accepts `--json` with one correctly shell-quoted JSON
argument, but complex shell payloads can still cause approval mismatches. The helper validates the whole batch, checks old
content/hash preconditions and confines writes to the worktree and temporary
directories. No extra permission is created for external writes.

Long commands create an attempt directory under
`artifacts/legal-interpretation-program/operations/`, write a RUNNING record
before starting, save output to `output.log`, and retain PASS, FAIL, TIMEOUT or
INTERRUPTED. The process is independent of a dropped tool output stream; inspect
its record before rerunning. A RUNNING record or an existing PID is never a
completion receipt. Hard host termination may leave RUNNING, requiring
reconciliation. Tests and builds time out after five minutes (tool self-tests:
two minutes). A justified longer check needs a reviewed timeout change.

## One installation approval

After the runner tests and proposed-rule checks pass, the installer command is:

```text
.venv/bin/python scripts/legal_interpretation_ops.py install-rules
```

It writes only the dedicated file
`/home/chakwong/.codex/rules/legalmath-legal-interpretation-program.rules`.
The installer is intentionally absent from the persistent rules: one explicit
protected-path approval installs all declared operations together. Existing
rules and global sandbox settings remain intact. Changed existing content is
a conflict, not permission to overwrite another rule.

The grouped approval covers local inspection, fixed CPU test groups, document
builds, durable attempt logs and the existing guarded editor. It grants no
provider calls, Claude dispatch, dependency downloads, source crawling, remote
publication or numerical allowance. These need concrete scope if later required.
The old assurance and prospectus runners are separate programs.

## Observed limits

The existing sandbox fails at startup on the host mount `/mnt/wslg/distro`.
Use trusted execution for an exact approved command when that failure applies.
A dedicated allow rule does not repair the mount or disable managed policy.
The installed CLI can check literal rule matching, but cannot prove a running
VS Code session has reloaded its rules. Record the actual live-session result.
If the client keeps asking for an unchanged approved command, reload the session
after saving work and recheck; do not accumulate broad interpreter/shell rules.

Official OpenAI rules/security pages and their Markdown endpoints returned
HTTP 403 during this setup. The concrete rule syntax and decisions are checked
with the installed `codex execpolicy check`, rather than assuming current
documentation behavior. References:
https://developers.openai.com/codex/rules
and https://developers.openai.com/codex/security.
