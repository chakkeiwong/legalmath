# Remove the unrelated P10 scheduling barrier

The user's question, “why is this necessary? these tasks do not depend on each
other”, identifies a scheduling defect in the already authorized six-call
P14/Gatecoin diagnostic. Neither test consumes P10's result. The previous runner
waited for every master owner to terminate to avoid competing for a nonblocking
provider lock. That workaround has delayed the requested observations for hours.

This is a reviewed scheduling amendment to
`legal-request-variants-2026-10-18.md`, not a new integration program. Preserve the
original plan, all four diagnostic authorities, exact inputs, receipts, and
P10's running source and bindings. The original six calls are an aggregate
ceiling across every diagnostic authority. The 8,100 global ceiling, original
deadline, model `gpt-6.1-sol`, zero retries, and refusal stops still apply.

The earlier recovery note says its scheduling change “grants no parallel
provider permission”. That describes the earlier recovery amendment; it is not
a user prohibition on independent tests. The campaign proposal/grant contains
no worker-concurrency ceiling. The user separately requested these tests and
now challenges making them depend on P10. This amendment implements that request
with one diagnostic request at a time alongside the existing serialized master.
It permits no second diagnostic worker, extra calls, or acquisition attempts.

| Work | Success prerequisites | Completion and continuation |
| --- | --- | --- |
| Stop the waiting diagnostic | Exact trusted PID/start identity; zero charges and reservations | Retain its source and zero-call stop receipt; leave P10 running. |
| Replace the owner barrier | Stopped diagnostic; original inputs and authorities authenticated | Separate diagnostic runner and authority; no P10 source, stage, binding, task, or worker-lock writes. |
| Verify scheduling and accounting | New runner | Exercise production reservation/circuit methods against isolated ledgers, including an occupied master lock, competing charges, open circuit, half-open ownership, and aggregate ceiling; retain receipts. |
| P14 request forms | Passing local checks; closed service circuit and valid global authority | Original before equivalent variants; a request error does not block other forms or Gatecoin. |
| Gatecoin request forms | Same checks; independent of P14 and P10 outcomes | Original before equivalent variants; stop remaining Gatecoin forms on an explicit safety block. |
| Review and refresh | All arms attempted or explicitly stopped; success not required | Preserve actual provider outcomes, update mission history under its lock, run the exact mission refresh, report results. |

The diagnostic keeps its deduplication lock and sequential dispatch. It does
not acquire the master runner, supervisor, or `service-worker.lock`: that lock
protects the master's delayed retry owner, which the diagnostic cannot become.
The shared global ledger lock serializes reservations; the unchanged production
circuit method independently vetoes new calls when the service is open or has
a master-owned half-open probe. Require v2 stage accounting so diagnostic
reservations cannot consume P10's per-stage allowance. A diagnostic failure can
open the real shared service circuit. That is a service veto, not an invented
result dependency. Already in-flight calls may finish; no subsequent diagnostic
call may ignore that circuit. Diagnostic success must not clear or requalify a
master-owned circuit/probe. There is no delayed retry in this diagnostic.

The engineering question is whether these already authorized tests can execute
without waiting for P10 or causing P10's nonblocking lock acquisition to fail.
The comparator is the retained owner-wait runner. The scheduling pass criterion
is a real diagnostic reservation with the master lock occupied, correct atomic
shared charges, and no master-lock acquisition by the diagnostic. Authority,
deadline, budget, corrupt evidence and service-circuit failures veto affected
dispatch. Offline controls establish only implementation behavior. Provider
observations retain the original evidence contract: exact replay, acyclic
schema-reference expansion, and JSON indentation with unchanged legal content.
No result establishes legal correctness, full integration, a model ranking, or
that formatting causally fixed an intermittent failure.

Material defaults: one additional request at a time is a bounded scheduling
choice, not evidence of provider capacity; watch real terminal failures. The
300-second call and 3,600-second batch bounds are inherited diagnostic limits.
The shared service scope, global grant, route and exact six inputs come from
authenticated predecessor evidence. Check these before reservation. Success
does not reset the circuit because this worker owns no service recovery.

Skeptical audit: **PASS subject to focused controls**. The old plan used a whole
worker lifetime as a proxy for a shared resource dependency. This amendment
removes that proxy, preserves actual atomic budget and service checks, and
avoids changing code used by the running master. Expected request rejection
blocks promotion of that arm, not independent tests. Unknown dispatch, invalid
authority, an open shared circuit or exhausted limits are true continuation
vetoes. A new authority aggregates every predecessor instead of resetting the
allocation. Retain results in the existing `request-variants` directory and
return directly to the requested provider observations after the local checks.
