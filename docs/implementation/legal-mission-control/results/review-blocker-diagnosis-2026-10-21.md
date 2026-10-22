# Why the current integration tasks are blocked

21 October 2026, Hong Kong. The latest failures include several reproducible
local implementation defects, a shared service-retry stop, and an unresolved
whole-program budget problem. They do not establish that Sol is unavailable or
that the six tools cannot help. Tool-effect comparisons depend on answers whose
reviews have not completed. None of the six tools has complete matched product
evaluation evidence yet.

This is an offline diagnosis and repair design within the existing integration
master. It does not adopt a production repair, change the running worker's
bindings, allocate calls, reset attempts, or promote a legal answer. The original
four questions, 46 obligations and 35 readings remain the substantive target.

## Evidence and verification

The comparator is the current retained-acquisition repair, Gatecoin baseline
attempt 3 and P14 baseline attempt 2. The mandatory mission check passed, status
reported work remaining, and admission returned `ADMITTED_MASTER_WORK`.
The admitted product-contribution dossier and standing continuation policy were
read. The no-call diagnostic passed its pre-execution skeptical review in
[the diagnostic plan](../../../plans/legal-review-blocker-diagnosis-2026-10-21.md).

The command actually executed was:

```text
.venv-context/bin/python artifacts/legal-mission-control/2026-10-21/review-blocker-diagnosis/diagnose.py
```

It completed at 13:41:36 UTC in 13.22 seconds, at commit
`3c3e462acabfde8c62285f4274f0f8c62b90a790`, with existing uncommitted production
changes. GPU devices were deliberately hidden. There were zero provider calls;
the live-call ledger was unchanged at 3,539 of 8,100 charges. The result is
`artifacts/legal-mission-control/2026-10-21/review-blocker-diagnosis/diagnosis.json`.
The result contains source identities and hashes of its plan and current
program. `manifest.json` additionally records implementation hashes and the
diagnostic script hash. Random seeds are N/A: this was deterministic replay and
measurement, with provider dispatch disabled.

The reconstructed products matched each saved input hash, store hash and every
source-store record. For each question the diagnostic measured the first and
largest source record, plus the first and largest serialized dependency. This
is eight named cases, not a complete capacity sweep.

## Verified causes and their consequences

### The enlarged capacity profile does not reach every constructor

`PhasedProduct.request` adds the selected downstream capacity profile after the
base constructor returns (`phased/product.py:58`). Grouped source reviews call
`product._request` directly (`phased/group_review.py:95`), as do explicit context
bridges (`phased/context_bridge.py:65`). These paths therefore retain the old
32,768-token / 200,000-byte profile. Ordinary review context packing also measures
requests inside `BoundedProduct.review_request`, before the outer override adds
the profile. It can consequently decline useful additional context using the
older bound even when the eventual request selects the larger one.

Gatecoin's expanded answer is 168,020 bytes and 35,808 local tokens. All 2,432
source/dependency review assignments were recorded as local capacity failures.
The grouped planner replaces detailed measurement failures with `Complete
individual review cannot fit`; those blocked singletons never reach the generic
capacity executor. Its grouped adapter partitions output decisions while
retaining the full shared answer and context, so output pagination alone cannot
solve an oversized shared input.

| Gatecoin sampled assignment | Current local tokens | Current result | Tokens with selected profile | Result with selected profile |
| --- | ---: | --- | ---: | --- |
| First source | 36,963 | REFUSED | 36,982 | FIT |
| Largest source text | 37,870 | REFUSED | 37,889 | FIT |
| First dependency | 38,034 | REFUSED | 38,053 | FIT |
| Largest serialized dependency | 39,427 | REFUSED | 39,446 | FIT |

Changing only the capacity-profile field makes these four requests fit both
local product and provider-visible measurements. The largest measured product
payload is 180,268 bytes, below the already-selected 250,000-byte bound. No text,
source, assignment, answer or schema changed. All four P14 samples fit under
either profile. These results demonstrate the wiring defect; they do not prove
every review or future bridge fits, or that the remote service will complete it.

Repair capacity selection at the common request-construction boundary, before
packing and measurement. Preserve synthesis's explicit capacity escalation and
each task's declared scope. Merely replacing `_request` with `request` in one
caller could change automatic source selection; it needs scope-preservation
tests. Enumerate every active caller and replay the complete saved population
before live adoption. Retain detailed refusal measurements for any remainder.

### P14's output schema and semantic validator disagree

At slot 3505 the retained group
`audit-group-p14-b1344d092fd76fb2dc46c4e1` passes its JSON schema but fails the
local validator. Two context needs are labelled `EXTERNAL_AUTHORITY` while each
also supplies four retained-source IDs and two locators. The schema permits this;
the validator forbids it. That malformed group loses five review assignments.
See `phased/group_review.py:15` and `:34`.

Use distinct source-text and absent-fact/authority variants in the output
contract, within the provider's supported schema dialect, and describe their
meaning in the instructions. An invalid response must receive its own bounded
repair and preserve its original receipt. Do not silently relabel the need or
weaken source validation. A valid retained-source request still needs scoped
source identities and valid locators.

### Invalid adverse reviews prevent all corrections

P14 has two reviews labelled `REJECT` with empty issues and support. Their prose
actually says that the answer should be accepted because the assigned Gatecoin
dependency is outside the answer's P14 inference. They occur in groups
`audit-group-p14-30ec8fd1a8d457853a226f61` (rationale `r4`, slot 3530) and
`audit-group-p14-eeebd28533c32653ba1b4367` (`r3`, slot 3534).

`shared_rationale.decisions` validates ACCEPT support but permits these empty
REJECT decisions (`phased/shared_rationale.py:29`). `correct_answer` then requires
every REJECT to contain support and issues (`bounded_product.py:1195`). The two
invalid reviews disable correction for all other objections; the saved outcome
is `NOT_ATTEMPTED`, with `eligible_adverse_review=False`.

Validate adverse-review structure at the review boundary. Retain valid individual
reviews and quarantine invalid ones with their exact assignments and provenance.
Assess valid objections independently. Do not infer ACCEPT from contradictory
prose: obtain a valid review before final acceptance. A partially valid group
must remain explicitly incomplete until all mandatory assignments are resolved.

### Gatecoin correction uses a global source-gap condition

All four Gatecoin requirement warrant assessments validate. Together they mark
22 issue occurrences WARRANTED and eight UNWARRANTED, with zero UNRESOLVED
issue decisions. They also retain 17–23 source gaps each. The code treats any
such gap as making the whole correction batch unsettled
(`bounded_product.py:1186`), producing `WARRANT_UNRESOLVED`.

The saved assessments identify contradictions in detailed accounts, including
claims that operative circular requirements, the ETD valuation of HK$10,958.27
per unit, or scenario-seven detail and sale/allocation directions are missing
when delivered records supply them. Some final-answer passages already contain
the relevant detail; an adequate final passage does not repair its contradictory
underlying account. These are recorded warrant assessments requiring correction
and fresh review, not an independent legal certification by this diagnostic.

Represent correction dependencies per issue. Correct supported account defects
while retaining unrelated later-treatment, transfer and client-fact gaps. If a
specific missing source is necessary for an issue, that issue remains blocked.
If necessary relations between issues cannot be separated, record their joint
dependency explicitly. Missing information may block final acceptance without
blocking an independently supported correction.

### Mixed context needs suppress available source retrieval

`PhasedProduct.audit_answer` skips bridging if any context need is not
`SOURCE_TEXT` (`phased/product.py:249`). One saved P14 unresolved review has both
source-text and external/fact needs and is skipped for this reason. Resolve its
available source needs while preserving the remaining needs for reassessment.
Resolving a source dependency must not erase a fact or authority condition.
The 40 other saved P14 context-bridge attempts failed on the shared service stop;
this separate mixed-needs bug explains one additional skipped continuation.

### The shared service reserve is exhausted

The latest charged failure, slot 3539, records `stream disconnected before
completion: Transport error: timeout` with no completed output. The selected
model is `gpt-6.1-sol`. The terminal receipt establishes a failed request; it
does not identify the remote cause or establish permanent model unavailability.

The shared delayed-retry ledger has consumed 24 of 24 replacements. Its bound
was originally chosen by the implementation because one one-hour wait plus 23
two-hour waits spans 47 hours. The later five-minute retry amendment retained
that count. The most recent three reservations use 300-second waits. Thus the
shared circuit remains open even though the overall 8,100-call allowance has
4,561 calls remaining and the deadline is 24 October at 02:19:15 UTC.

The standing user authorization for delayed retries is documented in
[the retained policy](delayed-service-retry-policy.md). A reviewed revision
should reconcile the finite recovery reserve with the current five-minute
interval and whole-program budget, preserving all 24 charges and prior failures.
Do not silently reset the circuit or create a fresh allowance. Keep exact
no-output failure classification, server-directed delays, one retry owner,
deadline checks and restart reconciliation. Completed invalid responses need
review repair, not transport resampling. No new retry count has been adopted by
this diagnostic.

### Scheduler activity is not currently substantive execution

Worker PID 941336 remained alive during diagnosis, but no product node was
RUNNING. The worker records one service prerequisite deferral about every
10–11 minutes. `defer_open_service` calls a full summary and then mission sync;
`MasterExecution.sync_mission` performs another summary, validates historical
evidence, invokes mission refresh, then computes another summary. This repeated
validation is a plausible source of the delay; its cost has not been profiled.

Retain one authenticated shared-service failure and batch affected deferrals
with one validated refresh. Keep independent local work ready. Measure before
introducing any validation cache, and never cache across changed evidence or
authority. Live process status alone must not be reported as answer progress.

## The whole review matrix needs a costed execution plan

The current output estimator requires `1024 + 1200*n <= 8192` and therefore allows
at most five assignments in each grouped call. The applicability register selects
all six tools for each original question. A fresh full pass has this lower bound:

| Question | Source/dependency assignments | Minimum groups per answer | Baseline plus six tool answers |
| --- | ---: | ---: | ---: |
| P10 | 1,751 | 351 | 2,457 |
| P14 | 1,751 | 351 | 2,457 |
| Evidence | 1,751 | 351 | 2,457 |
| Gatecoin | 2,432 | 487 | 3,409 |
| Total | | | 10,780 |

This exceeds the entire call ceiling before other stages, context bridges,
corrections or retries. It is a fresh-pass calculation, not the exact remaining
cost after authenticated reuse. Some tool attempts and individual reviews are
already retained. Nevertheless, simply restarting every answer under this
batching rule is not a feasible completion plan.

Before another matrix run, inventory exact reusable successes, determine which
changed answers or contracts require fresh review, and budget every remaining
branch plus bounded recovery. The 1,200-token-per-assignment estimate is an
engineering hypothesis, not measured semantic necessity. Inspect actual saved
group outputs before proposing different batch sizes or output limits; qualify
any change with adversarial cases, complete membership and distinct rationale
checks. A shared rationale is valid only when its scope and evidence apply to
each assigned item. Dropping assignments or merging different conclusions to
fit a budget is not a repair. If the reviewed plan still cannot fit, report the
quantified shortfall; this diagnosis grants no extra calls.

## Repair dependencies and acceptance of the design

Implement these as one reviewed amendment of the existing master. This table is
a proposed dependency map, not a second execution program or live authorization.

| Item | Success prerequisites | Independent work / completion-only follow-up | Evidence required |
| --- | --- | --- | --- |
| R0: settle current worker and retain comparator | Verified owner and dispatch state | Local diagnosis/design may continue before settlement | Exact attempts, charges, results and worker identities; no duplicate request |
| R1: capacity propagation | R0 for bound-code adoption | R2, R3, R4, R5 can be developed independently | All active constructors select intended profile before packing; saved population measurements; oversize controls still refuse |
| R2: typed context needs and adverse-review validation | R0 for adoption | R1, R3, R4, R5 | Saved malformed cases fail at the right boundary; valid siblings retained; bounded repair preserves scope and receipts |
| R3: issue-level correction and mixed-needs retrieval | R0; R2's explicit validity contract | R1, R4, R5 | Valid correction proceeds beside unrelated gap/invalid sibling; dependent unresolved issue stays blocked; fresh review required |
| R4: scheduler and finite service recovery | R0; reviewed retry accounting before live use | R1–R3 and R5 local work | No premature/duplicate retry; spent reserve retained; batch deferrals preserve unrelated ready tasks; restart controls |
| R5: whole-program reuse and budget census | R0 snapshot | R1–R4 | Exact reused identities, all remaining calls and recovery bounds; feasible current allowance or explicit shortfall |
| R6: adopt, replay and execute original tasks | Passing relevant R1–R5 checks and current binding | Completion/failure of each branch triggers diagnosis and ready-set refresh | Actual answer corrections, complete source review, applicable tool consideration and matched answer effects |

R1–R5 share no live service dependency for their local checks. Binding/state
writes remain serialized. Invalid common evidence, uncertain in-flight calls,
expired time or exhausted global authority veto dependent execution. One branch's
unresolved fact, malformed review or failed tool must not block unrelated local
repairs or another question. Each request repair remains bounded and retained;
reopening an exhausted owner requires explicit registration preserving its old
attempts. A new directory or phase does not renew a repair allowance.

Skeptical review: the diagnosis passes. Exact source identity is checked, the
capacity comparison changes only its selected profile, and failures are not
silently relabelled as legal success. The repair direction is supported, but a
full live restart is **not ready**: complete-population capacity, individual
review recovery, per-issue gap dependencies, retry allocation and remaining-call
cost still need concrete implementation and validation. This finding revises
the execution design; it does not reject tool integration as a research goal.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Accept the capacity-bypass diagnosis | Exact reconstructed samples refuse under old profile and fit under selected profile | No identity or no-call check failed | Unsampled assignments and remote completion | Repair common construction and replay all assignments locally | All requests fit or legal answers are accepted |
| Accept review/correction dependency defects | Saved outputs reproduce schema, verdict and global-gap problems | Invalid reviews and necessary missing sources still veto acceptance | Per-issue legal dependencies need preserved judgments | Validate/isolate malformed reviews and correct supported issues independently | That every source gap is irrelevant |
| Reject blind matrix restart | Current fresh-pass lower bound exceeds total allowance | Global budget remains enforced | Exact reusable results and a validated batching alternative | Cost the remaining graph before live adoption | That more budget is necessarily required or the task is impossible |
| Keep integration open | Matched accepted answers are missing | Product acceptance requirements remain unsatisfied | Actual downstream tool effect | Resume only reviewed, feasible original branches after repair | Tool failure, complete integration or general English-interpretation correctness |

The strongest alternative explanation for a later failure is that correcting
these engineering defects exposes a genuine unsupported legal conclusion or a
new service failure. The weakest current evidence is whole-population and
remote behavior: the sample proves a local bug, not eventual completion.
Client facts, dated applicability and later judicial treatment remain explicit
limitations wherever necessary. This diagnostic supplies no stochastic ranking,
service reliability estimate or new default-readiness claim.
