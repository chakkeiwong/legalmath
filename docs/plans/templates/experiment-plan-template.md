# Experiment plan: <name>

Use for a real comparative/research run, not as ceremony for a compile check.

## Intent and evidence contract

- Question and target population/workload:
- Candidate/mechanism and expected failure:
- Exact baseline(s), source/data parity and preparation costs:
- Primary success/promotion criterion:
- Promotion veto and threshold:
- Continuation veto (conditions invalidating the investigation):
- Repair trigger and next discriminating check:
- Explanatory diagnostics only:
- What must not be concluded:

## Assumptions and design

For each material default give provenance, justification, misleading-failure
mode, smallest diagnostic and status (hypothesis/baseline/reviewed choice).
Specify corpus/version, independent task families, development/held-out split,
reviewer assignments, seeds where relevant, budgets and stop conditions.
Define material/critical errors before outcomes are inspected. Explain the
uncertainty method and what insufficient independent observations would imply.

## Skeptical audit and pre-mortem

Check wrong baselines, proxies promoted to success criteria, hidden defaults,
leakage, unequal information, stale context, environment mismatch and outputs
that cannot answer the question. State how the run could pass while misleading
us and how implementation/tuning failures differ from evidence against the idea.
Record PASS or repairs needed before execution.

## Execution and evidence

- Exact commands/environment/toolchain:
- CPU/GPU policy (no GPU needed for ordinary LegalMath checks):
- Small focused diagnostic before the full run:
- Planned input/output artifact paths and hashes:
- Plan/result/reset-memo paths:
- Reproducibility and resume procedure:
