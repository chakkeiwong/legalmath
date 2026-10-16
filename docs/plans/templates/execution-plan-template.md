# Execution plan: <objective>

Use for a new multi-step plan. For a single-step plan, state the sole task,
its prerequisite and stop condition; omit the empty graph table. Keep the
substantive or research question separate from the scheduling mechanics.

## Objective and authority

- Intended result and evidence that would establish it:
- Baseline, protected inputs and known open questions:
- Scope, permissions, environment, shared budget/deadline and prior attempts:
- What a successful command or proxy check would **not** establish:

## Dependency graph

Use stable task IDs. Write `none` explicitly, and do not use `after` when a
downstream task actually needs a successful result. List alternatives only when
each is sufficient for the same input. Mark recovery as finite and specific.

| ID | Result and evidence receipt | Requires success | After completion | Any successful alternative | Runs after failure | Executor and write/budget resources | Attempt limit |
|---|---|---|---|---|---|---|---|
| <task> | <output/path/pass condition> | <IDs or none> | <IDs or none> | <IDs or none> | <IDs or none> | <agent/command; locks> | <number> |

- Independent ready items at admission:
- Tasks that can safely run concurrently, and resource conflicts that serialize others:
- Earliest diagnostic for missing/cyclic dependencies, stale inputs or a false success:

## Continuation, recovery and stop rules

- Branch failure: which success dependents block, and which independent or
  completion-only items still run:
- Declared recovery: trigger, retained failure evidence, finite attempt/budget,
  verification and return to the original objective:
- Shared continuation vetoes: invalid authority, deadline, global budget,
  corrupted common inputs, or other exact conditions:
- After each item: persist outcome, evidence and attempts; refresh ready set;
  continue all authorized ready items in the same session:
- After interruption: identify live workers, adopt valid completed results,
  and avoid duplicate external calls:
- `COMPLETE` requires verified required results. `BLOCKED` requires no authorized
  ready work and an exact list of unmet prerequisites. A checkpoint is neither.

## Skeptical pre-execution review

Check wrong baseline, proxy promotion, missing stop conditions, unfair
comparisons, hidden assumptions, stale context, environment mismatch, commands
whose artifacts cannot answer the question, circular dependencies, shared
resource conflicts and a branch failure mistakenly treated as a global veto.
Record PASS with reasons or repair the plan before execution.

## Execution and review record

- Exact commands or agent actions and result locations:
- Per-task result, blocked prerequisite, resource use and next ready set:
- Final review of dependency behavior and substantive outcome, kept separate:
