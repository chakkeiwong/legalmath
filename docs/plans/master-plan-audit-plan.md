# Master implementation plan: preparation and skeptical audit

Date: 22 September 2026. The user clarified that “master program” means a
master implementation plan, not application code. Requested outputs: development
readiness assessment, executable master plan, thorough review and a Claude
review handoff. Writing the handoff does not claim that Claude has reviewed it.

## Pre-execution audit

The wrong baseline would be treating the SPI-Demo1 JAR or 35 structural fixture
checks as the complete product. The comparator is the v0.3 proposal, normative
contracts and actual checked files. The main question is whether an implementing
agent can identify its next task, dependencies, inputs, output, failures and
completion evidence without inventing safety-critical semantics or scope.

Inspect the proposal, contracts, schemas, SQL, fixture checker and demonstrated
compiler. Check dependency cycles, missing contracts, semantic/hash disagreements,
stale schedule, implicit legal approvals, host races and unimplemented acceptance
commands. Preserve the proposal PDF and original Java verification record; any
fresh Java replay runs in an isolated temporary copy. No private data, network
model calls, package installation, GPU work or production connection is required.

Audit finding already confirmed: the backlog's final staffing paragraph retains
three weeks despite the required Java work and four-week allocation elsewhere.
Potential hash/release dependency issues require inspection before fixing the
written contract. An engineering blocker for a later milestone does not block
isolated environment/source work; separate entry readiness, stage completion and
production release. Do not turn a pending Claude review into user permission.

## Evidence contract

Pass for this planning task means a coherent dependency graph; stable task and
acceptance IDs; current-versus-planned commands distinguished; scoped completion
criteria; reviewed assumptions and tracked gaps; a preserved source snapshot;
and a review packet that asks Claude to challenge conclusions and supply concrete
counterexamples. Identity mismatches, circular evidence hashes, dependency cycles
or unverifiable claims veto readiness of the affected stage and require repair.

Run the existing specification checker and one isolated replay of the Java demo
to confirm the starting evidence. These are deterministic engineering checks,
not a performance or effectiveness experiment. Targeted static/probe checks may
confirm contract gaps. Tests are not evidence of legal approval, full-language
implementation, universal compiler correctness or user comprehension.

Deliver `docs/implementation/master-plan.md`, a machine-readable task graph,
`docs/reviews/master-plan-review.md`, `docs/reviews/claude-review-handoff.md` and
an evidence manifest. Synchronize directly affected entry points/contracts.
Do not implement the application or rewrite the manuscript during this task.

## Review order and stop conditions

1. Establish the actual inventory and preserve hashes.
2. Close engineering ambiguities necessary for the master plan; record legal and
   bank-specific choices as explicit later blockers with owners.
3. Write stages, tasks, interfaces, evidence checks and continuation conditions.
4. Audit the plan against adversarial cases and the actual repository.
5. Fix confirmed contradictions, check links/task graph/contract consistency,
   and prepare a bounded, self-contained review request for Claude.

Stop dependent work for a corrupted baseline, contradictory unresolved semantics,
or a change needing confidential bank interfaces. Continue independent planning
and specify the exact missing decision. A failed implementation candidate calls
for a repair task, not abandonment of the product direction.
