# Delayed Sol retries: user instruction of 16 October 2026

The user instructed: "I think sol can work, right?  it may not be reliable.  so if it does not work, you can wait for an hour or two and try again."

Treat this as standing authorization for delayed retries of transient service
failures within the existing campaign call ceiling and deadline. Successful
`gpt-6.1-sol` responses already establish that the route can work. An outage
does not by itself establish permanent model unavailability or failure of the
legal task. Do not ask for the same timing authorization on each occurrence.

Wait one hour after a proved terminal transient failure; after a further
transient failure, wait two hours before the next eligible attempt. Honor a
longer explicit server retry delay. Count every actual attempt, retain the
original failed receipt and exact request/schema, and reuse completed work.
Waiting does not consume another repair attempt. Retain all earlier spent
calls, replacements and repairs; this instruction does not reset them or
extend the grant deadline. Do not start a call without enough remaining time
for its normal timeout.

The retry record needs the original receipt, request/schema identity, failure
time, next eligible UTC time and current worker identity. A reload must inspect
that record and any surviving worker before sending a request. An uncertain
in-flight request must first be reconciled. Time passing alone cannot establish
successful service qualification. After a successful eligible request, resume
its dependent work and continue other ready work. During a wait, independent
local work may continue.

This permission covers classified no-output gateway/service failures and
terminated transport interruptions. It does not turn an unspecified invalid
request, unknown HTTP 499 cancellation, explicit provider refusal, completed
but invalid response, quota/authentication problem or changed evidence into a
retryable service failure. Those retain their separate diagnosis or disposition.

Review: this is an appropriate timing policy for intermittent availability.
The exact one-hour/two-hour durations come from the user; they are operational
choices, not evidence that service will recover. A successful retry establishes
only that request's completion, not answer correctness or general reliability.
Existing global limits and integrity checks remain continuation vetoes.

The baseline runner has second/minute backoff and a persistent open circuit;
its latest binding predates the registered local repair. The mandatory mission
check passes, status is BLOCKED and admission refuses. This reviewed amendment
addresses the named service prerequisite in the same master under the latest
user instruction. It does not renew R1--R10 or silently reuse their exhausted
48-replacement reserve.

## Executable amendment and dependencies

| Work | Success prerequisites | Completion evidence / independent continuation |
| --- | --- | --- |
| Freeze settled comparator | No running owner or reserved dispatch; current check passes | Authentic program, state, binding, ledger, scope and source snapshots |
| Durable delay policy | Authenticated no-output failure | Next UTC retry time survives reload; no early dispatch; exact request/schema; completed, refusal, 499, invalid-request and authority controls |
| Adoption and binding | Passing local tests and preserved predecessor | Register one local amendment, bind current code and a separate delayed-retry scope; no model call |
| P10 and evidence | Own unused attempt, retained acquisition and current binding | Resume original independent owners; successful accounts remain reusable; service retries happen within the current attempt |
| Other original branches | Their own successful preparation | Drain ready baseline/tool/comparison work; P14 invalid-request/cancellation and Gatecoin refusal remain separate |
| Settlement | All runnable work settled, or actual waiting worker recorded | Actual calls, next retry time, source results and ready set; refresh without claiming legal acceptance |

Allocate at most 24 delayed service replacements under this new instruction,
all charged inside the existing 8,100-call ceiling and original deadline. This
is a conservative finite implementation bound: one hour then 23 two-hour waits
already consumes 47 hours before call time. It is not a claim that 24 retries
will be needed, a new repair allowance, or an extension of the window. Each
actual retry must fit its wait plus normal call timeout before the deadline.
Phase admission budgets the actual logical work and finite replacement count;
it does not assume every hypothetical outage must fit before starting useful
work. The deadline is rechecked before every wait and dispatch.

Use the existing unused P10/evidence attempts. Binding and registration are
local adoption work, not extra answer attempts. The original four questions,
46 obligations, 35 readings and six matched tool evaluations remain unchanged.
No successful owner is resampled and neither P14 nor Gatecoin is reopened by
this timing instruction. Retain all old scopes and failures as historical
evidence. The first actual needed P10/evidence call tests the reopened service;
a small unrelated ping cannot promote the product route.

Evidence contract: the comparator is the frozen post-local-refresh program at
2,359 calls and detour 51. Pass requires exact old task limits and attempts,
unchanged grant and prior charges, durable no-early-retry behavior, no duplicate
dispatch during a cooldown, and actual continuation only under current bound
code. Corrupted evidence, uncertain in-flight work, exhausted call allowance
or expired deadline veto continuation. A further transient failure schedules
the next wait; it does not trigger a code-repair round. Tests and a successful
request are engineering evidence only; original legal acceptance is unchanged.

Skeptical review: PASS for this bounded amendment. The earlier policy treated
an outage stop as requiring another manual program revision, and its short
delays did not match the user's hour-scale recovery strategy. This amendment
keeps an auditable old circuit, adds a separately counted delayed policy under
the new instruction, and lets one eligible request reopen service after the
recorded wait. Half-open service permits only the failed request. A restarted
worker must reconcile any uncertain wire reservation before another call.
Waiting is persisted and polled in at most 60-second intervals. The main
remaining risk is that service recovery exposes another existing product
failure; that failure must remain separate and must not be retried as transport.

Implementation review, 16 October: the 180-test local regression passes in
8.08 seconds with zero provider calls and unchanged campaign charges. The
retained log and manifest are under
`artifacts/legal-mission-control/2026-10-16/delayed-service/`. The tests cover
saved UTC waits, exact request/schema identity, single-use half-open permits,
deadline refusal, finite replacement accounting, changed evidence, completed
output and nonservice exclusions, original policy behavior and preservation of
the existing task limits. The first delay applies once across the new shared
scope; later requests cannot reset it to one hour.

The skeptical implementation review found two cases requiring explicit bounds.
First, concurrent requests could otherwise compete to reopen one shared
circuit. This policy uses one acquisition worker and an exclusive service-worker
lock. Second, a killed process can still have an explicit invalid-request or
refusal event; timeout recovery now rejects that combination and any retained
model message pending inspection. A closed local child does not authorize
resampling a completed response.

The first live dispatch still requires successful staged mission validation and
the actual allowance validator against the staged binding. The old failure's
issue time plus its full 305-second timeout and at least one hour supplies a
conservative first eligible time. No unrecorded uptime assumption is needed.
Registration commits the program, state, binding and mission in one restartable
transaction. The detached worker retains its actual PID/start identity; an
interrupted worker is not silently replaced while a dispatch remains uncertain.

Decision: accept the local recovery implementation for the existing unused
P10/evidence attempts, subject to those actual adoption checks. Service
availability remains untested in this amendment, as does downstream answer
quality. No statistical reliability estimate or legal acceptance follows from
the regression tests. Record actual execution separately without rewriting this
sealed pre-run review.
