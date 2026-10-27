# Correct service inheritance in the renewed integration window

The October 24 continuation reached the first unsent P14 request, but the
service preflight refused it with `E_AUTHORITY: Service scope changed authority`.
Attempt 6 and its failure remain evidence. Calls are still 4,872 and service
replacements 195. This is an implementation defect in the time amendment,
not evidence of a Sol outage or an adverse legal judgment.

## Root cause and evidence contract

`legal_window_continuation.register` changes the binding review to the new time
review while retaining the existing service scope. It omitted the supported
`phase_service_predecessor` link. `CampaignAllowance.service_scope` therefore
compares the old scope review with the new time review and correctly refuses.
The general allowance check did not exercise this service preflight.

The baseline is the exact registered continuation and its failed sixth P14
attempt. The repair must restore explicit, hash-verified service inheritance,
pass the actual service preflight without a provider call, preserve all old
charges/results, and resume the 50 still-unsent requests. Local success is an
engineering prerequisite, not legal acceptance or proof of model availability.
Any changed grant, scope, predecessor bytes, uncertain reservation, live owner,
or exhausted deadline/budget vetoes deployment. A legal REJECT does not.

## Dependency map and execution

| Item | Success prerequisites | Completion prerequisites | Deliverable / bounded recovery |
|---|---|---|---|
| C0 | None | Failed attempt 6 | Exact failure, unchanged charge census and settled worker evidence |
| C1 | None | None | Candidate inheritance repair and negative tests; independent of worker cleanup |
| C2 | C0, C1 | None | Atomic reviewed registration; resolve only this exact authority veto |
| C3 | C2; existing P14 inputs | None | One continuation attempt 7, preserving attempts 1–6; reuse exact retained responses |
| C4 | C2; each original owner prerequisite | None | Existing Gatecoin reservations; if the old worker finalized an owner with this exact pre-dispatch defect, preserve it and add one corrected continuation only for that owner. Independent acquisition/tool branches do not depend on P14 acceptance |
| C5 | None | Each checkpoint | Retain actual result and refresh the original master frontier |

C3/C4 share the provider/state locks and run sequentially under one durable
supervisor; a branch outcome does not block other owners. This correction stays
inside the current window-continuation package (detour 66). It records one
additional software-recovery attempt per owner finalized by this exact defect, no new calls or replacements, no
deadline change and no reset of any historical allowance. It does not permit
resampling invalid responses. A fresh runtime avoids changing a sealed phase
binding and uses the same authenticated checkpoints; the failed run made no
new dispatches.

## Skeptical review

The first continuation's tests missed the production service preflight. Merely
changing the error text, skipping the authority check, changing the old scope,
or treating a running CPU process as evidence of provider progress would not
answer the question. The new check exercises `service_scope` and
`check_service`, verifies unchanged ledger/circuit/recovery bytes, and tests
wrong grant, scope, predecessor and modified archived bytes. Deployment waits
for verified process death and no reserved request; independent candidate
preparation can continue while checkpoint cleanup finishes.

Audit: PASS for one narrow correction, conditional on local tests and staged
mission/provider/service checks. Existing five-minute retry and capacity choices
remain reviewed inherited settings. No performance optimization or legal
acceptance change is included. Final acceptance still requires the original
four questions, 46 obligations, 35 readings and actual matched tool effects.

The old supervisor also finalized Gatecoin baseline with the identical defect.
Its checkpoint refresh repeatedly validates historical files while holding the
mission lock. Handover may interrupt that CPU-only refresh after acquiring the
state/provider/ledger locks, checking the process identity and absence of child
processes/reserved calls, and confirming that the mission lock belongs to that
same supervisor. Stop it first, reject an atomic write in progress, then end it
and acquire the released mission lock. Preserve all completed results and append
any missing mission-history records during registration. This does not authorize
interrupting a provider request or another process.
