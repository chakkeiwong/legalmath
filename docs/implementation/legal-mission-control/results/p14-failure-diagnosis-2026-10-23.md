# P14 failed-review diagnosis and local repair candidate

P14 attempt 4 ended on 23 October at 00:57:55 Hong Kong time with its answer
retained and review open. The 17 failed original groups and 52 failed repairs
are historical execution counts, not 69 distinct unresolved legal problems.
The worker subsequently ended at 02:23:32 with its service replacement reserve
exhausted. This diagnosis made no provider calls and changed no bound source,
historical result, grant or attempt.

## What failed

| Population | Exact cause | Count |
| --- | --- | ---: |
| Original groups | Invalid response schema | 9 |
| Original groups | Missing or unassigned rationale | 5 |
| Original groups | Numbered assertion without document/proposition binding | 3 |
| Repair calls | Shared service circuit already open | 37 |
| Repair calls | Service replacement reserve exhausted | 1 |
| Repair calls | Invalid response schema | 9 |
| Repair calls | Foreign assertion prose path or document | 3 |
| Repair calls | Numbered assertion without binding | 1 |
| Repair calls | Missing or unassigned rationale | 1 |
| Subsequent context bridges | Shared service circuit already open | 503 |

Thus 38 of the 52 repair failures concern service or recovery allowance; 14
concern response structure or citation integrity. The 503 bridge refusals are
not 503 failed provider calls. The exact ledger cross-check is in
`artifacts/legal-mission-control/2026-10-23/p14-diagnosis/repair-queue.json`.

The 17 failed original groups assigned 408 items. Of those, 63 valid individual
reviews were salvaged and 294 subsequently validated in repair. These categories
must not be counted again as unresolved group failures. Across all 1,751 initial
assignments, 1,699 structurally validated and 52 failed. The validated decisions
comprise 1,002 ACCEPT, 672 UNRESOLVED and 25 REJECT. A structurally valid unresolved
or adverse decision remains substantive work.

## Reproduced implementation defects

1. **Request/response assignment mismatch.** Every one of 415 saved group/repair
   contracts shows short request IDs such as `r1` but original opaque IDs as
   response object keys, without an explicit delivered mapping. Some retained
   responses explicitly report that they cannot associate those keys with the
   assigned items. This is a real contract defect; it does not prove that every
   malformed response has the same cause.
2. **Conflicting single-item repair scope.** A one-target repair keeps the
   original batch's assignments and instruction to review every assignment,
   although its schema permits only one target and one rationale. Full context
   should remain available, with required decisions explicitly limited to the
   selected target. Nested review structure, rationale membership and
   decision-relative citation paths also need precise instructions.
3. **Outage converted into failed product work.** The dispatcher reserves a
   logical call before the provider checks the shared circuit. Capacity and
   context loops then keep walking the remaining work, recording refusals as
   permanent failed reviews. A known shared outage is a missing provider
   prerequisite. It must pause provider work while preserving settled results,
   original attempts and independent local work.
4. **Saved-binding reload instability.** Sorted JSON persistence changes
   dictionary traversal order, which changes generated required-field arrays
   and hash aliases. All 415 inspected bindings differ when reconstructed from
   sorted JSON using the original code. This is a separate resume risk; it is
   not the recorded explanation of the 17 original failures.

The apparent 3,000-token instruction is already rewritten by the capacity
profile. It was investigated and is not a confirmed cause. No larger token
allocation is needed for the inspected candidate review requests.

## Local candidate and verification

The isolated checkout is `/tmp/legalmath-p14-repair-20261023`, branch
`fix/p14-review-contract-2026-10-23`, based on `a093e062a`. The durable candidate
snapshot, patch, source hashes and test runner are under
`artifacts/legal-mission-control/2026-10-23/p14-diagnosis/`.

Two explicit options default off: `explicit-review-assignment-contract.v1` and
`defer-unstarted-provider-work.v1`. The first supplies an exact target mapping,
corrects repair scope and makes new bindings stable across canonical JSON
reloads. The second checks service availability after retained-result reuse but
before a new dispatch reservation. Deferral propagates through capacity,
phases, context reviews and the supervisor. A paused owner retains its attempt;
authenticated service recovery releases it without inventing another attempt.
Independent ready tasks continue. Actual failed calls stay failed, uncertain
dispatch remains a veto, and elapsed-time/deadline limits are not reset.

**203 focused tests passed.** They cover real reference transport, single-target
repairs, old checkpoint reuse, malformed outputs, unsupported verdicts and
citations, mid-batch outage, exact result reuse, same-attempt supervisor resume,
independent work and uncertain dispatch. CPU devices were used; GPU devices were
intentionally hidden. One test of a production receipt initially could not find
that untracked evidence in the isolated checkout. The test runner explicitly
directed that read-only receipt check to the original evidence root; it passed.

**415/415 saved bindings passed the local replay audit.** The old unselected
behavior matches the unchanged baseline implementation. The candidate preserves
all decoded context and response validators, supplies the exact target mapping,
and survives sorted JSON reload. Maximum measured product-visible input was
125,285 bytes and 30,936 local tokens, within the existing 250,000-byte /
70,000-token limits. Hidden provider framing and actual model behavior remain
untested. These measurements do not establish legal correctness.

## Decision and remaining prerequisites

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Unsupported conclusion |
| --- | --- | --- | --- | --- | --- |
| Diagnosis established | Exact failures counted and code paths reproduced | None for local diagnosis | Some response failures can have multiple causes | Retain census and specific repair queue | All failures have one cause |
| Local candidate passes engineering checks | 203 tests and 415 preserved-context replay checks | No local test failure remains | Live model compliance and deployment migration | Review and bind one continuation to the current master | P14 accepted or tools fully integrated |
| Live continuation not launched | Service reserve 88/88; circuit open | Current recovery allocation exhausted | Provider availability | Review finite recovery allocation within the remaining 4,073 global calls, with existing deadline | More calls guarantee recovery |
| Substantive review remains open | 672 UNRESOLVED and 25 REJECT in initial assembled review | Missing context/adverse evidence remain substantive constraints | Whether additional evidence supports the answer | Resume exact necessary context reviews and warranted corrections | Format repair settles the law |

Deployment must use a reviewed successor binding and explicit checkpoint
import, preserving the 1,699 valid individual decisions and all actual failed
attempts. Do not simply enable the options in the old directories: their
request/phase identities are bound. The proposed queue distinguishes proven
unstarted work from actual responses needing another reviewed repair. P14's
spent owner attempts need explicit allocation before a new attempt; Gatecoin's
retained running reservation needs orphan reconciliation before resumption.
Neither the new profile nor a new directory replenishes allowances.

After service requalification, test one corrected actual malformed assignment
and one context bridge, with the original answer and sources. Stop promotion if
the request cannot be mapped, any exact context changes, membership is invalid,
or citation/verdict checks fail. A substantive UNRESOLVED or REJECT can be a
valid engineering result and must trigger its evidence-dependent next action,
not be relabelled as acceptance. Continue independent authorized work after each
checkpoint and retain the four questions, 46 obligations, 35 readings and
matched tool comparisons.

Post-run skeptical review: **PASS for the local candidate; no live acceptance
claim.** The strongest alternative explanation for remaining malformed outputs
is model noncompliance despite a coherent contract. The weakest evidence is the
absence of a live canary under the new profile. Known service unavailability is
handled, but a circuit that changes after preflight still follows the original
conservative dispatch-failure path. Historical failed rows are deliberately not
rewritten. This is one bounded follow-up candidate in the existing review
package; it records no deployed revision and resets no cumulative detour.
