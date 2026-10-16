# Standing dependency-aware execution policy

This policy applies to new or materially revised execution plans throughout this
repository, including legal interpretation and the separate prospectus work. It
does not rewrite sealed plans, results, grants, or the current legal-mission task
graph. The global Codex instruction is a short reminder; this file and the
[execution-plan template](templates/execution-plan-template.md) provide the
reviewable details for this repository.

For every plan, state whether it has one actionable item or several. A multi-item
plan must name each result and distinguish success dependencies, completion-only
dependencies, alternatives, and failure-triggered recovery. Name tasks that can
proceed independently, their shared write or budget resources, finite attempt
limits, and the evidence that completes each task. A linear plan can state that
there are no independent branches; it still needs its actual prerequisites and
stop condition. Parallelizable work may be scheduled concurrently when safe, or
advanced sequentially in the same work session when concurrency is unavailable.
The policy does not authorize spawning agents, external calls, or extra budget.

Before execution, check the graph for missing or circular dependencies, stale
inputs, conflicting writes, and tasks whose outputs cannot answer the objective.
Separate a branch failure from a shared continuation veto such as invalid
authority, an expired deadline, a depleted global allowance, or corrupted common
evidence. After every result, failure, or interruption, retain the result and
attempt count, recompute the ready set, and continue all authorized independent
ready work and declared recovery. Finishing one package or review is a checkpoint,
not an end-of-turn reason. A failed item blocks its success dependents only;
completion-only reviews can still report that failure. A new phase or renamed
task cannot reset a spent attempt or shared limit.

On restart, verify saved state and any recorded worker before dispatching again;
do not duplicate an external call. End a plan as complete only when all required
results are verified. If no authorized work remains ready, report the exact
blocked prerequisites and distinguish `BLOCKED` from `COMPLETE`. A persistent
plan helps resume after an IDE or session crash; it does not make an agent run
autonomously while disconnected.

## Skeptical review of this installation

The current baseline is a legal-mission-specific controller and instruction;
other plans and the reusable experiment template do not require dependency-aware
continuation. The proposed change is a global Codex reminder, a repository rule,
and reusable templates. It is not a claim that a generic template enforces
execution or that a product failure has been fixed. The smallest check is to
inspect the installed instructions and templates, then verify the existing
legal-mission admission still passes. We will not alter historical graphs or
measure legal progress by this policy edit.

Audit result: **PASS for installation**. The plan preserves the actual legal
baseline and global limits, does not promote a scheduler check into a product
criterion, and has explicit stop conditions. Risks are that future agents may
ignore prose instructions, a project may need a specialized runner, and a shared
resource may make nominally independent tasks unsafe to run concurrently. The
template requires the resource and restart checks, and future execution reviews
must verify behavior on the actual plan. This installation is policy and
scaffolding, not proof of future compliance.
