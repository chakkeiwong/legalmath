# Prospectus evidence master

Executed result: 36 issues, 18 qualified positives, 16 qualified negatives,
two unresolved. The regression suite passes 797 tests. All E0-E8 phases are
complete with qualifications; no transaction permission or complete legal
accuracy is established.

- [Results PDF](phases/E8/attempt-001/results.pdf)
- [Readable results](phases/E8/attempt-001/results.md)
- [Case/source index](phases/E8/attempt-001/CASE-INDEX.md)
- [Recovery memo and commands](RESET.md)
- [Final review](delivery-review.md)
- [Four-case challenge and causal repair](challenge-review.md)
- [Next evidence program](next-evidence-program.md)
- [Why approval prompts repeated](approval-friction.md)

From the isolated `bond-gap-closure` worktree, use the installed exact prefix:

```
.venv/bin/python scripts/run_prospectus_evidence_master.py status
.venv/bin/python scripts/run_prospectus_evidence_master.py run
.venv/bin/python scripts/run_prospectus_evidence_master.py verify
```

The active method is candidate-004. Both post-PDF repair cycles are consumed.
All four additional cases are now exposed; the historical frozen challenge and
rejected witnesses remain available. Further semantic development requires a
new reviewed protocol, with its own resource bounds and fresh-source selection.
