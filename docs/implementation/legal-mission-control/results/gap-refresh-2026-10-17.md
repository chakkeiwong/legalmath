# Same-master frontier review, 17 October

The product is incomplete. P10's latest stop is a local receipt-construction
defect, distinct from intermittent service failures. A production replay with
provider completion and reservation forbidden reproduced the stop at detail-10.
Slot 2190 contains a complete 3,005-token response, already explicitly reviewed
under the optional 4,096-token wire limit. The reconstructed request has the
same complete source records and all other fields, but four records have moved.
The response schema agrees. The saved-child traversal changed the record order;
the completed-receipt branch did not select its historical contract as the
ordinary successful-account branch does. This is our implementation defect.

The repair selects the authenticated completed contract only after checking
unique record IDs, equality of every full record and equality of every other
base-request field. It restores the historical order and explicit reviewed
output profile. Normal receipt authentication, decoded limits, account checks
and citations still apply. The original rejected dispatch remains rejected;
reassessment creates no provider sample. The before/after replay and semantic
mutation controls are required before adoption.

HTTP 499 alone does not establish a safely ended request. The opt-in requires an
explicit terminal failed turn and no model output. Completed output, partial
output, unknown dispatch, invalid request, refusal, authentication, quota and
billing failures remain excluded. The retry uses the exact request and schema,
the existing delayed-service ledger and its already-spent replacement. It adds
no calls, replacements or time. The one-hour first wait and subsequent two-hour
waits are the user's scheduling choice; longer explicit server instructions
must be honored and every wait and dispatch must fit the unchanged grant.

## Dependency and closure review

| Gap and root cause | Required action and evidence | Dependencies and present authority |
| --- | --- | --- |
| P10 completed receipt rejected after reconstruction | Reproduce the actual failure, prove the order-only difference, select the historical contract and revalidate the response | Local proof precedes live continuation. Allocate the last of the twenty extra owner attempts to P10, increasing its ceiling from seven to eight; retain all seven failures. |
| Evidence preparation still pending | Reuse its retained source accounts, execute its next missing work and preserve the actual answer/source review | Independent of P10, P14 and Gatecoin success. It retains one unused attempt. |
| Ended HTTP 499 and intermittent Sol failures | Persist terminal receipts, exact identity and next UTC time; wait and retry through the same worker | Shared service dependency only. Keep gpt-6.1-sol, 2,369 prior calls, the 8,100 ceiling and the existing 1/24 delayed replacements. |
| P14 invalid request at slot 2341 | Compare its exact wire contract with accepted neighboring contracts and inspect the provider diagnostic; retain the offending parameter as unknown unless evidence identifies it | Independent local diagnosis can continue. HTTP status and schema validity do not identify the invalid parameter. P14's ten owner attempts are exhausted; no extra attempt is created here. |
| P14 interrupted work | Preserve 36 accounts, 20 of 90 first-level syntheses, all five sent failures and 65 unsent requests; classify each failure independently | A complete authenticated continuation and an authorized owner allocation are prerequisites. A 499 classifier does not resolve the invalid request or create that allocation. |
| Gatecoin explicit refusal | Preserve the 34 accounts and 116 of 117 syntheses; retain the actual refusal and document the resulting answer limitation | No request transformation, splitting or rerouting to defeat the refusal. Thirteen owner attempts are exhausted. Other questions remain independent. |
| Dated source applicability and missing facts | Review actor, product, date and authoritative treatment against the delivered sources; continue conditional analysis of all four questions | Missing client facts limit conclusions. They do not block conditional source analysis. The prepared source notes are inputs, not complete answers. |
| Baseline and tool answers | Complete acquisition and substantive source/account review for each eligible question, then execute its full answer consumers | Only the affected question depends on its acquisition. Avoid treating local transport, capacity or schema checks as legal acceptance. |
| Six tool evaluations and 24 matched effects | Use the retained question/tool specifications; inspect actual tool execution, delivery, downstream consideration, failures and matched answer changes | Each pair requires its own same-source baseline and tool answer. Report help, no observed benefit, harm, limited support or inconclusive evidence. Zero of six tools is fully evaluated at this baseline. |
| Final product and original acceptance | Review four questions, 46 obligations, 35 readings and every tool disposition; retain unresolved legal ambiguity explicitly | Dependent on actual substantive evidence. Counts, retries, graph results and tests cannot close these obligations. |

## Skeptical audit

The frozen comparator is the settled state at detour 52 and 2,369 calls, not an
earlier successful fixture. The production replay tests the real constructor;
manually supplying the historical request would miss this defect. Permutation
repair requires complete content equality and cannot conceal a source change.
The HTTP 499 tests include partial output, unknown termination and disallowed
terminal errors. Retry success would establish availability for that request,
not legal accuracy or tool benefit. The machine amendment must reject hidden
changes to tasks, repair IDs, spent calls, service scope or deadlines.

This is one reviewed consolidation under the user's current instruction,
recorded as detour 53. It does not allocate R11 or renew the exhausted R1–R10
allowance. It uses the previously unallocated twentieth extra task attempt.
P14 and Gatecoin remain visibly limited by their own blockers and exhausted
owner allocations. No new phase name resets those limits.

Pre-execution verdict: PASS for the bounded local repair, proof and registration
described here; live execution requires the actual after replay, adversarial
checks, staged mission/provider validation and current binding to pass. Resolve
only the exact P10 receipt veto supported by that proof, retaining its original
history. Continue every other ready branch under the same task graph. Stop the
affected branch for unknown dispatch, changed semantics, corrupt evidence,
exhausted allowance or expired clocks. A transient failure schedules a wait;
it does not justify declaring the tools impossible to integrate.

Results, exact commands, environment, manifest and actual worker settlement are
retained under `artifacts/legal-mission-control/2026-10-17/gap-refresh/`.

## Registration-validator repair

The first registration attempt stopped before transaction creation and made no
provider call. The exact failure was in nested historical validation: the
delayed-service predecessor projected only its own aliases, while the enclosing
frontier review had archived two additional implementation files. Its historical
program was therefore compared with current-path references even though the
bytes were unchanged.

Nested validation now composes the enclosing and predecessor archive aliases by
`(path, SHA-256)` and rejects conflicting aliases. The delayed-service caller
uses this composed map; the prior delayed-service authority and task graph stay
unchanged. The focused test proves that inherited aliases survive composition
and that a conflicting alias is refused. This is a registration-integrity repair
within the same reviewed package, with no new task attempt, call, replacement,
repair allowance or deadline.

The subsequent registration check exposed one omitted archive alias: the new
composition regression test changed a test file cited by the sealed
delayed-service result. The frontier projection now includes that file's
already-frozen predecessor bytes as well as its current tested bytes. No sealed
result or test is rewritten. Pre-execution audit: this resolves a stale
historical reference, preserves exact SHA-256 authentication, and cannot change
owner attempts, task dependencies or service authority. The staged real
registration remains the acceptance check for this integrity repair; passing
fixture tests alone cannot establish that registration works.
