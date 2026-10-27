# Plan: repair the 23 retained P14 context-response failures

Date: 26 October 2026 (Hong Kong). This is a bounded continuation of the legal integration master. The live dispatcher remains protected; this plan does not restart it, mutate its binding, or add a live call merely because the user has a 20-attempt reserve.

## Objective and evidence contract

The objective is to stop malformed context-disposition responses at the request boundary, prepare one authenticated correction route for mechanically repairable responses, and keep unsupported legal assertions unresolved. The exact saved P14 request, source store, source indexes and raw response are the baseline. The existing canonical citation, source-scope, verdict and delivery-failure validators remain authoritative.

Success requires:

1. Every retained failure is classified by the first failing invariant and by whether the defect is mechanical, mixed, or substantive.
2. Future responses cannot type free source IDs, document hashes, or ineligible dispositions; selectors are bound to the current request.
3. A correction packet can repair only reference/shape fields and must preserve the answer, verdict, reason, issues, support, source gaps, and contrary material unless a separate substantive review is admitted.
4. Missing client facts, external authority, dated applicability, and unsupported numbered propositions remain explicit unresolved work.
5. The original raw responses, attempts, charges and live worker are unchanged.

This is not a claim that a corrected wire response is a correct legal answer. A passing transport test establishes engineering integrity only.

## Current evidence and scope

The saved replay contains 217 complete failed context-disposition calls. The unchanged responses all fail. The exact-reference simulation validates 194 and leaves 23. The current frontier is `WORK_REMAINS`: 41 succeeded, one corpus task blocked, one P14 baseline failed, one Gatecoin baseline failed, 50 pending and one tool owner running (the saved status may move as the live worker progresses). The active worker is PID 2726366 with recorded start identity 20871858; do not dispatch a duplicate.

The 23 are counted as follows:

| Class | Count | Disposition |
|---|---:|---|
| Unknown, stale, malformed or foreign document hash | 12 | Mechanical selector/schema defect; cannot be silently mapped to another document |
| Unavailable source alias or dependency alias used as a source ID | 2 | Mechanical selector/alias defect; offer only request-bound source selectors |
| Client-fact or external-authority need carries source IDs/locators | 4 | Mixed: schema defect plus a genuine missing-fact/authority need; clear identifiers only and preserve unresolved status |
| Ineligible `SUPPLIED_SOURCE` disposition | 1 | Mechanical route/disposition defect; correction may choose only an allowed disposition |
| Numbered prose lacks an exact proposition binding | 4 | Evidence-contract failure; require a genuine binding or substantive review, never invent one |

The first four classes are repairable by a bounded correction route. The last class is not an automatic formatting repair. A correction may only ask for a valid binding, while a fresh answer review handles changed legal prose or an omitted proposition.

## Dependency graph

| ID | Result and receipt | Requires success | Completion-only dependencies | Recovery | Resources and attempt limit |
|---|---|---|---|---|---|
| F0 | State/admission/protected-worker snapshot | none | none | Re-read current process and hashes once | read-only; no provider calls |
| F1 | Failure classifier with 23 exact call IDs and category counts | F0 | none | One parser correction; raw files remain immutable | local CPU; one bounded pass |
| F2 | Request-bound correction contract and schema | F1 | none | One adverse-test repair cycle | isolated `/tmp/legalmath-23-repair`; no live files |
| F3 | Mechanical normalization/correction queue for 19 cases | F2 | F1 | Reject any ambiguous source mapping; retain a packet for later live reassessment | 19 local packets; no provider calls |
| F4 | Substantive-review queue for four missing proposition bindings | F1 | none | Keep each unresolved with exact source paths and reason | four local packets; no provider calls |
| F5 | Replay, adverse tests and capacity check | F2,F3,F4 | none | One test repair cycle, then retain exact failure | local CPU; no network/provider |
| F6 | Durable result, refreshed frontier and activation handoff | F5 | F1–F4 completion | Persist ready set and blockers; do not activate during live worker | repository docs/artifacts only |
| F7 | Controlled live correction qualification | F6 | live worker stopped/checkpointed | At most 20 user-authorized live attempts, only after current grant/binding review | external calls; protected reserve |

F1, F2 and F4 are independent after F0/F1 where stated. F3 waits for the contract. F5 waits for all candidate outputs. F7 is deliberately separate: local success does not authorize changing the live worker.

## Repair design

The request schema will offer exact answer-field selectors, source-only record selectors, and current verified index hashes. It will offer only dispositions valid for each original need and will prohibit record IDs/locators on `CLIENT_FACT` and `EXTERNAL_AUTHORITY`. It will retain a full original need by authenticated need ID rather than matching on shared source anchors.

The correction packet carries the original request hash, response hash, category, exact failure path and immutable answer/source identities. The corrected response must preserve substantive fields and pass the unchanged canonical validator. For a mixed fact/authority defect, clearing an illegal source identifier preserves the missing need; it does not satisfy it. An invalid document hash is never replaced by a nearest hash or a different source. An alias is accepted only if the request's authenticated alias table maps it to a delivered source; otherwise the response goes to reassessment. A missing numbered binding remains unresolved until an exact indexed proposition is selected or the prose is reconsidered under a substantive review.

## Skeptical pre-execution audit

- **Wrong baseline:** use the exact saved request/source store/indexes, not current all-P14 records or a shortened corpus.
- **Proxy risk:** a lower failure count is diagnostic only; it cannot promote a legal answer.
- **Silent legal change:** correction validation freezes verdict/reason/issues/support/source gaps/contrary material. Unknown sources are not nearest-neighbor corrected.
- **Missing stop condition:** stop the local repair at one correction cycle; stop live work on invalid authority, changed binding, exhausted reserve or corrupted common evidence.
- **Dependency risk:** assertion-binding failures remain a separate substantive queue and do not block mechanical packet preparation.
- **Environment risk:** use `.venv-context/bin/python`, which contains the reviewed dependencies; no GPU, network or external model is needed locally.
- **Stale active state:** refresh the master before any activation. The active worker remains the only dispatcher and its attempts/charges are immutable.

Audit disposition: **PASS for isolated repair and classification; HOLD for live activation.** The plan answers the stated repair question without treating schema success as legal acceptance.

## Continuation and stop rules

After each local result, retain its exact input/output hash and refresh the category counts. A failed mechanical packet blocks only its own correction, not the substantive queue or worker monitoring. `F7` may use up to 20 external attempts only after the worker reaches a safe checkpoint and the same-master registration is reviewed. If a source identity or legal proposition remains ambiguous, record `UNRESOLVED` and continue independent work.

The plan is complete only when the classifier, correction contract, queues, replay/tests, result note and activation prerequisites are recorded. It is not complete when all 23 responses merely pass a schema.

## Execution record

F0–F4 completed locally. The protected worker remains PID 2726366 with start identity 20871858; no live files or grants were changed. The classifier produced exactly 23 rows: 12 invalid document references, 2 invalid aliases, 4 need-type/source substitutions, 1 invalid disposition and 4 substantive evidence-binding failures. It wrote 19 mechanical packets and 4 substantive packets. A hash verifier passed for all 23 raw/request pairs and confirmed `auto_accept=false` and zero provider calls.

F5 regression passed: 98 tests. The full replay rerun completed in 128.87 seconds: 217 unchanged failed responses, 194 validating protocol simulations, and 23 remaining rejections; zero provider calls. Its saved replay hash matches the classification. `git apply --check` passes for the unapplied candidate patch.

F6 result note: [legal-23-failure-repair-2026-10-26.md](../implementation/legal-mission-control/results/legal-23-failure-repair-2026-10-26.md). F7 remains HOLD: live qualification requires a safe checkpoint, reviewed registration/binding and current authority. The current master still has independent ready work; no duplicate dispatcher is started.

### Completion audit and bounded correction enforcement

The continuation audit found that F2/F3 were overstated: the candidate's request
schema is implemented, but the 19 packets contain descriptive permissions only.
They do not yet include executable field restrictions or authenticated correction
validation. F2/F3 are therefore reopened within this same local package. The
19/4 split classifies the first failing invariant; it does not prove that all
19 cases will pass after that invariant is repaired. No history or allowance is
reset by this correction to the execution record.

Implement a local packet builder and validator in
`scripts/legal_context_failure_repair.py`. It imports the retained isolated
candidate, verifies its identity and exact request/raw/schema/wire files, and
enumerates only defective reference or shape fields. Document/source replacements
must be explicit selections from the current request, never fuzzy substitutions.
Clearing identifiers from a client-fact/authority need is a deterministic shape
repair; its kind, query and reason remain fixed. A disposition replacement must
be valid for that exact original need and delivery result. Assertion bindings
are never invented. All other fields are frozen, and the existing canonical
validator runs after decoding. A passing result is an unpromoted protocol
candidate; the retained model result and legal decision remain unchanged.

Dependencies: this enforcement completes F2/F3 after F1; it is independent of
F4 and the live dispatcher. F5 checks the enforcement with adverse controls and
the four deterministic identifier-clearing proposals. F6 records the actual
outcomes, manifest and refreshed frontier. F7 retains its existing prerequisites.
One implementation and one corrective test cycle are allowed here. Stop this
local branch on altered inputs, changed candidate identity, unexpected fields,
or exhausted local correction cycle; persist any subsequent substantive failure
and continue the independent packet/document work.

Evidence contract: the baseline is each unchanged saved request and wire response
under the already-tested exact-reference simulation. Pass means only authorized
fields changed and the unchanged canonical validator passed. Changed identities
or prose are vetoes; residual validation failures trigger substantive reassessment
and are not evidence of a defective legal authority. Counts are explanatory only.
No live behavior, improved legal accuracy, accepted answer, or tool contribution
is concluded. Artifacts remain under the existing `failure-repair` directory.

Commands use `.venv-context/bin/python` from the repository root, with fixed
`scripts/legal_context_failure_repair.py build`, `verify`, and `check-shapes`
actions. The focused regression uses `-m pytest` and a retained XML report.
These commands are local and consume no external attempts. CPU-only execution
does not import GPU frameworks; seeds are inapplicable to deterministic checks.

Skeptical audit: **PASS for this bounded local completion; HOLD for activation**.
The exact baseline and substantive validator are preserved; schema success is
not a promotion criterion for law. Source selection remains a reviewed
hypothesis, not an automatic typo correction. Packet equality and negative
mutation tests expose silent legal changes; canonical validation exposes errors
hidden behind the first failure. No current worker, binding, sealed evidence,
attempt limit or unrelated branch is changed.

### Reviewed selections and binding reassessment

The four deterministic identifier-clearing proposals pass the unchanged full
validator and retain UNRESOLVED decisions. Review of the other saved inputs
identifies precise repair evidence: nine document cases repeat an exact prior
query/source identity, one paraphrases the same prior need with the identical
ordered locator signature, and two repeat document/locator pairs already present
in their decoded source-gap list. Each replacement will be recorded explicitly
with its request path; no string-distance rule is used. The incorrect client-fact
SUPPLIED_SOURCE status can become STILL_REQUIRED because its own unchanged reason
states that those facts remain absent.

The two r18 source aliases resolve to dependency assignments, not legal sources.
Use the single corrective cycle to permit removing only authenticated non-source
IDs from a SOURCE_TEXT need when a nonempty query or locator list remains. Keep
all valid source IDs, the entire need, query, reason and locators. This is a
shape correction, not a replacement source selection. Unknown aliases still
require explicit review. Retain v1 packets and results; v2 packets record this
additional exact rule, without resetting any execution allowance.

F4 must distinguish missing source evidence from missing assertion-link metadata.
Inspect the original delivered quotations and verified indexes for each actual
numbered prose path. An explicitly reviewed new binding may use only an exact
already-delivered indexed citation. Preserve every substantive field, the original
raw result and any genuine missing-fact/later-treatment need. Keep this separate
from the mechanical edit validator. A successful binding check establishes
attribution, not entailment or a newly accepted answer. If no genuine citation
can be verified, retain the case as unresolved; never fabricate it.

Audit: PASS for these local reviewed proposals. Valid sources are never discarded;
unknown identities and wrong-document citations remain vetoes. Original need IDs,
hashes and explicit source paths provide the comparator. All proposed bindings
are provisional and unpromoted. The live-activation HOLD remains unchanged.

### Verified local completion

F0–F6 local implementation and evidence are complete: v2 packets cover all 23
assignments; 25 enforcement tests pass; 18 of 19 mechanical proposals pass
immediately. The remaining mechanical case exposes a missing assertion link.
Explicit review of that case and the four original binding cases verifies seven
links to exact delivered indexed quotations; all five pass. Six adverse controls
remain rejected. The final unique population is 23 locally validating candidates,
with 21 UNRESOLVED, one REJECT and one pre-existing ACCEPT proposal unchanged.
This corrects the initial assumption that the four missing links necessarily
implied missing source evidence. The first-error queues remain historical evidence.

The executable enforcement is `scripts/legal_context_failure_repair.py`; reviewed
selection and binding checks live beside their receipts as
`execute_reviewed_corrections.py` and `check_reviewed_bindings.py`. No source
selection or assertion was filled by an arbitrary nearest match. All 364 protected
live files match their snapshot. Zero provider calls and zero live attempts were
consumed. The single local corrective cycle added authenticated non-source removal;
it did not change the bound candidate, canonical validator or master limits.

F7 remains pending. Host-level process verification confirms worker PID 2726366
is active; sandbox process invisibility is not a termination receipt. Do not start
a replacement dispatcher or change its binding. Independent master work stays
with the current dispatcher. A safe checkpoint, reviewed finite allocation within
the user's reserve, same-master registration and fresh protocol qualification are
still required before live promotion. The durable result and run manifest record
this boundary; local validity does not close the original four questions.
