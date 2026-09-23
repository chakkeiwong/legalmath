# Result: <task or experiment>

State the concrete result first. Separate engineering behavior, legal
interpretation and empirical effectiveness. Mark unexecuted checks NOT_RUN.

## Execution manifest

Plan/task ID; source/contract/code version or hashes; Git commit if available;
actual command; environment/toolchain; input/corpus version; seed if applicable;
CPU/GPU status; wall time; output paths/hashes; failures and retained reproducer.
Use N/A only when a field does not apply.

## Decision

| Decision | Primary criterion | Veto evidence | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| <retain/repair/reject> | <observed result> | <pass/failure/not checked> | <limit> | <task> | <scope> |

For stochastic or human comparisons also record:

| Inference question | Status and evidence |
| --- | --- |
| Hard veto screen | |
| Statistically supported ranking | |
| Descriptive-only differences | |
| Default readiness | |
| Additional evidence needed | |

Do not infer a ranking from a few cases, one seed or favorable means without the
predeclared uncertainty evidence. A candidate failure can trigger its planned
repair; identify whether the target/harness was invalid or only the candidate failed.

## Red-team note

Strongest alternative explanation; evidence that would overturn the conclusion;
weakest part of the evidence; concrete next check. Preserve all cases including
errors, abstentions, unresolved interpretations and failed runs.
