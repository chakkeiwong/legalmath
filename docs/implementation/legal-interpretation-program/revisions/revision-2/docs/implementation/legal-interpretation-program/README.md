# Legal interpretation program

[Master program](../../plans/legal-interpretation-master-program.md) ·
[Phase plans](../../plans/legal-interpretation-program/README.md) ·
[Program review](program-review.md) · [Claude review](claude-review.md) ·
[Revision-2 response](claude-review-response.md)

Revision 1's documentation checkpoint is committed as `00c1b4bb`.
Revision 2 incorporates the review findings in the master and affected phase plans;
all nine product phases remain planned. Check both revisions with:

```text
python3 -m scripts.check_legal_interpretation_revision
```

The [revision manifest](revision-2-manifest.json) binds amended files separately
and maps superseded originals into `revisions/revision-1/`. Original handoff
hashes and Claude's review remain unchanged. The old runner's `verify-handoff`
checks live paths only and now reports the expected edited paths; use the
revision checker to reconstruct all 693 original bindings and verify revision 2.
Historical validation/results describe their own revisions. See the response for
the exact monograph/source-note errata still pending.

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
