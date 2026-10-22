# Retained acquisition correction, 21 October 2026

The common-capacity planner changed the grouping of source and metadata
observations. The checkpoint loader incorrectly required the new group hashes
to occur in the completed historical acquisition. Gatecoin baseline attempt 2
therefore failed locally with `E_INTEGRITY` before any additional model request,
and the shared veto blocked all live consumers. This is an implementation
defect. The saved readings are present; the exact Sol recovery at slot 3486
had already succeeded.

The correction accepts a new observation batch only when its complete records
occur in one authenticated original parent request with identical non-record
fields, including reader and question scope. It still reconstructs every
original request from the unchanged source store and validates every successful
response. A failed parent requires all recorded recovery children, or the
existing exact-inventory disposition for requirements. Joint dependency reviews
still require their exact original packet hashes. No source, model answer,
failure disposition or acceptance criterion is rewritten.

The actual master `product_route` and `run_product` entry paths pass for P10,
P14, evidence and Gatecoin. Each replay stops after retained acquisition
validation with provider dispatch and phase admission disabled. All use the same
295 retained rows, comprising 235 original requests and 60 recovery requests.
The four current plans contain 550, 515, 553 and 588 packets respectively;
498, 463, 501 and 536 of their independent observation children map to complete
retained parents. These figures describe batching, not legal completeness.
The original 3,486-call ledger is unchanged.

The focused regression passed 71 tests. Controls reject missing records or
readers, changed source/question content, duplicate requests, malformed or
unsettled responses, false completion, incomplete recovery and missing joint
bridges. Registration controls preserve attempts, successful owners, earlier
events and unrelated vetoes. An initial registration test omitted its local
plan fixture; that fixture was corrected. Review also caught an audit-variable
collision with metadata substitutions; it was fixed and all four production
replays were repeated against the final loader. The final replay receipts each
contain the checked parent mappings.

The governed correction is one local package, recorded as detour 61 while
preserving the preceding 60. Gatecoin's failed attempt 2 remains retained; only
its exhausted baseline owner receives one explicitly recorded attempt 3 after
the pre-dispatch defect is repaired. Other original owners retain their existing
unused allocations. The registration resolves only the evidenced batching veto,
preserves successful owners and all call charges, and binds the current source
and program at a settled boundary.

The existing five-minute service retry adapter remains in use. Its old timing
grant is authenticated against exact archived predecessor program/binding
bytes, and its successor verifies the current reviewed program and binding.
The original 8,100-call ceiling, deadline of 24 October 02:19:15 UTC and the
three unused reservations within the 24-replacement reserve remain unchanged.
No additional availability probe is needed.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | What is not concluded |
| --- | --- | --- | --- | --- | --- |
| Accept the local loader correction | All four actual entries validate unchanged retained evidence; 71 focused controls pass | Missing/altered duties and bridges still rejected; no provider calls | Later answer and review behavior | Adopt checked binding, refresh, continue original ready owners | No legal-answer acceptance or tool benefit |
| Resolve the shared batching veto after adoption | Same reproduced defect repaired across every original question | All unrelated integrity/authority checks retained | Further independent product failures | Continue their own ready work and bounded recovery | No total integration completion |

The strongest alternative explanation was actually missing source evidence.
Exact original-request reconstruction and the absence of missing observation or
joint duties reject that explanation for this failure. The weakest part of this
evidence is its deliberate stopping point: it proves acquisition reuse through
the product boundary, while later legal answers, source reviews, dated source
applicability and six matched tool-effect evaluations remain open.

The plan is `docs/plans/legal-retained-acquisition-capacity-repair-2026-10-21.md`;
commands, tests, final source hashes, replay receipts, baseline and adoption
transaction are retained under
`artifacts/legal-mission-control/2026-10-21/retained-acquisition-repair/`.
Inspect that directory's `registration.json`, `worker.json`, `live-result.json`,
`worker-error.json` and `finished.json` for actual adoption and live status.
This review authorizes the checked local correction and bounded continuation;
it does not assert that the live work has completed.
