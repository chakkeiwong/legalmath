# Legal interpretation program

[Master program](../../plans/legal-interpretation-master-program.md) ·
[Phase plans](../../plans/legal-interpretation-program/README.md) ·
[Program review](program-review.md) · [Claude handoff](claude-handoff.md)

The documentation checkpoint is committed as `00c1b4bb`.
All nine product phases remain planned. The documentation and its retained
review inputs can be checked with:

```text
.venv/bin/python scripts/legal_interpretation_ops.py verify-handoff
```

Execution setup is now installed. Use the
[exact commands and editing procedure](execution/README.md) and
[setup review](execution/setup-review.md) before implementing the phases.
The [setup result](execution/result.json) records the actual policy checks,
30 passing tool tests and observed session behavior. No old provider budget is
transferred into this program.

From this worktree use `.venv/bin/python scripts/legal_interpretation_ops.py`
as the fixed prefix, `login: false`, and trusted execution while the known WSL
sandbox mount error persists. Keep payloads out of shell text: the `edit`
action receives guarded JSON via stdin. Tests, builds and inspection use the
fixed actions in the operator guide. Never substitute the old assurance
`ops-run` command for this program.
