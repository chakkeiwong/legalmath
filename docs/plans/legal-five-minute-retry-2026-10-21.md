# Five-minute service retries in the current integration master

The user replaces the hour/two-hour wait with five minutes: “I think waiting
5 minutes to retry is good enough. If Astra is working working Sol should be”.
This changes retry timing within the existing master and grant. It does not
establish Sol availability, authorize another model, reset task attempts, or
add calls or transport replacements.

The inspected baseline is the sleeping service worker for terminal no-output
slot 3485. Its already-counted replacement is number 21 of 24. Calls remain
3485/8100, and the effective deadline remains 24 October 2026 02:19:15 UTC.
The current route remains gpt-6.1-sol. The old failure has already waited longer
than five minutes. An exact retry, followed by the normal master, is the next
useful check. A new synthetic canary would not settle the reserved request.

## Execution and dependencies

| Item | Requires success | Completion prerequisite | Independent work | Evidence and bound |
|---|---|---|---|---|
| Inspect current admission, owner, charges and terminal receipt | none | none | Plan and read-only diagnosis | Existing check/status/admit; no model calls |
| Implement and test a timing adapter | Reviewed plan and admission | none | Local tests and documentation | One bounded timing change; no production-source mutation |
| Transfer the sleeping worker | Adapter tests; exact unchanged snapshot | none | Local diagnosis if transfer fails | Freeze the verified PID; recheck no live provider child or probe; retain snapshot; terminate only that waiter |
| Resume the existing exact reservation | Transfer; authority and source hashes | none | Local master commands | No added replacement charge; one-use half-open probe |
| Run the original master | Successful probe; normal stage admission | Probe failure still records refresh | Other ready branches subject to shared service | Existing calls, owner attempts and three remaining replacement reservations |
| Retain outcome and refresh | Valid retained evidence | Success or failure of execution | Other authorized ready work | Mission history, timing decisions, provider receipts and frontier |

The adapter uses five minutes from the existing recorded failure reservation,
not from agent restart. Future failure reservations use five minutes, honoring
any longer explicit server retry delay. Old ledger entries remain byte-for-byte
unchanged; separate timing decisions record their effective replacement times.
The policy applies to every retry inside this supervised master process. It
does not permit overlapping requests, bypass validation, retry partial output,
or restore a spent allowance. New execution after a reload uses the retained
worker receipt and this fixed entry point, never an untracked second worker.

The operational wrapper preserves bound production files, the historical v5
policy and sealed results. It applies only explicit runtime timing hooks, using
the existing user-directed scheduling precedent. The complete adapter, plan,
tests, baseline, current program, bindings and grant are hashed in its authority.
Unknown in-flight output, changed shared evidence, invalid grant, exhausted
replacement budget or expired deadline stops dispatch. Failures of individual
product branches retain their original dependency and recovery rules.

## Evidence contract and skeptical review

Question: does the explicit five-minute policy resume exactly one authenticated
pending retry and govern later retries without losing charges or weakening
product checks? Comparator: the actual two-hour schedule and terminal receipt.
Pass: elapsed waits are credited; a fresh eligible failure waits 300 seconds;
longer server delays win; the exact request/schema is preserved; attempts and
all prior charges remain; duplicate/partial/completed requests are refused;
the normal master continues after transport success.

Promotion vetoes: altered authority, unsafe process handover, duplicate dispatch,
lost charges, ignored server delay or failed identity checks. Provider timeout
or overload rejects that transport attempt and triggers only the remaining
finite recovery. Availability of Astra is explanatory context, not a Sol pass.
Even a successful exact response proves no legal conclusion or tool benefit.

The five-minute choice comes directly from the user and is a scheduling
preference, not a measured provider recovery time. Earliest checks use a fake
clock, actual retained receipt validation, adversarial input mutations, and a
stubbed provider across two consecutive failures and a success. The live result
is retained under artifacts/legal-mission-control/2026-10-21/five-minute-retry.

Skeptical review: PASS for this bounded timing change. It retains the real
baseline and shared resources; no proxy becomes legal acceptance. A material
hazard is killing a waiter after it has dispatched: freeze/revalidate before
termination, refuse active children or any probe-started receipt, and restore
the original process on failed pre-transfer validation. Another hazard is
silently inheriting the old two-hour wait on later failures: the controls must
exercise the normal provider retry loop with both timing hooks active.
