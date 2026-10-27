# P14 failure diagnosis and bounded repair, 23 October 2026

The user asks why the retained run reports 17 failed review groups and 52 failed
repairs, and whether they can be fixed. This work belongs to the current legal
integration master; it creates no new live-call or repair allowance. The baseline
is P14 attempt 4 in `review-repair/recovered-live`, completed at
2026-10-22T16:57:55Z with review still open. The active source checkout is
`checkpoint/legal-integration-2026-10-22`; main was merged separately to preserve
the live worker's bound files.

## Question and evidence contract

Determine which failures are service deferrals, malformed transport/response
contracts, invalid citations, or substantive unresolved readings. Compare exact
retained requests, schemas, responses, dispatch journals and assembled review
results. A count of failed historical calls is not the number of currently
unresolved legal issues. A repair passes engineering review only if it removes a
reproduced contract or continuation defect while preserving exact identity,
citations, original answers, settled results and all recorded charges. It does
not establish legal acceptance. Missing required source facts and actual provider
availability remain separate limitations.

## Dependencies and bounded scope

| Item | Success prerequisites | Completion and recovery |
| --- | --- | --- |
| Admission and current-state check | None | Run exact check/status/admit; retain result, inspect current dossier and process identity |
| Failure census | None; read-only | Count every failed group, repair and follow-up; preserve hashes and exact reasons |
| Response-contract trace | Census | Trace compressed IDs, schema/decoder, citation paths and individual salvage; reproduce locally without provider calls |
| Service/continuation trace | Census; independent of response trace | Explain reserve exhaustion, circuit state, pending/running status and fan-out after refusal |
| Bounded local repair | Reproduction and admission/reviewed revision | Isolate candidates from bound running source; verify behavioral positive and negative controls |
| Adoption/live continuation decision | Reviewed repair, verified worker settlement and existing authority | Never silently edit bindings, reset failed attempts, expand reserves or duplicate a running worker |
| Report and refresh | Both traces complete | Record actual causes, repair readiness and exact unresolved prerequisites; continue independent authorized work |

The diagnosis makes no provider calls. One bounded local candidate is permitted
for each reproduced engineering defect; failed candidates trigger a documented
decision rather than an unlimited new repair program. No additional live calls
are attempted until the existing authority and recovery prerequisites verify.

## Skeptical audit

PASS for diagnosis. The earlier status message did not distinguish the ended
P14 attempt from the still-live supervisor, and failed group counts include
superseded work. Correct those baselines first. Global service refusal must not
be counted as a semantic model failure. The input/output size allowance is not
presumed causal: inspect measurements and the exact failing validator. Avoid
guessing ID mappings, weakening citation checks, treating format-valid reviews
as legal success, or using tests from the merged main checkout against different
bound source. Local tests can establish contract correctness only. A changed
sealed input, uncertain dispatch, invalid authority or exhausted sub-budget vetoes
live continuation; it does not veto independent diagnosis and local preparation.

Initial census: groups have 9 schema failures, 5 unassigned-rationale failures
and 3 unbound-numbered-assertion failures. Repairs have 37 circuit refusals, one
exhausted replacement reserve, 9 schema failures and 5 integrity failures.
Another 503 explicit-context dispatches were refused by the same open circuit.
These are preliminary dispatch counts, not remaining legal obligations.

## Reviewed local candidate

The census now confirms 38 service/reserve failures and 14 response/citation
failures among the 52 repairs. All 415 inspected group/repair bindings give
aliased assignment IDs in the request but opaque original keys in the response
schema, with no explicit mapping in the delivered request. Single-target repairs
also retain a whole-batch review instruction. Repair those contracts through an
explicit opt-in profile, preserving full context, response validators and legacy
binding reproduction. Test actual transport round trips and adversarial outputs;
reconstruct all saved bindings locally to check context preservation and size.

Independently prepare an opt-in service prerequisite check before new dispatch
reservation. Reuse settled calls first; a known open circuit must propagate as
a deferred prerequisite through phase, capacity and context loops without
settling unstarted work as failed. Tests must show pause/resume without repeating
settled calls. A failure after dispatch stays a charged historical failure, and
uncertain reservations remain authority vetoes. The preflight does not promise
to eliminate races or cure an unavailable service. The existing live supervisor
must explicitly adopt this new deferral behavior before deployment.

Skeptical audit: PASS for these isolated local candidates, not live deployment.
Both profiles default off to preserve sealed request identities; their selectors
are recorded in product options. No semantic verdict, quotation, source, answer,
retry allowance or deadline changes. The current worker ended at
2026-10-22T18:23:32Z with exhausted replacement reserve (88/88). Its refreshed
state is evidence, not authorization to restart. A live canary still requires
reviewed adoption, settled-owner reconciliation and a valid recovery allocation.
The inherited 3000-token instruction is already rewritten by capacity_policy;
it is not a confirmed cause and requires no separate repair.

Saved-binding replay found another engineering defect: canonical JSON sorts
dictionary keys, while review schema required-field lists and identity-hash
aliases depended on runtime dictionary order. It reproduces in the unchanged
baseline code too. The opt-in contract now normalizes request key order and uses
the schema's declared required-field order. Historical paths remain unchanged;
replay compares that behavior against baseline code and checks exact decoded
context separately from transport alias spelling. This is a latent resume defect,
not a retrospective explanation of the 17 reported baseline-group failures.

## Result and refreshed next step

Local implementation and skeptical review are complete in the isolated candidate
checkout. All 203 focused tests pass; all 415 saved bindings preserve decoded
context and validators under the candidate, fit the existing input envelope and
survive canonical JSON reload. The saved baseline's reload defect is separately
retained. See
`docs/implementation/legal-mission-control/results/p14-failure-diagnosis-2026-10-23.md`
and the reproducible census, replay, repair queue, patch and source manifest in
`artifacts/legal-mission-control/2026-10-23/p14-diagnosis/`.

The ready diagnosis, contract repair, service repair and completion-only review
items are finished. Adoption/live execution remains a separate dependency:
review a finite recovery allocation with 88/88 replacements already used,
reconcile the Gatecoin orphan, allocate P14's spent attempt explicitly and bind
exact successful-review imports plus the specific pending repair queue. Preserve
4027/8100 call charges, the 24 October 02:19:15 UTC deadline, valid answers,
individual decisions and all old failures. No model call was made by this work.
The next substantive target remains product-contribution/P14 review, not a new
engineering program. The candidate does not close the 672 unresolved or 25
adverse initial decisions.
