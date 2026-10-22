# Closing the prospectus work without empty-queue handoffs

This is a reviewed continuation design for the existing prospectus authority.
It does not replace program.json, its 59 obligations, 44 tasks, admission
history, or sealed evidence. Baseline: revision 63 on
feature/prospectus-evidence-master. The current request is to explain repeated
stops and establish a concrete way to close the remaining work.

## What is actually causing the stops

The assistant has repeatedly ended a turn after a bounded package. The worktree
instructions already prohibit that when authorized work remains. Short tool
waits do not require short execution turns. Changing an allow-list cannot
repair the decision to send a final response.

There are also specific defects in the execution design:

1. execution_authority.status selects READY and ADMITTED tasks. A partial
   RECORD stays RESULT_RECORDED until a reviewed task specification changes.
   Therefore next_task=null says nothing about whether substantive local
   design, implementation or review remains possible.
2. There are 40 unfinished tasks without implemented task-specific acceptance.
   The two built-in workers and two registered acceptance validators account
   for the four completed tasks. Most other dossiers repeat the same generic
   acceptance sentence. Successful finite trials cannot close these broader
   tasks; their COMPLETE-only dependents then wait indefinitely.
3. Of 31 partial tasks, 25 have spent their admission allowance. Status hides
   this under RESULT_RECORDED; a reviewed refinement alone would not admit
   them. A justified changed package needs an explicit cumulative budget
   review, retaining all attempts. An unchanged retry is not a solution.
4. refresh validates a recorded transition and regenerates essentially the
   same table in three files. It does not design a successor. The compact CLI
   suppresses the partial-task detail and gives no substantive next action.
5. The four files in execution_authority.CODE are bound to every admission.
   Editing the common dispatcher just to improve a status message would stale
   current acceptance evidence and consume more revalidation work. This is a
   conservative correctness rule with a real execution cost, not a reason to
   silently relax evidence currentness.
6. Prior route reviews conflate missing external evidence with local design
   decisions. Choosing a bounded supported runtime and implementing its
   acceptance tests are local work. Unexposed readers, authentic holdings,
   missing executed agreements and an actual receiving institution are
   different dependencies.

No inspected evidence establishes the cause of the historical VS Code stream
disconnects. The official Codex reference was unavailable (HTTP 403 in both
sandboxed and trusted requests). This diagnosis rests on local code and retained
execution history, not an assumed platform timeout or product setting.

## Delivery and evidence boundaries

Every original obligation remains visible. Engineering delivery means the
declared product routes execute with supported inputs, preserve provenance,
refuse unsupported inputs, and affect the actual downstream answer as specified.
Assisted legal acceptance additionally needs genuine independent reading and
adjudication. Automatic capability additionally needs unseen complete cases and
the declared missing source/layout families. Package evaluation needs real
product use and matched effects, with failures attributed to our integration,
our usage, missing access, or a demonstrated package limitation.

The current evidence supports several finite repairs. It does not establish
full automatic interpretation, actual ownership, source authenticity or
universal package suitability. Unknowns must remain visible in delivered
answers. Unsupported financial families are not silently added to the original
fixed-rate delivery commitment. Changing required scope remains a substantive
project decision; recording a conditional result does not remove the obligation.

## One program, two kinds of work

The continuation map referenced by program.json accounts for every existing
task. It distinguishes local work, mixed local/external work, waiting for
specific evidence, genuine external inputs, and accepted work. Each entry
names a missing result, a concrete next action, a substantive acceptance test,
the external input if any, and its stop condition.

scripts.prospectus_continuation is a read-only inspector of that same program,
history and map. It cannot admit work, alter budgets, accept evidence or start a
process. Its purpose is to expose a missing continuation decision without
invalidating product evidence merely to improve reporting. It must say
REVIEW_REQUIRED when the admission queue is empty but local work remains. It
must never turn an expired budget or incomplete dependency into admission.
An inspected plan is not itself a task-specific acceptance implementation.

Before an implementation package, refine its existing task through revise,
freeze the complete plan and comparator, and implement or specify its acceptance
route before launching the experiment. A task without an executable validator
can retain useful evidence but cannot be advertised as complete. Human
acceptance needs authenticated substantive review plus mechanical checks; a
Python validator cannot supply the judgment.

## Ordered work and concrete completion tests

| Phase | Work using existing tasks | Required result and acceptance | Dependency / continuation |
| --- | --- | --- | --- |
| 0: current execution diagnosis | All 44 tasks; no product re-execution | Exact 59-obligation/44-task coverage, visible capped partials, evidence-backed blockers, tested read-only continuation report | Completed only after the actual current program is inspected; this does not close a product task |
| 1: supported native runtime | native-binding, native-confinement, portability | Versioned supported source/runtime matrix; native text, fresh OCR and retained-image routes; changed/missing input, lookup, race, environment and overflow controls; full downstream equality; installed relocation and genuinely different supported environment | Specify native-binding acceptance first. Preserve binding005/006 failures and bounds. Confinement depends on actual binding acceptance; portability is a separate result |
| 2: extraction and source coverage | native-layout-cases, native-candidates, page-coverage, portuguese-2008, relation-discovery | Real table, rotation, true vertical and bidirectional originals; complete word/character and region accounting; source-bound qualification links; production geometry adapter; unseen complete-page/answer comparisons | Local adapter and error handling can progress before independent readers; missing families veto general automatic promotion |
| 3: original documents and authority | source-authority and all fourteen source-bes tasks | Exact issuer/period/edition and executed agreement identities; incorporation ranges, original statement cells, audit status and date/availability evidence; controlling resolution of the printed bilingual discrepancy | Retained originals support local source analysis now. Missing exact documents stay distinct from review of available originals |
| 4: legal construction and facts | basf-references, basf-margins, basf-office, basf-incorporation, basf-meanings, law-applicability, reasoning-corpus, instrument-facts | Explicit treatment of the 92/94-page conflict and default(f), actual calculation-agent designation, dated applicable law, premise-level conditional answers, counterexamples and qualified adjudication | Continue conditional source analysis without client facts. Do not relabel rejected law006; a new admission needs genuinely changed source/model evidence |
| 5: financial use and package trials | finance-conventions, entitlement, actus-prerequisites/comparison, cdm-profile/roundtrip | Exact source-specified cash flows and entitlement conditions through actual consumers; same-input independent schedules; actual ACTUS events/payoffs/states; receiver-specific CDM semantic round trip | Fixed-rate supported scope first. ACTUS core/source/tests/terms and actual CDM receiving profile remain separate prerequisites |
| 6: independent evaluation and release evidence | independent-packet, independent-readings, authoring-export, recovery, authority-acceptance | Administrator-established unexposed cohort, authenticated first readings and adjudication, actual browser exports, relevant changed-code recovery and capability-by-capability final decisions | Start external preparation alongside phases 1–5. Final review compares full answers with independently produced evidence; test totals cannot substitute |

These are dependency groups, not mandatory serial barriers. Continue independent
ready work when a source, reader or package-access route is blocked. Do not
rerun recovery after every planning change; rerun only when its real bound
method/input changes. Do not keep reaccepting the authority instead of fixing
the next substantive task.

### First engineering package: native acceptance and supported scope

The starting scope is an explicit optional Linux CPU runtime with fixed
manifest files and environment, covering the three existing native call sites.
The host kernel, Python orchestration, Bubblewrap setup and private proc/dev
remain declared trusted inputs. Same-kernel isolation does not prove portability.
No cache reuse or new default is implied. This is a reviewed candidate scope,
not evidence that it already passes.

Before requesting native-binding admission 007, retain a task-specific matrix:
each route, source/language family, exact manifest, expected full consumer
result, adverse control, unsupported-case behavior and evidence file. Start
with the existing 006 actual comparator but add a distinct retained source or
runtime condition that discriminates the missing supported-scope claim.
Review the proposed validator against missing-route evidence, forged PASS,
stale input, changed receipt, removed adverse control and missing consumer.
Its predicates must cover native-binding's responsibility without absorbing
the independent confinement/portability obligations or certifying legal truth.

The admission request must retain all six previous binding admissions and the
visible process-start history. Only one additional admission is supported by
the existing revision mechanism; there is no blanket extension. Specify a
finite worker-start/time/output budget from the exact stage list before
admission. If no new discriminating case can be nominated, finish the scope and
validator design, record that exact limitation, and move to another local route.
Do not spend another admission replaying the unchanged exposed source.

Acceptance implementation changes would modify common bound controller files.
Before that change, identify which accepted results become stale and prepare
their necessary validation in the same reviewed package. A future split of
control-plane and product bindings requires tamper/staleness tests and explicit
review; do not silently exempt code from currentness to avoid this cost.

### External inputs to collect as a single prepared batch

Prepare the exact evidence checklist locally before asking for input:

- Four missing BES Finance originals (02, 03, 04, 10) and the three executed
  agency/Interbolsa/representative agreements, including parties and amendments.
- Genuine independent readers and an administrator-controlled unexposed cohort;
  the 47 exposed and 15 unknown entries are not eligible by declaration alone.
- Applicable dated legal authority, actual calculation-agent office designation,
  and authentic instrument/holder/account/record-date/event evidence.
- Authorized ACTUS core 1.1.0, compatible official source/tests and applicable
  terms; the actual CDM receiving system, version, profile and required functions.

Do not ask the user to approve ordinary local edits or routine design choices.
Do not send external messages without authorization. Missing information is not
an approval, and missing client facts do not prevent conditional source analysis.

## Execution loop and stopping rule

Use the pinned worktree command check/status/admit and resume after interruption.
For a running package, retain one process identity, yield after one second, poll
that session with bounded output, inspect the result and run the next stage.
Freeze a plan before admission; amendments create a new reviewed revision,
never a changed bound file inside a running attempt.

After a package, retain failures as well as successes, record, refresh and
continue. If the queue is empty, run the continuation inspector and review the
local routes. A finite failed candidate triggers its predeclared changed repair
or another independent route. Budget exhaustion requires a justified cumulative
review or an explicit closed experiment, not an automatic increase.

A whole-program blocked handoff is justified only when every unfinished route
has a specific current blocking condition, no local preparatory or repair work
remains within authorization, and the exact next input/action is recorded.
The diagnostic inspector does not enforce agent lifetime; the executing agent
must obey this rule. Never claim that adding a policy file prevents platform
disconnects or guarantees uninterrupted future execution.

## Skeptical audit and evidence contract for phase 0

Question: does the current program distinguish completed work, executable work,
local refinement and genuine external waiting, without changing acceptance?
Comparator: revision 63 and its current sealed history, not older R0–R8 PASS
receipts. Primary pass criterion: exact task coverage and correct continuation
classification, including the live empty queue with locally actionable gaps.
Required controls: omitted/duplicated task, stale map, tampered map/method,
exhausted partial budget, incomplete dependency, genuine external-only queue,
active job, and claimed completion inconsistent with unfinished tasks.

Veto: damaged authority history/input identity, missing task coverage, false
permission/acceptance inference, or any changed sealed evidence. These stop
phase 0. A product gap or missing external file does not invalidate this
diagnostic. Counts are explanatory, not product promotion criteria.

Default audit: use the original 44 tasks and 59 obligations because they are
the reviewed scope; detect omission by exact set comparison. Use a read-only
inspector to avoid invalidating actual product evidence for a reporting change;
test that it neither writes events nor dispatches. Treat route classifications
as reviewed hypotheses; stale task hashes demand renewed review. Preserve
original budgets rather than silently treating them as fresh allowances.

Pre-mortem: a neat report could still hide an impossible acceptance criterion,
call every task external, or count a plan as an implementation. The all-task map,
mixed/local labels, actual missing-validator list and explicit first native
package expose those failures. The inspector cannot establish legal truth or
future persistence. No product benchmark, native subprocess, installation,
GPU run or external communication belongs to phase 0.

Audit verdict: proceed with the bounded diagnostic, reviewed program metadata
and focused adversarial tests. Do not change common bound authority methods or
start a native experiment under this diagnostic authorization. Retain the
actual command, environment, test report and current report in the authority
directory; then report exactly which remaining work is local versus external.
