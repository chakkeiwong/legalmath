# Approval diagnosis and operating rule

The excessive prompts had three observed causes. Some execution occurred before
the reusable rule was installed. Some invocations changed the interpreter/path
or used a shell wrapper, so they no longer matched the approved literal prefix.
The filesystem sandbox also fails on the host mount at `/mnt/wslg/distro`, so
even ordinary reads sometimes need trusted execution. An unquoted URL containing
`?` caused an additional avoidable pattern/approval mismatch.

The dedicated rule is installed at
`/home/chakwong/.codex/rules/legalmath-prospectus-evidence.rules`. It matches:

```
.venv/bin/python scripts/run_prospectus_evidence_master.py
```

Use that exact command from this worktree with trusted execution for every
declared action. Quote URL and regular-expression arguments; do not wrap the
command in `bash -c`, change it to `python3`, or prefix shell assignments.
The program itself fixes and validates actions, campaign paths, approved public
hosts, budgets and subprocesses. It accepts no arbitrary shell argument.

The installed rule has 13 positive action tests and four mismatch tests. These
tests establish this dedicated rule's matching behaviour, not every platform
policy. `authorize` refreshed the approval snapshot after the two exact publisher
hosts were added. Future policy changes require review before execution; platform
restrictions can still request approval. The scoped rule does not disable them.

The immediate cause was incomplete execution setup and inconsistent command
forms. A written request for fewer prompts is not itself a persisted matcher.
The runner, installed rule and tested command form now provide that setup.
