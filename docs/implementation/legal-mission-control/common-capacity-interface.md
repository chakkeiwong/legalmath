# Common capacity interface

The reviewed implementation uses `common-stage-capacity.v1` on the active
legal-integration route. The governing plan is
`docs/plans/legal-common-capacity-interface-2026-10-20.md`; the implementation,
test report, replay and deployment receipts are retained under
`artifacts/legal-mission-control/2026-10-20/common-capacity-interface/`.
Production installation is established by `adoption.json` plus the registered
master and its verification; staging tests alone do not establish installation.

## Entry points

`BoundedProduct` accepts `common_capacity_profile`, with the exact version above,
and an optional authenticated `capacity_checkpoint`. `PhasedProduct`
passes these options through. The product attaches one `CapacityManager` to
its dispatch and route. Existing calls to `dispatch.call` and `phase.execute`
therefore enter the same capacity layer; callers need not implement another
split/retry loop. Live leaves still pass existing per-call phase admission.

The manager exposes `call`, `phase`, `run` and `native`. Model operations retain
their original request, JSON schema and semantic validator. Capacity handling
returns the existing validated/failed result structure and never converts a
schema-valid result into an accepted legal answer. Native operations receive
one complete assembled packet, whose memory footprint is checked before use.

`capacity_policy.STAGES` registers all 20 current model operations. Each entry
defines its semantic adapter, output token and byte budgets, finite call/depth
and elapsed-time bounds, and the reason for partitioning or remaining atomic.
Unknown stages or profile versions fail closed. The selected profile remains
opt-in so historical sealed runs retain their exact original behavior.

## Partition and validation rules

| Adapter | Safe unit | Required shared context and completion check |
|---|---|---|
| `records` | Independent source or metadata observation | Exact record population; later dependency review remains required |
| `warrants` | Independent review issue | Whole answer, review, accounts and source context in every piece; original whole-result validator |
| `grouped-review` | Independent assigned decision | Complete shared answer and sources; exact assignments and rebased identifiers |
| `source-note` | Partial requirement reading | All originals and all partial readings in a joint bridge, followed by original validation |
| `atomic` | Whole judgment | Full context and output must fit; report the precise remainder otherwise |

Candidates, argument graphs, complete answers, corrections and matched effect
comparisons stay atomic. Combining independently solved graphs could change
attacks and preferences, so native tools never receive an unverified graph union.
A bridge that cannot fit is an explicit capacity limitation.

Only input/output capacity failures can trigger subdivision. Semantic failures
remain substantive failures. Service errors remain service errors. Admission,
deadline, exhausted calls and uncertain reservations do not buy extra samples.
Independent ordinary failures leave other independent pieces executable; their
dependent assembly remains incomplete. Per-operation limits are 31 leaves,
depth four and 14,400 seconds, subordinate to the existing global authority.

## Persistence and reuse

Each logical request records its contract, exact request/schema identities,
pieces, results and assembled outcome. Shared candidate and criticism ownership
is recorded before transport. A RESERVED request is uncertain and cannot be
redispatched by another arm. Successful retained answers, reviews and native
results are reused only under matching identities. Successful master owners
remain the exact comparison inputs. Changed successful answers are refused.

The retained P14 criticism has a separate, authenticated size-only revalidation.
Its original failure remains intact. Revalidation passes the original schema
and semantic validator under the reviewed larger budget; it still reports
16 unresolved questions.

## Adding a stage

1. Register its exact task name and reviewed budget in `capacity_policy.STAGES`.
2. Choose an existing adapter only if its independence and shared-context rules
   hold. Otherwise start atomic or implement a reviewed adapter in
   `capacity_adapters.py` with exact membership and assembly checks.
3. Keep production calls on `dispatch.call` or `phase.execute`; do not call a
   provider directly. Native kinds require registration in `capacity_policy.NATIVE`.
4. Test direct and oversized requests, missing/duplicate assignments, remote
   exceptions, whole-result vetoes, interrupted reservations, changed identity
   and exact restart reuse. Include a real request replay for the stage.
5. Review and bind the changed implementation through the current master.
   Stage coverage and passing local tests do not establish legal acceptance
   or provider reliability.

## Evidence

The sealed regression report has 174 passing tests. All four retained candidate
requests fit their current input envelopes. The real P14 baseline replay reuses
16 completed calls without changing its answer and exposes the still-missing
351 source-review requests and two pieces of one warrant. The offline provider
intentionally refuses those missing calls; replay does not count them as passed.
The separate handover guard suite has four tests and does not change the sealed
174-test implementation report.

A separate source audit finds all 20 registered task names in product call
sites. Active direct provider calls are confined to the common dispatch
transport. Older dossier/staged-investigation routes also exist in this
repository; they are outside the selected bounded master route and retain
their previous implementation. The claim of complete wiring applies to the
active master, not every historical alternative in the repository.
